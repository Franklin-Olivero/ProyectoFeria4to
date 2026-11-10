"""Dibujo y ratón del vestidor del lobby online (estilo Among Us).

Modal sobre la sala, con el estilo de ahora del juego (vidrio oscuro y el
morado de Civitas, como el lobby del hotel): botón X para cerrar, las seis
pestañas COLOR / HAT / SKIN / HAIR / SHIRT / PANTS arriba, a la izquierda
el jugador en grande con lo que lleva puesto y a la derecha la cuadrícula de
opciones de la pestaña (la equipada, resaltada). Cada casilla muestra la
parte real que se pondría, armada desde las recetas de Pixelbolt
(sprites.sprite_parte_jugador): la cabeza con ese tono de piel (COLOR) o
color de pelo (HAIR), la cabeza de ese rol (HAT), su torso y piernas (SKIN)
o el traje con esa camisa (SHIRT) o ese pantalón (PANTS). Qué opciones hay
y qué se equipa lo decide Online/personalizacion.py.
"""

import math

import pygame

from src.core import assets
from src.ui import dibujo, kit, layout, sprites

from Online.personalizacion import (
    COLOR, COLUMNAS, HAIR, HAT, PANTS, PESTANAS, SHIRT, SKIN, color_de_opcion, etiqueta_opcion, nombre_rol, opciones,
    texto_opcion,
)

COLOR_ACENTO = assets.COLOR_CIVITAS  # el morado de Civitas (antes, neón cian)
COLOR_FONDO_CASILLA = (38, 22, 70)
COLOR_FONDO_CASILLA_ELEGIDA = (70, 42, 124)
COLOR_FONDO_VISTA = (30, 18, 56)
COLOR_LUZ_VISTA = (164, 110, 255, 46)  # el foco bajo el jugador

RECT_MODAL = pygame.Rect(170, 84, 940, 540)
CENTRO_CERRAR = (RECT_MODAL.left + 34, RECT_MODAL.top + 34)
RADIO_CERRAR = 20
X_PESTANAS = RECT_MODAL.left + 72
Y_PESTANAS = RECT_MODAL.top + 12
ANCHO_PESTANA = 100
ALTO_PESTANA = 44
SEPARACION_PESTANAS = 8
RECT_VISTA = pygame.Rect(RECT_MODAL.left + 20, RECT_MODAL.top + 72, 300, 420)
RECT_OPCIONES = pygame.Rect(RECT_VISTA.right + 20, RECT_VISTA.top,
                            RECT_MODAL.right - RECT_VISTA.right - 40, RECT_VISTA.height)
LADO_CASILLA = 100
SEPARACION_CASILLAS = 10
MARGEN_CUADRICULA = 20  # entre el borde del panel de opciones y la primera fila
ESCALA_VISTA = 11  # jugador de la vista previa: 176x220 px (distinta de la revelación del rol)
ESCALA_CASILLA = 5  # parte de cada casilla: 80x50 px
RADIO_MUESTRA_TONO = 8

