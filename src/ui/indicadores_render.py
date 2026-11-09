"""Panel de estado de Ciudad Nova y deltas de indicadores (solo presentación).

    - dibujar_panel_estado: los 7 indicadores como barras (teal los
      buenos, magenta los malos), reputación y puntos del jugador,
      pistas de NOVA_404 reunidas y zonas purificadas. Se abre con la
      tecla I en la ciudad y lo reutiliza la pantalla final.
    - dibujar_deltas: lista "Confianza +8 / Desinformación −10" de la
      última consecuencia (pantalla de resultado).
Lee Campania (src/story/campania.py); no la modifica.
"""

import pygame

from src.core import assets
from src.story.estado_ciudad import NOMBRES_INDICADORES
from src.ui import dibujo, layout

TITULO_PANEL = "Estado de Ciudad Nova"
TEXTO_CERRAR = "I: cerrar"


def dibujar_panel_estado(pantalla, campania, rect=assets.RECT_PANEL_ESTADO, mostrar_cerrar=True, transcurrido=1.0):
    rect = layout.entrada(rect, transcurrido, desde="derecha")
    dibujo.panel_alfa(pantalla, rect, assets.COLOR_FONDO_PANEL_ESTADO, radio=10)
    dibujo.panel(pantalla, rect, None, assets.COLOR_BORDE_PANEL, 1, radio=10)
    x = rect.left + 24
    y = rect.top + 18
    dibujo.texto(pantalla, TITULO_PANEL, (x, y), assets.COLOR_TEXTO_HUD, assets.TAMANIO_FUENTE_TITULO, negrita=True)
    if mostrar_cerrar:
        dibujo.chip(pantalla, TEXTO_CERRAR, (rect.right - 20, y + 2), ancla="topright")
    y += 40
    resumen = campania.resumen()
    dibujo.texto(pantalla, f"Salud general: {resumen['salud']}/100", (x, y), assets.COLOR_TEXTO_SECUNDARIO,
                 assets.TAMANIO_FUENTE_NORMAL)
    y += 30
    ancho_barra = rect.width - 48
    for nombre, valor, es_bueno in campania.estado.filas():
        color = assets.COLOR_INDICADOR_BUENO if es_bueno else assets.COLOR_INDICADOR_MALO
        dibujo.texto(pantalla, nombre, (x, y), assets.COLOR_TEXTO_HUD, assets.TAMANIO_FUENTE_NORMAL)
        dibujo.texto(pantalla, str(valor), (x + ancho_barra, y), color, assets.TAMANIO_FUENTE_NORMAL,
                     negrita=True, ancla="topright")
        dibujo.barra(pantalla, (x, y + 22, ancho_barra, assets.ALTO_BARRA_INDICADOR), valor / 100.0, color,
                     assets.COLOR_FONDO_INDICADOR, None)
        y += assets.SEPARACION_INDICADORES
    y += 6
    pygame.draw.line(pantalla, assets.COLOR_BORDE_PANEL, (x, y), (rect.right - 24, y))
    y += 14
    dibujo.texto(pantalla, f"Reputación: {resumen['reputacion']:+d} · {resumen['nivel_reputacion']}", (x, y),
                 assets.color_reputacion(resumen["reputacion"]), assets.TAMANIO_FUENTE_NORMAL, negrita=True)
    dibujo.texto(pantalla, f"Puntos: {resumen['puntos']}", (rect.right - 24, y), assets.COLOR_TEXTO_HUD,
                 assets.TAMANIO_FUENTE_NORMAL, ancla="topright")
    y += 26
    dibujo.texto(pantalla, f"Pistas NOVA_404: {resumen['pistas']}/{resumen['total_pistas']}", (x, y),
                 assets.COLOR_PISTA if resumen["pistas"] else assets.COLOR_TEXTO_SECUNDARIO, assets.TAMANIO_FUENTE_NORMAL)
    y += 26
    purificadas = ", ".join(resumen["purificadas"]) or "ninguna todavía"
    for linea in dibujo.ajustar_texto(f"Zonas purificadas: {purificadas}", assets.TAMANIO_FUENTE_NORMAL, ancho_barra):
        dibujo.texto(pantalla, linea, (x, y), assets.COLOR_TEXTO_SECUNDARIO, assets.TAMANIO_FUENTE_NORMAL)
        y += 20
    return rect


def dibujar_deltas(pantalla, rect, deltas, titulo="Así cambió Ciudad Nova"):
    """Panel con un renglón por indicador que cambió (orden del
    diccionario). Un indicador sin cambio no se lista."""
    rect = dibujo.panel(pantalla, rect, assets.COLOR_FONDO_PANEL, assets.COLOR_BORDE_PANEL, 1, radio=8)
    x = rect.left + 18
    y = rect.top + 14
    dibujo.texto(pantalla, titulo, (x, y), assets.COLOR_TEXTO_SECUNDARIO, assets.TAMANIO_FUENTE_NORMAL, negrita=True)
    y += 28
    cambios = [(n, d) for n, d in deltas.items() if d]
    if not cambios:
        dibujo.texto(pantalla, "Sin cambios en los indicadores.", (x, y), assets.COLOR_TEXTO_APAGADO,
                     assets.TAMANIO_FUENTE_NORMAL)
        return rect
    for nombre, delta in cambios[:7]:
        bueno = nombre not in ("desinformacion", "conflictos")
        mejora = (delta > 0) == bueno
        color = assets.COLOR_DELTA_POSITIVO if mejora else assets.COLOR_DELTA_NEGATIVO
        dibujo.texto(pantalla, NOMBRES_INDICADORES[nombre], (x, y), assets.COLOR_TEXTO_HUD, assets.TAMANIO_FUENTE_NORMAL)
        signo = "+" if delta > 0 else "−"
        dibujo.chip(pantalla, f"{signo}{abs(delta)}", (rect.right - 18, y - 4), color, assets.COLOR_FONDO_PANEL, color,
                    ancla="topright")
        y += 24
    return rect
