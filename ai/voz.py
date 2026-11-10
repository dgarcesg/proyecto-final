"""Nota de voz -> texto, con Whisper (faster-whisper, modelo "small", en la misma computadora).

- No usa API key ni manda el audio a ningún servicio externo.
- No guarda el audio: lo recibe en memoria (bytes), lo transcribe y lo descarta.
- "int8" hace que el modelo use menos memoria y vaya más rápido en un CPU sin tarjeta gráfica.

Uso (desde la raíz del repo), para probar con un archivo:
    python -m ai.voz data/demo/ejemplo_san_juan_de_lurigancho.wav
"""

from __future__ import annotations

import io
import sys
import time
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

MODELO_WHISPER = "small"
MAX_SEGUNDOS = 180  # notas de voz de hasta 3 minutos
FRECUENCIA = 16_000  # Whisper trabaja con audio a 16 kHz

# Vocabulario del tema: ayuda a Whisper a escribir bien siglas y palabras técnicas.
CONTEXTO = (
    "Nota de voz de un emprendedor de Lima sobre su licencia de funcionamiento: "
    "municipalidad, TUPA, Indecopi, ITSE, Defensa Civil, croquis, DNI, RUC."
)


@dataclass
class Transcripcion:
    texto: str
    duracion_audio: float  # segundos
    segundos_proceso: float


class AudioInvalido(ValueError):
    """El audio no se pudo leer, está vacío o es demasiado largo."""


@lru_cache(maxsize=1)
def modelo():
    from faster_whisper import WhisperModel  # tarda; solo se carga si se usa

    return WhisperModel(MODELO_WHISPER, device="cpu", compute_type="int8")


def transcribir(audio: bytes) -> Transcripcion:
    """Recibe el audio (wav, m4a, mp3, ogg, webm) como bytes y devuelve el texto en español."""
    from faster_whisper.audio import decode_audio

    inicio = time.perf_counter()
    try:
        senal = decode_audio(io.BytesIO(audio), sampling_rate=FRECUENCIA)
    except Exception as error:  # formato que PyAV no reconoce
        raise AudioInvalido(f"No se pudo leer el audio: {error}") from error
    duracion = len(senal) / FRECUENCIA
    if duracion < 1:
        raise AudioInvalido("El audio está vacío o dura menos de un segundo.")
    if duracion > MAX_SEGUNDOS:
        raise AudioInvalido(f"El audio dura {duracion:.0f} s; el máximo es {MAX_SEGUNDOS} s.")

    segmentos, _ = modelo().transcribe(
        senal, language="es", beam_size=5, initial_prompt=CONTEXTO,
        vad_filter=True,  # salta los silencios (evita que invente texto)
    )
    texto = " ".join(s.text.strip() for s in segmentos).strip()
    if not texto:
        raise AudioInvalido("No se escuchó ninguna voz en el audio.")
    return Transcripcion(texto, round(duracion, 1), round(time.perf_counter() - inicio, 1))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    t = transcribir(Path(sys.argv[1]).read_bytes())
    print(f"Audio de {t.duracion_audio} s, transcrito en {t.segundos_proceso} s:\n{t.texto}")
