"""Prueba de la memoria de cálculo: se genera y contiene tablas, gráficas y conclusión."""
from docx import Document

from app.modelo import DatosCimentacion, calcular
from app.reporte import filas_verificaciones, generar_memoria, hay_despegue


def test_memoria_se_genera_completa(tmp_path):
    calculo = {"id": 1, "proyecto": "Prueba", "ubicacion": "Bogotá",
               "descripcion": "Z-1", "fecha": "2026-11-08 10:00",
               "entradas": DatosCimentacion().como_dict()}
    ruta = generar_memoria(calculo, tmp_path / "memoria.docx")
    doc = Document(ruta)
    texto = "\n".join(p.text for p in doc.paragraphs)
    assert "CUMPLE" in texto and "{{" not in texto and "{%" not in texto
    assert "Advertencia" not in texto               # e < B/6: no hay despegue
    assert len(doc.inline_shapes) == 2              # las dos gráficas
    filas_entradas = len(doc.tables[1].rows)        # encabezado + 15 datos
    assert filas_entradas == 16


def test_despegue_es_advertencia_y_no_contradice_la_conclusion(tmp_path):
    # M = 500 kN·m -> e = 0.42 m > B/6 = 0.37 m, pero FS y asentamiento cumplen
    datos = DatosCimentacion(M=500)
    r = calcular(datos)
    assert r.cumple and hay_despegue(datos, r)
    estados = [f["estado"] for f in filas_verificaciones(datos, r)]
    # FS, asentamiento, presión máxima (532 > 406 kPa) y despegue
    assert estados == ["CUMPLE", "CUMPLE", "ADVERTENCIA", "ADVERTENCIA"]

    calculo = {"id": 2, "proyecto": "Prueba", "ubicacion": "Bogotá",
               "descripcion": "Z-2", "fecha": "2026-11-09 10:00",
               "entradas": datos.como_dict()}
    doc = Document(generar_memoria(calculo, tmp_path / "memoria.docx"))
    texto = "\n".join(p.text for p in doc.paragraphs)
    assert "NO CUMPLE" not in texto and "Advertencia" in texto


def test_e_igual_a_b_sexto_no_es_despegue():
    datos = DatosCimentacion(M=1200 * 2.2 / 6)      # e = B/6 exacto
    assert not hay_despegue(datos, calcular(datos))
