"""Pruebas del escrito en PDF (ai/escrito.py) con la medida real de San Juan de Lurigancho.

No llama a Claude. Lee el PDF generado con pypdf para revisar su contenido. Tarda unos segundos.

Correr desde la raíz del repo:
    python -m tests.test_escrito
"""

from datetime import date
from io import BytesIO

from pypdf import PdfReader

from ai import escrito
from ai.schemas import CitaNorma, EvaluacionLLM, ExtraccionNota
from ai.semaforo import cargar_medidas, decidir

HOY = date(2026, 11, 10)
EXTRACCION = ExtraccionNota(distrito="San Juan de Lurigancho", giro="bodega", requisitos=["horario"])


def evaluacion(id_medida, color="ambar", base_legal=()):
    ev = EvaluacionLLM(requisito="solo puedo atender de 6 a 23 horas", medida_publicada_id=id_medida,
                       tramite_medida=None, color_sugerido=color, base_legal=list(base_legal),
                       explicacion_simple="...")
    final = decidir(ev, EXTRACCION.distrito, cargar_medidas(), HOY)
    for c in final.base_legal:
        c.verificada = True
    return final


def texto_del_pdf(contenido: bytes) -> str:
    return " ".join(" ".join(p.extract_text().split()) for p in PdfReader(BytesIO(contenido)).pages)


def test_escrito_con_la_resolucion_el_art_8_3_y_espacios_en_blanco():
    rojo = evaluacion("2567628-1#2", base_legal=[CitaNorma(
        norma="TUO de la Ley 28976, art. 7", fragmento="serán exigibles como máximo, los siguientes requisitos")])
    assert rojo.color == "rojo"
    contenido = escrito.generar_pdf([rojo], EXTRACCION, hoy=HOY)
    assert contenido.startswith(b"%PDF")
    texto = texto_del_pdf(contenido)
    for esperado in [
        "SEÑOR(A) ____",  # el cargo del destinatario se llena a mano
        "DE LA MUNICIPALIDAD DISTRITAL DE SAN JUAN DE LURIGANCHO",
        "identificado(a) con Documento Nacional de Identidad N° ____",  # se llena a mano
        "licencia de funcionamiento de mi bodega",
        "Mediante Resolución 0549-2026/SEL-INDECOPI, publicada en el diario oficial El Peruano el 25 de octubre de 2026",
        "la Sala Especializada en Eliminación de Barreras Burocráticas del Tribunal del Indecopi",
        "declaró barrera burocrática ilegal y carente de razonabilidad",
        "8.3. La inaplicación con efectos generales opera a partir del día siguiente",
        "desde el 26 de octubre de 2026",
        "multas de hasta veinte (20) Unidades Impositivas Tributarias, conforme al numeral 34.1",
        "1. Cuando incumpla el mandato de inaplicación de la barrera burocrática declarada ilegal",
        "Lima, 10 de noviembre de 2026",
    ]:
        assert esperado in texto, esperado
    # la founder decidió: el fundamento es la inaplicación (sin otras normas), sin pie de página
    assert "Ley Marco" not in texto and "Modelo generado" not in texto and "Alcalde" not in texto


def test_solo_rojo_y_sin_repetir_la_misma_medida():
    rojo = evaluacion("2567628-1#2")
    ambar = evaluacion(None)
    assert escrito.rojas([rojo, ambar, rojo]) == [rojo]
    try:
        escrito.generar_pdf([ambar], EXTRACCION, hoy=HOY)
    except ValueError:
        pass
    else:
        raise AssertionError("no debe generar escrito sin rojo")


if __name__ == "__main__":
    pruebas = [f for n, f in sorted(globals().items()) if n.startswith("test_")]
    for prueba in pruebas:
        prueba()
        print(f"OK  {prueba.__name__}")
    print(f"{len(pruebas)} pruebas pasaron.")
