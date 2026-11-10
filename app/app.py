"""TUPA bajo la lupa: la app (Streamlit).

El emprendedor cuenta en una nota de voz (o por escrito) qué le pide su municipalidad para la
licencia de funcionamiento, y la app le dice, requisito por requisito:
  🔴 rojo:  INDECOPI declaró esa barrera con efectos generales para su distrito;
  🟡 ámbar: hay normas o resoluciones de otros distritos que podrían sustentar su ilegalidad;
  🟢 verde: la norma permite pedirlo.

Correr desde la raíz del repo:
    streamlit run app/app.py
"""

from __future__ import annotations

import hashlib
import logging
import sys
import time
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))  # para poder importar ai/ al correr "streamlit run app/app.py"

import streamlit as st  # noqa: E402

from ai import analisis, llm, medidas, rag, voz  # noqa: E402

st.set_page_config(page_title="TUPA bajo la lupa", page_icon="🔎", layout="centered")

MAX_CONSULTAS = 5  # por visitante: cuida el crédito de la API
MAX_CONSULTAS_DIA = 60  # entre todos los visitantes (aprox. US$ 7 al día como máximo)
MAX_CARACTERES = 2500
EJEMPLO = RAIZ / "data" / "demo" / "ejemplo_san_juan_de_lurigancho.wav"

COLORES = {
    "rojo": ("🔴", "Barrera declarada para tu distrito", st.error),
    "ambar": ("🟡", "Posible barrera: revisa la base legal", st.warning),
    "verde": ("🟢", "Te lo pueden pedir", st.success),
}
ORDEN = {"rojo": 0, "ambar": 1, "verde": 2}


@st.cache_resource(show_spinner="Preparando la app (solo la primera vez, aprox. 1 minuto)...")
def preparar() -> bool:
    """Carga una sola vez Whisper, el modelo de embeddings y las bases de búsqueda."""
    voz.modelo()
    rag.coleccion()
    medidas.medidas_relacionadas(["prueba"], None)
    return True


@st.cache_resource
def contador_global() -> dict:
    """Consultas de hoy entre todos los visitantes (vive mientras el servidor esté prendido)."""
    return {"dia": date.today(), "consultas": 0}


def quedan_consultas_hoy() -> bool:
    c = contador_global()
    if c["dia"] != date.today():
        c.update(dia=date.today(), consultas=0)
    return c["consultas"] < MAX_CONSULTAS_DIA


def estado_inicial() -> None:
    for clave, valor in {"texto": "", "ultimo_audio": None, "resultado": None, "consultas": 0}.items():
        st.session_state.setdefault(clave, valor)


def transcribir(audio: bytes) -> None:
    """Transcribe un audio nuevo y lo pone en el cuadro de texto. El audio no se guarda."""
    huella = hashlib.sha256(audio).hexdigest()
    if huella == st.session_state.ultimo_audio:
        return  # ya se transcribió (Streamlit vuelve a correr el script en cada clic)
    st.session_state.ultimo_audio = huella
    try:
        with st.spinner("Escuchando tu nota de voz..."):
            t = voz.transcribir(audio)
    except voz.AudioInvalido as e:
        st.error(str(e))
        return
    st.session_state.texto = t.texto
    st.session_state.resultado = None


def mostrar_evaluacion(e) -> None:
    emoji, etiqueta, caja = COLORES[e.color]
    with st.container(border=True):
        st.markdown(f"### {emoji} {e.requisito}")
        st.caption(etiqueta)
        if e.texto_publicacion:
            caja(e.texto_publicacion)
        if e.color != "rojo" or not e.texto_publicacion:
            st.markdown(f"**En simple:** {e.explicacion_simple}")
        if e.publicacion and e.publicacion.url_el_peruano.startswith("http"):
            st.markdown(f"[Ver la resolución en El Peruano]({e.publicacion.url_el_peruano})")
        if e.base_legal:
            with st.expander("Base legal"):
                for c in e.base_legal:
                    marca = "✅ cita verificada en la norma" if c.verificada else "⚠️ no pudimos verificar esta cita"
                    st.markdown(f"**{c.norma}** · {marca}\n\n> {c.fragmento}")
        if e.color == "rojo" and e.texto_publicacion:
            with st.expander("Qué dice Claude"):
                st.write(e.explicacion_simple)


