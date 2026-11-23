# asistente-rrhh

Asistente de RRHH construido con Google ADK que responde preguntas de empleados sobre las políticas internas citando el artículo exacto, consulta el saldo de vacaciones del empleado y escala a RRHH con un ticket cuando no sabe la respuesta.

## Stack

- Python 3.12 (`/opt/homebrew/bin/python3.12`) con entorno virtual en `.venv`.
- `google-adk` 2.x.
- Gemini vía Google AI Studio: `GOOGLE_API_KEY` y `GOOGLE_GENAI_USE_VERTEXAI=FALSE`.
- Modelos configurados por `.env`: `MODELO=gemini-3.5-flash-lite` y `MODELO_RESPALDO=gemini-3.1-flash-lite`.
- API con FastAPI + Pydantic.
- Interfaz: un solo `static/index.html` con HTML + JS sin frameworks.
- Persistencia: SQLite con `sqlite3` de la librería estándar.
- RAG con `rank-bm25`.
- Pruebas con `pytest`; lint y formato con `ruff`.

## Código

- Type hints en todas las funciones.
- Sin comentarios innecesarios; la documentación va en Markdown.
- Tools del agente:
  - Funciones con type hints y docstring corto (qué hace y `Args`).
  - Retornan un `dict` con `"status"`: `"ok"`, `"sin_resultados"` o `"error"`.
  - Nunca lanzan excepciones.
  - Validan todo lo que manda el modelo.
- Los system prompts viven en `prompts/*.md` con su versión, nunca dentro del código.
- Prohibido usar llaves en los prompts (ADK las interpreta como variables de estado).
- Rutas con `pathlib`, resueltas desde la raíz del proyecto.
- Las rutas de configuración se leen en tiempo de ejecución para poder parcharlas en pruebas.
- Secretos solo en `.env`.
- Las pruebas nunca llaman al LLM.

## Git (Gitflow + Conventional Commits)

- Nunca hacer commit ni push a `main` ni a `develop`.
- Cada cambio va en una rama `<tipo>/<descripcion-corta>` que sale de `develop` actualizada.
- Commits pequeños, uno por cambio lógico, con formato `tipo(alcance): descripcion`.
- Alcance obligatorio y en minúsculas: `agente`, `tools`, `rag`, `api`, `ui`, `datos`, `docs`, `deps`, `config`, `test`, `repo`.
- Descripción en español, en minúscula y en presente.
- Encabezado de máximo 100 caracteres.
- Tipos válidos: `feat`, `fix`, `hotfix`, `chore`, `docs`, `refactor`, `test`, `perf`, `ci`, `build`, `style`.
- Al terminar cada cambio se entregan los comandos git listos para copiar, con título en formato Conventional Commits.
