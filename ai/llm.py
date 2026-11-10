"""La ÚNICA parte del proyecto que llama a Claude (API de Anthropic).

- La clave se lee de la variable ANTHROPIC_API_KEY (archivo .env en local, "secret" en Hugging
  Face). Nunca se escribe en el código.
- Antes de enviar la transcripción se reemplazan DNI, RUC, teléfonos y correos (anonimizar).
- Se usan salidas estructuradas: Claude responde con el esquema Pydantic de ai/schemas.py y el
  SDK lo valida; no hay que leer texto libre.
- Si Claude se niega a responder (stop_reason "refusal"), el servidor reintenta con otro modelo
  ("fallbacks": "default"); si igual se niega, se muestra un error claro.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from dataclasses import dataclass, field
from functools import lru_cache
from typing import TypeVar

from pydantic import BaseModel

MODELO = "claude-opus-5-5"
BETAS = ["server-side-fallback-2026-07-01"]  # necesaria para fallbacks="default"
PRECIO_ENTRADA = 4.00 / 1_000_000  # US$ por token (Claude Opus 5.5)
PRECIO_SALIDA = 20.00 / 1_000_000

Esquema = TypeVar("Esquema", bound=BaseModel)


class ErrorClaude(RuntimeError):
    """Algo falló al consultar a Claude; el mensaje se puede mostrar al usuario."""


# --- Datos personales -------------------------------------------------------

_PATRONES = [
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+"), "[CORREO]"),
    (re.compile(r"\b(?:10|15|17|20)\d{9}\b"), "[RUC]"),
    (re.compile(r"(?:\+?51[\s-]?)?\b9\d{2}[\s-]?\d{3}[\s-]?\d{3}\b"), "[TELÉFONO]"),
    (re.compile(r"\b\d{8}\b"), "[DNI]"),
]


def anonimizar(texto: str) -> str:
    """Reemplaza correos, RUC, celulares y DNI por etiquetas antes de enviar el texto a Claude."""
    for patron, etiqueta in _PATRONES:
        texto = patron.sub(etiqueta, texto)
    return texto


# --- Llamada a Claude -------------------------------------------------------

@dataclass
class Consumo:
    """Tokens usados en una consulta (para mostrar el costo aproximado)."""

    entrada: int = 0
    salida: int = 0
    llamadas: list[str] = field(default_factory=list)

    @property
    def costo_usd(self) -> float:
        return round(self.entrada * PRECIO_ENTRADA + self.salida * PRECIO_SALIDA, 4)


@lru_cache(maxsize=1)
def cliente():
    import anthropic
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parent.parent / ".env")  # en local; en Hugging Face es un secret
    if not os.environ.get("ANTHROPIC_API_KEY", "").strip():
        raise ErrorClaude(
            "Falta la clave de Claude: copia .env.example como .env y escribe tu clave en "
            "ANTHROPIC_API_KEY (en Hugging Face, agrégala como secret)."
        )
    return anthropic.Anthropic(max_retries=3, timeout=120.0)


def preguntar(
    esquema: type[Esquema], sistema: str, mensaje: str, *, esfuerzo: str, max_tokens: int,
    consumo: Consumo, nombre: str,
) -> Esquema:
    """Envía un mensaje a Claude y devuelve su respuesta ya validada con el esquema."""
    import anthropic

    try:
        r = cliente().beta.messages.parse(
            model=MODELO,
            max_tokens=max_tokens,
            system=sistema,
            messages=[{"role": "user", "content": mensaje}],
            output_format=esquema,
            output_config={"effort": esfuerzo},  # low | medium | high: cuánto "piensa"
            betas=BETAS,
            fallbacks="default",
        )
    except anthropic.AuthenticationError as e:
        raise ErrorClaude("La clave de Claude no es válida. Revisa ANTHROPIC_API_KEY.") from e
    except anthropic.RateLimitError as e:
        raise ErrorClaude("Claude está recibiendo muchas consultas. Intenta en un minuto.") from e
    except anthropic.APIConnectionError as e:
        raise ErrorClaude("No hay conexión con Claude. Revisa tu internet.") from e
    except anthropic.APIStatusError as e:
        mensaje_error = str(getattr(e, "message", "") or e)
        if "credit" in mensaje_error.lower() or "spend" in mensaje_error.lower():
            raise ErrorClaude("Se acabó el crédito o se alcanzó el límite de gasto de la API.") from e
        raise ErrorClaude(f"Claude respondió con un error ({e.status_code}).") from e

    consumo.entrada += r.usage.input_tokens
    consumo.salida += r.usage.output_tokens
    consumo.llamadas.append(nombre)
    if r.stop_reason == "refusal":
        raise ErrorClaude("Claude no pudo responder esta consulta. Prueba describiendo el caso de otra forma.")
    if r.stop_reason == "max_tokens":
        raise ErrorClaude("La respuesta de Claude quedó incompleta. Prueba con una nota de voz más corta.")
    if r.parsed_output is None:
        raise ErrorClaude("La respuesta de Claude no tuvo el formato esperado. Intenta otra vez.")
    return r.parsed_output
