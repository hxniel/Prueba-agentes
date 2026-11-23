import os
from pathlib import Path

from dotenv import load_dotenv

RAIZ: Path = Path(__file__).resolve().parent.parent

load_dotenv(RAIZ / ".env")

MODELO: str = os.getenv("MODELO", "gemini-3.5-flash-lite")
MODELO_RESPALDO: str = os.getenv("MODELO_RESPALDO", "gemini-3.1-flash-lite")
UMBRAL_BM25_POR_DEFECTO: float = 3.0
UMBRAL_BM25: float = float(os.getenv("UMBRAL_BM25", str(UMBRAL_BM25_POR_DEFECTO)))
RUTA_BD: Path = RAIZ / "data" / "rrhh.db"
RUTA_POLITICAS: Path = RAIZ / "data" / "politicas"
