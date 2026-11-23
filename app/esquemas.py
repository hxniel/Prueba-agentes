from typing import Literal

from pydantic import BaseModel, Field


class SolicitudChat(BaseModel):
    mensaje: str = Field(min_length=1, max_length=1000)
    session_id: str | None = None
    id_empleado: str = Field(pattern=r"^\d{4}$")


class Paso(BaseModel):
    agente: str
    tipo: Literal["delegacion", "llamada_tool", "resultado_tool", "respuesta"]
    detalle: str


class Fuente(BaseModel):
    documento: str
    articulo: int
    titulo: str


class RespuestaChat(BaseModel):
    respuesta: str
    session_id: str
    pasos: list[Paso]
    fuentes: list[Fuente]
    duracion_ms: int


class Empleado(BaseModel):
    id_empleado: str
    nombre: str
