"""Generación de la memoria de cálculo en Word con docxtpl.

Funciona para cualquier cálculo guardado: a partir de las entradas se
recalcula el modelo (es determinista) y se regeneran las gráficas.
"""
import io
import re
from pathlib import Path

from docx.shared import Mm
from docxtpl import DocxTemplate, InlineImage

from app.graficas import figura_a_png, grafica_capacidad, grafica_esfuerzos
from app.modelo import CAMPOS, DatosCimentacion, calcular

RAIZ = Path(__file__).resolve().parent.parent
PLANTILLA = RAIZ / "plantillas" / "memoria.docx"
CARPETA_REPORTES = RAIZ / "reportes"


def _fmt(valor, decimales=2):
    """Número con decimales fijos y separador de miles (formato colombiano)."""
    texto = f"{valor:,.{decimales}f}"
    return texto.replace(",", "X").replace(".", ",").replace("X", ".")


def filas_entradas(datos: DatosCimentacion):
    """Lista de filas para la tabla de entradas ({%tr for %})."""
    valores = datos.como_dict()
    return [
        {"grupo": grupo, "nombre": nombre, "simbolo": simbolo,
         "valor": _fmt(valores[campo], 2), "unidad": unidad}
        for grupo, campos in CAMPOS.items()
        for campo, (nombre, simbolo, unidad) in campos.items()
    ]


def filas_resultados(r):
    """Lista de filas para la tabla de resultados."""
    filas = [
        ("Factor de capacidad", "Nc", r.Nc, "-"),
        ("Factor de capacidad", "Nq", r.Nq, "-"),
        ("Factor de capacidad", "Nγ", r.Ngamma, "-"),
        ("Excentricidad", "e", r.e, "m"),
        ("Ancho efectivo", "B'", r.B_efectivo, "m"),
        ("Capacidad última", "q_u", r.q_ult, "kPa"),
        ("Carga última", "Q_ult", r.Q_ult, "kN"),
        ("Carga admisible", "Q_adm", r.Q_adm, "kN"),
        ("Presión de contacto máxima", "q_max", r.q_max, "kPa"),
        ("Presión de contacto mínima", "q_min", r.q_min, "kPa"),
        ("Presión neta", "q_neta", r.q_neta, "kPa"),
        ("Asentamiento (quad)", "s", r.s_quad, "mm"),
        ("Asentamiento (Simpson, Das)", "s_S", r.s_simpson, "mm"),
    ]
    if r.B_min is not None:
        filas.append(("Ancho mínimo por capacidad (brentq)", "B_min", r.B_min, "m"))
    return [{"nombre": n, "simbolo": s, "valor": _fmt(v), "unidad": u} for n, s, v, u in filas]


def hay_despegue(datos, r):
    """True si e > B/6: la presión mínima es nula y parte de la base se despega.

    No hace que la zapata deje de cumplir (la capacidad ya usa el área efectiva
    de Meyerhof), pero se informa como advertencia. La tolerancia evita que
    e = B/6 exacto se marque por errores de redondeo.
    """
    return r.e - datos.B / 6 > 1e-9


def filas_verificaciones(datos, r):
    """Chequeos de la memoria: cumple / no cumple, y la advertencia de despegue."""
    def estado(ok):
        return "CUMPLE" if ok else "NO CUMPLE"

    return [
        {"nombre": "Factor de seguridad (capacidad portante)", "obtenido": _fmt(r.FS),
         "limite": f"≥ {_fmt(datos.FS_req)}", "estado": estado(r.cumple_capacidad)},
        {"nombre": "Asentamiento total (mm)", "obtenido": _fmt(r.s_quad, 1),
         "limite": f"≤ {_fmt(datos.s_adm, 1)}", "estado": estado(r.cumple_asentamiento)},
        {"nombre": "Excentricidad sin despegue de la base (m)", "obtenido": _fmt(r.e, 3),
         "limite": f"≤ B/6 = {_fmt(datos.B / 6, 3)}",
         "estado": "ADVERTENCIA" if hay_despegue(datos, r) else "CUMPLE"},
    ]


def _motivo(r):
    motivos = []
    if not r.cumple_capacidad:
        motivos.append("el factor de seguridad es menor que el requerido.")
    if not r.cumple_asentamiento:
        motivos.append("el asentamiento supera el admisible.")
    return " Además, ".join(motivos)


def construir_contexto(plantilla, calculo):
    """Diccionario de variables para la plantilla a partir de un cálculo guardado."""
    datos = DatosCimentacion(**calculo["entradas"])
    r = calcular(datos)

    def imagen(fig):
        return InlineImage(plantilla, io.BytesIO(figura_a_png(fig)), width=Mm(150))

    return {
        "proyecto": calculo["proyecto"],
        "ubicacion": calculo.get("ubicacion") or "—",
        "descripcion": calculo["descripcion"],
        "fecha": calculo["fecha"],
        "B": _fmt(datos.B), "L": _fmt(datos.L), "Df": _fmt(datos.Df),
        "phi": _fmt(datos.phi, 1), "FS_req": _fmt(datos.FS_req),
        "Nc": _fmt(r.Nc), "Nq": _fmt(r.Nq), "Ngamma": _fmt(r.Ngamma),
        "entradas": filas_entradas(datos),
        "resultados": filas_resultados(r),
        "verificaciones": filas_verificaciones(datos, r),
        "cumple": r.cumple,
        "motivo": _motivo(r),
        "despegue": hay_despegue(datos, r),
        "e": _fmt(r.e, 3), "B_sexto": _fmt(datos.B / 6, 3),
        "grafica_capacidad": imagen(grafica_capacidad(datos, r.B_min)),
        "grafica_esfuerzos": imagen(grafica_esfuerzos(datos)),
    }


def generar_memoria(calculo, destino=None):
    """Genera el .docx de un cálculo guardado y retorna la ruta del archivo.

    ``calculo`` es el diccionario que devuelve ``db.obtener_calculo``.
    """
    plantilla = DocxTemplate(PLANTILLA)
    plantilla.render(construir_contexto(plantilla, calculo))
    if destino is None:
        CARPETA_REPORTES.mkdir(exist_ok=True)
        nombre = re.sub(r"[^\w\-]+", "_", f"memoria_{calculo['id']}_{calculo['descripcion']}")
        destino = CARPETA_REPORTES / f"{nombre}.docx"
    plantilla.save(destino)
    return Path(destino)
