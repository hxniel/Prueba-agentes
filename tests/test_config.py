from asistente_rrhh import config


def test_raiz_existe() -> None:
    assert config.RAIZ.exists()


def test_ruta_politicas_dentro_de_raiz() -> None:
    assert config.RUTA_POLITICAS.is_relative_to(config.RAIZ)
