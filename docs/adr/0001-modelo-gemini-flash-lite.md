# ADR 0001: Modelo Gemini Flash-Lite vía Google AI Studio

Estado: aceptada

## Contexto

El asistente hace entre 3 y 5 llamadas al LLM por turno (orquestador, subagente, tools y redacción). Las tareas son acotadas: elegir a qué agente delegar, elegir una tool con argumentos simples y redactar una respuesta breve a partir de datos que ya entregan las tools. La prueba técnica debe funcionar con una API key gratuita y con latencia baja en una demo en vivo.

## Opciones consideradas

1. **Gemini Flash-Lite (`gemini-3.5-flash-lite`) vía AI Studio.** Barato, rápido, con tool calling nativo y capa gratuita.
2. **Gemini Pro.** Mejor razonamiento, pero más lento y caro por turno, y con límites gratuitos más bajos.
3. **Modelo de otro proveedor (OpenAI o Anthropic) a través de LiteLLM en ADK.** Posible, pero suma otra clave, otra dependencia y no aprovecha la integración nativa de ADK con Gemini.
4. **Vertex AI en lugar de AI Studio.** Más control empresarial (IAM, región, cuotas), pero exige proyecto de GCP y credenciales de servicio.

## Decisión

Usar `gemini-3.5-flash-lite` vía Google AI Studio (`GOOGLE_GENAI_USE_VERTEXAI=FALSE`), con temperatura 0.1 y `max_output_tokens=1024` en los tres agentes. El modelo y el de respaldo se configuran en `.env` (`MODELO`, `MODELO_RESPALDO`).

## Consecuencias

- **Se gana:** turnos de 1 a 5 segundos medidos, costo 0 en la capa gratuita y respuestas estables gracias a la temperatura baja. Cambiar de modelo es editar `.env`.
- **Se sacrifica:** capacidad de razonamiento en preguntas ambiguas o de varios pasos; por eso las cifras, cálculos y validaciones se hacen en código y no en el modelo.
- **Riesgo que queda:** durante las pruebas Gemini devolvió `503 UNAVAILABLE` por alta demanda. `MODELO_RESPALDO` está definido en la configuración pero **todavía no se usa**: hoy el error se convierte en un 503 de la API y el usuario reintenta. Falta implementar el cambio automático al modelo de respaldo. Además, ADK avisa que sin `context_cache_config` cada transferencia entre agentes reenvía el prompt completo sin caché.
