"""Pruebas del CRUD de SQLite usando una base de datos temporal."""
import pytest

from app import db


@pytest.fixture
def con(tmp_path):
    conexion = db.conectar(tmp_path / "prueba.db")
    yield conexion
    conexion.close()


def test_guardar_buscar_reabrir_eliminar(con):
    pid = db.obtener_o_crear_proyecto(con, "Bodega Fontibón", "Bogotá")
    cid = db.guardar_calculo(con, pid, "Zapata Z-1", {"B": 2.0}, {"FS": 3.4}, True)

    assert len(db.buscar_calculos(con, "fontibón")) == 1
    assert len(db.buscar_calculos(con, "no existe")) == 0

    calculo = db.obtener_calculo(con, cid)
    assert calculo["entradas"]["B"] == 2.0
    assert calculo["proyecto"] == "Bodega Fontibón"

    db.eliminar_calculo(con, cid)
    assert db.obtener_calculo(con, cid) is None


def test_proyecto_no_se_duplica_y_borra_en_cascada(con):
    pid1 = db.obtener_o_crear_proyecto(con, "Puente peatonal")
    pid2 = db.obtener_o_crear_proyecto(con, "Puente peatonal")
    assert pid1 == pid2
    db.guardar_calculo(con, pid1, "Estribo", {}, {}, False)
    db.eliminar_proyecto(con, pid1)
    assert db.buscar_calculos(con) == []


def test_busqueda_no_permite_inyeccion(con):
    pid = db.obtener_o_crear_proyecto(con, "Edificio")
    db.guardar_calculo(con, pid, "Z-1", {}, {}, True)
    db.buscar_calculos(con, "'; DROP TABLE calculos; --")
    assert len(db.buscar_calculos(con)) == 1
