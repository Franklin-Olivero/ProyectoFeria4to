"""Primitivas de dibujo compartidas por todas las pantallas (solo presentación).

Paneles con esquinas redondeadas, chips de tecla, barras de progreso,
líneas punteadas y texto. Todos los colores por defecto salen de
src/core/assets.py; ninguna pantalla debería dibujar un rectángulo
"a mano" si una de estas funciones lo cubre.
"""

import pygame

from src.core import assets
from src.ui.fuentes import fuente


def panel(pantalla, rect, relleno=assets.COLOR_FONDO_PANEL, borde=assets.COLOR_BORDE_PANEL,
          grosor=1, radio=assets.RADIO_PANEL):
    """Rectángulo redondeado con relleno y borde opcionales."""
    rect = pygame.Rect(rect)
    if relleno is not None:
        pygame.draw.rect(pantalla, relleno, rect, border_radius=radio)
    if borde is not None and grosor > 0:
        pygame.draw.rect(pantalla, borde, rect, grosor, border_radius=radio)
    return rect


def panel_alfa(pantalla, rect, color_rgba, radio=assets.RADIO_PANEL):
    """Rectángulo redondeado semitransparente (color con alfa)."""
    rect = pygame.Rect(rect)
    capa = pygame.Surface(rect.size, pygame.SRCALPHA)
    pygame.draw.rect(capa, color_rgba, capa.get_rect(), border_radius=radio)
    pantalla.blit(capa, rect.topleft)


def texto(pantalla, cadena, posicion, color=assets.COLOR_TEXTO_HUD,
          tamanio=assets.TAMANIO_FUENTE_NORMAL, negrita=False, ancla="topleft"):
    """Dibuja `cadena` anclada en `posicion` (ancla = nombre de atributo
    de Rect: topleft, center, midright...). Retorna el rect ocupado."""
    superficie = fuente(tamanio, negrita).render(str(cadena), True, color)
    rect = superficie.get_rect(**{ancla: posicion})
    pantalla.blit(superficie, rect)
    return rect


def chip(pantalla, cadena, posicion, color_texto=assets.COLOR_TEXTO_HUD,
         relleno=assets.COLOR_FONDO_CHIP, borde=assets.COLOR_BORDE_CHIP,
         tamanio=assets.TAMANIO_FUENTE_PEQUENA, negrita=True, ancla="topleft",
         alto=assets.ALTO_CHIP, margen=assets.MARGEN_CHIP):
    """Etiqueta pequeña con fondo (tecla, estado, delta). Retorna su rect."""
    superficie = fuente(tamanio, negrita).render(str(cadena), True, color_texto)
    rect = pygame.Rect(0, 0, superficie.get_width() + margen * 2, alto)
    setattr(rect, ancla, posicion)
    panel(pantalla, rect, relleno, borde, 1, radio=5)
    pantalla.blit(superficie, superficie.get_rect(center=rect.center))
    return rect


def barra(pantalla, rect, fraccion, color=assets.COLOR_BARRA_COLAPSO,
          fondo=assets.COLOR_FONDO_BARRA, borde=assets.COLOR_BORDE_BARRA, radio=3):
    """Barra de progreso horizontal llena hasta `fraccion` (0-1)."""
    rect = pygame.Rect(rect)
    pygame.draw.rect(pantalla, fondo, rect, border_radius=radio)
    fraccion = max(0.0, min(1.0, fraccion))
    if fraccion > 0:
        relleno = rect.copy()
        relleno.width = max(radio * 2, round(rect.width * fraccion))
        pygame.draw.rect(pantalla, color, relleno, border_radius=radio)
    if borde is not None:
        pygame.draw.rect(pantalla, borde, rect, 1, border_radius=radio)
    return rect


def linea_punteada(pantalla, color, inicio, fin, largo=6, hueco=6, grosor=2):
    """Línea discontinua entre dos puntos (color puede llevar alfa)."""
    inicio, fin = pygame.Vector2(inicio), pygame.Vector2(fin)
    distancia = inicio.distance_to(fin)
    if distancia < 1:
        return
    direccion = (fin - inicio) / distancia
    capa = None
    if len(color) == 4:
        capa = pygame.Surface(pantalla.get_size(), pygame.SRCALPHA)
    destino = capa if capa is not None else pantalla
    recorrido = 0.0
    while recorrido < distancia:
        a = inicio + direccion * recorrido
        b = inicio + direccion * min(recorrido + largo, distancia)
        pygame.draw.line(destino, color, a, b, grosor)
        recorrido += largo + hueco
    if capa is not None:
        pantalla.blit(capa, (0, 0))


def poligono_alfa(pantalla, color_rgba, puntos):
    """Polígono semitransparente en coordenadas de pantalla."""
    capa = pygame.Surface(pantalla.get_size(), pygame.SRCALPHA)
    pygame.draw.polygon(capa, color_rgba, puntos)
    pantalla.blit(capa, (0, 0))


def corchetes(pantalla, rect, color, largo, grosor, margen=0):
    """Cuatro esquinas en "L" alrededor de `rect` (marco de objetivo)."""
    r = pygame.Rect(rect).inflate(margen * 2, margen * 2)
    esquinas = (
        (r.topleft, (1, 0), (0, 1)),
        (r.topright, (-1, 0), (0, 1)),
        (r.bottomleft, (1, 0), (0, -1)),
        (r.bottomright, (-1, 0), (0, -1)),
    )
    for (x, y), (dx, _), (_, dy) in esquinas:
        pygame.draw.line(pantalla, color, (x, y), (x + dx * largo, y), grosor)
        pygame.draw.line(pantalla, color, (x, y), (x, y + dy * largo), grosor)


def ajustar_texto(cadena, tamanio, ancho_max, negrita=False):
    """Parte `cadena` en líneas que quepan en `ancho_max` píxeles."""
    f = fuente(tamanio, negrita)
    lineas, actual = [], ""
    for palabra in cadena.split(" "):
        prueba = palabra if not actual else actual + " " + palabra
        if f.size(prueba)[0] <= ancho_max:
            actual = prueba
        else:
            if actual:
                lineas.append(actual)
            actual = palabra
    if actual:
        lineas.append(actual)
    return lineas


def parrafo(pantalla, cadena, posicion, ancho_max, color=assets.COLOR_TEXTO_HUD,
            tamanio=assets.TAMANIO_FUENTE_NORMAL, negrita=False, interlineado=4,
            centrado=False):
    """Texto en varias líneas desde `posicion` (topleft, o midtop si centrado).
    Retorna la coordenada y donde termina."""
    x, y = posicion
    alto = fuente(tamanio, negrita).get_height()
    for linea in ajustar_texto(cadena, tamanio, ancho_max, negrita):
        if centrado:
            texto(pantalla, linea, (x, y), color, tamanio, negrita, ancla="midtop")
        else:
            texto(pantalla, linea, (x, y), color, tamanio, negrita)
        y += alto + interlineado
    return y
