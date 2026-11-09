"""Mapa del mundo: el grafo de calles de Ciudad Nova en abstracto
(tecla M en la escena CIUDAD, solo presentación y solo lectura).

Cada nodo se dibuja en su casilla del mapa escalada
(ORIGEN_MAPA_MUNDO + casilla * ESCALA_MAPA_MUNDO, la misma escala en x
y en y), así el dibujo conserva la forma y las distancias de la ciudad:
una calle que se ve el doble de larga mide y pesa el doble. Calles como
líneas (por sus codos) con su peso en la mitad del recorrido, las
bloqueadas en magenta con su barricada, zonas como círculos con nombre y
toxicidad, cruces como puntos, el jugador en su lugar, una leyenda de
escala y la ruta sugerida (Dijkstra) hasta el destino elegido con TAB,
con sus metros, el tiempo a pie y el costo total en un panel inferior.
No modifica la partida.
"""

import pygame

from src.core import assets
from src.dungeon import ciudad_mapa
from src.core.balance import METROS_POR_CASILLA, METROS_POR_PUNTO_DE_PESO
from src.dungeon.grafo_ciudad import CRUCES, ZONA_FINAL, ZONA_INICIO, metros_tramo, tiempo_recorrido
from src.ui import casillas_ciudad, dibujo, sprites
from src.ui.fuentes import fuente


def a_pantalla(col, fila):
    """Casilla (puede ser fraccionaria) -> px de pantalla del mapa."""
    ox, oy = assets.ORIGEN_MAPA_MUNDO
    sx, sy = assets.ESCALA_MAPA_MUNDO
    return (round(ox + (col + 0.5) * sx), round(oy + (fila + 0.5) * sy))


def _puntos_tramo(a, b):
    return [a_pantalla(*punto) for punto in ciudad_mapa.tramo(a, b).puntos]


def dibujar_mapa_mundo(pantalla, partida, seleccionada, posicion_jugador):
    ciudad = partida.ciudad
    ruta = partida.ruta_sugerida(posicion_jugador, seleccionada)
    camino = ruta[0] if ruta else []
    tramos_ruta = {frozenset(par) for par in zip(camino, camino[1:])}

    _dibujar_fondo(pantalla)

    # Primero las líneas (la ruta más gruesa), luego los pesos encima.
    calles = ciudad.calles()
    for a, b, _ in calles:
        puntos = _puntos_tramo(a, b)
        if ciudad.esta_bloqueada(a, b):
            for p, q in zip(puntos, puntos[1:]):
                dibujo.linea_punteada(pantalla, assets.COLOR_CALLE_BLOQUEADA, p, q, 8, 6, assets.GROSOR_CALLE)
            continue
        en_ruta = frozenset((a, b)) in tramos_ruta
        color = assets.COLOR_RUTA_SEGURA if en_ruta else assets.COLOR_CALLE
        grosor = assets.GROSOR_RUTA_SEGURA if en_ruta else assets.GROSOR_CALLE
        pygame.draw.lines(pantalla, color, False, puntos, grosor)
    for a, b, peso in calles:
        _dibujar_peso(pantalla, a, b, peso, frozenset((a, b)) in tramos_ruta, ciudad.esta_bloqueada(a, b))

    for cruce in CRUCES:
        centro = a_pantalla(*ciudad_mapa.NODOS_CALLE[cruce])
        pygame.draw.circle(pantalla, assets.COLOR_ZONA_MAPA, centro, assets.RADIO_CRUCE_MAPA)
        pygame.draw.circle(pantalla, assets.COLOR_FONDO, centro, assets.RADIO_CRUCE_MAPA, 2)
    for zona in ciudad.zonas():
        _dibujar_zona(pantalla, partida, zona, zona == seleccionada)

    # El jugador, donde está en el mundo.
    col = posicion_jugador[0] / ciudad_mapa.TAM_CASILLA - 0.5
    fila = posicion_jugador[1] / ciudad_mapa.TAM_CASILLA - 0.5
    imagen = sprites.sprite_jugador(assets.COLOR_ZONA_ACTUAL, assets.ESCALA_JUGADOR_MAPA_MUNDO)
    sprites.dibujar_centrado(pantalla, imagen, a_pantalla(col, fila))

    _dibujar_escala(pantalla)
    _dibujar_panel_ruta(pantalla, seleccionada, ruta)


def _dibujar_fondo(pantalla):
    """Cuadrícula tenue en la zona de la vista."""
    area = pygame.Rect(assets.RECT_VISTA_CIUDAD)
    pygame.draw.rect(pantalla, assets.COLOR_FONDO, area)
    paso = 40
    color = assets.COLOR_FONDO_PANEL
    for x in range(area.left, area.right, paso):
        pygame.draw.line(pantalla, color, (x, area.top), (x, area.bottom))
    for y in range(area.top, area.bottom, paso):
        pygame.draw.line(pantalla, color, (area.left, y), (area.right, y))


