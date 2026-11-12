"""Vista Cálculo: formulario de entrada, resultados, gráficas, guardar y memoria."""
import flet as ft

from app import db
from app.graficas import figura_a_png, grafica_capacidad, grafica_esfuerzos
from app.modelo import CAMPOS, DatosCimentacion, calcular
from app.reporte import hay_despegue
from app.ui.comunes import avisar, generar_y_abrir_memoria


class VistaCalculo:
    """Arma la vista y maneja sus eventos. El control raíz está en ``self.control``."""

    def __init__(self, page, con, al_guardar):
        self.page = page
        self.con = con
        self.al_guardar = al_guardar          # avisa al Historial que debe refrescarse
        self.ultimo = None                    # (datos, resultado) del último cálculo
        self.calculo_id = None                # id en la BD si el cálculo está guardado

        self.campos = self._crear_campos()
        self.estado = ft.Text("Ingrese los datos y presione Calcular.", italic=True)
        self.tabla = ft.Column(spacing=2)
        self.img_capacidad = ft.Image(src=b"", width=520, visible=False)
        self.img_esfuerzos = ft.Image(src=b"", width=520, visible=False)
        self.control = self._armar()

    # ------------------------------------------------------------- armado
    def _crear_campos(self):
        """Un TextField por dato, con su unidad como sufijo y el valor por defecto."""
        defecto = DatosCimentacion().como_dict()
        return {
            campo: ft.TextField(
                label=f"{nombre} ({simbolo})", suffix=unidad, value=str(defecto[campo]),
                dense=True, width=300, keyboard_type=ft.KeyboardType.NUMBER,
                on_change=self._limpiar_error,
            )
            for grupo in CAMPOS.values()
            for campo, (nombre, simbolo, unidad) in grupo.items()
        }

    def _armar(self):
        """Formulario a la izquierda; botones, resultados y gráficas a la derecha."""
        grupos = [
            ft.Column([ft.Text(grupo, weight=ft.FontWeight.BOLD)]
                      + [self.campos[c] for c in campos])
            for grupo, campos in CAMPOS.items()
        ]
        botones = ft.Row([
            ft.FilledButton("Calcular", icon=ft.Icons.CALCULATE, on_click=self.calcular),
            ft.OutlinedButton("Guardar", icon=ft.Icons.SAVE, on_click=self.pedir_guardar),
            ft.OutlinedButton("Memoria .docx", icon=ft.Icons.DESCRIPTION,
                              on_click=self.generar_memoria),
        ])
        formulario = ft.Column(grupos, spacing=10, width=320, scroll=ft.ScrollMode.AUTO)
        resultados = ft.Column(
            [botones,
             ft.Text("Resultados", size=20, weight=ft.FontWeight.BOLD),
             self.estado, self.tabla, self.img_capacidad, self.img_esfuerzos],
            expand=True, scroll=ft.ScrollMode.AUTO,
        )
        return ft.Row([formulario, ft.VerticalDivider(), resultados],
                      expand=True, vertical_alignment=ft.CrossAxisAlignment.START)

    # ---------------------------------------------------------- entradas
    def _limpiar_error(self, e):
        """Al editar un campo se borra su error y el cálculo deja de ser el guardado."""
        e.control.error = None
        self.calculo_id = None                # los datos cambiaron: ya no es el guardado

    def leer_datos(self):
        """Convierte los campos a DatosCimentacion. Retorna None si hay errores."""
        valores, hay_error = {}, False
        for campo, tf in self.campos.items():
            texto = (tf.value or "").strip().replace(",", ".")
            try:
                valores[campo] = float(texto)
                tf.error = None
            except ValueError:
                tf.error = "Vacío" if not texto else "Debe ser un número"
                hay_error = True
        self.page.update()
        if hay_error:
            avisar(self.page, "Revise los campos marcados en rojo.", error=True)
            return None
        return DatosCimentacion(**valores)

    def cargar(self, calculo):
        """Llena el formulario con un cálculo guardado y lo recalcula (Historial -> Abrir)."""
        for campo, valor in calculo["entradas"].items():
            self.campos[campo].value = str(valor)
            self.campos[campo].error = None
        self.calcular(None)
        self.calculo_id = calculo["id"]
        self.estado.value += f"  ·  cálculo #{calculo['id']}: {calculo['proyecto']} · {calculo['descripcion']}"
        self.page.update()

    # ----------------------------------------------------------- acciones
    def calcular(self, e):
        """Botón Calcular: lee y valida los datos, ejecuta el modelo y muestra los resultados.

        Los errores de formato (campo vacío o con letras) los marca ``leer_datos``;
        los de coherencia física (por ejemplo B > L) llegan del modelo como ValueError.
        """
        datos = self.leer_datos()
        if datos is None:
            return
        try:
            r = calcular(datos)
        except ValueError as error:
            avisar(self.page, str(error), error=True)
            return
        self.ultimo = (datos, r)
        self._mostrar_resultados(datos, r)

    def _mostrar_resultados(self, datos, r):
        """Llena la tabla de resultados, el estado (cumple o no) y las dos gráficas."""
        filas = [
            ("Factores Nc / Nq / Nγ", f"{r.Nc:.2f} / {r.Nq:.2f} / {r.Ngamma:.2f}", ""),
            ("Excentricidad e / ancho efectivo B'", f"{r.e:.3f} / {r.B_efectivo:.3f}", "m"),
            ("Capacidad última q_u", f"{r.q_ult:,.1f}", "kPa"),
            ("Carga última / admisible", f"{r.Q_ult:,.0f} / {r.Q_adm:,.0f}", "kN"),
            ("Factor de seguridad", f"{r.FS:.2f}  (requerido {datos.FS_req:g})", ""),
            ("Presión de contacto máx / mín", f"{r.q_max:.1f} / {r.q_min:.1f}", "kPa"),
            ("Asentamiento quad (Simpson)", f"{r.s_quad:.1f}  ({r.s_simpson:.1f})", "mm"),
            ("B mínimo por capacidad (brentq)",
             f"{r.B_min:.2f}" if r.B_min is not None else "fuera de rango", "m"),
        ]
        self.tabla.controls = [
            ft.Row([ft.Text(n, width=260), ft.Text(f"{v} {u}", weight=ft.FontWeight.W_500)])
            for n, v, u in filas
        ]
        self.estado.value = "CUMPLE" if r.cumple else "NO CUMPLE: " + ", ".join(
            t for t, ok in [("capacidad portante", r.cumple_capacidad),
                            ("asentamiento", r.cumple_asentamiento)] if not ok)
        self.estado.color = ft.Colors.GREEN_700 if r.cumple else ft.Colors.RED_700
        if hay_despegue(datos, r):
            self.estado.value += "  ·  Advertencia: e > B/6, parte de la base se despega"
            if r.cumple:
                self.estado.color = ft.Colors.ORANGE_800
        self.estado.italic = False
        self.estado.weight = ft.FontWeight.BOLD
        self.img_capacidad.src = figura_a_png(grafica_capacidad(datos, r.B_min))
        self.img_esfuerzos.src = figura_a_png(grafica_esfuerzos(datos))
        self.img_capacidad.visible = self.img_esfuerzos.visible = True
        self.page.update()

    def pedir_guardar(self, e):
        """Abre un diálogo para elegir proyecto y descripción antes de guardar."""
        if self.ultimo is None:
            avisar(self.page, "Primero calcule.", error=True)
            return
        existentes = [p["nombre"] for p in db.listar_proyectos(self.con)]
        nombre = ft.TextField(label="Proyecto", width=400, value=existentes[0] if existentes else "")
        ubicacion = ft.TextField(label="Ubicación de la obra", hint_text="Bogotá D.C., Fontibón",
                                 helper="Ciudad o dirección del proyecto (solo para proyectos nuevos)",
                                 width=400)
        descripcion = ft.TextField(label="Descripción del elemento", hint_text="Zapata Z-1, eje B-3",
                                   width=400)
        elegir = ft.Dropdown(
            label="o elegir un proyecto existente", width=400,
            options=[ft.DropdownOption(n) for n in existentes],
            on_select=lambda ev: setattr(nombre, "value", ev.control.value) or self.page.update(),
        )

        def guardar(ev):
            """Valida proyecto y descripción, guarda en SQLite y cierra el diálogo."""
            if not nombre.value.strip() or not descripcion.value.strip():
                nombre.error = None if nombre.value.strip() else "Obligatorio"
                descripcion.error = None if descripcion.value.strip() else "Obligatorio"
                self.page.update()
                return
            datos, r = self.ultimo
            pid = db.obtener_o_crear_proyecto(self.con, nombre.value.strip(), ubicacion.value.strip())
            self.calculo_id = db.guardar_calculo(self.con, pid, descripcion.value.strip(),
                                                 datos.como_dict(), r.como_dict(), r.cumple)
            self.page.pop_dialog()
            avisar(self.page, f"Cálculo #{self.calculo_id} guardado.")
            self.al_guardar()

        self.page.show_dialog(ft.AlertDialog(
            title=ft.Text("Guardar cálculo"),
            content=ft.Column([elegir, nombre, ubicacion, descripcion], tight=True, width=400),
            actions=[ft.TextButton("Cancelar", on_click=lambda ev: self.page.pop_dialog()),
                     ft.FilledButton("Guardar", on_click=guardar)],
        ))

    def generar_memoria(self, e):
        """Botón Memoria .docx: genera y abre la memoria del cálculo guardado.

        Exige guardar primero, porque la memoria se arma con los datos de la base
        de datos (proyecto, ubicación, descripción y fecha).
        """
        if self.calculo_id is None:
            avisar(self.page, "Guarde el cálculo antes de generar la memoria.", error=True)
            return
        generar_y_abrir_memoria(self.page, db.obtener_calculo(self.con, self.calculo_id))
