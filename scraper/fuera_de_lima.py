"""Marca las medidas de municipalidades fuera de Lima Metropolitana, con el criterio de la founder.

Criterio de la founder (revisión del 10/11/2026): en esas filas puso el nombre del lugar en
`distrito_lima` y en `notas`: "No distrito de Lima, sino <departamento>. Mantener como
referencia". Se quedan en la tabla como referencia, pero nunca dan semáforo rojo.

Este script lo replica en las filas con `distrito_lima` vacío:
  1. Si la founder ya anotó esa misma entidad, copia exactamente lo que ella escribió.
  2. Si no, usa la tabla UBICACION de abajo (Callao, Lima Provincias y otros departamentos).
  3. Si la entidad es en realidad de Lima Metropolitana (la pista automática falló), le
     pone su distrito y no la marca como referencia.
Además corrige las resoluciones de HOMONIMOS: municipalidades que se llaman como un distrito
de Lima pero son de otro departamento (la pista automática las confunde).
Nunca sobrescribe lo que la founder ya marcó como referencia.

Uso (desde la raíz del repo):
    python -m scraper.fuera_de_lima
"""

from __future__ import annotations

import re

from scraper import revision
from scraper.elperuano import distrito_de_lima, sin_tildes

NOTA = "No distrito de Lima, sino {}. Mantener como referencia"
PREFIJO_NOTA = "no distrito de lima"

# entidad (sin tildes, en minúsculas) -> (lugar para distrito_lima, departamento para la nota)
UBICACION = {
    "municipalidad distrital de amarilis": ("Amarilis", "Huánuco"),
    "municipalidad distrital de carmen de la legua reynoso": ("Carmen de la Legua Reynoso", "Callao"),
    "municipalidad distrital de chancay": ("Chancay", "Huaral (Lima Provincias)"),
    "municipalidad distrital de chilca": ("Chilca", "Cañete (Lima Provincias)"),
    "municipalidad distrital de el tambo": ("El Tambo", "Junín"),
    "municipalidad distrital de huaura": ("Huaura", "Huaura (Lima Provincias)"),
    "municipalidad distrital de la banda de shilcayo": ("La Banda de Shilcayo", "San Martín"),
    "municipalidad distrital de la perla": ("La Perla", "Callao"),
    "municipalidad distrital de punchana": ("Punchana", "Loreto"),
    "municipalidad distrital de ventanilla": ("Ventanilla", "Callao"),
    "municipalidad provincial de barranca": ("Barranca", "Barranca (Lima Provincias)"),
    "municipalidad provincial de callao": ("Callao", "Callao"),
    "municipalidad provincial del callao": ("Callao", "Callao"),
    "municipalidad provincial de canete": ("Cañete", "Cañete (Lima Provincias)"),
    "municipalidad provincial de chiclayo": ("Chiclayo", "Lambayeque"),
    "municipalidad provincial de huaral": ("Huaral", "Huaral (Lima Provincias)"),
    "municipalidad provincial de huancayo": ("Huancayo", "Junín"),
    "municipalidad provincial de huaura": ("Huaura", "Huaura (Lima Provincias)"),
    "municipalidad provincial de huanuco": ("Huánuco", "Huánuco"),
    "municipalidad provincial de lambayeque": ("Lambayeque", "Lambayeque"),
    "municipalidad provincial de paita": ("Paita", "Piura"),
    "municipalidad provincial de piura": ("Piura", "Piura"),
    "municipalidad provincial de trujillo": ("Trujillo", "La Libertad"),
    "municipalidad provincial del santa": ("Santa", "Ancash"),
}

# Resoluciones de municipalidades homónimas de un distrito de Lima, revisadas por la founder.
# numero_resolucion -> (lugar para distrito_lima, departamento para la nota)
HOMONIMOS = {
    # "Municipalidad Distrital de Santa Rosa": no es Santa Rosa (Lima), sino del Santa,
    # en Chimbote (revisión de la founder del 10/11/2026).
    "0693-2017/CEB-INDECOPI": ("Santa", "Ancash"),
}


def clave(entidad: str) -> str:
    """'MUNICIPALIDAD ... Carmen de la Legua - Reynoso' -> 'municipalidad ... carmen de la legua reynoso'."""
    return " ".join(re.sub(r"\s+-\s+", " ", sin_tildes(entidad)).split())


def es_referencia(fila: dict) -> bool:
    return sin_tildes(fila.get("notas", "")).startswith(PREFIJO_NOTA)


def main() -> None:
    filas = revision.leer_csv()
    homonimos = 0
    for f in filas:
        if f["numero_resolucion"] in HOMONIMOS and not es_referencia(f):
            lugar, departamento = HOMONIMOS[f["numero_resolucion"]]
            f["distrito_lima"] = lugar
            f["notas"] = NOTA.format(departamento)
            homonimos += 1
    criterio_founder = {
        clave(f["entidad"]): (f["distrito_lima"], f["notas"])
        for f in filas
        if es_referencia(f) and f["distrito_lima"].strip()
        and not distrito_de_lima(f["entidad"])  # homónimo de Lima: se decide por resolución
    }
    copiadas, por_tabla, de_lima, pendientes = 0, 0, 0, set()
    for f in filas:
        if f["distrito_lima"].strip():
            continue  # ya tiene distrito: no se toca
        k = clave(f["entidad"])
        if k in criterio_founder:
            f["distrito_lima"], nota = criterio_founder[k]
            f["notas"] = f["notas"] or nota
            copiadas += 1
        elif k in UBICACION:
            lugar, departamento = UBICACION[k]
            f["distrito_lima"] = lugar
            f["notas"] = f["notas"] or NOTA.format(departamento)
            por_tabla += 1
        elif distrito := distrito_de_lima(f["entidad"]):
            f["distrito_lima"] = distrito  # es de Lima Metropolitana: no es referencia
            de_lima += 1
        else:
            pendientes.add(f["entidad"])
    revision.guardar_csv(filas)
    print(f"{homonimos} filas de municipalidades homónimas de un distrito de Lima (HOMONIMOS).")
    print(f"{copiadas} filas con el mismo texto que ya puso la founder para esa entidad.")
    print(f"{por_tabla} filas marcadas con la tabla UBICACION.")
    print(f"{de_lima} filas eran de Lima Metropolitana (la pista automática había fallado).")
    if pendientes:
        print("Sin resolver (agregar a UBICACION):", sorted(pendientes))
    referencia = sum(1 for f in filas if es_referencia(f))
    print(f"Total marcadas como referencia fuera de Lima: {referencia}.")


if __name__ == "__main__":
    main()