def _dibujar_peso(pantalla, a, b, peso, en_ruta, bloqueada):
    centro = pygame.Vector2(a_pantalla(*ciudad_mapa.punto_medio_tramo(ciudad_mapa.tramo(a, b))))
    if bloqueada:
        imagen = casillas_ciudad.casilla_barricada()
        pantalla.blit(imagen, imagen.get_rect(center=(centro.x, centro.y - 18)))
        borde = assets.COLOR_CALLE_BLOQUEADA
    else:
        borde = assets.COLOR_RUTA_SEGURA if en_ruta else assets.COLOR_CALLE
    pygame.draw.circle(pantalla, assets.COLOR_FONDO_ETIQUETA_PESO, centro, assets.RADIO_ETIQUETA_PESO)
    pygame.draw.circle(pantalla, borde, centro, assets.RADIO_ETIQUETA_PESO, assets.GROSOR_BORDE_ETIQUETA_PESO)
    dibujo.texto(pantalla, str(peso), centro, assets.COLOR_TEXTO_HUD, assets.TAMANIO_FUENTE_PEQUENA,
                 negrita=True, ancla="center")


def _dibujar_zona(pantalla, partida, zona, seleccionada):
    centro = a_pantalla(*ciudad_mapa.NODOS_CALLE[zona])
    radio = assets.RADIO_ZONA_MAPA
    if zona == ZONA_INICIO:
        color = assets.COLOR_ZONA_ACTUAL
    elif zona == ZONA_FINAL:
        color = assets.COLOR_ZONA_ALCALDIA
    else:
        color = assets.COLORES_NEON_ZONA.get(zona, assets.COLOR_ZONA_MAPA)
    if seleccionada:
        halo = pygame.Surface((radio * 4, radio * 4), pygame.SRCALPHA)
        pygame.draw.circle(halo, (*assets.COLOR_ZONA_SELECCIONADA, 40), (radio * 2, radio * 2), round(radio * 1.6))
        pantalla.blit(halo, halo.get_rect(center=centro))
    pygame.draw.circle(pantalla, color, centro, radio)
    pygame.draw.circle(pantalla, assets.COLOR_FONDO, centro, radio, 3)
    if seleccionada:
        pygame.draw.circle(pantalla, assets.COLOR_ZONA_SELECCIONADA, centro,
                           radio + assets.GROSOR_ZONA_SELECCIONADA + 2, assets.GROSOR_ZONA_SELECCIONADA)
    dibujo.texto(pantalla, zona[0], centro, assets.COLOR_FONDO, assets.TAMANIO_FUENTE_TITULO,
                 negrita=True, ancla="center")

    color_nombre = assets.COLOR_ZONA_SELECCIONADA if seleccionada else assets.COLOR_TEXTO_HUD
    ancla, ox, oy = assets.ETIQUETAS_MAPA_MUNDO[zona]
    _etiqueta(pantalla, zona, _detalle_zona(partida, zona), (centro[0] + ox, centro[1] + oy), color_nombre, ancla)


def _etiqueta(pantalla, nombre, detalle, posicion, color_nombre, ancla):
    """Nombre + detalle sobre un panel, para que las calles no los tapen."""
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
        return "Inicio"
    if zona == ZONA_FINAL:
        return "Jefe final" if partida.alcaldia_desbloqueada() else "Sellada"
    return f"Toxicidad {partida.toxicidad(zona):.0f}"


def _dibujar_escala(pantalla):
    """Barra de escala (20 m = cuántas casillas) y cómo se calcula el peso."""
    derecha, y = assets.POSICION_ESCALA_MAPA
    casillas = METROS_POR_PUNTO_DE_PESO / METROS_POR_CASILLA
    largo = round(casillas * assets.ESCALA_MAPA_MUNDO[0])
    color = assets.COLOR_ESCALA_MAPA
    pygame.draw.line(pantalla, color, (derecha - largo, y), (derecha, y), 2)
    for x in (derecha - largo, derecha):
        pygame.draw.line(pantalla, color, (x, y - 5), (x, y + 5), 2)
    dibujo.texto(pantalla, f"{METROS_POR_PUNTO_DE_PESO} m = 1 de peso", (derecha - largo - 10, y), color,
                 assets.TAMANIO_FUENTE_PEQUENA, ancla="midright")
    dibujo.texto(pantalla, f"1 casilla = {METROS_POR_CASILLA} m · peso = largo + saturación", (derecha, y + 12),
                 color, assets.TAMANIO_FUENTE_PEQUENA, ancla="topright")


def _dibujar_panel_ruta(pantalla, destino, ruta):
    panel = dibujo.panel(pantalla, assets.RECT_PANEL_RUTA)
    x, y = assets.POSICION_TEXTO_RUTA
    texto_ruta = " › ".join(ruta[0]) if ruta else assets.TEXTO_SIN_RUTA
    dibujo.texto(pantalla, f"Ruta sugerida a {destino} (Dijkstra, sin calles bloqueadas)", (x, y),
                 assets.COLOR_TEXTO_SECUNDARIO, assets.TAMANIO_FUENTE_PEQUENA)
    dibujo.texto(pantalla, texto_ruta, (x, y + 22), assets.COLOR_TEXTO_HUD, assets.TAMANIO_FUENTE_NORMAL, negrita=True)
    if ruta:
        tramos = list(zip(ruta[0], ruta[0][1:]))
        metros = sum(metros_tramo(a, b) for a, b in tramos)
        segundos = sum(tiempo_recorrido(a, b) for a, b in tramos)
        dibujo.chip(pantalla, f"Costo {ruta[1]:g} · {metros} m · ~{segundos:.0f} s", (panel.right - 16, panel.centery),
                    assets.COLOR_AMARILLO,
                    assets.COLOR_FONDO, assets.COLOR_AMARILLO, assets.TAMANIO_FUENTE_NORMAL, ancla="midright",
                    alto=32, margen=12)
