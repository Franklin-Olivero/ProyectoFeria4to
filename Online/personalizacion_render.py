"""Dibujo y ratón del vestidor del lobby online (estilo Among Us).

Modal sobre la sala: botón X para cerrar, pestañas COLOR / HAT / SKIN
arriba, a la izquierda el jugador en grande con lo que lleva puesto y a
la derecha la cuadrícula de opciones de la pestaña (la equipada,
resaltada). Cada casilla muestra la parte real que se pondría, armada
desde las recetas de Pixelbolt (sprites.sprite_parte_jugador): la cabeza
con ese tono de piel (COLOR), la cabeza de ese rol (HAT) o su torso y
piernas (SKIN). Qué opciones hay y qué se equipa lo decide
Online/personalizacion.py.
"""

import math

import pygame

from src.core import assets
from src.ui import dibujo, sprites

from Online.personalizacion import (
    COLOR, COLUMNAS, HAT, PESTANAS, SKIN, etiqueta_opcion, nombre_rol, opciones, texto_opcion,
)

COLOR_ACENTO = assets.COLOR_ACENTO_VESTIDOR

RECT_MODAL = pygame.Rect(170, 84, 940, 540)
CENTRO_CERRAR = (RECT_MODAL.left + 34, RECT_MODAL.top + 34)
RADIO_CERRAR = 20
X_PESTANAS = RECT_MODAL.left + 72
Y_PESTANAS = RECT_MODAL.top + 12
ANCHO_PESTANA = 150
ALTO_PESTANA = 44
SEPARACION_PESTANAS = 10
RECT_VISTA = pygame.Rect(RECT_MODAL.left + 20, RECT_MODAL.top + 72, 300, 420)
RECT_OPCIONES = pygame.Rect(RECT_VISTA.right + 20, RECT_VISTA.top,
                            RECT_MODAL.right - RECT_VISTA.right - 40, RECT_VISTA.height)
LADO_CASILLA = 100
SEPARACION_CASILLAS = 10
MARGEN_CUADRICULA = 20  # entre el borde del panel de opciones y la primera fila
ESCALA_VISTA = 12  # jugador de la vista previa: 192x240 px
ESCALA_CASILLA = 5  # parte de cada casilla: 80x50 px
RADIO_MUESTRA_TONO = 8

AYUDA_PESTANA = {
    COLOR: "Tono de piel de la cara y las manos. AUTO deja el tono original de la cabeza que lleves.",
    HAT: "La parte de arriba (pelo, cara y lentes) de cualquier personaje. AUTO usa la de tu rol "
         "y cambia sola si eliges otro rol en la laptop.",
    SKIN: "El traje (camisa, pantalón y zapatos) de cualquier personaje. Tu accesorio "
            "(megáfono, micrófono...) siempre es el de tu rol.",
}

# Qué hay bajo el ratón (objetivo_en).
CERRAR = "cerrar"
PESTANA = "pestana"
OPCION = "opcion"
DENTRO = "dentro"
FUERA = "fuera"


def rect_pestana(indice):
    return pygame.Rect(X_PESTANAS + indice * (ANCHO_PESTANA + SEPARACION_PESTANAS), Y_PESTANAS,
                       ANCHO_PESTANA, ALTO_PESTANA)


def rect_casilla(indice):
    """Casilla `indice` de la cuadrícula (COLUMNAS por fila, centrada)."""
    fila, columna = divmod(indice, COLUMNAS)
    ancho_total = COLUMNAS * LADO_CASILLA + (COLUMNAS - 1) * SEPARACION_CASILLAS
    x0 = RECT_OPCIONES.left + (RECT_OPCIONES.width - ancho_total) // 2
    paso = LADO_CASILLA + SEPARACION_CASILLAS
    return pygame.Rect(x0 + columna * paso, RECT_OPCIONES.top + MARGEN_CUADRICULA + fila * paso,
                       LADO_CASILLA, LADO_CASILLA)


def objetivo_en(vestidor, posicion):
    """(qué, índice) bajo `posicion`: (CERRAR, None), (PESTANA, i),
    (OPCION, i), (DENTRO, None) o (FUERA, None) si cae fuera del modal."""
    if math.dist(posicion, CENTRO_CERRAR) <= RADIO_CERRAR:
        return CERRAR, None
    if not RECT_MODAL.collidepoint(posicion):
        return FUERA, None
    for indice in range(len(PESTANAS)):
        if rect_pestana(indice).collidepoint(posicion):
            return PESTANA, indice
    for indice in range(len(vestidor.opciones)):
        if rect_casilla(indice).collidepoint(posicion):
            return OPCION, indice
    return DENTRO, None


