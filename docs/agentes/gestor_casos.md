# Agente: gestor_casos

## Propósito y alcance

Opera sobre los datos del empleado de la sesión: saldo de vacaciones, cálculo de días por antigüedad y tickets para RRHH.

**Sí hace:**

- Consulta el saldo de vacaciones del empleado de la sesión.
- Calcula los días que corresponden por años cumplidos según el artículo 76 de la LFT.
- Crea tickets cuando la información no está en las políticas, el tema es sensible o el empleado lo pide.

**No hace:**

- No consulta ni comparte datos de otros empleados.
- No responde qué dicen las políticas: transfiere a `experto_politicas`.
- No inventa cifras, fechas ni folios.

## Modelo y parámetros

| Parámetro | Valor | Por qué |
| --- | --- | --- |
| Proveedor | Gemini vía Google AI Studio | Capa gratuita e integración nativa con ADK |
| Modelo | `config.MODELO` (`gemini-3.5-flash-lite` por defecto) | Las cifras salen de las tools; el modelo solo elige la tool y redacta |
| Temperatura | 0.1 | Elección de tool y redacción consistentes |
| `max_output_tokens` | 1024 | Respuestas breves con folio o saldo |

## Prompt

- Ruta: [prompts/gestor_casos.md](../../prompts/gestor_casos.md)
- Versión: 1.0.0

## Tools

### `consultar_mi_saldo_vacaciones(tool_context: ToolContext)`

- **Para qué:** saldo del empleado de la sesión.
- **Parámetros:** ninguno controlado por el modelo; `id_empleado` se toma de `tool_context.state`.
- **Salida `ok`:** `id_empleado`, `nombre`, `fecha_ingreso`, `anios_cumplidos`, `dias_corresponden`, `dias_tomados`, `dias_disponibles`, `proximo_aniversario` y `fuente` ("LFT art. 76"). La lógica de fechas está en la función pura `calcular_saldo(fecha_ingreso, dias_tomados, hoy)`.
- **Errores:** "No hay un empleado identificado en la sesión.", "No existe el empleado N." y "No se pudo consultar el saldo de vacaciones."

### `calcular_dias_vacaciones(anios_cumplidos: int)`

- **Para qué:** días que corresponden por antigüedad.
- **Parámetros:** `anios_cumplidos`, entero de 0 a 60.
- **Salida `ok`:** `anios_cumplidos`, `dias` y `fuente`. Tabla: 1→12, 2→14, 3→16, 4→18, 5→20, 6-10→22 y +2 días por cada bloque de 5 años. Con 0 devuelve `dias: 0` y el mensaje "Aún no cumple un año de servicio; las vacaciones se generan al cumplirlo."
- **Errores:** "Los años cumplidos deben ser un número entero.", "Los años cumplidos deben estar entre 0 y 60." y "No se pudo calcular los días de vacaciones."

### `crear_ticket_rrhh(tema: str, resumen: str, tool_context: ToolContext)`

- **Para qué:** escalar un caso a RRHH.
- **Parámetros:** `tema`, uno de `vacaciones`, `permisos`, `nomina`, `prestaciones`, `teletrabajo`, `viaticos`, `conducta` u `otro`; `resumen`, de 10 a 500 caracteres. `id_empleado` sale de la sesión.
- **Salida `ok`:** `folio` con formato `RH-AAAA-NNNN` (consecutivo por año), `tema` y `mensaje` "RRHH responderá en un máximo de 2 días hábiles." El ticket se guarda con estado `abierto`.
- **Errores:** "No hay un empleado identificado en la sesión.", "Tema no válido. Opciones: ...", "El resumen debe tener entre 10 y 500 caracteres." y "No se pudo crear el ticket."

## Datos y memoria

- **Fuentes:** `data/rrhh.db` (SQLite), tablas `empleados` y `tickets`. Ver [ADR 0005](../adr/0005-sqlite.md).
- **Sesión:** lee `state["id_empleado"]`, que fija la API al crear la sesión; nunca lo escribe.

## Flujo

1. Recibe el control del orquestador o de `experto_politicas`.
2. Según la petición:
   - saldo → `consultar_mi_saldo_vacaciones`;
   - "cuántos días me tocan con N años" → `calcular_dias_vacaciones`;
   - sin respuesta en políticas, tema sensible o petición explícita → `crear_ticket_rrhh`.
3. Responde con los datos de la tool: saldo, días con su fuente, o folio y tiempo de respuesta.
4. Si la pregunta es sobre lo que dice una política, transfiere a `experto_politicas`.

## Límites y salvaguardas

- **Otros empleados:** la tool no acepta un id como argumento, así que aunque el modelo quisiera no podría consultar a otro empleado; el prompt además le pide rechazar la petición.
- **Datos mínimos:** el resumen del ticket no debe incluir información innecesaria.
- **Si falla una tool:** explica el problema en pocas palabras y no inventa el resultado. Por ejemplo, en `adk web` no hay `id_empleado` y responde que no hay un empleado identificado.
- **Comportamiento a revisar:** crea el ticket en cuanto detecta que la información no está en las políticas, sin pedir confirmación al empleado.

## Ejemplos

| Entrada | Salida esperada |
| --- | --- |
| "¿Cuántos días de vacaciones me quedan?" (empleado 1002) | `consultar_mi_saldo_vacaciones` → 3 años cumplidos, 16 días, 10 tomados, 6 disponibles, próximo aniversario 2027-03-01 (LFT art. 76). |
| "¿Cuántos días me tocan con 3 años?" | `calcular_dias_vacaciones(3)` → 16 días según LFT art. 76. |
| "¿Hay apoyo para guardería?" (tras `sin_resultados`) | `crear_ticket_rrhh("otro", ...)` → folio `RH-2026-0001` y "RRHH responderá en un máximo de 2 días hábiles." |
