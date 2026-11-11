"""El escrito en PDF que el emprendedor presenta a la municipalidad (solo para el semáforo rojo).

Pide que no se le exija la medida que INDECOPI declaró barrera burocrática con efectos generales
para su distrito, citando la resolución publicada en El Peruano, el art. 8.3 del D.Leg. 1256 y, sobre
la multa al funcionario que no cumpla el mandato de inaplicación, el numeral 34.1 del mismo decreto.

No lo escribe Claude: se arma con las plantillas de abajo (redacción de la founder, 10/11/2026)
y con los datos de la publicación revisada. No pide datos personales: deja espacios en blanco
para que la persona escriba a mano su nombre, DNI y domicilio.

Para cambiar la redacción, edita las plantillas de este archivo.
"""

from __future__ import annotations

from datetime import date

from fpdf import FPDF

from ai import citas, textos
from ai.fechas import hoy_en_lima
from ai.schemas import Evaluacion, ExtraccionNota, MedidaPublicada

# --- Plantillas (redacción del escrito) ----------------------------------------------------

SUMILLA = {
    False: "Solicito que no se me exija medida declarada barrera burocrática con efectos generales",
    True: "Solicito que no se me exijan medidas declaradas barreras burocráticas con efectos generales",
}
DESTINATARIO = "SEÑOR(A) ________________________________ DE LA {entidad}:"  # cargo, a mano
IDENTIFICACION = (
    "_________________________________________________, identificado(a) con Documento Nacional de "
    "Identidad N° __________________, con domicilio en "
    "______________________________________________________________, en el trámite de licencia "
    "de funcionamiento {del_negocio}, ante usted me presento y digo:"
)
PETITORIO = {
    False: "Solicito que, en el trámite de mi licencia de funcionamiento, no se me exija la siguiente "
           "medida, por haber sido declarada barrera burocrática con efectos generales por el Indecopi:",
    True: "Solicito que, en el trámite de mi licencia de funcionamiento, no se me exijan las siguientes "
          "medidas, por haber sido declaradas barreras burocráticas con efectos generales por el Indecopi:",
}
ITEM_PETITORIO = "{medida} (Resolución {resolucion})."
MARCO_LEGAL = (
    "El numeral 8.3 del artículo 8 del Decreto Legislativo 1256, Aprueba la Ley de Prevención y "
    "Eliminación de Barreras Burocráticas, establece lo siguiente:"
)
RESOLUCION = (
    "Mediante Resolución {resolucion}, publicada en el diario oficial El Peruano el {publicada}, "
    "{organo} declaró {barrera} la siguiente medida de la {entidad}: «{medida}», y dispuso su "
    "inaplicación con efectos generales."
)
CONSECUENCIA = (
    "En consecuencia, desde el {desde}, día siguiente de dicha publicación, la referida medida no "
    "me puede ser exigida en el presente trámite."
)
SANCION = (
    "Finalmente, cabe recordar que el incumplimiento del mandato de inaplicación es sancionable con "
    "multas de hasta veinte (20) Unidades Impositivas Tributarias, conforme al numeral 34.1 del "
    "artículo 34 del Decreto Legislativo 1256, que establece lo siguiente:"
)
CITA_ART_34 = "D.Leg. 1256, art. 34"
FRAGMENTO_ART_34_1 = (  # copiado de data/normas/DL-1256.html
    "Cuando incumpla el mandato de inaplicación de la barrera burocrática declarada ilegal al que se "
    "hace referencia en el artículo 8 de la presente ley."
)
ANEXO = "Copia de la publicación de la Resolución {resolucion} en el diario oficial El Peruano{enlace}."
POR_TANTO = "A usted, solicito acceder a lo solicitado por encontrarse arreglado a ley."
LUGAR_FECHA = "Lima, {fecha}"

ORGANOS = {
    "CEB": "la Comisión de Eliminación de Barreras Burocráticas del Indecopi",
    "SEL": "la Sala Especializada en Eliminación de Barreras Burocráticas del Tribunal del Indecopi",
    "SDC": "la Sala de Defensa de la Competencia del Tribunal del Indecopi",
}
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "setiembre",
         "octubre", "noviembre", "diciembre"]


def fecha_larga(d: date) -> str:
    """date(2026, 10, 25) -> '25 de octubre de 2026'."""
    return f"{d.day} de {MESES[d.month - 1]} de {d.year}"


# --- PDF ----------------------------------------------------------------------------------

def _latin1(texto: str) -> str:
    """La letra Times del PDF solo tiene caracteres latinos: cambia comillas tipográficas y guiones."""
    for original, cambio in {"“": '"', "”": '"', "‘": "'", "’": "'", "–": "-", "—": "-", "…": "...",
                             " ": " "}.items():
        texto = texto.replace(original, cambio)
    return texto.encode("latin-1", "replace").decode("latin-1")


