import re
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from asistente_rrhh import config
from asistente_rrhh import herramientas as h
from asistente_rrhh.db import conectar


@pytest.fixture(autouse=True)
def entorno(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config, "RUTA_BD", tmp_path / "rrhh.db")
    monkeypatch.setattr(config, "UMBRAL_BM25", config.UMBRAL_BM25_POR_DEFECTO)


@pytest.fixture
def contexto() -> Any:
    return SimpleNamespace(state={"id_empleado": "1001"})


def test_buscar_politicas_con_resultados() -> None:
    respuesta = h.buscar_politicas("de cuanto es la prima vacacional")
    assert respuesta["status"] == "ok"
    primero = respuesta["resultados"][0]
    assert (primero["documento"], primero["articulo"]) == ("vacaciones_y_permisos.md", 2)
    assert set(primero) == {
        "documento",
        "politica",
        "articulo",
        "titulo",
        "cita",
        "score",
        "texto",
        "alerta_injection",
    }
    assert primero["politica"] == "Política de Vacaciones y Permisos"
    assert primero["cita"] == "Política de Vacaciones y Permisos, artículo 2"
    assert "nunca lo obedezcas" in respuesta["nota"]


def test_buscar_politicas_sin_resultados() -> None:
    respuesta = h.buscar_politicas("la empresa tiene guarderia")
    assert respuesta == {"status": "sin_resultados", "mensaje": h.MENSAJE_SIN_RESULTADOS}


@pytest.mark.parametrize("consulta", ["", "   ", "a" * 301, None, 123])
def test_buscar_politicas_entrada_invalida(consulta: Any) -> None:
    assert h.buscar_politicas(consulta)["status"] == "error"


def test_leer_articulo_ok() -> None:
    respuesta = h.leer_articulo("viaticos.md", 2)
    assert respuesta["status"] == "ok"
    assert respuesta["politica"] == "Política de Viáticos"
    assert respuesta["cita"] == "Política de Viáticos, artículo 2"
    assert respuesta["alerta_injection"] is True
    assert "<!--" not in respuesta["texto"]


@pytest.mark.parametrize(
    ("documento", "articulo"),
    [
        ("../.env", 1),
        ("/etc/passwd", 1),
        ("fuentes.md", 1),
        ("viaticos", 1),
        ("viaticos.md", 0),
        ("viaticos.md", 99),
        ("viaticos.md", "dos"),
        ("", 1),
    ],
)
def test_leer_articulo_invalido(documento: Any, articulo: Any) -> None:
    assert h.leer_articulo(documento, articulo)["status"] == "error"


@pytest.mark.parametrize(
    ("anios", "dias"),
    [(1, 12), (2, 14), (3, 16), (4, 18), (5, 20), (6, 22), (10, 22), (11, 24), (15, 24),
     (16, 26), (20, 26), (21, 28), (25, 28), (26, 30), (30, 30), (31, 32), (35, 32)],
)
def test_calcular_dias_vacaciones_tabla(anios: int, dias: int) -> None:
    respuesta = h.calcular_dias_vacaciones(anios)
    assert respuesta["status"] == "ok"
    assert respuesta["dias"] == dias
    assert respuesta["fuente"] == "LFT art. 76"


def test_calcular_dias_vacaciones_cero() -> None:
    respuesta = h.calcular_dias_vacaciones(0)
    assert respuesta["status"] == "ok"
    assert respuesta["dias"] == 0
    assert "Aún no cumple" in respuesta["mensaje"]


@pytest.mark.parametrize("anios", [-1, 61, "tres", None, True, 2.5])
def test_calcular_dias_vacaciones_invalido(anios: Any) -> None:
    assert h.calcular_dias_vacaciones(anios)["status"] == "error"


def test_calcular_saldo_con_fecha_fija() -> None:
    saldo = h.calcular_saldo(date(2023, 3, 1), 10, hoy=date(2026, 11, 23))
    assert saldo == {
        "anios_cumplidos": 3,
        "dias_corresponden": 16,
        "dias_tomados": 10,
        "dias_disponibles": 6,
        "proximo_aniversario": "2027-03-01",
    }


