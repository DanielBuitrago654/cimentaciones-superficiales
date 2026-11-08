"""Paquete de la aplicación de cimentaciones superficiales.

Se fija el backend 'Agg' de Matplotlib antes de cualquier importación de
pyplot: la app dibuja las gráficas en memoria (PNG) y no abre ventanas.
"""
import matplotlib

matplotlib.use("Agg")