def dibujar_vestidor(pantalla, vestidor, rol, color_rol, posicion_mouse):
    """Modal completo para un jugador de rol `rol` (clave de sprite)."""
    dibujo.panel_alfa(pantalla, pantalla.get_rect(), assets.COLOR_FONDO_MODAL_ALFA, radio=0)
    dibujo.panel(pantalla, RECT_MODAL, assets.COLOR_FONDO_PANEL, COLOR_ACENTO, grosor=3, radio=16)
    objetivo, indice = objetivo_en(vestidor, posicion_mouse)
    _dibujar_cerrar(pantalla, objetivo == CERRAR)
    _dibujar_pestanas(pantalla, vestidor, indice if objetivo == PESTANA else None)
    dibujo.texto(pantalla, "VESTIDOR", (RECT_MODAL.right - 24, RECT_MODAL.top + 14), COLOR_ACENTO,
                 assets.TAMANIO_FUENTE_TITULO, negrita=True, ancla="topright")
    dibujo.texto(pantalla, "Toda la sala ve tus cambios al instante",
                 (RECT_MODAL.right - 24, RECT_MODAL.top + 42), assets.COLOR_TEXTO_SECUNDARIO,
                 assets.TAMANIO_FUENTE_MINI, ancla="topright")
    _dibujar_vista(pantalla, vestidor, rol, color_rol)
    _dibujar_opciones(pantalla, vestidor, rol, indice if objetivo == OPCION else None)
    dibujo.texto(pantalla, "Presiona [E] o [Esc] para cerrar", (RECT_MODAL.centerx, RECT_MODAL.bottom - 18),
                 assets.COLOR_TEXTO_APAGADO, assets.TAMANIO_FUENTE_PEQUENA, ancla="center")


def _dibujar_cerrar(pantalla, resaltado):
    """Botón redondo con una X, como el de Among Us."""
    pygame.draw.circle(pantalla, assets.COLOR_TEXTO_HUD, CENTRO_CERRAR, RADIO_CERRAR)
    pygame.draw.circle(pantalla, COLOR_ACENTO if resaltado else assets.COLOR_BORDE_CHIP, CENTRO_CERRAR,
                       RADIO_CERRAR, 3)
    brazo = RADIO_CERRAR // 2
    cx, cy = CENTRO_CERRAR
    for signo in (1, -1):
        pygame.draw.line(pantalla, assets.COLOR_FONDO, (cx - brazo, cy - signo * brazo),
                         (cx + brazo, cy + signo * brazo), 4)


def _dibujar_pestanas(pantalla, vestidor, resaltada):
    for indice, nombre in enumerate(PESTANAS):
        rect = rect_pestana(indice)
        activa = nombre == vestidor.pestana
        if activa:
            relleno, borde, color_texto = assets.COLOR_FONDO_PANEL_CLARO, COLOR_ACENTO, COLOR_ACENTO
        else:
            relleno, color_texto = assets.COLOR_FONDO_CHIP, assets.COLOR_TEXTO_SECUNDARIO
            borde = assets.COLOR_TEXTO_SECUNDARIO if indice == resaltada else assets.COLOR_BORDE_CHIP
        dibujo.panel(pantalla, rect, relleno, borde, grosor=2 if activa else 1, radio=8)
        dibujo.texto(pantalla, nombre, rect.center, color_texto, assets.TAMANIO_FUENTE_TITULO,
                     negrita=True, ancla="center")
        dibujo.texto(pantalla, str(indice + 1), (rect.left + 8, rect.top + 4), assets.COLOR_TEXTO_APAGADO,
                     assets.TAMANIO_FUENTE_MINI)


def _dibujar_vista(pantalla, vestidor, rol, color_rol):
    """Izquierda: el jugador en grande, su rol y lo que lleva en cada pestaña."""
    dibujo.panel(pantalla, RECT_VISTA, assets.COLOR_FONDO_VISTA_PREVIA, assets.COLOR_BORDE_CHIP, radio=12)
    dibujo.texto(pantalla, "TU PERSONAJE", (RECT_VISTA.centerx, RECT_VISTA.top + 16), COLOR_ACENTO,
                 assets.TAMANIO_FUENTE_PEQUENA, negrita=True, ancla="center")
    pies = (RECT_VISTA.centerx, RECT_VISTA.top + 285)
    sombra = pygame.Rect(0, 0, 150, 26)
    sombra.center = pies
    dibujo.panel_alfa(pantalla, sombra, assets.COLOR_SOMBRA_VESTIDOR, radio=13)
    imagen = sprites.sprite_jugador(color_rol, escala=ESCALA_VISTA, rol=rol, apariencia=vestidor.apariencia)
    pantalla.blit(imagen, imagen.get_rect(midbottom=(pies[0], pies[1] + 6)))
    dibujo.chip(pantalla, f"Rol: {nombre_rol(rol)}", (RECT_VISTA.centerx, RECT_VISTA.top + 318), color_rol,
                assets.COLOR_FONDO, color_rol, assets.TAMANIO_FUENTE_PEQUENA, ancla="center")
    y = RECT_VISTA.top + 348
    for indice, pestana in enumerate(PESTANAS):
        activa = pestana == vestidor.pestana
        valor = opciones(pestana)[vestidor.indice_elegido(pestana)]
        dibujo.texto(pantalla, pestana, (RECT_VISTA.left + 34, y + indice * 22),
                     COLOR_ACENTO if activa else assets.COLOR_TEXTO_APAGADO, assets.TAMANIO_FUENTE_PEQUENA,
                     negrita=True)
        dibujo.texto(pantalla, etiqueta_opcion(pestana, valor), (RECT_VISTA.left + 110, y + indice * 22),
                     assets.COLOR_TEXTO_HUD if activa else assets.COLOR_TEXTO_SECUNDARIO,
                     assets.TAMANIO_FUENTE_PEQUENA)