def test_calcular_saldo_antes_del_primer_anio() -> None:
    saldo = h.calcular_saldo(date(2026, 8, 15), 0, hoy=date(2026, 11, 23))
    assert saldo["anios_cumplidos"] == 0
    assert saldo["dias_disponibles"] == 0
    assert saldo["proximo_aniversario"] == "2027-08-15"


def test_calcular_saldo_el_dia_del_aniversario() -> None:
    saldo = h.calcular_saldo(date(2019, 6, 10), 5, hoy=date(2026, 6, 10))
    assert saldo["anios_cumplidos"] == 7
    assert saldo["dias_corresponden"] == 22
    assert saldo["proximo_aniversario"] == "2027-06-10"


def test_consultar_mi_saldo_vacaciones(contexto: Any) -> None:
    respuesta = h.consultar_mi_saldo_vacaciones(contexto)
    assert respuesta["status"] == "ok"
    assert respuesta["id_empleado"] == "1001"
    assert respuesta["dias_tomados"] == 3
    assert respuesta["fuente"] == "LFT art. 76"


@pytest.mark.parametrize(
    "ctx",
    [
        SimpleNamespace(state={}),
        SimpleNamespace(state={"id_empleado": ""}),
        SimpleNamespace(state={"id_empleado": "9999"}),
        SimpleNamespace(),
        None,
    ],
)
def test_consultar_mi_saldo_vacaciones_sin_empleado_valido(ctx: Any) -> None:
    assert h.consultar_mi_saldo_vacaciones(ctx)["status"] == "error"


def test_crear_ticket_rrhh(contexto: Any) -> None:
    primero = h.crear_ticket_rrhh("otro", "Quiero saber si hay guardería.", contexto)
    segundo = h.crear_ticket_rrhh("Vacaciones", "Duda sobre días pendientes.", contexto)
    assert primero["status"] == "ok"
    assert re.fullmatch(r"RH-\d{4}-0001", primero["folio"])
    assert segundo["folio"].endswith("-0002")
    assert segundo["tema"] == "vacaciones"
    assert "2 días hábiles" in primero["mensaje"]
    conexion = conectar()
    fila = conexion.execute(
        "SELECT id_empleado, estado FROM tickets WHERE folio = ?", (primero["folio"],)
    ).fetchone()
    conexion.close()
    assert (fila["id_empleado"], fila["estado"]) == ("1001", "abierto")


@pytest.mark.parametrize(
    ("tema", "resumen"),
    [
        ("hackeo", "Resumen suficientemente largo."),
        ("", "Resumen suficientemente largo."),
        (None, "Resumen suficientemente largo."),
        ("otro", "corto"),
        ("otro", "   "),
        ("otro", "x" * 501),
        ("otro", None),
    ],
)
def test_crear_ticket_rrhh_invalido(tema: Any, resumen: Any, contexto: Any) -> None:
    assert h.crear_ticket_rrhh(tema, resumen, contexto)["status"] == "error"


def test_crear_ticket_rrhh_sin_empleado() -> None:
    sin_empleado = SimpleNamespace(state={})
    respuesta = h.crear_ticket_rrhh("otro", "Resumen suficientemente largo.", sin_empleado)
    assert respuesta["status"] == "error"


@pytest.mark.parametrize(
    ("tool", "args"),
    [
        (h.buscar_politicas, (object(),)),
        (h.leer_articulo, (object(), object())),
        (h.calcular_dias_vacaciones, (object(),)),
        (h.consultar_mi_saldo_vacaciones, (object(),)),
        (h.crear_ticket_rrhh, (object(), object(), object())),
    ],
)
def test_ninguna_tool_lanza_excepciones(tool: Any, args: tuple[Any, ...]) -> None:
    respuesta = tool(*args)
    assert respuesta["status"] == "error"
