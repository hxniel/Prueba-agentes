from collections.abc import Iterator
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app import servicio
from app.esquemas import Fuente, Paso, RespuestaChat
from app.main import MENSAJE_NO_DISPONIBLE, app
from asistente_rrhh import config


@pytest.fixture
def cliente(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setattr(config, "RUTA_BD", tmp_path / "rrhh.db")
    with TestClient(app) as cliente_prueba:
        yield cliente_prueba


def _evento(
    author: str = "experto_politicas",
    llamadas: list[Any] | None = None,
    respuestas: list[Any] | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        author=author,
        get_function_calls=lambda: llamadas or [],
        get_function_responses=lambda: respuestas or [],
    )


def test_chat_respuesta_valida(cliente: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    recibido: dict[str, Any] = {}

    async def falso(mensaje: str, session_id: str | None, id_empleado: str) -> RespuestaChat:
        recibido.update(mensaje=mensaje, session_id=session_id, id_empleado=id_empleado)
        return RespuestaChat(
            respuesta="La prima vacacional es del 25%.",
            session_id="s-1",
            pasos=[Paso(agente="asistente_rrhh", tipo="respuesta", detalle="ok")],
            fuentes=[
                Fuente(
                    documento="vacaciones_y_permisos.md",
                    politica="Política de Vacaciones y Permisos",
                    articulo=2,
                    titulo="Prima vacacional",
                )
            ],
            duracion_ms=12,
        )

    monkeypatch.setattr(servicio, "ejecutar_turno", falso)
    respuesta = cliente.post(
        "/api/chat", json={"mensaje": "prima vacacional", "id_empleado": "1001"}
    )
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["session_id"] == "s-1"
    assert cuerpo["fuentes"][0]["articulo"] == 2
    assert recibido == {"mensaje": "prima vacacional", "session_id": None, "id_empleado": "1001"}


@pytest.mark.parametrize(
    "cuerpo",
    [
        {"mensaje": "hola", "id_empleado": "abc"},
        {"mensaje": "hola", "id_empleado": "10011"},
        {"mensaje": "hola"},
        {"mensaje": "", "id_empleado": "1001"},
        {"mensaje": "x" * 1001, "id_empleado": "1001"},
    ],
)
def test_chat_422_con_datos_invalidos(cliente: TestClient, cuerpo: dict[str, Any]) -> None:
    assert cliente.post("/api/chat", json=cuerpo).status_code == 422


def test_chat_503_ante_error_del_agente(
    cliente: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def falla(mensaje: str, session_id: str | None, id_empleado: str) -> RespuestaChat:
        raise servicio.ErrorAgente("timeout")

    monkeypatch.setattr(servicio, "ejecutar_turno", falla)
    respuesta = cliente.post("/api/chat", json={"mensaje": "hola", "id_empleado": "1001"})
    assert respuesta.status_code == 503
    assert respuesta.json() == {"detail": MENSAJE_NO_DISPONIBLE}


def test_empleados(cliente: TestClient) -> None:
    respuesta = cliente.get("/api/empleados")
    assert respuesta.status_code == 200
    empleados = respuesta.json()
    assert [e["id_empleado"] for e in empleados] == ["1001", "1002", "1003", "1004", "1005"]
    assert set(empleados[0]) == {"id_empleado", "nombre"}


def test_salud(cliente: TestClient) -> None:
    assert cliente.get("/api/salud").json() == {"status": "ok"}


def test_extraer_pasos_delegacion() -> None:
    llamada = SimpleNamespace(name="transfer_to_agent", args={"agent_name": "gestor_casos"})
    respuesta = SimpleNamespace(name="transfer_to_agent", response={"result": None})
    pasos = servicio.extraer_pasos(_evento("asistente_rrhh", [llamada], [respuesta]))
    assert pasos == [
        Paso(agente="asistente_rrhh", tipo="delegacion", detalle="asistente_rrhh → gestor_casos")
    ]


def test_extraer_pasos_llamada_tool_trunca_argumentos() -> None:
    llamada = SimpleNamespace(name="buscar_politicas", args={"consulta": "x" * 500})
    pasos = servicio.extraer_pasos(_evento(llamadas=[llamada]))
    assert len(pasos) == 1
    assert pasos[0].tipo == "llamada_tool"
    assert pasos[0].detalle.startswith('buscar_politicas({"consulta": "xxx')
    assert len(pasos[0].detalle) <= servicio.MAX_DETALLE


def test_extraer_pasos_resultado_tool_con_status() -> None:
    respuesta = SimpleNamespace(
        name="buscar_politicas", response={"status": "sin_resultados", "mensaje": "escalar"}
    )
    pasos = servicio.extraer_pasos(_evento(respuestas=[respuesta]))
    assert pasos[0].tipo == "resultado_tool"
    assert pasos[0].detalle.startswith("buscar_politicas → sin_resultados")


def test_extraer_pasos_evento_sin_llamadas() -> None:
    assert servicio.extraer_pasos(_evento()) == []


def test_extraer_fuentes_de_buscar_y_leer() -> None:
    resultado = {
        "documento": "viaticos.md",
        "politica": "Política de Viáticos",
        "articulo": 1,
        "titulo": "Topes diarios",
    }
    busqueda = {"status": "ok", "resultados": [resultado]}
    respuestas = [
        SimpleNamespace(name="buscar_politicas", response=busqueda),
        SimpleNamespace(name="leer_articulo", response={"status": "ok", **resultado}),
        SimpleNamespace(name="crear_ticket_rrhh", response={"status": "ok", "folio": "RH-1"}),
        SimpleNamespace(name="leer_articulo", response={"status": "error", "mensaje": "x"}),
    ]
    fuentes = servicio.extraer_fuentes(_evento(respuestas=respuestas))
    assert fuentes == [Fuente(**resultado), Fuente(**resultado)]


def _fuente(politica: str, articulo: int) -> Fuente:
    return Fuente(documento="x.md", politica=politica, articulo=articulo, titulo="t")


def test_filtrar_fuentes_conserva_solo_las_citadas() -> None:
    viaticos = _fuente("Política de Viáticos", 1)
    teletrabajo = _fuente("Política de Teletrabajo", 3)
    respuesta = "Los topes son 1,800 y 600 pesos (Política de Viáticos, artículo 1)."
    assert servicio.filtrar_fuentes_citadas([viaticos, teletrabajo], respuesta) == [viaticos]


def test_filtrar_fuentes_sin_citas_regresa_vacio() -> None:
    respuesta = "No hay información sobre guardería. Creé el ticket RH-2026-0002."
    fuentes = [_fuente("Política de Teletrabajo", 3)]
    assert servicio.filtrar_fuentes_citadas(fuentes, respuesta) == []


def test_filtrar_fuentes_ignora_mayusculas_y_no_confunde_numeros() -> None:
    articulo_1 = _fuente("Política de Prestaciones", 1)
    articulo_2 = _fuente("Política de Prestaciones", 2)
    respuesta = "Ver (política de prestaciones, Artículo 1) y el artículo 12 de otra norma."
    assert servicio.filtrar_fuentes_citadas([articulo_1, articulo_2], respuesta) == [articulo_1]