class _Escritor:
    def __init__(self) -> None:
        self.pdf = FPDF(format="A4")
        self.pdf.set_margins(25, 22, 25)
        self.pdf.set_auto_page_break(True, margin=25)
        self.pdf.add_page()

    def parrafo(self, texto: str, estilo: str = "", tam: int = 12, sangria: float = 0, alto: float = 6,
                alinear: str = "J", espacio: float = 3) -> None:
        self.pdf.set_font("Times", estilo, tam)
        self.pdf.set_x(self.pdf.l_margin + sangria)
        self.pdf.multi_cell(self.pdf.epw - sangria, alto, _latin1(texto), align=alinear,
                            new_x="LMARGIN", new_y="NEXT")
        self.pdf.ln(espacio)

    def titulo(self, texto: str) -> None:
        self.parrafo(texto, estilo="B", alinear="L", espacio=2)

    def numerado(self, numero: str, texto: str, sangria: float = 0) -> None:
        """'1.' a la izquierda y el texto justificado a su derecha."""
        self.pdf.set_font("Times", "", 12)
        y = self.pdf.get_y()
        self.pdf.set_xy(self.pdf.l_margin + sangria, y)
        self.pdf.cell(8, 6, numero)
        self.pdf.set_xy(self.pdf.l_margin + sangria + 8, y)
        self.pdf.multi_cell(self.pdf.epw - sangria - 8, 6, _latin1(texto), align="J",
                            new_x="LMARGIN", new_y="NEXT")
        self.pdf.ln(3)

    def cita(self, norma: str, fragmento: str) -> None:
        """La norma con su nombre completo, el encabezado del artículo y el texto, con sangría."""
        x = citas.extracto(norma, fragmento)
        if x is None:
            return
        self.parrafo(x.norma, estilo="B", tam=11, sangria=16, alto=5, espacio=1)
        self.parrafo(x.encabezado, estilo="I", tam=11, sangria=16, alto=5, espacio=1)
        if x.texto:
            self.parrafo(f"«{x.texto}»", tam=11, sangria=16, alto=5)

    def bytes(self) -> bytes:
        return bytes(self.pdf.output())


def rojas(evaluaciones: list[Evaluacion]) -> list[Evaluacion]:
    """Las evaluaciones en rojo, una por medida (si dos requisitos son la misma medida, va una vez)."""
    vistas, unicas = set(), []
    for e in evaluaciones:
        if e.color == "rojo" and e.publicacion and e.publicacion.id_medida not in vistas:
            vistas.add(e.publicacion.id_medida)
            unicas.append(e)
    return unicas


def generar_pdf(evaluaciones: list[Evaluacion], extraccion: ExtraccionNota, hoy: date | None = None) -> bytes:
    """El escrito para todas las medidas en rojo de la consulta. Error si no hay ninguna."""
    en_rojo = rojas(evaluaciones)
    if not en_rojo:
        raise ValueError("El escrito solo se genera para requisitos en rojo")
    hoy = hoy or hoy_en_lima()
    varias = len(en_rojo) > 1
    medidas: list[MedidaPublicada] = [e.publicacion for e in en_rojo]
    e_ = _Escritor()

    # Sumilla (arriba a la derecha) y destinatario
    ancho = e_.pdf.epw * 0.55
    e_.pdf.set_font("Times", "B", 12)
    e_.pdf.set_x(e_.pdf.l_margin + e_.pdf.epw - ancho)
    e_.pdf.multi_cell(ancho, 6, _latin1(f"SUMILLA: {SUMILLA[varias]}"), align="L",
                      new_x="LMARGIN", new_y="NEXT")
    e_.pdf.ln(8)
    e_.titulo(DESTINATARIO.format(entidad=medidas[0].entidad.upper()))
    e_.pdf.ln(2)

    giro = (extraccion.giro or "").strip()
    e_.parrafo(IDENTIFICACION.format(del_negocio=f"de mi {giro}" if giro else "de mi establecimiento"),
               alinear="L", alto=8)  # sin justificar: las líneas para escribir a mano no se estiran

    e_.titulo("I. PETITORIO")
    e_.parrafo(PETITORIO[varias])
    for n, m in enumerate(medidas, start=1):
        e_.numerado(f"{n}.", ITEM_PETITORIO.format(medida=m.medida.rstrip(". "), resolucion=m.numero_resolucion),
                    sangria=6)

    e_.titulo("II. FUNDAMENTOS")
    numero = 1
    e_.numerado(f"{numero}.", MARCO_LEGAL)
    e_.cita(textos.CITA_ART_8, textos.FRAGMENTO_ART_8_3)
    for ev in en_rojo:
        m = ev.publicacion
        numero += 1
        e_.numerado(f"{numero}.", RESOLUCION.format(
            resolucion=m.numero_resolucion, publicada=fecha_larga(m.fecha_publicacion),
            organo=ORGANOS.get(m.organo, "el Indecopi"), barrera=textos._barrera(m), entidad=m.entidad,
            medida=m.medida.rstrip(". "),
        ))
        numero += 1
        e_.numerado(f"{numero}.", CONSECUENCIA.format(desde=fecha_larga(ev.surte_efecto_desde)))
    # el fundamento principal es la inaplicación con efectos generales: no se citan otras normas
    numero += 1
    e_.numerado(f"{numero}.", SANCION)
    e_.cita(CITA_ART_34, FRAGMENTO_ART_34_1)

    e_.titulo("III. ANEXOS")
    for letra, m in zip("ABCDEFGHIJ", medidas):
        enlace = f" ({m.url_el_peruano})" if m.url_el_peruano.startswith("http") else ""
        e_.numerado(f"1-{letra}", ANEXO.format(resolucion=m.numero_resolucion, enlace=enlace))

    e_.titulo("POR TANTO:")
    e_.parrafo(POR_TANTO)
    e_.parrafo(LUGAR_FECHA.format(fecha=fecha_larga(hoy)), alinear="R", espacio=22)
    e_.parrafo("________________________________\nFirma\nNombre:\nDNI:", alinear="L", espacio=0)
    return e_.bytes()
