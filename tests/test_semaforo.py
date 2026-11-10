"""Pruebas de la regla del rojo (ai/semaforo.py) con una medida inventada.

Correr desde la raíz del repo:
    python -m tests.test_semaforo
"""

from datetime import date

from ai.schemas import EvaluacionLLM, MedidaPublicada
from ai.semaforo import decidir

MEDIDA = MedidaPublicada(
    id_medida="PRUEBA#1",
    numero_resolucion="0000-2026/SEL-INDECOPI (ficticia)",
    organo="SEL",
    entidad="Municipalidad Distrital de La Victoria",
    distrito="La Victoria",
    tipo="ilegal",
    medida="medida ficticia para pruebas",
    fecha_publicacion=date(2026, 11, 8),
    url_el_peruano="-",
    efectos_generales=True,
)
HOY = date(2026, 11, 10)


def evaluacion(id_medida, color="verde"):
    return EvaluacionLLM(
        requisito="requisito", medida_publicada_id=id_medida, color_sugerido=color,
        norma_citada="", fragmento_usado="", explicacion_simple="",
    )


def color(id_medida, distrito, hoy=HOY, medida=MEDIDA, sugerido="verde"):
    return decidir(evaluacion(id_medida, sugerido), distrito, {medida.id_medida: medida}, hoy).color


def test_rojo_si_coincide_en_el_mismo_distrito_y_ya_surte_efecto():
    assert color("PRUEBA#1", "la victoria") == "rojo"


def test_ambar_el_mismo_dia_de_la_publicacion():  # art. 8.3: desde el día siguiente
    assert color("PRUEBA#1", "La Victoria", hoy=date(2026, 11, 8)) == "ambar"


def test_ambar_si_es_de_otro_distrito():  # precedente, no inaplicación exigible
    assert color("PRUEBA#1", "Surquillo") == "ambar"


def test_ambar_si_la_founder_marco_sin_efectos_generales():
    sin_efectos = MEDIDA.model_copy(update={"efectos_generales": False})
    assert color("PRUEBA#1", "La Victoria", medida=sin_efectos) == "ambar"


def test_ambar_si_esta_revocada():
    revocada = MEDIDA.model_copy(update={"estado": "revocada"})
    assert color("PRUEBA#1", "La Victoria", medida=revocada) == "ambar"


def test_distritos_homonimos_no_se_confunden():  # 'Santa' (Áncash) no es 'Santa Anita'
    santa = MEDIDA.model_copy(update={"distrito": "Santa"})
    assert color("PRUEBA#1", "Santa Anita", medida=santa) == "ambar"


def test_cercado_y_metropolitana_son_el_mismo_distrito():
    mml = MEDIDA.model_copy(update={"distrito": "Lima (Metropolitana)"})
    assert color("PRUEBA#1", "Cercado de Lima", medida=mml) == "rojo"


def test_referencia_fuera_de_lima_nunca_da_rojo():
    callao = MEDIDA.model_copy(update={"distrito": "La Victoria", "referencia_fuera_de_lima": True})
    assert color("PRUEBA#1", "La Victoria", medida=callao) == "ambar"


def test_si_claude_inventa_un_id_no_hay_rojo():
    assert color("NO-EXISTE#9", "La Victoria") == "verde"


def test_sin_coincidencia_se_respeta_la_sugerencia_de_claude():
    assert color(None, "La Victoria", sugerido="ambar") == "ambar"


if __name__ == "__main__":
    pruebas = [f for n, f in sorted(globals().items()) if n.startswith("test_")]
    for prueba in pruebas:
        prueba()
        print(f"OK  {prueba.__name__}")
    print(f"{len(pruebas)} pruebas pasaron.")
