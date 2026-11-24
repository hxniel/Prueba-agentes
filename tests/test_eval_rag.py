import json
from pathlib import Path
from typing import Any

import pytest

from asistente_rrhh import config
from asistente_rrhh.rag import IndicePoliticas

RUTA_EVAL = Path(__file__).parent / "data" / "eval_rag.json"
META_HIT_AT_3 = 0.8


@pytest.fixture
def evaluacion() -> dict[str, Any]:
    return json.loads(RUTA_EVAL.read_text(encoding="utf-8"))


@pytest.fixture
def indice(monkeypatch: pytest.MonkeyPatch) -> IndicePoliticas:
    monkeypatch.setattr(config, "UMBRAL_BM25", config.UMBRAL_BM25_POR_DEFECTO)
    return IndicePoliticas()


def test_hit_at_3(indice: IndicePoliticas, evaluacion: dict[str, Any]) -> None:
    casos = evaluacion["en_corpus"]
    aciertos = 0
    for caso in casos:
        resultados = indice.buscar(caso["pregunta"], k=3)
        esperado = (caso["documento"], caso["articulo"])
        if esperado in [(f.documento, f.articulo) for f, _ in resultados]:
            aciertos += 1
    assert aciertos / len(casos) >= META_HIT_AT_3


def test_preguntas_fuera_de_corpus_no_regresan_resultados(
    indice: IndicePoliticas, evaluacion: dict[str, Any]
) -> None:
    for pregunta in evaluacion["fuera_de_corpus"]:
        assert indice.buscar(pregunta) == [], pregunta
