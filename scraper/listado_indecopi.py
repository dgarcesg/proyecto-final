"""Agrega al CSV de revisión el listado oficial de INDECOPI de resoluciones con efectos generales.

Fuente: "Listado de resoluciones con efectos generales - barreras burocráticas", publicado
por INDECOPI en gob.pe:
https://www.gob.pe/institucion/indecopi/informes-publicaciones/4292797-listado-de-resoluciones-con-efectos-generales_barreras-burocraticas

Diferencias con el scraper de El Peruano (scraper/elperuano.py):
  - Rango: el listado va de 2017 al 06/11/2026; el scraper, del 01/01/2025 al 10/11/2026.
  - El listado no trae el link de El Peruano, el tipo de barrera ni la norma cuestionada,
    pero sí la materia (p. ej., "Licencia de funcionamiento").
  - Como INDECOPI lo publica como listado de resoluciones CON efectos generales, por
    defecto `efectos_generales` = "sí" (decisión de la founder). Sigue siendo revisable.

Qué hace:
  1. Lee el Excel: una fila por resolución; las barreras adicionales vienen en filas de
     abajo (celdas combinadas) o varias en una misma celda "(i)... (ii)...".
  2. Se queda con las que involucran a una municipalidad.
  3. Si la resolución ya la trajo el scraper, no la duplica: marca esa fila como hallada
     en ambas fuentes, le agrega la materia y pone efectos_generales = "sí" si estaba vacío.
  4. Si no, agrega sus medidas como filas nuevas. Lo ya revisado por la founder se conserva.

Uso (desde la raíz del repo):
    python -m scraper.listado_indecopi
"""

from __future__ import annotations

import argparse
import re
from datetime import date, datetime
from pathlib import Path

import openpyxl

from scraper import revision
from scraper.elperuano import FUENTE_SCRAPER, distrito_de_lima, sin_tildes

ARCHIVO = revision.CARPETA / "fuentes" / "indecopi" / "4292797-resoluciones-con-efectos-generales.xlsx"
URL_LISTADO = (
    "https://www.gob.pe/institucion/indecopi/informes-publicaciones/"
    "4292797-listado-de-resoluciones-con-efectos-generales_barreras-burocraticas"
)
FUENTE_LISTADO = "Listado INDECOPI de resoluciones con efectos generales (2017–06/11/2026)"
FUENTE_AMBAS = "El Peruano (scraper) y listado INDECOPI"

# "(i) ...", "(ii) ...", "1. ...", "2) ..." al inicio de un párrafo
NUMERAL = re.compile(r"^\(?\s*(?:[ivx]+|\d{1,2})\s*[\).]\s*", re.IGNORECASE)


def limpiar(valor) -> str:
    return " ".join(str(valor or "").replace("\xa0", " ").split())


def clave_resolucion(numero: str) -> str | None:
    """'0549-2026/SEL-INDECOPI' y '549-2026/SEL-INDECOPI' -> '549-2026-SEL-'.

    Sirve para reconocer la misma resolución escrita de distintas formas en las dos fuentes.
    Conserva el sufijo regional (p. ej., CEB-INDECOPI-JUN) porque es otra comisión.
    """
    m = re.search(
        r"(\d{1,6})\s*-\s*(\d{4})\s*[/-]\s*([A-Z]{3})(?:\s*-\s*INDECOPI)?(?:\s*-\s*([A-Z]{3}))?",
        numero.upper(),
    )
    return f"{int(m[1])}-{m[2]}-{m[3]}-{m[4] or ''}" if m else None


def separar_celda(texto: str) -> list[str]:
    """Separa una celda con varias barreras numeradas. Sin numerales, es una sola."""
    parrafos = [limpiar(p) for p in str(texto or "").replace("\xa0", " ").split("\n") if p.strip()]
    if not parrafos:
        return []
    if not any(NUMERAL.match(p) for p in parrafos):
        return [" ".join(parrafos)]
    medidas: list[str] = []
    for p in parrafos:
        if NUMERAL.match(p) or not medidas:
            medidas.append(NUMERAL.sub("", p))
        else:
            medidas[-1] += " " + p
    return medidas


