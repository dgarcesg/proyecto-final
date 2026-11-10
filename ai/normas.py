"""Lee las normas exportadas de SPIJ (data/normas/*.html) y las divide en fragmentos por artículo.

Paso previo del buscador (ai/rag.py). No usa IA: solo lee el HTML con reglas fijas.

Cuidado con SPIJ: cuando un artículo fue modificado, el archivo trae la versión antigua, una
nota "(*) ... modificado por ..." y después la versión nueva entre comillas. Por eso:
  - si aparece de nuevo el encabezado del MISMO artículo entre comillas, se descarta lo
    anterior y se queda la versión nueva;
  - si aparece entre comillas un numeral o literal que ya estaba ("8.1.", "a)"), la versión
    nueva reemplaza a la anterior en su mismo lugar;
  - las notas de SPIJ ("(*) ...", "(Texto según ...)") no entran al texto del artículo.

El TUO de la Ley Marco de Licencia (D.S. 163-2020-PCM) es de 2020. Sus notas "(*)" dicen que
la Ley 31914 (2023) y el D.Leg. 1657 (2024) modificaron la Ley 28976, pero no traen el texto
nuevo. La exportación de SPIJ que usamos sí trae esos textos al final del archivo (son los que
SPIJ muestra al abrir las notas; no forman parte del TUO). Se guardan como fragmentos aparte,
citados como "Ley 28976 (modificada por ...)", para que Claude vea el texto vigente.
La founder comparó el archivo con una descarga directa de SPIJ y decidió mantenerlos (10/11/2026).

Uso (desde la raíz del repo), para revisar cómo quedó un artículo:
    python -m ai.normas "D.Leg. 1256" 8
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

from bs4 import BeautifulSoup

CARPETA = Path(__file__).resolve().parent.parent / "data" / "normas"

MAX_CARACTERES = 1800  # artículos más largos se parten (el modelo de embeddings lee ~512 tokens)


@dataclass
class Norma:
    archivo: str
    corto: str  # cómo se cita: "D.Leg. 1256, art. 8"
    nombre: str
    inicio: str | None = None  # párrafo donde empieza el texto (p. ej., el título del TUO)
    fin: tuple[str, ...] = ("POR TANTO",)  # párrafos donde termina (firmas, fe de erratas)
    modificatorias: str | None = None  # párrafo después del cual SPIJ pone las modificaciones


NORMAS = [
    Norma(
        "DL-1256.html", "D.Leg. 1256",
        "Decreto Legislativo 1256, Ley de Prevención y Eliminación de Barreras Burocráticas "
        "(texto consolidado, incluye la Ley 32587)",
    ),
    Norma(
        "DS-006-2026-JUS-TUO-LPAG.html", "TUO de la Ley 27444",
        "TUO de la Ley 27444, Ley del Procedimiento Administrativo General (D.S. 006-2026-JUS)",
        inicio="TEXTO ÚNICO ORDENADO", fin=("DICE:",),  # al final viene una fe de erratas
    ),
    Norma(
        "DS-163-2020-PCM-TUO-Ley-Marco-Licencia-Funcionamiento.html", "TUO de la Ley 28976",
        "TUO de la Ley 28976, Ley Marco de Licencia de Funcionamiento (D.S. 163-2020-PCM)",
        inicio="TEXTO ÚNICO ORDENADO", fin=(), modificatorias="Enlace Web: Anexos",
    ),
    Norma(
        "DL-1246.html", "D.Leg. 1246",
        "Decreto Legislativo 1246, que aprueba diversas medidas de simplificación administrativa",
    ),
    Norma(
        "Ley-31866.html", "Ley 31866",
        "Ley 31866, que modifica la Ley 30877, Ley General de Bodegueros",
        fin=("POR TANTO", "Comuníquese"),
    ),
]

# Modificaciones de la Ley 28976 que SPIJ pone al final del TUO (según sus notas "(*)"):
# el art. 7 lo modificó el D.Leg. 1657 (2024); los demás (1, 2, 9 y 19 a 22), la Ley 31914 (2023).
MODIFICADA_POR = {"7": "D.Leg. 1657"}
MODIFICADA_POR_DEFECTO = "Ley 31914"

COMILLAS = "\"“”'‘’"
ENCABEZADO_ARTICULO = re.compile(
    r"^[\"“]?\s*Art[íi]culo\s+(\d+(?:-[A-Z])?|[IVXL]+|[úu]nico)\b\s*\.?\s*-?\s*(.*)$", re.I
)
ORDINALES = (
    "primera|segunda|tercera|cuarta|quinta|sexta|s[ée]ptima|octava|novena|d[ée]cima(?: \\w+)?"
    "|und[ée]cima|duod[ée]cima|[úu]nica"
)
ENCABEZADO_DISPOSICION = re.compile(rf"^[\"“]?\s*({ORDINALES})\s*\.\s*-?\s*(.*)$", re.I)
SECCION = re.compile(r"^[\"“]?\s*(T[ÍI]TULO|CAP[ÍI]TULO|SUBCAP[ÍI]TULO|SECCI[ÓO]N)\b", re.I)
ROTULO = re.compile(r"^[\"“]?\s*(\d+(?:\.\d+)+\.?|\d+[.)]|[a-zñ]\.\d+\)|[a-zñ][.)])\s", re.I)
NOTA = re.compile(
    r"^(\(\*\)|\((Texto|Art[íi]culo|[ÚU]ltimo|P[áa]rrafo|Numeral|Literal|Inciso)\b|Enlace Web|CONCORDANCIA)",
    re.I,
)
RELLENO = {"(...)", "(…)", "[...]", "[…]", "..."}


@dataclass
class Fragmento:
    norma: str  # "D.Leg. 1256"
    articulo: str  # "8", "I", "único" o "Primera (Disposiciones Complementarias Finales)"
    epigrafe: str
    cita: str  # "D.Leg. 1256, art. 8"
    parrafos: list[str] = field(default_factory=list)
    parte: str = ""  # "1/2" si el artículo se partió

    @property
    def texto(self) -> str:
        encabezado = f"{self.cita}. {self.epigrafe}".strip(". ") + "."
        return "\n".join([encabezado, *self.parrafos])


def _parrafos(ruta: Path) -> list[str]:
    soup = BeautifulSoup(ruta.read_text(encoding="utf-8"), "html.parser")
    textos = (" ".join(p.get_text(" ").split()) for p in soup.find_all("p"))
    return [t for t in textos if t]


def _limpiar(texto: str) -> str:
    """Quita las marcas de nota de SPIJ que quedan dentro del texto: '(*)', '(*)NOTA SPIJ'."""
    texto = texto.split("(*)")[0] if ENCABEZADO_ARTICULO.match(texto) else texto
    texto = re.sub(r"\s*\(\*\)\s*(NOTA SPIJ)?", " ", texto)
    return " ".join(texto.split())


def _sin_comillas(texto: str) -> str:
    return texto.strip(COMILLAS + " ")


def _es_seccion(texto: str) -> bool:
    """TÍTULO I, CAPÍTULO II, o líneas en mayúsculas como 'DISPOSICIONES COMPLEMENTARIAS FINALES'."""
    limpio = _sin_comillas(texto)
    return bool(SECCION.match(limpio)) or (limpio.isupper() and len(limpio) > 3)


def _cortar(parrafos: list[str], norma: Norma) -> tuple[list[str], list[str]]:
    """Devuelve (texto de la norma, modificaciones que SPIJ puso al final)."""
    inicio = 0
    if norma.inicio:
        inicio = next(i for i, p in enumerate(parrafos) if p.startswith(norma.inicio))
    cuerpo = parrafos[inicio:]
    modificaciones: list[str] = []
    if norma.modificatorias:
        corte = next(i for i, p in enumerate(cuerpo) if p.startswith(norma.modificatorias))
        cuerpo, modificaciones = cuerpo[:corte], cuerpo[corte + 1:]
    for i, p in enumerate(cuerpo):
        if any(p.startswith(f) for f in norma.fin):
            cuerpo = cuerpo[:i]
            break
    return cuerpo, modificaciones


def _fragmentos(parrafos: list[str], corto: str, modificada: bool = False) -> list[Fragmento]:
    fragmentos: list[Fragmento] = []
    actual: Fragmento | None = None
    seccion = ""  # p. ej. "Disposiciones Complementarias Finales"
    for crudo in parrafos:
        if NOTA.match(crudo) or crudo in RELLENO:
            continue
        texto = _limpiar(crudo)
        if not texto or _sin_comillas(texto) in RELLENO:
            continue
        citado = texto[0] in COMILLAS  # texto nuevo que SPIJ cita después de una modificación

        if m := ENCABEZADO_ARTICULO.match(texto):
            numero, epigrafe = m.group(1), _sin_comillas(m.group(2)).strip(" .-")
            numero = numero.lower() if numero.lower() == "único" else numero
            if citado and actual and actual.articulo == numero and actual.norma == corto:
                actual.epigrafe, actual.parrafos = epigrafe, []  # versión nueva del mismo artículo
                continue
            if citado and actual and not modificada:
                # artículo de OTRA ley citado por una norma que lo modifica (la Ley 31866
                # cita el nuevo art. 6 de la Ley 30877): es parte del artículo que lo modifica
                actual.parrafos.append(_sin_comillas(texto))
                continue
            norma = f"Ley 28976 (modificada por {MODIFICADA_POR.get(numero, MODIFICADA_POR_DEFECTO)})" if modificada else corto
            actual = Fragmento(norma, numero, epigrafe, f"{norma}, art. {numero}")
            fragmentos.append(actual)
            seccion = ""
            continue

        if (m := ENCABEZADO_DISPOSICION.match(texto)) and seccion:
            ordinal = m.group(1).capitalize()
            actual = Fragmento(corto, f"{ordinal} ({seccion})", _sin_comillas(m.group(2)).strip(" .-"),
                               f"{corto}, {ordinal} Disposición ({seccion})")
            fragmentos.append(actual)
            continue

        if _es_seccion(texto):
            limpio = _sin_comillas(texto)
            if "DISPOSICI" in limpio.upper():
                seccion = limpio.capitalize()
            continue

        if actual is None:
            continue  # considerandos y títulos antes del primer artículo
        contenido = _sin_comillas(texto) if citado else texto
        if citado and (r := ROTULO.match(contenido)):
            previos = [i for i, p in enumerate(actual.parrafos) if (q := ROTULO.match(p)) and q.group(1) == r.group(1)]
            if previos:
                actual.parrafos[previos[-1]] = contenido  # versión nueva del numeral o literal
                continue
        actual.parrafos.append(contenido)
    return [f for f in fragmentos if f.parrafos]


def _partir(fragmento: Fragmento) -> list[Fragmento]:
    """Parte los artículos largos por párrafos; cada parte conserva la cita y el epígrafe."""
    if len(fragmento.texto) <= MAX_CARACTERES:
        return [fragmento]
    grupos, grupo, largo = [], [], 0
    for p in fragmento.parrafos:
        if grupo and largo + len(p) > MAX_CARACTERES:
            grupos.append(grupo)
            grupo, largo = [], 0
        grupo.append(p)
        largo += len(p)
    grupos.append(grupo)
    return [
        Fragmento(fragmento.norma, fragmento.articulo, fragmento.epigrafe, fragmento.cita, g, f"{n}/{len(grupos)}")
        for n, g in enumerate(grupos, start=1)
    ]


def leer_normas(carpeta: Path = CARPETA) -> list[Fragmento]:
    """Todos los fragmentos de las 4 normas, listos para el buscador."""
    todos: list[Fragmento] = []
    for norma in NORMAS:
        cuerpo, modificaciones = _cortar(_parrafos(carpeta / norma.archivo), norma)
        fragmentos = _fragmentos(cuerpo, norma.corto)
        if modificaciones:
            fragmentos += _fragmentos(modificaciones, norma.corto, modificada=True)
        for f in fragmentos:
            todos.extend(_partir(f))
    return todos


if __name__ == "__main__":
    fragmentos = leer_normas()
    if len(sys.argv) == 3:
        norma, articulo = sys.argv[1], sys.argv[2]
        for f in fragmentos:
            if f.norma == norma and f.articulo == articulo:
                print(f.texto, f"\n[{f.parte}]" if f.parte else "", "\n")
    else:
        from collections import Counter
        print(f"{len(fragmentos)} fragmentos:")
        for norma, n in Counter(f.norma for f in fragmentos).items():
            print(f"  {norma}: {n}")
