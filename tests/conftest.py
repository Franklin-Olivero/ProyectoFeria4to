"""Configuración común de los tests.

Cada test usa su propia carpeta de datos de usuario (CIVITAS_DATOS), así
lo que el juego guarda al jugar (preferencias, audio, apariencias del
vestidor) nunca toca la carpeta real ni se filtra de un test a otro."""

import pytest


@pytest.fixture(autouse=True)
def datos_de_usuario_aislados(tmp_path, monkeypatch):
    monkeypatch.setenv("CIVITAS_DATOS", str(tmp_path / "datos_usuario"))
    from src.core import apariencias_guardadas
    monkeypatch.setattr(apariencias_guardadas, "_en_memoria", None)
