"""Jefe final "Servidor Central" (lógica pura, sin Pygame).

Lo gobierna un behavior tree propio (src/ai/behavior_tree.py). Cada
frame se hace tick() a esta raíz; el Selector ejecuta la PRIMERA rama
cuya condición se cumpla:

    Selector
    ├── Sequence "cambio de fase": ¿en pausa? -> telegrafiar (no ataca)
    ├── Sequence "fase 3": ¿fase 3? -> acercarse -> avanzar ciclo -> Selector
    │       ├── Sequence: ¿descanso? -> descansar (sin emisiones)
    │       └── Sequence: ráfagas del ciclo -> espiral del ciclo -> dirigido -> charco
    ├── Sequence "fase 2": ¿fase 2? -> espiral -> disparo dirigido
    └── Sequence "fase 1": ¿fase 1? -> ráfaga radial -> invocar súbditos

Regla de diseño: TODO patrón deja un pasillo esquivable.
    - La ráfaga radial sale siempre con JEFE_RADIAL_HUECO balas
      consecutivas faltantes, y el hueco salta a más de
      JEFE_RADIAL_SEPARACION_HUECO grados del anterior (hay que moverse).
    - La espiral tiene a lo sumo 2 brazos, gira lento y sus balas van a
      la misma velocidad que las de la fase 1.
    - La fase 3 no lo combina todo: es un ciclo de FASE3_CICLO s
      (2 ráfagas, luego espiral, luego FASE3_DESCANSO s sin ataques).
    - Nunca hay más de MAX_PROYECTILES_JEFE balas del jefe vivas: la
      arena le informa cuántas hay y, con el tope lleno, omite emitir.

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
from src.audio import eventos_sonido
from src.core import assets
from src.core.balance import (
    CHARCO_DISTANCIA_MIN_JUGADOR,
    CHARCO_INTERVALO,
    CHARCO_MAXIMO_ACTIVOS,
    CHARCO_RADIO,
    DIRIGIDO_INTERVALO,
    DIRIGIDO_MARGEN_RAFAGA,
    DIRIGIDO_VELOCIDAD,
    DURACION_DESTELLO_DANIO,
    ESCUDO_VIDA,
    ESPIRAL_INTERVALO,
    ESPIRAL_VELOCIDAD,
    FASE3_CICLO,
    FASE3_DESCANSO,
    FASE3_ESPIRAL_DURACION,
    FASE3_ESPIRAL_INICIO,
    FASE3_RAFAGAS,
    INVOCACION_CANTIDAD,
    INVOCACION_INTERVALO,
    JEFE_ESPIRAL_BRAZOS,
    JEFE_HUECO_DISTANCIA_MURO,
    JEFE_ESPIRAL_VEL_ANGULAR,
    JEFE_RADIAL_BALAS,
    JEFE_RADIAL_HUECO,
    JEFE_RADIAL_SEPARACION_HUECO,
    MAX_PROYECTILES_JEFE,
    PAUSA_CAMBIO_FASE,
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

PASO_RADIAL = 360 / JEFE_RADIAL_BALAS  # grados entre posiciones del círculo
INTENTOS_CHARCO = 30  # posiciones al azar probadas antes de omitir un charco


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


def distancia_angular(a, b):
    """Distancia en grados entre dos ángulos, en [0, 180]."""
    d = abs(a - b) % 360
    return min(d, 360 - d)


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
        # Ángulo (centro) del hueco de la última ráfaga; None si no hubo.
        self.ultimo_hueco = None
        self._angulo_espiral = 0.0
        self._tiempo_desde_rafaga = math.inf
        # Ciclo de la fase 3: segundos dentro del ciclo y ráfagas que
        # todavía faltan en este ciclo (pueden esperar al tope de balas).
        self.tiempo_ciclo = 0.0
        self._rafagas_pendientes = list(FASE3_RAFAGAS)
        self._primer_tick_ciclo = True  # el primer tick de la fase 3 es t = 0
        self._charcos = []  # charcos propios aún vivos (los actualiza la mazmorra)

        # Contexto del frame, lo llena actualizar() antes del tick.
        self._dt = 0.0
        self._objetivo = (x, y)
        self._salida = None
        self._balas_vivas = 0

        self.arbol = Selector(
            [
                # Cambio de fase: mientras dure la pausa esta rama tiene
                # éxito y el Selector no llega a ninguna rama de ataque.
                Sequence([Action(self._en_cambio_de_fase), Action(self._telegrafiar)]),
                # Fase 3 (30%-0%): ciclo ráfagas -> espiral -> descanso.
                Sequence(
                    [
                        Action(lambda: self._es_fase(3)),
                        Action(self._acercarse_al_jugador),
                        Action(self._avanzar_ciclo),
                        Selector(
                            [
                                Sequence([Action(self._en_descanso), Action(self._descansar)]),
                                Sequence(
                                    [
                                        Action(self._rafagas_del_ciclo),
                                        Action(self._espiral_del_ciclo),
                                        Action(self._dirigido_lejos_de_rafaga),
                                        Action(self._soltar_charco),
                                    ]
                                ),
                            ]
                        ),
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
                # Fase 1 (100%-60%): ráfaga radial con hueco + invocar súbditos.
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
        eventos_sonido.emitir("impacto_enemigo")
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

    def actualizar(self, dt, objetivo, salida, balas_vivas=0):
        """Avanza temporizadores y hace tick al árbol.

        `objetivo` = (x, y) del jugador; `salida` = SalidaJefe donde se
        agregan disparos, charcos e invocaciones de este frame;
        `balas_vivas` = proyectiles del jefe que siguen en la arena (para
        respetar MAX_PROYECTILES_JEFE).
        """
        self._dt = dt
        self._objetivo = objetivo
        self._salida = salida
        self._balas_vivas = balas_vivas

        self.tiempo_pausa = max(0.0, self.tiempo_pausa - dt)
        self.tiempo_destello = max(0.0, self.tiempo_destello - dt)
        self._tiempo_desde_rafaga += dt
        for nombre in self._cooldowns:
            # El piso -dt conserva el sobrante de un frame (cadencia
            # independiente del framerate) sin acumular disparos
            # atrasados mientras un ataque está fuera de su ventana.
            self._cooldowns[nombre] = max(self._cooldowns[nombre] - dt, -dt)
        self._charcos = [charco for charco in self._charcos if charco.vivo]

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
        if nueva == 3:
            self.tiempo_ciclo = 0.0
            self._rafagas_pendientes = list(FASE3_RAFAGAS)
            self._primer_tick_ciclo = True

    def _sincronizar_rect(self):
        if self.rect is not None:
            self.rect.center = (round(self.x), round(self.y))

    def _consumir(self, nombre, intervalo):
        """True si el ataque `nombre` está listo, y lo recarga.

        Se conserva el sobrante del frame (restante + intervalo) para
        que la cadencia no dependa del framerate.
        """
        restante = self._cooldowns[nombre]
        if restante > 0:
            return False
        self._cooldowns[nombre] = restante + intervalo
        return True

    def _hay_cupo(self, cantidad):
        """True si emitir `cantidad` balas más no pasa MAX_PROYECTILES_JEFE."""
        return self._balas_vivas + len(self._salida.disparos) + cantidad <= MAX_PROYECTILES_JEFE

    def _disparar(self, angulo_grados, velocidad):
        rad = math.radians(angulo_grados)
        self._salida.disparos.append(
            DisparoJefe(self.x, self.y, math.cos(rad), math.sin(rad), velocidad)
        )

    # ------------------------------------------------------------------
    # Hojas del árbol (las de ataque siempre retornan EXITO, aunque estén
    # en cooldown o sin cupo, para no cortar la Sequence de su fase)
    # ------------------------------------------------------------------

    def _en_cambio_de_fase(self):
        return EXITO if self.tiempo_pausa > 0 else FALLO

    def _telegrafiar(self):
        # El parpadeo lo dibuja la arena a partir de tiempo_pausa.
        return EXITO

    def _es_fase(self, numero):
        return EXITO if self.fase == numero else FALLO

    # --- Ráfaga radial con hueco --------------------------------------

    def elegir_hueco(self):
        """Índice de la primera bala faltante del hueco nuevo.

        Al azar entre las posiciones cuyo centro de hueco queda a más de
        JEFE_RADIAL_SEPARACION_HUECO grados del hueco anterior (siempre)
        y que no apuntan contra un muro cercano: en esa dirección debe
        haber JEFE_HUECO_DISTANCIA_MURO px de arena, si no el pasillo
        termina en la pared. Si ninguna cumple lo segundo (jefe pegado a
        una esquina), se usa la de más espacio entre las válidas.
        """
        candidatos = list(range(JEFE_RADIAL_BALAS))
        if self.ultimo_hueco is not None:
            candidatos = [
                i for i in candidatos
                if distancia_angular(self._centro_hueco(i), self.ultimo_hueco)
                > JEFE_RADIAL_SEPARACION_HUECO
            ]
        abiertos = [
            i for i in candidatos
            if self._distancia_al_muro(self._centro_hueco(i)) >= JEFE_HUECO_DISTANCIA_MURO
        ]
        if abiertos:
            return self.rng.choice(abiertos)
        return max(candidatos, key=lambda i: self._distancia_al_muro(self._centro_hueco(i)))

    def _distancia_al_muro(self, angulo_grados):
        """Px desde el jefe hasta el muro siguiendo `angulo_grados`."""
        izquierda, arriba, derecha, abajo = self.limites
        dx, dy = math.cos(math.radians(angulo_grados)), math.sin(math.radians(angulo_grados))
        distancias = []
        if dx > 1e-9:
            distancias.append((derecha - self.x) / dx)
        elif dx < -1e-9:
            distancias.append((izquierda - self.x) / dx)
        if dy > 1e-9:
            distancias.append((abajo - self.y) / dy)
        elif dy < -1e-9:
            distancias.append((arriba - self.y) / dy)
        return min(distancias)

    @staticmethod
    def _centro_hueco(inicio):
        """Ángulo del centro de un hueco que empieza en la posición `inicio`."""
        return (inicio + (JEFE_RADIAL_HUECO - 1) / 2) * PASO_RADIAL % 360

    def _emitir_rafaga(self):
        """Emite el círculo con hueco si hay cupo. True si salió."""
        if not self._hay_cupo(JEFE_RADIAL_BALAS - JEFE_RADIAL_HUECO):
            return False
        inicio = self.elegir_hueco()
        faltantes = {(inicio + k) % JEFE_RADIAL_BALAS for k in range(JEFE_RADIAL_HUECO)}
        for i in range(JEFE_RADIAL_BALAS):
            if i not in faltantes:
                self._disparar(i * PASO_RADIAL, RAFAGA_VELOCIDAD)
        self.ultimo_hueco = self._centro_hueco(inicio)
        self._tiempo_desde_rafaga = 0.0
        eventos_sonido.emitir("jefe_rafaga")
        return True

    def _rafaga_radial(self):
        """Fase 1: una ráfaga cada RAFAGA_INTERVALO (espera cupo si hace falta)."""
        if self._cooldowns["rafaga"] <= 0 and self._emitir_rafaga():
            self._consumir("rafaga", RAFAGA_INTERVALO)
        return EXITO

    def _invocar(self):
        if self._consumir("invocar", INVOCACION_INTERVALO):
            self._salida.invocaciones += INVOCACION_CANTIDAD
        return EXITO

    # --- Espiral y disparo dirigido -----------------------------------

    def _espiral(self):
        if self._cooldowns["espiral"] <= 0 and self._hay_cupo(JEFE_ESPIRAL_BRAZOS):
            self._consumir("espiral", ESPIRAL_INTERVALO)
            for brazo in range(JEFE_ESPIRAL_BRAZOS):
                self._disparar(
                    self._angulo_espiral + brazo * 360 / JEFE_ESPIRAL_BRAZOS, ESPIRAL_VELOCIDAD
                )
            self._angulo_espiral += JEFE_ESPIRAL_VEL_ANGULAR * ESPIRAL_INTERVALO
        return EXITO

    def _disparo_dirigido(self):
        if self._cooldowns["dirigido"] <= 0 and self._hay_cupo(1):
            self._consumir("dirigido", DIRIGIDO_INTERVALO)
            dx = self._objetivo[0] - self.x
            dy = self._objetivo[1] - self.y
            if dx or dy:
                self._disparar(math.degrees(math.atan2(dy, dx)), DIRIGIDO_VELOCIDAD)
        return EXITO

    # --- Ciclo de la fase 3 -------------------------------------------

    def _avanzar_ciclo(self):
        """Avanza el reloj del ciclo; al completarlo, reinicia las ráfagas."""
        if self._primer_tick_ciclo:
            self._primer_tick_ciclo = False
        else:
            self.tiempo_ciclo += self._dt
        if self.tiempo_ciclo >= FASE3_CICLO:
            self.tiempo_ciclo -= FASE3_CICLO
            self._rafagas_pendientes = list(FASE3_RAFAGAS)
        return EXITO

    def _en_descanso(self):
        return EXITO if self.tiempo_ciclo >= FASE3_CICLO - FASE3_DESCANSO else FALLO

    def _descansar(self):
        """Ventana sin ataques: el jugador puede castigar al jefe."""
        return EXITO

    def _rafagas_del_ciclo(self):
        """Emite la siguiente ráfaga pendiente cuando llega su momento.
        Si el tope de balas la retrasa hasta la espiral, se descarta (no
        se mezclan anillos con espiral)."""
        if self._rafagas_pendientes and self.tiempo_ciclo >= self._rafagas_pendientes[0]:
            if self.tiempo_ciclo >= FASE3_ESPIRAL_INICIO:
                self._rafagas_pendientes.clear()
            elif self._emitir_rafaga():
                self._rafagas_pendientes.pop(0)
        return EXITO

    def _espiral_del_ciclo(self):
        if FASE3_ESPIRAL_INICIO <= self.tiempo_ciclo < FASE3_ESPIRAL_INICIO + FASE3_ESPIRAL_DURACION:
            self._espiral()
        return EXITO

    def _dirigido_lejos_de_rafaga(self):
        """El disparo dirigido nunca sale junto a una ráfaga: espera
        DIRIGIDO_MARGEN_RAFAGA s, así no alcanza al anillo (es más
        rápido) ni tapa su hueco."""
        if self._tiempo_desde_rafaga >= DIRIGIDO_MARGEN_RAFAGA:
            self._disparo_dirigido()
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

    # --- Charcos ------------------------------------------------------

    def _soltar_charco(self):
        """Un charco cada CHARCO_INTERVALO s, con a lo sumo
        CHARCO_MAXIMO_ACTIVOS vivos, lejos del jugador y fuera del jefe."""
        if not self._consumir("charco", CHARCO_INTERVALO):
            return EXITO
        if len(self._charcos) >= CHARCO_MAXIMO_ACTIVOS:
            return EXITO
        posicion = self._posicion_para_charco()
        if posicion is not None:
            charco = Charco(*posicion)
            self._charcos.append(charco)
            self._salida.charcos.append(charco)
        return EXITO

    def _posicion_para_charco(self):
        """Centro al azar dentro de la arena que cumple las distancias, o
        None si en INTENTOS_CHARCO intentos no se encontró."""
        izquierda, arriba, derecha, abajo = self.limites
        lejos_jugador = CHARCO_DISTANCIA_MIN_JUGADOR + CHARCO_RADIO
        # Medio lado del jefe en diagonal: el charco no toca su cuerpo.
        lejos_jefe = CHARCO_RADIO + assets.TAMANIO_JEFE / 2 * math.sqrt(2)
        for _ in range(INTENTOS_CHARCO):
            x = self.rng.uniform(izquierda + CHARCO_RADIO, derecha - CHARCO_RADIO)
            y = self.rng.uniform(arriba + CHARCO_RADIO, abajo - CHARCO_RADIO)
            if (
                math.dist((x, y), self._objetivo) >= lejos_jugador
                and math.dist((x, y), (self.x, self.y)) >= lejos_jefe
            ):
                return (x, y)
        return None
