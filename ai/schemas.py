"""Esquemas de datos (Pydantic) de TUPA bajo la lupa.

Hay dos grupos:
  - MedidaPublicada: una barrera publicada en El Peruano, ya revisada por la founder.
    Es la fuente del semáforo rojo.
  - Lo que devuelve Claude (ExtraccionNota, EvaluacionLLM). Ojo: EvaluacionLLM no tiene
    la opción "rojo". Claude solo puede sugerir ámbar o verde y señalar si el requisito
    coincide con una medida publicada; el rojo lo decide el código (ai/semaforo.py).
"""

from __future__ import annotations

from datetime import date
from typing import Literal, Optional

from pydantic import BaseModel, Field


class MedidaPublicada(BaseModel):
    """Una medida declarada barrera burocrática y publicada en El Peruano."""

    id_medida: str = Field(
        description="ID de la medida: '2461162-1#3' (El Peruano) o 'INDECOPI:0549-2026/SEL-INDECOPI#1' (listado)"
    )
    fuente: str = Field(default="", description="El Peruano (scraper), listado INDECOPI o ambas")
    numero_resolucion: str
    organo: Literal["CEB", "SEL", "SDC"]  # SDC: antigua Sala de Defensa de la Competencia
    entidad: str
    distrito: str = Field(description="Distrito de Lima, confirmado por la founder")
    materia: str = Field(default="", description="Materia según el listado INDECOPI")
    tipo: str = Field(default="", description="ilegal y/o carente de razonabilidad (el listado no lo indica)")
    medida: str = Field(description="Texto de la barrera declarada, tal como se publicó")
    norma_cuestionada: str = ""
    fecha_publicacion: date = Field(description="Fecha de publicación en El Peruano")
    url_el_peruano: str = Field(default="", description="Vacío si la medida viene solo del listado INDECOPI")
    efectos_generales: bool = Field(description="Decisión legal de la founder en la revisión")
    referencia_fuera_de_lima: bool = Field(
        default=False,
        description="Municipalidad fuera de Lima Metropolitana: solo sirve como precedente, nunca da rojo",
    )
    estado: Literal["vigente", "revocada", "entidad_ya_modifico"] = "vigente"
    notas: str = ""


# --- Lo que devuelve Claude -------------------------------------------------

class ExtraccionNota(BaseModel):
    """Paso 3: de la transcripción de la nota de voz a datos ordenados."""

    distrito: Optional[str] = Field(description="Distrito de Lima donde está el negocio, si se menciona")
    giro: Optional[str] = Field(description="Tipo de negocio, p. ej. 'bodega'")
    requisitos: list[str] = Field(description="Cada cosa que le pidieron, tal como la dijo el usuario")


class EvaluacionLLM(BaseModel):
    """Paso 4: evaluación de un requisito con las normas recuperadas por el RAG."""

    requisito: str = Field(description="El requisito tal como lo dijo el usuario")
    medida_publicada_id: Optional[str] = Field(
        description="id_medida de la lista de medidas publicadas que corresponde a este requisito, o null si ninguna"
    )
    color_sugerido: Literal["ambar", "verde"] = Field(
        description="ambar: posible barrera según la Ley Marco o el TUO de la LPAG; verde: se lo pueden pedir"
    )
    norma_citada: str = Field(description="Norma y artículo en que se basa la evaluación")
    fragmento_usado: str = Field(description="Cita textual del fragmento recuperado que sustenta la evaluación")
    explicacion_simple: str = Field(description="Explicación en lenguaje simple para el emprendedor")


class EvaluacionesLLM(BaseModel):
    """Una sola llamada a Claude evalúa todos los requisitos."""

    evaluaciones: list[EvaluacionLLM]


# --- Lo que muestra la app --------------------------------------------------

class Evaluacion(BaseModel):
    """Resultado final por requisito, después de aplicar la regla del rojo en código."""

    requisito: str
    color: Literal["rojo", "ambar", "verde"]
    norma_citada: str
    fragmento_usado: str
    explicacion_simple: str
    publicacion: Optional[MedidaPublicada] = None
    surte_efecto_desde: Optional[date] = None
    cita_verificada: bool = Field(
        default=False,
        description="El código comprobó que el fragmento citado está, palabra por palabra, en las normas recuperadas",
    )
