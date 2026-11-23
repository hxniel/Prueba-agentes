from pathlib import Path

from asistente_rrhh.db import conectar, inicializar_bd


def _contar(ruta: Path, tabla: str) -> int:
    conexion = conectar(ruta)
    total = conexion.execute(f"SELECT COUNT(*) FROM {tabla}").fetchone()[0]
    conexion.close()
    return total


def test_crea_tablas(tmp_path: Path) -> None:
    ruta = tmp_path / "rrhh.db"
    inicializar_bd(ruta)
    conexion = conectar(ruta)
    tablas = {
        fila["name"]
        for fila in conexion.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
    }
    conexion.close()
    assert {"empleados", "tickets"} <= tablas


def test_carga_cinco_empleados(tmp_path: Path) -> None:
    ruta = tmp_path / "rrhh.db"
    inicializar_bd(ruta)
    assert _contar(ruta, "empleados") == 5


def test_es_idempotente(tmp_path: Path) -> None:
    ruta = tmp_path / "rrhh.db"
    inicializar_bd(ruta)
    inicializar_bd(ruta)
    assert _contar(ruta, "empleados") == 5
    assert _contar(ruta, "tickets") == 0
