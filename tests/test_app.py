"""Prueba de la app de Streamlit (app/app.py) SIN llamar a Claude ni gastar crédito.

Simula a una persona que usa el audio de ejemplo y aprieta "Revisar mis requisitos". Whisper y
el buscador sí corren de verdad; las respuestas de Claude se reemplazan por respuestas fijas.
Tarda 1 a 2 minutos (carga los modelos).

Correr desde la raíz del repo:
    python -m tests.test_app
"""

from streamlit.testing.v1 import AppTest

from ai import llm
from ai.schemas import CitaNorma, EvaluacionesLLM, EvaluacionLLM, ExtraccionNota


def claude_simulado(esquema, sistema, mensaje, **kwargs):
    if esquema is ExtraccionNota:
        return ExtraccionNota(distrito="San Juan de Lurigancho", giro="bodega", requisitos=[
            "solo puedo atender de 6 de la mañana a 11 de la noche", "copia de mi DNI"])
    return EvaluacionesLLM(evaluaciones=[
        EvaluacionLLM(requisito="solo puedo atender de 6 de la mañana a 11 de la noche",
                      medida_publicada_id="2567628-1#2", tramite_medida=None, color_sugerido="ambar",
                      base_legal=[], explicacion_simple="Explicación simulada del horario."),
        EvaluacionLLM(requisito="copia de mi DNI", medida_publicada_id=None, tramite_medida=None,
                      color_sugerido="ambar",
                      base_legal=[CitaNorma(norma="D.Leg. 1246, art. 5",
                                            fragmento="a) Copia del Documento Nacional de Identidad.")],
                      explicacion_simple="Explicación simulada del DNI."),
    ])


def test_flujo_de_la_app_con_el_audio_de_ejemplo():
    app = AppTest.from_file("../app/app.py", default_timeout=300)  # relativa a tests/
    app.run()
    assert not app.exception, app.exception
    revisar = next(b for b in app.button if b.label == "Revisar mis requisitos")
    assert revisar.disabled  # sin texto no se puede revisar

    next(b for b in app.button if b.label.startswith("Usar el audio de ejemplo")).click().run()
    texto = app.text_area(key="texto").value
    assert "Lurigancho" in texto or "bodega" in texto.lower(), texto  # Whisper lo transcribió

    original = llm.preguntar
    llm.preguntar = claude_simulado
    try:
        next(b for b in app.button if b.label == "Revisar mis requisitos").click().run()
    finally:
        llm.preguntar = original
    assert not app.exception, app.exception
    otros_errores = [e.value for e in app.error if not e.value.startswith("INDECOPI declaró")]
    assert not otros_errores, otros_errores  # el único "error" (caja roja) es el texto del rojo
    titulos = [m.value for m in app.markdown if m.value.startswith("### ")]
    assert titulos[0].startswith("### 🔴") and titulos[1].startswith("### 🟡"), titulos  # rojo primero
    rojo = [e.value for e in app.error if e.value.startswith("INDECOPI declaró")]
    assert rojo and "San Juan de Lurigancho" in rojo[0]
    assert "Artículo 8.- De la inaplicación" in rojo[0]  # el art. 8.3, en la misma caja de la resolución
    dni = [w.value for w in app.warning if w.value.startswith("**Se verifica que esta exigencia figura como prohibida")]
    assert dni and "Decreto Legislativo 1246, Aprueba diversas medidas de simplificación administrativa" in dni[0]
    assert "*Artículo 5.- Prohibición de la exigencia de documentación*" in dni[0]
    assert [x.label for x in app.expander] == ["Cómo funciona"]  # la base legal no es desplegable
    assert app.get("download_button"), "falta el botón del escrito en PDF"  # hay un rojo
    assert app.session_state.consultas == 1


if __name__ == "__main__":
    test_flujo_de_la_app_con_el_audio_de_ejemplo()
    print("OK  test_flujo_de_la_app_con_el_audio_de_ejemplo")
