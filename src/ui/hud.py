"""HUD superior y barra de controles inferior (solo presentación).

HUD superior: etiqueta del jugador, corazones de vida, carga de la
habilidad (F), contador de enemigos, título/subtítulo del lugar y la
barra de colapso electoral. Barra inferior: chips con las teclas de la
escena actual. No modifican ningún estado del juego.
"""

import math

import pygame

from src.core import assets
from src.ui import dibujo, sprites

CONTROLES_COMBATE = [
    ("WASD", "mover"),
    ("Ratón", "apuntar"),
    ("Clic", "disparar"),
    ("F", "habilidad"),
    ("M", "minimapa"),
    ("Tab", "ver árbol de comportamiento"),
]
CONTROLES_JEFE = [
    ("WASD", "mover"),
    ("Ratón", "apuntar"),
    ("Clic", "disparar"),
    ("F", "habilidad"),
    ("Tab", "ver árbol de comportamiento"),
]
CONTROLES_TERMINAL = [("← →", "elegir opción"), ("Enter", "confirmar")]
CONTROLES_MAPA = [("← →", "elegir zona"), ("Enter", "viajar")]
CONTROLES_FINAL = [("Enter", "continuar"), ("Esc", "salir")]
CONTROLES_SELECCION = [("1-4", "elegir rol")]


def dibujar_hud_superior(pantalla, jugador, cantidad_enemigos, titulo, subtitulo, colapso,
                         etiqueta_jugador="J1"):
    """Franja superior completa: jugador, vida, habilidad, enemigos,
    título y barra de colapso. `jugador` puede ser None (mapa)."""
    franja = pygame.Rect(0, 0, pantalla.get_width(), assets.ALTO_HUD)
    pygame.draw.rect(pantalla, assets.COLOR_FONDO, franja)
    pygame.draw.line(pantalla, assets.COLOR_LINEA_HUD, (0, franja.bottom), (franja.right, franja.bottom), 2)

    dibujo.texto(pantalla, etiqueta_jugador, assets.POSICION_JUGADOR_HUD, assets.COLOR_TEAL,
                 assets.TAMANIO_FUENTE_TITULO, negrita=True, ancla="center")
    if jugador is not None:
        dibujar_corazones(pantalla, jugador.vida, jugador.vida_maxima)
        dibujar_habilidad(pantalla, jugador)

    if cantidad_enemigos is not None:
        x, y = assets.POSICION_ENEMIGOS_HUD
        dibujo.texto(pantalla, "Enemigos", (x, y), assets.COLOR_TEXTO_SECUNDARIO,
                     assets.TAMANIO_FUENTE_PEQUENA)
        dibujo.texto(pantalla, str(cantidad_enemigos), (x, y + 16), assets.COLOR_MAGENTA,
                     assets.TAMANIO_FUENTE_TITULO, negrita=True)

    if titulo:
        dibujo.texto(pantalla, titulo, assets.POSICION_TITULO_HUD, assets.COLOR_TEXTO_HUD,
                     assets.TAMANIO_FUENTE_MEDIA, negrita=True, ancla="center")
    if subtitulo:
        dibujo.texto(pantalla, subtitulo, assets.POSICION_SUBTITULO_HUD, assets.COLOR_TEXTO_SECUNDARIO,
                     assets.TAMANIO_FUENTE_PEQUENA, ancla="center")

    dibujar_barra_colapso(pantalla, colapso)


