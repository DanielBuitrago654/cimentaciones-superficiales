"""Modelo de ingeniería: capacidad portante y asentamiento de zapatas.

Este módulo NO importa Flet: se puede usar y probar sin abrir la ventana.

Unidades (SI, consistentes en todo el módulo):
    longitudes en m, fuerzas en kN, momentos en kN·m,
    esfuerzos y presiones en kPa (kN/m²), pesos unitarios en kN/m³,
    ángulos en grados, asentamientos en mm (solo en el resultado final).

Referencias:
    [1] Das, B. M. Principios de ingeniería de cimentaciones, 7.ª ed.,
        Cengage, 2012. Cap. 3 (ecuación general de capacidad de carga,
        factores de forma, profundidad e inclinación; carga excéntrica,
        método del área efectiva de Meyerhof) y cap. 5 (incremento de
        esfuerzo de Boussinesq y asentamiento por consolidación).
    [2] Vesić, A. S. (1973). Analysis of ultimate loads of shallow
        foundations. J. Soil Mech. Found. Div., ASCE, 99(1), 45-73.
    [3] NSR-10, Título H, numeral H.4.7: factores de seguridad indirectos
        mínimos para capacidad portante.

Hipótesis:
    - Suelo homogéneo para la capacidad portante, nivel freático profundo.
    - Carga excéntrica en una sola dirección (a lo largo de B).
    - Estrato de arcilla normalmente consolidada para el asentamiento, con
      incremento de esfuerzo de Boussinesq bajo el centro de la zapata.
"""
from dataclasses import asdict, dataclass

import numpy as np
from scipy import integrate, optimize  # se usan desde el martes (quad y brentq)

from app.zapata import presiones_contacto


# ---------------------------------------------------------------------------
# Datos de entrada y resultados
# ---------------------------------------------------------------------------
# Descripción, símbolo y unidad de cada dato de entrada, agrupados.
# La interfaz y la memoria de cálculo usan esta misma tabla.
CAMPOS = {
    "Geometría y cargas": {
        "B": ("Ancho (lado corto)", "B", "m"),
        "L": ("Largo", "L", "m"),
        "Df": ("Profundidad de desplante", "Df", "m"),
        "P": ("Carga vertical de servicio", "P", "kN"),
        "M": ("Momento (eje paralelo a L)", "M", "kN·m"),
        "beta": ("Inclinación de la carga", "β", "°"),
    },
    "Suelo de fundación": {
        "gamma": ("Peso unitario", "γ", "kN/m³"),
        "c": ("Cohesión", "c", "kPa"),
        "phi": ("Ángulo de fricción", "φ", "°"),
        "FS_req": ("Factor de seguridad requerido", "FS", "-"),
    },
    "Estrato de arcilla": {
        "z_arcilla": ("Profundidad del techo bajo la base", "z1", "m"),
        "H_arcilla": ("Espesor", "H", "m"),
        "Cc": ("Índice de compresión", "Cc", "-"),
        "e0": ("Relación de vacíos inicial", "e0", "-"),
        "s_adm": ("Asentamiento admisible", "s_adm", "mm"),
    },
}


@dataclass
class DatosCimentacion:
    """Datos de entrada de una zapata rectangular aislada."""

    B: float = 2.2          # ancho (lado corto), m
    L: float = 2.2          # largo, m
    Df: float = 1.5         # profundidad de desplante, m
    P: float = 1200.0       # carga vertical de servicio, kN
    M: float = 120.0        # momento alrededor del eje paralelo a L, kN·m
    beta: float = 0.0       # inclinación de la carga respecto a la vertical, °
    gamma: float = 18.0     # peso unitario del suelo, kN/m³
    c: float = 10.0         # cohesión, kPa
    phi: float = 28.0       # ángulo de fricción interna, °
    FS_req: float = 3.0     # factor de seguridad requerido (NSR-10 H.4.7)
    z_arcilla: float = 3.0  # profundidad del techo de la arcilla bajo la base, m
    H_arcilla: float = 3.0  # espesor del estrato de arcilla, m
    Cc: float = 0.25        # índice de compresión, -
    e0: float = 0.90        # relación de vacíos inicial, -
    s_adm: float = 50.0     # asentamiento admisible, mm

    def validar(self):
        """Revisa coherencia física de los datos.

        Retorna una lista de mensajes de error (vacía si todo está bien).
        """
        errores = []
        positivos = {"B": self.B, "L": self.L, "Df": self.Df, "P": self.P,
                     "gamma": self.gamma, "FS_req": self.FS_req,
                     "H_arcilla": self.H_arcilla, "Cc": self.Cc,
                     "e0": self.e0, "s_adm": self.s_adm}
        errores += [f"{k} debe ser mayor que cero." for k, v in positivos.items() if v <= 0]
        if self.B > self.L:
            errores.append("B es el lado corto: debe cumplirse B ≤ L.")
        if self.c < 0 or self.M < 0 or self.beta < 0 or self.z_arcilla < 0:
            errores.append("c, M, β y la profundidad de la arcilla no pueden ser negativos.")
        if not 0 <= self.phi <= 45:
            errores.append("φ debe estar entre 0° y 45°.")
        if self.beta >= 90:
            errores.append("β debe ser menor que 90°.")
        if self.P > 0 and self.M / self.P >= self.B / 2:
            errores.append("La excentricidad e = M/P es mayor o igual a B/2: la zapata se voltea.")
        return errores

    def como_dict(self):
        """Diccionario con los datos (para guardar en la base de datos)."""
        return asdict(self)


