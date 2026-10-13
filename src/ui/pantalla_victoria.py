"""Pantalla de victoria tras derrotar al jefe final (solo presentación).

Oscurece la arena y muestra un panel centrado, por debajo del HUD
superior, con el título y las dos opciones. Las teclas las atiende
Main.py (estado Escena.VICTORIA). `dibujar_panel_final` también lo usa
la pantalla de derrota global (src/ui/pantalla_derrota.py).
"""

import pygame

from src.core import assets

TITULO = "Servidor Central purificado"
OPCIONES = [
    "ENTER: volver al mapa de la ciudad",
    "ESC: salir del juego",
]


def dibujar_victoria(pantalla, fuente_titulo, fuente):
    dibujar_panel_final(
        pantalla, fuente_titulo, fuente, TITULO, OPCIONES,
        color_velo=assets.COLOR_VELO_VICTORIA,
        rect_panel=assets.RECT_PANEL_VICTORIA,
        color_fondo=assets.COLOR_FONDO_PANEL_VICTORIA,
        color_borde=assets.COLOR_BORDE_PANEL_VICTORIA,
        grosor_borde=assets.GROSOR_BORDE_PANEL_VICTORIA,
        color_titulo=assets.COLOR_MENSAJE_VICTORIA,
    )


def dibujar_panel_final(
    pantalla, fuente_titulo, fuente, titulo, opciones,
    color_velo, rect_panel, color_fondo, color_borde, grosor_borde, color_titulo,
):
    """Velo semitransparente + panel con un título y una línea por opción."""
    velo = pygame.Surface(pantalla.get_size(), pygame.SRCALPHA)
    velo.fill(color_velo)
    pantalla.blit(velo, (0, 0))

    panel = pygame.Rect(rect_panel)
    pygame.draw.rect(pantalla, color_fondo, panel)
    pygame.draw.rect(pantalla, color_borde, panel, grosor_borde)

    separacion = assets.SEPARACION_LINEAS_VICTORIA
    y = panel.top + separacion
    superficie = fuente_titulo.render(titulo, True, color_titulo)
    pantalla.blit(superficie, superficie.get_rect(center=(panel.centerx, y)))

    y += separacion + separacion // 2
    for opcion in opciones:
        texto = fuente.render(opcion, True, assets.COLOR_TEXTO_HUD)
        pantalla.blit(texto, texto.get_rect(center=(panel.centerx, y)))
        y += separacion
