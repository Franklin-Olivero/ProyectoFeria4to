"""Dos fallos vistos en la feria con 3 PCs:

1. El 3er jugador no veía a los demás (los otros sí lo veían a él): si un
   paso del frame del invitado fallaba, se cortaba antes de anotar a los
   demás jugadores. Ahora cada paso va por separado.
2. El panel de la misión titilaba con el mouse encima: al abrirse dejaba
   de haber zona de mouse y se cerraba al cuadro siguiente.
"""

import os
import time

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402
import pytest  # noqa: E402

from Online import registro_errores  # noqa: E402
from Online.cliente import Cliente  # noqa: E402
from Online.servidor import Servidor  # noqa: E402
from Online.sesion_red import AdaptadorOnlineHost, AdaptadorOnlineJoin  # noqa: E402
from src.core import assets  # noqa: E402
from src.core.escenas import Escena  # noqa: E402
from src.dungeon.partida import Partida  # noqa: E402
from src.entities.influencer import Influencer  # noqa: E402
from src.entities.periodista import Periodista  # noqa: E402
from src.entities.player import Ciudadano  # noqa: E402
from src.ui import hud_partida, hud_visibilidad  # noqa: E402

CLASES = (Influencer, Ciudadano, Periodista)


@pytest.fixture(autouse=True)
def _ventana():
    pygame.init()
    pygame.display.set_mode((1280, 720))


@pytest.fixture
def errores(monkeypatch):
    anotados = []
    monkeypatch.setattr(registro_errores, "registrar", lambda contexto, error=None: anotados.append(contexto))
    return anotados


def _esperar(condicion, limite_s=5.0):
    fin = time.time() + limite_s
    while time.time() < fin:
        if condicion():
            return True
        time.sleep(0.01)
    return False


class _Sesion:
    pass


@pytest.fixture
def tres_pcs():
    """Host real + 2 invitados reales por 127.0.0.1, con sus jugadores."""
    servidor = Servidor()
    assert servidor.iniciar(0, interfaz="127.0.0.1") is not None
    clientes = [Cliente(), Cliente()]
    for cliente in clientes:
        assert cliente.conectar("127.0.0.1", servidor.puerto)
        assert _esperar(lambda c=cliente: c.id_jugador is not None)
    assert _esperar(lambda: all(len(c.sala.jugadores()) == 3 for c in clientes))
    pcs = [AdaptadorOnlineHost(servidor, ids_red=[0, 1, 2])] + [
        AdaptadorOnlineJoin(c, id_local=c.id_jugador, ids_red=[0, 1, 2]) for c in clientes]
    estado = []
    for i, adaptador in enumerate(pcs):
        jugadores = [clase(1400 + 40 * k, 1270) for k, clase in enumerate(CLASES)]
        sesion = _Sesion()
        estado.append((adaptador, sesion, Partida(), jugadores, i))
    yield estado
    for cliente in clientes:
        cliente.desconectar()
    servidor.detener()


def _frames(pcs, cantidad=40):
    for _ in range(cantidad):
        for adaptador, sesion, partida, jugadores, i in pcs:
            jugador = jugadores[i]
            adaptador.actualizar(Escena.CIUDAD, None, None, 0.0, 1 / 60, sesion, partida, jugadores, jugador)
            adaptador.actualizar_ciudad(1 / 60, partida, jugadores, jugador)
        time.sleep(0.01)


def test_con_tres_pcs_todas_ven_a_los_tres(tres_pcs, errores):
    _frames(tres_pcs)
    for _, _, partida, jugadores, i in tres_pcs:
        assert partida.jugadores_online == jugadores, f"la PC {i + 1} no ve a todos"
    assert errores == []


def test_si_converger_falla_el_tercero_igual_ve_a_los_demas(tres_pcs, errores, monkeypatch):
    tercero = tres_pcs[2][0]

    def falla(*args, **kwargs):
        raise RuntimeError("falla al converger en esta PC")

    monkeypatch.setattr(tercero, "_converger", falla)
    _frames(tres_pcs)
    _, _, partida, jugadores, _ = tres_pcs[2]
    assert partida.jugadores_online == jugadores  # antes: nunca se anotaban
    assert tercero._ultimo_estado is not None and tercero.reunion is not None
    assert "AdaptadorOnlineJoin.converger" in errores  # queda anotado en el log


def test_antes_del_primer_estado_ya_se_dibuja_a_todos(errores):
    invitado = AdaptadorOnlineJoin(Cliente(), id_local=2)  # sin conectar: nunca llega estado
    partida, jugadores = Partida(), [clase(0, 0) for clase in CLASES]
    invitado._espejo = True
    invitado.cliente.conectado = True
    invitado.actualizar(Escena.CIUDAD, None, None, 0.0, 1 / 60, _Sesion(), partida, jugadores, jugadores[2])
    assert partida.jugadores_online == jugadores


# ----------------------------------------------------------------------
# Panel de la misión con el mouse encima
# ----------------------------------------------------------------------

def _mision():
    from src.story.misiones import mision_actual

    partida = Partida()
    return mision_actual(Escena.CIUDAD.value, partida.campania, partida)


def _dibujar(abierta):
    pantalla = pygame.display.get_surface()
    bloques = hud_visibilidad.bloques_visibles(Escena.CIUDAD, mision_abierta=abierta)
    ctx = hud_partida.ContextoHud(mision=_mision(), transcurrido_mision=5.0)
    return hud_partida.dibujar_hud(pantalla, bloques, ctx)


def test_el_panel_abierto_mantiene_la_zona_del_mouse():
    linea = _dibujar(abierta=False)
    assert linea is not None
    mouse = linea.center
    # Como Main: abierta = mouse sobre la zona del cuadro anterior.
    zona, estados = linea, []
    for _ in range(10):
        abierta = zona is not None and zona.collidepoint(mouse)
        estados.append(abierta)
        zona = _dibujar(abierta)
    assert all(estados), "el panel se cerraba y abría (titilaba)"
    assert zona.contains(linea) and zona.collidepoint(mouse)


def test_el_panel_se_cierra_al_sacar_el_mouse():
    zona = _dibujar(abierta=True)
    afuera = (zona.right + 50, zona.bottom + 50)
    assert not zona.collidepoint(afuera)
    assert _dibujar(abierta=False) is not None  # cerrado vuelve la línea
    assert pygame.Rect(assets.RECT_PANEL_MISION_CIUDAD).colliderect(zona)
