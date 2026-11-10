"""Buscador de normas (RAG): encuentra los artículos que se relacionan con un requisito.

Cómo funciona:
  1. ai/normas.py divide las 4 normas de data/normas/ en fragmentos por artículo.
  2. Cada fragmento se convierte en un vector de 384 números que representa su significado
     (embedding), con el modelo multilingual-e5-small. Corre en la computadora, sin API key.
     Ese modelo pide anteponer "passage: " a los textos y "query: " a las búsquedas.
  3. Los vectores se guardan en data/normas/indice/ para que la app no los recalcule cada
     vez, y al arrancar se cargan en una base ChromaDB en memoria.
  4. Para un requisito ("me piden croquis de ubicación") se calcula su vector y ChromaDB
     devuelve los artículos más parecidos. Esos artículos se le pasan a Claude para que cite
     la norma exacta en vez de recordarla de memoria.

Uso (desde la raíz del repo):
    python -m ai.rag construir                         # recalcula el índice
    python -m ai.rag buscar "me piden croquis de ubicación"

La app usa contexto_legal(requisitos): los artículos base, que siempre van, más los 3
artículos más parecidos a cada requisito.
"""

from __future__ import annotations

import hashlib
import json
import sys
import unicodedata
from dataclasses import dataclass
from functools import lru_cache

import numpy as np

from ai.normas import CARPETA, NORMAS, leer_normas

MODELO = "intfloat/multilingual-e5-small"
CARPETA_INDICE = CARPETA / "indice"
ARCHIVO_FRAGMENTOS = CARPETA_INDICE / "fragmentos.json"
ARCHIVO_VECTORES = CARPETA_INDICE / "vectores.npy"


@dataclass
class ArticuloRecuperado:
    cita: str  # "TUO de la Ley 28976, art. 7"
    texto: str
    similitud: float  # de 0 a 1: qué tan parecido es al requisito


@lru_cache(maxsize=1)
def modelo():
    from sentence_transformers import SentenceTransformer  # tarda; solo se carga si se usa

    return SentenceTransformer(MODELO, device="cpu")


def _huella_normas() -> str:
    """Si cambia algún HTML de data/normas/ o el código que los divide, cambia la huella."""
    h = hashlib.sha256()
    archivos = [CARPETA / n.archivo for n in NORMAS] + [CARPETA.parent.parent / "ai" / "normas.py"]
    for archivo in archivos:
        # sin distinguir los saltos de línea de Windows y de Linux (el servidor usa Linux)
        h.update(archivo.read_bytes().replace(b"\r\n", b"\n"))
    return h.hexdigest()[:16]


