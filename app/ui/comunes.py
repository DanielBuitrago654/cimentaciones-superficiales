"""Utilidades de interfaz compartidas por las vistas."""
import os
import subprocess
import sys
from pathlib import Path

import flet as ft

from app.reporte import generar_memoria


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


def generar_y_abrir_memoria(page, calculo):
    """Genera la memoria de un cálculo guardado y la abre en Word.

    Si el archivo ya está abierto en Word, Windows no deja sobrescribirlo
    (PermissionError): se avisa en vez de dejar que la app se caiga. Lo mismo si
    el cálculo se eliminó desde el Historial (``calculo`` llega como None).
    """
    if calculo is None:
        avisar(page, "Ese cálculo ya fue eliminado. Guárdelo de nuevo para generar la memoria.",
               error=True)
        return
    try:
        ruta = generar_memoria(calculo)
    except PermissionError as error:
        nombre = Path(error.filename).name if error.filename else "la memoria"
        avisar(page, f"No se pudo guardar {nombre}: probablemente está abierta en Word. "
                     "Ciérrela e intente de nuevo.", error=True)
        return
    avisar(page, f"Memoria generada: {ruta.name}")
    abrir_archivo(ruta)
