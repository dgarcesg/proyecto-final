"""Las citas de la base legal, como se escriben en un escrito: nombre completo de la norma,
encabezado del artículo y el párrafo citado con el numeral o literal que lo introduce.

Ejemplo (Claude citó el literal e del art. 5 del D.Leg. 1246):
    Decreto Legislativo 1246, Aprueba diversas medidas de simplificación administrativa
    Artículo 5.- Prohibición de la exigencia de documentación
    5.1 Las entidades (...) los siguientes documentos: (...) e) Copia de la ficha RUC o ...

No usa IA: busca la frase de Claude en el texto de la norma (data/normas/) y arma la cita.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from ai import rag
from ai.normas import nombre_completo

ARTICULO_CITADO = re.compile(r"^Art[íi]culo \d+")

# Artículos que se citan siempre completos (criterio de la founder, 10/11/2026): el art. 7 de la
# Ley Marco lista los requisitos máximos, y con solo un fragmento no se sabe cuáles son.
ARTICULOS_COMPLETOS = {"TUO de la Ley 28976, art. 7", "Ley 28976 (modificada por D.Leg. 1657), art. 7"}


@dataclass
class Extracto:
    norma: str  # "Decreto Legislativo 1246, Aprueba diversas medidas de simplificación administrativa"
    encabezado: str  # "Artículo 5.- Prohibición de la exigencia de documentación"
    texto: str  # "5.1 Las entidades ... documentos: (...) e) Copia de la ficha RUC ..." (completos: con saltos de línea)


def normalizar(texto: str) -> str:
    """Para comparar textos sin que importen mayúsculas, espacios ni el tipo de comillas."""
    texto = unicodedata.normalize("NFKC", texto or "")
    texto = texto.replace("“", '"').replace("”", '"').replace("’", "'")
    return " ".join(texto.lower().split()).strip(" .\"'")


def cita_del_articulo(norma: str) -> str:
    """'D.Leg. 1246, art. 5.1 a)' -> 'D.Leg. 1246, art. 5' (en el corpus, las citas son por artículo)."""
    return re.sub(r"(, art\. [\w-]+?)(?:\.\d+.*|\s.*)$", r"\1", norma.strip())


def _nivel(parrafo: str) -> int:
    """Qué tan adentro está el párrafo: 0 = suelto; 1 = numeral (5.1); 2 = subnumeral (40.1.1);
    10 = literal (a); 11 = subliteral (d.1) o ítem (1.)."""
    if re.match(r"^[a-zñ]\.\d+\)", parrafo, re.I) or re.match(r"^\d+[.)]\s", parrafo):
        return 11
    if re.match(r"^[a-zñ][.)]\s", parrafo, re.I):
        return 10
    if m := re.match(r"^\d+((?:\.\d+)+)\.?\s", parrafo):
        return m.group(1).count(".")
    return 0


def _singular(seccion: str) -> str:
    """'Disposiciones complementarias finales' -> 'Disposición Complementaria Final'."""
    palabras = []
    for p in seccion.lower().split():
        if p == "disposiciones":
            p = "disposición"
        elif p.endswith("ales"):
            p = p[:-2]
        elif p.endswith("s"):
            p = p[:-1]
        palabras.append(p.capitalize())
    return " ".join(palabras)


def _encabezado(articulo: str, epigrafe: str) -> str:
    if m := re.fullmatch(r"(\w+) \((.+)\)", articulo):  # "Primera (Disposiciones complementarias finales)"
        titulo = f"{m.group(1)} {_singular(m.group(2))}"
    else:
        titulo = f"Artículo {articulo}"
    return f"{titulo}.- {epigrafe}" if epigrafe else titulo


def _ubicar(fragmento: str, parrafos: list[str]) -> tuple[int, int] | None:
    """Primer y último párrafo donde está la frase citada: el tramo más corto (puede ser más de uno)."""
    buscado = normalizar(fragmento)
    for largo in range(1, len(parrafos) + 1):
        for i in range(len(parrafos) - largo + 1):
            if buscado in normalizar(" ".join(parrafos[i:i + largo])):
                return i, i + largo - 1
    return None


def extracto(norma: str, fragmento: str) -> Extracto | None:
    """Arma la cita; None si la norma no está en el corpus o la frase no está en el artículo."""
    cita = cita_del_articulo(norma)
    datos = next((f for f in rag._indice()[0] if f["cita"] == cita), None)
    if datos is None:
        return None
    primera, *parrafos = rag.articulo_completo(cita).texto.splitlines()
    epigrafe = primera[len(cita):].strip(" .")
    encabezado = _encabezado(datos["articulo"], epigrafe)
    nombre = nombre_completo(datos["norma"])

    ubicacion = _ubicar(fragmento, parrafos)
    en_titulo = len(normalizar(fragmento)) >= 15 and normalizar(fragmento) in normalizar(primera)
    if ubicacion is None and not en_titulo:
        return None
    if cita in ARTICULOS_COMPLETOS:
        return Extracto(nombre, encabezado, "\n".join(parrafos))  # un párrafo por línea
    if ubicacion is None:
        return Extracto(nombre, encabezado, "")  # Claude citó el título del artículo
    inicio, fin = ubicacion

    # Si la frase está en un literal, se agregan los párrafos que lo introducen ("... los siguientes:")
    introducen, nivel = [], _nivel(parrafos[inicio])
    for k in range(inicio - 1, -1, -1):
        if nivel <= 1:  # un numeral (8.3) o un párrafo suelto no necesita párrafo que lo introduzca
            break
        if parrafos[k].rstrip().endswith(":") and _nivel(parrafos[k]) < nivel:
            introducen.insert(0, k)
            nivel = _nivel(parrafos[k])
    # Una ley que modifica otra cita el artículo nuevo ("Artículo 6. Simplificación de trámites"):
    # se muestra ese encabezado para saber de qué artículo es el párrafo
    primero = introducen[0] if introducen else inicio
    citado = next((k for k in range(primero - 1, -1, -1) if ARTICULO_CITADO.match(parrafos[k])), None)
    if citado is not None:
        introducen.insert(0, citado)

    partes, anterior = [], -1
    for k in introducen + list(range(inicio, fin + 1)):
        if k != anterior + 1:
            partes.append("(...)")  # párrafos que se saltan
        partes.append(parrafos[k])
        anterior = k
    return Extracto(nombre, encabezado, " ".join(partes))
