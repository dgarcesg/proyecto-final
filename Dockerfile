# Instrucciones para que Hugging Face Spaces instale y prenda la app (plantilla Docker de Streamlit).
FROM python:3.12-slim

# Hugging Face corre la app con el usuario 1000 (no como administrador)
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    PYTHONIOENCODING=utf-8 \
    PYTHONUNBUFFERED=1
WORKDIR /home/user/app

# requirements.txt ya pide torch solo para CPU en Linux (la versión normal pesa varios GB más)
COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=user . .

# Descarga Whisper y el modelo de embeddings al construir, y revisa los índices,
# para que el primer visitante no espere la descarga
RUN python -c "from ai import medidas, rag, voz; voz.modelo(); rag.modelo(); rag._indice(); medidas._indice()"

EXPOSE 8501
# enableXsrfProtection=false: sin esto, subir o grabar audio falla dentro de la página de Hugging Face
CMD ["streamlit", "run", "app/app.py", "--server.port=8501", "--server.address=0.0.0.0", \
     "--server.enableXsrfProtection=false", "--browser.gatherUsageStats=false"]
