"""Partículas visuales (solo presentación: sin hitbox ni efecto en el juego).

El rastro del dash: cada frame que un jugador dashea, Main.py emite
DASH_PARTICULAS_POR_FRAME partículas con el color del rol donde está.
Cada una vive DASH_PARTICULA_DURACION segundos y, a medida que se le
acaba la vida, se encoge y se vuelve transparente.

    emitir(...)     agrega partículas al pool              O(k)
    actualizar(dt)  descuenta vida y quita las muertas     O(n)
    dibujar(sup)    pinta las vivas                        O(n)
"""

import random

import pygame

from src.core import assets


class Particula:
    """Un punto que se encoge y se desvanece hasta desaparecer."""

    def __init__(self, x, y, color_base, radio, vida):
        self.x = x
        self.y = y
        self.color_base = color_base
        self.radio = radio
        self.vida = vida
        self.vida_max = vida

    @property
    def viva(self):
        return self.vida > 0

    @property
    def fraccion(self):
        """1.0 recién nacida, 0.0 al morir."""
        return max(0.0, self.vida / self.vida_max)

    def dibujar(self, superficie):
        radio = round(self.radio * self.fraccion)
        if radio <= 0:
            return
        alfa = round(assets.DASH_PARTICULA_ALFA_INICIAL * self.fraccion)
        capa = pygame.Surface((radio * 2, radio * 2), pygame.SRCALPHA)
        pygame.draw.circle(capa, (*self.color_base[:3], alfa), (radio, radio), radio)
        superficie.blit(capa, (round(self.x) - radio, round(self.y) - radio))


class SistemaParticulas:
    """Pool de partículas activas."""

    def __init__(self, rng=None):
        self.particulas = []
        self._rng = rng or random.Random()

    def emitir(self, centro, color, cantidad=assets.DASH_PARTICULAS_POR_FRAME):
        """Agrega `cantidad` partículas alrededor de `centro`, un poco dispersas."""
        dispersion = assets.DASH_PARTICULA_DISPERSION
        for _ in range(cantidad):
            self.particulas.append(Particula(
                centro[0] + self._rng.uniform(-dispersion, dispersion),
                centro[1] + self._rng.uniform(-dispersion, dispersion),
                color,
                assets.DASH_PARTICULA_RADIO,
                assets.DASH_PARTICULA_DURACION,
            ))

    def actualizar(self, dt):
        for particula in self.particulas:
            particula.vida -= dt
        self.particulas = [particula for particula in self.particulas if particula.viva]

    def dibujar(self, superficie):
        for particula in self.particulas:
            particula.dibujar(superficie)

    def limpiar(self):
        self.particulas.clear()
