"""Dibujo de la pantalla de selección de rol (solo presentación).

Una tarjeta por rol: tecla, sprite, nombre, habilidad y una barra
horizontal por estadística (Velocidad, Cadencia, Daño, Vida). El largo
de cada barra es la fracción de esa estadística respecto al rol que la
tiene más alta (balance.stats_normalizadas), así de un vistazo se ve
quién es rápido, quién es lento y quién aguanta.
"""

from src.core import assets
from src.core.balance import ESTADISTICAS_VISIBLES, stats_normalizadas
from src.ui import dibujo, sprites

TITULO = "Elige tu personaje"
SUBTITULO = "Civitas · 4 roles, una ciudad al borde del colapso"


def dibujar_seleccion(pantalla, clases_rol):
    """`clases_rol` es la lista ordenada de clases de rol (tecla 1 = la primera)."""
    pantalla.fill(assets.COLOR_FONDO)
    cx, cy = assets.POSICION_TITULO_SELECCION
    dibujo.texto(pantalla, TITULO, (cx, cy), assets.COLOR_TEXTO_HUD, assets.TAMANIO_FUENTE_GRANDE,
                 negrita=True, ancla="center")
    dibujo.texto(pantalla, SUBTITULO, (cx, cy + 34), assets.COLOR_TEXTO_SECUNDARIO,
                 assets.TAMANIO_FUENTE_NORMAL, ancla="center")

    normalizadas = stats_normalizadas()
    origen_x, origen_y = assets.ORIGEN_COLUMNAS_SELECCION
    fila = assets.SEPARACION_FILAS_SELECCION

    for indice, clase in enumerate(clases_rol):
        tarjeta = dibujo.panel(
            pantalla,
            (origen_x + indice * assets.ANCHO_COLUMNA_SELECCION, origen_y,
             assets.ANCHO_TARJETA_SELECCION, assets.ALTO_TARJETA_SELECCION),
            assets.COLOR_FONDO_PANEL, clase.COLOR, 2, radio=10,
        )
        x = tarjeta.left + 20
        y = tarjeta.top + 18
        dibujo.chip(pantalla, str(indice + 1), (x, y), clase.COLOR, assets.COLOR_FONDO, clase.COLOR,
                    assets.TAMANIO_FUENTE_MEDIA, alto=30, margen=11)
        imagen = sprites.sprite_jugador(clase.COLOR, escala=5)
        pantalla.blit(imagen, imagen.get_rect(midtop=(tarjeta.centerx, y + 40)))
        y += 140
        dibujo.texto(pantalla, clase.NOMBRE, (tarjeta.centerx, y), clase.COLOR, assets.TAMANIO_FUENTE_TITULO,
                     negrita=True, ancla="center")
        y += 26
        dibujo.texto(pantalla, clase.NOMBRE_HABILIDAD, (tarjeta.centerx, y), assets.COLOR_TEXTO_SECUNDARIO,
                     assets.TAMANIO_FUENTE_PEQUENA, ancla="center")
        y += 40

        for etiqueta, atributo in ESTADISTICAS_VISIBLES:
            dibujo.texto(pantalla, etiqueta, (x, y), assets.COLOR_TEXTO_HUD, assets.TAMANIO_FUENTE_PEQUENA)
            dibujo.barra(
                pantalla, (x + assets.DESPLAZAMIENTO_BARRA_X, y + 3, assets.ANCHO_MAXIMO_BARRA, assets.ALTO_BARRA),
                normalizadas[clase.rol][atributo], clase.COLOR, borde=None, radio=3,
            )
            y += fila
