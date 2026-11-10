"""Pruebas de cómo se arma cada cita de la base legal (ai/citas.py) y de los giros de bodega.

Usa el texto real de las normas (data/normas/); no llama a Claude. Tarda unos segundos.

Correr desde la raíz del repo:
    python -m tests.test_citas
"""

from ai import rag
from ai.citas import extracto
from ai.textos import CITA_ART_8, FRAGMENTO_ART_8_3


def test_literal_con_su_numeral_como_en_un_escrito():  # el ejemplo de la founder
    x = extracto("D.Leg. 1246, art. 5", "e) Copia de la ficha RUC o certificado de información registrada en "
                 "la Superintendencia Nacional de Aduanas y Administración Tributaria - SUNAT")
    assert x.norma == "Decreto Legislativo 1246, Aprueba diversas medidas de simplificación administrativa"
    assert x.encabezado == "Artículo 5.- Prohibición de la exigencia de documentación"
    assert x.texto == (
        "5.1 Las entidades de la Administración Pública están prohibidas de exigir a los administrados o "
        "usuarios, en el marco de un procedimiento o trámite administrativo, los siguientes documentos: (...) "
        "e) Copia de la ficha RUC o certificado de información registrada en la Superintendencia Nacional de "
        "Aduanas y Administración Tributaria - SUNAT."
    )


def test_literal_que_sigue_al_numeral_va_sin_puntos_suspensivos():
    x = extracto("D.Leg. 1246, art. 5.1 a)", "Copia del Documento Nacional de Identidad")
    assert x.texto.endswith("los siguientes documentos: a) Copia del Documento Nacional de Identidad.")


def test_numeral_que_no_es_el_primero():
    x = extracto(CITA_ART_8, FRAGMENTO_ART_8_3)
    assert x.norma == "Decreto Legislativo 1256, Aprueba la Ley de Prevención y Eliminación de Barreras Burocráticas"
    assert x.encabezado.startswith("Artículo 8.- De la inaplicación con efectos generales")
    assert x.texto.startswith("(...) 8.3. La inaplicación con efectos generales")


def test_item_dentro_de_un_literal_trae_los_parrafos_que_lo_introducen():
    x = extracto("D.Leg. 1256, art. 18", "La existencia del interés público que sustentó la medida cuestionada")
    assert x.texto.startswith("18.1. Una vez que la Comisión o la Sala")  # numeral
    assert "elaboración y emisión de la medida cuestionada: a. Que la medida no es arbitraria" in x.texto  # literal
    assert "acredite: 1. La existencia del interés público" in x.texto  # ítem citado


def test_art_7_de_la_ley_marco_va_siempre_completo():  # criterio de la founder: los requisitos máximos
    for cita in ["TUO de la Ley 28976, art. 7", "Ley 28976 (modificada por D.Leg. 1657), art. 7"]:
        x = extracto(cita, "serán exigibles como máximo, los siguientes requisitos")  # solo el encabezado
        assert "(...)" not in x.texto
        assert x.texto.splitlines()[0].startswith("Para el otorgamiento de la licencia de funcionamiento")
        assert any(p.startswith("d.1)") for p in x.texto.splitlines())
        assert x.texto.splitlines()[-1].startswith("Verificados los requisitos señalados")
    x = extracto("TUO de la Ley 28976, art. 7", "número D.N.I.")
    assert x.norma == ("Decreto Supremo 163-2020-PCM, Texto Único Ordenado de la Ley 28976, Ley Marco de "
                       "Licencia de Funcionamiento")
    assert "\nb) En el caso de personas jurídicas" in x.texto and "\nc) Declaración Jurada" in x.texto
    assert extracto("TUO de la Ley 28976, art. 7", "texto inventado por el modelo") is None  # se verifica igual


def test_subnumeral_trae_su_numeral():
    x = extracto("TUO de la Ley 27444, art. 40", "Fotografías personales")
    assert x.norma.startswith("Decreto Supremo 006-2026-JUS, Texto Único Ordenado de la Ley 27444")
    assert x.texto.startswith("40.1 Para el inicio") and "(...) 40.1.4 Fotografías personales" in x.texto


def test_ley_modificada_por_otra_norma():
    x = extracto("Ley 28976 (modificada por D.Leg. 1657), art. 7",
                 "Declaración jurada de contar con la autorización sectorial")
    assert x.norma == "Ley 28976, Ley Marco de Licencia de Funcionamiento, modificada por el Decreto Legislativo 1657"


def test_frase_o_norma_que_no_existen():
    assert extracto("D.Leg. 1246, art. 5", "texto inventado por el modelo") is None
    assert extracto("D.Leg. 9999, art. 1", "Copia del Documento Nacional de Identidad") is None


def test_tienda_de_abarrotes_y_minimarket_cuentan_como_bodega():
    for giro in ["bodega", "Tienda de Abarrotes", "minimárket", "Mini Market"]:
        assert rag.es_bodega(giro), giro
    for giro in ["restaurante", "peluquería", None]:
        assert not rag.es_bodega(giro), giro


if __name__ == "__main__":
    pruebas = [f for n, f in sorted(globals().items()) if n.startswith("test_")]
    for prueba in pruebas:
        prueba()
        print(f"OK  {prueba.__name__}")
    print(f"{len(pruebas)} pruebas pasaron.")
