from google.adk.agents import Agent
from google.genai import types

from asistente_rrhh import config
from asistente_rrhh.herramientas import (
    buscar_politicas,
    calcular_dias_vacaciones,
    consultar_mi_saldo_vacaciones,
    crear_ticket_rrhh,
    leer_articulo,
)
from asistente_rrhh.prompts import cargar_prompt


def _configuracion() -> types.GenerateContentConfig:
    return types.GenerateContentConfig(temperature=0.1, max_output_tokens=1024)


experto_politicas = Agent(
    name="experto_politicas",
    model=config.MODELO,
    description=(
        "Responde qué dicen las políticas internas de RRHH (reglamento, vacaciones, permisos, "
        "prestaciones, teletrabajo y viáticos) citando el documento y el artículo exacto."
    ),
    instruction=cargar_prompt("experto_politicas"),
    tools=[buscar_politicas, leer_articulo],
    generate_content_config=_configuracion(),
)

gestor_casos = Agent(
    name="gestor_casos",
    model=config.MODELO,
    description=(
        "Consulta el saldo de vacaciones del empleado de la sesión, calcula días por "
        "antigüedad y crea tickets para RRHH en temas sensibles o sin respuesta en políticas."
    ),
    instruction=cargar_prompt("gestor_casos"),
    tools=[consultar_mi_saldo_vacaciones, calcular_dias_vacaciones, crear_ticket_rrhh],
    generate_content_config=_configuracion(),
)

root_agent = Agent(
    name="asistente_rrhh",
    model=config.MODELO,
    description=(
        "Orquestador del asistente de RRHH: atiende al empleado y delega en el experto de "
        "políticas o en el gestor de casos."
    ),
    instruction=cargar_prompt("orquestador"),
    sub_agents=[experto_politicas, gestor_casos],
    generate_content_config=_configuracion(),
)
