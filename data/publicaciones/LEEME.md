# Publicaciones de barreras burocráticas en El Peruano

Esta carpeta alimenta el **semáforo rojo**. Un requisito sale en rojo solo si coincide con una medida de `publicaciones.json` de **esa municipalidad**, que la founder marcó **con efectos generales** y **vigente**, y que ya surte efecto (desde el día siguiente de su publicación, art. 8.3 del D.Leg. 1256). La regla está en [`ai/semaforo.py`](../../ai/semaforo.py).

## Dos fuentes, con rangos de fechas distintos

| Fuente | Rango | Qué trae | Qué no trae |
|---|---|---|---|
| **Scraper de El Peruano** ([`scraper/elperuano.py`](../../scraper/elperuano.py)): búsqueda "barrera burocrática" en [busquedas.elperuano.pe](https://busquedas.elperuano.pe), sector INDECOPI, entidades municipales | **01/01/2025 – 10/11/2026** | Link a El Peruano, tipo de barrera (ilegal / carente de razonabilidad), norma cuestionada, sustento. Incluye comisiones regionales | Resoluciones cuya sumilla no contiene "barrera burocrática" |
| **[Listado de INDECOPI de resoluciones con efectos generales](https://www.gob.pe/institucion/indecopi/informes-publicaciones/4292797-listado-de-resoluciones-con-efectos-generales_barreras-burocraticas)** ([`scraper/listado_indecopi.py`](../../scraper/listado_indecopi.py)), Excel en `fuentes/indecopi/` | **2017 – 06/11/2026** (la última publicación del archivo es del 25/10/2026) | Materia (p. ej., "Licencia de funcionamiento"), número y fecha de publicación | Link a El Peruano, tipo de barrera, norma cuestionada. No incluye las comisiones regionales ni lo publicado después de su corte |

- Si una resolución está en **ambas**, no se duplica: queda la fila del scraper, con la fuente "El Peruano (scraper) y listado INDECOPI" y la materia del listado.
- Para las medidas del listado, **`efectos_generales` = "sí" por defecto**, porque INDECOPI las publica como resoluciones con efectos generales (decisión de la founder). Igual se pueden cambiar.
- El mismo criterio se aplica a las medidas que solo trajo el scraper: **"sí" cuando la pista del texto dice "sí"** (por ejemplo, "sí (art. 8: ilegal)"). Las que dicen "revisar" o "no" quedan vacías para la founder.
- **`usar_en_app` = "sí" en todas** (decisión de la founder del 10/11/2026). La app elige en cada consulta las medidas más parecidas ([`ai/medidas.py`](../../ai/medidas.py)).
- Para el periodo en que se solapan (2025–2026), 45 resoluciones municipales están en ambas fuentes, 8 solo en el listado y 37 solo en el scraper (sobre todo de comisiones regionales y del 08/11/2026).

## Cómo se arma

1. **Scraper** de El Peruano (sin IA: lee los campos rotulados de cada resolución).
2. **Listado INDECOPI**: agrega las medidas que el scraper no trajo.
3. **Revisión de la founder** en Excel: `python -m scraper.excel_revision exportar` genera `publicaciones_para_revisar.xlsx` (filtros, listas desplegables, columnas a llenar en amarillo) e `importar` pasa lo marcado al CSV. Si se vuelven a correr los pasos 1 y 2, **lo ya revisado se conserva**.
4. **Fuera de Lima** ([`scraper/fuera_de_lima.py`](../../scraper/fuera_de_lima.py)): replica el criterio de la founder en las municipalidades que no son de Lima Metropolitana (Callao, Lima Provincias y otros departamentos). Pone el lugar en `distrito_lima` y la nota *"No distrito de Lima, sino [departamento]. Mantener como referencia"*. Esas medidas se quedan como **referencia**: pueden mostrarse como precedente (ámbar), pero **nunca dan rojo**.
5. **Carga** ([`scraper/cargar_revision.py`](../../scraper/cargar_revision.py)): valida las filas marcadas y escribe `publicaciones.json`, que es la tabla que usa la app.

```bash
python -m scraper.elperuano --desde 2025-01-01 --hasta 2026-11-10
python -m scraper.listado_indecopi
python -m scraper.excel_revision exportar    # la founder revisa el .xlsx
python -m scraper.excel_revision importar
python -m scraper.fuera_de_lima
python -m scraper.cargar_revision
```

## Archivos

| Archivo | Qué es |
|---|---|
| `busqueda_elperuano.csv` | Todos los resultados del buscador (cualquier sector) |
| `fuentes/elperuano/<id>.html` | Texto de cada publicación de INDECOPI, tal como lo sirve El Peruano |
| `fuentes/indecopi/4292797-resoluciones-con-efectos-generales.xlsx` | Listado oficial de INDECOPI, tal como se descargó de gob.pe |
| `publicaciones_crudas.json` | Resoluciones que involucran a municipalidades, con sus campos leídos |
| `publicaciones_para_revisar.csv` | Una fila por medida, para la revisión de la founder |
| `publicaciones.json` | La tabla revisada que usa la app |

## Columnas que llena la founder

| Columna | Valores | Para qué |
|---|---|---|
| `efectos_generales` | sí / no | Decisión legal (arts. 8, 9 y 10 del D.Leg. 1256). La columna `efectos_generales_sugerido` es solo una pista |
| `usar_en_app` | sí / no | Si la medida entra a la tabla de la app |
| `estado` | vigente / revocada / entidad_ya_modifico | Si la barrera sigue vigente |
| `distrito_lima` | (corregir si hace falta) | Las pistas automáticas pueden fallar con distritos homónimos |
| `notas` | texto libre | Comentarios de la revisión |

Las columnas `tipo_acto_pista`, `procedimiento_pista` y `efectos_generales_sugerido` las calcula el scraper a partir del texto y **la founder las confirma**.
