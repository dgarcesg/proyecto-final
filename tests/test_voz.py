"""Pruebas de la transcripción (ai/voz.py). La última carga Whisper y tarda unos 20 segundos.

El audio de ejemplo es una voz sintética de Windows (no es la voz de una persona real) con un
caso inventado.

Correr desde la raíz del repo:
    python -m tests.test_voz
"""

import io
import wave
from pathlib import Path

from ai.voz import AudioInvalido, transcribir

EJEMPLO = Path(__file__).resolve().parent.parent / "data" / "demo" / "ejemplo_san_juan_de_lurigancho.wav"


def silencio(segundos: float) -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16_000)
        w.writeframes(b"\x00\x00" * int(16_000 * segundos))
    return buffer.getvalue()


def falla(audio: bytes) -> bool:
    try:
        transcribir(audio)
    except AudioInvalido:
        return True
    return False


def test_un_archivo_que_no_es_audio_da_un_error_claro():
    assert falla(b"esto no es un audio")


def test_un_audio_de_medio_segundo_da_un_error_claro():
    assert falla(silencio(0.5))


def test_un_audio_de_mas_de_3_minutos_da_un_error_claro():
    assert falla(silencio(181))


def test_z_transcribe_el_audio_de_ejemplo():  # "z": va al final porque carga el modelo
    texto = transcribir(EJEMPLO.read_bytes()).texto.lower()
    for palabra in ["san juan de lurigancho", "licencia de funcionamiento", "croquis", "dni"]:
        assert palabra in texto, palabra


if __name__ == "__main__":
    pruebas = [f for n, f in sorted(globals().items()) if n.startswith("test_")]
    for prueba in pruebas:
        prueba()
        print(f"OK  {prueba.__name__}")
    print(f"{len(pruebas)} pruebas pasaron.")
