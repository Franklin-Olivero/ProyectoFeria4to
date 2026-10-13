"""Dibujo de la pantalla de selección de rol (solo presentación).

Una columna por rol: tecla + nombre, nombre de la habilidad y una barra
horizontal por estadística (Velocidad, Cadencia, Daño, Vida). El largo
de cada barra es la fracción de esa estadística respecto al rol que la
tiene más alta (balance.stats_normalizadas), así de un vistazo se ve
quién es rápido, quién es lento y quién aguanta.
"""

import pygame

from src.core import assets
from src.core.balance import ESTADISTICAS_VISIBLES, stats_normalizadas


def dibujar_seleccion(pantalla, clases_rol, fuente_titulo, fuente):
    """`clases_rol` es la lista ordenada de clases de rol (tecla 1 = la primera)."""
    titulo = fuente_titulo.render("Elige tu personaje (1-4)", True, assets.COLOR_TEXTO_HUD)
    pantalla.blit(titulo, assets.POSICION_TITULO_SELECCION)

    normalizadas = stats_normalizadas()
    origen_x, origen_y = assets.ORIGEN_COLUMNAS_SELECCION
    fila = assets.SEPARACION_FILAS_SELECCION

    for indice, clase in enumerate(clases_rol):
        x = origen_x + indice * assets.ANCHO_COLUMNA_SELECCION
        y = origen_y

        nombre = fuente_titulo.render(f"{indice + 1}. {clase.NOMBRE}", True, clase.COLOR)
        pantalla.blit(nombre, (x, y))
        y += fila
        habilidad = fuente.render(clase.NOMBRE_HABILIDAD, True, assets.COLOR_TEXTO_SECUNDARIO)
        pantalla.blit(habilidad, (x, y))
        y += fila

        for etiqueta, atributo in ESTADISTICAS_VISIBLES:
            texto = fuente.render(etiqueta, True, assets.COLOR_TEXTO_HUD)
            pantalla.blit(texto, (x, y))
            fondo = pygame.Rect(
                x + assets.DESPLAZAMIENTO_BARRA_X, y, assets.ANCHO_MAXIMO_BARRA, assets.ALTO_BARRA
            )
            pygame.draw.rect(pantalla, assets.COLOR_FONDO_BARRA, fondo)
            relleno = fondo.copy()
            relleno.width = round(assets.ANCHO_MAXIMO_BARRA * normalizadas[clase.rol][atributo])
            pygame.draw.rect(pantalla, clase.COLOR, relleno)
            y += fila
