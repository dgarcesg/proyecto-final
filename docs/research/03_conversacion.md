# Conversación N.º 3: abogado especialista en barreras burocráticas

Notas de la founder después de la conversación. Sin nombre: la persona aparece con un alias. No es un emprendedor sino un colega de la founder, que asesora en estos casos: por eso varias preguntas de la plantilla no aplican.

- **Fecha:** noviembre de 2026
- **Canal:** *(por completar)*
- **Perfil:** abogado especialista en barreras burocráticas, colega de la founder
- **Distrito:** no aplica
- **Giro del negocio:** no aplica (asesoría legal)
- **¿Aceptó que use sus respuestas (anonimizadas) en el proyecto?:** *(por confirmar)*

## Preguntas

1. **¿Qué te pidieron para la licencia de funcionamiento?** No aplica.
2. **¿Cuánto demoró el trámite?** No aplica.
3. **¿Cuánto pagaste en total?** No aplica.
4. **¿Qué tan difícil es saber si una exigencia ya fue declarada barrera con efectos generales?**
   Confirmó que **no hay una herramienta centralizada** para consultar qué resoluciones ha publicado INDECOPI para que tengan el efecto de inaplicación con efectos generales. **Incluso para un abogado es difícil vincular una resolución colgada en el portal de INDECOPI con su publicación en El Peruano**, así que no se imagina lo difícil que es para un pequeño emprendedor.
5. **¿Te serviría la herramienta?**
   Mostró interés en el **scraper**, justamente para resolver ese vínculo entre el portal de INDECOPI y El Peruano.

## Frases textuales que me llamaron la atención

- No anoté frases textuales.

## Lo que aprendí (y qué cambia en el producto)

- **Lo difícil está en los datos, no solo en el lenguaje legal.** Saber si una exigencia ya no se puede exigir requiere unir dos fuentes: la resolución de INDECOPI y su publicación en El Peruano, que fija desde cuándo opera la inaplicación (numeral 8.3 del artículo 8 del Decreto Legislativo 1256). Es lo que hacen el scraper de El Peruano, el listado de INDECOPI y la revisión de la founder (`scraper/`, `data/publicaciones/`).
- **Si a un especialista le cuesta, para un emprendedor es casi imposible.** Confirma que el usuario final necesita la respuesta ya armada, y no una lista de resoluciones.
- **Puede haber un segundo cliente: abogados y estudios.** Les interesa la base que une cada resolución con su publicación. Por ahora queda como hipótesis; no cambia los planes de precios.
- **La base unida es difícil de copiar:** hoy se arma con el scraper más la revisión de un abogado, medida por medida.
