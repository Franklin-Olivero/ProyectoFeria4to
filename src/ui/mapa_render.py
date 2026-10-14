"""Minimapa de la mazmorra (tecla M, solo presentación).

Dibuja el grafo de cuartos de una Mazmorra (src/dungeon/mazmorra.py)
en su posición de cuadrícula:
    - pasillos = aristas del grafo;
    - color de cada cuarto según su toxicidad local (verde 0 -> rojo 100),
      oscurecido si todavía está pendiente (no limpio: nunca visitado o
      con enemigos);
    - el cuarto actual con borde blanco;
    - el cuarto final con un candado mientras está sellado y con una
      estrella cuando se desbloquea;
    - la ruta BFS más corta del cuarto actual al final, resaltada.
No modifica la mazmorra.
"""

import math

import pygame

from src.core import assets
from src.core.balance import LADO_CUADRICULA_MAZMORRA, TOXICIDAD_MAXIMA_CUARTO


def color_toxicidad(nivel, visitado=True):
    """Interpola entre verde (0) y rojo (100); oscurece si no se visitó."""
    t = max(0.0, min(1.0, nivel / TOXICIDAD_MAXIMA_CUARTO))
    baja, alta = assets.COLOR_TOXICIDAD_BAJA, assets.COLOR_TOXICIDAD_ALTA
    color = [round(b + (a - b) * t) for b, a in zip(baja, alta)]
    if not visitado:
        color = [round(c * assets.FACTOR_OSCURO_NO_VISITADO) for c in color]
    return tuple(color)


def _centro_celda(celda):
    origen_x, origen_y = assets.ORIGEN_MINIMAPA
    medio = assets.TAMANIO_CELDA_MINIMAPA // 2
    return (
        origen_x + celda[0] * assets.PASO_CELDA_MINIMAPA + medio,
        origen_y + celda[1] * assets.PASO_CELDA_MINIMAPA + medio,
    )


def dibujar_minimapa(pantalla, mazmorra):
    from src.ui import dibujo

    tamanio = assets.TAMANIO_CELDA_MINIMAPA
    lado_total = (LADO_CUADRICULA_MAZMORRA - 1) * assets.PASO_CELDA_MINIMAPA + tamanio
    fondo = pygame.Rect(assets.ORIGEN_MINIMAPA, (lado_total, lado_total))
    fondo.inflate_ip(assets.MARGEN_FONDO_MINIMAPA * 2, assets.MARGEN_FONDO_MINIMAPA * 2)
    fondo.height += 18  # espacio para el título
    fondo.top -= 18
    dibujo.panel(pantalla, fondo, assets.COLOR_FONDO_MINIMAPA, assets.COLOR_BORDE_PANEL, 1)
    dibujo.texto(pantalla, "Mapa (M)", (fondo.left + 8, fondo.top + 4), assets.COLOR_TEXTO_SECUNDARIO,
                 assets.TAMANIO_FUENTE_PEQUENA)

    grafo = mazmorra.grafo
    centros = {cuarto: _centro_celda(celda) for cuarto, celda in mazmorra.celdas.items()}
    for a in grafo.nodos():
        for b in grafo.vecinos(a):
            if a < b:
                pygame.draw.line(
                    pantalla, assets.COLOR_PASILLO_MINIMAPA, centros[a], centros[b],
                    assets.GROSOR_PASILLO_MINIMAPA,
                )

    ruta = mazmorra.ruta_al_final() or []
    for a, b in zip(ruta, ruta[1:]):
        pygame.draw.line(
            pantalla, assets.COLOR_RUTA_MINIMAPA, centros[a], centros[b], assets.GROSOR_RUTA_MINIMAPA
        )

    for cuarto, centro in centros.items():
        rect = pygame.Rect(0, 0, tamanio, tamanio)
        rect.center = centro
        limpio = cuarto in mazmorra.limpiados
        pygame.draw.rect(pantalla, color_toxicidad(mazmorra.toxicidad[cuarto], limpio), rect)
        if cuarto in ruta and cuarto != mazmorra.actual:
            pygame.draw.rect(pantalla, assets.COLOR_RUTA_MINIMAPA, rect, assets.GROSOR_BORDE_RUTA_MINIMAPA)
        if cuarto == mazmorra.actual:
            pygame.draw.rect(pantalla, assets.COLOR_CUARTO_ACTUAL, rect, assets.GROSOR_CUARTO_ACTUAL)
        if cuarto == mazmorra.cuarto_final:
            if mazmorra.final_desbloqueado():
                _dibujar_estrella(pantalla, centro)
            else:
                _dibujar_candado(pantalla, centro)


def _dibujar_candado(pantalla, centro):
    """Cuerpo rectangular + arco (rectángulo sin base) encima."""
    ancho = assets.TAMANIO_CANDADO
    cuerpo = pygame.Rect(0, 0, ancho, ancho * 3 // 4)
    cuerpo.midtop = (centro[0], centro[1] - 1)
    arco = pygame.Rect(0, 0, ancho * 2 // 3, ancho * 2 // 3)
    arco.midbottom = (centro[0], cuerpo.top + assets.GROSOR_CANDADO)
    pygame.draw.rect(pantalla, assets.COLOR_CANDADO, arco, assets.GROSOR_CANDADO)
    pygame.draw.rect(pantalla, assets.COLOR_CANDADO, cuerpo)
    pygame.draw.rect(pantalla, assets.COLOR_MARCA_FINAL, cuerpo, 1)


def _dibujar_estrella(pantalla, centro):
    """Estrella de 5 puntas: el cuarto final ya se puede abrir."""
    radio = assets.TAMANIO_CANDADO * 0.75
    puntos = []
    for i in range(10):
        r = radio if i % 2 == 0 else radio * 0.45
        angulo = math.radians(-90 + i * 36)
        puntos.append((centro[0] + r * math.cos(angulo), centro[1] + r * math.sin(angulo)))
    pygame.draw.polygon(pantalla, assets.COLOR_FINAL_DESBLOQUEADO, puntos)
    pygame.draw.polygon(pantalla, assets.COLOR_MARCA_FINAL, puntos, 1)
