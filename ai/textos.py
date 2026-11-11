"""Textos legales fijos que muestra la app cuando hay una medida publicada (redacción de la founder).

No los escribe Claude: se arman con los datos de la publicación revisada por la founder.
  - ROJO: la medida está inaplicada con efectos generales en el distrito del emprendedor.
  - ÁMBAR con publicación: hay una resolución de INDECOPI, pero no se puede exigir su
    inaplicación en esa ventanilla (otro distrito, otro lugar, sin efectos generales, etc.).
Para cambiar la redacción, edita las plantillas de este archivo.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import date

from ai.schemas import MedidaPublicada

# Texto del art. 8.3 del D.Leg. 1256, copiado de data/normas/DL-1256.html.
FRAGMENTO_ART_8_3 = (
    "La inaplicación con efectos generales opera a partir del día siguiente de publicado el "
    "extracto de la resolución emitida por la Comisión o la Sala, de ser el caso, en el diario "
    "oficial “El Peruano”."
)
CITA_ART_8 = "D.Leg. 1256, art. 8"

ROJO = (
    "INDECOPI declaró esta medida {barrera} con efectos generales para {el_distrito} (Res. "
    "{resolucion}, publicada el {publicada}). Desde el {desde} la municipalidad no puede "
    "exigírtela (art. 8.3 del D.Leg. 1256)."
)
PRECEDENTE = (
    "No es una medida sujeta a inaplicación con efectos generales en {el_distrito}, pero ha sido "
    "declarada {barrera} para {tramite} de la {entidad}{lugar} mediante Res. {resolucion} "
    "(publicada el {publicada})."
)
SIN_EFECTOS_GENERALES = (
    "INDECOPI declaró esta medida {barrera} para {tramite} mediante Res. {resolucion} (publicada el "
    "{publicada}), pero sin efectos generales en {el_distrito}: solo se inaplicó a quien la denunció."
)
NO_VIGENTE = (
    "INDECOPI declaró esta medida {barrera} mediante Res. {resolucion} (publicada el {publicada}), "
    "pero según nuestra revisión {estado}."
)
AUN_NO_SURTE_EFECTO = (
    "INDECOPI declaró esta medida {barrera} con efectos generales para {el_distrito} (Res. "
    "{resolucion}, publicada el {publicada}). Surte efecto desde el {desde} (art. 8.3 del D.Leg. 1256)."
)

# Aviso bajo cada rojo (criterio de la founder, 10/11/2026): la inaplicación con efectos generales
# alcanza a la disposición declarada barrera, no a la misma exigencia reintroducida en otra norma.
AVISO_ROJO = (
    "**Verifica el fundamento antes de presentar el escrito.** La inaplicación con efectos generales "
    "solo alcanza a la disposición que INDECOPI declaró barrera burocrática en la Res. {resolucion}"
    "{disposicion}. Si la municipalidad te exige este requisito con base en esa misma disposición, se "
    "aplica. Si la exigencia fue reintroducida en otra norma posterior (por ejemplo, una nueva "
    "ordenanza), esta resolución ya no la alcanza. Pide a la municipalidad que te indique en qué "
    "norma se basa."
)

# Dónde estaba la exigencia, según el texto de la medida: "... materializada en el artículo 4 de la
# Ordenanza 334-MDSJL". Se prefiere "materializada en": "contenida en" a veces nombra otra norma
# ("la autorización sectorial contenida en el Decreto Supremo 006-2013-PCM, materializada en ...").
_MATERIALIZADA = re.compile(r"\bmaterializad[oa]s? en (.+)$", re.I | re.S)
_CONTENIDA = re.compile(r"\b(?:contenid|consignad)[oa]s? en (.+)$", re.I | re.S)
_INSTRUMENTO = re.compile(r"Ordenanza|Texto Único|TUPA|Decreto|Acuerdo|Resolución|Reglamento", re.I)
_FIN_DE_ORACION = re.compile(r"\.\s+(?=[A-ZÁÉÍÓÚÑ(“\"-])")  # no corta en "numeral 7.2. del" ni "D.S. 046"
_SIN_NOMBRE = re.compile(r"\b(?:citad|mencionad|referid)[oa]s?\b", re.I)  # "la citada ordenanza": ¿cuál?

ESTADOS = {
    "revocada": "esa resolución fue revocada",
    "entidad_ya_modifico": "la municipalidad ya modificó la norma que la contenía",
}


def _fecha(d: date) -> str:
    return d.strftime("%d/%m/%Y")


def _barrera(m: MedidaPublicada) -> str:
    tipo = m.tipo.lower()
    if "ilegal" in tipo and "razonabilidad" in tipo:
        return "barrera burocrática ilegal y carente de razonabilidad"
    if "razonabilidad" in tipo:
        return "barrera burocrática carente de razonabilidad"
    if "ilegal" in tipo:
        return "barrera burocrática ilegal"
    return "barrera burocrática"  # el listado de INDECOPI no indica el tipo


def _normalizar(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto or "")
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return " ".join(texto.lower().replace("“", "").replace("”", "").replace('"', "").split())


def tramite(m: MedidaPublicada, sugerido: str | None) -> str:
    """'el trámite “X”' si Claude copió un nombre que está en la publicación; si no, la materia."""
    fuente = _normalizar(f"{m.medida} {m.norma_cuestionada}")
    limpio = (sugerido or "").strip(" “”\"'.")
    if len(limpio) >= 5 and _normalizar(limpio) in fuente:
        return f"el trámite “{limpio}”"
    if m.materia:
        return f"un trámite en materia de {m.materia.lower()}"
    return "otro trámite"


def el_distrito(distrito_usuario: str | None) -> str:
    """'el distrito de San Juan de Lurigancho' (el distrito de la consulta)."""
    return f"el distrito de {distrito_usuario.strip()}" if (distrito_usuario or "").strip() else "tu distrito"


def _datos(m: MedidaPublicada, desde: date, tramite_sugerido: str | None, distrito_usuario: str | None) -> dict:
    lugar = f" ({m.distrito})" if m.distrito and _normalizar(m.distrito) not in _normalizar(m.entidad) else ""
    return {
        "barrera": _barrera(m), "resolucion": m.numero_resolucion, "publicada": _fecha(m.fecha_publicacion),
        "desde": _fecha(desde), "entidad": m.entidad, "lugar": lugar,
        "tramite": tramite(m, tramite_sugerido), "estado": ESTADOS.get(m.estado, m.estado),
        "el_distrito": el_distrito(distrito_usuario),
    }


def texto_rojo(m: MedidaPublicada, desde: date, distrito_usuario: str | None) -> str:
    return ROJO.format(**_datos(m, desde, None, distrito_usuario))


def disposicion_declarada(m: MedidaPublicada) -> str | None:
    """'el artículo 4 de la Ordenanza 334-MDSJL'; None si la medida no dice dónde estaba."""
    x = _MATERIALIZADA.search(m.medida) or _CONTENIDA.search(m.medida)
    if x is None:
        return None
    texto = " ".join(x.group(1).split())
    texto = _FIN_DE_ORACION.split(texto)[0]  # algunas filas traen pegada la medida siguiente
    texto = re.split(r",? materializad[oa]s? en ", texto)[0]  # filas que repiten la disposición
    texto = texto.split(":")[0]  # "... de la Ordenanza 007-2017-MDMM: exhibiciones, ..."
    texto = re.sub(r",? para los siguientes supuestos$", "", texto.rstrip(" .,;"))
    texto = texto.replace("la presente resolución", "la resolución")
    if not _INSTRUMENTO.search(texto) or _SIN_NOMBRE.search(texto):
        return None  # "el artículo 17 de la citada ordenanza" no dice cuál es
    return texto


def aviso_rojo(m: MedidaPublicada, escapar=lambda t: t) -> str:
    """El aviso del rojo. `escapar` protege el texto de la medida del formato de la app (app.md)."""
    disposicion = disposicion_declarada(m)
    return AVISO_ROJO.format(
        resolucion=m.numero_resolucion, disposicion=f": {escapar(disposicion)}" if disposicion else "",
    )


def texto_ambar(
    m: MedidaPublicada, motivo: str, desde: date, tramite_sugerido: str | None, distrito_usuario: str | None,
) -> str:
    """Texto para una medida publicada que no da rojo, según el motivo (ai/semaforo.py)."""
    plantilla = {
        "otro_distrito": PRECEDENTE,
        "fuera_de_lima": PRECEDENTE,
        "sin_efectos_generales": SIN_EFECTOS_GENERALES,
        "no_vigente": NO_VIGENTE,
        "aun_no_surte_efecto": AUN_NO_SURTE_EFECTO,
    }[motivo]
    return plantilla.format(**_datos(m, desde, tramite_sugerido, distrito_usuario))
