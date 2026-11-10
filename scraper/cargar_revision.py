"""Convierte la revisión de la founder (CSV) en la tabla que usa la app (JSON).

La founder abre data/publicaciones/publicaciones_para_revisar.csv en Excel, llena las
columnas `efectos_generales`, `usar_en_app`, `estado` y `notas` (y corrige `distrito_lima`
si hace falta), y lo guarda como CSV. Este script:
  - toma solo las filas con usar_en_app = sí,
  - valida cada fila con el esquema MedidaPublicada (si algo está mal, dice en qué fila),
  - y escribe data/publicaciones/publicaciones.json.

Uso (desde la raíz del repo):
    python -m scraper.cargar_revision
"""

from __future__ import annotations

import csv
import json
import sys
from datetime import date, datetime
from pathlib import Path

from pydantic import ValidationError

from ai.schemas import MedidaPublicada

CARPETA = Path(__file__).resolve().parent.parent / "data" / "publicaciones"
ENTRADA = CARPETA / "publicaciones_para_revisar.csv"
SALIDA = CARPETA / "publicaciones.json"

SI = {"si", "sí", "x", "1", "true", "s"}


def leer_csv(ruta: Path) -> list[dict]:
    """Lee el CSV aunque Excel lo haya guardado con ';' en vez de ','."""
    texto = ruta.read_text(encoding="utf-8-sig")
    separador = ";" if texto.splitlines()[0].count(";") > texto.splitlines()[0].count(",") else ","
    return list(csv.DictReader(texto.splitlines(), delimiter=separador))


def leer_fecha(valor: str) -> date:
    """Acepta 2026-11-08 o 8/11/2026 (Excel a veces cambia el formato)."""
    for formato in ("%Y-%m-%d", "%d/%m/%Y", "%d/%m/%y"):
        try:
            return datetime.strptime(valor.strip(), formato).date()
        except ValueError:
            continue
    raise ValueError(f"fecha no reconocida: {valor!r}")


def main() -> None:
    filas = leer_csv(ENTRADA)
    medidas, errores = [], []
    for n, f in enumerate(filas, start=2):  # fila 1 = encabezados
        if f.get("usar_en_app", "").strip().lower() not in SI:
            continue
        try:
            medidas.append(MedidaPublicada(
                id_medida=f["id_medida"],
                numero_resolucion=f["numero_resolucion"],
                organo=f["organo"],
                entidad=f["entidad"],
                distrito=f["distrito_lima"],
                tipo=f["tipo"],
                medida=f["medida"],
                norma_cuestionada=f["norma_cuestionada"],
                fecha_publicacion=leer_fecha(f["fecha_publicacion"]),
                url_el_peruano=f["url_el_peruano"],
                efectos_generales=f.get("efectos_generales", "").strip().lower() in SI,
                estado=(f.get("estado") or "vigente").strip(),
                notas=f.get("notas", ""),
            ))
        except (ValidationError, ValueError, KeyError) as error:
            errores.append(f"fila {n} ({f.get('id_medida')}): {error}")

    if errores:
        print("Hay filas con errores; corrígelas en el CSV y vuelve a correr:")
        print("\n".join(errores))
        sys.exit(1)

    SALIDA.write_text(
        json.dumps([m.model_dump(mode="json") for m in medidas], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    con_efectos = sum(m.efectos_generales for m in medidas)
    print(f"{len(medidas)} medidas en {SALIDA.name} ({con_efectos} con efectos generales).")


if __name__ == "__main__":
    main()
