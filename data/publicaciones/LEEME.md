# Publicaciones de inaplicación con efectos generales

Esta carpeta alimenta el **semáforo rojo**. La app pinta un requisito de rojo solo si aquí hay una publicación en El Peruano para **esa municipalidad y esa medida**, y si ya surte efecto según su fecha. El LLM no decide el rojo: lo decide el código contra esta tabla.

## Qué poner aquí

1. **Los archivos tal cual los descargaste** (PDF o HTML de El Peruano) en `fuentes/`.
2. **Los links de El Peruano**, uno por línea, en `urls.txt` (si los tienes).

Con eso, la ingesta arma `publicaciones.json`, y **la founder la revisa a mano antes de usarla**.

## Datos que necesita cada caso

| Campo | Ejemplo |
|---|---|
| Número de resolución | `0XXX-2026/CEB-INDECOPI` |
| Órgano | CEB o Sala (SEL) |
| Municipalidad | Municipalidad Distrital de ... |
| Tipo de acto | disposición administrativa o actuación material |
| Norma cuestionada | ordenanza, TUPA, artículo |
| Medida declarada barrera | qué exigencia se declaró barrera |
| Tipo | ilegal o carente de razonabilidad |
| Fecha de publicación en El Peruano | dd/mm/aaaa |
| URL en El Peruano | `https://busquedas.elperuano.pe/dispositivo/NL/...` |
| Estado | vigente, revocada o la entidad ya modificó |

Solo casos de **licencia de funcionamiento** en municipalidades de **Lima**.
