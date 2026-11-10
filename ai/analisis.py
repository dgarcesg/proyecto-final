"""El flujo completo, de la transcripción al semáforo. Es lo que llama la app.

    transcripción
      -> anonimizar (DNI, RUC, teléfonos, correos)              ai/llm.py
      -> Claude extrae distrito, giro y requisitos              ai/llm.py + ai/prompts.py
      -> el buscador trae los artículos de cada requisito       ai/rag.py
      -> y las medidas publicadas más parecidas                 ai/medidas.py
      -> Claude evalúa cada requisito (solo ámbar o verde)      ai/llm.py + ai/prompts.py
      -> el código revisa la cita y decide el rojo              aquí + ai/semaforo.py

Uso (desde la raíz del repo; necesita ANTHROPIC_API_KEY en .env y cuesta unos centavos):
    python -m ai.analisis "Tengo una bodega en San Juan de Lurigancho y me piden croquis..."
"""

from __future__ import annotations

import sys
import unicodedata
from dataclasses import dataclass
from datetime import date

from ai import llm, medidas as buscador_medidas, prompts, rag, semaforo
from ai.schemas import Evaluacion, EvaluacionesLLM, ExtraccionNota


@dataclass
class Resultado:
    texto_enviado: str  # la transcripción ya anonimizada
    extraccion: ExtraccionNota
    evaluaciones: list[Evaluacion]
    consumo: llm.Consumo


def _normalizar(texto: str) -> str:
    texto = unicodedata.normalize("NFKC", texto or "")
    texto = texto.replace("“", '"').replace("”", '"').replace("’", "'")
    return " ".join(texto.lower().split()).strip(" .\"'")


def cita_verificada(fragmento: str, articulos: list[rag.ArticuloRecuperado]) -> bool:
    """¿El fragmento que citó Claude está, palabra por palabra, en algún artículo recuperado?"""
    buscado = _normalizar(fragmento)
    return len(buscado) >= 15 and any(buscado in _normalizar(a.texto) for a in articulos)


def analizar(transcripcion: str, hoy: date | None = None) -> Resultado:
    consumo = llm.Consumo()
    texto = llm.anonimizar(transcripcion)

    extraccion = llm.preguntar(
        ExtraccionNota, prompts.SISTEMA, prompts.prompt_extraccion(texto),
        esfuerzo="low", max_tokens=4000, consumo=consumo, nombre="extracción",
    )
    if not extraccion.requisitos:
        return Resultado(texto, extraccion, [], consumo)

    base, por_requisito = rag.contexto_legal(extraccion.requisitos)
    medidas = semaforo.cargar_medidas()  # la tabla completa, para decidir el rojo
    candidatas = buscador_medidas.medidas_relacionadas(extraccion.requisitos, extraccion.distrito)
    respuesta = llm.preguntar(
        EvaluacionesLLM, prompts.SISTEMA,
        prompts.prompt_evaluacion(extraccion, base, por_requisito, candidatas),
        esfuerzo="medium", max_tokens=16000, consumo=consumo, nombre="evaluación",
    )

    recuperados = base + [a for arts in por_requisito.values() for a in arts]
    evaluaciones = []
    for ev in respuesta.evaluaciones:
        final = semaforo.decidir(ev, extraccion.distrito, medidas, hoy)
        final.cita_verificada = cita_verificada(ev.fragmento_usado, recuperados)
        evaluaciones.append(final)
    return Resultado(texto, extraccion, evaluaciones, consumo)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    r = analizar(" ".join(sys.argv[1:]))
    print(f"Distrito: {r.extraccion.distrito} | Giro: {r.extraccion.giro}")
    for e in r.evaluaciones:
        print(f"\n[{e.color.upper()}] {e.requisito}")
        print(f"   {e.norma_citada}  (cita verificada: {'sí' if e.cita_verificada else 'no'})")
        if e.publicacion:
            print(f"   Publicación: {e.publicacion.numero_resolucion} ({e.publicacion.distrito}),"
                  f" surte efecto desde {e.surte_efecto_desde}")
        print(f"   {e.explicacion_simple}")
    print(f"\nCosto aproximado: US$ {r.consumo.costo_usd} ({r.consumo.entrada} tokens de entrada,"
          f" {r.consumo.salida} de salida)")
