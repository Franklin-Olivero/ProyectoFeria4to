"""Dibujo y ratón del menú de pausa (solo presentación).

Encima del último frame de la partida: un velo, el panel neón con
PAUSA, si el mundo está congelado o sigue (multijugador), las opciones
de src/ui/pausa.py y, si se pidió, la confirmación Sí / No. Con Ajustes
abierto se dibuja el modal de siempre (src/ui/ajustes_render.py) con la
pestaña PARTIDA.
"""

import pygame

from src.core import assets
from src.ui import dibujo, kit
from src.ui.ajustes_render import VistaAjustes
from src.ui.navegacion import SONIDO_NAVEGAR
from src.ui.pausa import ETIQUETAS, NO, PREGUNTAS, SI

TITULO = "PAUSA"
SUBTITULO_CONGELADA = "La partida está detenida"
SUBTITULO_SIGUE = "Multijugador: el juego sigue mientras eliges"
AYUDA = "↑ ↓ elegir  ·  Enter confirmar  ·  Esc / P continuar  ·  N silencio"


def rects_opciones(pausa):
    """{opción: Rect} de cada fila del menú."""
    panel = pygame.Rect(assets.RECT_PANEL_PAUSA)
    y = panel.top + 112
    rects = {}
    for opcion in pausa.opciones:
        rects[opcion] = pygame.Rect(panel.left + 24, y, panel.width - 48, assets.ALTO_OPCION_PAUSA - 8)
        y += assets.ALTO_OPCION_PAUSA
    return rects


def rects_confirmacion():
    caja = pygame.Rect(assets.RECT_CONFIRMACION_PAUSA)
    ancho = assets.ANCHO_BOTON_CONFIRMACION
    y = caja.bottom - 62
    return {
        SI: pygame.Rect(caja.centerx - ancho - 12, y, ancho, 42),
        NO: pygame.Rect(caja.centerx + 12, y, ancho, 42),
    }


class VistaPausa:
    def __init__(self):
        self.ajustes = VistaAjustes()

    def dibujar(self, pantalla, pausa, audio, reducir_movimiento=False):
        kit.velo(pantalla, assets.ALFA_VELO_PAUSA)
        if pausa.ajustes is not None:
            self.ajustes.dibujar(pantalla, pausa.ajustes, audio, 0, reducir_movimiento)
            return
        panel = kit.panel(pantalla, assets.RECT_PANEL_PAUSA, assets.COLOR_NEON_LOBBY, alfa=240, filo="todo")
        dibujo.corchetes(pantalla, panel, assets.COLOR_NEON_LOBBY_2, 16, 2, margen=-6)
        for dx, dy in ((-2, 0), (2, 0), (0, -2), (0, 2)):
            dibujo.texto(pantalla, TITULO, (panel.centerx + dx, panel.top + 44 + dy), assets.COLOR_MORADO_OSCURO,
                         assets.TAMANIO_FUENTE_GRANDE, negrita=True, ancla="center")
        dibujo.texto(pantalla, TITULO, (panel.centerx, panel.top + 44), assets.COLOR_TEXTO_HUD,
                     assets.TAMANIO_FUENTE_GRANDE, negrita=True, ancla="center")
        subtitulo = SUBTITULO_CONGELADA if pausa.congelada else SUBTITULO_SIGUE
        dibujo.texto(pantalla, subtitulo, (panel.centerx, panel.top + 80), assets.COLOR_NEON_LOBBY_2,
                     assets.TAMANIO_FUENTE_PEQUENA, ancla="center")

        for opcion, rect in rects_opciones(pausa).items():
            enfocada = opcion == pausa.opcion_enfocada and pausa.confirmando is None
            if enfocada:
                dibujo.panel(pantalla, rect, assets.COLOR_FILA_ENFOCADA, assets.COLOR_NEON_LOBBY, 2, radio=8)
            texto = f"[ {ETIQUETAS[opcion]} ]" if enfocada else ETIQUETAS[opcion]
            dibujo.texto(pantalla, texto, rect.center, assets.COLOR_TEXTO_HUD if enfocada else assets.COLOR_TEXTO_SECUNDARIO,
                         assets.TAMANIO_FUENTE_NORMAL, negrita=True, ancla="center")

        estado = "Silencio (N)" if audio is not None and audio.silenciado else "N: silencio"
        dibujo.texto(pantalla, estado, (panel.centerx, panel.bottom - 20), assets.COLOR_TEXTO_APAGADO,
                     assets.TAMANIO_FUENTE_PEQUENA, ancla="center")
        dibujo.texto(pantalla, AYUDA, (pantalla.get_width() // 2, panel.bottom + 26), assets.COLOR_TEXTO_SECUNDARIO,
                     assets.TAMANIO_FUENTE_PEQUENA, ancla="center")
        if pausa.confirmando is not None:
            self._dibujar_confirmacion(pantalla, pausa)

    def _dibujar_confirmacion(self, pantalla, pausa):
        kit.velo(pantalla, 120)
        caja = kit.panel(pantalla, assets.RECT_CONFIRMACION_PAUSA, assets.COLOR_MAGENTA, alfa=245, filo="todo")
        dibujo.parrafo(pantalla, PREGUNTAS[pausa.confirmando], (caja.centerx, caja.top + 28), caja.width - 60,
                       assets.COLOR_TEXTO_HUD, assets.TAMANIO_FUENTE_NORMAL, negrita=True, centrado=True)
        for opcion, rect in rects_confirmacion().items():
            enfocada = opcion == pausa.foco_confirmacion
            color = assets.COLOR_MAGENTA if opcion == SI else assets.COLOR_TEAL
            dibujo.panel(pantalla, rect, assets.COLOR_FILA_ENFOCADA if enfocada else assets.COLOR_FONDO_MODAL,
                         color, 2 if enfocada else 1, radio=8)
            texto = "SÍ" if opcion == SI else "NO"
            dibujo.texto(pantalla, f"[ {texto} ]" if enfocada else texto, rect.center,
                         color if enfocada else assets.COLOR_TEXTO_SECUNDARIO, assets.TAMANIO_FUENTE_NORMAL,
                         negrita=True, ancla="center")

    # --- Ratón -------------------------------------------------------------

    def manejar_mouse(self, evento, pausa):
        """Hover enfoca y clic elige. Retorna el sonido o None."""
        if pausa.ajustes is not None:
            return self.ajustes.manejar_mouse(evento, pausa.ajustes)
        if evento.type not in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN):
            return None
        rects = rects_confirmacion() if pausa.confirmando is not None else rects_opciones(pausa)
        for opcion, rect in rects.items():
            if rect.collidepoint(evento.pos):
                if evento.type == pygame.MOUSEMOTION:
                    return SONIDO_NAVEGAR if pausa.enfocar(opcion) else None
                if evento.button == 1:
                    pausa.enfocar(opcion)
                    return pausa.elegir(opcion)
        return None
