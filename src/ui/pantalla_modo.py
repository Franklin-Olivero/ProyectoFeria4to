"""Dibujo de la pantalla de modo: 1 o 2 jugadores (solo presentación).

Dos tarjetas lado a lado; la resaltada es la del SelectorModo
(src/ui/seleccion.py). Abajo se muestra si hay un control conectado,
porque el J2 lo necesita, o el aviso de que falta uno.
"""

from src.core import assets
from src.ui import dibujo, sprites
from src.ui.seleccion import DOS_JUGADORES, MODOS

TITULO = "Civitas"
SUBTITULO = "¿Cuántos jugadores?"
OPCIONES = {
    1: ("1 jugador", ["Teclado y ratón"]),
    2: ("2 jugadores", ["J1: teclado y ratón", "J2: control de PS4", "Cooperativo, misma pantalla"]),
}
AVISO_SIN_CONTROL = "Conecta un control de PS4 para jugar de a dos"


def dibujar_modo(pantalla, selector, nombre_mando, aviso_activo):
    """`nombre_mando` es el nombre del control conectado o None;
    `aviso_activo` muestra en rojo que falta el control."""
    pantalla.fill(assets.COLOR_FONDO)
    cx, cy = assets.POSICION_TITULO_SELECCION
    dibujo.texto(pantalla, TITULO, (cx, cy), assets.COLOR_TEXTO_HUD, assets.TAMANIO_FUENTE_GRANDE,
                 negrita=True, ancla="center")
    dibujo.texto(pantalla, SUBTITULO, (cx, cy + 34), assets.COLOR_TEXTO_SECUNDARIO,
                 assets.TAMANIO_FUENTE_NORMAL, ancla="center")

    for modo, rect in zip(MODOS, assets.RECTS_OPCION_MODO):
        elegido = modo == selector.seleccionado
        color = assets.COLOR_TEAL if elegido else assets.COLOR_BORDE_CHIP
        tarjeta = dibujo.panel(pantalla, rect, assets.COLOR_FONDO_PANEL, color,
                               assets.GROSOR_TARJETA_RESALTADA if elegido else 1, radio=12)
        dibujo.chip(pantalla, str(modo), (tarjeta.left + 20, tarjeta.top + 18), color, assets.COLOR_FONDO,
                    color, assets.TAMANIO_FUENTE_MEDIA, alto=30, margen=11)

        # Un muñeco por jugador.
        munecos = [(assets.COLOR_CIUDADANO, "ciudadano"), (assets.COLOR_INFLUENCER, "influencer")][:modo]
        separacion = 90
        inicio = tarjeta.centerx - separacion * (len(munecos) - 1) / 2
        for i, (color_sprite, rol) in enumerate(munecos):
            imagen = sprites.sprite_jugador(color_sprite, escala=5, rol=rol)
            pantalla.blit(imagen, imagen.get_rect(midtop=(round(inicio + i * separacion), tarjeta.top + 60)))

        nombre, lineas = OPCIONES[modo]
        y = tarjeta.top + 200
        dibujo.texto(pantalla, nombre, (tarjeta.centerx, y), assets.COLOR_TEXTO_HUD if elegido
                     else assets.COLOR_TEXTO_SECUNDARIO, assets.TAMANIO_FUENTE_TITULO, negrita=True, ancla="center")
        for linea in lineas:
            y += 28
            dibujo.texto(pantalla, linea, (tarjeta.centerx, y), assets.COLOR_TEXTO_SECUNDARIO,
                         assets.TAMANIO_FUENTE_NORMAL, ancla="center")

    if aviso_activo:
        texto, color = AVISO_SIN_CONTROL, assets.COLOR_MAGENTA
    elif nombre_mando:
        texto, color = f"Control detectado: {nombre_mando}", assets.COLOR_TEAL
    else:
        texto, color = "Sin control conectado", assets.COLOR_TEXTO_SECUNDARIO
    if selector.seleccionado == DOS_JUGADORES or aviso_activo or nombre_mando:
        dibujo.texto(pantalla, texto, assets.POSICION_AVISO_MODO, color, assets.TAMANIO_FUENTE_MEDIA,
                     negrita=aviso_activo, ancla="center")
