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
from src.ui import fuentes, sprites


_cache_nombres = {}


def _etiqueta_nombre(nombre):
    """Texto del nombre (blanco con sombra), cacheado."""
    if nombre not in _cache_nombres:
        fuente = fuentes.fuente(assets.TAMANIO_FUENTE_PEQUENA, negrita=True)
        texto = fuente.render(nombre, True, assets.COLOR_NOMBRE_ENEMIGO)
        sombra = fuente.render(nombre, True, assets.COLOR_SOMBRA_NOMBRE_ENEMIGO)
        lienzo = pygame.Surface((texto.get_width() + 2, texto.get_height() + 2), pygame.SRCALPHA)
        lienzo.blit(sombra, (2, 2))
        lienzo.blit(texto, (0, 0))
        _cache_nombres[nombre] = lienzo
    return _cache_nombres[nombre]


def dibujar_nombre(pantalla, enemigo, arriba):
    """Debug de balance: el nombre exacto de la variante, centrado sobre
    el sprite (`arriba` = y de lo alto del sprite)."""
    etiqueta = _etiqueta_nombre(enemigo.nombre)
    pantalla.blit(etiqueta, etiqueta.get_rect(midbottom=(enemigo.rect.centerx, arriba - assets.SEPARACION_NOMBRE_ENEMIGO)))


def dibujar_enemigo(pantalla, enemigo):
    variante = getattr(enemigo, "variante", None)
    imagen = None
    if variante is not None:
        imagen = sprites.sprite_variante(
            variante.nombre, enemigo.reloj, enemigo.ataque_t, enemigo.mirando_izquierda)
    con_variante = imagen is not None
    if imagen is None:
        imagen = sprites.sprite_enemigo(enemigo.tipo, tiempo=enemigo.reloj)
    if not con_variante and getattr(enemigo, "telegrafia", 0) > 0:
        imagen = imagen.copy()
        imagen.fill(assets.COLOR_TELEGRAFIA_TIRADOR, special_flags=pygame.BLEND_RGB_MAX)
    if enemigo.congelado:
        pulso = 0.5 + 0.5 * math.sin(2 * math.pi * enemigo.reloj / assets.PERIODO_PARPADEO_GRACIA)
        imagen = imagen.copy()
        imagen.set_alpha(round(assets.ALFA_MIN_ENEMIGO_GRACIA
                               + (assets.ALFA_MAX_ENEMIGO_GRACIA - assets.ALFA_MIN_ENEMIGO_GRACIA) * pulso))
    destino = imagen.get_rect(center=enemigo.rect.center)
    pantalla.blit(imagen, destino)
    if con_variante and assets.MOSTRAR_NOMBRE_ENEMIGO:
        dibujar_nombre(pantalla, enemigo, destino.top)

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