AYUDA_PESTANA = {
    COLOR: "Tono de piel de la cara y las manos. AUTO deja el tono original de la cabeza que lleves.",
    HAT: "La parte de arriba (pelo, cara y lentes) de cualquier personaje. AUTO usa la de tu rol "
         "y cambia sola si eliges otro rol en la recepción.",
    SKIN: "El traje (camisa, pantalón y zapatos) de cualquier personaje. Tu accesorio "
          "(megáfono, micrófono...) siempre es el de tu rol.",
    HAIR: "Color del pelo de la cabeza que lleves, con sus sombras. AUTO deja el color original.",
    SHIRT: "Color de la camisa o chaqueta del traje que lleves. El cuello y la corbata no cambian.",
    PANTS: "Color del pantalón del traje que lleves. Los zapatos no cambian.",
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
    kit.panel(pantalla, RECT_MODAL, COLOR_ACENTO, alfa=246, radio=16)
    pygame.draw.rect(pantalla, COLOR_ACENTO, RECT_MODAL, 2, border_radius=16)
    objetivo, indice = objetivo_en(vestidor, posicion_mouse)
    _dibujar_cerrar(pantalla, objetivo == CERRAR)
    _dibujar_pestanas(pantalla, vestidor, indice if objetivo == PESTANA else None)
    dibujo.texto(pantalla, "VESTIDOR", (RECT_MODAL.right - 24, RECT_MODAL.top + 14), COLOR_ACENTO,
                 assets.TAMANIO_FUENTE_TITULO, negrita=True, ancla="topright")
    dibujo.texto(pantalla, "Todos ven tus cambios", (RECT_MODAL.right - 24, RECT_MODAL.top + 42),
                 assets.COLOR_TEXTO_SECUNDARIO, assets.TAMANIO_FUENTE_MINI, ancla="topright")
    _dibujar_vista(pantalla, vestidor, rol, color_rol)
    _dibujar_opciones(pantalla, vestidor, rol, indice if objetivo == OPCION else None)
    dibujo.texto(pantalla, "[E] o [Esc] cierra  ·  Tab o 1-6 cambian de pestaña",
                 (RECT_MODAL.centerx, RECT_MODAL.bottom - 18), assets.COLOR_TEXTO_APAGADO,
                 assets.TAMANIO_FUENTE_PEQUENA, ancla="center")


def _dibujar_cerrar(pantalla, resaltado):
    """Botón redondo con una X, como el de Among Us."""
    pygame.draw.circle(pantalla, COLOR_FONDO_CASILLA_ELEGIDA if resaltado else COLOR_FONDO_CASILLA, CENTRO_CERRAR,
                       RADIO_CERRAR)
    pygame.draw.circle(pantalla, COLOR_ACENTO, CENTRO_CERRAR, RADIO_CERRAR, 3 if resaltado else 2)
    brazo = RADIO_CERRAR // 2
    cx, cy = CENTRO_CERRAR
    for signo in (1, -1):
        pygame.draw.line(pantalla, assets.COLOR_TEXTO_HUD, (cx - brazo, cy - signo * brazo),
                         (cx + brazo, cy + signo * brazo), 4)


def _dibujar_pestanas(pantalla, vestidor, resaltada):
    for indice, nombre in enumerate(PESTANAS):
        rect = rect_pestana(indice)
        activa = nombre == vestidor.pestana
        if activa:
            relleno, borde, color_texto = COLOR_FONDO_CASILLA_ELEGIDA, COLOR_ACENTO, assets.COLOR_TEXTO_HUD
        else:
            relleno, color_texto = COLOR_FONDO_CASILLA, assets.COLOR_TEXTO_SECUNDARIO
            borde = COLOR_ACENTO if indice == resaltada else assets.COLOR_BORDE_VIDRIO
        dibujo.panel(pantalla, rect, relleno, borde, grosor=2 if activa else 1, radio=10)
        dibujo.texto(pantalla, nombre, (rect.centerx, rect.centery + 2), color_texto, assets.TAMANIO_FUENTE_MEDIA,
                     negrita=True, ancla="center")
        dibujo.texto(pantalla, str(indice + 1), (rect.left + 7, rect.top + 3), COLOR_ACENTO if activa else
                     assets.COLOR_TEXTO_APAGADO, assets.TAMANIO_FUENTE_MINI)


def _dibujar_vista(pantalla, vestidor, rol, color_rol):
    """Izquierda: el jugador en grande, su rol y lo que lleva en cada pestaña."""
    dibujo.panel(pantalla, RECT_VISTA, COLOR_FONDO_VISTA, assets.COLOR_BORDE_VIDRIO, radio=12)
    kit.rotulo(pantalla, "Tu personaje", (RECT_VISTA.centerx, RECT_VISTA.top + 12), COLOR_ACENTO, ancla="midtop")
    pies = (RECT_VISTA.centerx, RECT_VISTA.top + 262)
    foco = pygame.Rect(0, 0, 220, 46)
    foco.center = pies
    dibujo.panel_alfa(pantalla, foco, COLOR_LUZ_VISTA, radio=23)
    sombra = pygame.Rect(0, 0, 150, 22)
    sombra.center = pies
    dibujo.panel_alfa(pantalla, sombra, assets.COLOR_SOMBRA_VESTIDOR, radio=11)
    imagen = sprites.sprite_jugador(color_rol, escala=ESCALA_VISTA, rol=rol, apariencia=vestidor.apariencia)
    pantalla.blit(imagen, imagen.get_rect(midbottom=(pies[0], pies[1] + 6)))
    dibujo.chip(pantalla, f"Rol: {nombre_rol(rol)}", (RECT_VISTA.centerx, RECT_VISTA.top + 296), color_rol,
                assets.COLOR_FONDO, color_rol, assets.TAMANIO_FUENTE_PEQUENA, ancla="center")
    # Lo que lleva en cada pestaña, en dos columnas de tres.
    for indice, pestana in enumerate(PESTANAS):
        columna, fila = divmod(indice, 3)
        x = RECT_VISTA.left + 18 + columna * 142
        y = RECT_VISTA.top + 324 + fila * 24
        activa = pestana == vestidor.pestana
        valor = opciones(pestana)[vestidor.indice_elegido(pestana)]
        dibujo.texto(pantalla, pestana, (x, y), COLOR_ACENTO if activa else assets.COLOR_TEXTO_APAGADO,
                     assets.TAMANIO_FUENTE_MINI, negrita=True)
        muestra = color_de_opcion(pestana, valor)
        x_valor = x + 50
        if muestra is not None:
            pygame.draw.circle(pantalla, muestra, (x_valor + 5, y + 7), 5)
            x_valor += 14
        ancho = (x + 136 if columna == 0 else RECT_VISTA.right - 8) - x_valor
        layout.texto_en_ancho(pantalla, etiqueta_opcion(pestana, valor), (x_valor, y), ancho,
                              assets.COLOR_TEXTO_HUD if activa else assets.COLOR_TEXTO_SECUNDARIO,
                              assets.TAMANIO_FUENTE_MINI, minimo=8)


def _dibujar_opciones(pantalla, vestidor, rol, resaltada):
    """Derecha: la cuadrícula de la pestaña visible y qué es lo equipado."""
    dibujo.panel(pantalla, RECT_OPCIONES, COLOR_FONDO_VISTA, assets.COLOR_BORDE_VIDRIO, radio=12)
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
        dibujo.panel_alfa(pantalla, rect.inflate(8, 8), (*COLOR_ACENTO, 60), radio=14)
        relleno, borde, grosor = COLOR_FONDO_CASILLA_ELEGIDA, COLOR_ACENTO, 3
    else:
        relleno, grosor = COLOR_FONDO_CASILLA, 1
        borde = assets.COLOR_TEXTO_SECUNDARIO if resaltada else assets.COLOR_BORDE_VIDRIO
    dibujo.panel(pantalla, rect, relleno, borde, grosor=grosor, radio=10)
    imagen = _imagen_opcion(vestidor, rol, valor)
    if imagen is not None:
        pantalla.blit(imagen, imagen.get_rect(center=(rect.centerx, rect.centery - 8)))
    muestra = color_de_opcion(vestidor.pestana, valor)
    if muestra is not None:
        centro = (rect.right - RADIO_MUESTRA_TONO - 6, rect.top + RADIO_MUESTRA_TONO + 6)
        pygame.draw.circle(pantalla, muestra, centro, RADIO_MUESTRA_TONO)
        pygame.draw.circle(pantalla, assets.COLOR_FONDO, centro, RADIO_MUESTRA_TONO, 2)
    color_etiqueta = COLOR_ACENTO if valor is None else (
        assets.COLOR_TEXTO_HUD if elegida else assets.COLOR_TEXTO_SECUNDARIO)
    dibujo.texto(pantalla, etiqueta_opcion(vestidor.pestana, valor), (rect.centerx, rect.bottom - 13),
                 color_etiqueta, assets.TAMANIO_FUENTE_MINI, negrita=elegida or valor is None, ancla="center")


def _imagen_opcion(vestidor, rol, valor):
    """La parte que se vería con esa opción, con la piel y los colores que tendría."""
    apariencia = vestidor.apariencia
    pestana = vestidor.pestana
    piel = None if apariencia.piel is None else assets.TONOS_PIEL[apariencia.piel]
    if pestana == COLOR:
        piel = None if valor is None else assets.TONOS_PIEL[valor]
        return sprites.sprite_parte_jugador(assets.SIMBOLOS_CABEZA, apariencia.cabeza_para(rol), piel,
                                            ESCALA_CASILLA, apariencia)
    if pestana == HAIR:
        return sprites.sprite_parte_jugador(assets.SIMBOLOS_CABEZA, apariencia.cabeza_para(rol), piel,
                                            ESCALA_CASILLA, apariencia.con("pelo", valor))
    if pestana in (SHIRT, PANTS):
        campo = "ropa" if pestana == SHIRT else "pantalon"
        return sprites.sprite_parte_jugador(assets.SIMBOLOS_TRAJE, apariencia.traje_para(rol), piel,
                                            ESCALA_CASILLA, apariencia.con(campo, valor))
    simbolos = assets.SIMBOLOS_CABEZA if pestana == HAT else assets.SIMBOLOS_TRAJE
    return sprites.sprite_parte_jugador(simbolos, valor or rol, piel, ESCALA_CASILLA, apariencia)
