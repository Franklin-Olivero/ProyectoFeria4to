"""Enemigo controlado por un árbol de comportamiento (ver
src/ai/behavior_tree.py).

Cada frame, `actualizar` guarda el contexto del frame (jugador, dt,
lista de salida de proyectiles) y hace tick() al árbol raíz, que es:

    Selector
    ├── Sequence: "¿jugador en rango?" -> "perseguir" -> "disparar"
    └── Action: "quedarse quieto" (siempre EXITO)

Es decir: si el jugador está en rango de disparo, el enemigo lo
persigue y le dispara; si no, se queda quieto (patrulla mínima viable
para el MVP, más simple de sustentar que un recorrido de puntos).
"""

import pygame

from src.ai.behavior_tree import EXITO, FALLO, Action, Selector, Sequence
from src.core import assets
from src.entities.projectile import Proyectil


class Enemigo:
    def __init__(self, x, y):
        self.rect = pygame.Rect(0, 0, assets.TAMANIO_ENEMIGO, assets.TAMANIO_ENEMIGO)
        self.rect.center = (x, y)
        # Posición en punto flotante: pygame.Rect solo guarda enteros,
        # así que mover el rect directamente con incrementos fraccionarios
        # (velocidad * dt) trunca la parte decimal cada frame y la
        # velocidad real termina siendo menor a la configurada. Se
        # acumula aquí y el rect se sincroniza redondeando cada frame.
        self.posicion = pygame.Vector2(self.rect.center)
        self.vida = assets.VIDA_ENEMIGO
        self.cooldown_disparo = 0.0

        # Contexto del frame actual; lo llena `actualizar` antes del
        # tick para que las acciones del árbol (sin argumentos, por
        # diseño de Action) puedan leerlo.
        self._jugador = None
        self._dt = 0.0
        self._proyectiles_salida = None

        self.arbol = Selector(
            [
                Sequence(
                    [
                        Action(self._en_rango_de_disparo),
                        Action(self._perseguir_jugador),
                        Action(self._disparar_a_jugador),
                    ]
                ),
                Action(self._quedarse_quieto),
            ]
        )

    @property
    def vivo(self):
        return self.vida > 0

    def actualizar(self, dt, jugador, proyectiles_enemigos):
        """Ejecuta un tick del árbol de comportamiento para este frame."""
        self._jugador = jugador
        self._dt = dt
        self._proyectiles_salida = proyectiles_enemigos

        if self.cooldown_disparo > 0:
            self.cooldown_disparo -= dt

        self.arbol.tick()

    def _en_rango_de_disparo(self):
        distancia = pygame.Vector2(self.rect.center).distance_to(self._jugador.rect.center)
        return EXITO if distancia <= assets.RANGO_DISPARO_ENEMIGO else FALLO

    def _perseguir_jugador(self):
        direccion = pygame.Vector2(self._jugador.rect.center) - self.posicion
        if direccion.length_squared() > 0:
            direccion = direccion.normalize()
            self.posicion += direccion * assets.VELOCIDAD_ENEMIGO * self._dt
            self.rect.center = (round(self.posicion.x), round(self.posicion.y))
        return EXITO

    def _disparar_a_jugador(self):
        # Este nodo siempre retorna EXITO, incluso en cooldown: el
        # cooldown solo bloquea la creación del proyectil, no el
        # resultado del nodo. Si retornara FALLO durante el cooldown,
        # la Sequence completa fallaría y el Selector caería a
        # "quedarse quieto", interrumpiendo la persecución cada vez que
        # el enemigo no puede disparar. Así, perseguir nunca se
        # interrumpe por el cooldown de disparo.
        if self.cooldown_disparo <= 0:
            direccion = pygame.Vector2(self._jugador.rect.center) - pygame.Vector2(
                self.rect.center
            )
            if direccion.length_squared() > 0:
                proyectil = Proyectil(
                    posicion=self.rect.center,
                    direccion=direccion,
                    velocidad=assets.VELOCIDAD_PROYECTIL,
                    danio=assets.DANIO_PROYECTIL_ENEMIGO,
                    color=assets.COLOR_PROYECTIL_ENEMIGO,
                )
                self._proyectiles_salida.append(proyectil)
                self.cooldown_disparo = assets.COOLDOWN_DISPARO_ENEMIGO
        return EXITO

    def _quedarse_quieto(self):
        return EXITO

    def recibir_dano(self, danio):
        self.vida -= danio

    def dibujar(self, pantalla):
        pygame.draw.rect(pantalla, assets.COLOR_ENEMIGO, self.rect)
