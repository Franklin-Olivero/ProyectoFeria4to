"""Apariencias del vestidor guardadas entre partidas, el vestidor en la
selección de roles local y el personaje de Higgsfield teñido al posar."""

import json
import os
import sys
from types import SimpleNamespace

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pygame  # noqa: E402
import pytest  # noqa: E402

from src.core import apariencias_guardadas, assets  # noqa: E402
from src.core.apariencia import PREDETERMINADA, Apariencia  # noqa: E402
from Online import lobby  # noqa: E402
from Online.personalizacion import PESTANAS, SHOES, Vestidor  # noqa: E402

VESTIDO = Apariencia(piel=4, pelo=3, ropa=1, pantalon=2, zapatos=5)


def test_sin_archivo_todo_en_auto(tmp_path):
    assert apariencias_guardadas.cargar(str(tmp_path / "no.json")) == [PREDETERMINADA, PREDETERMINADA]


def test_guardar_y_cargar_ida_y_vuelta(tmp_path):
    ruta = str(tmp_path / "apariencias.json")
    assert apariencias_guardadas.guardar([VESTIDO, PREDETERMINADA], ruta)
    assert apariencias_guardadas.cargar(ruta) == [VESTIDO, PREDETERMINADA]
    assert apariencias_guardadas.guardar_puesto(1, Apariencia(zapatos=0), ruta)
    assert apariencias_guardadas.cargar(ruta) == [VESTIDO, Apariencia(zapatos=0)]
    datos = json.loads(open(ruta, encoding="utf-8").read())
    assert datos["version"] == 1 and datos["jugadores"][0]["zapatos"] == 5


def test_por_defecto_va_a_la_carpeta_de_datos_de_usuario():
    apariencias_guardadas.guardar([VESTIDO])
    assert os.path.isfile(apariencias_guardadas.ruta_predeterminada())
    assert apariencias_guardadas.cargar() == [VESTIDO, PREDETERMINADA]


@pytest.mark.parametrize("contenido", ["{roto", "[]", '{"jugadores": 3}', '{"jugadores": [{"zapatos": 99}, 7]}'])
def test_un_archivo_roto_nunca_impide_arrancar(tmp_path, contenido):
    ruta = tmp_path / "apariencias.json"
    ruta.write_text(contenido, encoding="utf-8")
    assert apariencias_guardadas.cargar(str(ruta)) == [PREDETERMINADA, PREDETERMINADA]


def test_si_el_disco_falla_queda_en_memoria(monkeypatch):
    monkeypatch.setattr(apariencias_guardadas.datos_usuario, "guardar_json_atomico", lambda *_: False)
    assert apariencias_guardadas.guardar([VESTIDO]) is False
    assert apariencias_guardadas.cargar() == [VESTIDO, PREDETERMINADA]


def test_para_jugador():
    assert apariencias_guardadas.para_jugador(PREDETERMINADA) is None
    assert apariencias_guardadas.para_jugador(None) is None
    assert apariencias_guardadas.para_jugador(VESTIDO) is VESTIDO


# --- Partida local: cada jugador sale vestido -----------------------------

def test_la_sesion_local_viste_a_cada_jugador():
    import Main
    from src.entities.candidato import Candidato
    from src.entities.player import Ciudadano

    sesion = Main._nueva_sesion([Ciudadano, Candidato], None, None, [VESTIDO, PREDETERMINADA])
    assert sesion.jugadores[0].apariencia == VESTIDO
    assert sesion.jugadores[1].apariencia is None  # todo en AUTO: la hoja de su rol
    assert Main._nueva_sesion([Ciudadano], None).jugadores[0].apariencia is None


def test_el_jugador_dibuja_su_apariencia_en_combate(monkeypatch):
    from src.entities.player import Ciudadano
    from src.ui import sprites

    llamadas = []
    original = sprites.sprite_jugador
    monkeypatch.setattr(sprites, "sprite_jugador", lambda *a, **k: llamadas.append(k) or original(*a, **k))
    jugador = Ciudadano(100, 100)
    jugador.apariencia = VESTIDO
    jugador.dibujar(pygame.Surface((300, 300)))
    assert llamadas and all(k.get("apariencia") == VESTIDO for k in llamadas)


# --- Vestidor con el control (J2) -----------------------------------------

def _boton(boton):
    return SimpleNamespace(type=pygame.CONTROLLERBUTTONDOWN, button=boton)


def test_el_vestidor_con_el_control():
    vestidor = Vestidor()
    assert lobby.evento_vestidor_mando(_boton(pygame.CONTROLLER_BUTTON_DPAD_RIGHT), vestidor) == lobby.CAMBIO_VESTIDOR
    assert vestidor.apariencia.piel == 0
    assert lobby.evento_vestidor_mando(_boton(pygame.CONTROLLER_BUTTON_LEFTSHOULDER), vestidor) is None
    assert vestidor.pestana == PESTANAS[-1] == SHOES  # L1 desde COLOR da la vuelta a SHOES
    lobby.evento_vestidor_mando(_boton(pygame.CONTROLLER_BUTTON_DPAD_DOWN), vestidor)
    assert vestidor.apariencia.zapatos is not None
    for boton in lobby.BOTONES_CERRAR_VESTIDOR:
        assert lobby.evento_vestidor_mando(_boton(boton), vestidor) == lobby.CERRAR_VESTIDOR
    assert lobby.evento_vestidor_mando(SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_a), vestidor) is None


# --- La selección muestra al personaje de Higgsfield ----------------------

def test_la_tarjeta_usa_la_apariencia_de_quien_la_senala():
    from src.ui.seleccion_rol import VistaSeleccion

    vista = VistaSeleccion(4)
    vista.apariencias = [VESTIDO, Apariencia(zapatos=1)]
    seleccion = SimpleNamespace(cursores=[SimpleNamespace(indice=2), SimpleNamespace(indice=0)])
    assert vista.apariencia_en(2, seleccion) == VESTIDO
    assert vista.apariencia_en(0, seleccion) == Apariencia(zapatos=1)
    assert vista.apariencia_en(1, seleccion) is None
    seleccion.cursores[1].indice = 2  # los dos en la misma: manda J1
    assert vista.apariencia_en(2, seleccion) == VESTIDO


@pytest.mark.parametrize("rol", assets.ROLES_APARIENCIA)
def test_el_retrato_teñido_lleva_los_colores_elegidos(rol):
    from src.ui import sprites

    pygame.display.init()
    pygame.display.set_mode((1, 1))
    sprites.limpiar_cache_hojas()
    normal = sprites.retrato_rol(rol, 120)
    teñido = sprites.retrato_rol(rol, 120, VESTIDO)
    assert teñido is not None and teñido.get_size() == normal.get_size()
    colores = {tuple(teñido.get_at((x, y)))[:3] for x in range(teñido.get_width()) for y in range(teñido.get_height())
               if teñido.get_at((x, y)).a}
    assert assets.COLORES_ROPA[1] in colores and assets.TONOS_PIEL[4] in colores
    assert sprites.retrato_rol(rol, 120, VESTIDO) is teñido  # se tiñe una vez
    assert sprites.retrato_rol(f"{rol}_decidido", 120, VESTIDO) is teñido  # las variantes usan el retrato base
