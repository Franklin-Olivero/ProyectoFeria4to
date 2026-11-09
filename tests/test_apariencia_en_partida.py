"""La apariencia de los vestidores del lobby, durante la partida online.

Al configurar la sesión, cada PC viste a cada jugador con la apariencia de
su nodo en el grafo de sala (Online/sesion_red._vestir_jugadores), por el
mismo orden de ids de red en todas las PCs. Después, el dibujo de la
ciudad y del combate se la pasa a sprites.sprite_jugador. En una partida
local la apariencia queda en None: la hoja de siempre.

Las conexiones son un Servidor() o un Cliente() sin conectar (su .sala es
un GrafoSala); el dibujo va sobre Surfaces en memoria, sin ventana.
"""

import os
import sys
from types import SimpleNamespace

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pygame  # noqa: E402
import pytest  # noqa: E402

from Online import registro_errores  # noqa: E402
from Online.cliente import Cliente  # noqa: E402
from Online.protocolo import GrafoSala  # noqa: E402
from Online.servidor import Servidor  # noqa: E402
from Online.sesion_red import ConfigSesionHost, ConfigSesionJoin, preparar_sesion_online  # noqa: E402
from src.core import assets  # noqa: E402
from src.core.apariencia import PREDETERMINADA, Apariencia  # noqa: E402
from src.core.config import ALTO_PANTALLA, ANCHO_PANTALLA  # noqa: E402
from src.dungeon.grafo_ciudad import EDIFICIOS  # noqa: E402
from src.dungeon.partida import Partida  # noqa: E402
from src.entities.candidato import Candidato  # noqa: E402
from src.entities.influencer import Influencer  # noqa: E402
from src.entities.periodista import Periodista  # noqa: E402
from src.entities.player import Ciudadano  # noqa: E402
from src.ui import ciudad_render, sprites  # noqa: E402

# Lo que cada id eligió en los vestidores. No hay id 1: se fue antes de
# iniciar, así el índice de un jugador no coincide con su id.
VESTIDOS = {
    0: Apariencia(piel=0),
    2: Apariencia(cabeza="candidato", traje="influencer"),
    3: Apariencia(piel=7, cabeza="periodista", traje="ciudadano"),
}


def _sala(ids=(0, 2, 3)):
    """Grafo de sala con esos ids conectados y vestidos según VESTIDOS."""
    sala = GrafoSala()
    for jid in ids:
        sala.conectar(jid)
        if jid in VESTIDOS:
            sala.elegir_apariencia(jid, VESTIDOS[jid])
    return sala


def _sesion(clases):
    """Lo que Main._nueva_sesion le pasa a configurar_sesion: los jugadores ya creados."""
    return SimpleNamespace(jugadores=[clase(0, 0) for clase in clases])


def _apariencias(sesion):
    return [jugador.apariencia for jugador in sesion.jugadores]


@pytest.fixture(autouse=True)
def cache_limpio():
    sprites.limpiar_cache_hojas()
    yield
    sprites.limpiar_cache_hojas()


@pytest.fixture(autouse=True)
def errores(monkeypatch):
    """Contextos que se anotan en el registro de errores (sin escribir en
    Online/errores_online.log)."""
    anotados = []
    monkeypatch.setattr(registro_errores, "registrar", lambda contexto, error=None: anotados.append(contexto))
    return anotados


@pytest.fixture
def llamadas_sprite(monkeypatch):
    """kwargs de cada llamada a sprites.sprite_jugador. Delega en la real,
    así un argumento que no acepte también hace fallar el test."""
    llamadas = []
    original = sprites.sprite_jugador

    def espia(*args, **kwargs):
        llamadas.append(kwargs)
        return original(*args, **kwargs)

    monkeypatch.setattr(sprites, "sprite_jugador", espia)
    return llamadas


# ----------------------------------------------------------------------
# El jugador y su dibujo en combate
# ----------------------------------------------------------------------

@pytest.mark.parametrize("clase", [Ciudadano, Influencer, Periodista, Candidato])
def test_un_jugador_nuevo_no_tiene_apariencia(clase):
    assert clase(0, 0).apariencia is None


@pytest.mark.parametrize("apariencia", [None, VESTIDOS[3]], ids=["local", "vestido"])
def test_dibujar_pasa_su_apariencia_al_sprite_tambien_con_rastro_de_dash(llamadas_sprite, apariencia):
    jugador = Candidato(100, 100)
    jugador.apariencia = apariencia
    jugador.rastro_dash.extend([(60, 100), (80, 100)])  # imágenes fantasma del dash
    jugador.dibujar(pygame.Surface((200, 200)))
    assert llamadas_sprite
    assert all(kwargs.get("apariencia") == apariencia for kwargs in llamadas_sprite)


