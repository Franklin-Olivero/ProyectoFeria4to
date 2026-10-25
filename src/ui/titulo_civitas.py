"""Título "CIVITAS" del menú principal con resplandor y glitch (solo presentación).

Las letras son pixel art dibujado en código (src/ui/sprites.py,
LETRAS_TITULO), igual que el resto de sprites: no hay fuente pixel en
el repositorio. Se componen una sola vez con su sombra y un resplandor
violeta difuminado.

Efectos, breves y poco frecuentes para que el título siempre se lea:
    - scanlines fijas grabadas en las letras (no se mueven);
    - cada INTERVALO_GLITCH_TITULO segundos, durante DURACION_GLITCH_TITULO:
      separación cromática (copias cian y magenta corridas unos píxeles),
      dos o tres franjas horizontales desplazadas y un destello de brillo.
El texto original se dibuja siempre completo debajo de los efectos.
Con reducir_movimiento no hay glitch: solo el título con su resplandor.
"""

import random

import pygame

from src.core import assets
from src.ui import sprites


class TituloCivitas:
    def __init__(self, semilla=assets.SEMILLA_FONDO_CIUDAD):
        self._rng = random.Random(semilla)
        escala = assets.ESCALA_TITULO
        self.letras = _componer(sprites.palabra_titulo(assets.COLOR_TITULO, assets.COLOR_TITULO_LUZ), escala)
        sombra = _componer(sprites.palabra_titulo(assets.COLOR_TITULO_SOMBRA, assets.COLOR_TITULO_SOMBRA), escala)
        # Letras + sombra corrida hacia abajo (relieve de cartel).
        desfase = escala
        self.imagen = pygame.Surface((self.letras.get_width(), self.letras.get_height() + desfase), pygame.SRCALPHA)
        self.imagen.blit(sombra, (0, desfase))
        self.imagen.blit(self.letras, (0, 0))
        _grabar_scanlines(self.imagen)
        self.resplandor = _resplandor(self.letras, assets.COLOR_RESPLANDOR_TITULO, assets.RADIO_RESPLANDOR_TITULO)
        # Copias de un solo color sobre negro, para sumarlas con BLEND_ADD.
        self.cian = _sobre_negro(_colorear(self.letras, assets.COLOR_GLITCH_CIAN))
        self.magenta = _sobre_negro(_colorear(self.letras, assets.COLOR_GLITCH_MAGENTA))
        self.destello = _sobre_negro(_colorear(self.letras, assets.COLOR_DESTELLO_TITULO))
        self._glitch = 0.0  # segundos que le quedan al glitch actual
        self._proximo = self._rng.uniform(*assets.INTERVALO_GLITCH_TITULO)
        self._franjas = []
        self._separacion = 0

    def actualizar(self, dt, reducir_movimiento):
        if reducir_movimiento:
            self._glitch = 0.0
            return
        if self._glitch > 0:
            self._glitch -= dt
            return
        self._proximo -= dt
        if self._proximo <= 0:
            self._proximo = self._rng.uniform(*assets.INTERVALO_GLITCH_TITULO)
            self._glitch = assets.DURACION_GLITCH_TITULO
            self._separacion = self._rng.randint(*assets.SEPARACION_CROMATICA_TITULO)
            alto = self.letras.get_height()
            self._franjas = [
                (self._rng.randrange(0, alto - 8), self._rng.randint(4, 12),
                 self._rng.choice((-1, 1)) * self._rng.randint(*assets.DESPLAZAMIENTO_FRANJA_TITULO))
                for _ in range(self._rng.randint(2, 3))
            ]

    def dibujar(self, pantalla, centro):
        rect = self.imagen.get_rect(center=centro)
        pantalla.blit(self.resplandor, self.resplandor.get_rect(center=rect.center),
                      special_flags=pygame.BLEND_ADD)
        if self._glitch > 0:
            d = self._separacion
            pantalla.blit(self.cian, (rect.x - d, rect.y), special_flags=pygame.BLEND_ADD)
            pantalla.blit(self.magenta, (rect.x + d, rect.y), special_flags=pygame.BLEND_ADD)
        pantalla.blit(self.imagen, rect)
        if self._glitch > 0:
            for y, alto, dx in self._franjas:
                franja = pygame.Rect(0, y, self.letras.get_width(), alto)
                pantalla.blit(self.letras, (rect.x + dx, rect.y + y), franja)
            pantalla.blit(self.destello, rect, special_flags=pygame.BLEND_ADD)
        return rect


def _componer(filas_y_paleta, escala):
    filas, paleta = filas_y_paleta
    return sprites.sprite(filas, paleta, escala)


def _colorear(superficie, color):
    """Misma silueta en un solo color (para la separación cromática)."""
    copia = superficie.copy()
    copia.fill((0, 0, 0, 255), special_flags=pygame.BLEND_RGBA_MULT)
    copia.fill((*color, 0), special_flags=pygame.BLEND_RGBA_ADD)
    return copia


def _sobre_negro(superficie):
    """Copia sin alfa sobre fondo negro: con BLEND_ADD el negro no suma
    nada, así solo las letras aportan color."""
    resultado = pygame.Surface(superficie.get_size())
    resultado.blit(superficie, (0, 0))
    return resultado


def _resplandor(superficie, color, radio):
    """Silueta teñida y difuminada, con margen para que el brillo no se corte."""
    margen = radio * 3
    base = pygame.Surface((superficie.get_width() + margen * 2, superficie.get_height() + margen * 2),
                          pygame.SRCALPHA)
    base.blit(_colorear(superficie, color), (margen, margen))
    return _sobre_negro(pygame.transform.gaussian_blur(base, radio))


def _grabar_scanlines(superficie):
    """Oscurece una fila de cada PASO_SCANLINES_TITULO. Multiplica solo el
    color, así lo transparente alrededor de las letras sigue transparente."""
    factor = assets.BRILLO_SCANLINES_TITULO
    for y in range(0, superficie.get_height(), assets.PASO_SCANLINES_TITULO):
        superficie.fill((factor, factor, factor, 255), (0, y, superficie.get_width(), 1),
                        special_flags=pygame.BLEND_RGBA_MULT)
