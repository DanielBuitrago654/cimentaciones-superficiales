"""Comparación de varios cálculos guardados (Historial -> Comparar).

Igual que la memoria, cada cálculo se recalcula a partir de sus entradas: el
modelo es determinista y así la comparación siempre usa el modelo vigente.
No importa Flet, de modo que se puede probar sin abrir la ventana.
"""
from app.modelo import DatosCimentacion, calcular


def fila_comparacion(calculo):
    """Dimensiones, resultados y límites de un cálculo guardado, en un diccionario."""
    d = DatosCimentacion(**calculo["entradas"])
    r = calcular(d)
    return {
        "id": calculo["id"],
        "etiqueta": f"#{calculo['id']}",
        "descripcion": calculo["descripcion"],
        "B": d.B, "L": d.L, "Df": d.Df, "P": d.P, "M": d.M,
        "FS": r.FS, "FS_req": d.FS_req,
        "s": r.s_quad, "s_adm": d.s_adm,
        "cumple_capacidad": r.cumple_capacidad,
        "cumple_asentamiento": r.cumple_asentamiento,
        "cumple": r.cumple,
    }


def filas_comparacion(calculos):
    """Una fila por cálculo, en el mismo orden en que se reciben."""
    return [fila_comparacion(c) for c in calculos]
