"""Genera plantillas/memoria.docx, la plantilla Jinja que usa docxtpl.

Solo hace falta correrlo si se quiere regenerar la plantilla desde cero:
    python plantillas/crear_plantilla.py
La plantilla también se puede editar directamente en Word (sin romper las
etiquetas {{ }} y {% %}).
"""
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

# Formato en tonos neutros: para cambiar la letra basta con cambiar FUENTE
# (por ejemplo, "Times New Roman").
FUENTE = "Cambria"
NEGRO = RGBColor(0x00, 0x00, 0x00)
GRIS_OSCURO = RGBColor(0x40, 0x40, 0x40)
GRIS_MEDIO = RGBColor(0x59, 0x59, 0x59)
RELLENO_ENCABEZADO = "D9D9D9"   # gris claro para la fila de títulos de las tablas
RELLENO_ETIQUETA = "F2F2F2"     # gris muy claro para la columna de etiquetas


def fijar_fuente(rpr_padre, nombre):
    """Asigna la letra a un estilo o run, quitando la fuente de tema de Word."""
    rpr = rpr_padre.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.insert(0, rfonts)
    for atributo in ("asciiTheme", "hAnsiTheme", "eastAsiaTheme", "cstheme"):
        rfonts.attrib.pop(qn(f"w:{atributo}"), None)
    for atributo in ("ascii", "hAnsi", "eastAsia", "cs"):
        rfonts.set(qn(f"w:{atributo}"), nombre)


def configurar_estilos(doc):
    """Texto, títulos, encabezado y pie en negro y grises, con la misma letra."""
    formatos = {  # estilo: (tamaño, color, negrita)
        "Normal": (11, NEGRO, False),
        "Title": (20, NEGRO, True),
        "Heading 1": (13, NEGRO, True),
        "Heading 2": (11.5, GRIS_OSCURO, True),
        "Header": (9, GRIS_MEDIO, False),
        "Footer": (9, GRIS_MEDIO, False),
    }
    for nombre, (tamano, color, negrita) in formatos.items():
        estilo = doc.styles[nombre]
        fijar_fuente(estilo.element, FUENTE)
        estilo.font.size = Pt(tamano)
        estilo.font.color.rgb = color
        estilo.font.bold = negrita
    # La línea bajo el título del documento pasa de azul a negro.
    borde = doc.styles["Title"].element.pPr.find(qn("w:pBdr")).find(qn("w:bottom"))
    borde.set(qn("w:color"), "000000")
    borde.attrib.pop(qn("w:themeColor"), None)
    doc.styles["Heading 1"].paragraph_format.space_before = Pt(18)
    doc.styles["Heading 1"].paragraph_format.space_after = Pt(6)
    doc.styles["Heading 2"].paragraph_format.space_after = Pt(4)


def rellenar(celda, color):
    """Fondo de una celda (hexadecimal sin #)."""
    sombra = OxmlElement("w:shd")
    sombra.set(qn("w:val"), "clear")
    sombra.set(qn("w:color"), "auto")
    sombra.set(qn("w:fill"), color)
    celda._tc.get_or_add_tcPr().append(sombra)


def texto_celda(celda, texto, negrita=False):
    celda.text = texto
    run = celda.paragraphs[0].runs[0]
    run.font.size = Pt(10)
    run.bold = negrita


def tabla_con_ciclo(doc, encabezados, variable, campos):
    """Tabla con fila de encabezado y una fila repetida con {%tr for %}."""
    tabla = doc.add_table(rows=4, cols=len(encabezados))
    tabla.style = "Table Grid"
    tabla.alignment = WD_TABLE_ALIGNMENT.CENTER
    for celda, texto in zip(tabla.rows[0].cells, encabezados):
        texto_celda(celda, texto, negrita=True)
        rellenar(celda, RELLENO_ENCABEZADO)
    # El encabezado se repite si la tabla pasa a la página siguiente.
    tabla.rows[0]._tr.get_or_add_trPr().append(OxmlElement("w:tblHeader"))
    tabla.rows[1].cells[0].text = f"{{%tr for f in {variable} %}}"
    for celda, campo in zip(tabla.rows[2].cells, campos):
        texto_celda(celda, f"{{{{ f.{campo} }}}}")
    tabla.rows[3].cells[0].text = "{%tr endfor %}"
    return tabla


def ecuacion(doc, texto):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(texto)
    run.font.name = "Cambria Math"
    run.italic = True


