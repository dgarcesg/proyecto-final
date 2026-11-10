"""Textos legales fijos que muestra la app cuando hay una medida publicada (redacción de la founder).

No los escribe Claude: se arman con los datos de la publicación revisada por la founder.
  - ROJO: la medida está inaplicada con efectos generales en el distrito del emprendedor.
  - ÁMBAR con publicación: hay una resolución de INDECOPI, pero no se puede exigir su
    inaplicación en esa ventanilla (otro distrito, otro lugar, sin efectos generales, etc.).
Para cambiar la redacción, edita las plantillas de este archivo.
"""

from __future__ import annotations

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
    "INDECOPI declaró esta medida {barrera} con efectos generales (Res. {resolucion}, publicada "
    "el {publicada}). Desde el {desde} la municipalidad no puede exigírtela (art. 8.3 del D.Leg. 1256)."
)
PRECEDENTE = (
    "No es una medida sujeta a inaplicación con efectos generales en tu distrito, pero ha sido "
    "declarada {barrera} para {tramite} de la {entidad}{lugar} mediante Res. {resolucion} "
    "(publicada el {publicada})."
)
SIN_EFECTOS_GENERALES = (
    "INDECOPI declaró esta medida {barrera} para {tramite} mediante Res. {resolucion} (publicada el "
    "{publicada}), pero sin efectos generales: solo se inaplicó a quien la denunció."
)
NO_VIGENTE = (
    "INDECOPI declaró esta medida {barrera} mediante Res. {resolucion} (publicada el {publicada}), "
    "pero según nuestra revisión {estado}."
)
AUN_NO_SURTE_EFECTO = (
    "INDECOPI declaró esta medida {barrera} con efectos generales (Res. {resolucion}, publicada el "
    "{publicada}). Surte efecto desde el {desde} (art. 8.3 del D.Leg. 1256)."
)

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


def _datos(m: MedidaPublicada, desde: date, tramite_sugerido: str | None) -> dict:
    lugar = f" ({m.distrito})" if m.distrito and _normalizar(m.distrito) not in _normalizar(m.entidad) else ""
    return {
        "barrera": _barrera(m), "resolucion": m.numero_resolucion, "publicada": _fecha(m.fecha_publicacion),
        "desde": _fecha(desde), "entidad": m.entidad, "lugar": lugar,
        "tramite": tramite(m, tramite_sugerido), "estado": ESTADOS.get(m.estado, m.estado),
    }


def texto_rojo(m: MedidaPublicada, desde: date) -> str:
    return ROJO.format(**_datos(m, desde, None))


def texto_ambar(m: MedidaPublicada, motivo: str, desde: date, tramite_sugerido: str | None) -> str:
    """Texto para una medida publicada que no da rojo, según el motivo (ai/semaforo.py)."""
    plantilla = {
        "otro_distrito": PRECEDENTE,
        "fuera_de_lima": PRECEDENTE,
        "sin_efectos_generales": SIN_EFECTOS_GENERALES,
        "no_vigente": NO_VIGENTE,
        "aun_no_surte_efecto": AUN_NO_SURTE_EFECTO,
    }[motivo]
    return plantilla.format(**_datos(m, desde, tramite_sugerido))
