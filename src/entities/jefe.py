"""Jefe final "Servidor Central" (lógica pura, sin Pygame).

Lo gobierna un behavior tree propio (src/ai/behavior_tree.py). Cada
frame se hace tick() a esta raíz; el Selector ejecuta la PRIMERA rama
cuya condición se cumpla:

    Selector
    ├── Sequence "cambio de fase": ¿en pausa? -> telegrafiar (no ataca)
    ├── Sequence "fase 3": ¿fase 3? -> acercarse -> ráfaga -> espiral -> charco
    ├── Sequence "fase 2": ¿fase 2? -> espiral -> disparo dirigido
    └── Sequence "fase 1": ¿fase 1? -> ráfaga radial -> invocar súbditos

La fase sale del % de vida restante (fase_por_vida). Al cambiar de
fase el jefe deja de atacar PAUSA_CAMBIO_FASE segundos y parpadea, para
telegrafiar el cambio; al entrar a fase 2 recupera el escudo de
anonimato.

Este módulo no crea proyectiles de Pygame: describe cada disparo como
un DisparoJefe (datos) en una SalidaJefe, y la arena
(src/dungeon/arena_jefe.py) los convierte en proyectiles reales. Así
toda la lógica del jefe se prueba sin Pygame. La arena también le
asigna `rect` (un pygame.Rect) para las colisiones; el jefe solo lo
mantiene centrado en su posición.

El jefe se comporta como un enemigo más ante los ataques de los roles
(vivo, rect, recibir_dano, escudo_anonimato, empujar, forzar_objetivo),
así el loop de colisiones de Main.py no necesita saber que es un jefe.
"""

import math
import random
from dataclasses import dataclass, field

from src.ai.behavior_tree import EXITO, FALLO, Action, Selector, Sequence
from src.core import assets
from src.core.balance import (
    CHARCO_INTERVALO,
    CHARCO_RADIO,
    DIRIGIDO_INTERVALO,
    DIRIGIDO_VELOCIDAD,
    DURACION_DESTELLO_DANIO,
    ESCUDO_VIDA,
    ESPIRAL_BRAZOS,
    ESPIRAL_INTERVALO,
    ESPIRAL_PASO_GRADOS,
    ESPIRAL_VELOCIDAD,
    FACTOR_INTERVALO_FASE_3,
    INVOCACION_CANTIDAD,
    INVOCACION_INTERVALO,
    PAUSA_CAMBIO_FASE,
    RAFAGA_CANTIDAD,
    RAFAGA_INTERVALO,
    RAFAGA_VELOCIDAD,
    UMBRAL_FASE_2,
    UMBRAL_FASE_3,
    VELOCIDAD_MOVIMIENTO_JEFE,
    VIDA_JEFE,
)
from src.dungeon.charco import Charco

EVENTO_CAMBIO_FASE = "cambio_fase"
EVENTO_ESCUDO_ROTO = "escudo_roto"


def fase_por_vida(fraccion):
    """Fase (1, 2 o 3) según la fracción de vida restante (0.0 a 1.0).

    > 60% -> fase 1; > 30% -> fase 2; el resto -> fase 3. Justo en
    60% ya es fase 2 y justo en 30% ya es fase 3.
    """
    if fraccion > UMBRAL_FASE_2:
        return 1
    if fraccion > UMBRAL_FASE_3:
        return 2
    return 3


@dataclass
class DisparoJefe:
    """Descripción de un proyectil del jefe: origen, dirección unitaria, velocidad."""

    x: float
    y: float
    dx: float
    dy: float
    velocidad: float


@dataclass
class SalidaJefe:
    """Lo que el jefe produjo en un frame; la arena lo materializa."""

    disparos: list = field(default_factory=list)
    charcos: list = field(default_factory=list)
    invocaciones: int = 0