@dataclass
class ResultadoCimentacion:
    """Resultados del cálculo (unidades en el nombre de cada comentario)."""

    Nc: float
    Nq: float
    Ngamma: float
    e: float                # excentricidad, m
    B_efectivo: float       # B' = B − 2e, m
    q_ult: float            # capacidad última sobre el área efectiva, kPa
    Q_ult: float            # carga última, kN
    Q_adm: float            # carga admisible = Q_ult / FS_req, kN
    FS: float               # factor de seguridad obtenido, -
    q_max: float            # presión de contacto máxima, kPa
    q_min: float            # presión de contacto mínima, kPa
    q_neta: float           # presión neta para asentamiento, kPa
    s_quad: float           # asentamiento integrado con scipy quad, mm
    s_simpson: float        # asentamiento con el promedio de Simpson de Das, mm
    B_min: float | None     # ancho mínimo que cumple FS_req (brentq), m
    cumple_capacidad: bool
    cumple_asentamiento: bool

    @property
    def cumple(self):
        """True si la zapata cumple capacidad portante y asentamiento."""
        return self.cumple_capacidad and self.cumple_asentamiento

    def como_dict(self):
        """Diccionario con los resultados (para guardar en la base de datos)."""
        return asdict(self)


# ---------------------------------------------------------------------------
# Capacidad portante (ecuación general, Das [1] cap. 3) — vectorizado
# ---------------------------------------------------------------------------
def factores_capacidad(phi):
    """Factores de capacidad de carga Nc, Nq, Nγ (Vesić).

    Nq = tan²(45° + φ/2)·e^(π·tanφ)
    Nc = (Nq − 1)·cotφ        (para φ = 0, Nc = π + 2 = 5.14)
    Nγ = 2·(Nq + 1)·tanφ

    ``phi`` en grados; acepta escalares o arreglos de NumPy.
    """
    phi_r = np.radians(np.asarray(phi, dtype=float))
    tan_phi = np.tan(phi_r)
    Nq = np.tan(np.pi / 4 + phi_r / 2) ** 2 * np.exp(np.pi * tan_phi)
    with np.errstate(divide="ignore", invalid="ignore"):
        Nc = np.where(phi_r > 0, (Nq - 1) / tan_phi, np.pi + 2)
    Ngamma = 2 * (Nq + 1) * tan_phi
    return Nc, Nq, Ngamma


def factores_forma(B, L, phi, Nc, Nq):
    """Factores de forma de De Beer (1970): Fcs, Fqs, Fγs."""
    tan_phi = np.tan(np.radians(phi))
    Fcs = 1 + (B / L) * (Nq / Nc)
    Fqs = 1 + (B / L) * tan_phi
    Fgs = 1 - 0.4 * (B / L)
    return Fcs, Fqs, Fgs


def factores_profundidad(Df, B, phi, Nc):
    """Factores de profundidad de Hansen (1970): Fcd, Fqd, Fγd.

    Si Df/B ≤ 1 se usa k = Df/B; si Df/B > 1, k = arctan(Df/B) en radianes.
    """
    phi_r = np.radians(phi)
    razon = np.asarray(Df / B, dtype=float)
    k = np.where(razon <= 1, razon, np.arctan(razon))
    Fqd = 1 + 2 * np.tan(phi_r) * (1 - np.sin(phi_r)) ** 2 * k
    with np.errstate(divide="ignore", invalid="ignore"):
        Fcd = np.where(phi_r > 0, Fqd - (1 - Fqd) / (Nc * np.tan(phi_r)), 1 + 0.4 * k)
    Fgd = np.ones_like(k)
    return Fcd, Fqd, Fgd


def factores_inclinacion(beta, phi):
    """Factores de inclinación de Meyerhof y Hanna (1981): Fci, Fqi, Fγi."""
    Fci = Fqi = (1 - beta / 90) ** 2
    if beta == 0:
        Fgi = 1.0
    elif beta < phi:
        Fgi = (1 - beta / phi) ** 2
    else:
        Fgi = 0.0  # carga más inclinada que φ: el término de γ no aporta
    return Fci, Fqi, Fgi


def capacidad_ultima(B, L, Df, gamma, c, phi, beta=0.0, e=0.0):
    """Capacidad de carga última q_u (kPa) con la ecuación general.

    q_u = c·Nc·Fcs·Fcd·Fci + q·Nq·Fqs·Fqd·Fqi + ½·γ·B'·Nγ·Fγs·Fγd·Fγi

    con q = γ·Df y B' = B − 2e (área efectiva de Meyerhof). Los factores de
    forma usan B'/L y los de profundidad usan B, como indica Das [1].
    ``B`` puede ser un arreglo de NumPy (se usa para la curva Q_adm vs B).
    """
    B = np.asarray(B, dtype=float)
    B_ef = B - 2 * e
    q = gamma * Df
    Nc, Nq, Ng = factores_capacidad(phi)
    Fcs, Fqs, Fgs = factores_forma(B_ef, L, phi, Nc, Nq)
    Fcd, Fqd, Fgd = factores_profundidad(Df, B, phi, Nc)
    Fci, Fqi, Fgi = factores_inclinacion(beta, phi)
    return (c * Nc * Fcs * Fcd * Fci
            + q * Nq * Fqs * Fqd * Fqi
            + 0.5 * gamma * B_ef * Ng * Fgs * Fgd * Fgi)


def carga_ultima(B, d: DatosCimentacion):
    """Carga última Q_ult = q_u·B'·L (kN) manteniendo la relación L/B de los datos.

    ``B`` puede ser escalar o arreglo: así se evalúa toda la curva sin ciclos.
    """
    B = np.asarray(B, dtype=float)
    L = B * (d.L / d.B)
    e = d.M / d.P
    q_u = capacidad_ultima(B, L, d.Df, d.gamma, d.c, d.phi, d.beta, e)
    return q_u * (B - 2 * e) * L


