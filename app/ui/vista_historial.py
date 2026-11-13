"""Vista Historial: listar, buscar, reabrir, comparar, generar memoria y eliminar cálculos o proyectos."""
import flet as ft

from app import db
from app.comparacion import filas_comparacion
from app.graficas import figura_a_png, grafica_comparacion
from app.ui.comunes import avisar, confirmar, generar_y_abrir_memoria


class VistaHistorial:
    """Lista de cálculos guardados. El control raíz está en ``self.control``."""

    def __init__(self, page, con, al_abrir):
        self.page = page
        self.con = con
        self.al_abrir = al_abrir          # recibe el cálculo y lo lleva a la vista Cálculo
        self.seleccion = set()            # ids marcados para comparar
        self.buscador = ft.TextField(
            label="Buscar por proyecto o descripción", prefix_icon=ft.Icons.SEARCH,
            on_change=lambda e: self.refrescar(), width=420,
        )
        self.boton_comparar = ft.FilledButton(
            "Comparar seleccionados", icon=ft.Icons.COMPARE_ARROWS,
            on_click=self.comparar, disabled=True,
        )
        self.proyecto = ft.Dropdown(label="Proyecto", width=420, dense=True)
        self.boton_eliminar_proyecto = ft.OutlinedButton(
            "Eliminar proyecto", icon=ft.Icons.DELETE_FOREVER, icon_color=ft.Colors.RED_700,
            on_click=self.eliminar_proyecto,
        )
        self.lista = ft.ListView(expand=True, spacing=4)
        self.control = ft.Column(
            [ft.Text("Historial de cálculos", size=20, weight=ft.FontWeight.BOLD),
             ft.Row([self.buscador, self.boton_comparar]),
             ft.Text("Marque dos o más cálculos para compararlos.", italic=True, size=12),
             self.lista,
             ft.Divider(),
             ft.Row([self.proyecto, self.boton_eliminar_proyecto])],
            expand=True,
        )
        self.refrescar()

    def refrescar(self):
        """Vuelve a consultar la base de datos con el texto del buscador."""
        filas = db.buscar_calculos(self.con, self.buscador.value or "")
        self.seleccion &= {f["id"] for f in filas}   # olvida los que ya no existen
        self.lista.controls = [self._fila(f) for f in filas] or [
            ft.Text("No hay cálculos guardados que coincidan.", italic=True)]
        self._actualizar_boton()
        self._actualizar_proyectos()
        self.page.update()

    def _actualizar_proyectos(self):
        """Opciones del menú de proyectos, con el número de cálculos de cada uno."""
        proyectos = db.listar_proyectos(self.con)
        self.proyecto.options = [
            ft.DropdownOption(key=str(p["id"]), text=f"{p['nombre']} ({p['n_calculos']} cálculos)")
            for p in proyectos
        ]
        if self.proyecto.value not in {str(p["id"]) for p in proyectos}:
            self.proyecto.value = None

    def _fila(self, f):
        """Un renglón: casilla para comparar, estado, datos y botones de acción."""
        cumple = bool(f["cumple"])
        return ft.ListTile(
            leading=ft.Row([
                ft.Checkbox(value=f["id"] in self.seleccion,
                            on_change=lambda e, i=f["id"]: self._marcar(i, e.control.value)),
                ft.Icon(ft.Icons.CHECK_CIRCLE if cumple else ft.Icons.CANCEL,
                        color=ft.Colors.GREEN_700 if cumple else ft.Colors.RED_700),
            ], tight=True),
            title=ft.Text(f"#{f['id']} · {f['descripcion']}"),
            subtitle=ft.Text(f"{f['proyecto']} · {f['fecha']} · "
                             f"{'Cumple' if cumple else 'No cumple'}"),
            trailing=ft.Row([
                ft.IconButton(ft.Icons.OPEN_IN_NEW, tooltip="Abrir",
                              on_click=lambda e, i=f["id"]: self.abrir(i)),
                ft.IconButton(ft.Icons.DESCRIPTION, tooltip="Generar memoria",
                              on_click=lambda e, i=f["id"]: self.memoria(i)),
                ft.IconButton(ft.Icons.DELETE, tooltip="Eliminar", icon_color=ft.Colors.RED_700,
                              on_click=lambda e, fila=f: self.eliminar(fila)),
            ], tight=True),
        )

    def _marcar(self, calculo_id, marcado):
        """Agrega o quita un cálculo de la selección para comparar."""
        if marcado:
            self.seleccion.add(calculo_id)
        else:
            self.seleccion.discard(calculo_id)
        self._actualizar_boton()
        self.page.update()

    def _actualizar_boton(self):
        """El botón Comparar se activa con dos o más cálculos marcados."""
        n = len(self.seleccion)
        self.boton_comparar.disabled = n < 2
        self.boton_comparar.content = f"Comparar seleccionados ({n})" if n else \
            "Comparar seleccionados"

    def abrir(self, calculo_id):
        """Botón Abrir: carga el cálculo en el formulario de la vista Cálculo."""
        self.al_abrir(db.obtener_calculo(self.con, calculo_id))

    def memoria(self, calculo_id):
        """Botón Generar memoria: crea y abre el .docx de ese cálculo."""
        generar_y_abrir_memoria(self.page, db.obtener_calculo(self.con, calculo_id))

    def comparar(self, e):
        """Botón Comparar: tabla y gráfica de barras de los cálculos marcados."""
        calculos = [db.obtener_calculo(self.con, i) for i in sorted(self.seleccion)]
        filas = filas_comparacion(calculos)
        self.page.show_dialog(ft.AlertDialog(
            title=ft.Text(f"Comparación de {len(filas)} cálculos"),
            content=ft.Column(
                [self._tabla_comparacion(filas),
                 ft.Image(src=figura_a_png(grafica_comparacion(filas)), width=780)],
                tight=True, scroll=ft.ScrollMode.AUTO, width=920,
            ),
            actions=[ft.TextButton("Cerrar", on_click=lambda ev: self.page.pop_dialog())],
        ))

    @staticmethod
    def _tabla_comparacion(filas):
        """DataTable con dimensiones, FS, asentamiento y estado de cada cálculo."""
        columnas = ["Cálculo", "Descripción", "B (m)", "L (m)", "Df (m)", "P (kN)",
                    "M (kN·m)", "FS (req.)", "s mm (adm.)", "Estado"]

        def celdas(f):
            estado = ft.Text("CUMPLE" if f["cumple"] else "NO CUMPLE",
                             weight=ft.FontWeight.BOLD,
                             color=ft.Colors.GREEN_700 if f["cumple"] else ft.Colors.RED_700)
            textos = [f["etiqueta"], f["descripcion"], f"{f['B']:g}", f"{f['L']:g}",
                      f"{f['Df']:g}", f"{f['P']:g}", f"{f['M']:g}",
                      f"{f['FS']:.2f} ({f['FS_req']:g})",
                      f"{f['s']:.1f} ({f['s_adm']:g})"]
            return [ft.DataCell(ft.Text(t)) for t in textos] + [ft.DataCell(estado)]

        return ft.DataTable(
            columns=[ft.DataColumn(ft.Text(c)) for c in columnas],
            rows=[ft.DataRow(cells=celdas(f)) for f in filas],
            column_spacing=18,
        )

    def eliminar(self, fila):
        """Botón Eliminar: pide confirmación y, si se acepta, borra el cálculo."""
        def borrar():
            """Borra el cálculo de SQLite, avisa y refresca la lista."""
            db.eliminar_calculo(self.con, fila["id"])
            avisar(self.page, f"Cálculo #{fila['id']} eliminado.")
            self.refrescar()

        confirmar(self.page, "Eliminar cálculo",
                  f"¿Eliminar el cálculo #{fila['id']} «{fila['descripcion']}»? "
                  "Esta acción no se puede deshacer.", borrar)

    def eliminar_proyecto(self, e):
        """Botón Eliminar proyecto: borra el proyecto elegido y, en cascada, sus cálculos.

        La cascada la hace SQLite (ON DELETE CASCADE en db.py), no esta función.
        """
        if not self.proyecto.value:
            avisar(self.page, "Elija primero el proyecto que quiere eliminar.", error=True)
            return
        proyecto_id = int(self.proyecto.value)
        p = next(p for p in db.listar_proyectos(self.con) if p["id"] == proyecto_id)

        def borrar():
            """Borra el proyecto de SQLite, avisa y refresca la lista."""
            db.eliminar_proyecto(self.con, proyecto_id)
            avisar(self.page, f"Proyecto «{p['nombre']}» eliminado con sus "
                              f"{p['n_calculos']} cálculos.")
            self.refrescar()

        confirmar(self.page, "Eliminar proyecto",
                  f"¿Eliminar el proyecto «{p['nombre']}» y sus {p['n_calculos']} cálculos? "
                  "Esta acción no se puede deshacer.", borrar)
