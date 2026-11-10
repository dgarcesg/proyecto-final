"""Regla del semáforo. Aquí, y no en el LLM, se decide el rojo.

Un requisito es ROJO solo si Claude lo relacionó con una medida publicada y además:
  1. la founder marcó que esa publicación tiene efectos generales (arts. 8 y 9 del
     D.Leg. 1256, revisados caso por caso);
  2. la medida sigue vigente (la founder no la marcó como revocada ni ya modificada);
  3. es de una municipalidad de Lima Metropolitana (no una referencia de otro lugar) y
     del mismo distrito donde el emprendedor hace su trámite;
  4. ya surte efecto: desde el día siguiente de su publicación en El Peruano (art. 8.3).

Si Claude la relacionó con una medida publicada pero falla alguna de esas condiciones, el
requisito queda ÁMBAR: hay un precedente, pero no una inaplicación que se pueda exigir en
esa ventanilla.

En ambos casos, el texto sobre la publicación no lo escribe Claude: es una plantilla fija de
la founder (ai/textos.py). En rojo, además, la norma citada pasa a ser el art. 8.3 del D.Leg. 1256.
"""

from __future__ import annotations

import json
import unicodedata
from datetime import date, timedelta
from pathlib import Path

from ai import textos
from ai.schemas import Evaluacion, EvaluacionLLM, MedidaPublicada

TABLA = Path(__file__).resolve().parent.parent / "data" / "publicaciones" / "publicaciones.json"


def _normalizar(texto: str | None) -> str:
    texto = unicodedata.normalize("NFKD", texto or "")
    return " ".join("".join(c for c in texto if not unicodedata.combining(c)).lower().split())


def cargar_medidas(ruta: Path = TABLA) -> dict[str, MedidaPublicada]:
    """Lee la tabla revisada por la founder: {id_medida: MedidaPublicada}."""
    if not ruta.exists():
        return {}
    filas = json.loads(ruta.read_text(encoding="utf-8"))
    medidas = [MedidaPublicada(**f) for f in filas]
    return {m.id_medida: m for m in medidas}


def surte_efecto_desde(medida: MedidaPublicada) -> date:
    """Art. 8.3: opera a partir del día siguiente de la publicación en El Peruano."""
    return medida.fecha_publicacion + timedelta(days=1)


# Formas de nombrar al Cercado / Municipalidad Metropolitana de Lima.
_ALIAS_LIMA = {"lima (metropolitana)", "cercado de lima", "lima cercado", "cercado", "lima"}


def _distrito_canonico(nombre: str | None) -> str:
    n = _normalizar(nombre)
    n = n.removeprefix("distrito de ").removeprefix("municipalidad distrital de ")
    return "lima" if n in _ALIAS_LIMA else n


def mismo_distrito(a: str | None, b: str | None) -> bool:
    """Comparación exacta (sin tildes ni mayúsculas): 'Santa' NO es 'Santa Anita'."""
    a, b = _distrito_canonico(a), _distrito_canonico(b)
    return bool(a) and a == b


def motivo_no_rojo(medida: MedidaPublicada, distrito_usuario: str | None, hoy: date) -> str | None:
    """Por qué una medida publicada NO da rojo; None si da rojo."""
    if medida.referencia_fuera_de_lima:
        return "fuera_de_lima"
    if not mismo_distrito(medida.distrito, distrito_usuario):
        return "otro_distrito"
    if not medida.efectos_generales:
        return "sin_efectos_generales"
    if medida.estado != "vigente":
        return "no_vigente"
    if hoy < surte_efecto_desde(medida):
        return "aun_no_surte_efecto"
    return None


def es_rojo(medida: MedidaPublicada, distrito_usuario: str | None, hoy: date) -> bool:
    return motivo_no_rojo(medida, distrito_usuario, hoy) is None


def decidir(
    ev: EvaluacionLLM,
    distrito_usuario: str | None,
    medidas: dict[str, MedidaPublicada],
    hoy: date | None = None,
) -> Evaluacion:
    """Convierte la evaluación de Claude en la evaluación final que ve el usuario."""
    hoy = hoy or date.today()
    medida = medidas.get(ev.medida_publicada_id or "")  # si Claude inventa un id, no existe
    norma, fragmento, texto = ev.norma_citada, ev.fragmento_usado, ""

    if medida:
        desde = surte_efecto_desde(medida)
        motivo = motivo_no_rojo(medida, distrito_usuario, hoy)
        if motivo is None:
            color = "rojo"
            texto = textos.texto_rojo(medida, desde, distrito_usuario)  # texto fijo de la founder
            norma, fragmento = textos.CITA_ART_8, textos.FRAGMENTO_ART_8_3
        else:
            color = "ambar"  # hay precedente publicado, pero no una inaplicación exigible aquí
            texto = textos.texto_ambar(medida, motivo, desde, ev.tramite_medida, distrito_usuario)
    else:
        color = ev.color_sugerido  # ámbar o verde: el esquema de Claude no permite rojo

    return Evaluacion(
        requisito=ev.requisito,
        color=color,
        norma_citada=norma,
        fragmento_usado=fragmento,
        explicacion_simple=ev.explicacion_simple,
        publicacion=medida,
        surte_efecto_desde=surte_efecto_desde(medida) if medida else None,
        texto_publicacion=texto,
    )
