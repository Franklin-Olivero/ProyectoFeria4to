"""Dibujo del mapa de la ciudad (escena MAPA_CIUDAD, solo presentación).

Pinta el GrafoCiudad de la Partida: calles como líneas con su peso
(saturación) encima, zonas como círculos con su nombre, la ruta más
segura (Dijkstra) desde la ubicación actual hasta la zona seleccionada
resaltada, y su costo en colapso en un panel inferior. No modifica la
partida. El HUD superior y la barra de controles los dibuja Main.py.
"""

import pygame

from src.core import assets
from src.core.balance import COSTO_VIAJE_COLAPSO
from src.dungeon.clasificador_toxicidad import calcular_nivel_toxicidad, construir_arbol_reportes
from src.dungeon.grafo_ciudad import ZONA_FINAL, ZONA_INICIO
from src.ui import dibujo

TITULO = "Mapa de la ciudad"


def dibujar_mapa_ciudad(pantalla, partida, seleccionada):
    ciudad = partida.ciudad
    posiciones = assets.POSICIONES_MAPA_CIUDAD
    camino, costo = partida.ruta_hasta(seleccionada)
    camino = camino or []
    tramos_ruta = set()
    for a, b in zip(camino, camino[1:]):
        tramos_ruta.add(frozenset((a, b)))

    _dibujar_fondo(pantalla)

    # Calles: primero las líneas (la ruta segura más gruesa), luego los
    # pesos encima para que ninguna línea los tape.
    calles = ciudad.calles()
    for a, b, _ in calles:
        en_ruta = frozenset((a, b)) in tramos_ruta
        color = assets.COLOR_RUTA_SEGURA if en_ruta else assets.COLOR_CALLE
        grosor = assets.GROSOR_RUTA_SEGURA if en_ruta else assets.GROSOR_CALLE
        pygame.draw.line(pantalla, color, posiciones[a], posiciones[b], grosor)
    for a, b, peso in calles:
        _dibujar_peso(pantalla, posiciones[a], posiciones[b], peso, frozenset((a, b)) in tramos_ruta)

    for zona in ciudad.zonas():
        _dibujar_zona(pantalla, partida, zona, zona == seleccionada)

    _dibujar_panel_ruta(pantalla, camino, costo)


def _dibujar_fondo(pantalla):
    """Cuadrícula tenue entre el HUD y la barra de controles."""
    area = pygame.Rect(0, assets.ALTO_HUD, pantalla.get_width(),
                       pantalla.get_height() - assets.ALTO_HUD - assets.ALTO_BARRA_CONTROLES)
    paso = 40
    color = (22, 20, 46)
    for x in range(area.left, area.right, paso):
        pygame.draw.line(pantalla, color, (x, area.top), (x, area.bottom))
    for y in range(area.top, area.bottom, paso):
        pygame.draw.line(pantalla, color, (area.left, y), (area.right, y))


