"""Regla del semáforo. Aquí, y no en el LLM, se decide el rojo.

Un requisito es ROJO solo si Claude lo relacionó con una medida publicada y además:
  1. la founder marcó que esa publicación tiene efectos generales (arts. 8 y 9 del
     D.Leg. 1256, revisados caso por caso);
  2. la medida sigue vigente (la founder no la marcó como revocada ni ya modificada);
  3. es de la misma municipalidad (distrito) donde el emprendedor hace su trámite;
  4. ya surte efecto: desde el día siguiente de su publicación en El Peruano (art. 8.3).

Si Claude la relacionó con una medida publicada pero falla 1, 3 o 4, el requisito queda
ÁMBAR: hay un precedente, pero no una inaplicación que se pueda exigir en ventanilla.
"""

from __future__ import annotations

import json
import unicodedata
from datetime import date, timedelta
from pathlib import Path

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


def mismo_distrito(a: str | None, b: str | None) -> bool:
    a, b = _normalizar(a), _normalizar(b)
    return bool(a) and bool(b) and (a == b or a in b or b in a)


def es_rojo(medida: MedidaPublicada, distrito_usuario: str | None, hoy: date) -> bool:
    return (
        medida.efectos_generales
        and medida.estado == "vigente"
        and mismo_distrito(medida.distrito, distrito_usuario)
        and hoy >= surte_efecto_desde(medida)
    )


def decidir(
    ev: EvaluacionLLM,
    distrito_usuario: str | None,
    medidas: dict[str, MedidaPublicada],
    hoy: date | None = None,
) -> Evaluacion:
    """Convierte la evaluación de Claude en la evaluación final que ve el usuario."""
    hoy = hoy or date.today()
    medida = medidas.get(ev.medida_publicada_id or "")  # si Claude inventa un id, no existe

    if medida and es_rojo(medida, distrito_usuario, hoy):
        color = "rojo"
    elif medida:
        color = "ambar"  # hay precedente publicado, pero no una inaplicación exigible aquí
    else:
        color = ev.color_sugerido  # ámbar o verde: el esquema de Claude no permite rojo

    return Evaluacion(
        requisito=ev.requisito,
        color=color,
        norma_citada=ev.norma_citada,
        fragmento_usado=ev.fragmento_usado,
        explicacion_simple=ev.explicacion_simple,
        publicacion=medida,
        surte_efecto_desde=surte_efecto_desde(medida) if medida else None,
    )
