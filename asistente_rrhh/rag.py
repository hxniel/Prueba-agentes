import re
import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from rank_bm25 import BM25Okapi

from asistente_rrhh import config

STOPWORDS: frozenset[str] = frozenset(
    {
        "a", "al", "algo", "como", "con", "cual", "cuando", "cuanta", "cuantas", "cuanto",
        "cuantos", "dan", "dar", "de", "del", "donde", "el", "empresa", "en", "es", "esta",
        "este", "ha", "hago", "hay", "la", "las", "le", "lo", "los", "me", "mi", "mis", "no",
        "o", "pagan", "para", "pedir", "pero", "por", "pueden", "puedo", "que", "quiero",
        "se", "ser", "si", "sin", "sobre", "son", "su", "sus", "te", "tengo", "tiene",
        "tienen", "tu", "un", "una", "voy", "y", "ya", "yo",
    }
)

ARCHIVOS_EXCLUIDOS: frozenset[str] = frozenset({"fuentes.md"})

PATRON_COMENTARIO = re.compile(r"<!--.*?-->", re.DOTALL)
PATRON_ARTICULO = re.compile(r"^## Artículo (\d+)\.\s*(.+)$", re.MULTILINE)
PATRONES_INJECTION: tuple[re.Pattern[str], ...] = tuple(
    re.compile(patron, re.IGNORECASE)
    for patron in (
        r"\b(ignora|olvida)\w*\b.{0,40}\binstrucciones\b",
        r"\beres ahora\b",
        r"\bsystem prompt\b",
        r"\basistente\s*:",
        r"\bresponde que\b",
    )
)


@dataclass(frozen=True)
class Fragmento:
    documento: str
    articulo: int
    titulo: str
    texto: str
    alerta_injection: bool


def _sin_acentos(texto: str) -> str:
    descompuesto = unicodedata.normalize("NFD", texto)
    return "".join(c for c in descompuesto if unicodedata.category(c) != "Mn")


def normalizar(texto: str) -> list[str]:
    """Convierte un texto en tokens en minúsculas, sin acentos ni stopwords.

    Args:
        texto: Texto a normalizar.
    """
    tokens = re.findall(r"\w+", _sin_acentos(texto.lower()))
    return [token for token in tokens if token not in STOPWORDS]


def sanitizar(texto: str) -> tuple[str, bool]:
    """Elimina comentarios HTML y detecta patrones de prompt injection.

    Args:
        texto: Texto original de la política.
    """
    alerta = any(patron.search(texto) for patron in PATRONES_INJECTION)
    limpio = PATRON_COMENTARIO.sub("", texto)
    limpio = re.sub(r"[ \t]{2,}", " ", limpio).strip()
    return limpio, alerta


def cargar_fragmentos(ruta: Path) -> list[Fragmento]:
    """Divide cada política en un fragmento por artículo.

    Args:
        ruta: Carpeta con las políticas en Markdown.
    """
    fragmentos: list[Fragmento] = []
    for archivo in sorted(ruta.glob("*.md")):
        if archivo.name in ARCHIVOS_EXCLUIDOS:
            continue
        contenido = archivo.read_text(encoding="utf-8")
        encabezados = list(PATRON_ARTICULO.finditer(contenido))
        for i, encabezado in enumerate(encabezados):
            fin = encabezados[i + 1].start() if i + 1 < len(encabezados) else len(contenido)
            cuerpo = contenido[encabezado.end() : fin]
            texto, alerta = sanitizar(cuerpo)
            fragmentos.append(
                Fragmento(
                    documento=archivo.name,
                    articulo=int(encabezado.group(1)),
                    titulo=encabezado.group(2).strip(),
                    texto=texto,
                    alerta_injection=alerta,
                )
            )
    return fragmentos


class IndicePoliticas:
    """Índice BM25 sobre los artículos de las políticas."""

    def __init__(self, ruta: Path | None = None) -> None:
        self.fragmentos = cargar_fragmentos(ruta or config.RUTA_POLITICAS)
        corpus = [normalizar(f"{f.titulo} {f.texto}") for f in self.fragmentos]
        self._bm25 = BM25Okapi(corpus)

    def puntuar(self, consulta: str) -> list[tuple[Fragmento, float]]:
        """Devuelve todos los fragmentos ordenados por score, sin aplicar umbral.

        Args:
            consulta: Pregunta del empleado.
        """
        tokens = normalizar(consulta)
        if not tokens:
            return []
        scores = self._bm25.get_scores(tokens)
        pares = zip(self.fragmentos, (float(s) for s in scores), strict=True)
        return sorted(pares, key=lambda par: par[1], reverse=True)

    def buscar(self, consulta: str, k: int = 3) -> list[tuple[Fragmento, float]]:
        """Devuelve hasta k fragmentos cuyo score supera config.UMBRAL_BM25.

        Args:
            consulta: Pregunta del empleado.
            k: Número máximo de resultados.
        """
        return [par for par in self.puntuar(consulta) if par[1] > config.UMBRAL_BM25][:k]


@lru_cache(maxsize=1)
def obtener_indice() -> IndicePoliticas:
    """Devuelve el índice de políticas, construido una sola vez."""
    return IndicePoliticas()
