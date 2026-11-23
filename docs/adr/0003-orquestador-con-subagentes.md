# ADR 0003: Orquestador con dos subagentes especializados

Estado: aceptada

## Contexto

El asistente tiene dos tipos de trabajo con riesgos distintos: responder qué dicen las políticas (solo lectura de documentos) y operar sobre datos del empleado (leer su saldo y escribir tickets en la base de datos). Además debe rechazar lo que no es de RRHH sin gastar tools.

## Opciones consideradas

1. **Un solo agente con las cinco tools.** Más simple y con menos llamadas al LLM, pero un prompt mezcla reglas de citas y de datos personales, y cualquier pregunta tiene acceso a todas las tools.
2. **Orquestador con dos subagentes (`experto_politicas` y `gestor_casos`).** Cada subagente tiene un prompt corto y solo las tools de su función.
3. **Flujo determinista (clasificador + `SequentialAgent` o enrutamiento en código).** Más predecible, pero rígido ante preguntas mixtas o de seguimiento.

## Decisión

Usar un orquestador `asistente_rrhh` (`root_agent`) sin tools, con dos `sub_agents`:

- `experto_politicas`: `buscar_politicas` y `leer_articulo`.
- `gestor_casos`: `consultar_mi_saldo_vacaciones`, `calcular_dias_vacaciones` y `crear_ticket_rrhh`.

ADK agrega `transfer_to_agent` a cada agente; los subagentes pueden transferir al padre y entre sí, por ejemplo el experto transfiere al gestor cuando no encuentra la respuesta.

## Consecuencias

- **Se gana:** separación de permisos (el experto no puede escribir tickets ni leer la base de datos), prompts cortos y enfocados, y trazas legibles que muestran quién hizo qué.
- **Se sacrifica:** más llamadas al LLM por turno (3 medidas en una consulta simple y 5 en una que escala a ticket) y por lo tanto más latencia y tokens que un agente único.
- **Riesgo que queda:** el enrutamiento depende del modelo. Puede delegar al agente equivocado o encadenar transferencias de más. Se mitiga con `description` claras y reglas explícitas en los prompts, pero no hay una prueba automática del enrutamiento real porque las pruebas no llaman al LLM.