def test_el_jugador_vestido_se_ve_distinto_en_el_lienzo_de_combate():
    def lienzo_con(apariencia):
        jugador = Ciudadano(100, 100)  # quieto: siempre el primer cuadro
        jugador.apariencia = apariencia
        lienzo = pygame.Surface((200, 200))
        jugador.dibujar(lienzo)
        return pygame.image.tobytes(lienzo, "RGB")

    # La predeterminada es la hoja del rol, igual que una partida local.
    assert lienzo_con(PREDETERMINADA) == lienzo_con(None)
    assert lienzo_con(Apariencia(cabeza="candidato")) != lienzo_con(None)


# ----------------------------------------------------------------------
# Ciudad Nova: el jugador local (ciudad_render) y los demás (Main)
# ----------------------------------------------------------------------

@pytest.mark.parametrize("apariencia", [None, VESTIDOS[2]], ids=["local", "vestido"])
def test_la_ciudad_dibuja_al_jugador_con_su_apariencia(llamadas_sprite, apariencia):
    pygame.font.init()  # los rótulos de los edificios
    partida = Partida()
    jugador = Periodista(0, 0)
    jugador.colocar_en(partida.posicion_aparicion())
    jugador.apariencia = apariencia
    ciudad_render.dibujar_ciudad(pygame.Surface((ANCHO_PANTALLA, ALTO_PANTALLA)), partida, jugador, 0.0)
    del_jugador = [kwargs.get("apariencia") for kwargs in llamadas_sprite if kwargs.get("rol") == "periodista"]
    assert del_jugador == [apariencia]


def test_la_ciudad_dibuja_a_los_demas_jugadores_online_con_su_apariencia(llamadas_sprite):
    from Main import _dibujar_ciudad  # dentro del test: importar Main carga todo el juego

    pygame.font.init()
    partida = Partida()
    local, otro = Ciudadano(0, 0), Candidato(0, 0)
    x, y = partida.posicion_aparicion()
    local.colocar_en((x, y))
    otro.colocar_en((x + 40, y))
    local.apariencia, otro.apariencia = VESTIDOS[0], VESTIDOS[3]
    partida.jugadores_online = [local, otro]  # lo pone el adaptador de red en cada frame
    _dibujar_ciudad(pygame.Surface((ANCHO_PANTALLA, ALTO_PANTALLA)), partida, local, EDIFICIOS[0],
                    0.0, False, False)
    por_rol = {kwargs["rol"]: kwargs.get("apariencia") for kwargs in llamadas_sprite}
    assert por_rol == {"ciudadano": VESTIDOS[0], "candidato": VESTIDOS[3]}


def test_la_partida_nueva_tras_la_derrota_global_conserva_la_apariencia():
    from Main import _jugadores_nuevos

    viejos = [Ciudadano(0, 0), Candidato(0, 0)]
    viejos[0].apariencia = VESTIDOS[2]
    viejos[0].vida = 0
    viejos[1].carga_habilidad = 3
    nuevos = _jugadores_nuevos(viejos)
    assert [type(j) for j in nuevos] == [Ciudadano, Candidato]
    assert all(nuevo is not viejo for nuevo, viejo in zip(nuevos, viejos))
    assert nuevos[0].vida == nuevos[0].vida_maxima and nuevos[1].carga_habilidad == 0
    assert [j.apariencia for j in nuevos] == [VESTIDOS[2], None]


# ----------------------------------------------------------------------
# configurar_sesion: cada jugador con la apariencia de SU id
# ----------------------------------------------------------------------

def test_el_host_viste_a_cada_jugador_segun_el_orden_de_ids_red(errores):
    servidor = Servidor()  # sin iniciar
    servidor.sala = _sala((0, 2, 3))
    clases = [Ciudadano, Influencer, Periodista]
    sesion = ConfigSesionHost(servidor, clases, ids_red=[0, 3, 2]).configurar_sesion(_sesion(clases))
    assert _apariencias(sesion) == [VESTIDOS[0], VESTIDOS[3], VESTIDOS[2]]
    assert errores == []


def test_el_invitado_viste_a_cada_jugador_segun_el_orden_de_ids_red(errores):
    cliente = Cliente()  # sin conectar
    cliente.id_jugador = 2
    cliente.sala = GrafoSala.de_dict(_sala((0, 2, 3)).a_dict())  # el último LOBBY recibido
    clases = [Ciudadano, Influencer, Periodista]
    config = ConfigSesionJoin(cliente, clases, id_local=2, ids_red=[3, 0, 2])
    sesion = config.configurar_sesion(_sesion(clases))
    assert _apariencias(sesion) == [VESTIDOS[3], VESTIDOS[0], VESTIDOS[2]]
    assert sesion.jugadores[sesion.id_local].apariencia == VESTIDOS[2]  # se ve a sí mismo con lo suyo
    assert errores == []


