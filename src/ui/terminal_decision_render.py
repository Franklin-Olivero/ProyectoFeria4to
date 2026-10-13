"""Dibujo de la terminal de decisión con Pygame (solo presentación).

Lee el estado de una TerminalDecision (src/ui/terminal_decision.py) y
lo pinta como un panel centrado: nodo actual arriba, sus hijos en una
fila (el seleccionado resaltado) y el tiempo restante abajo. No
modifica la terminal.
"""

import pygame

from src.core import assets


def dibujar_terminal(pantalla, terminal, fuente):
    panel = pygame.Rect(0, 0, assets.ANCHO_TERMINAL, assets.ALTO_TERMINAL)
    panel.center = pantalla.get_rect().center
    pygame.draw.rect(pantalla, assets.COLOR_FONDO_TERMINAL, panel)
    pygame.draw.rect(
        pantalla, assets.COLOR_BORDE_TERMINAL, panel, assets.GROSOR_BORDE_TERMINAL
    )

    x = panel.left + assets.MARGEN_TERMINAL
    y = panel.top + assets.MARGEN_TERMINAL

    titulo = fuente.render(str(terminal.nodo_actual.etiqueta), True, assets.COLOR_TEXTO_TERMINAL)
    pantalla.blit(titulo, (x, y))
    y += assets.SEPARACION_LINEAS_TERMINAL

    # Opciones en fila, distribuidas a lo ancho del panel.
    hijos = terminal.nodo_actual.hijos
    ancho_util = panel.width - 2 * assets.MARGEN_TERMINAL
    for i, hijo in enumerate(hijos):
        seleccionado = i == terminal.indice_seleccionado
        texto = f"[{hijo.etiqueta}]" if seleccionado else hijo.etiqueta
        color = assets.COLOR_OPCION_SELECCIONADA if seleccionado else assets.COLOR_TEXTO_TERMINAL
        superficie = fuente.render(texto, True, color)
        pantalla.blit(superficie, (x + i * ancho_util // len(hijos), y))
    y += assets.SEPARACION_LINEAS_TERMINAL

    tiempo = fuente.render(
        f"Tiempo: {terminal.tiempo_restante:.1f}s", True, assets.COLOR_TIEMPO_TERMINAL
    )
    pantalla.blit(tiempo, (x, y))
