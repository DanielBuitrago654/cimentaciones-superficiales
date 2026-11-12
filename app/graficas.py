"""Gráficas técnicas con Matplotlib.

Cada función devuelve una ``Figure``; ``figura_a_png`` la convierte a bytes
PNG. Los mismos bytes se muestran en la app (ft.Image) y se insertan en la
memoria de cálculo (InlineImage), así la gráfica es idéntica en ambos lados.
"""
import io

import numpy as np
from matplotlib.figure import Figure
from matplotlib.patches import Patch

from app.modelo import (DatosCimentacion, carga_ultima, esfuerzo_efectivo_inicial,
                        incremento_esfuerzo, presion_neta)

AZUL, NARANJA, VERDE, GRIS = "#2a78d6", "#eb6834", "#1baf7a", "#898781"


def _figura(ancho=6.4, alto=4.2):
    """Figura vacía con fondo blanco."""
    fig = Figure(figsize=(ancho, alto), dpi=120, layout="constrained")
    # sections.py activa el estilo 'ggplot' al importarse; se fija fondo blanco aquí
    fig.set_facecolor("white")
    return fig


def _estilo(ax, titulo, xlabel, ylabel):
    """Estilo sobrio para unos ejes (rejilla tenue, sin bordes superiores)."""
    ax.set_facecolor("white")
    ax.set_title(titulo, fontsize=11, loc="left")
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.grid(True, color="#e3e2de", linewidth=0.6)
    ax.spines[["top", "right"]].set_visible(False)
    for lado in ("left", "bottom"):
        ax.spines[lado].set_color(GRIS)


def _ejes(titulo, xlabel, ylabel):
    """Crea una figura con unos solos ejes ya estilizados."""
    fig = _figura()
    ax = fig.add_subplot()
    _estilo(ax, titulo, xlabel, ylabel)
    return fig, ax


def grafica_capacidad(d: DatosCimentacion, B_min=None):
    """Carga admisible Q_adm = Q_ult/FS_req (kN) en función del ancho B (m).

    La curva se evalúa de forma vectorizada sobre una malla de anchos. Su
    cruce con la carga aplicada P es el ancho mínimo hallado con brentq.
    El quiebre en Df/B = 1 es propio de los factores de profundidad de Hansen
    (k pasa de Df/B a arctan(Df/B)), no un error numérico.
    """
    e = d.M / d.P
    B = np.linspace(max(2.2 * e, 0.3), max(2.0 * d.B, 3.0), 200)
    Q_adm = carga_ultima(B, d) / d.FS_req

    fig, ax = _ejes("Carga admisible vs. ancho de la zapata",
                    "Ancho B (m)", "Carga (kN)")
    ax.plot(B, Q_adm, color=AZUL, linewidth=2,
            label=f"Q_adm = Q_ult / {d.FS_req:g}  (L/B = {d.L / d.B:.2f})")
    ax.axhline(d.P, color=NARANJA, linewidth=2, linestyle="--", label=f"P aplicada = {d.P:g} kN")
    ax.axvline(d.B, color=GRIS, linewidth=1, linestyle=":")
    ax.plot([d.B], [carga_ultima(d.B, d) / d.FS_req], "o", color=AZUL, markersize=8,
            markeredgecolor="white", label=f"Diseño: B = {d.B:g} m")
    if B_min is not None:
        ax.plot([B_min], [d.P], "o", color=NARANJA, markersize=8, markeredgecolor="white",
                label=f"B mínimo (brentq) = {B_min:.2f} m")
    ax.set_xlim(B[0], B[-1])
    ax.set_ylim(bottom=0)
    ax.legend(frameon=False, fontsize=8, loc="upper left")
    return fig


def grafica_esfuerzos(d: DatosCimentacion):
    """Perfil de esfuerzos bajo el centro: σ'0 y Δσ (kPa) vs. profundidad (m).

    Se sombrea el estrato de arcilla, que es donde se integra el asentamiento.
    """
    z_fondo = d.z_arcilla + d.H_arcilla
    z = np.linspace(0.01, 1.25 * z_fondo, 300)
    delta = incremento_esfuerzo(presion_neta(d), d.B, d.L, z)
    sigma0 = esfuerzo_efectivo_inicial(z, d)

    fig, ax = _ejes("Esfuerzos bajo el centro de la zapata",
                    "Esfuerzo (kPa)", "Profundidad bajo la base z (m)")
    ax.axhspan(d.z_arcilla, z_fondo, color=VERDE, alpha=0.12, linewidth=0,
               label="Estrato de arcilla")
    ax.plot(delta, z, color=AZUL, linewidth=2, label="Δσ (Boussinesq)")
    ax.plot(sigma0, z, color=NARANJA, linewidth=2, label="σ'0 = γ (Df + z)")
    ax.set_ylim(z[-1], 0)          # profundidad hacia abajo
    ax.set_xlim(left=0)
    ax.legend(frameon=False, fontsize=8, loc="lower right")
    return fig


def grafica_comparacion(filas):
    """Barras de FS y de asentamiento (mm) de varios cálculos, con su límite.

    ``filas`` viene de ``comparacion.filas_comparacion``. Cada barra lleva una
    raya negra con su propio límite (FS requerido o asentamiento admisible),
    porque cada cálculo puede tener límites distintos. Las barras naranjas no
    cumplen ese criterio.
    """
    x = np.arange(len(filas))
    etiquetas = [f["etiqueta"] for f in filas]
    fig = _figura(ancho=8.0, alto=3.4)
    criterios = [
        ("Factor de seguridad", "FS (-)", "FS", "FS_req", "FS requerido", "cumple_capacidad"),
        ("Asentamiento", "Asentamiento s (mm)", "s", "s_adm", "s admisible",
         "cumple_asentamiento"),
    ]
    for i, (titulo, ylabel, clave, limite, nombre_limite, cumple) in enumerate(criterios, 1):
        ax = fig.add_subplot(1, 2, i)
        _estilo(ax, titulo, "Cálculo", ylabel)
        valores = np.array([f[clave] for f in filas])
        limites = np.array([f[limite] for f in filas])
        colores = [AZUL if f[cumple] else NARANJA for f in filas]
        ax.bar(x, valores, width=0.6, color=colores)
        ax.hlines(limites, x - 0.38, x + 0.38, colors="black", linewidth=2,
                  label=nombre_limite)
        ax.set_xticks(x, etiquetas)
        ax.set_ylim(0, 1.15 * max(valores.max(), limites.max()))
        ax.legend(handles=[ax.get_legend_handles_labels()[0][0],
                           Patch(color=AZUL, label="Cumple"),
                           Patch(color=NARANJA, label="No cumple")],
                  frameon=False, fontsize=8, ncol=3,
                  loc="upper center", bbox_to_anchor=(0.5, -0.22))
    return fig


def figura_a_png(fig):
    """Convierte una Figure a bytes PNG (para Flet y para docxtpl)."""
    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", dpi=120)
    return buffer.getvalue()