def crear(ruta):
    doc = Document()
    configurar_estilos(doc)
    for seccion in doc.sections:
        seccion.left_margin = seccion.right_margin = Cm(2.5)
        seccion.header.paragraphs[0].text = "Memoria de cálculo · {{ proyecto }}"
        seccion.footer.paragraphs[0].text = (
            "Generado con la aplicación Cimentaciones Superficiales · {{ fecha }}")

    titulo = doc.add_heading("MEMORIA DE CÁLCULO", level=0)
    titulo.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("Capacidad portante y asentamiento de una zapata superficial")
    r.font.size, r.font.color.rgb = Pt(12), GRIS_OSCURO

    info = doc.add_table(rows=4, cols=2)
    info.style = "Table Grid"
    for fila, (k, v) in zip(info.rows, [("Proyecto", "{{ proyecto }}"),
                                        ("Ubicación", "{{ ubicacion }}"),
                                        ("Elemento", "{{ descripcion }}"),
                                        ("Fecha del cálculo", "{{ fecha }}")]):
        texto_celda(fila.cells[0], k, negrita=True)
        rellenar(fila.cells[0], RELLENO_ETIQUETA)
        texto_celda(fila.cells[1], v)

    doc.add_heading("1. Datos de entrada", level=1)
    tabla_con_ciclo(doc, ["Grupo", "Parámetro", "Símbolo", "Valor", "Unidad"],
                    "entradas", ["grupo", "nombre", "simbolo", "valor", "unidad"])

    doc.add_heading("2. Procedimiento", level=1)
    doc.add_heading("2.1 Capacidad portante (ecuación general)", level=2)
    doc.add_paragraph(
        "Se usa la ecuación general de capacidad de carga (Das, cap. 3) con los "
        "factores de Vesić, forma de De Beer, profundidad de Hansen e inclinación "
        "de Meyerhof y Hanna. La excentricidad se trata con el área efectiva de Meyerhof.")
    ecuacion(doc, "q_u = c·Nc·Fcs·Fcd·Fci + q·Nq·Fqs·Fqd·Fqi + ½·γ·B'·Nγ·Fγs·Fγd·Fγi")
    ecuacion(doc, "Nq = tan²(45° + φ/2)·e^(π·tanφ)     Nc = (Nq − 1)·cotφ     Nγ = 2(Nq + 1)·tanφ")
    ecuacion(doc, "e = M / P     B' = B − 2e     Q_ult = q_u·B'·L     FS = Q_ult / P")
    doc.add_paragraph(
        "Con φ = {{ phi }}° se obtiene Nc = {{ Nc }}, Nq = {{ Nq }} y Nγ = {{ Ngamma }}. "
        "El ancho mínimo que cumple FS = {{ FS_req }} se halla resolviendo "
        "Q_ult(B)/P − FS = 0 con el método de Brent (scipy.optimize.brentq).")
    doc.add_paragraph("{{ grafica_capacidad }}").alignment = WD_ALIGN_PARAGRAPH.CENTER
    doc.add_paragraph("Figura 1. Carga admisible en función del ancho de la zapata.").alignment = \
        WD_ALIGN_PARAGRAPH.CENTER

    doc.add_heading("2.2 Asentamiento por consolidación primaria", level=2)
    doc.add_paragraph(
        "El incremento de esfuerzo bajo el centro de la zapata se calcula con la "
        "solución de Boussinesq para un área rectangular (superposición de cuatro "
        "esquinas). El asentamiento de la arcilla normalmente consolidada se integra "
        "numéricamente en todo el espesor del estrato (scipy.integrate.quad) y se "
        "compara con el método de Simpson de Das.")
    ecuacion(doc, "s = ∫ [Cc / (1 + e₀)] · log₁₀[(σ'0(z) + Δσ(z)) / σ'0(z)] dz")
    ecuacion(doc, "q_neta = P/(B·L) − γ·Df     σ'0(z) = γ·(Df + z)")
    doc.add_paragraph("{{ grafica_esfuerzos }}").alignment = WD_ALIGN_PARAGRAPH.CENTER
    doc.add_paragraph("Figura 2. Esfuerzo inicial e incremento de esfuerzo bajo el centro.").alignment = \
        WD_ALIGN_PARAGRAPH.CENTER

    doc.add_heading("3. Resultados", level=1)
    tabla_con_ciclo(doc, ["Resultado", "Símbolo", "Valor", "Unidad"],
                    "resultados", ["nombre", "simbolo", "valor", "unidad"])

    doc.add_heading("4. Verificaciones", level=1)
    tabla_con_ciclo(doc, ["Verificación", "Obtenido", "Límite", "Estado"],
                    "verificaciones", ["nombre", "obtenido", "limite", "estado"])

    doc.add_heading("5. Conclusión", level=1)
    doc.add_paragraph("{%p if cumple %}")
    doc.add_paragraph(
        "La zapata de {{ B }} m × {{ L }} m desplantada a {{ Df }} m CUMPLE las "
        "verificaciones de capacidad portante y asentamiento para las cargas indicadas.")
    doc.add_paragraph("{%p else %}")
    doc.add_paragraph(
        "La zapata de {{ B }} m × {{ L }} m desplantada a {{ Df }} m NO CUMPLE: "
        "{{ motivo }} Se recomienda revisar las dimensiones.")
    doc.add_paragraph("{%p endif %}")
    doc.add_paragraph("{%p if despegue %}")
    doc.add_paragraph(
        "Advertencia: la excentricidad e = {{ e }} m supera B/6 = {{ B_sexto }} m, por lo "
        "que la presión mínima de contacto es nula y parte de la base se despega del suelo. "
        "La capacidad portante ya considera el área efectiva de Meyerhof (B' = B − 2e); "
        "se recomienda aumentar B o reducir el momento para que toda la base trabaje a compresión.")
    doc.add_paragraph("{%p endif %}")

    doc.add_heading("Referencias", level=1)
    for ref in [
        "Das, B. M. (2012). Fundamentos de ingeniería de cimentaciones (7.ª ed.). Cengage Learning.",
        "Vesić, A. S. (1973). Analysis of ultimate loads of shallow foundations. "
        "J. Soil Mech. Found. Div., ASCE, 99(1), 45–73.",
        "AIS (2010). Reglamento Colombiano de Construcción Sismo Resistente NSR-10, Título H.",
    ]:
        doc.add_paragraph(ref, style="List Bullet")

    doc.save(ruta)


if __name__ == "__main__":
    destino = Path(__file__).resolve().parent / "memoria.docx"
    crear(destino)
    print(f"Plantilla creada: {destino}")