def mostrar_resultado(r: analisis.Resultado, segundos: float) -> None:
    ex = r.extraccion
    st.subheader("3. Resultado")
    st.markdown(f"**Distrito:** {ex.distrito or 'no lo mencionaste'} · **Negocio:** {ex.giro or 'no lo mencionaste'}")
    if not r.evaluaciones:
        st.info("No encontramos requisitos en tu mensaje. Cuéntanos qué te pide la municipalidad.")
        return
    conteo = {c: sum(e.color == c for e in r.evaluaciones) for c in COLORES}
    a, b, c = st.columns(3)
    a.metric("🔴 Rojo", conteo["rojo"])
    b.metric("🟡 Ámbar", conteo["ambar"])
    c.metric("🟢 Verde", conteo["verde"])
    for e in sorted(r.evaluaciones, key=lambda e: ORDEN[e.color]):
        mostrar_evaluacion(e)
    if conteo["rojo"]:
        st.info("En los requisitos en rojo, la municipalidad no puede exigírtelos. Puedes presentar un "
                "escrito citando la resolución de INDECOPI.")
    st.caption(f"Consulta procesada en {segundos:.0f} s · costo aproximado US$ {r.consumo.costo_usd:.2f}")


def main() -> None:
    estado_inicial()
    st.title("🔎 TUPA bajo la lupa")
    st.markdown(
        "¿Estás sacando tu **licencia de funcionamiento** en Lima? Cuéntanos qué te pide la "
        "municipalidad y te decimos, requisito por requisito, si te lo pueden exigir."
    )
    st.caption("Orientación, no asesoría legal. Los casos complejos deben verse con un abogado.")
    preparar()

    st.subheader("1. Cuéntanos tu caso")
    st.markdown("Di tu **distrito**, tu **tipo de negocio** y **qué te piden** (documentos, pagos, horarios...).")
    grabar, subir, escribir = st.tabs(["🎙️ Grabar", "📁 Subir audio", "⌨️ Escribir"])
    with grabar:
        grabado = st.audio_input("Graba tu nota de voz (máximo 3 minutos)")
        if grabado:
            transcribir(grabado.getvalue())
    with subir:
        subido = st.file_uploader("Sube un audio", type=["wav", "mp3", "m4a", "ogg", "webm"])
        if subido:
            transcribir(subido.getvalue())
        if st.button("Usar el audio de ejemplo (bodega en San Juan de Lurigancho)"):
            transcribir(EJEMPLO.read_bytes())
    with escribir:
        st.caption("Escribe tu caso en el cuadro de abajo.")

    st.subheader("2. Revisa lo que entendimos")
    texto = st.text_area(
        "Puedes corregir el texto antes de revisarlo", key="texto", height=140, max_chars=MAX_CARACTERES,
        placeholder="Ej.: Tengo una bodega en Santa Anita y me cobran S/ 170 por la licencia...",
    )
    hay_cupo = st.session_state.consultas < MAX_CONSULTAS and quedan_consultas_hoy()
    revisar = st.button("Revisar mis requisitos", type="primary", disabled=not texto.strip() or not hay_cupo)
    if not hay_cupo:
        st.warning("Llegaste al máximo de consultas de esta demo por hoy. Gracias por probarla.")
    st.caption("No guardamos tu audio. Antes de enviar el texto a Claude, reemplazamos DNI, RUC, "
               "teléfonos y correos.")

    if revisar:
        inicio = time.perf_counter()
        try:
            with st.spinner("Revisando tus requisitos con las normas y las resoluciones de INDECOPI "
                            "(aprox. 40 segundos)..."):
                resultado = analisis.analizar(texto)
        except llm.ErrorClaude as e:
            st.error(str(e))
        except Exception:  # cualquier otro problema: mensaje simple, sin detalles técnicos
            logging.exception("Falló el análisis")  # el detalle queda en el registro del servidor
            st.error("Ocurrió un problema al revisar tus requisitos. Inténtalo de nuevo en unos minutos.")
        else:
            st.session_state.consultas += 1
            contador_global()["consultas"] += 1
            st.session_state.resultado = (resultado, time.perf_counter() - inicio)

    if st.session_state.resultado:
        mostrar_resultado(*st.session_state.resultado)

    with st.expander("Cómo funciona"):
        st.markdown(
            "1. **Whisper** convierte tu nota de voz en texto, en nuestro servidor.\n"
            "2. **Claude** identifica tu distrito, tu negocio y cada requisito.\n"
            "3. Un buscador encuentra los **artículos de ley** (Ley Marco de Licencia de "
            "Funcionamiento, TUO de la Ley 27444, D.Leg. 1246, D.Leg. 1256, Ley 31866) y las "
            "**resoluciones de INDECOPI** publicadas más parecidas.\n"
            "4. Claude evalúa cada requisito citando la norma; el sistema comprueba que la cita "
            "esté palabra por palabra en la ley.\n"
            "5. El **rojo** no lo decide la IA: solo sale si INDECOPI declaró esa barrera con "
            "efectos generales para tu distrito y ya surte efecto (art. 8.3 del D.Leg. 1256)."
        )


main()
