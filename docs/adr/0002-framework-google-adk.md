# ADR 0002: Framework de agentes Google ADK

Estado: aceptada

## Contexto

Se necesita un asistente con varios agentes que delegan entre sí, tools en Python que leen datos locales, sesiones con estado por empleado y trazas de cada paso para mostrarlas en la interfaz. El stack de la prueba es Gemini.

## Opciones consideradas

1. **Google ADK 2.x.** Integración nativa con Gemini, agentes con `sub_agents` y transferencia automática (`transfer_to_agent`), tools como funciones Python con `ToolContext`, `Runner` con servicio de sesiones y eventos que exponen llamadas y respuestas de tools. Incluye `adk web` para depurar.
2. **LangGraph.** Muy flexible para grafos explícitos, pero hay que modelar a mano el enrutamiento y el estado, y su integración con Gemini pasa por LangChain.
3. **SDK `google-genai` directo con un bucle propio de function calling.** Control total y menos dependencias, pero habría que reimplementar sesiones, delegación entre agentes y trazas.

## Decisión

Usar Google ADK 2.x (`google-adk==2.15.0`). Los agentes se definen con `Agent` en `asistente_rrhh/agent.py`, las tools son funciones en `asistente_rrhh/herramientas.py` y la API ejecuta los turnos con `Runner` e `InMemorySessionService` en `app/servicio.py`.

## Consecuencias

- **Se gana:** delegación entre agentes sin código de enrutamiento, `id_empleado` en `tool_context.state` para que el modelo nunca lo controle, eventos con `get_function_calls()` y `get_function_responses()` para construir las trazas, y `adk web` para depurar.
- **Se sacrifica:** control fino del enrutamiento, que queda en manos del modelo guiado por las `description` y los prompts. ADK interpreta las llaves de las instrucciones como variables de estado, así que los prompts no pueden llevar llaves (`cargar_prompt` lo valida).
- **Riesgo que queda:** ADK evoluciona rápido y su API cambia entre versiones; por eso las versiones están fijadas en `requirements.txt` y se revisa la API instalada antes de usarla.