def leer_listado(ruta: Path) -> list[dict]:
    """Devuelve una lista de resoluciones, cada una con todas sus medidas."""
    hoja = openpyxl.load_workbook(ruta, read_only=True, data_only=True).worksheets[0]
    filas = list(hoja.iter_rows(values_only=True))[1:]  # la fila 1 son encabezados
    resoluciones: list[dict] = []
    for fila_excel, fila in enumerate(filas, start=2):
        n, entidad, materia, medida, numero, fecha, n_barreras = (list(fila) + [None] * 7)[:7]
        if any(v is not None for v in (entidad, numero, fecha)):  # empieza una resolución
            resoluciones.append({
                "fila_excel": fila_excel,
                "n": limpiar(n),
                "entidad": limpiar(entidad),
                "materia": limpiar(materia),
                "numero_resolucion": limpiar(numero),
                "fecha_publicacion": (
                    fecha.date().isoformat() if isinstance(fecha, datetime)
                    else fecha.isoformat() if isinstance(fecha, date) else limpiar(fecha)
                ),
                "n_barreras": limpiar(n_barreras),
                "medidas": [],
            })
        if medida is not None and resoluciones:
            resoluciones[-1]["medidas"].extend(separar_celda(medida))
    # El Excel trae algunas filas con solo el nombre de la entidad (sin número, fecha ni
    # barrera): no son resoluciones.
    return [r for r in resoluciones if r["numero_resolucion"] or r["medidas"]]


def organo(numero: str) -> str:
    for sigla in ("SEL", "CEB", "SDC"):
        if sigla in numero.upper():
            return sigla
    return ""


def sugerencia(medida: str) -> str:
    base = "sí (figura en el listado INDECOPI de resoluciones con efectos generales)"
    if "revocacion indirecta" in sin_tildes(medida):
        return base + "; revisar: menciona revocación indirecta (excepción del art. 8.1)"
    return base


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--archivo", type=Path, default=ARCHIVO, help="ruta del Excel de INDECOPI")
    args = parser.parse_args()

    resoluciones = leer_listado(args.archivo)
    municipales = [r for r in resoluciones if "municipalidad" in sin_tildes(r["entidad"])]
    print(f"1) Listado INDECOPI: {len(resoluciones)} resoluciones; {len(municipales)} de municipalidades.")

    # Las filas del listado se rearman en cada corrida (conservando la revisión de la
    # founder); las del scraper se mantienen y solo se marcan si están en ambas fuentes.
    todas = revision.leer_csv()
    previas_listado = [f for f in todas if f.get("fuente") == FUENTE_LISTADO]
    filas = [f for f in todas if f.get("fuente") != FUENTE_LISTADO]
    por_resolucion: dict[str, list[dict]] = {}
    for f in filas:
        if f.get("fuente", "").startswith(FUENTE_SCRAPER):
            clave = clave_resolucion(f["numero_resolucion"])
            if clave:
                por_resolucion.setdefault(clave, []).append(f)

    en_ambas, nuevas = 0, []
    for r in municipales:
        clave = clave_resolucion(r["numero_resolucion"])
        if clave and clave in por_resolucion:  # ya la trajo el scraper
            en_ambas += 1
            for f in por_resolucion[clave]:
                f["fuente"] = FUENTE_AMBAS
                f["materia"] = f.get("materia") or r["materia"]
                if not f.get("efectos_generales", "").strip():
                    f["efectos_generales"] = "sí"
            continue
        base_id = r["numero_resolucion"] or f"sin-numero-fila{r['fila_excel']}"
        for i, medida in enumerate(r["medidas"] or [""], start=1):
            nuevas.append({
                "id_medida": f"INDECOPI:{base_id}#{i}",
                "fuente": FUENTE_LISTADO,
                "id": "",
                "numero_resolucion": r["numero_resolucion"],
                "organo": organo(r["numero_resolucion"]),
                "fecha_publicacion": r["fecha_publicacion"],
                "entidad": r["entidad"],
                "distrito_lima": distrito_de_lima(r["entidad"]),
                "materia": r["materia"],
                "tipo": "",
                "tipo_acto_pista": "",
                "procedimiento_pista": "",
                "efectos_generales_sugerido": sugerencia(medida),
                "menciona_licencia": "sí" if "licencia de funcionamiento" in sin_tildes(
                    medida + " " + r["materia"]) else "",
                "n_medida": i,
                "medida": medida,
                "norma_cuestionada": "",
                "url_el_peruano": "",
                "efectos_generales": "sí",
                "usar_en_app": "",
                "estado": "vigente",
                "notas": "" if r["numero_resolucion"] and r["fecha_publicacion"]
                         else "el listado no trae número o fecha de publicación",
            })

    nuevas = revision.conservar_revision(nuevas, previas_listado)
    repetidos = len(nuevas) - len({f["id_medida"] for f in nuevas})
    if repetidos:
        raise SystemExit(f"Hay {repetidos} id_medida repetidos en el listado: revisar el Excel.")
    revision.guardar_csv(filas + nuevas)
    lima = sum(1 for f in nuevas if f["distrito_lima"])
    print(f"2) {en_ambas} resoluciones ya estaban (traídas por el scraper): marcadas como 'ambas'.")
    print(f"3) {len(nuevas)} medidas del listado que no trajo el scraper ({lima} parecen de Lima).")
    print(f"   Total en {revision.RUTA_REVISION.name}: {len(filas) + len(nuevas)} medidas.")


if __name__ == "__main__":
    main()
