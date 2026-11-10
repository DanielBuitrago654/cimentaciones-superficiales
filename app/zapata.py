"""Geometría en planta de la zapata, construida sobre pysections.

La planta de una zapata rectangular es un polígono. La clase base
``_SinglePolygonSection`` de pysections (archivo ``sections.py``, copiado sin
modificaciones) calcula área, centroide e inercias de cualquier polígono;
aquí solo se definen los cuatro vértices.

Convención (la misma de pysections):
    eje horizontal del polígono -> dirección del ancho B
    eje vertical del polígono   -> dirección del largo L
"""
import numpy as np

from app.sections import _SinglePolygonSection


class ZapataRectangular(_SinglePolygonSection):
    """Planta rectangular de B x L (m), con esquina inferior izquierda en (0, 0)."""

    def __init__(self, B, L):
        self.B = B
        self.L = L
        super().__init__()

    def _calculate_points(self):
        """Vértices en sentido antihorario (área positiva en pysections)."""
        return np.array(
            [[0.0, 0.0], [self.B, 0.0], [self.B, self.L], [0.0, self.L]],
            dtype=float,
        )

    @property
    def I_flexion(self):
        """Inercia (m⁴) respecto al eje centroidal paralelo a L.

        Es la que interviene cuando el momento M hace variar la presión a lo
        largo de B. En pysections corresponde a ``Izz`` (= L·B³/12).
        """
        return self.Izz


def presiones_contacto(P, M, B, L):
    """Presiones de contacto máxima y mínima bajo la zapata (kPa).

    Usa la fórmula de flexión compuesta q = P/A ± M·c/I con A e I de pysections.
    Si la excentricidad e = M/P supera B/6 parte de la base se despega y se
    usa la distribución triangular: q_max = 4P / (3·L·(B − 2e)), q_min = 0.

    Parámetros: P (kN), M (kN·m), B y L (m).
    Retorna: (q_max, q_min) en kPa.
    """
    zapata = ZapataRectangular(B, L)
    e = M / P
    if e <= B / 6:
        flexion = M * (B / 2) / zapata.I_flexion
        return P / zapata.area + flexion, P / zapata.area - flexion
    return 4 * P / (3 * L * (B - 2 * e)), 0.0
