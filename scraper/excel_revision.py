"""Excel para que la founder revise las medidas cómodamente, y su vuelta al CSV.

El CSV (publicaciones_para_revisar.csv) sigue siendo la fuente de verdad del repo. Este
script solo genera una copia en Excel con filtros, listas desplegables y las columnas a
llenar resaltadas, y después copia al CSV lo que la founder marcó.

Uso (desde la raíz del repo):
    python -m scraper.excel_revision exportar   # CSV -> publicaciones_para_revisar.xlsx
    python -m scraper.excel_revision importar   # lo marcado en el .xlsx -> CSV
"""

from __future__ import annotations

import sys

import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.datavalidation import DataValidation

from scraper import revision

RUTA_XLSX = revision.CARPETA / "publicaciones_para_revisar.xlsx"

ANCHOS = {"medida": 80, "entidad": 32, "efectos_generales_sugerido": 34, "fuente": 26,
          "norma_cuestionada": 40, "materia": 22, "notas": 30, "url_el_peruano": 22}
LISTAS = {
    "efectos_generales": '"sí,no"',
    "usar_en_app": '"sí,no"',
    "estado": '"vigente,revocada,entidad_ya_modifico"',
}
AMARILLO = PatternFill("solid", fgColor="FFF2CC")
GRIS = PatternFill("solid", fgColor="D9D9D9")

INSTRUCCIONES = [
    "Cómo revisar",
    "",
    "1. Usa los filtros de la fila 1 (flechita) para ver, por ejemplo, solo un distrito_lima o menciona_licencia = sí.",
    "2. Llena SOLO las columnas amarillas:",
    "   - efectos_generales: sí / no (tu decisión legal; la columna efectos_generales_sugerido es una pista).",
    "   - usar_en_app: sí para que la medida entre a la app. Lo que no marques, no se usa.",
    "   - estado: vigente / revocada / entidad_ya_modifico.",
    "   - distrito_lima: corrígelo si la pista falló (debe ser un distrito de Lima o quedar vacío).",
    "   - notas: lo que quieras anotar.",
    "3. No cambies id_medida: es la llave para pasar tus marcas al CSV.",
    "4. Guarda (Ctrl+G) en este mismo formato .xlsx, cierra el archivo y avísale a Claude.",
]


def exportar() -> None:
    filas = revision.leer_csv()
    # Primero Lima y, dentro de cada grupo, lo más reciente arriba.
    filas.sort(key=lambda f: f.get("fecha_publicacion", ""), reverse=True)
    filas.sort(key=lambda f: f.get("distrito_lima", "") == "")

    libro = openpyxl.Workbook()
    hoja = libro.active
    hoja.title = "Revisión"
    hoja.append(revision.COLUMNAS)
    for f in filas:
        hoja.append([str(f.get(c, "") or "") for c in revision.COLUMNAS])

    for i, col in enumerate(revision.COLUMNAS, start=1):
        celda = hoja.cell(row=1, column=i)
        celda.font = Font(bold=True)
        celda.fill = AMARILLO if col in revision.COLUMNAS_FOUNDER else GRIS
        letra = celda.column_letter
        hoja.column_dimensions[letra].width = ANCHOS.get(col, 14)
        if col in LISTAS:
            validacion = DataValidation(type="list", formula1=LISTAS[col], allow_blank=True)
            hoja.add_data_validation(validacion)
            validacion.add(f"{letra}2:{letra}{len(filas) + 1}")
        if col == "medida":
            for celda_m in hoja[letra][1:]:
                celda_m.alignment = Alignment(wrap_text=True, vertical="top")
    hoja.freeze_panes = "B2"
    hoja.auto_filter.ref = hoja.dimensions

    ayuda = libro.create_sheet("Instrucciones")
    for linea in INSTRUCCIONES:
        ayuda.append([linea])
    ayuda["A1"].font = Font(bold=True, size=14)
    ayuda.column_dimensions["A"].width = 120

    try:
        libro.save(RUTA_XLSX)
    except PermissionError:
        raise SystemExit(f"No se pudo escribir {RUTA_XLSX.name}: ciérralo en Excel y vuelve a correr.")
    print(f"{len(filas)} medidas exportadas a {RUTA_XLSX}")


def importar() -> None:
    hoja = openpyxl.load_workbook(RUTA_XLSX, read_only=True, data_only=True)["Revisión"]
    filas_xlsx = list(hoja.iter_rows(values_only=True))
    columnas = [str(c) for c in filas_xlsx[0]]
    marcadas = {}
    for valores in filas_xlsx[1:]:
        f = dict(zip(columnas, ["" if v is None else str(v).strip() for v in valores]))
        if f.get("id_medida"):
            marcadas[f["id_medida"]] = f

    filas = revision.leer_csv()
    cambios = 0
    for f in filas:
        nueva = marcadas.get(f["id_medida"])
        if not nueva:
            continue
        for col in revision.COLUMNAS_FOUNDER:
            if col in nueva and nueva[col] != f.get(col, ""):
                f[col] = nueva[col]
                cambios += 1
    revision.guardar_csv(filas)
    usar = sum(1 for f in filas if f.get("usar_en_app", "").lower() in {"sí", "si"})
    print(f"{cambios} celdas actualizadas en el CSV; {usar} medidas con usar_en_app = sí.")


if __name__ == "__main__":
    {"exportar": exportar, "importar": importar}.get(
        sys.argv[1] if len(sys.argv) > 1 else "", lambda: print(__doc__)
    )()
