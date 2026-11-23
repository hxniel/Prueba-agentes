from pathlib import Path

import pytest
from google.adk.agents import Agent

from asistente_rrhh import config
from asistente_rrhh.agent import experto_politicas, gestor_casos, root_agent
from asistente_rrhh.prompts import cargar_prompt

AGENTES: list[Agent] = [root_agent, experto_politicas, gestor_casos]


def _nombres_tools(agente: Agent) -> set[str]:
    return {tool.__name__ for tool in agente.tools}


def test_nombres_de_los_agentes() -> None:
    assert [a.name for a in AGENTES] == ["asistente_rrhh", "experto_politicas", "gestor_casos"]


def test_sub_agentes_del_orquestador() -> None:
    assert [a.name for a in root_agent.sub_agents] == ["experto_politicas", "gestor_casos"]
    assert experto_politicas.sub_agents == []
    assert gestor_casos.sub_agents == []


def test_tools_de_cada_agente() -> None:
    assert root_agent.tools == []
    assert _nombres_tools(experto_politicas) == {"buscar_politicas", "leer_articulo"}
    assert _nombres_tools(gestor_casos) == {
        "consultar_mi_saldo_vacaciones",
        "calcular_dias_vacaciones",
        "crear_ticket_rrhh",
    }


@pytest.mark.parametrize("agente", AGENTES, ids=lambda a: a.name)
def test_configuracion_del_modelo(agente: Agent) -> None:
    assert agente.model == config.MODELO
    assert agente.generate_content_config.temperature == 0.1
    assert agente.generate_content_config.max_output_tokens == 1024
    assert agente.description


@pytest.mark.parametrize("nombre", ["orquestador", "experto_politicas", "gestor_casos"])
def test_prompts_cargan_sin_llaves(nombre: str) -> None:
    texto = cargar_prompt(nombre)
    assert texto.startswith("Versión: 1.0.0")
    assert "{" not in texto and "}" not in texto


def test_cargar_prompt_rechaza_llaves(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / "prompts").mkdir()
    (tmp_path / "prompts" / "malo.md").write_text("Hola {usuario}", encoding="utf-8")
    monkeypatch.setattr(config, "RAIZ", tmp_path)
    with pytest.raises(ValueError):
        cargar_prompt("malo")
