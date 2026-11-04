"""Tarjetas de Civitas del modo historia (solo presentación).

    - dibujar_tarjeta_publicacion: la publicación a decidir (usuario,
      texto, imagen simulada, sello según el estado de evidencia y
      contadores). La usa la terminal de decisión.
    - dibujar_tarjeta_evidencia: una prueba encontrada (título, fuente y
      fragmento), con el chip "PISTA NOVA_404" si la trae. Aparece unos
      segundos en combate al limpiar un cuarto y en la pantalla de
      resultado.
    - dibujar_lista_evidencias: las pruebas reveladas de la zona en
      formato compacto (panel lateral de la terminal).
No modifican ningún estado.
"""

import pygame

from src.core import assets
from src.story.escenarios import NOMBRES_ESTADO_EVIDENCIA, SIN_PRUEBAS
from src.ui import dibujo, layout, sprites

TEXTO_PISTA = "PISTA NOVA_404"
TEXTO_EVIDENCIA = "Evidencia encontrada"


def dibujar_tarjeta_publicacion(pantalla, rect, post, estado_evidencia=None, chip="Publicación en Civitas"):
    rect = dibujo.panel(pantalla, rect, assets.COLOR_FONDO_TARJETA, None, 0, radio=4)
    x = rect.left + 20
    y = rect.top + 18
    dibujo.chip(pantalla, chip, (x, y), assets.COLOR_TEXTO_HUD, assets.COLOR_MAGENTA, assets.COLOR_MAGENTA, alto=24)
    y += 44
    avatar = sprites.sprite(sprites.AVATAR, sprites.PALETA_AVATAR, escala=3)
    pantalla.blit(avatar, (x, y))
    dibujo.texto(pantalla, post["usuario"], (x + 40, y), assets.COLOR_TEXTO_TARJETA,
                 assets.TAMANIO_FUENTE_NORMAL, negrita=True)
    dibujo.texto(pantalla, post.get("hace", ""), (x + 40, y + 20), assets.COLOR_TEXTO_TARJETA_SUAVE,
                 assets.TAMANIO_FUENTE_PEQUENA)
    y += 52
    y = dibujo.parrafo(pantalla, post["texto"], (x, y), rect.width - 40, assets.COLOR_TEXTO_TARJETA,
                       assets.TAMANIO_FUENTE_NORMAL, interlineado=6)
    y += 12
    imagen = pygame.Rect(x, y, rect.width - 40, 96)
    pygame.draw.rect(pantalla, assets.COLOR_IMAGEN_TARJETA, imagen, border_radius=3)
    for i, (ancho, alto) in enumerate(((120, 6), (80, 10), (170, 6), (60, 6))):
        linea = pygame.Rect(imagen.left + (8 if i % 2 == 0 else 24), imagen.top + 12 + i * 20, ancho, alto)
        pygame.draw.rect(pantalla, assets.COLOR_MAGENTA, linea)
    # Pie de la imagen sobre una banda oscura, para que no se mezcle con las barras.
    pie = pygame.Rect(imagen.left, imagen.bottom - 24, imagen.width, 24)
    pygame.draw.rect(pantalla, assets.COLOR_FONDO, pie, border_bottom_left_radius=3, border_bottom_right_radius=3)
    layout.texto_en_ancho(pantalla, post.get("imagen", "[imagen]"), pie.center, imagen.width - 12,
                          assets.COLOR_TEXTO_HUD, assets.TAMANIO_FUENTE_PEQUENA, ancla="center")
    y = imagen.bottom + 16
    sello = dibujo.chip(pantalla, post.get("etiqueta", ""), (x, y), assets.COLOR_MAGENTA, (252, 232, 238),
                        assets.COLOR_MAGENTA, alto=24)
    if estado_evidencia is not None:
        color = assets.COLOR_SELLO_EVIDENCIA.get(estado_evidencia, assets.COLOR_TEXTO_SECUNDARIO)
        dibujo.chip(pantalla, NOMBRES_ESTADO_EVIDENCIA.get(estado_evidencia, estado_evidencia),
                    (sello.right + 8, y), color, assets.COLOR_FONDO_TARJETA, color, alto=24)
    y += 40
    dibujo.texto(pantalla, post.get("compartidos", ""), (x, y), assets.COLOR_TEXTO_TARJETA_SUAVE,
                 assets.TAMANIO_FUENTE_PEQUENA)
    dibujo.texto(pantalla, post.get("comentarios", ""), (x, y + 18), assets.COLOR_TEXTO_TARJETA_SUAVE,
                 assets.TAMANIO_FUENTE_PEQUENA)
    return rect


def dibujar_tarjeta_evidencia(pantalla, rect, evidencia, indice=None, total=None, titulo=TEXTO_EVIDENCIA):
    rect = dibujo.panel(pantalla, rect, assets.COLOR_FONDO_EVIDENCIA, assets.COLOR_BORDE_EVIDENCIA, 2, radio=6)
    x = rect.left + 14
    encabezado = titulo if indice is None else f"{titulo} {indice}/{total}"
    dibujo.texto(pantalla, encabezado, (x, rect.top + 8), assets.COLOR_FUENTE_EVIDENCIA, assets.TAMANIO_FUENTE_PEQUENA)
    if evidencia.get("pista"):
        dibujo.chip(pantalla, TEXTO_PISTA, (rect.right - 12, rect.top + 8), assets.COLOR_TEXTO_HUD,
                    assets.COLOR_PISTA, assets.COLOR_PISTA, alto=20, ancla="topright")
    dibujo.texto(pantalla, evidencia["titulo"], (x, rect.top + 26), assets.COLOR_TITULO_EVIDENCIA,
                 assets.TAMANIO_FUENTE_NORMAL, negrita=True)
    dibujo.texto(pantalla, f"Fuente: {evidencia['fuente']}", (x, rect.top + 46), assets.COLOR_FUENTE_EVIDENCIA,
                 assets.TAMANIO_FUENTE_PEQUENA)
    layout.parrafo_en_caja(pantalla, f"“{evidencia['fragmento']}”", (x, rect.top + 64, rect.width - 28, rect.height - 70),
                           assets.COLOR_TITULO_EVIDENCIA, assets.TAMANIO_FUENTE_PEQUENA, interlineado=3)
    return rect


def dibujar_lista_evidencias(pantalla, posicion, evidencias, total, ancho):
    """Lista compacta "Pruebas reunidas 2/3" con una línea por prueba;
    las no reveladas se muestran como "???". Retorna la y final."""
    x, y = posicion
    reveladas = len(evidencias)
    estado = "sin pruebas" if reveladas == 0 else f"{reveladas}/{total}"
    dibujo.texto(pantalla, f"Pruebas reunidas: {estado}", (x, y), assets.COLOR_TEXTO_SECUNDARIO,
                 assets.TAMANIO_FUENTE_PEQUENA, negrita=True)
    y += 20
    for i in range(total):
        if i < reveladas:
            evidencia = evidencias[i]
            color = assets.COLOR_PISTA if evidencia.get("pista") else assets.COLOR_TEXTO_HUD
            texto = f"• {evidencia['titulo']}"
        else:
            color, texto = assets.COLOR_TEXTO_APAGADO, "• ???"
        lineas = dibujo.ajustar_texto(texto, assets.TAMANIO_FUENTE_PEQUENA, ancho)
        dibujo.texto(pantalla, lineas[0], (x, y), color, assets.TAMANIO_FUENTE_PEQUENA)
        y += 18
    return y


def estado_sin_pruebas():
    return SIN_PRUEBAS