def dibujar_corazones(pantalla, vida, vida_maxima):
    """Un corazón por punto de vida máxima; lleno, medio o vacío."""
    x, y = assets.POSICION_CORAZONES
    lleno = sprites.sprite(sprites.CORAZON, sprites.PALETA_CORAZON_LLENO)
    vacio = sprites.sprite(sprites.CORAZON, sprites.PALETA_CORAZON_VACIO)
    for i in range(math.ceil(vida_maxima)):
        pantalla.blit(vacio, (x + i * assets.SEPARACION_CORAZONES, y))
        restante = vida - i
        if restante >= 1:
            pantalla.blit(lleno, (x + i * assets.SEPARACION_CORAZONES, y))
        elif restante > 0:
            # Medio corazón: solo la mitad izquierda del sprite lleno.
            mitad = pygame.Rect(0, 0, lleno.get_width() // 2, lleno.get_height())
            pantalla.blit(lleno, (x + i * assets.SEPARACION_CORAZONES, y), mitad)


def dibujar_habilidad(pantalla, jugador):
    x, y = assets.POSICION_HABILIDAD_HUD
    fraccion = jugador.carga_habilidad / jugador.carga_maxima if jugador.carga_maxima else 0
    lista = jugador.puede_usar_habilidad()
    color = assets.COLOR_TEAL if lista else assets.COLOR_MORADO
    dibujo.texto(pantalla, "F", (x, y - 3), color, assets.TAMANIO_FUENTE_PEQUENA, negrita=True)
    dibujo.barra(pantalla, (x + 16, y, assets.ANCHO_BARRA_HABILIDAD, assets.ALTO_BARRA_HABILIDAD),
                 fraccion, color, borde=None, radio=2)
    etiqueta = "LISTA" if lista else f"{jugador.carga_habilidad:g}/{jugador.carga_maxima}"
    dibujo.texto(pantalla, etiqueta, (x + 16 + assets.ANCHO_BARRA_HABILIDAD + 8, y - 4),
                 assets.COLOR_TEXTO_SECUNDARIO, assets.TAMANIO_FUENTE_PEQUENA)


def dibujar_barra_colapso(pantalla, colapso, rect=assets.RECT_BARRA_COLAPSO,
                          posicion_etiqueta=assets.POSICION_ETIQUETA_COLAPSO,
                          posicion_valor=assets.POSICION_VALOR_COLAPSO):
    dibujo.texto(pantalla, "Barra de colapso electoral", posicion_etiqueta,
                 assets.COLOR_TEXTO_SECUNDARIO, assets.TAMANIO_FUENTE_PEQUENA)
    dibujo.barra(pantalla, rect, colapso.valor / 100.0)
    dibujo.texto(pantalla, f"{colapso.valor:.1f}%", posicion_valor, assets.COLOR_AMARILLO,
                 assets.TAMANIO_FUENTE_NORMAL, negrita=True, ancla="midleft")


def dibujar_barra_controles(pantalla, controles):
    """Franja inferior con un chip de tecla + descripción por control."""
    alto = assets.ALTO_BARRA_CONTROLES
    franja = pygame.Rect(0, pantalla.get_height() - alto, pantalla.get_width(), alto)
    pygame.draw.rect(pantalla, assets.COLOR_FONDO, franja)
    pygame.draw.line(pantalla, assets.COLOR_LINEA_HUD, (0, franja.top), (franja.right, franja.top), 2)

    # Se mide todo primero para centrar la fila completa.
    from src.ui.fuentes import fuente  # import local: evita ciclo en tests sin fuentes

    f_chip = fuente(assets.TAMANIO_FUENTE_PEQUENA, True)
    f_desc = fuente(assets.TAMANIO_FUENTE_NORMAL)
    anchos = []
    for tecla, descripcion in controles:
        anchos.append(f_chip.size(tecla)[0] + assets.MARGEN_CHIP * 2 + 8 + f_desc.size(descripcion)[0])
    total = sum(anchos) + assets.SEPARACION_CONTROLES * (len(controles) - 1)
    x = (pantalla.get_width() - total) // 2
    y = franja.centery
    for (tecla, descripcion), ancho in zip(controles, anchos):
        rect = dibujo.chip(pantalla, tecla, (x, y), ancla="midleft")
        dibujo.texto(pantalla, descripcion, (rect.right + 8, y), assets.COLOR_TEXTO_SECUNDARIO,
                     assets.TAMANIO_FUENTE_NORMAL, ancla="midleft")
        x += ancho + assets.SEPARACION_CONTROLES
