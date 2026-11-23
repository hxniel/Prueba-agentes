import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse

from app import servicio
from app.esquemas import Empleado, RespuestaChat, SolicitudChat
from asistente_rrhh import config
from asistente_rrhh.db import conectar, inicializar_bd

MENSAJE_NO_DISPONIBLE = "El asistente no está disponible en este momento, intenta de nuevo."
HTML_PROVISIONAL = (
    "<!doctype html><html lang=\"es\"><head><meta charset=\"utf-8\">"
    "<title>Asistente de RRHH</title></head><body><h1>Asistente de RRHH</h1></body></html>"
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    if not config.RUTA_BD.exists():
        inicializar_bd()
    yield


app = FastAPI(title="Asistente de RRHH", lifespan=lifespan)


@app.exception_handler(servicio.ErrorAgente)
async def manejar_error_agente(_: Request, __: Exception) -> JSONResponse:
    return JSONResponse(status_code=503, content={"detail": MENSAJE_NO_DISPONIBLE})


@app.post("/api/chat")
async def chat(solicitud: SolicitudChat) -> RespuestaChat:
    return await servicio.ejecutar_turno(
        solicitud.mensaje, solicitud.session_id, solicitud.id_empleado
    )


@app.get("/api/empleados")
def empleados() -> list[Empleado]:
    conexion = conectar()
    filas = conexion.execute(
        "SELECT id_empleado, nombre FROM empleados ORDER BY id_empleado"
    ).fetchall()
    conexion.close()
    return [Empleado(id_empleado=fila["id_empleado"], nombre=fila["nombre"]) for fila in filas]


@app.get("/api/salud")
def salud() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/", include_in_schema=False)
def inicio() -> FileResponse:
    ruta = config.RAIZ / "static" / "index.html"
    if not ruta.exists():
        ruta.parent.mkdir(parents=True, exist_ok=True)
        ruta.write_text(HTML_PROVISIONAL, encoding="utf-8")
    return FileResponse(ruta)
