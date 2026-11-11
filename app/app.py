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
import re
import sys
import time
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))  # para poder importar ai/ al correr "streamlit run app/app.py"

import streamlit as st  # noqa: E402

from ai import analisis, citas, escrito, llm, medidas, rag, textos, voz  # noqa: E402

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
# Encabezados de la base legal (redacción de la founder)
PROHIBIDA = "se verifica que esta exigencia figura como prohibida en las siguientes disposiciones:"
PERMITIDA = "Esta exigencia está permitida por las siguientes disposiciones:"


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


def md(texto: str) -> str:
    """Escapa los signos que la app leería como formato ($ como fórmula, * como cursiva...)."""
    texto = re.sub(r"([\\`*_$<>#~\[\]])", r"\\\1", texto)
    texto = re.sub(r"^(\d+)\.", r"\1\\.", texto, flags=re.M)  # "1. Tratándose..." no es una lista
    return texto.replace("\n", "  \n")  # artículos completos: cada literal en su línea


def bloque_cita(c) -> str:
    """Nombre completo de la norma, encabezado del artículo y el texto citado (ai/citas.py)."""
    x = citas.extracto(c.norma, c.fragmento)
    if x is None:
        return f"**{md(c.norma)}**\n\n{md(c.fragmento)}"
    partes = [f"**{md(x.norma)}**", f"*{md(x.encabezado)}*"]
    if x.texto:
        partes.append(md(x.texto))
    return "\n\n".join(partes)


def titulo_base_legal(e) -> str:
    if e.color == "verde":
        return PERMITIDA
    return f"Asimismo, {PROHIBIDA}" if e.texto_publicacion else PROHIBIDA[0].upper() + PROHIBIDA[1:]


def mostrar_evaluacion(e) -> None:
    emoji, etiqueta, caja = COLORES[e.color]
    verificadas = [c for c in e.base_legal if c.verificada]
    # en rojo, el art. 8.3 del D.Leg. 1256 va junto a la resolución: es el fundamento de la inaplicación
    de_la_resolucion = [c for c in verificadas if e.color == "rojo" and c.norma == textos.CITA_ART_8]
    otras = [c for c in verificadas if c not in de_la_resolucion]
    with st.container(border=True):
        st.markdown(f"### {emoji} {md(e.requisito)}")
        st.caption(etiqueta)
        if e.texto_publicacion:
            partes = [md(e.texto_publicacion)]
            if e.publicacion and e.publicacion.url_el_peruano.startswith("http"):
                partes.append(f"[Ver la resolución en El Peruano]({e.publicacion.url_el_peruano})")
            caja("\n\n".join(partes + [bloque_cita(c) for c in de_la_resolucion]))
        if otras:
            caja("\n\n".join([f"**{titulo_base_legal(e)}**", *(bloque_cita(c) for c in otras)]))
        if e.color == "rojo" and e.publicacion:  # la inaplicación alcanza solo a la disposición declarada
            st.warning(textos.aviso_rojo(e.publicacion, md), icon="⚠️")
        for c in e.base_legal:
            if not c.verificada:
                st.caption(f"⚠️ Claude citó también {md(c.norma)}, pero esa frase no está en el texto de la "
                           "norma; por eso no se muestra.")
        if e.color != "rojo" or not e.texto_publicacion:  # en rojo manda el texto fijo
            st.markdown(f"**En simple:** {md(e.explicacion_simple)}")


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
        st.info("La municipalidad no puede exigirte los requisitos en rojo si se basan en la misma "
                "disposición que INDECOPI declaró barrera burocrática (revisa el aviso ⚠️ de cada uno). "
                "Descarga este escrito, completa a mano tu nombre, DNI y domicilio, y preséntalo en "
                "mesa de partes.")
        st.download_button(
            "📄 Descargar escrito para la municipalidad (PDF)",
            data=escrito.generar_pdf(r.evaluaciones, ex),
            file_name="escrito_barrera_burocratica.pdf", mime="application/pdf", type="primary",
            on_click="ignore",  # descargar no vuelve a correr la app
        )
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
            "3. Un buscador encuentra, para cada requisito, los **artículos de ley** más parecidos "
            "en estas normas:\n"
            "    - Decreto Supremo 163-2020-PCM, Texto Único Ordenado de la Ley 28976, Ley Marco de "
            "Licencia de Funcionamiento, con las modificaciones de la Ley 31914 y del Decreto "
            "Legislativo 1657.\n"
            "    - Decreto Supremo 006-2026-JUS, Texto Único Ordenado de la Ley 27444, Ley del "
            "Procedimiento Administrativo General.\n"
            "    - Decreto Legislativo 1246, Aprueba diversas medidas de simplificación administrativa.\n"
            "    - Decreto Legislativo 1256, Aprueba la Ley de Prevención y Eliminación de Barreras "
            "Burocráticas.\n"
            "    - Ley 31866, Ley que modifica la Ley 30877, Ley General de Bodegueros, a fin de "
            "impulsar la formalización de la actividad del bodeguero como microemprendedor.\n\n"
            "   También encuentra las **resoluciones de INDECOPI publicadas en el Diario Oficial El "
            "Peruano** que declararon barreras burocráticas ilegales con efectos generales, tanto "
            "de tu distrito como de otras municipalidades.\n"
            "4. Claude evalúa cada requisito citando la norma; el sistema comprueba que la cita "
            "esté palabra por palabra en la ley.\n"
            "5. El resultado es un **semáforo** para cada requisito:\n"
            "    - 🟢 **Verde:** te lo pueden pedir, porque la ley lo permite.\n"
            "    - 🟡 **Ámbar:** podría ser una barrera burocrática. Hay normas o resoluciones de "
            "INDECOPI que podrían sustentar su ilegalidad, pero no una declaración con efectos "
            "generales que ya se aplique a tu distrito (por ejemplo, porque la resolución es de "
            "otra municipalidad).\n"
            "    - 🔴 **Rojo:** INDECOPI ya declaró esa exigencia barrera burocrática con efectos "
            "generales para tu distrito y ya surte efecto, conforme al numeral 8.3 del artículo 8 "
            "del Decreto Legislativo 1256, Aprueba la Ley de Prevención y Eliminación de Barreras "
            "Burocráticas. El rojo no lo decide la IA, sino una regla fija. Si hay un rojo, la app "
            "te entrega un escrito para presentarlo en mesa de partes."
        )


main()
