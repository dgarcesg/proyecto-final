"""El CSV de revisión de la founder: columnas, lectura, escritura y conservación.

Lo usan el scraper de El Peruano y el cargador del listado de INDECOPI. Regla de oro: si
se vuelven a correr, NO se pierde lo que la founder ya marcó (efectos_generales,
usar_en_app, estado, notas, distrito corregido).
"""

from __future__ import annotations

import csv
from pathlib import Path

CARPETA = Path(__file__).resolve().parent.parent / "data" / "publicaciones"
RUTA_REVISION = CARPETA / "publicaciones_para_revisar.csv"

COLUMNAS = [
    "id_medida", "fuente", "id", "numero_resolucion", "organo", "fecha_publicacion",
    "entidad", "distrito_lima", "materia", "tipo", "tipo_acto_pista", "procedimiento_pista",
    "efectos_generales_sugerido", "menciona_licencia", "n_medida", "medida",
    "norma_cuestionada", "url_el_peruano",
    # --- columnas que llena la founder ---
    "efectos_generales", "usar_en_app", "estado", "notas",
]
COLUMNAS_FOUNDER = ["distrito_lima", "efectos_generales", "usar_en_app", "estado", "notas"]


def leer_csv(ruta: Path = RUTA_REVISION) -> list[dict]:
    """Lee el CSV aunque Excel lo haya guardado con ';' en vez de ','."""
    if not ruta.exists():
        return []
    texto = ruta.read_text(encoding="utf-8-sig")
    lineas = texto.splitlines()
    if not lineas:
        return []
    separador = ";" if lineas[0].count(";") > lineas[0].count(",") else ","
    return list(csv.DictReader(lineas, delimiter=separador))


def guardar_csv(filas: list[dict], ruta: Path = RUTA_REVISION) -> None:
    """Escribe el CSV en utf-8-sig para que Excel muestre bien las tildes."""
    extras = [k for f in filas for k in f if k not in COLUMNAS]
    columnas = COLUMNAS + list(dict.fromkeys(extras))
    try:
        with ruta.open("w", encoding="utf-8-sig", newline="") as f:
            escritor = csv.DictWriter(f, fieldnames=columnas, restval="")
            escritor.writeheader()
            escritor.writerows(filas)
    except PermissionError:
        raise SystemExit(f"No se pudo escribir {ruta.name}: ciérralo en Excel y vuelve a correr.")


def aplicar_criterios_founder(filas: list[dict]) -> tuple[int, int]:
    """Valores por defecto que decidió la founder (10/11/2026). Solo llena celdas vacías.

    - usar_en_app: "sí" en todas las medidas.
    - efectos_generales: "sí" cuando la pista del texto dice "sí" (por ejemplo, "sí (art. 8:
      ilegal)"), igual que en el listado de INDECOPI. Las que dicen "revisar" o "no" quedan
      vacías para su revisión.
    Devuelve cuántas celdas llenó de cada columna.
    """
    usar = efectos = 0
    for f in filas:
        if not f.get("usar_en_app", "").strip():
            f["usar_en_app"] = "sí"
            usar += 1
        if not f.get("efectos_generales", "").strip() and \
                f.get("efectos_generales_sugerido", "").strip().lower().startswith("sí"):
            f["efectos_generales"] = "sí"
            efectos += 1
    return usar, efectos


def conservar_revision(nuevas: list[dict], anteriores: list[dict]) -> list[dict]:
    """Copia a las filas nuevas lo que la founder ya llenó en las anteriores (por id_medida)."""
    previas = {f["id_medida"]: f for f in anteriores if f.get("id_medida")}
    for fila in nuevas:
        previa = previas.get(fila["id_medida"])
        if not previa:
            continue
        for col in COLUMNAS_FOUNDER + ["fuente", "materia"]:
            if previa.get(col, "").strip():
                fila[col] = previa[col]
    return nuevas
