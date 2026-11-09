"""Qué bloques del HUD se ven en cada escena (lógica pura)."""

from src.core.escenas import Escena
from src.ui import hud_visibilidad as v


def test_combate_solo_lo_esencial():
    for escena in (Escena.MAZMORRA, Escena.JEFE):
        bloques = v.bloques_visibles(escena)
        assert bloques and all(v.es_esencial(b) for b in bloques), (escena, bloques)
    assert {v.VIDA, v.HABILIDAD, v.COLAPSO, v.CONTADOR} <= v.bloques_visibles(Escena.MAZMORRA)
    assert v.JEFE in v.bloques_visibles(Escena.JEFE)


def test_minimapa_con_la_tecla():
    assert v.MINIMAPA in v.bloques_visibles(Escena.MAZMORRA, minimapa=True)
    assert v.MINIMAPA not in v.bloques_visibles(Escena.MAZMORRA, minimapa=False)


def test_ciudad_mision_en_una_linea_y_se_abre():
    cerrada = v.bloques_visibles(Escena.CIUDAD)
    assert v.MISION_LINEA in cerrada and v.MISION not in cerrada
    assert v.CINTILLO in cerrada and v.CONTROLES not in cerrada
    assert v.MISION in v.bloques_visibles(Escena.CIUDAD, mision_abierta=True)


def test_controles_solo_unos_segundos_o_con_detallado():
    for escena in (Escena.CIUDAD, Escena.MAZMORRA, Escena.JEFE):
        assert v.CONTROLES not in v.bloques_visibles(escena)
        assert v.CONTROLES in v.bloques_visibles(escena, mostrar_controles=True)
        assert v.CONTROLES in v.bloques_visibles(escena, hud_detallado=True)
    assert v.CONTROLES in v.bloques_visibles(Escena.DECISION)  # sin ellos no se juega la terminal


def test_hud_detallado_agrega_lo_secundario():
    for escena in (Escena.CIUDAD, Escena.MAZMORRA, Escena.JEFE):
        limpio = v.bloques_visibles(escena)
        detallado = v.bloques_visibles(escena, hud_detallado=True)
        assert limpio < detallado
        assert all(b in v.SECUNDARIOS for b in detallado - limpio)
    assert {v.TITULO, v.DESTINO, v.REPUTACION, v.MISION} <= v.bloques_visibles(Escena.CIUDAD, hud_detallado=True)


def test_mapa_del_mundo_tapa_la_ciudad():
    bloques = v.bloques_visibles(Escena.CIUDAD, mapa_mundo=True)
    assert v.CINTILLO not in bloques and v.MISION_LINEA not in bloques and v.AVISO not in bloques
    assert v.CONTROLES in bloques


def test_multijugador_sin_panel_de_vida_arriba():
    bloques = v.bloques_visibles(Escena.MAZMORRA, multijugador=True)
    assert v.VIDA not in bloques and v.HABILIDAD not in bloques and v.COLAPSO in bloques


def test_escenas_sin_hud():
    for escena in (Escena.VICTORIA, Escena.DERROTA, Escena.RESULTADO):
        assert v.bloques_visibles(escena, hud_detallado=True) == frozenset()


def test_esenciales_y_secundarios_no_se_mezclan():
    assert not (v.ESENCIALES & v.SECUNDARIOS)
