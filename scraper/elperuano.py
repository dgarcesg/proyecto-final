"""Scraper de El Peruano: inaplicaciones de barreras burocráticas publicadas por INDECOPI.

Qué hace, en tres pasos:
  1. Recorre las páginas del buscador de El Peruano (busquedas.elperuano.pe) con la
     búsqueda "barrera burocrática" en el rango de fechas elegido por la founder.
  2. Se queda con las publicaciones cuyo sector es INDECOPI y descarga el texto de cada
     una desde el "visor HTML" (busquedas.elperuano.pe/api/visor_html/<id>).
  3. Lee los campos rotulados de cada resolución (ENTIDAD QUE IMPUSO..., BARRERAS
     BUROCRÁTICAS DECLARADAS..., etc.) y guarda solo las que involucran a una
     municipalidad.

No usa IA: los campos salen del propio formato de la publicación. La founder revisa el
resultado a mano (publicaciones_para_revisar.csv) antes de que la app lo use.

Uso (desde la raíz del repo):
    python -m scraper.elperuano --desde 2025-01-01 --hasta 2026-11-10
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import time
import unicodedata
from datetime import date, datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup

from scraper import revision

BASE = "https://busquedas.elperuano.pe"
FUENTE_SCRAPER = "El Peruano (scraper)"
CARPETA = Path(__file__).resolve().parent.parent / "data" / "publicaciones"
CARPETA_HTML = CARPETA / "fuentes" / "elperuano"

# Nos identificamos y vamos despacio: una petición por segundo. Si el servidor corta la
# conexión, esperamos más y reintentamos (10 s y luego 30 s).
HEADERS = {"User-Agent": "TUPA-bajo-la-lupa/0.1 (proyecto academico, Diplomatura Q-Lab PUCP)"}
ESPERAS_SEGUNDOS = [1, 10, 30]

# Los 43 distritos de la provincia de Lima ("Lima" cubre el Cercado).
DISTRITOS_LIMA = [
    "Ancon", "Ate", "Barranco", "Brena", "Carabayllo", "Chaclacayo", "Chorrillos",
    "Cieneguilla", "Comas", "El Agustino", "Independencia", "Jesus Maria", "La Molina",
    "La Victoria", "Lima", "Lince", "Los Olivos", "Lurigancho", "Lurin",
    "Magdalena del Mar", "Miraflores", "Pachacamac", "Pucusana", "Pueblo Libre",
    "Puente Piedra", "Punta Hermosa", "Punta Negra", "Rimac", "San Bartolo", "San Borja",
    "San Isidro", "San Juan de Lurigancho", "San Juan de Miraflores", "San Luis",
    "San Martin de Porres", "San Miguel", "Santa Anita", "Santa Maria del Mar",
    "Santa Rosa", "Santiago de Surco", "Surquillo", "Villa El Salvador",
    "Villa Maria del Triunfo",
]


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------

def sin_tildes(texto: str) -> str:
    """'Jesús María' -> 'jesus maria'. Conserva el largo del texto, letra por letra.

    Conservar el largo permite buscar un rótulo en el texto "limpio" y luego recortar el
    texto original (con sus tildes) en las mismas posiciones.
    """
    salida = []
    for c in texto:
        base = "".join(x for x in unicodedata.normalize("NFKD", c) if not unicodedata.combining(x))
        salida.append((base[:1] or c).lower()[:1] or c)
    return "".join(salida)


def descargar(url: str, params: dict | None = None) -> str:
    """Descarga una página y devuelve su HTML, con pausa antes de cada pedido y reintentos."""
    for intento, espera in enumerate(ESPERAS_SEGUNDOS, start=1):
        time.sleep(espera)
        try:
            resp = requests.get(url, params=params, headers=HEADERS, timeout=30)
            resp.raise_for_status()
            resp.encoding = "utf-8"
            return resp.text
        except requests.RequestException:
            if intento == len(ESPERAS_SEGUNDOS):
                raise
    raise RuntimeError("inalcanzable")


# ---------------------------------------------------------------------------
# Paso 1: el buscador
# ---------------------------------------------------------------------------

def leer_tarjetas(html: str) -> list[dict]:
    """Lee las tarjetas de resultados de una página del buscador."""
    sopa = BeautifulSoup(html, "html.parser")
    tarjetas = []
    for ojo in sopa.find_all("a", attrs={"aria-label": "Ver dispositivo"}):
        tarjeta = ojo.find_parent("div", class_="bg-card")
        if tarjeta is None:
            continue
        parrafos = [p.get_text(" ", strip=True) for p in tarjeta.find_all("p")]
        enlaces = tarjeta.find_all("a", href=re.compile(r"/dispositivo/NL/"))
        sumilla = enlaces[-1].get_text(" ", strip=True) if enlaces else ""
        fecha = re.search(r"(\d{2})\.(\d{2})\.(\d{4})", tarjeta.get_text(" ", strip=True))
        id_norma = ojo["href"].rstrip("/").split("/")[-1]
        tarjetas.append({
            "id": id_norma,
            "sector": parrafos[0] if parrafos else "",
            "tipo_norma": parrafos[1] if len(parrafos) > 1 else "",
            "numero": parrafos[2] if len(parrafos) > 2 else "",
            "sumilla": sumilla,
            "fecha_publicacion": (
                date(int(fecha[3]), int(fecha[2]), int(fecha[1])).isoformat() if fecha else ""
            ),
            "url_el_peruano": f"{BASE}/dispositivo/NL/{id_norma}",
        })
    return tarjetas


def buscar(desde: date, hasta: date, consulta: str = "barrera burocrática") -> list[dict]:
    """Recorre todas las páginas del buscador (20 resultados por página)."""
    resultados: list[dict] = []
    vistos: set[str] = set()
    inicio = 0
    while True:
        params = {
            "start": inicio,
            "query": consulta,
            "ci": "only",
            "fechaIni": desde.strftime("%Y%m%d"),
            "fechaFin": hasta.strftime("%Y%m%d"),
            "showFilters": "true",
        }
        nuevas = [t for t in leer_tarjetas(descargar(f"{BASE}/", params)) if t["id"] not in vistos]
        if not nuevas:  # página vacía o repetida: llegamos al final
            break
        resultados.extend(nuevas)
        vistos.update(t["id"] for t in nuevas)
        print(f"   página {inicio // 20 + 1}: {len(nuevas)} resultados (total {len(resultados)})")
        inicio += 20
    return resultados


def es_indecopi(tarjeta: dict) -> bool:
    sector = sin_tildes(tarjeta["sector"])
    return "indecopi" in sector or "defensa de la competencia" in sector


# ---------------------------------------------------------------------------
# Paso 2: el texto de cada resolución
# ---------------------------------------------------------------------------

def leer_visor(id_norma: str) -> str:
    """Devuelve el HTML del visor; lo guarda en data/ para no volver a pedirlo."""
    CARPETA_HTML.mkdir(parents=True, exist_ok=True)
    archivo = CARPETA_HTML / f"{id_norma}.html"
    if archivo.exists():
        return archivo.read_text(encoding="utf-8")
    html = descargar(f"{BASE}/api/visor_html/{id_norma}")
    archivo.write_text(html, encoding="utf-8")
    return html


# ---------------------------------------------------------------------------
# Paso 3: los campos rotulados
#
# El Peruano usa varios formatos: el rótulo y el valor en el mismo párrafo o en párrafos
# separados, rótulos partidos en dos líneas, con o sin dos puntos, y en distinto orden.
# Por eso se buscan los rótulos en el texto completo y se toma como valor lo que hay
# entre un rótulo y el siguiente.
# ---------------------------------------------------------------------------

# Cubre "barrera burocrática declarada ilegal", "barreras burocráticas declaradas ilegales
# y/o carentes de razonabilidad", "barrera(s) burocrática(s) identificada(s)", etc.
_DECLARADA = (
    r"barreras?(?:\(s\))?\s+burocraticas?(?:\(s\))?\s+(?:declarad|identificad)\w*(?:\(s\))?"
    r"(?:\s+(?:ilegal(?:es)?|y(?:/o)?|carentes?\s+de\s+razonabilidad))*"
)
ROTULOS = {
    "autoridad": r"autoridad\s+que\s+emite\s+la\s+resolucion",
    "fecha_emision": r"fecha\s+de\s+emision\s+de\s+la\s+resolucion",
    "entidad": rf"entidad(?:es)?\s+que\s+(?:la\s+|las\s+)?impus\w*(?:\s+(?:la|las)\s+{_DECLARADA})?",
    "norma": rf"(?:normas?\s+que\s+contienen?|medios?\s+de\s+materializacion)(?:\s+(?:de\s+)?(?:la|las)\s+{_DECLARADA})?",
    "primera_instancia": r"pronunciamiento\s+de\s+primera\s+instancia",
    # En el formato de la Comisión, barreras y fundamentos van bajo un mismo rótulo.
    "medidas": rf"{_DECLARADA}(?:\s*fundamentos\s+de\s+la\s+decision)?",
    "sustento": r"(?:sustento|fundamentos?)(?:\s+y\s+fundamentos?)?\s+de\s+la\s+decision",
}


def campos_rotulados(html: str) -> dict[str, str]:
    """Devuelve {"entidad": "...", "medidas": "...", ..., "_rotulos": "..."}.

    Si la publicación no tiene el rótulo de la entidad, no es una declaración de barrera
    (p. ej., una resolución administrativa de INDECOPI) y devuelve {}.
    """
    sopa = BeautifulSoup(html, "html.parser")
    lineas = [e.get_text(" ", strip=True) for e in sopa.find_all(["h2", "p"])]
    texto = "\n".join(x for x in lineas if x)
    limpio = sin_tildes(texto)

    elegidos: list[tuple[int, int, str]] = []  # (inicio, fin, nombre)

    def tomar(nombre: str) -> None:
        for m in re.finditer(ROTULOS[nombre], limpio):
            # No vale un rótulo que está dentro de otro ya elegido (p. ej., "barreras
            # declaradas ilegales" dentro de "entidad que impuso las barreras...").
            if all(m.end() <= i or m.start() >= f for i, f, _ in elegidos):
                elegidos.append((m.start(), m.end(), nombre))
                return

    for nombre in ["entidad", "norma", "autoridad", "fecha_emision", "primera_instancia",
                   "medidas", "sustento"]:
        tomar(nombre)
    if not any(n == "entidad" for _, _, n in elegidos):
        return {}

    elegidos.sort()
    campos = {"_texto": texto, "_rotulos": " | ".join(limpio[i:f] for i, f, _ in elegidos)}
    for k, (inicio, fin, nombre) in enumerate(elegidos):
        hasta = elegidos[k + 1][0] if k + 1 < len(elegidos) else len(texto)
        campos[nombre] = texto[fin:hasta].strip(" :\n")
        campos[f"_rotulo_{nombre}"] = limpio[inicio:fin]
    return campos


NUMERAL = re.compile(r"^\(\s*(?:[ivx]+|\d+)\s*\)\s*")


def separar_medidas(texto: str, con_fundamentos: bool = False) -> list[str]:
    """Separa las barreras declaradas en una lista, una por numeral (i), (ii), ...

    - Formato de la Sala: cada numeral empieza un párrafo; si una barrera sigue en el
      párrafo siguiente, se une. Sin numerales, todo el texto es una sola barrera.
    - Formato de la Comisión (con_fundamentos=True): después de las barreras vienen los
      fundamentos, así que solo se toman los párrafos numerados o, si no hay, el primero.
    """
    lineas = [" ".join(x.split()) for x in texto.split("\n") if x.strip()]
    if not lineas:
        return []
    hay_numerales = any(NUMERAL.match(x) for x in lineas)
    if con_fundamentos:
        if hay_numerales:
            return [NUMERAL.sub("", x) for x in lineas if NUMERAL.match(x)]
        return [lineas[0]]
    if not hay_numerales:
        return [" ".join(lineas)]
    medidas: list[str] = []
    for x in lineas:
        if NUMERAL.match(x) or not medidas:
            medidas.append(NUMERAL.sub("", x))
        else:
            medidas[-1] += " " + x
    return medidas


def sugerir_efectos_generales(tipos: list[str], tipo_acto: str, procedimiento: str,
                              texto_limpio: str) -> str:
    """Sugerencia para la founder, según los arts. 8, 9 y 10 del D.Leg. 1256.

    Es solo una ayuda para la revisión: la decisión final es la columna `efectos_generales`.
    """
    if "revocacion indirecta" in texto_limpio:
        return "revisar: posible revocación indirecta de licencia (excepción del art. 8.1)"
    if tipo_acto == "actuacion_material":
        return "revisar: actuación material (régimen transitorio de la Ley 32587)"
    if "ilegal" in tipos:
        return "sí (art. 8: ilegal)"
    if "carente de razonabilidad" in tipos:
        if procedimiento == "de oficio":
            return "sí (art. 9: carente de razonabilidad, de oficio)"
        if procedimiento == "de parte":
            return "no (art. 10: carente de razonabilidad, de parte: solo caso concreto)"
    return "revisar"


def distrito_de_lima(entidad: str) -> str:
    """Si la entidad parece una municipalidad de Lima, devuelve el distrito. Si no, ''.

    Es solo una pista para la revisión: hay distritos con el mismo nombre en otras
    provincias (p. ej., Miraflores en Arequipa). La founder confirma cada caso.
    """
    ent = sin_tildes(entidad)
    if "metropolitana de lima" in ent:
        return "Lima (Metropolitana)"
    if "provincial" in ent:
        return ""
    candidatos = [d for d in DISTRITOS_LIMA if re.search(rf"\bde {sin_tildes(d)}\b", ent)]
    return max(candidatos, key=len) if candidatos else ""


def parsear_resolucion(tarjeta: dict, html: str) -> dict | None:
    """Convierte una publicación en un diccionario. None si no es una declaración de barrera."""
    campos = campos_rotulados(html)
    if not campos:
        return None
    texto_limpio = sin_tildes(campos["_texto"])
    rotulos = campos["_rotulos"]

    numero = re.search(r"\d{3,6}-\d{4}[/-](?:SEL|CEB)[\w\-]*", campos["_texto"])
    numero = numero.group(0) if numero else tarjeta["numero"]
    tipos = []
    if "ilegal" in rotulos:
        tipos.append("ilegal")
    if "razonabilidad" in rotulos:
        tipos.append("carente de razonabilidad")
    rotulo_norma = campos.get("_rotulo_norma", "")
    medidas = separar_medidas(
        campos.get("medidas", ""),
        con_fundamentos="fundamentos" in campos.get("_rotulo_medidas", ""),
    )
    norma = " ".join(campos.get("norma", "").split())
    tipo_acto = (
        "disposicion_administrativa" if "norma" in rotulo_norma
        else "revisar (medio de materializacion)" if "materializacion" in rotulo_norma
        else ""
    )
    procedimiento = (
        "de oficio" if "de oficio" in texto_limpio
        else "de parte" if re.search(r"denunciante|a pedido de parte", texto_limpio)
        else ""
    )

    return {
        "id": tarjeta["id"],
        "numero_resolucion": numero,
        "organo": "SEL" if "SEL" in numero.upper() else ("CEB" if "CEB" in numero.upper() else ""),
        "autoridad": " ".join(campos.get("autoridad", "").split()),
        "fecha_emision": " ".join(campos.get("fecha_emision", "").split()),
        "fecha_publicacion": tarjeta["fecha_publicacion"],
        "entidad": " ".join(campos.get("entidad", "").split()),
        "distrito_lima": distrito_de_lima(campos.get("entidad", "")),
        "tipo": tipos,
        # Pistas para la revisión (las confirma la founder).
        "tipo_acto_pista": tipo_acto,
        "procedimiento_pista": procedimiento,
        "efectos_generales_sugerido": sugerir_efectos_generales(
            tipos, tipo_acto, procedimiento, texto_limpio
        ),
        "norma_cuestionada": norma,
        "medidas": medidas,
        "primera_instancia": " ".join(campos.get("primera_instancia", "").split()),
        "sustento": " ".join(campos.get("sustento", "").split()),
        "sumilla": tarjeta["sumilla"],
        "menciona_licencia": "licencia de funcionamiento" in sin_tildes(
            " ".join(medidas) + " " + norma + " " + tarjeta["sumilla"]
        ),
        "url_el_peruano": tarjeta["url_el_peruano"],
    }


# ---------------------------------------------------------------------------
# Salidas
# ---------------------------------------------------------------------------

def guardar_csv(ruta: Path, filas: list[dict]) -> None:
    if not filas:
        return
    # utf-8-sig para que Excel muestre bien las tildes.
    with ruta.open("w", encoding="utf-8-sig", newline="") as f:
        escritor = csv.DictWriter(f, fieldnames=list(filas[0].keys()))
        escritor.writeheader()
        escritor.writerows(filas)


def filas_para_revisar(resoluciones: list[dict], fuente: str) -> list[dict]:
    """Una fila por medida (una resolución puede declarar varias barreras).

    Las últimas columnas están vacías: las llena la founder en Excel.
    """
    filas = []
    for r in resoluciones:
        for i, medida in enumerate(r["medidas"] or [""], start=1):
            filas.append({
                "id_medida": f"{r['id']}#{i}",
                "fuente": fuente,
                "id": r["id"],
                "numero_resolucion": r["numero_resolucion"],
                "organo": r["organo"],
                "fecha_publicacion": r["fecha_publicacion"],
                "entidad": r["entidad"],
                "distrito_lima": r["distrito_lima"],
                "tipo": " y ".join(r["tipo"]),
                "tipo_acto_pista": r["tipo_acto_pista"],
                "procedimiento_pista": r["procedimiento_pista"],
                "efectos_generales_sugerido": r["efectos_generales_sugerido"],
                "menciona_licencia": "sí" if r["menciona_licencia"] else "",
                "n_medida": i,
                "medida": medida,
                "norma_cuestionada": r["norma_cuestionada"],
                "url_el_peruano": r["url_el_peruano"],
                # --- columnas para la revisión de la founder ---
                "efectos_generales": "",  # sí / no: decisión legal de la founder
                "usar_en_app": "",       # sí / no
                "estado": "vigente",     # vigente / revocada / entidad_ya_modifico
                "notas": "",
            })
    return filas


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--desde", default="2025-01-01", help="fecha inicial AAAA-MM-DD")
    parser.add_argument("--hasta", default=date.today().isoformat(), help="fecha final AAAA-MM-DD")
    args = parser.parse_args()
    desde = datetime.strptime(args.desde, "%Y-%m-%d").date()
    hasta = datetime.strptime(args.hasta, "%Y-%m-%d").date()

    CARPETA.mkdir(parents=True, exist_ok=True)
    print(f"1) Buscando 'barrera burocrática' en El Peruano del {desde} al {hasta}...")
    tarjetas = buscar(desde, hasta)
    guardar_csv(CARPETA / "busqueda_elperuano.csv", tarjetas)
    indecopi = [t for t in tarjetas if es_indecopi(t)]
    print(f"   {len(tarjetas)} resultados; {len(indecopi)} publicados por INDECOPI.")

    print("2) Descargando y leyendo cada publicación de INDECOPI...")
    resoluciones, no_barrera, fallidas = [], [], []
    for n, t in enumerate(indecopi, start=1):
        try:
            r = parsear_resolucion(t, leer_visor(t["id"]))
        except requests.RequestException as error:
            fallidas.append(t["id"])
            print(f"   [{n}/{len(indecopi)}] {t['id']}: NO SE PUDO DESCARGAR ({type(error).__name__})")
            continue
        if r is None:
            no_barrera.append(t["id"])
            continue
        if "municipalidad" in sin_tildes(r["entidad"]):
            resoluciones.append(r)

    resoluciones.sort(key=lambda r: r["fecha_publicacion"], reverse=True)
    (CARPETA / "publicaciones_crudas.json").write_text(
        json.dumps(resoluciones, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    # Se conserva lo que la founder ya revisó y las filas de otras fuentes (listado INDECOPI).
    fuente = f"{FUENTE_SCRAPER} ({desde:%d/%m/%Y}–{hasta:%d/%m/%Y})"
    anteriores = revision.leer_csv()
    filas = revision.conservar_revision(filas_para_revisar(resoluciones, fuente), anteriores)
    ids = {f["id_medida"] for f in filas}
    otras = [f for f in anteriores
             if f["id_medida"] not in ids and not f.get("fuente", "").startswith(FUENTE_SCRAPER)]
    revision.guardar_csv(filas + otras)
    if otras:
        print(f"   (se conservaron {len(otras)} filas de otras fuentes)")

    en_lima = [r for r in resoluciones if r["distrito_lima"]]
    print("3) Resumen")
    print(f"   {len(indecopi) - len(no_barrera) - len(fallidas)} declaraciones de barrera leídas; "
          f"{len(no_barrera)} publicaciones de INDECOPI que no son de barreras; "
          f"{len(fallidas)} sin descargar {fallidas if fallidas else ''}")
    print(f"   {len(resoluciones)} involucran a una municipalidad; {len(en_lima)} parecen de Lima.")
    print(f"   {len(filas)} medidas en publicaciones_para_revisar.csv")


if __name__ == "__main__":
    main()
