"""Pantalla de elecciones y epílogo (solo presentación).

Tras derrotar al Servidor Central: barras de apoyo de los cuatro
candidatos ficticios, el panel de estado de Ciudad Nova (reutiliza
indicadores_render), el título y el texto del final alcanzado y la
nota de que es una simulación ficticia. Lee resumen_final(campania)
(src/story/eleccion.py); no modifica nada. Enter vuelve a la ciudad,
Esc sale (lo atiende Main.py en la escena VICTORIA).
"""

from src.core import assets
from src.story.eleccion import FINAL_ARQUITECTO, FINAL_RENACE
from src.ui import dibujo, indicadores_render, sprites

TITULO = "Elecciones de Ciudad Nova"
COLORES_FINAL = {
    FINAL_RENACE: assets.COLOR_FINAL_RENACE,
    FINAL_ARQUITECTO: assets.COLOR_FINAL_ARQUITECTO,
}


def dibujar_elecciones(pantalla, resumen):
    pantalla.fill(assets.COLOR_FONDO)
    fondo = sprites.fondo_historia(assets.FONDO_ELECCIONES, pantalla.get_size())
    if fondo is not None:
        fondo = fondo.copy()
        fondo.set_alpha(assets.ALFA_FONDO_ELECCIONES)
        pantalla.blit(fondo, (0, 0))
    dibujo.texto(pantalla, TITULO, (60, 36), assets.COLOR_TEXTO_HUD, assets.TAMANIO_FUENTE_GRANDE, negrita=True)
    dibujo.texto(pantalla, resumen["nota"], (60, 82), assets.COLOR_TEXTO_APAGADO, assets.TAMANIO_FUENTE_PEQUENA)

    panel = dibujo.panel(pantalla, assets.RECT_PANEL_CANDIDATOS, assets.COLOR_FONDO_PANEL, assets.COLOR_BORDE_PANEL, 1, radio=8)
    x, y = panel.left + 24, panel.top + 16
    dibujo.texto(pantalla, "Apoyo simulado (según los indicadores y tu reputación)", (x, y),
                 assets.COLOR_TEXTO_SECUNDARIO, assets.TAMANIO_FUENTE_NORMAL, negrita=True)
    y += 34
    ancho = panel.width - 48
    maximo = max(p for _, p in resumen["apoyos"]) or 1
    for indice, (candidato, porcentaje) in enumerate(resumen["apoyos"]):
        color = assets.COLORES_CANDIDATOS[indice % len(assets.COLORES_CANDIDATOS)]
        dibujo.texto(pantalla, f"{candidato['nombre']}  ·  {candidato['lema']}", (x, y), assets.COLOR_TEXTO_HUD,
                     assets.TAMANIO_FUENTE_NORMAL, negrita=indice == 0)
        dibujo.texto(pantalla, f"{porcentaje:.1f} %", (x + ancho, y), color, assets.TAMANIO_FUENTE_MEDIA,
                     negrita=True, ancla="topright")
        dibujo.barra(pantalla, (x, y + 26, ancho, assets.ALTO_BARRA_CANDIDATO), porcentaje / maximo, color,
                     assets.COLOR_FONDO_INDICADOR, None)
        y += assets.SEPARACION_CANDIDATOS

    color_final = COLORES_FINAL.get(resumen["clave"], assets.COLOR_FINAL_DIVIDIDA)
    epilogo = dibujo.panel(pantalla, assets.RECT_PANEL_EPILOGO, assets.COLOR_FONDO_PANEL, color_final, 2, radio=8)
    dibujo.texto(pantalla, resumen["titulo"], (epilogo.left + 20, epilogo.top + 12), color_final,
                 assets.TAMANIO_FUENTE_TITULO, negrita=True)
    dibujo.parrafo(pantalla, resumen["texto"], (epilogo.left + 20, epilogo.top + 44), epilogo.width - 40,
                   assets.COLOR_TEXTO_HUD, assets.TAMANIO_FUENTE_PEQUENA, interlineado=3)

    indicadores_render.dibujar_panel_estado(pantalla, resumen["campania"], assets.RECT_PANEL_ESTADO_FINAL,
                                            mostrar_cerrar=False)
    chip = dibujo.chip(pantalla, "Enter", (520, 690), ancla="midright")
    dibujo.texto(pantalla, "volver a Ciudad Nova", (chip.right + 8, chip.centery), assets.COLOR_TEXTO_SECUNDARIO, ancla="midleft")
    chip = dibujo.chip(pantalla, "Esc", (760, 690), ancla="midright")
    dibujo.texto(pantalla, "salir", (chip.right + 8, chip.centery), assets.COLOR_TEXTO_SECUNDARIO, ancla="midleft")
