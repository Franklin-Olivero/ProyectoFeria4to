"""Pantalla de victoria tras derrotar al jefe final (solo presentación).

Oscurece la arena y muestra un panel centrado con el título y las dos
opciones. Las teclas las atiende Main.py (estado Escena.VICTORIA).
`dibujar_panel_final` también lo usa la pantalla de derrota global
(src/ui/pantalla_derrota.py).
"""

import pygame

from src.core import assets
from src.ui import dibujo, sprites

TITULO = "Servidor Central purificado"
DETALLE = "La Alcaldía vuelve a estar en línea. El colapso baja 0.1%."
OPCIONES = [
    ("Enter", "volver al mapa de la ciudad"),
    ("Esc", "salir del juego"),
]


def dibujar_victoria(pantalla):
    dibujar_panel_final(
        pantalla, TITULO, DETALLE, OPCIONES,
        color_velo=assets.COLOR_VELO_VICTORIA,
        rect_panel=assets.RECT_PANEL_VICTORIA,
        color_fondo=assets.COLOR_FONDO_PANEL_VICTORIA,
        color_borde=assets.COLOR_BORDE_PANEL_VICTORIA,
        grosor_borde=assets.GROSOR_BORDE_PANEL_VICTORIA,
        color_titulo=assets.COLOR_MENSAJE_VICTORIA,
        icono=sprites.sprite(sprites.CHULO, sprites.PALETA_CHULO, escala=4),
    )


def dibujar_panel_final(
    pantalla, titulo, detalle, opciones,
    color_velo, rect_panel, color_fondo, color_borde, grosor_borde, color_titulo, icono=None,
):
    """Velo semitransparente + panel con icono, título, detalle y una
    línea (chip de tecla + descripción) por opción."""
    velo = pygame.Surface(pantalla.get_size(), pygame.SRCALPHA)
    velo.fill(color_velo)
    pantalla.blit(velo, (0, 0))

    panel = dibujo.panel(pantalla, rect_panel, color_fondo, color_borde, grosor_borde, radio=10)
    y = panel.top + 34
    if icono is not None:
        pantalla.blit(icono, icono.get_rect(center=(panel.centerx, y + 10)))
        y += 56
    dibujo.texto(pantalla, titulo, (panel.centerx, y), color_titulo, assets.TAMANIO_FUENTE_GRANDE,
                 negrita=True, ancla="center")
    y += 40
    dibujo.texto(pantalla, detalle, (panel.centerx, y), assets.COLOR_TEXTO_SECUNDARIO,
                 assets.TAMANIO_FUENTE_NORMAL, ancla="center")
    y += assets.SEPARACION_LINEAS_VICTORIA + 6
    for tecla, descripcion in opciones:
        chip = dibujo.chip(pantalla, tecla, (panel.centerx - 60, y), ancla="midright")
        dibujo.texto(pantalla, descripcion, (chip.right + 10, y), assets.COLOR_TEXTO_HUD,
                     assets.TAMANIO_FUENTE_NORMAL, ancla="midleft")
        y += 36
