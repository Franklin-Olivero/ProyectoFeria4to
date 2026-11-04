"""Pantalla de elecciones y epílogo (solo presentación).

Tras la cinemática de la caída del Servidor Central: las barras de
apoyo de los cuatro candidatos ficticios se llenan en
DURACION_CONTEO_ELECCIONES s (conteo en vivo), el panel de estado de
Ciudad Nova (reutiliza indicadores_render) y, cuando el jugador pulsa
Enter, el final se revela con su cinemática (src/story/cinematica.py);
hasta entonces el panel inferior dice "Enter: conocer el resultado".
Lee resumen_final(campania) (src/story/eleccion.py); no modifica nada.
"""

import math

import pygame

from src.core import assets
from src.story.eleccion import FINAL_ARQUITECTO, FINAL_RENACE
from src.ui import dibujo, indicadores_render, layout, sprites

TITULO = "Elecciones de Ciudad Nova"
TEXTO_REVELAR = "Enter: conocer el desenlace"
TEXTO_CONTANDO = "Escrutinio en curso…"
TEXTO_GANADOR = "Alcalde electo"
COLORES_FINAL = {
    FINAL_RENACE: assets.COLOR_FINAL_RENACE,
    FINAL_ARQUITECTO: assets.COLOR_FINAL_ARQUITECTO,
}


def fraccion_conteo(tiempo, duracion=assets.DURACION_CONTEO_ELECCIONES):
    """0-1 del escrutinio con desaceleración (puro)."""
    if duracion <= 0:
        return 1.0
    t = max(0.0, min(1.0, tiempo / duracion))
    return 1 - (1 - t) ** 2


def dibujar_elecciones(pantalla, resumen, tiempo=10.0, mostrar_final=True):
    pantalla.fill(assets.COLOR_FONDO)
    fondo = sprites.fondo_historia(assets.FONDO_ELECCIONES, pantalla.get_size())
    if fondo is not None:
        fondo = fondo.copy()
        fondo.set_alpha(assets.ALFA_FONDO_ELECCIONES)
        pantalla.blit(fondo, (0, 0))
    margen = assets.MARGEN_PANTALLA
    dibujo.texto(pantalla, TITULO, (60, 36), assets.COLOR_TEXTO_HUD, assets.TAMANIO_FUENTE_GRANDE, negrita=True)
    layout.texto_en_ancho(pantalla, resumen["nota"], (60, 84), pantalla.get_width() - 60 - margen,
                          assets.COLOR_TEXTO_APAGADO, assets.TAMANIO_FUENTE_PEQUENA, minimo=11)

    conteo = fraccion_conteo(tiempo)
    panel = dibujo.panel(pantalla, assets.RECT_PANEL_CANDIDATOS, assets.COLOR_FONDO_PANEL, assets.COLOR_BORDE_PANEL, 1, radio=8)
    x, y = panel.left + 24, panel.top + 16
    dibujo.texto(pantalla, "Apoyo simulado (según los indicadores y tu reputación)", (x, y),
                 assets.COLOR_TEXTO_SECUNDARIO, assets.TAMANIO_FUENTE_NORMAL, negrita=True)
    y += 34
    ancho = panel.width - 48
    maximo = max(p for _, p in resumen["apoyos"]) or 1
    for indice, (candidato, porcentaje) in enumerate(resumen["apoyos"]):
        color = assets.COLORES_CANDIDATOS[indice % len(assets.COLORES_CANDIDATOS)]
        ganador = indice == 0 and conteo >= 1
        nombre = f"{candidato['nombre']}  ·  {candidato['lema']}"
        etiqueta = layout.texto_en_ancho(pantalla, nombre, (x, y), ancho - 110, assets.COLOR_TEXTO_HUD,
                                         assets.TAMANIO_FUENTE_NORMAL, negrita=indice == 0)
        if ganador:
            dibujo.chip(pantalla, TEXTO_GANADOR, (etiqueta.right + 10, y - 3), assets.COLOR_FONDO, color, color, alto=22)
        dibujo.texto(pantalla, f"{porcentaje * conteo:.1f} %", (x + ancho, y), color, assets.TAMANIO_FUENTE_MEDIA,
                     negrita=True, ancla="topright")
        dibujo.barra(pantalla, (x, y + 26, ancho, assets.ALTO_BARRA_CANDIDATO), porcentaje * conteo / maximo, color,
                     assets.COLOR_FONDO_INDICADOR, None)
        y += assets.SEPARACION_CANDIDATOS

    epilogo = pygame.Rect(assets.RECT_PANEL_EPILOGO)
    if mostrar_final:
        color_final = COLORES_FINAL.get(resumen["clave"], assets.COLOR_FINAL_DIVIDIDA)
        dibujo.panel(pantalla, epilogo, assets.COLOR_FONDO_PANEL, color_final, 2, radio=8)
        dibujo.texto(pantalla, resumen["titulo"], (epilogo.left + 20, epilogo.top + 12), color_final,
                     assets.TAMANIO_FUENTE_TITULO, negrita=True)
        layout.parrafo_en_caja(pantalla, resumen["texto"], (epilogo.left + 20, epilogo.top + 44, epilogo.width - 40,
                                                            epilogo.height - 54),
                               assets.COLOR_TEXTO_HUD, assets.TAMANIO_FUENTE_PEQUENA, interlineado=3)
    else:
        dibujo.panel(pantalla, epilogo, assets.COLOR_FONDO_PANEL, assets.COLOR_BORDE_PANEL, 1, radio=8)
        pulso = 0.6 + 0.4 * math.sin(tiempo * 4)
        dibujo.texto(pantalla, "¿Qué ciudad queda después de la elección?", (epilogo.centerx, epilogo.centery - 22),
                     assets.COLOR_TEXTO_HUD, assets.TAMANIO_FUENTE_MEDIA, negrita=True, ancla="center")
        dibujo.texto(pantalla, "Depende de tus decisiones, tus pruebas y a quién señalaste.",
                     (epilogo.centerx, epilogo.centery + 6), assets.COLOR_TEXTO_SECUNDARIO,
                     assets.TAMANIO_FUENTE_NORMAL, ancla="center")
        color = tuple(round(c * pulso + 40 * (1 - pulso)) for c in assets.COLOR_AMARILLO)
        dibujo.chip(pantalla, TEXTO_REVELAR if conteo >= 1 else TEXTO_CONTANDO, (epilogo.centerx, epilogo.centery + 42),
                    color, assets.COLOR_FONDO_PANEL, color, assets.TAMANIO_FUENTE_NORMAL, ancla="center", alto=30,
                    margen=14)

    indicadores_render.dibujar_panel_estado(pantalla, resumen["campania"], assets.RECT_PANEL_ESTADO_FINAL,
                                            mostrar_cerrar=False)
    if mostrar_final:
        chip = dibujo.chip(pantalla, "Enter", (520, 690), ancla="midright")
        dibujo.texto(pantalla, "volver a Ciudad Nova", (chip.right + 8, chip.centery), assets.COLOR_TEXTO_SECUNDARIO,
                     ancla="midleft")
        chip = dibujo.chip(pantalla, "Esc", (760, 690), ancla="midright")
        dibujo.texto(pantalla, "salir", (chip.right + 8, chip.centery), assets.COLOR_TEXTO_SECUNDARIO, ancla="midleft")
    else:
        chip = dibujo.chip(pantalla, "Enter", (600, 690), ancla="midright")
        dibujo.texto(pantalla, "conocer el desenlace", (chip.right + 8, chip.centery), assets.COLOR_TEXTO_SECUNDARIO,
                     ancla="midleft")