def _dibujar_opciones(pantalla, vestidor, rol, resaltada):
    """Derecha: la cuadrícula de la pestaña visible y qué es lo equipado."""
    dibujo.panel(pantalla, RECT_OPCIONES, assets.COLOR_FONDO_VISTA_PREVIA, assets.COLOR_BORDE_CHIP, radio=12)
    elegida = vestidor.indice_elegido()
    for indice, valor in enumerate(vestidor.opciones):
        _dibujar_casilla(pantalla, rect_casilla(indice), vestidor, rol, valor,
                         elegida=indice == elegida, resaltada=indice == resaltada)
    ultima = rect_casilla(len(vestidor.opciones) - 1)
    y = ultima.bottom + 24
    dibujo.texto(pantalla, texto_opcion(vestidor.pestana, vestidor.opciones[elegida], rol),
                 (RECT_OPCIONES.left + 24, y), assets.COLOR_TEXTO_HUD, assets.TAMANIO_FUENTE_TITULO, negrita=True)
    dibujo.parrafo(pantalla, AYUDA_PESTANA[vestidor.pestana], (RECT_OPCIONES.left + 24, y + 36),
                   RECT_OPCIONES.width - 48, assets.COLOR_TEXTO_SECUNDARIO, assets.TAMANIO_FUENTE_NORMAL)


def _dibujar_casilla(pantalla, rect, vestidor, rol, valor, elegida, resaltada):
    if elegida:
        relleno, borde, grosor = assets.COLOR_FONDO_PANEL_CLARO, COLOR_ACENTO, 3
    else:
        relleno, grosor = assets.COLOR_FONDO_CHIP, 1
        borde = assets.COLOR_TEXTO_SECUNDARIO if resaltada else assets.COLOR_BORDE_CHIP
    dibujo.panel(pantalla, rect, relleno, borde, grosor=grosor, radio=10)
    imagen = _imagen_opcion(vestidor, rol, valor)
    if imagen is not None:
        pantalla.blit(imagen, imagen.get_rect(center=(rect.centerx, rect.centery - 8)))
    if vestidor.pestana == COLOR and valor is not None:
        centro = (rect.right - RADIO_MUESTRA_TONO - 6, rect.top + RADIO_MUESTRA_TONO + 6)
        pygame.draw.circle(pantalla, assets.TONOS_PIEL[valor], centro, RADIO_MUESTRA_TONO)
        pygame.draw.circle(pantalla, assets.COLOR_FONDO, centro, RADIO_MUESTRA_TONO, 2)
    color_etiqueta = COLOR_ACENTO if valor is None else (
        assets.COLOR_TEXTO_HUD if elegida else assets.COLOR_TEXTO_SECUNDARIO)
    dibujo.texto(pantalla, etiqueta_opcion(vestidor.pestana, valor), (rect.centerx, rect.bottom - 13),
                 color_etiqueta, assets.TAMANIO_FUENTE_MINI, negrita=elegida or valor is None, ancla="center")


def _imagen_opcion(vestidor, rol, valor):
    """La parte que se vería con esa opción, con la piel que tendría."""
    apariencia = vestidor.apariencia
    if vestidor.pestana == COLOR:
        piel = None if valor is None else assets.TONOS_PIEL[valor]
        return sprites.sprite_parte_jugador(assets.SIMBOLOS_CABEZA, apariencia.cabeza_para(rol), piel,
                                            ESCALA_CASILLA)
    piel = None if apariencia.piel is None else assets.TONOS_PIEL[apariencia.piel]
    simbolos = assets.SIMBOLOS_CABEZA if vestidor.pestana == HAT else assets.SIMBOLOS_TRAJE
    return sprites.sprite_parte_jugador(simbolos, valor or rol, piel, ESCALA_CASILLA)
