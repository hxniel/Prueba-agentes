import asyncio
import json
import logging
import re
import time
from typing import Any

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService, Session
from google.genai import types

from app.esquemas import Fuente, Paso, RespuestaChat
from asistente_rrhh.agent import root_agent

NOMBRE_APP = "asistente_rrhh"
TIMEOUT_SEGUNDOS = 60
MAX_DETALLE = 300
TOOLS_CON_FUENTES: frozenset[str] = frozenset({"buscar_politicas", "leer_articulo"})
RESPUESTA_VACIA = "No pude generar una respuesta. Intenta reformular tu pregunta."

logger = logging.getLogger(__name__)

servicio_sesiones = InMemorySessionService()
runner = Runner(agent=root_agent, app_name=NOMBRE_APP, session_service=servicio_sesiones)


class ErrorAgente(Exception):
    """El agente no pudo completar el turno."""


def _truncar(texto: str, limite: int = MAX_DETALLE) -> str:
    return texto if len(texto) <= limite else f"{texto[: limite - 1]}…"


def _json(valor: Any) -> str:
    return json.dumps(valor, ensure_ascii=False, default=str)


def extraer_pasos(evento: Any) -> list[Paso]:
    """Convierte las llamadas y respuestas de tools de un evento en pasos de traza.

    Args:
        evento: Evento de ADK con get_function_calls, get_function_responses y author.
    """
    agente = getattr(evento, "author", None) or "desconocido"
    pasos: list[Paso] = []
    for llamada in evento.get_function_calls() or []:
        argumentos = dict(llamada.args or {})
        if llamada.name == "transfer_to_agent":
            destino = argumentos.get("agent_name", "")
            pasos.append(Paso(agente=agente, tipo="delegacion", detalle=f"{agente} → {destino}"))
        else:
            detalle = _truncar(f"{llamada.name}({_json(argumentos)})")
            pasos.append(Paso(agente=agente, tipo="llamada_tool", detalle=detalle))
    for respuesta in evento.get_function_responses() or []:
        if respuesta.name == "transfer_to_agent":
            continue
        contenido = respuesta.response or {}
        status = contenido.get("status", "sin_status") if isinstance(contenido, dict) else "?"
        detalle = _truncar(f"{respuesta.name} → {status}: {_json(contenido)}")
        pasos.append(Paso(agente=agente, tipo="resultado_tool", detalle=detalle))
    return pasos


def extraer_fuentes(evento: Any) -> list[Fuente]:
    """Obtiene las fuentes citables de las respuestas de las tools de políticas.

    Args:
        evento: Evento de ADK con get_function_responses.
    """
    fuentes: list[Fuente] = []
    for respuesta in evento.get_function_responses() or []:
        contenido = respuesta.response or {}
        if respuesta.name not in TOOLS_CON_FUENTES or not isinstance(contenido, dict):
            continue
        if contenido.get("status") != "ok":
            continue
        registros = contenido.get("resultados") or [contenido]
        for registro in registros:
            fuentes.append(
                Fuente(
                    documento=registro["documento"],
                    politica=registro.get("politica") or registro["documento"],
                    articulo=registro["articulo"],
                    titulo=registro["titulo"],
                )
            )
    return fuentes


def filtrar_fuentes_citadas(fuentes: list[Fuente], respuesta: str) -> list[Fuente]:
    """Conserva solo las fuentes cuya cita aparece en el texto de la respuesta.

    Args:
        fuentes: Fuentes recuperadas por las tools durante el turno.
        respuesta: Texto final del asistente.
    """
    texto = respuesta.casefold()
    return [
        fuente
        for fuente in fuentes
        if re.search(
            rf"{re.escape(fuente.politica.casefold())},\s*artículo\s+{fuente.articulo}\b", texto
        )
    ]


def _texto(evento: Any) -> str:
    contenido = getattr(evento, "content", None)
    partes = getattr(contenido, "parts", None) or []
    return "".join(parte.text for parte in partes if getattr(parte, "text", None)).strip()


async def _obtener_sesion(session_id: str | None, id_empleado: str) -> Session:
    if session_id:
        sesion = await servicio_sesiones.get_session(
            app_name=NOMBRE_APP, user_id=id_empleado, session_id=session_id
        )
        if sesion is not None and sesion.state.get("id_empleado") == id_empleado:
            return sesion
    return await servicio_sesiones.create_session(
        app_name=NOMBRE_APP, user_id=id_empleado, state={"id_empleado": id_empleado}
    )


async def ejecutar_turno(mensaje: str, session_id: str | None, id_empleado: str) -> RespuestaChat:
    """Ejecuta un turno del asistente y devuelve la respuesta con trazas y fuentes.

    Args:
        mensaje: Mensaje del empleado.
        session_id: Sesión previa, o None para iniciar una nueva.
        id_empleado: Empleado autenticado de la demo.
    """
    inicio = time.perf_counter()
    pasos: list[Paso] = []
    fuentes: dict[tuple[str, int], Fuente] = {}
    respuesta = ""
    try:
        sesion = await _obtener_sesion(session_id, id_empleado)
        contenido = types.Content(role="user", parts=[types.Part(text=mensaje)])
        async with asyncio.timeout(TIMEOUT_SEGUNDOS):
            async for evento in runner.run_async(
                user_id=id_empleado, session_id=sesion.id, new_message=contenido
            ):
                pasos.extend(extraer_pasos(evento))
                for fuente in extraer_fuentes(evento):
                    fuentes.setdefault((fuente.documento, fuente.articulo), fuente)
                if evento.is_final_response() and (texto := _texto(evento)):
                    respuesta = texto
                    agente = evento.author or "desconocido"
                    pasos.append(Paso(agente=agente, tipo="respuesta", detalle=_truncar(texto)))
    except Exception as error:
        logger.exception("Fallo del agente en el turno")
        raise ErrorAgente(str(error)) from error

    duracion_ms = int((time.perf_counter() - inicio) * 1000)
    agentes = sorted({paso.agente for paso in pasos})
    tools = [paso.detalle.split("(")[0] for paso in pasos if paso.tipo == "llamada_tool"]
    logger.info(
        "turno session_id=%s agentes=%s tools=%s duracion_ms=%d",
        sesion.id,
        agentes,
        tools,
        duracion_ms,
    )
    return RespuestaChat(
        respuesta=respuesta or RESPUESTA_VACIA,
        session_id=sesion.id,
        pasos=pasos,
        fuentes=filtrar_fuentes_citadas(list(fuentes.values()), respuesta),
        duracion_ms=duracion_ms,
    )
