"""Pantalla de victoria tras derrotar al jefe final (solo presentación).

Oscurece la arena y muestra un panel centrado, por debajo del HUD
superior, con el título y las dos opciones. Las teclas las atiende
Main.py (estado Escena.VICTORIA).
"""

import pygame

from src.core import assets

TITULO = "Servidor Central purificado"
OPCIONES = [
    "ENTER: volver a una mazmorra nueva",
    "ESC: salir del juego",
]


def dibujar_victoria(pantalla, fuente_titulo, fuente):
    velo = pygame.Surface(pantalla.get_size(), pygame.SRCALPHA)
    velo.fill(assets.COLOR_VELO_VICTORIA)
    pantalla.blit(velo, (0, 0))

    panel = pygame.Rect(assets.RECT_PANEL_VICTORIA)
    pygame.draw.rect(pantalla, assets.COLOR_FONDO_PANEL_VICTORIA, panel)
    pygame.draw.rect(
        pantalla, assets.COLOR_BORDE_PANEL_VICTORIA, panel, assets.GROSOR_BORDE_PANEL_VICTORIA
    )

    separacion = assets.SEPARACION_LINEAS_VICTORIA
    y = panel.top + separacion
    titulo = fuente_titulo.render(TITULO, True, assets.COLOR_MENSAJE_VICTORIA)
    pantalla.blit(titulo, titulo.get_rect(center=(panel.centerx, y)))

    y += separacion + separacion // 2
    for opcion in OPCIONES:
        texto = fuente.render(opcion, True, assets.COLOR_TEXTO_HUD)
        pantalla.blit(texto, texto.get_rect(center=(panel.centerx, y)))
        y += separacion
