"""Pantalla de derrota global: Colapso Electoral al 100% (solo presentación).

Tiñe la escena de rojo oscuro y muestra "Colapso total" con las dos
opciones. Las teclas las atiende Main.py (estado Escena.DERROTA).
"""

from src.core import assets
from src.ui import sprites
from src.ui.pantalla_victoria import dibujar_panel_final

TITULO = "Colapso total"
DETALLE = "La barra de colapso electoral llegó al 100%. La ciudad cayó."
OPCIONES = [
    ("Enter", "reiniciar la partida"),
    ("Esc", "salir del juego"),
]


def dibujar_derrota(pantalla):
    dibujar_panel_final(
        pantalla, TITULO, DETALLE, OPCIONES,
        color_velo=assets.COLOR_VELO_COLAPSO,
        rect_panel=assets.RECT_PANEL_COLAPSO,
        color_fondo=assets.COLOR_FONDO_PANEL_COLAPSO,
        color_borde=assets.COLOR_BORDE_PANEL_COLAPSO,
        grosor_borde=assets.GROSOR_BORDE_PANEL_COLAPSO,
        color_titulo=assets.COLOR_MENSAJE_DERROTA,
        icono=sprites.sprite(sprites.EXPLOSION, sprites.PALETA_EXPLOSION, escala=3),
    )