def test_host_e_invitado_ven_igual_a_cada_jugador(errores):
    """El camino real (preparar_sesion_online): el invitado arma la sala
    con el LOBBY que le llega por red y empareja con el mismo orden."""
    servidor = Servidor()
    servidor.sala = _sala((0, 2, 3))
    clases = [Ciudadano, Periodista, Candidato]
    _, _, config_host = preparar_sesion_online(clases, None, servidor, es_host=True)
    sesion_host = config_host.configurar_sesion(_sesion(clases))

    cliente = Cliente()
    cliente.id_jugador = 3
    cliente.sala = GrafoSala.de_dict(servidor.sala.a_dict())
    _, _, config_join = preparar_sesion_online(clases, None, cliente, es_host=False)
    sesion_join = config_join.configurar_sesion(_sesion(clases))

    esperadas = [VESTIDOS[0], VESTIDOS[2], VESTIDOS[3]]
    assert _apariencias(sesion_host) == esperadas
    assert _apariencias(sesion_join) == esperadas
    assert sesion_join.id_local == 2
    assert errores == []


@pytest.mark.parametrize("es_host", [True, False], ids=["host", "invitado"])
def test_sin_ids_red_empareja_por_el_orden_de_la_sala(es_host, errores):
    conexion = Servidor() if es_host else Cliente()
    conexion.sala = _sala((0, 2, 3))
    clases = [Ciudadano, Influencer, Candidato]
    config = ConfigSesionHost(conexion, clases) if es_host else ConfigSesionJoin(conexion, clases, id_local=1)
    sesion = config.configurar_sesion(_sesion(clases))
    assert _apariencias(sesion) == [VESTIDOS[0], VESTIDOS[2], VESTIDOS[3]]
    assert errores == []


# ----------------------------------------------------------------------
# Robustez: vestir nunca rompe la sesión
# ----------------------------------------------------------------------

def _configurar(es_host, conexion, sesion, clases=(Ciudadano, Candidato)):
    clases = list(clases)
    if es_host:
        return ConfigSesionHost(conexion, clases, ids_red=[0, 1]).configurar_sesion(sesion)
    return ConfigSesionJoin(conexion, clases, id_local=1, ids_red=[0, 1]).configurar_sesion(sesion)


@pytest.mark.parametrize("es_host", [True, False], ids=["host", "invitado"])
@pytest.mark.parametrize("conexion", [SimpleNamespace(sala=None), object(), None, "no soy una conexión"],
                         ids=["sala_none", "object", "none", "texto"])
def test_sin_sala_la_sesion_queda_armada_y_sin_vestir(es_host, conexion, errores):
    sesion = _configurar(es_host, conexion, _sesion([Ciudadano, Candidato]))
    assert sesion.adaptador_red is not None and len(sesion.entradas) == 2
    assert _apariencias(sesion) == [None, None]  # la hoja de cada rol
    assert errores == ["_vestir_jugadores"]


@pytest.mark.parametrize("es_host", [True, False], ids=["host", "invitado"])
@pytest.mark.parametrize("sesion", [SimpleNamespace(), SimpleNamespace(jugadores=[])],
                         ids=["sin_atributo", "lista_vacia"])
def test_sin_jugadores_la_sesion_queda_armada(es_host, sesion, errores):
    servidor = Servidor()
    servidor.sala = _sala((0, 1))
    _configurar(es_host, servidor, sesion)
    assert sesion.adaptador_red is not None and len(sesion.entradas) == 2
    assert errores == ["_vestir_jugadores"]


class _SalaRota:
    """Falla al pedir la apariencia del segundo jugador."""

    def jugadores(self):
        return [0, 1]

    def apariencia_de(self, jid):
        if jid == 1:
            raise RuntimeError("sala corrupta")
        return Apariencia(piel=2)


def test_si_la_sala_falla_a_medias_nadie_queda_vestido(errores):
    sesion = _configurar(True, SimpleNamespace(sala=_SalaRota()), _sesion([Ciudadano, Candidato]))
    assert sesion.adaptador_red is not None
    assert _apariencias(sesion) == [None, None]
    assert errores == ["_vestir_jugadores"]


class _SalaConDatosRaros:
    """Cada id trae algo que no es una Apariencia válida."""

    DATOS = {
        0: Apariencia(piel=len(assets.TONOS_PIEL)),  # tono fuera de rango, construida a mano
        1: {"piel": 99, "cabeza": "candidato", "traje": "Ciudadano"},  # dict de red a medias
        2: "basura",
    }

    def jugadores(self):
        return sorted(self.DATOS)

    def apariencia_de(self, jid):
        return self.DATOS[jid]


def test_lo_invalido_se_valida_como_lo_que_llega_por_red(errores):
    clases = [Ciudadano, Influencer, Candidato]
    sesion = ConfigSesionHost(SimpleNamespace(sala=_SalaConDatosRaros()), clases,
                              ids_red=[0, 1, 2]).configurar_sesion(_sesion(clases))
    assert _apariencias(sesion) == [PREDETERMINADA, Apariencia(cabeza="candidato"), PREDETERMINADA]
    for jugador in sesion.jugadores:
        jugador.dibujar(pygame.Surface((100, 100)))  # ningún tono inválido llega al dibujo
    assert errores == []
