from google.adk.agents import Agent

from asistente_rrhh import config

root_agent = Agent(
    name="asistente_rrhh",
    model=config.MODELO,
    instruction="Responde que el asistente está en construcción.",
)
