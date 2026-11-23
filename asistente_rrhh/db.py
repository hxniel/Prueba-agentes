import sqlite3
from pathlib import Path

from asistente_rrhh import config

ESQUEMA = """
CREATE TABLE IF NOT EXISTS empleados (
    id_empleado TEXT PRIMARY KEY,
    nombre TEXT NOT NULL,
    puesto TEXT NOT NULL,
    fecha_ingreso DATE NOT NULL,
    dias_vacaciones_tomados INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS tickets (
    folio TEXT PRIMARY KEY,
    id_empleado TEXT NOT NULL,
    tema TEXT NOT NULL,
    resumen TEXT NOT NULL,
    estado TEXT NOT NULL DEFAULT 'abierto',
    creado_en TEXT NOT NULL
);
"""

EMPLEADOS: list[tuple[str, str, str, str, int]] = [
    ("1001", "Ana López Ramírez", "Analista de compras", "2025-08-15", 3),
    ("1002", "Carlos Méndez Ortiz", "Ejecutivo de ventas", "2023-03-01", 10),
    ("1003", "Lucía Hernández Soto", "Contadora", "2019-06-10", 5),
    ("1004", "Jorge Ramírez Díaz", "Gerente de almacén", "2012-01-20", 0),
    ("1005", "María Torres Vega", "Directora de operaciones", "2001-09-05", 20),
]


def conectar(ruta: Path | None = None) -> sqlite3.Connection:
    """Abre una conexión a la base de datos de RRHH.

    Args:
        ruta: Ruta del archivo SQLite; por defecto config.RUTA_BD.
    """
    destino = ruta or config.RUTA_BD
    destino.parent.mkdir(parents=True, exist_ok=True)
    conexion = sqlite3.connect(destino)
    conexion.row_factory = sqlite3.Row
    return conexion


def inicializar_bd(ruta: Path | None = None) -> None:
    """Crea las tablas y carga los empleados ficticios sin duplicarlos.

    Args:
        ruta: Ruta del archivo SQLite; por defecto config.RUTA_BD.
    """
    with conectar(ruta) as conexion:
        conexion.executescript(ESQUEMA)
        conexion.executemany(
            "INSERT OR IGNORE INTO empleados "
            "(id_empleado, nombre, puesto, fecha_ingreso, dias_vacaciones_tomados) "
            "VALUES (?, ?, ?, ?, ?)",
            EMPLEADOS,
        )
    conexion.close()
