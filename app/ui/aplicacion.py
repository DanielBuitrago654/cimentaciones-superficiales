"""Ventana principal: navegación entre las vistas Cálculo e Historial."""
import flet as ft

from app import db
from app.ui.vista_calculo import VistaCalculo
from app.ui.vista_historial import VistaHistorial


def main(page: ft.Page):
    """Configura la ventana, abre la base de datos y arma la navegación entre vistas.

    Flet llama esta función al iniciar (``ft.run(main)`` en main.py). Las dos
    vistas comparten la misma conexión: al guardar en Cálculo se refresca el
    Historial, y al abrir desde el Historial se carga el cálculo en Cálculo.
    """
    page.title = "Cimentaciones superficiales · capacidad portante y asentamiento"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.window.width, page.window.height = 1280, 820
    page.padding = 16

    con = db.conectar()   # crea la base de datos y las tablas si no existen

    def ir_a(indice):
        """Muestra la vista ``indice`` (0 = Cálculo, 1 = Historial)."""
        riel.selected_index = indice
        contenido.content = vistas[indice].control
        page.update()

    def abrir_desde_historial(calculo):
        """Lleva un cálculo guardado al formulario de la vista Cálculo."""
        ir_a(0)
        calculo_vista.cargar(calculo)

    calculo_vista = VistaCalculo(page, con, al_guardar=lambda: historial_vista.refrescar())
    historial_vista = VistaHistorial(page, con, al_abrir=abrir_desde_historial)
    vistas = [calculo_vista, historial_vista]

    riel = ft.NavigationRail(
        selected_index=0,
        label_type=ft.NavigationRailLabelType.ALL,
        destinations=[
            ft.NavigationRailDestination(icon=ft.Icons.CALCULATE, label="Cálculo"),
            ft.NavigationRailDestination(icon=ft.Icons.HISTORY, label="Historial"),
        ],
        on_change=lambda e: ir_a(e.control.selected_index),
    )
    contenido = ft.Container(content=calculo_vista.control, expand=True)
    page.add(ft.Row([riel, ft.VerticalDivider(width=1), contenido], expand=True))
