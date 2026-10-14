"""Tests de los nodos de comportamiento de los tipos de enemigo y de la
gracia de entrada, con agentes falsos (sin pygame)."""

import math
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest  # noqa: E402

from src.ai.behavior_tree import EXITO, FALLO  # noqa: E402
from src.ai.nodos_combate import (  # noqa: E402
    CurarAliado,
    DispararApuntado,
    DistanciaMenorQue,
    Huir,
    MantenerDistancia,
    punto_detras,
)
from src.core.balance import GRACIA_ENTRADA_CUARTO_S  # noqa: E402
from src.dungeon.gracia_entrada import GraciaEntrada  # noqa: E402


class Agente:
    """Implementa la interfaz de agente de nodos_combate sin pygame."""

    def __init__(self, xy=(0.0, 0.0), objetivo=(100.0, 0.0), velocidad=100.0, dt=0.1):
        self.xy = xy
        self.objetivo_xy = objetivo
        self.velocidad = velocidad
        self.dt = dt
        self.recarga_disparo = 0.0
        self.telegrafia = 0.0
        self.disparos = []
        self.tiempo = 0.0
        self.cooldown_cura = 0.0
        self.aliados = []
        self.curados = []
        self.vida, self.vida_maxima = 1, 2
        self.vivo = True
        self.curable = True
        self.curaciones_recibidas = 0

    def mover(self, dx, dy, factor=1.0):
        paso = self.velocidad * factor * self.dt
        self.xy = (self.xy[0] + dx * paso, self.xy[1] + dy * paso)

    def disparar_hacia_objetivo(self):
        self.disparos.append(self.tiempo)

    def al_curar(self, aliado):
        self.curados.append(aliado)


class Aliado:
    def __init__(self, xy, vida, vida_maxima=3, curable=True):
        self.xy, self.vida, self.vida_maxima = xy, vida, vida_maxima
        self.curable, self.vivo, self.curaciones_recibidas = curable, True, 0


def distancia(agente):
    return math.dist(agente.xy, agente.objetivo_xy)


# ----------------------------------------------------------------------
# Gracia de entrada
# ----------------------------------------------------------------------

def test_gracia_empieza_en_un_segundo_baja_y_termina():
    gracia = GraciaEntrada()
    assert not gracia.activa
    gracia.iniciar()
    assert gracia.restante == GRACIA_ENTRADA_CUARTO_S == 1.0
    assert gracia.activa and gracia.fraccion == 1.0
    gracia.actualizar(0.4)
    assert gracia.restante == pytest.approx(0.6) and gracia.activa
    gracia.actualizar(0.7)
    assert gracia.restante == 0.0 and not gracia.activa and gracia.fraccion == 0.0
    gracia.iniciar()  # se reinicia completa
    assert gracia.restante == 1.0


# ----------------------------------------------------------------------
# Nodos
# ----------------------------------------------------------------------

def test_distancia_menor_que():
    agente = Agente(objetivo=(150, 0))
    assert DistanciaMenorQue(agente, 200).tick() == EXITO
    assert DistanciaMenorQue(agente, 100).tick() == FALLO


def test_huir_se_aleja():
    agente = Agente(objetivo=(50, 0))
    antes = distancia(agente)
    assert Huir(agente).tick() == EXITO
    assert distancia(agente) == pytest.approx(antes + 10)


@pytest.mark.parametrize("inicial, cambio", [(100, "aleja"), (600, "acerca"), (320, "orbita")])
def test_mantener_distancia(inicial, cambio):
    agente = Agente(objetivo=(inicial, 0))
    nodo = MantenerDistancia(agente, 320, 40, 0.5)
    antes = distancia(agente)
    assert nodo.tick() == EXITO
    despues = distancia(agente)
    if cambio == "aleja":
        assert despues > antes
    elif cambio == "acerca":
        assert despues < antes
    else:
        assert despues == pytest.approx(antes, abs=1)
        assert agente.xy[1] != 0  # se movió de lado


def test_disparar_apuntado_respeta_cadencia_y_telegrafia():
    agente = Agente(dt=0.05)
    nodo = DispararApuntado(agente, cadencia_s=1.8, telegrafia_s=0.25)
    telegrafiando_antes_de_disparar = []
    for paso in range(int(5 / agente.dt)):
        agente.tiempo = paso * agente.dt
        tele_antes = agente.telegrafia
        cantidad = len(agente.disparos)
        assert nodo.tick() == EXITO
        if len(agente.disparos) > cantidad:
            telegrafiando_antes_de_disparar.append(tele_antes > 0)
    assert len(agente.disparos) == 3
    assert all(telegrafiando_antes_de_disparar)
    # El primero sale tras la telegrafía; los demás cada cadencia + telegrafía.
    assert agente.disparos[0] == pytest.approx(0.25, abs=0.06)
    for a, b in zip(agente.disparos, agente.disparos[1:]):
        assert b - a == pytest.approx(1.8 + 0.25, abs=0.11)


def nodo_cura(agente, max_curas=2):
    return CurarAliado(agente, intervalo_s=3.0, fraccion=0.34, radio=280, max_curas=max_curas)


def test_curar_aliado_cura_al_mas_herido_en_el_radio():
    agente = Agente()
    poco = Aliado((50, 0), vida=2.5)
    mucho = Aliado((60, 0), vida=1)
    lejos = Aliado((900, 0), vida=0.5)
    agente.aliados = [agente, poco, mucho, lejos]
    nodo_cura(agente).tick()
    assert mucho.vida == pytest.approx(1 + 3 * 0.34)
    assert poco.vida == 2.5 and lejos.vida == 0.5
    assert agente.curados == [mucho] and agente.cooldown_cura == 3.0


def test_curar_no_se_cura_a_si_mismo_ni_al_jefe():
    agente = Agente()  # herido: vida 1 de 2
    jefe = Aliado((10, 0), vida=10, vida_maxima=120, curable=False)
    agente.aliados = [agente, jefe]
    nodo_cura(agente).tick()
    assert agente.vida == 1 and jefe.vida == 10 and agente.curados == []


def test_curar_respeta_el_intervalo_y_el_limite_por_aliado():
    agente = Agente(dt=0.5)
    herido = Aliado((10, 0), vida=0.1, vida_maxima=10)
    agente.aliados = [herido]
    nodo = nodo_cura(agente, max_curas=2)
    for _ in range(int(20 / agente.dt)):  # 20 s: daría para 7 curas sin límite
        nodo.tick()
    assert herido.curaciones_recibidas == 2
    assert len(agente.curados) == 2


def test_curar_espera_el_intervalo_entre_curas():
    agente = Agente(dt=1.0)
    herido = Aliado((10, 0), vida=0.1, vida_maxima=10)
    agente.aliados = [herido]
    nodo = nodo_cura(agente, max_curas=5)
    nodo.tick()  # cura ya (cooldown inicial 0)
    nodo.tick()
    nodo.tick()
    assert herido.curaciones_recibidas == 1
    nodo.tick()  # pasaron 3 s
    assert herido.curaciones_recibidas == 2


def test_punto_detras_de_los_aliados():
    assert punto_detras([], (0, 0), 100) is None
    punto = punto_detras([(100, 0), (100, 20)], (0, 10), 50)
    assert punto == pytest.approx((150, 10))
