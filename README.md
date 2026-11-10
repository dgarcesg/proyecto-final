# TUPA bajo la lupa

> **Estado:** en construcción (martes 10 de noviembre de 2026). Este README se completa a lo largo del día.

## 1. One-liner

*(borrador)* Ayudamos a emprendedores de Lima a saber, con una nota de voz, si lo que les pide su municipalidad para la licencia de funcionamiento es legal y, si ya fue declarado barrera burocrática, les damos el escrito listo para presentarlo.

## 2. Founder

**Diana Adriana Garces Garcia**. *(foto y línea por completar)*

## 3. Problema

*(por completar: quién lo sufre, cuánto le cuesta y cómo lo resuelve hoy; evidencia en [`docs/research/`](docs/research/))*

## 4. Solución e insight

*(por completar)*

## 5. Why now

*(por completar)*

## 6. Demo

*(URL pública, 3 capturas, diagrama de arquitectura y video de respaldo: por completar)*

### Cómo correrlo en local

```bash
conda create -n tupa python=3.12 -y
conda activate tupa
pip install -r requirements.txt
cp .env.example .env        # y pega tu ANTHROPIC_API_KEY en .env
streamlit run app/app.py
```

## 7. Modelo de negocio

*(por completar)*

## 8. Herramientas del curso

| Herramienta | Sesión | Dónde está en el repo |
|---|---|---|
| Scraping y APIs | 03 | `scraper/` *(en construcción)* |
| LLM con salidas estructuradas y RAG | 08 | `ai/` *(en construcción)* |
| Voz a texto con Whisper | 13 | `ai/` *(en construcción)* |

## 9. Qué hizo el agente

*(se completa al final; registro parcial:)*

- **Estructura del repo:** Claude Code creó las carpetas, `.gitignore`, `.env.example`, `requirements.txt` y este esqueleto de README, a partir de un brief de diseño escrito por la founder.

## Estructura del repo

```
app/              # interfaz en Streamlit
ai/               # prompts, esquemas Pydantic, RAG y la única llamada a Claude (ai/llm.py)
scraper/          # lectura de publicaciones de El Peruano
data/normas/      # textos legales (exportados del SPIJ)
data/publicaciones/  # inaplicaciones con efectos generales publicadas en El Peruano
docs/             # capturas y diagrama
docs/research/    # notas de las 3 conversaciones con usuarios
notebooks/        # exploración
```

## Aviso

TUPA bajo la lupa da **orientación, no asesoría legal**. Los casos complejos deben verse con un abogado.

## Licencia

[MIT](LICENSE)
