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

Pruebas (no usan la API de Claude):

```bash
python -m tests.test_semaforo   # regla del semáforo rojo
python -m tests.test_normas     # división de las normas por artículo
python -m tests.test_voz        # transcripción (carga Whisper; ~20 s)
python -m tests.test_analisis   # flujo completo con Claude simulado (no gasta crédito)
python -m ai.rag buscar "me piden croquis de ubicación"   # prueba del buscador
```

## 7. Modelo de negocio

*(por completar)*

## 8. Herramientas del curso

| Herramienta | Sesión | Dónde está en el repo |
|---|---|---|
| Scraping y APIs | 03 | `scraper/` *(en construcción)* |
| RAG: embeddings (multilingual-e5-small) + ChromaDB sobre las normas, y búsqueda de las medidas publicadas más parecidas | 08 | [`ai/normas.py`](ai/normas.py), [`ai/rag.py`](ai/rag.py), [`ai/medidas.py`](ai/medidas.py) |
| LLM con salidas estructuradas (Claude Opus 5.5 + Pydantic) | 08 | [`ai/llm.py`](ai/llm.py), [`ai/prompts.py`](ai/prompts.py), [`ai/analisis.py`](ai/analisis.py) |
| Voz a texto con Whisper (faster-whisper `small`, int8, en la misma computadora) | 13 | [`ai/voz.py`](ai/voz.py) |

## 9. Qué hizo el agente

*(se completa al final; registro parcial:)*

- **Estructura del repo:** Claude Code creó las carpetas, `.gitignore`, `.env.example`, `requirements.txt` y este esqueleto de README, a partir de un brief de diseño escrito por la founder.
- **Buscador de normas (RAG):** Claude Code escribió `ai/normas.py`, que divide las normas por artículo y se queda con el texto vigente cuando SPIJ trae versiones anteriores, y `ai/rag.py` (embeddings y ChromaDB). La founder eligió las normas y decidió mantener los textos modificatorios de la Ley 28976 que trae SPIJ.
- **Voz a texto:** Claude Code escribió `ai/voz.py` (Whisper en la misma computadora; el audio no se guarda) y generó un audio de ejemplo con la voz sintética de Windows y un caso inventado (`data/demo/`).
- **Llamada a Claude:** Claude Code escribió `ai/llm.py` (la única llamada a la API, con anonimización de DNI, RUC, teléfonos y correos), los prompts (`ai/prompts.py`) y el flujo (`ai/analisis.py`). El código comprueba que la frase que cita Claude esté palabra por palabra en la norma, y el rojo lo sigue decidiendo `ai/semaforo.py`.

## Fuentes de datos

| Fuente | Rango | Para qué |
|---|---|---|
| Normas en `data/normas/` (exportadas del SPIJ): D.Leg. 1256 (con la Ley 32587), TUO de la Ley 27444 (DS 006-2026-JUS), TUO de la Ley Marco de Licencia de Funcionamiento (DS 163-2020-PCM), D.Leg. 1246, Ley 31866 | Vigentes al 10/11/2026 | Corpus del RAG |
| Scraper de El Peruano (INDECOPI, municipalidades) | 01/01/2025 – 10/11/2026 | Semáforo rojo |
| [Listado de INDECOPI de resoluciones con efectos generales](https://www.gob.pe/institucion/indecopi/informes-publicaciones/4292797-listado-de-resoluciones-con-efectos-generales_barreras-burocraticas) | 2017 – 06/11/2026 | Semáforo rojo (complementa al scraper) |

Las dos fuentes de publicaciones tienen **rangos de fechas distintos**; el detalle de cómo se combinan está en [`data/publicaciones/LEEME.md`](data/publicaciones/LEEME.md). Todo es información pública; no hay datos personales.

## Estructura del repo

```
app/              # interfaz en Streamlit
ai/               # prompts, esquemas Pydantic, RAG y la única llamada a Claude (ai/llm.py)
scraper/          # lectura de publicaciones de El Peruano
data/normas/      # textos legales (exportados del SPIJ) y su índice de búsqueda (indice/)
data/publicaciones/  # inaplicaciones con efectos generales publicadas en El Peruano
docs/             # capturas y diagrama
docs/research/    # notas de las 3 conversaciones con usuarios
tests/            # pruebas del semáforo y de la lectura de normas
notebooks/        # exploración
```

## Aviso

TUPA bajo la lupa da **orientación, no asesoría legal**. Los casos complejos deben verse con un abogado.

## Licencia

[MIT](LICENSE)
