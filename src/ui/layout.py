"""Capa de interfaz común: zonas seguras, texto que siempre cabe y
animaciones de entrada (solo presentación).

Reglas que aplican todas las pantallas del modo historia:
    - ningún texto sale de assets.RECT_ZONA_SEGURA ni de su panel;
    - un bloque de texto que no cabe primero se parte en líneas
      (word wrap real), luego baja de tamaño y, si aun así no cabe,
      se recorta con "…" en la última línea (nunca se dibuja cortado);
    - los overlays modales (diálogo, cinemática, panel de estado,
      ayuda, misión) se dibujan en un orden fijo de capas (CAPA_*) y
      solo uno de los modales se muestra a la vez (Main.py elige el
      prioritario con `modal_prioritario`);
    - cada overlay entra con un deslizamiento corto (`entrada`).

Las funciones puras (`recortar_lineas`, `fraccion_entrada`,
`modal_prioritario`) no necesitan pygame para probarse; las de dibujo sí.
"""

import pygame

from src.core import assets
from src.ui import dibujo
from src.ui.fuentes import fuente

# Orden de capas (de abajo hacia arriba). Main.py dibuja en este orden.
CAPA_MUNDO = 0
CAPA_HUD = 1
CAPA_PANEL = 2  # paneles no modales: misión, minimapa, tarjeta de evidencia
CAPA_MODAL = 3  # un único modal: estado, ayuda, diálogo, cinemática
CAPA_TOAST = 4  # avisos breves encima de todo

# Prioridad de los modales cuando más de uno quiere mostrarse (menor = más prioritario).
PRIORIDAD_MODALES = ("cinematica", "dialogo", "ayuda", "estado", "mapa_mundo")


def modal_prioritario(activos):
    """Nombre del único modal que se dibuja: el más prioritario de los
    activos (nombres de PRIORIDAD_MODALES). None si no hay ninguno. O(n)."""
    for nombre in PRIORIDAD_MODALES:
        if nombre in activos:
            return nombre
    return None


def fraccion_entrada(transcurrido, duracion=assets.DURACION_ENTRADA_PANEL):
    """0-1 de la animación de entrada con desaceleración (ease-out cúbico)."""
    if duracion <= 0:
        return 1.0
    t = max(0.0, min(1.0, transcurrido / duracion))
    return 1 - (1 - t) ** 3


def recortar_lineas(lineas, maximo):
    """Deja a lo sumo `maximo` líneas; si sobra, la última termina en "…"."""
    if maximo <= 0:
        return []
    if len(lineas) <= maximo:
        return list(lineas)
    recorte = list(lineas[:maximo])
    ultima = recorte[-1].rstrip(" .,;:")
    recorte[-1] = (ultima[:-1] if len(ultima) > 1 else ultima) + "…"
    return recorte


def texto_que_cabe(cadena, ancho, alto, tamanio=assets.TAMANIO_FUENTE_NORMAL, negrita=False,
                   interlineado=4, minimo=assets.TAMANIO_FUENTE_PEQUENA):
    """(tamaño elegido, líneas) tal que el párrafo cabe en ancho x alto:
    baja el tamaño de a 1 px hasta `minimo` y, si todavía no cabe,
    recorta las líneas con "…"."""
    tamanio_actual = tamanio
    while True:
        lineas = dibujo.ajustar_texto(cadena, tamanio_actual, ancho, negrita)
        alto_linea = fuente(tamanio_actual, negrita).get_height() + interlineado
        caben = max(1, int((alto + interlineado) // alto_linea))
        if len(lineas) <= caben or tamanio_actual <= minimo:
            return tamanio_actual, recortar_lineas(lineas, caben)
        tamanio_actual -= 1


def parrafo_en_caja(pantalla, cadena, rect, color=assets.COLOR_TEXTO_HUD, tamanio=assets.TAMANIO_FUENTE_NORMAL,
                    negrita=False, interlineado=4, centrado=False, alinear_arriba=True):
    """Dibuja `cadena` dentro de `rect` sin salirse (word wrap, reducción
    de tamaño y recorte con "…"). Retorna la y donde terminó el texto."""
    rect = pygame.Rect(rect)
    tamanio_final, lineas = texto_que_cabe(cadena, rect.width, rect.height, tamanio, negrita, interlineado)
    alto_linea = fuente(tamanio_final, negrita).get_height() + interlineado
    total = len(lineas) * alto_linea - interlineado
    y = rect.top if alinear_arriba else rect.centery - total // 2
    for linea in lineas:
        if centrado:
            dibujo.texto(pantalla, linea, (rect.centerx, y), color, tamanio_final, negrita, ancla="midtop")
        else:
            dibujo.texto(pantalla, linea, (rect.left, y), color, tamanio_final, negrita)
        y += alto_linea
    return y


def parrafo_progresivo(pantalla, cadena, visibles, rect, color=assets.COLOR_TEXTO_HUD,
                       tamanio=assets.TAMANIO_FUENTE_NORMAL, negrita=False, interlineado=4):
    """Máquina de escribir: el párrafo se parte en líneas con el texto
    COMPLETO y se dibujan solo los primeros `visibles` caracteres. Así una
    palabra no salta de línea a mitad de escribirse."""
    rect = pygame.Rect(rect)
    tamanio_final, lineas = texto_que_cabe(cadena, rect.width, rect.height, tamanio, negrita, interlineado)
    alto_linea = fuente(tamanio_final, negrita).get_height() + interlineado
    y = rect.top
    restantes = visibles
    for linea in lineas:
        if restantes <= 0:
            break
        dibujo.texto(pantalla, linea[:restantes], (rect.left, y), color, tamanio_final, negrita)
        restantes -= len(linea) + 1
        y += alto_linea
    return y


def texto_en_ancho(pantalla, cadena, posicion, ancho, color=assets.COLOR_TEXTO_HUD,
                   tamanio=assets.TAMANIO_FUENTE_NORMAL, negrita=False, ancla="topleft",
                   minimo=assets.TAMANIO_FUENTE_PEQUENA):
    """Una sola línea que nunca pasa de `ancho`: baja el tamaño hasta
    `minimo` y luego recorta con "…". Retorna el rect dibujado."""
    tamanio_actual = tamanio
    while tamanio_actual > minimo and fuente(tamanio_actual, negrita).size(cadena)[0] > ancho:
        tamanio_actual -= 1
    f = fuente(tamanio_actual, negrita)
    while len(cadena) > 1 and f.size(cadena)[0] > ancho:
        cadena = cadena[:-2].rstrip() + "…"
    return dibujo.texto(pantalla, cadena, posicion, color, tamanio_actual, negrita, ancla)


def velo(pantalla, color=assets.COLOR_VELO_OVERLAY):
    """Oscurece toda la pantalla detrás de un modal."""
    capa = pygame.Surface(pantalla.get_size(), pygame.SRCALPHA)
    capa.fill(color)
    pantalla.blit(capa, (0, 0))


def entrada(rect, transcurrido, desde="abajo", distancia=24):
    """Rect desplazado según la animación de entrada: llega desde
    `desde` ("abajo", "arriba", "izquierda", "derecha") y se asienta."""
    rect = pygame.Rect(rect)
    falta = round(distancia * (1 - fraccion_entrada(transcurrido)))
    if desde == "abajo":
        rect.y += falta
    elif desde == "arriba":
        rect.y -= falta
    elif desde == "izquierda":
        rect.x -= falta
    else:
        rect.x += falta
    return rect


def alfa_entrada(transcurrido):
    return round(255 * fraccion_entrada(transcurrido))