def _dibujar_peso(pantalla, a, b, peso, en_ruta):
    centro = ((a[0] + b[0]) // 2, (a[1] + b[1]) // 2)
    borde = assets.COLOR_RUTA_SEGURA if en_ruta else assets.COLOR_CALLE
    pygame.draw.circle(pantalla, assets.COLOR_FONDO_ETIQUETA_PESO, centro, assets.RADIO_ETIQUETA_PESO)
    pygame.draw.circle(pantalla, borde, centro, assets.RADIO_ETIQUETA_PESO, assets.GROSOR_BORDE_ETIQUETA_PESO)
    dibujo.texto(pantalla, str(peso), centro, assets.COLOR_TEXTO_HUD, assets.TAMANIO_FUENTE_PEQUENA,
                 negrita=True, ancla="center")


def _dibujar_zona(pantalla, partida, zona, seleccionada):
    centro = assets.POSICIONES_MAPA_CIUDAD[zona]
    radio = assets.RADIO_ZONA_MAPA
    if zona == partida.ubicacion:
        color = assets.COLOR_ZONA_ACTUAL
    elif zona == ZONA_FINAL:
        color = assets.COLOR_ZONA_ALCALDIA
    else:
        color = assets.COLOR_ZONA_MAPA
    if seleccionada:
        halo = pygame.Surface((radio * 4, radio * 4), pygame.SRCALPHA)
        pygame.draw.circle(halo, (*assets.COLOR_ZONA_SELECCIONADA, 40), (radio * 2, radio * 2), round(radio * 1.6))
        pantalla.blit(halo, halo.get_rect(center=centro))
    pygame.draw.circle(pantalla, color, centro, radio)
    pygame.draw.circle(pantalla, assets.COLOR_FONDO, centro, radio, 3)
    if seleccionada:
        pygame.draw.circle(pantalla, assets.COLOR_ZONA_SELECCIONADA, centro,
                           radio + assets.GROSOR_ZONA_SELECCIONADA + 2, assets.GROSOR_ZONA_SELECCIONADA)
    # Inicial de la zona dentro del círculo.
    dibujo.texto(pantalla, zona[0], centro, assets.COLOR_FONDO, assets.TAMANIO_FUENTE_TITULO,
                 negrita=True, ancla="center")

    color_nombre = assets.COLOR_ZONA_SELECCIONADA if seleccionada else assets.COLOR_TEXTO_HUD
    detalle = _detalle_zona(partida, zona)
    separacion = assets.SEPARACION_NOMBRE_ZONA
    if zona in assets.ZONAS_ETIQUETA_ABAJO:
        _etiqueta(pantalla, zona, detalle, (centro[0], centro[1] + radio + separacion), color_nombre, "midtop")
    else:
        _etiqueta(pantalla, zona, detalle, (centro[0], centro[1] - radio - separacion), color_nombre, "midbottom")


def _etiqueta(pantalla, nombre, detalle, posicion, color_nombre, ancla):
    """Nombre + detalle sobre un panel, para que las calles no los tapen."""
    from src.ui.fuentes import fuente

    ancho = max(fuente(assets.TAMANIO_FUENTE_MEDIA, True).size(nombre)[0],
                fuente(assets.TAMANIO_FUENTE_PEQUENA).size(detalle)[0]) + 24
    rect = pygame.Rect(0, 0, ancho, 48)
    setattr(rect, ancla, posicion)
    dibujo.panel(pantalla, rect, assets.COLOR_FONDO_PANEL, assets.COLOR_BORDE_PANEL, 1)
    dibujo.texto(pantalla, nombre, (rect.centerx, rect.top + 14), color_nombre, assets.TAMANIO_FUENTE_MEDIA,
                 negrita=True, ancla="center")
    dibujo.texto(pantalla, detalle, (rect.centerx, rect.top + 34), assets.COLOR_TEXTO_SECUNDARIO,
                 assets.TAMANIO_FUENTE_PEQUENA, ancla="center")


def _detalle_zona(partida, zona):
    """Texto bajo cada zona: inicio, estado de la Alcaldía o toxicidad."""
    if zona == ZONA_INICIO:
        detalle = "Inicio"
    elif zona == ZONA_FINAL:
        detalle = "Jefe final" if partida.alcaldia_desbloqueada() else "Bloqueada"
    else:
        reportes = partida.ciudad.reportes(zona)
        nivel = calcular_nivel_toxicidad(construir_arbol_reportes(reportes, zona))
        detalle = f"Toxicidad {nivel:.0f}"
    if zona == partida.ubicacion:
        detalle += " · aquí"
    return detalle


def _dibujar_panel_ruta(pantalla, camino, costo):
    panel = dibujo.panel(pantalla, assets.RECT_PANEL_RUTA)
    x, y = assets.POSICION_TEXTO_RUTA
    dibujo.texto(pantalla, "Ruta más segura (Dijkstra)", (x, y), assets.COLOR_TEXTO_SECUNDARIO,
                 assets.TAMANIO_FUENTE_PEQUENA)
    ruta = " › ".join(camino) if camino else "sin ruta"
    dibujo.texto(pantalla, ruta, (x, y + 18), assets.COLOR_TEXTO_HUD, assets.TAMANIO_FUENTE_NORMAL, negrita=True)
    texto_costo = f"Costo {costo:g}  ·  +{costo * COSTO_VIAJE_COLAPSO:.2f}% colapso"
    dibujo.chip(pantalla, texto_costo, (panel.right - 16, panel.centery), assets.COLOR_AMARILLO,
                assets.COLOR_FONDO, assets.COLOR_AMARILLO, assets.TAMANIO_FUENTE_NORMAL, ancla="midright",
                alto=32, margen=12)
