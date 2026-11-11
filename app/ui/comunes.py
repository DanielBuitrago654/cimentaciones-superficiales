"""Utilidades de interfaz compartidas por las vistas."""
import os
import subprocess
import sys

import flet as ft


def avisar(page, mensaje, error=False):
    """Muestra un SnackBar (verde si todo salió bien, rojo si hubo error)."""
    page.show_dialog(ft.SnackBar(
        ft.Text(mensaje, color=ft.Colors.WHITE),
        bgcolor=ft.Colors.RED_700 if error else ft.Colors.GREEN_700,
    ))


def confirmar(page, titulo, mensaje, al_aceptar):
    """Diálogo de confirmación; ``al_aceptar`` se ejecuta solo si el usuario acepta."""
    def aceptar(e):
        """Cierra el diálogo y ejecuta la acción confirmada."""
        page.pop_dialog()
        al_aceptar()

    page.show_dialog(ft.AlertDialog(
        modal=True,
        title=ft.Text(titulo),
        content=ft.Text(mensaje),
        actions=[
            ft.TextButton("Cancelar", on_click=lambda e: page.pop_dialog()),
            ft.FilledButton("Eliminar", on_click=aceptar,
                            style=ft.ButtonStyle(bgcolor=ft.Colors.RED_700)),
        ],
    ))


def abrir_archivo(ruta):
    """Abre un archivo con el programa predeterminado del sistema (Word, etc.)."""
    try:
        if sys.platform.startswith("win"):
            os.startfile(ruta)  # noqa: S606 (solo existe en Windows)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(ruta)])
        else:
            subprocess.Popen(["xdg-open", str(ruta)])
    except OSError:
        pass  # si no se puede abrir, el usuario igual tiene la ruta en el aviso