class Jefe:
    def __init__(self, x, y, limites, rng=None):
        """`limites` = (izquierda, arriba, derecha, abajo) del cuarto."""
        self.x = x
        self.y = y
        self.limites = limites
        self.rng = rng or random.Random()
        self.rect = None  # lo asigna la arena; aquí solo se mantiene centrado

        self.vida_maxima = VIDA_JEFE
        self.vida = VIDA_JEFE
        self.fase = 1
        self._vida_escudo = 0
        self.tiempo_pausa = 0.0  # > 0: cambiando de fase, no ataca
        self.tiempo_destello = 0.0  # > 0: acaba de recibir un impacto
        # Eventos para el "juice" (sacudida); la mazmorra los consume.
        self.eventos = []

        # Segundos que faltan para cada ataque. Arrancan en su intervalo
        # para que el jugador tenga un respiro al empezar la pelea.
        self._cooldowns = {
            "rafaga": RAFAGA_INTERVALO,
            "invocar": INVOCACION_INTERVALO,
            "espiral": 0.0,
            "dirigido": DIRIGIDO_INTERVALO,
            "charco": CHARCO_INTERVALO,
        }
        self._giro_rafaga = 0.0  # cada ráfaga se gira medio hueco: cambia el camino seguro
        self._angulo_espiral = 0.0

        # Contexto del frame, lo llena actualizar() antes del tick.
        self._dt = 0.0
        self._objetivo = (x, y)
        self._salida = None

        self.arbol = Selector(
            [
                # Cambio de fase: mientras dure la pausa esta rama tiene
                # éxito y el Selector no llega a ninguna rama de ataque.
                Sequence([Action(self._en_cambio_de_fase), Action(self._telegrafiar)]),
                # Fase 3 (30%-0%): todo junto, intervalos 30% más cortos.
                Sequence(
                    [
                        Action(lambda: self._es_fase(3)),
                        Action(self._acercarse_al_jugador),
                        Action(self._rafaga_radial),
                        Action(self._espiral),
                        Action(self._soltar_charco),
                    ]
                ),
                # Fase 2 (60%-30%): espiral continua + disparo dirigido.
                Sequence(
                    [
                        Action(lambda: self._es_fase(2)),
                        Action(self._espiral),
                        Action(self._disparo_dirigido),
                    ]
                ),
                # Fase 1 (100%-60%): ráfaga radial + invocar súbditos.
                Sequence(
                    [
                        Action(lambda: self._es_fase(1)),
                        Action(self._rafaga_radial),
                        Action(self._invocar),
                    ]
                ),
            ]
        )

    # ------------------------------------------------------------------
    # Estado
    # ------------------------------------------------------------------

    @property
    def vivo(self):
        return self.vida > 0

    @property
    def fraccion_vida(self):
        return self.vida / self.vida_maxima

    @property
    def vida_escudo(self):
        return self._vida_escudo

    @property
    def escudo_anonimato(self):
        """Mismo atributo que en Enemigo: mientras sea True no pierde vida."""
        return self._vida_escudo > 0

    @escudo_anonimato.setter
    def escudo_anonimato(self, activo):
        # Asignar False es lo que hace el Fact-Checking del Periodista
        # (RayoPerforante.al_impactar): rompe el escudo de golpe.
        if activo:
            self._vida_escudo = ESCUDO_VIDA
        elif self._vida_escudo > 0:
            self._vida_escudo = 0
            self.eventos.append(EVENTO_ESCUDO_ROTO)

    # ------------------------------------------------------------------
    # Interfaz de "enemigo" que usan los ataques de los roles
    # ------------------------------------------------------------------

    def recibir_dano(self, danio):
        """Con escudo, cada impacto quita 1 de escudo (sin importar el
        daño) y la vida no baja. Sin escudo, baja la vida."""
        if not self.vivo:
            return
        self.tiempo_destello = DURACION_DESTELLO_DANIO
        if self.escudo_anonimato:
            self._vida_escudo -= 1
            if self._vida_escudo == 0:
                self.eventos.append(EVENTO_ESCUDO_ROTO)
            return
        self.vida = max(0.0, self.vida - danio)
        # Se revisa la fase en el acto: si este impacto cruza el 60%,
        # el escudo se levanta antes del siguiente impacto del frame.
        self._revisar_cambio_de_fase()

    def empujar(self, impulso):
        """El jefe es inmune al empuje del Influencer."""

    def forzar_objetivo(self, objetivo, duracion):
        """El jefe ya persigue siempre al jugador; ignora el aggro forzado."""

    # ------------------------------------------------------------------
    # Frame
    # ------------------------------------------------------------------

    def actualizar(self, dt, objetivo, salida):
        """Avanza temporizadores y hace tick al árbol.

        `objetivo` = (x, y) del jugador; `salida` = SalidaJefe donde se
        agregan disparos, charcos e invocaciones de este frame.
        """
        self._dt = dt
        self._objetivo = objetivo
        self._salida = salida

        self.tiempo_pausa = max(0.0, self.tiempo_pausa - dt)
        self.tiempo_destello = max(0.0, self.tiempo_destello - dt)
        for nombre in self._cooldowns:
            self._cooldowns[nombre] -= dt

        self._revisar_cambio_de_fase()
        if self.vivo:
            self.arbol.tick()
        self._sincronizar_rect()

    def _revisar_cambio_de_fase(self):
        if not self.vivo:
            return
        nueva = fase_por_vida(self.fraccion_vida)
        if nueva <= self.fase:
            return
        self.fase = nueva
        self.tiempo_pausa = PAUSA_CAMBIO_FASE
        self.eventos.append(EVENTO_CAMBIO_FASE)
        if nueva == 2:
            self.escudo_anonimato = True

    def _sincronizar_rect(self):
        if self.rect is not None:
            self.rect.center = (round(self.x), round(self.y))

    def _intervalo(self, base):
        return base * FACTOR_INTERVALO_FASE_3 if self.fase == 3 else base

    def _consumir(self, nombre, intervalo):
        """True si el ataque `nombre` está listo, y lo recarga.

        Se conserva el sobrante del frame (restante + intervalo) para
        que la cadencia no dependa del framerate.
        """
        restante = self._cooldowns[nombre]
        if restante > 0:
            return False
        self._cooldowns[nombre] = max(restante + intervalo, 0.0)
        return True

    def _disparar(self, angulo_grados, velocidad):
        rad = math.radians(angulo_grados)
        self._salida.disparos.append(
            DisparoJefe(self.x, self.y, math.cos(rad), math.sin(rad), velocidad)
        )

    # ------------------------------------------------------------------
    # Hojas del árbol (las de ataque siempre retornan EXITO, aunque estén
    # en cooldown, para no cortar la Sequence de su fase)
    # ------------------------------------------------------------------

    def _en_cambio_de_fase(self):
        return EXITO if self.tiempo_pausa > 0 else FALLO

    def _telegrafiar(self):
        # El parpadeo lo dibuja la arena a partir de tiempo_pausa.
        return EXITO

    def _es_fase(self, numero):
        return EXITO if self.fase == numero else FALLO

    def _rafaga_radial(self):
        if self._consumir("rafaga", self._intervalo(RAFAGA_INTERVALO)):
            paso = 360 / RAFAGA_CANTIDAD
            for i in range(RAFAGA_CANTIDAD):
                self._disparar(self._giro_rafaga + i * paso, RAFAGA_VELOCIDAD)
            self._giro_rafaga += paso / 2
        return EXITO

    def _invocar(self):
        if self._consumir("invocar", INVOCACION_INTERVALO):
            self._salida.invocaciones += INVOCACION_CANTIDAD
        return EXITO

    def _espiral(self):
        if self._consumir("espiral", self._intervalo(ESPIRAL_INTERVALO)):
            for brazo in range(ESPIRAL_BRAZOS):
                self._disparar(
                    self._angulo_espiral + brazo * 360 / ESPIRAL_BRAZOS, ESPIRAL_VELOCIDAD
                )
            self._angulo_espiral += ESPIRAL_PASO_GRADOS
        return EXITO

    def _disparo_dirigido(self):
        if self._consumir("dirigido", DIRIGIDO_INTERVALO):
            dx = self._objetivo[0] - self.x
            dy = self._objetivo[1] - self.y
            if dx or dy:
                self._disparar(math.degrees(math.atan2(dy, dx)), DIRIGIDO_VELOCIDAD)
        return EXITO

    def _acercarse_al_jugador(self):
        dx = self._objetivo[0] - self.x
        dy = self._objetivo[1] - self.y
        distancia = math.hypot(dx, dy)
        paso = VELOCIDAD_MOVIMIENTO_JEFE * self._dt
        if distancia > paso:
            self.x += dx / distancia * paso
            self.y += dy / distancia * paso
        # Se queda dentro del cuarto, con todo su cuerpo.
        mitad = assets.TAMANIO_JEFE / 2
        izquierda, arriba, derecha, abajo = self.limites
        self.x = min(max(self.x, izquierda + mitad), derecha - mitad)
        self.y = min(max(self.y, arriba + mitad), abajo - mitad)
        return EXITO

    def _soltar_charco(self):
        if self._consumir("charco", CHARCO_INTERVALO):
            izquierda, arriba, derecha, abajo = self.limites
            x = self.rng.uniform(izquierda + CHARCO_RADIO, derecha - CHARCO_RADIO)
            y = self.rng.uniform(arriba + CHARCO_RADIO, abajo - CHARCO_RADIO)
            self._salida.charcos.append(Charco(x, y))
        return EXITO
