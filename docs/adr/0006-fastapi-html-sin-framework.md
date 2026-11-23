# ADR 0006: API con FastAPI e interfaz HTML sin framework

Estado: aceptada

## Contexto

Se necesita una API para conversar con el asistente y una interfaz que un empleado use sin explicación técnica, que muestre fuentes y trazas. La demo debe arrancar con un solo proceso y sin paso de compilación.

## Opciones consideradas

1. **FastAPI + Pydantic con un solo `static/index.html` (HTML, CSS y JS sin frameworks).** Un proceso, validación declarativa y sin `node_modules`.
2. **FastAPI + React o Vue.** Mejor para una interfaz grande, pero agrega Node, un build y un segundo proceso en desarrollo.
3. **Streamlit o Gradio.** Interfaz rápida en Python, pero menos control del diseño, del manejo de errores y del panel de trazas, y la API REST queda en segundo plano.
4. **Solo `adk web`.** Útil para depurar, pero no es una interfaz para empleados y no inyecta `id_empleado` en la sesión.

## Decisión

- **API:** FastAPI en `app/main.py` con `POST /api/chat`, `GET /api/empleados`, `GET /api/salud` y `GET /`. Esquemas Pydantic en `app/esquemas.py`: `id_empleado` con patrón `^\d{4}$` y mensaje de 1 a 1000 caracteres (422 si no se cumple). `ErrorAgente` se traduce a 503 con un mensaje claro. El turno corre con un límite de 60 segundos.
- **Interfaz:** un solo `static/index.html` servido con `FileResponse`. Escapa siempre la respuesta antes de convertir negritas y saltos de línea, guarda `session_id` en una variable de JS (sin `localStorage`) y muestra fuentes, duración y trazas por turno.

## Consecuencias

- **Se gana:** se arranca con `./iniciar.sh`, el contrato de la API está tipado y probado con `TestClient`, y la interfaz no tiene dependencias.
- **Se sacrifica:** escalabilidad del frontend; si la interfaz crece, un solo archivo se vuelve difícil de mantener.
- **Riesgo que queda:** el selector de empleado es solo para la demo; cualquiera puede elegir otro empleado. En producción el `id_empleado` vendría de autenticación real (SSO o token firmado) y no del cuerpo de la petición.
