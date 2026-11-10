# Arquitectura de TUPA bajo la lupa

```mermaid
flowchart TD
    U["Emprendedor: nota de voz o texto"] --> W["Whisper small, en el servidor<br/>ai/voz.py (el audio no se guarda)"]
    U -.->|"o escribe"| T
    W --> T["Texto que la persona puede corregir<br/>app/app.py"]
    T --> A["Anonimiza DNI, RUC, teléfonos y correos<br/>ai/llm.py"]
    A --> X["Claude Opus 5.5: distrito, giro y requisitos<br/>salida estructurada · ai/prompts.py"]
    X --> R["Buscador de normas (RAG)<br/>e5-small + ChromaDB · ai/rag.py"]
    X --> M["Medidas publicadas más parecidas<br/>e5-small · ai/medidas.py"]
    R --> E["Claude Opus 5.5: evalúa cada requisito y cita la norma<br/>ai/analisis.py"]
    M --> E
    E --> V["Comprueba cada cita palabra por palabra<br/>ai/citas.py"]
    E --> S["Regla del rojo, sin IA: art. 8.3 del D.Leg. 1256<br/>ai/semaforo.py + textos fijos ai/textos.py"]
    V --> P["Semáforo por requisito con su base legal"]
    S --> P
    P -->|"si hay rojo"| PDF["Escrito en PDF para mesa de partes<br/>ai/escrito.py"]

    subgraph DATOS["Datos públicos (se preparan antes, sin IA)"]
        N["SPIJ: 5 normas<br/>data/normas/"]
        EP["Scraper de El Peruano<br/>scraper/elperuano.py"]
        LI["Listado de INDECOPI con efectos generales<br/>scraper/listado_indecopi.py"]
        RF["Revisión de la founder<br/>publicaciones_para_revisar.csv"]
    end
    N --> R
    EP --> RF
    LI --> RF
    RF --> M
    RF --> S
```

## Cómo leerlo

1. **Voz a texto.** Whisper (`small`, int8) corre en el mismo servidor de la app: el audio no se envía a otro servicio y no se guarda. La persona ve el texto y puede corregirlo.
2. **Extracción.** Antes de enviar el texto a Claude, el código reemplaza DNI, RUC, teléfonos y correos. Claude devuelve, en un esquema fijo (Pydantic), el distrito, el giro y la lista de requisitos.
3. **Búsqueda.** Para cada requisito, el buscador trae los artículos más parecidos de las 5 normas (468 fragmentos) y las medidas publicadas más parecidas: 5 del distrito de la persona y 3 de otras municipalidades.
4. **Evaluación.** Claude evalúa cada requisito, solo como ámbar o verde, citando la norma y copiando la frase exacta. El código comprueba que esa frase esté palabra por palabra en el artículo citado; si no está, la cita no se muestra.
5. **Rojo.** El rojo no lo decide la IA. Sale solo si el requisito coincide con una medida de **ese distrito** que INDECOPI declaró barrera burocrática **con efectos generales**, publicada en El Peruano y vigente, y desde el día siguiente de su publicación (art. 8.3 del D.Leg. 1256). Los textos del rojo y de los precedentes son fijos, redactados por la founder.
6. **Escrito.** Si hay algún rojo, la app arma un escrito en PDF con la resolución, el art. 8.3 y el numeral 34.1 del D.Leg. 1256 (multa al funcionario que incumple el mandato de inaplicación). La persona llena a mano su nombre, DNI y domicilio.