def construir_indice() -> None:
    fragmentos = leer_normas()
    textos = [f.texto for f in fragmentos]
    print(f"Calculando {len(textos)} vectores con {MODELO} (tarda uno o dos minutos)...")
    vectores = modelo().encode(
        ["passage: " + t for t in textos], batch_size=16, normalize_embeddings=True,
        show_progress_bar=True,
    )
    CARPETA_INDICE.mkdir(exist_ok=True)
    np.save(ARCHIVO_VECTORES, vectores.astype(np.float32))
    ARCHIVO_FRAGMENTOS.write_text(json.dumps({
        "modelo": MODELO,
        "huella_normas": _huella_normas(),
        "fragmentos": [
            {"cita": f.cita, "norma": f.norma, "articulo": f.articulo, "parte": f.parte, "texto": f.texto}
            for f in fragmentos
        ],
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Índice guardado en {CARPETA_INDICE}.")


def _cargar_indice() -> tuple[list[dict], np.ndarray]:
    """Lee el índice guardado; si falta o las normas cambiaron, lo vuelve a construir."""
    vigente = False
    if ARCHIVO_FRAGMENTOS.exists() and ARCHIVO_VECTORES.exists():
        datos = json.loads(ARCHIVO_FRAGMENTOS.read_text(encoding="utf-8"))
        vigente = datos["modelo"] == MODELO and datos["huella_normas"] == _huella_normas()
    if not vigente:
        construir_indice()
        datos = json.loads(ARCHIVO_FRAGMENTOS.read_text(encoding="utf-8"))
    vectores = np.load(ARCHIVO_VECTORES)
    if len(vectores) != len(datos["fragmentos"]):
        raise RuntimeError("El índice está incompleto: corre  python -m ai.rag construir")
    return datos["fragmentos"], vectores


@lru_cache(maxsize=1)
def _indice() -> tuple[list[dict], np.ndarray]:
    return _cargar_indice()


@lru_cache(maxsize=1)
def coleccion():
    """Base ChromaDB en memoria con todos los artículos (se arma una sola vez)."""
    import chromadb

    fragmentos, vectores = _indice()
    cliente = chromadb.EphemeralClient(settings=chromadb.Settings(anonymized_telemetry=False))
    col = cliente.get_or_create_collection(
        "normas", embedding_function=None, configuration={"hnsw": {"space": "cosine"}},
    )
    lote = 200
    for i in range(0, len(fragmentos), lote):
        parte = fragmentos[i:i + lote]
        col.add(
            ids=[str(n) for n in range(i, i + len(parte))],
            embeddings=vectores[i:i + lote],
            documents=[f["texto"] for f in parte],  # texto limpio, sin el prefijo "passage: "
            metadatas=[{"cita": f["cita"], "norma": f["norma"], "articulo": f["articulo"], "parte": f["parte"]} for f in parte],
        )
    return col


# El emprendedor dice el requisito con sus palabras; esta frase ayuda a ubicarlo en la ley.
PLANTILLA_CONSULTA = "requisito para la licencia de funcionamiento: {}"

# Siempre se le pasan a Claude: los requisitos máximos de la licencia (art. 7 de la Ley
# Marco, en el TUO y con su modificación posterior) y la documentación prohibida de
# solicitar (art. 40 del TUO de la Ley 27444 y art. 5 del D.Leg. 1246, que prohíbe, entre
# otros, pedir copia del DNI o de la ficha RUC).
ARTICULOS_BASE = [
    "TUO de la Ley 28976, art. 7",
    "Ley 28976 (modificada por D.Leg. 1657), art. 7",
    "TUO de la Ley 27444, art. 40",
    "D.Leg. 1246, art. 5",
]


def _unir_partes(textos: list[str]) -> str:
    """Une las partes de un artículo largo sin repetir el encabezado."""
    primera, *resto = textos
    return "\n".join([primera, *("\n".join(t.splitlines()[1:]) for t in resto)])


def articulo_completo(cita: str) -> ArticuloRecuperado:
    fragmentos, _ = _indice()
    textos = [f["texto"] for f in fragmentos if f["cita"] == cita]
    if not textos:
        raise KeyError(f"No hay un artículo con la cita {cita!r}")
    return ArticuloRecuperado(cita=cita, texto=_unir_partes(textos), similitud=1.0)


def articulos_base() -> list[ArticuloRecuperado]:
    return [articulo_completo(c) for c in ARTICULOS_BASE]


def buscar(requisito: str, k: int = 3) -> list[ArticuloRecuperado]:
    """Los k artículos más parecidos al requisito, del más al menos parecido.

    Si un artículo largo está partido, junta las partes que salieron en la búsqueda.
    """
    consulta = "query: " + PLANTILLA_CONSULTA.format(requisito)
    vector = modelo().encode([consulta], normalize_embeddings=True)
    r = coleccion().query(query_embeddings=vector, n_results=k * 3, include=["documents", "metadatas", "distances"])
    por_cita: dict[str, list[tuple[str, str, float]]] = {}
    for texto, meta, distancia in zip(r["documents"][0], r["metadatas"][0], r["distances"][0]):
        por_cita.setdefault(meta["cita"], []).append((meta.get("parte", ""), texto, 1 - distancia))
    resultado = []
    for cita, partes in list(por_cita.items())[:k]:  # el orden es el de la mejor parte
        partes.sort()  # "1/2" antes que "2/2"
        resultado.append(ArticuloRecuperado(
            cita=cita, texto=_unir_partes([t for _, t, _ in partes]),
            similitud=round(max(s for _, _, s in partes), 3),
        ))
    return resultado


# Para bodegas, además: el régimen de licencia provisional de la Ley 30877, modificada por la Ley 31866.
ARTICULOS_BODEGA = ["Ley 31866, art. único"]
# Giros que cuentan como bodega (criterio de la founder, 10/11/2026)
GIROS_BODEGA = ("bodega", "abarrotes", "minimarket", "mini market", "mini-market")


def es_bodega(giro: str | None) -> bool:
    """'Tienda de abarrotes', 'Minimárket' o 'bodega' -> True (sin importar tildes ni mayúsculas)."""
    sin_tildes = unicodedata.normalize("NFKD", giro or "").encode("ascii", "ignore").decode().lower()
    return any(palabra in sin_tildes for palabra in GIROS_BODEGA)


def contexto_legal(
    requisitos: list[str], giro: str | None = None, k: int = 3,
) -> tuple[list[ArticuloRecuperado], dict[str, list[ArticuloRecuperado]]]:
    """Lo que recibe Claude: (artículos base, {requisito: artículos encontrados})."""
    base = articulos_base()
    if es_bodega(giro):
        base += [articulo_completo(c) for c in ARTICULOS_BODEGA]
    citas_base = {a.cita for a in base}
    por_requisito = {
        req: [a for a in buscar(req, k + len(citas_base)) if a.cita not in citas_base][:k]
        for req in requisitos
    }
    return base, por_requisito


if __name__ == "__main__":
    if sys.argv[1:2] == ["construir"]:
        construir_indice()
    elif sys.argv[1:2] == ["buscar"] and len(sys.argv) > 2:
        for a in buscar(" ".join(sys.argv[2:])):
            print(f"[{a.similitud:.3f}] {a.cita}\n    {a.texto[:200]}...\n")
    else:
        print(__doc__)
