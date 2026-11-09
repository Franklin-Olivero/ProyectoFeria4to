"""Panel de misión y avisos de objetivo (solo presentación).

    - dibujar_panel_mision: "MISIÓN ACTUAL: INVESTIGA EL COLEGIO" con sus
      objetivos (✓ hechos en teal, pendiente en blanco, futuros apagados)
      y el progreso real ("2/3"). En la ciudad va bajo el cintillo; en
      combate, abajo a la izquierda (lejos del minimapa y del HUD).
    - dibujar_toast_objetivo: aviso breve "Objetivo completado" que baja
      desde arriba y se desvanece (DURACION_TOAST_MISION).
Lee una Mision (src/story/misiones.py); no la modifica.
"""

import pygame

from src.core import assets
from src.ui import dibujo, kit, layout
from src.ui.fuentes import fuente

ROTULO = "MISIÓN ACTUAL"
TEXTO_TOAST = "Objetivo completado"
TEXTO_TOAST_MISION = "Misión completada"


def dibujar_panel_mision(pantalla, mision, rect, transcurrido=1.0, compacto=False):
    """`compacto` (combate) muestra solo el objetivo pendiente y el
    siguiente; en la ciudad se ve la lista completa."""
    rect = layout.entrada(rect, transcurrido, desde="izquierda")
    objetivos = list(mision.objetivos)
    if compacto:
        pendiente = mision.objetivo_pendiente
        if pendiente is not None:
            i = objetivos.index(pendiente)
            objetivos = objetivos[max(0, i - 1): i + 2]
    alto_fila = 20
    alto = 54 + alto_fila * len(objetivos) + (0 if compacto else 48)
    rect = pygame.Rect(rect.left, rect.top, rect.width, alto)
    kit.panel(pantalla, rect, assets.COLOR_BORDE_MISION, alfa=222, radio=8)
    x, y = rect.left + 14, rect.top + 8
    dibujo.texto(pantalla, ROTULO, (x, y), assets.COLOR_TEXTO_SECUNDARIO, assets.TAMANIO_FUENTE_MINI, negrita=True)
    layout.texto_en_ancho(pantalla, mision.titulo, (x, y + 12), rect.width - 28, assets.COLOR_TITULO_MISION,
                          assets.TAMANIO_FUENTE_MEDIA, negrita=True)
    y += 40
    for objetivo in objetivos:
        if objetivo.hecho:
            color, marca = assets.COLOR_OBJETIVO_HECHO, "✓"
        elif objetivo.activo:
            color, marca = assets.COLOR_OBJETIVO_PENDIENTE, "▸"
        else:
            color, marca = assets.COLOR_OBJETIVO_FUTURO, "·"
        dibujo.texto(pantalla, marca, (x, y), color, assets.TAMANIO_FUENTE_PEQUENA, negrita=True)
        ancho_progreso = fuente(assets.TAMANIO_FUENTE_PEQUENA, True).size(objetivo.progreso)[0] + 8 if objetivo.progreso else 0
        layout.texto_en_ancho(pantalla, objetivo.texto, (x + 16, y), rect.width - 30 - 16 - ancho_progreso, color,
                              assets.TAMANIO_FUENTE_PEQUENA, minimo=11)
        if objetivo.progreso:
            dibujo.texto(pantalla, objetivo.progreso, (rect.right - 12, y), color, assets.TAMANIO_FUENTE_PEQUENA,
                         negrita=True, ancla="topright")
        y += alto_fila
    if not compacto and mision.pista:
        y += 4
        layout.parrafo_en_caja(pantalla, mision.pista, (x, y, rect.width - 26, 40), assets.COLOR_TEXTO_SECUNDARIO,
                               assets.TAMANIO_FUENTE_PEQUENA, interlineado=2)
    return rect


def dibujar_toast_objetivo(pantalla, texto, restante, duracion=assets.DURACION_TOAST_MISION, titulo=TEXTO_TOAST):
    """Aviso centrado arriba: entra deslizándose, se queda y se desvanece
    en el último medio segundo. `restante` son los segundos que le quedan."""
    transcurrido = duracion - restante
    alfa = 255
    if restante < 0.5:
        alfa = round(255 * restante / 0.5)
    rect = layout.entrada(assets.RECT_TOAST_MISION, transcurrido, desde="arriba", distancia=30)
    capa = pygame.Surface(rect.size, pygame.SRCALPHA)
    pygame.draw.rect(capa, assets.COLOR_FONDO_TOAST, capa.get_rect(), border_radius=10)
    pygame.draw.rect(capa, (*assets.COLOR_BORDE_TOAST, 255), capa.get_rect(), 2, border_radius=10)
    # Chulo que "se dibuja" en los primeros 0.3 s.
    progreso = min(1.0, transcurrido / 0.3)
    cx, cy = 28, rect.height // 2
    puntos = [(cx - 9, cy), (cx - 2, cy + 7), (cx + 10, cy - 8)]
    if progreso < 0.5:
        fin = pygame.Vector2(puntos[0]).lerp(puntos[1], progreso * 2)
        pygame.draw.line(capa, assets.COLOR_TEAL, puntos[0], fin, 3)
    else:
        pygame.draw.line(capa, assets.COLOR_TEAL, puntos[0], puntos[1], 3)
        fin = pygame.Vector2(puntos[1]).lerp(puntos[2], (progreso - 0.5) * 2)
        pygame.draw.line(capa, assets.COLOR_TEAL, puntos[1], fin, 3)
    dibujo.texto(capa, titulo, (52, 9), assets.COLOR_TEAL, assets.TAMANIO_FUENTE_PEQUENA, negrita=True)
    layout.texto_en_ancho(capa, texto, (52, 28), rect.width - 64, assets.COLOR_TEXTO_HUD, assets.TAMANIO_FUENTE_NORMAL)
    capa.set_alpha(alfa)
    pantalla.blit(capa, rect.topleft)
    return rect
