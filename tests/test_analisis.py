"""Pruebas del flujo completo (ai/analisis.py) SIN llamar a Claude ni gastar crédito.

En la última prueba, las respuestas de Claude se reemplazan por respuestas fijas ("simuladas")
para comprobar que el código arma bien el resultado y decide el rojo. Esa prueba usa el
buscador de normas, así que tarda unos 40 segundos.

Correr desde la raíz del repo:
    python -m tests.test_analisis
"""

from datetime import date

from ai import analisis, llm
from ai.rag import ArticuloRecuperado
from ai.schemas import CitaNorma, EvaluacionesLLM, EvaluacionLLM, ExtraccionNota


def test_anonimizar_reemplaza_datos_personales():
    texto = "Mi DNI es 45678912, mi RUC 20123456789, mi cel 987 654 321 y mi correo ana.p@gmail.com"
    limpio = llm.anonimizar(texto)
    for dato in ["45678912", "20123456789", "987 654 321", "ana.p@gmail.com"]:
        assert dato not in limpio, dato
    assert "[DNI]" in limpio and "[RUC]" in limpio and "[TELÉFONO]" in limpio and "[CORREO]" in limpio


def test_anonimizar_no_toca_montos_ni_horarios():
    texto = "Me cobran S/ 148.60 y solo puedo abrir de 6:00 a 23:00 horas"
    assert llm.anonimizar(texto) == texto


def test_cita_verificada_solo_si_el_fragmento_esta_en_la_norma():
    art = ArticuloRecuperado("TUO de la Ley 28976, art. 7", "Para el otorgamiento de la licencia de "
                             "funcionamiento serán exigibles como máximo, los siguientes requisitos:", 1.0)
    assert analisis.cita_verificada("serán exigibles como máximo, los siguientes requisitos", [art])
    assert not analisis.cita_verificada("se puede exigir cualquier documento adicional", [art])
    assert not analisis.cita_verificada("máximo", [art])  # demasiado corto para contar como cita


def test_z_flujo_completo_con_claude_simulado():
    def claude_simulado(esquema, sistema, mensaje, **kwargs):
        if esquema is ExtraccionNota:
            return ExtraccionNota(distrito="San Juan de Lurigancho", giro="bodega", requisitos=[
                "solo puedo atender de 6 de la mañana a 11 de la noche",
                "croquis de ubicación del local",
                "copia de mi DNI",
                "solicitud con declaración jurada con mi número de RUC",
            ])
        assert "2567628-1#2" in mensaje  # las medidas publicadas llegan al prompt
        assert 'cita="TUO de la Ley 28976, art. 7"' in mensaje  # y los artículos base también
        assert 'cita="D.Leg. 1246, art. 5"' in mensaje
        assert 'cita="Ley 31866, art. único"' in mensaje  # es una bodega
        return EvaluacionesLLM(evaluaciones=[
            EvaluacionLLM(requisito="solo puedo atender de 6 de la mañana a 11 de la noche",
                          medida_publicada_id="2567628-1#2", tramite_medida=None, color_sugerido="ambar",
                          base_legal=[CitaNorma(norma="D.Leg. 1256, art. 8",
                                                fragmento="dispone su inaplicación con efectos generales")],
                          explicacion_simple="..."),
            EvaluacionLLM(requisito="croquis de ubicación del local",
                          medida_publicada_id="INDECOPI:0482-2024/SEL-INDECOPI#1",
                          tramite_medida="Renovación del Certificado de Seguridad de Defensa Civil", color_sugerido="ambar",
                          base_legal=[CitaNorma(norma="TUO de la Ley 28976, art. 7",
                                                fragmento="serán exigibles como máximo, los siguientes requisitos")],
                          explicacion_simple="..."),
            EvaluacionLLM(requisito="copia de mi DNI", medida_publicada_id=None, tramite_medida=None, color_sugerido="ambar",
                          base_legal=[
                              CitaNorma(norma="D.Leg. 1246, art. 5.1 a)",  # con literal: se verifica igual
                                        fragmento="a) Copia del Documento Nacional de Identidad."),
                              CitaNorma(norma="TUO de la Ley 28976, art. 7",  # frase de OTRO artículo
                                        fragmento="a) Copia del Documento Nacional de Identidad."),
                          ],
                          explicacion_simple="..."),
            EvaluacionLLM(requisito="solicitud con declaración jurada con mi número de RUC",
                          medida_publicada_id=None, tramite_medida=None, color_sugerido="verde",
                          base_legal=[CitaNorma(norma="TUO de la Ley 28976, art. 7",
                                                fragmento="texto inventado por el modelo")],
                          explicacion_simple="..."),
        ])

    original = llm.preguntar
    llm.preguntar = claude_simulado
    try:
        r = analisis.analizar("Tengo una bodega en San Juan de Lurigancho, mi DNI es 45678912...",
                              hoy=date(2026, 11, 10))
    finally:
        llm.preguntar = original

    assert "45678912" not in r.texto_enviado
    colores = [e.color for e in r.evaluaciones]
    # mismo distrito / precedente de otro distrito / sin medida (ámbar por norma) / sin medida (verde)
    assert colores == ["rojo", "ambar", "ambar", "verde"]
    assert r.evaluaciones[0].surte_efecto_desde == date(2026, 10, 26)  # día siguiente de la publicación
    assert r.evaluaciones[0].texto_publicacion.startswith("INDECOPI declaró esta medida")
    rojo, croquis, dni, solicitud = r.evaluaciones
    # en rojo, la primera base legal es el art. 8.3 del D.Leg. 1256 (y no se repite el art. 8)
    assert [c.norma for c in rojo.base_legal] == ["D.Leg. 1256, art. 8"] and rojo.base_legal[0].verificada
    assert "el trámite “Renovación del Certificado de Seguridad de Defensa Civil”" in croquis.texto_publicacion
    assert croquis.base_legal[0].verificada
    assert [c.verificada for c in dni.base_legal] == [True, False]  # la frase no está en el art. 7
    assert not solicitud.base_legal[0].verificada  # la frase no está en la norma


if __name__ == "__main__":
    pruebas = [f for n, f in sorted(globals().items()) if n.startswith("test_")]
    for prueba in pruebas:
        prueba()
        print(f"OK  {prueba.__name__}")
    print(f"{len(pruebas)} pruebas pasaron.")
