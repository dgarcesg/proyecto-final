"""Buscador de medidas publicadas: elige cuáles de las 530 medidas se le muestran a Claude.

Son demasiadas para mandarlas todas en cada consulta (unos 295 000 caracteres). Para cada
requisito se eligen, por parecido de significado (los mismos embeddings del buscador de
normas):
  - las POR_DISTRITO más parecidas de la municipalidad del distrito del emprendedor (las que
    pueden dar rojo), y
  - las DE_OTRAS más parecidas de otras municipalidades (solo precedentes: ámbar).

El rojo lo sigue decidiendo ai/semaforo.py con la tabla completa.

Uso (desde la raíz del repo), para ver qué medidas se elegirían:
    python -m ai.medidas "San Juan de Lurigancho" "solo puedo atender hasta las 11 de la noche"
"""

from __future__ import annotations

import hashlib
import json
import sys
from functools import lru_cache

import numpy as np

from ai.rag import modelo
from ai.schemas import MedidaPublicada
from ai.semaforo import TABLA, cargar_medidas, mismo_distrito

CARPETA_INDICE = TABLA.parent / "indice"
ARCHIVO_IDS = CARPETA_INDICE / "medidas.json"
ARCHIVO_VECTORES = CARPETA_INDICE / "medidas.npy"

POR_DISTRITO = 5
DE_OTRAS = 3


def _texto(m: MedidaPublicada) -> str:
    return f"{m.entidad}. {m.materia}. {m.medida}".replace(". .", ".")


def _huella() -> str:
    return hashlib.sha256(TABLA.read_bytes().replace(b"\r\n", b"\n")).hexdigest()[:16]


def construir_indice(medidas: dict[str, MedidaPublicada]) -> None:
    ids = list(medidas)
    print(f"Calculando {len(ids)} vectores de medidas publicadas...")
    vectores = modelo().encode(
        ["passage: " + _texto(medidas[i]) for i in ids], batch_size=32, normalize_embeddings=True,
    )
    CARPETA_INDICE.mkdir(exist_ok=True)
    np.save(ARCHIVO_VECTORES, vectores.astype(np.float32))
    ARCHIVO_IDS.write_text(json.dumps({"huella": _huella(), "ids": ids}, ensure_ascii=False), encoding="utf-8")


@lru_cache(maxsize=1)
def _indice() -> tuple[dict[str, MedidaPublicada], list[str], np.ndarray]:
    """Carga las medidas y sus vectores; si publicaciones.json cambió, los recalcula."""
    medidas = cargar_medidas()
    vigente = ARCHIVO_IDS.exists() and ARCHIVO_VECTORES.exists() and \
        json.loads(ARCHIVO_IDS.read_text(encoding="utf-8"))["huella"] == _huella()
    if not vigente:
        construir_indice(medidas)
    ids = json.loads(ARCHIVO_IDS.read_text(encoding="utf-8"))["ids"]
    return medidas, ids, np.load(ARCHIVO_VECTORES)


def medidas_relacionadas(requisitos: list[str], distrito: str | None) -> list[MedidaPublicada]:
    """Las medidas que se le muestran a Claude para estos requisitos (sin repetir)."""
    medidas, ids, vectores = _indice()
    if not requisitos or not ids:
        return []
    del_distrito = np.array([
        mismo_distrito(medidas[i].distrito, distrito) and not medidas[i].referencia_fuera_de_lima
        for i in ids
    ])
    consultas = modelo().encode(["query: " + r for r in requisitos], normalize_embeddings=True)
    elegidas: dict[str, MedidaPublicada] = {}
    for similitud in consultas @ vectores.T:  # una fila por requisito
        orden = np.argsort(-similitud)
        propias = [i for i in orden if del_distrito[i]][:POR_DISTRITO]
        otras = [i for i in orden if not del_distrito[i]][:DE_OTRAS]
        for i in propias + otras:
            elegidas.setdefault(ids[i], medidas[ids[i]])
    return list(elegidas.values())


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    for m in medidas_relacionadas(sys.argv[2:], sys.argv[1]):
        print(f"{m.id_medida} | {m.distrito} | {m.medida[:110]}")
