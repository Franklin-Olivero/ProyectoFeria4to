"""Dibujo de los enemigos (solo presentación).

La imagen sale siempre de sprites.sprite_enemigo(tipo): cambiar el arte
de un tipo no toca este módulo. Encima van los estados que el jugador
debe leer:
    - gracia de entrada (`congelado`): el sprite parpadea con alfa pulsante;
    - telegrafía del tirador (`telegrafia` > 0): se ilumina antes de disparar;
    - escudo de anonimato: marco celeste;
    - curandero: rayo verde con partículas hacia el aliado que acaba de
      curar y contorno magenta cuando entra en pánico.
"""

import math

import pygame

from src.core import assets
from src.ui import sprites


def dibujar_enemigo(pantalla, enemigo):
    imagen = sprites.sprite_enemigo(enemigo.tipo)
    if getattr(enemigo, "telegrafia", 0) > 0:
        imagen = imagen.copy()
        imagen.fill(assets.COLOR_TELEGRAFIA_TIRADOR, special_flags=pygame.BLEND_RGB_MAX)
    if enemigo.congelado:
        pulso = 0.5 + 0.5 * math.sin(2 * math.pi * enemigo.reloj / assets.PERIODO_PARPADEO_GRACIA)
        imagen = imagen.copy()
        imagen.set_alpha(round(assets.ALFA_MIN_ENEMIGO_GRACIA
                               + (assets.ALFA_MAX_ENEMIGO_GRACIA - assets.ALFA_MIN_ENEMIGO_GRACIA) * pulso))
    pantalla.blit(imagen, imagen.get_rect(center=enemigo.rect.center))

    if enemigo.escudo_anonimato:
        pygame.draw.rect(pantalla, assets.COLOR_ESCUDO_JEFE, enemigo.rect.inflate(8, 8), 2, border_radius=4)
    if getattr(enemigo, "en_panico", False):
        pygame.draw.rect(pantalla, assets.COLOR_PANICO_CURANDERO, enemigo.rect.inflate(6, 6), 2, border_radius=6)
    aliado = getattr(enemigo, "efecto_cura", None)
    if aliado is not None:
        _dibujar_rayo_cura(pantalla, enemigo, aliado)


def _dibujar_rayo_cura(pantalla, curandero, aliado):
    inicio = pygame.Vector2(curandero.rect.center)
    fin = pygame.Vector2(aliado.rect.center)
    pygame.draw.line(pantalla, assets.COLOR_RAYO_CURA, inicio, fin, assets.GROSOR_RAYO_CURA)
    # Partículas que viajan del curandero al aliado.
    lado = assets.TAMANIO_PARTICULA_CURA
    for i in range(assets.CANTIDAD_PARTICULAS_CURA):
        t = (i / assets.CANTIDAD_PARTICULAS_CURA + curandero.reloj * 2) % 1.0
        punto = inicio.lerp(fin, t) + pygame.Vector2(0, -6 * math.sin(t * math.pi * 3 + i))
        pygame.draw.rect(pantalla, assets.COLOR_PARTICULA_CURA, (punto.x - lado / 2, punto.y - lado / 2, lado, lado))
