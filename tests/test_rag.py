from pathlib import Path

import pytest

from asistente_rrhh import config
from asistente_rrhh.rag import (
    IndicePoliticas,
    cargar_fragmentos,
    normalizar,
    sanitizar,
    titulo_politica,
)


@pytest.fixture
def indice(monkeypatch: pytest.MonkeyPatch) -> IndicePoliticas:
    monkeypatch.setattr(config, "UMBRAL_BM25", config.UMBRAL_BM25_POR_DEFECTO)
    return IndicePoliticas()


def test_normalizar_quita_acentos_mayusculas_y_stopwords() -> None:
    assert normalizar("¿Cuántos DÍAS de Vacaciones me tocan?") == ["dias", "vacaciones", "tocan"]


def test_sanitizar_elimina_comentario_de_viaticos_y_marca_alerta() -> None:
    contenido = (config.RUTA_POLITICAS / "viaticos.md").read_text(encoding="utf-8")
    limpio, alerta = sanitizar(contenido)
    assert alerta is True
    assert "<!--" not in limpio
    assert "ilimitados" not in limpio


def test_sanitizar_texto_normal_sin_alerta() -> None:
    assert sanitizar("El aguinaldo es de 15 días.") == ("El aguinaldo es de 15 días.", False)


def test_conteo_de_fragmentos() -> None:
    fragmentos = cargar_fragmentos(config.RUTA_POLITICAS)
    assert len(fragmentos) == 34
    assert all(f.documento != "fuentes.md" for f in fragmentos)
    marcados = [(f.documento, f.articulo) for f in fragmentos if f.alerta_injection]
    assert marcados == [("viaticos.md", 2)]


def test_pregunta_de_viaticos_trae_topes_diarios(indice: IndicePoliticas) -> None:
    resultados = indice.buscar("¿Los viáticos son ilimitados?")
    assert resultados
    assert (resultados[0][0].documento, resultados[0][0].articulo) == ("viaticos.md", 1)


def test_vacaciones_primer_anio_trae_politica_de_vacaciones(indice: IndicePoliticas) -> None:
    resultados = indice.buscar("cuantos dias de vacaciones me tocan en mi primer año")
    assert resultados
    assert resultados[0][0].documento == "vacaciones_y_permisos.md"


def test_fragmentos_incluyen_titulo_de_la_politica() -> None:
    fragmentos = cargar_fragmentos(config.RUTA_POLITICAS)
    politicas = {f.documento: f.politica for f in fragmentos}
    assert politicas == {
        "prestaciones.md": "Política de Prestaciones",
        "reglamento_interno.md": "Reglamento Interno de Trabajo",
        "teletrabajo.md": "Política de Teletrabajo",
        "vacaciones_y_permisos.md": "Política de Vacaciones y Permisos",
        "viaticos.md": "Política de Viáticos",
    }


def test_titulo_politica_sin_encabezado_usa_nombre_de_archivo() -> None:
    assert titulo_politica("Sin encabezado", Path("bono_anual.md")) == "Bono anual"
