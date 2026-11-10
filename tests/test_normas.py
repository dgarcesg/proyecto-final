"""Pruebas de cómo se dividen las normas de SPIJ (ai/normas.py). No usan el modelo de embeddings.

Correr desde la raíz del repo:
    python -m tests.test_normas
"""

from ai.normas import leer_normas

FRAGMENTOS = leer_normas()


def texto(cita: str) -> str:
    partes = [f.texto for f in FRAGMENTOS if f.cita == cita]
    assert partes, f"no se encontró {cita}"
    return "\n".join(partes)


def test_dl_1256_art_8_queda_con_la_version_de_la_ley_32587():
    art8 = texto("D.Leg. 1256, art. 8")
    assert "y en actuaciones materiales" in art8.splitlines()[0]  # epígrafe nuevo
    assert art8.count("8.1.") == 1  # SPIJ trae 3 versiones del 8.1; queda solo la última
    assert "disposiciones administrativas o en actuaciones materiales, dispone su inaplicación" in art8
    assert "revocación indirecta de licencia" in art8


def test_dl_1256_art_9_queda_con_la_ultima_version():
    art9 = texto("D.Leg. 1256, art. 9")
    assert art9.count("En los procedimientos iniciados de oficio") == 1
    assert "o en actuaciones materiales" in art9


def test_no_entran_las_notas_de_spij():
    assert not any("(*)" in f.texto or "Texto según" in f.texto for f in FRAGMENTOS)


def test_no_entra_la_fe_de_erratas_del_tuo_lpag():
    assert not any("DEBE DECIR" in f.texto for f in FRAGMENTOS)


def test_tuo_lpag_art_40_documentacion_prohibida():
    assert "Documentación prohibida de solicitar" in texto("TUO de la Ley 27444, art. 40")


def test_no_se_confunden_los_articulos_del_decreto_con_los_del_tuo():
    # el D.S. 163-2020-PCM tiene sus propios arts. 1 a 5 (aprobación, refrendo) antes del TUO
    assert not any(f.epigrafe == "Refrendo" for f in FRAGMENTOS)
    assert "Finalidad de la Ley" in texto("TUO de la Ley 28976, art. 1")


def test_modificacion_posterior_del_art_7_de_la_ley_marco():
    assert "d.4)" in texto("Ley 28976 (modificada por D.Leg. 1657), art. 7")


def test_dl_1246_prohibe_pedir_copia_del_dni():
    assert "a) Copia del Documento Nacional de Identidad." in texto("D.Leg. 1246, art. 5")


def test_dl_1246_las_modificatorias_no_se_confunden_con_sus_articulos():
    # su Primera Disposición cita el nuevo art. 6 del D.Leg. 1140; no es el art. 6 del D.Leg. 1246
    assert "Facilidades para efectuar el pago" in texto("D.Leg. 1246, art. 6")
    assert "Oficina Nacional de Gobierno Interior" not in texto("D.Leg. 1246, art. 6")


def test_ley_31866_incluye_el_nuevo_art_6_de_la_ley_de_bodegueros():
    articulo = texto("Ley 31866, art. único")
    assert "licencia provisional de funcionamiento" in articulo
    assert not any(f.cita == "Ley 31866, art. 6" for f in FRAGMENTOS)


if __name__ == "__main__":
    pruebas = [f for n, f in sorted(globals().items()) if n.startswith("test_")]
    for prueba in pruebas:
        prueba()
        print(f"OK  {prueba.__name__}")
    print(f"{len(pruebas)} pruebas pasaron.")
