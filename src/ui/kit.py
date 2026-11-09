"""Piezas de interfaz de la identidad visual de Civitas (solo presentación).

Un solo lenguaje para todas las pantallas (docs/ART_DIRECTION.md): paneles de
vidrio oscuro con filo de color, rótulos pequeños en mayúsculas, un único
acento por significado y barras de datos. Cada color sale de los tokens
semánticos de src/core/assets.py:

    violeta  Civitas e interfaz          cian     información verificada
    magenta  manipulación de NOVA_404    ámbar    advertencias
    rojo     consecuencias graves

Las superficies translúcidas se cachean por tamaño y color: dibujar un panel
cuesta un blit, no un degradado por frame.
"""

import math

import pygame

from src.core import assets
from src.ui import dibujo, layout
from src.ui.fuentes import fuente

_cache_paneles = {}
_cache_velos = {}


def panel(pantalla, rect, acento=assets.COLOR_CIVITAS, alfa=232, radio=10, filo="izquierda"):
    """Panel de vidrio oscuro con un filo de color (el significado del panel)."""
    rect = pygame.Rect(rect)
    clave = (rect.size, acento, alfa, radio, filo)
    superficie = _cache_paneles.get(clave)
    if superficie is None:
        superficie = pygame.Surface(rect.size, pygame.SRCALPHA)
        arriba, abajo = assets.COLOR_VIDRIO_ARRIBA, assets.COLOR_VIDRIO_ABAJO
        forma = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(forma, (255, 255, 255, 255), forma.get_rect(), border_radius=radio)
        for y in range(rect.height):
            t = y / max(1, rect.height - 1)
            color = tuple(round(a + (b - a) * t) for a, b in zip(arriba, abajo))
            pygame.draw.line(superficie, (*color, alfa), (0, y), (rect.width, y))
        superficie.blit(forma, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        pygame.draw.rect(superficie, (*assets.COLOR_BORDE_VIDRIO, 255), superficie.get_rect(), 1, border_radius=radio)
        if filo == "izquierda":
            pygame.draw.rect(superficie, acento, (0, radio, 3, max(0, rect.height - 2 * radio)))
        elif filo == "arriba":
            pygame.draw.rect(superficie, acento, (radio, 0, max(0, rect.width - 2 * radio), 3))
        elif filo == "todo":
            pygame.draw.rect(superficie, acento, superficie.get_rect(), 2, border_radius=radio)
        if len(_cache_paneles) > 256:
            _cache_paneles.clear()
        _cache_paneles[clave] = superficie
    pantalla.blit(superficie, rect.topleft)
    return rect


def velo(pantalla, alfa=170, color=assets.COLOR_NOCHE):
    """Oscurece la pantalla detrás de una capa. Cacheado: una superficie por alfa."""
    tamanio = pantalla.get_size()
    clave = (tamanio, alfa, color)
    capa = _cache_velos.get(clave)
    if capa is None:
        capa = pygame.Surface(tamanio)
        capa.fill(color)
        capa.set_alpha(alfa)
        if len(_cache_velos) > 64:
            _cache_velos.clear()
        _cache_velos[clave] = capa
    pantalla.blit(capa, (0, 0))


def rotulo(pantalla, cadena, posicion, color=assets.COLOR_TEXTO_SECUNDARIO, tamanio=assets.TAMANIO_FUENTE_PEQUENA,
           ancla="topleft"):
    """Rótulo pequeño en mayúsculas: la jerarquía se lee de un vistazo."""
    return dibujo.texto(pantalla, cadena.upper(), posicion, color, tamanio, negrita=True, ancla=ancla)


def cabecera(pantalla, sobre, titulo, x=48, y=30, color_sobre=assets.COLOR_CIVITAS, ancho=None):
    """Sobretítulo + título grande. Retorna la y donde termina."""
    rotulo(pantalla, sobre, (x, y), color_sobre)
    rect = layout.texto_en_ancho(pantalla, titulo, (x, y + 20), ancho or pantalla.get_width() - 2 * x,
                                 assets.COLOR_TEXTO_HUD, assets.TAMANIO_FUENTE_GRANDE, negrita=True,
                                 minimo=assets.TAMANIO_FUENTE_TITULO)
    return rect.bottom


def tecla(pantalla, cadena, descripcion, posicion, ancla="midright"):
    """Pista de tecla: chip + qué hace. Retorna el rect de todo el conjunto."""
    f = fuente(assets.TAMANIO_FUENTE_PEQUENA)
    ancho_texto = f.size(descripcion)[0]
    fchip = fuente(assets.TAMANIO_FUENTE_PEQUENA, True)
    ancho_chip = fchip.size(cadena)[0] + 2 * assets.MARGEN_CHIP
    total = ancho_chip + 8 + ancho_texto
    x, y = posicion
    if ancla == "midright":
        x -= total
    elif ancla == "center":
        x -= total // 2
    chip = dibujo.chip(pantalla, cadena, (x, y), ancla="midleft")
    dibujo.texto(pantalla, descripcion, (chip.right + 8, y), assets.COLOR_TEXTO_SECUNDARIO,
                 assets.TAMANIO_FUENTE_PEQUENA, ancla="midleft")
    return pygame.Rect(x, y - chip.height // 2, total, chip.height)


def opcion(pantalla, rect, texto, seleccionada, tiempo=0.0, acento=assets.COLOR_CIVITAS, detalle="", tamanio=None):
    """Tarjeta elegible. Un solo estilo de foco para TODO el juego: filo y
    fondo violeta con un latido suave. El foco nunca sugiere si es correcta."""
    rect = pygame.Rect(rect)
    if seleccionada:
        latido = 0.5 + 0.5 * math.sin(tiempo * 4)
        pygame.draw.rect(pantalla, acento, rect.inflate(round(4 + 3 * latido), round(4 + 3 * latido)), 1, border_radius=9)
        dibujo.panel(pantalla, rect, assets.COLOR_FOCO_FONDO, acento, 2, radio=8)
    else:
        dibujo.panel(pantalla, rect, assets.COLOR_OPCION_FONDO, assets.COLOR_BORDE_VIDRIO, 1, radio=8)
    color = assets.COLOR_TEXTO_HUD if seleccionada else assets.COLOR_TEXTO_SECUNDARIO
    interior = rect.inflate(-24, -16)
    tam = tamanio or assets.TAMANIO_FUENTE_NORMAL
    if detalle:
        titulo_y = layout.parrafo_en_caja(pantalla, texto, pygame.Rect(interior.left, interior.top, interior.width, interior.height // 2),
                                          color, tam, negrita=True, interlineado=2)
        layout.parrafo_en_caja(pantalla, detalle, pygame.Rect(interior.left, titulo_y + 2, interior.width, interior.bottom - titulo_y - 2),
                               assets.COLOR_TEXTO_SECUNDARIO, assets.TAMANIO_FUENTE_PEQUENA, interlineado=2)
    else:
        layout.parrafo_en_caja(pantalla, texto, interior, color, tam, negrita=True, interlineado=2, alinear_arriba=False,
                               centrado=True)
    return rect


def barra_reputacion(pantalla, rect, valor, valor_marca=None, mostrar_tramos=True):
    """Barra de -100 a +100 con el cero al centro, tramos por nivel y marca
    del valor anterior. Se llena desde el centro, en cian o magenta."""
    rect = pygame.Rect(rect)
    pygame.draw.rect(pantalla, assets.COLOR_FONDO_BARRA, rect, border_radius=rect.height // 2)
    x_de = lambda v: rect.left + round(rect.width * (v + 100) / 200)  # noqa: E731
    centro = x_de(0)
    x_valor = x_de(max(-100, min(100, valor)))
    color = assets.color_reputacion(valor)
    if x_valor != centro:
        relleno = pygame.Rect(min(centro, x_valor), rect.top, abs(x_valor - centro), rect.height)
        pygame.draw.rect(pantalla, color, relleno, border_radius=rect.height // 2)
    if mostrar_tramos:
        for marca in assets.MARCAS_REPUTACION:
            pygame.draw.line(pantalla, assets.COLOR_NOCHE, (x_de(marca), rect.top), (x_de(marca), rect.bottom - 1), 1)
    pygame.draw.line(pantalla, assets.COLOR_TEXTO_HUD, (centro, rect.top - 2), (centro, rect.bottom + 1), 1)
    if valor_marca is not None:
        x = x_de(valor_marca)
        pygame.draw.line(pantalla, assets.COLOR_TEXTO_HUD, (x, rect.top - 4), (x, rect.bottom + 3), 2)
    # Puntero del valor actual.
    pygame.draw.polygon(pantalla, assets.COLOR_TEXTO_HUD,
                        [(x_valor - 5, rect.bottom + 8), (x_valor + 5, rect.bottom + 8), (x_valor, rect.bottom + 2)])
    return rect


def puntos_oportunidad(pantalla, posicion, restantes, total, color=assets.COLOR_ALERTA):
    """Círculos de oportunidades que quedan: el jugador sabe cuánto margen tiene."""
    x, y = posicion
    for i in range(total):
        centro = (x + i * 20, y)
        if i < restantes:
            pygame.draw.circle(pantalla, color, centro, 6)
        else:
            pygame.draw.circle(pantalla, assets.COLOR_BORDE_VIDRIO, centro, 6, 2)
    return x + total * 20
