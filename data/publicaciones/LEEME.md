# Publicaciones de barreras burocráticas en El Peruano

Esta carpeta alimenta el **semáforo rojo**. Un requisito sale en rojo solo si coincide con una medida de `publicaciones.json` de **esa municipalidad**, que la founder marcó **con efectos generales** y **vigente**, y que ya surte efecto (desde el día siguiente de su publicación, art. 8.3 del D.Leg. 1256). La regla está en [`ai/semaforo.py`](../../ai/semaforo.py).

## Cómo se arma

1. **Scraper** ([`scraper/elperuano.py`](../../scraper/elperuano.py)): busca "barrera burocrática" en [busquedas.elperuano.pe](https://busquedas.elperuano.pe) del 01/01/2025 al 10/11/2026, se queda con lo publicado por INDECOPI que involucra a una municipalidad y lee los campos rotulados de cada resolución. No usa IA.
2. **Revisión de la founder**: abre `publicaciones_para_revisar.csv` en Excel y llena las columnas de la derecha.
3. **Carga** ([`scraper/cargar_revision.py`](../../scraper/cargar_revision.py)): valida las filas marcadas y escribe `publicaciones.json`, que es la tabla que usa la app.

```bash
python -m scraper.elperuano --desde 2025-01-01 --hasta 2026-11-10
python -m scraper.cargar_revision
```

## Archivos

| Archivo | Qué es |
|---|---|
| `busqueda_elperuano.csv` | Todos los resultados del buscador (cualquier sector) |
| `fuentes/elperuano/<id>.html` | Texto de cada publicación de INDECOPI, tal como lo sirve El Peruano |
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
