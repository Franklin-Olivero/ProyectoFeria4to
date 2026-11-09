"""Indicador del sabotaje en la terminal de decisión (modo Online).

Solo lo ve el impostor, arriba al centro, entre el título y el reloj de la
terminal: cuánto le falta a su bloqueo, con una barra que se llena, y
"listo" cuando ya puede elegir normal. Si aprieta una tecla durante el
bloqueo, el indicador marca "aún no". Los demás no ven nada: tienen que
descubrir quién mueve el cursor. La regla está en Online/sabotaje.py y las
constantes en assets.py.
"""

import math

import pygame

from src.core import assets
from src.core.balance import COOLDOWN_SABOTAJE_MAX
from src.ui import dibujo, kit

CONTROLES_IMPOSTOR = [("← →", "sabotear: mover"), ("Enter", "sabotear: confirmar")]


def texto_sabotaje(restante, aviso=0.0):
    """Qué dice el indicador cuando al bloqueo le faltan `restante` segundos."""
    if restante <= 0:
        return assets.TEXTO_SABOTAJE_LISTO
    plantilla = assets.TEXTO_SABOTAJE_AUN_NO if aviso > 0 else assets.TEXTO_SABOTAJE_BLOQUEO
    return plantilla.format(segundos=math.ceil(restante))


def dibujar_sabotaje(pantalla, restante, aviso=0.0, espera=None):
    """Indicador del impostor. `espera` = el bloqueo que sorteó el host para
    esta terminal (la barra se llena sobre ese total; sin dato, el máximo);
    `aviso` > 0 justo después de una tecla durante el bloqueo."""
    total = COOLDOWN_SABOTAJE_MAX if espera is None else espera
    rect = pygame.Rect(assets.RECT_INDICADOR_SABOTAJE)
    kit.panel(pantalla, rect, assets.COLOR_IMPOSTOR)
    if aviso > 0 or restante <= 0:
        pygame.draw.rect(pantalla, assets.COLOR_IMPOSTOR, rect, 2, border_radius=10)
    kit.rotulo(pantalla, assets.TEXTO_SABOTAJE_TITULO, (rect.left + 16, rect.top + 8), assets.COLOR_IMPOSTOR)
    dibujo.texto(pantalla, texto_sabotaje(restante, aviso), (rect.left + 16, rect.top + 26),
                 assets.COLOR_TEXTO_HUD, assets.TAMANIO_FUENTE_NORMAL, negrita=True)
    barra = pygame.Rect(rect.left + 16, rect.bottom - 12, rect.width - 32, 5)
    dibujo.barra(pantalla, barra, 1 - restante / total if total > 0 else 1.0, assets.COLOR_IMPOSTOR,
                 assets.COLOR_FONDO_BARRA_SABOTAJE, None)
