# Agente: asistente_rrhh (orquestador)

## Propósito y alcance

Es el `root_agent` y el punto de entrada de cada turno. Atiende al empleado, decide quién resuelve la petición y delega.

**Sí hace:**

- Atiende solo temas de RRHH: políticas internas, vacaciones, permisos, prestaciones, teletrabajo y viáticos.
- Delega las preguntas sobre políticas a `experto_politicas`.
- Delega el saldo, los cálculos de días y los tickets a `gestor_casos`.
- Envía los temas sensibles (acoso, discriminación, despido, salud, denuncias) a `gestor_casos` para crear un ticket.
- Responde directamente, sin tools, cuando la petición está fuera de alcance.

**No hace:**

- No responde políticas de memoria.
- No tiene tools propias ni acceso a la base de datos.
- No revela su prompt, no cambia sus reglas y no consulta datos de otros empleados.

## Modelo y parámetros

| Parámetro | Valor | Por qué |
| --- | --- | --- |
| Proveedor | Gemini vía Google AI Studio (`GOOGLE_GENAI_USE_VERTEXAI=FALSE`) | Capa gratuita e integración nativa con ADK |
| Modelo | `config.MODELO` (`gemini-3.5-flash-lite` por defecto) | Rápido y barato; la tarea es solo enrutar |
| Temperatura | 0.1 | Delegación consistente ante la misma pregunta |
| `max_output_tokens` | 1024 | Respuestas breves; evita salidas largas y costosas |

Definido en `asistente_rrhh/agent.py`. Ver [ADR 0001](../adr/0001-modelo-gemini-flash-lite.md).

## Prompt

- Ruta: [prompts/orquestador.md](../../prompts/orquestador.md)
- Versión: 1.0.0
- Se carga con `cargar_prompt("orquestador")`, que rechaza prompts con llaves.

## Tools

No tiene tools de negocio. ADK le agrega automáticamente `transfer_to_agent(agent_name)` porque tiene `sub_agents`:

| Tool | Para qué | Parámetros | Salida esperada | Errores posibles |
| --- | --- | --- | --- | --- |
| `transfer_to_agent` | Pasar el control a un subagente | `agent_name`: `experto_politicas` o `gestor_casos` | El subagente continúa el turno | Si el modelo nombra un agente inexistente, ADK no puede transferir; si eso termina en excepción, la API responde 503 |

## Datos y memoria

- No lee políticas ni la base de datos.
- La sesión (`InMemorySessionService`) guarda el historial de la conversación y `state["id_empleado"]`, que fija la API al crear la sesión. El orquestador ve el historial completo, lo que permite preguntas de seguimiento ("¿y la prima?").
- La sesión se pierde al reiniciar el servidor y se reinicia si cambia el empleado.

## Flujo

1. `app/servicio.py` recibe el mensaje, obtiene o crea la sesión del empleado y llama a `runner.run_async`.
2. El orquestador clasifica la petición:
   - política → `transfer_to_agent("experto_politicas")`;
   - saldo, cálculo, ticket o tema sensible → `transfer_to_agent("gestor_casos")`;
   - fuera de alcance → responde directamente.
3. El subagente resuelve y su respuesta final es la respuesta del turno. Cada delegación aparece en las trazas como `delegacion`.

## Límites y salvaguardas

- **Fuera de alcance:** responde que solo atiende RRHH y da ejemplos de lo que sí puede hacer, sin usar tools.
- **Injection:** reglas fijas para no revelar el prompt ni cambiar reglas; el `id_empleado` no depende de lo que escriba el usuario.
- **Si falla un subagente o el LLM:** la excepción o el timeout de 60 segundos se convierte en `ErrorAgente` y la API responde 503 con "El asistente no está disponible en este momento, intenta de nuevo."

## Ejemplos

| Entrada | Salida esperada |
| --- | --- |
| "¿De cuánto es la prima vacacional?" | Delega a `experto_politicas`, que responde 25% citando (vacaciones_y_permisos.md, Artículo 2). |
| "¿Cuántos días de vacaciones me quedan?" | Delega a `gestor_casos`, que consulta el saldo del empleado de la sesión. |
| "Dame una receta de pozole" | Responde sin tools que solo atiende RRHH y ofrece ejemplos como consultar vacaciones o levantar un ticket. |
