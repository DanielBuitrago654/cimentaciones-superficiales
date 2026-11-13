"""Pruebas de la comparación de cálculos (Historial -> Comparar), sin abrir la ventana."""
from app.comparacion import filas_comparacion
from app.graficas import grafica_comparacion
from app.modelo import DatosCimentacion


def _calculo(calculo_id, **cambios):
    """Cálculo guardado de mentira, con la misma forma que devuelve db.obtener_calculo."""
    return {"id": calculo_id, "descripcion": f"Z-{calculo_id}",
            "entradas": DatosCimentacion(**cambios).como_dict()}


def test_filas_comparacion_recalcula_y_conserva_el_orden():
    filas = filas_comparacion([_calculo(1), _calculo(2, B=1.6, L=1.6)])
    assert [f["etiqueta"] for f in filas] == ["#1", "#2"]
    # Mismos valores de la demo de la guía: 2.2 m cumple y 1.6 m no cumple
    assert abs(filas[0]["FS"] - 5.06) < 0.01 and filas[0]["cumple"]
    assert abs(filas[1]["FS"] - 2.59) < 0.01 and not filas[1]["cumple_capacidad"]
    assert filas[1]["B"] == 1.6 and filas[1]["FS_req"] == 3.0


def test_grafica_comparacion_tiene_dos_paneles_con_una_barra_por_calculo():
    filas = filas_comparacion([_calculo(1), _calculo(2, B=1.6, L=1.6), _calculo(3, Df=2.0)])
    fig = grafica_comparacion(filas)
    assert len(fig.axes) == 2
    for ax in fig.axes:
        assert len(ax.patches) == 3                       # una barra por cálculo
        assert ax.get_xlabel() and ax.get_ylabel() and ax.get_title(loc="left")
