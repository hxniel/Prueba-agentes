# Diseño

```
Empleado → static/index.html (chat + "Pensando…" + trazas + fuentes)
  → POST /api/chat {mensaje, session_id, id_empleado} → app/main.py (FastAPI + Pydantic)
  → InMemorySessionService state={"id_empleado"} → Runner (google-adk)
  → asistente_rrhh [orquestador, root_agent, prompts/orquestador.md]
     ├─ experto_politicas [prompts/experto_politicas.md]
     │    ├ buscar_politicas(consulta) → BM25 sobre data/politicas/*.md
     │    └ leer_articulo(documento, articulo) → texto exacto + cita
     └─ gestor_casos [prompts/gestor_casos.md]
          ├ consultar_mi_saldo_vacaciones() → data/rrhh.db (id_empleado desde ToolContext)
          ├ calcular_dias_vacaciones(anios_cumplidos) → tabla LFT art. 76
          └ crear_ticket_rrhh(tema, resumen) → data/rrhh.db (folio)
  → Gemini (gemini-3.5-flash-lite, temperatura 0.1)
```

- **El código decide y el LLM redacta:** los datos, los cálculos y las citas salen de tools deterministas; el modelo solo elige la tool y redacta la respuesta con lo que recibe.
- **Umbral de BM25 que obliga a escalar:** si ningún resultado de `buscar_politicas` supera `UMBRAL_BM25`, la tool devuelve `sin_resultados` y el agente ofrece crear un ticket en lugar de inventar.
- **Separación de permisos entre agentes:** `experto_politicas` solo lee políticas y `gestor_casos` es el único que accede a `data/rrhh.db`; cada uno ve únicamente sus tools.
- **Defensas contra prompt injection:** el `id_empleado` viene del estado de sesión vía `ToolContext` y nunca del mensaje, las tools validan cada argumento y los prompts tratan el texto del usuario y de las políticas como datos, no como instrucciones.
- **Trazas visibles:** la interfaz muestra qué agente respondió, qué tools se llamaron y las fuentes citadas, para auditar cada respuesta.
