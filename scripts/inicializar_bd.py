import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from asistente_rrhh import config  # noqa: E402
from asistente_rrhh.db import inicializar_bd  # noqa: E402


def main() -> None:
    inicializar_bd()
    print(f"Base de datos lista en {config.RUTA_BD}")


if __name__ == "__main__":
    main()
