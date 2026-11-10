"""Pruebas del modelo contra la literatura y casos resueltos a mano.

Ejecutar desde la raíz del proyecto:  pytest -v
"""
import math

import numpy as np
import pytest

from app.modelo import capacidad_ultima, factores_capacidad
from app.zapata import ZapataRectangular, presiones_contacto


# 1. Literatura: Das, Principios de ing. de cimentaciones, tabla 3.3 (Vesić)
@pytest.mark.parametrize("phi, Nc, Nq, Ng", [
    (0, 5.14, 1.00, 0.00),
    (20, 14.83, 6.40, 5.39),
    (30, 30.14, 18.40, 22.40),
    (35, 46.12, 33.30, 48.03),
])
def test_factores_capacidad_tabla_das(phi, Nc, Nq, Ng):
    calc = factores_capacidad(phi)
    assert calc == pytest.approx((Nc, Nq, Ng), rel=1e-3, abs=1e-2)


def test_factores_capacidad_vectorizado():
    """Un arreglo de ángulos debe dar un arreglo de factores (sin ciclos)."""
    Nc, Nq, Ng = factores_capacidad(np.array([0, 20, 30]))
    assert Nc.shape == (3,)
    assert Nq[2] == pytest.approx(18.40, rel=1e-3)


# 2. Literatura: solución de Prandtl, zapata corrida en arcilla (φ = 0, Df = 0)
def test_prandtl_arcilla_corrida():
    c = 50.0
    q_u = capacidad_ultima(B=1.0, L=1e4, Df=0.0, gamma=18.0, c=c, phi=0.0)
    assert q_u == pytest.approx((math.pi + 2) * c, rel=1e-3)


# 3. Caso resuelto a mano (CASO DE VALIDACIÓN C1)
def test_caso_a_mano_zapata_cuadrada_arena():
    """Zapata cuadrada 2 x 2 m, Df = 1 m, arena c = 0, φ = 30°, γ = 18 kN/m³.

    Nq = 18.40, Nγ = 22.40                       (tabla 3.3 de Das)
    Fqs = 1 + (B/L) tan30° = 1.5774 ; Fγs = 1 − 0.4 = 0.60
    Df/B = 0.5 ≤ 1  ->  Fqd = 1 + 2 tan30° (1 − sen30°)² (0.5) = 1.1443
    q = γ Df = 18 kPa
    q_u = 18(18.40)(1.5774)(1.1443) + ½(18)(2)(22.40)(0.60)
        = 597.9 + 241.9 = 839.8 kPa
    """
    q_u = capacidad_ultima(B=2.0, L=2.0, Df=1.0, gamma=18.0, c=0.0, phi=30.0)
    assert q_u == pytest.approx(839.8, rel=5e-3)


# 4. Presiones de contacto (pysections) contra la fórmula P/A (1 ± 6e/B)
def test_zapata_pysections_area_inercia():
    z = ZapataRectangular(2.0, 3.0)
    assert z.area == pytest.approx(6.0)
    assert z.I_flexion == pytest.approx(3.0 * 2.0 ** 3 / 12)


def test_presiones_excentricidad_pequena():
    P, M, B, L = 1000.0, 100.0, 2.0, 2.0      # e = 0.10 m < B/6
    q_max, q_min = presiones_contacto(P, M, B, L)
    e = M / P
    assert q_max == pytest.approx(P / (B * L) * (1 + 6 * e / B))
    assert q_min == pytest.approx(P / (B * L) * (1 - 6 * e / B))


def test_presiones_excentricidad_grande():
    P, M, B, L = 1000.0, 500.0, 2.0, 2.0      # e = 0.50 m > B/6
    q_max, q_min = presiones_contacto(P, M, B, L)
    assert q_min == 0.0
    assert q_max == pytest.approx(4 * P / (3 * L * (B - 2 * 0.5)))


