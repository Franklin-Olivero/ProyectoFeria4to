"""Dibujo del mapa de la ciudad (escena MAPA_CIUDAD, solo presentación).

Pinta el GrafoCiudad de la Partida: calles como líneas con su peso
(saturación) encima, zonas como círculos con su nombre, la ruta más
segura (Dijkstra) desde la ubicación actual hasta la zona seleccionada
resaltada, y su costo en colapso. No modifica la partida.
"""

import pygame

from src.core import assets
from src.core.balance import COSTO_VIAJE_COLAPSO
from src.dungeon.clasificador_toxicidad import calcular_nivel_toxicidad, construir_arbol_reportes
from src.dungeon.grafo_ciudad import ZONA_FINAL, ZONA_INICIO

TITULO = "Mapa de la ciudad"
AYUDA = "Flechas izq/der: elegir zona   ENTER: viajar"


def dibujar_mapa_ciudad(pantalla, partida, seleccionada, fuente, fuente_pequena):
    ciudad = partida.ciudad
    posiciones = assets.POSICIONES_MAPA_CIUDAD
    camino, costo = partida.ruta_hasta(seleccionada)
    tramos_ruta = set()
    for a, b in zip(camino, camino[1:]):
        tramos_ruta.add(frozenset((a, b)))

    titulo = fuente.render(TITULO, True, assets.COLOR_TEXTO_HUD)
    pantalla.blit(titulo, titulo.get_rect(center=assets.POSICION_TITULO_MAPA))

    # Calles: primero las líneas (la ruta segura más gruesa), luego los
    # pesos encima para que ninguna línea los tape.
    calles = ciudad.calles()
    for a, b, _ in calles:
        en_ruta = frozenset((a, b)) in tramos_ruta
        color = assets.COLOR_RUTA_SEGURA if en_ruta else assets.COLOR_CALLE
        grosor = assets.GROSOR_RUTA_SEGURA if en_ruta else assets.GROSOR_CALLE
        pygame.draw.line(pantalla, color, posiciones[a], posiciones[b], grosor)
    for a, b, peso in calles:
        _dibujar_peso(pantalla, fuente_pequena, posiciones[a], posiciones[b], peso,
                      frozenset((a, b)) in tramos_ruta)

    for zona in ciudad.zonas():
        _dibujar_zona(pantalla, fuente, fuente_pequena, partida, zona, zona == seleccionada)

    _dibujar_textos_ruta(pantalla, fuente_pequena, camino, costo)


def _dibujar_peso(pantalla, fuente, a, b, peso, en_ruta):
    centro = ((a[0] + b[0]) // 2, (a[1] + b[1]) // 2)
    borde = assets.COLOR_RUTA_SEGURA if en_ruta else assets.COLOR_CALLE
    pygame.draw.circle(pantalla, assets.COLOR_FONDO_ETIQUETA_PESO, centro, assets.RADIO_ETIQUETA_PESO)
    pygame.draw.circle(pantalla, borde, centro, assets.RADIO_ETIQUETA_PESO, assets.GROSOR_BORDE_ETIQUETA_PESO)
    texto = fuente.render(str(peso), True, assets.COLOR_TEXTO_HUD)
    pantalla.blit(texto, texto.get_rect(center=centro))


def _dibujar_zona(pantalla, fuente, fuente_pequena, partida, zona, seleccionada):
    centro = assets.POSICIONES_MAPA_CIUDAD[zona]
    radio = assets.RADIO_ZONA_MAPA
    if zona == partida.ubicacion:
        color = assets.COLOR_ZONA_ACTUAL
    elif zona == ZONA_FINAL:
        color = assets.COLOR_ZONA_ALCALDIA
    else:
        color = assets.COLOR_ZONA_MAPA
    pygame.draw.circle(pantalla, color, centro, radio)
    if seleccionada:
        pygame.draw.circle(
            pantalla, assets.COLOR_ZONA_SELECCIONADA, centro,
            radio + assets.GROSOR_ZONA_SELECCIONADA, assets.GROSOR_ZONA_SELECCIONADA,
        )

    color_nombre = assets.COLOR_ZONA_SELECCIONADA if seleccionada else assets.COLOR_TEXTO_HUD
    nombre = fuente.render(zona, True, color_nombre)
    detalle = fuente_pequena.render(_detalle_zona(partida, zona), True, assets.COLOR_TEXTO_SECUNDARIO)
    separacion = assets.SEPARACION_NOMBRE_ZONA // 2
    if zona in assets.ZONAS_ETIQUETA_ABAJO:
        rect_nombre = nombre.get_rect(midtop=(centro[0], centro[1] + radio + separacion))
        rect_detalle = detalle.get_rect(midtop=(centro[0], rect_nombre.bottom + separacion // 2))
    else:
        rect_nombre = nombre.get_rect(midbottom=(centro[0], centro[1] - radio - separacion))
        rect_detalle = detalle.get_rect(midtop=(centro[0], centro[1] + radio + separacion))
    _blit_con_fondo(pantalla, nombre, rect_nombre)
    _blit_con_fondo(pantalla, detalle, rect_detalle)


def _blit_con_fondo(pantalla, superficie, rect):
    """Texto sobre un recuadro del color de fondo: las calles que pasan
    por detrás no lo tapan."""
    margen = assets.MARGEN_FONDO_ETIQUETA
    pygame.draw.rect(pantalla, assets.COLOR_FONDO, rect.inflate(margen * 2, margen * 2))
    pantalla.blit(superficie, rect)


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
        detalle += " (aquí)"
    return detalle


def _dibujar_textos_ruta(pantalla, fuente, camino, costo):
    ruta = fuente.render("Ruta más segura: " + " > ".join(camino), True, assets.COLOR_TEXTO_HUD)
    pantalla.blit(ruta, assets.POSICION_TEXTO_RUTA)
    texto_costo = f"Costo: {costo:g}  (+{costo * COSTO_VIAJE_COLAPSO:.2f}% colapso)"
    pantalla.blit(fuente.render(texto_costo, True, assets.COLOR_RUTA_SEGURA), assets.POSICION_TEXTO_COSTO)
    pantalla.blit(fuente.render(AYUDA, True, assets.COLOR_TEXTO_SECUNDARIO), assets.POSICION_TEXTO_AYUDA_MAPA)
