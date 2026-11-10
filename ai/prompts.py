"""Instrucciones (prompts) que recibe Claude. Están aquí, separadas del código, para revisarlas fácil.

Son dos pasos:
  1. EXTRACCION: de la transcripción de la nota de voz saca el distrito, el giro y la lista de
     requisitos que le pidieron al emprendedor.
  2. EVALUACION: para cada requisito, con los artículos que encontró el buscador (RAG) y las
     medidas publicadas que revisó la founder, sugiere ámbar o verde y, si corresponde, a qué
     medida publicada se parece. Claude NO puede poner rojo: eso lo decide ai/semaforo.py.
"""

from __future__ import annotations

from ai.rag import ArticuloRecuperado
from ai.schemas import ExtraccionNota, MedidaPublicada
from scraper.elperuano import DISTRITOS_LIMA

SISTEMA = """Eres el asistente de "TUPA bajo la lupa", que orienta a emprendedores de Lima \
Metropolitana sobre los requisitos que les piden las municipalidades para la licencia de \
funcionamiento. Das orientación, no asesoría legal.

Reglas:
- Usa solo las normas y las medidas publicadas que vienen en el mensaje. No cites artículos \
de memoria ni inventes resoluciones, números o fechas.
- Escribe en español sencillo, para alguien que no es abogado. Frases cortas, sin jerga.
- Si la información no alcanza para concluir algo, dilo."""

EXTRACCION = """Esta es la transcripción de una nota de voz de un emprendedor (los datos \
personales ya fueron reemplazados por etiquetas como [DNI]):

<transcripcion>
{transcripcion}
</transcripcion>

Extrae:
- distrito: el distrito donde está el negocio. Si es un distrito de Lima Metropolitana, \
escríbelo exactamente como en esta lista: {distritos}. Si dice "Cercado" o "Lima Cercado", \
escribe "Cercado de Lima". Si no lo menciona, null.
- giro: el tipo de negocio (por ejemplo, "bodega", "restaurante"). Si no lo menciona, null.
- requisitos: cada cosa que la municipalidad le pide, le cobra o le restringe para la \
licencia o para funcionar (documentos, pagos, certificados, horarios, etc.). Una entrada por \
cada cosa, con las palabras del emprendedor, resumidas. Incluye montos y horarios si los dice. \
No agregues requisitos que no mencionó."""

EVALUACION = """El emprendedor tiene un negocio{giro} en el distrito de {distrito}. Evalúa cada \
requisito que le pidieron.

<normas_base>
Estos artículos aplican a todos los requisitos:
{normas_base}
</normas_base>

<medidas_publicadas>
Barreras burocráticas que INDECOPI declaró y publicó, revisadas por la founder. Son las más \
parecidas a los requisitos, de la municipalidad del emprendedor y de otras:
{medidas}
</medidas_publicadas>

<requisitos>
{requisitos}
</requisitos>

Para cada requisito, en el mismo orden, devuelve:
- requisito: el texto del requisito, igual que arriba.
- medida_publicada_id: el id de la medida publicada que corresponde a este requisito, o null.
  * Medida de la municipalidad del distrito del emprendedor: elígela solo si es la misma \
exigencia (el mismo documento, el mismo cobro o la misma restricción) en el mismo \
procedimiento, la licencia de funcionamiento; o si es una restricción general que se aplica \
a todos los negocios del distrito (por ejemplo, un horario de funcionamiento). Si es de la \
misma municipalidad pero de OTRO procedimiento (por ejemplo, anuncios publicitarios o \
Defensa Civil), no la elijas: la inaplicación se refiere a la disposición de ese otro \
procedimiento.
  * Medida de otra municipalidad: elígela solo si es el mismo tipo de exigencia (por \
ejemplo, el mismo documento), como precedente, aunque sea de otro procedimiento.
  * Si ninguna corresponde, null. No elijas una medida solo porque trata un tema parecido.
- color_sugerido: "ambar" si, según las normas, la municipalidad no podría exigirlo o hay \
dudas serias de que pueda (por ejemplo, porque no está entre los requisitos máximos del \
art. 7 de la Ley Marco o porque es documentación prohibida de solicitar). "verde" si la \
norma permite pedirlo.
- norma_citada: la norma y el artículo exactos, tal como aparecen en el atributo "cita" de los \
artículos de arriba (por ejemplo, "TUO de la Ley 28976, art. 7").
- fragmento_usado: una frase copiada palabra por palabra del artículo citado, la que sustenta \
tu evaluación. No la resumas ni la cambies.
- explicacion_simple: 2 o 3 frases para el emprendedor: qué dice la norma y qué significa para \
él. Si elegiste una medida publicada, menciona qué declaró INDECOPI y en qué resolución; no \
digas si ya es exigible en su distrito, eso lo calcula el sistema."""


def lista_distritos() -> str:
    return ", ".join(sorted(DISTRITOS_LIMA))


def _articulo(a: ArticuloRecuperado) -> str:
    return f'<articulo cita="{a.cita}">\n{a.texto}\n</articulo>'


def _medida(m: MedidaPublicada) -> str:
    extra = ""
    if m.materia:
        extra += f"\nMateria: {m.materia}"
    if m.norma_cuestionada:
        extra += f"\nDonde está: {m.norma_cuestionada[:300]}"
    return (
        f'<medida id="{m.id_medida}" municipalidad="{m.entidad}" distrito="{m.distrito}" '
        f'resolucion="{m.numero_resolucion}" publicada="{m.fecha_publicacion}">\n{m.medida[:1200]}{extra}\n</medida>'
    )


def prompt_extraccion(transcripcion: str) -> str:
    return EXTRACCION.format(transcripcion=transcripcion, distritos=lista_distritos())


def prompt_evaluacion(
    extraccion: ExtraccionNota,
    base: list[ArticuloRecuperado],
    por_requisito: dict[str, list[ArticuloRecuperado]],
    medidas: list[MedidaPublicada],
) -> str:
    requisitos = "\n".join(
        f'<requisito n="{n}">\n<texto>{req}</texto>\n<articulos_encontrados>\n'
        + "\n".join(_articulo(a) for a in articulos)
        + "\n</articulos_encontrados>\n</requisito>"
        for n, (req, articulos) in enumerate(por_requisito.items(), start=1)
    )
    return EVALUACION.format(
        giro=f" ({extraccion.giro})" if extraccion.giro else "",
        distrito=extraccion.distrito or "(no lo dijo)",
        normas_base="\n".join(_articulo(a) for a in base),
        medidas="\n".join(_medida(m) for m in medidas) or "(ninguna)",
        requisitos=requisitos,
    )
