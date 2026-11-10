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

## Fuentes de datos

| Fuente | Rango | Para qué |
|---|---|---|
| Normas en `data/normas/` (exportadas del SPIJ): D.Leg. 1256 (con la Ley 32587), TUO de la Ley 27444 (DS 006-2026-JUS), TUO de la Ley Marco de Licencia de Funcionamiento (DS 163-2020-PCM), Ley 31866 | Vigentes al 10/11/2026 | Corpus del RAG |
| Scraper de El Peruano (INDECOPI, municipalidades) | 01/01/2025 – 10/11/2026 | Semáforo rojo |
| [Listado de INDECOPI de resoluciones con efectos generales](https://www.gob.pe/institucion/indecopi/informes-publicaciones/4292797-listado-de-resoluciones-con-efectos-generales_barreras-burocraticas) | 2017 – 06/11/2026 | Semáforo rojo (complementa al scraper) |

Las dos fuentes de publicaciones tienen **rangos de fechas distintos**; el detalle de cómo se combinan está en [`data/publicaciones/LEEME.md`](data/publicaciones/LEEME.md). Todo es información pública; no hay datos personales.

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
