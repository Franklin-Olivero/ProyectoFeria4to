"""HUD de la partida: un coordinador y una función por bloque (solo presentación).

Qué bloques se ven lo decide src/ui/hud_visibilidad.py (puro); aquí solo
se dibujan, todos con el mismo estilo: paneles chicos semitransparentes
en las esquinas (assets.COLOR_PANEL_HUD con ALFA_PANEL_HUD), el mismo
margen (MARGEN_HUD) y la misma fuente pequeña. El centro de la acción
queda libre.

    dibujar_hud(pantalla, bloques, ctx) -> dibuja los bloques pedidos y
        devuelve el rect de la línea de misión (para el mouse) o None.

`ctx` es un ContextoHud con los datos de este frame.
"""

from dataclasses import dataclass, field

import pygame

from src.core import assets
from src.ui import dibujo, hud, hud_visibilidad as v, mision_render, reputacion_render
from src.ui.fuentes import fuente
from src.ui.mapa_render import dibujar_minimapa


@dataclass
class ContextoHud:
    jugador: object = None
    etiqueta_jugador: str = "J1"
    colapso: object = None
    enemigos: int = 0
    cuartos: tuple = None  # (limpios, total) en una mazmorra normal
    mazmorra: object = None  # Mazmorra (grafo) para el minimapa
    arena: object = None  # ArenaJefe: barra, fase y tiempo
    titulo: str = ""
    subtitulo: str = ""
    destino: str = ""
    calles_bloqueadas: int = 0
    mision: object = None
    transcurrido_mision: float = 1.0
    titulares: list = field(default_factory=list)
    tiempo: float = 0.0
    reputacion: int = None
    controles: list = field(default_factory=list)
    aviso: tuple = None  # (texto, color, centro)


def dibujar_hud(pantalla, bloques, ctx):
    rect_mision = None
    if v.CINTILLO in bloques:
        bloque_cintillo(pantalla, ctx.titulares, ctx.tiempo)
    if v.VIDA in bloques and ctx.jugador is not None:
        bloque_vida_habilidad(pantalla, ctx.jugador, ctx.etiqueta_jugador, v.HABILIDAD in bloques)
    if v.COLAPSO in bloques and ctx.colapso is not None:
        bloque_colapso(pantalla, ctx.colapso)
    if v.CONTADOR in bloques:
        bloque_contador(pantalla, ctx.enemigos, ctx.cuartos)
    if v.JEFE in bloques and ctx.arena is not None:
        bloque_jefe(pantalla, ctx.arena)
    if v.TITULO in bloques and ctx.titulo:
        debajo = v.CONTADOR in bloques or v.JEFE in bloques
        bloque_titulo(pantalla, ctx.titulo, ctx.subtitulo, debajo)
    if v.DESTINO in bloques and ctx.destino:
        bloque_destino(pantalla, ctx.destino, ctx.calles_bloqueadas)
    if v.MINIMAPA in bloques and ctx.mazmorra is not None:
        bloque_minimapa(pantalla, ctx.mazmorra)
    if v.REPUTACION in bloques and ctx.reputacion is not None:
        reputacion_render.dibujar_chip_reputacion(pantalla, ctx.reputacion)
    if ctx.mision is not None:
        if v.MISION in bloques:
            panel = bloque_mision(pantalla, ctx.mision, ctx.transcurrido_mision, compacto=v.MISION_LINEA not in bloques)
            if v.MISION_LINEA in bloques and panel is not None:
                # Abierto con el mouse: la zona sigue siendo la de la línea más el
                # panel; si no, al abrirse dejaba de haber zona, se cerraba al
                # cuadro siguiente y volvía a abrirse (titilaba).
                rect_mision = pygame.Rect(assets.POSICION_LINEA_MISION,
                                          (assets.ANCHO_MAXIMO_LINEA_MISION, assets.ALTO_LINEA_MISION)).union(panel)
        elif v.MISION_LINEA in bloques:
            rect_mision = bloque_mision_linea(pantalla, ctx.mision)
    if v.AVISO in bloques and ctx.aviso is not None:
        bloque_aviso(pantalla, *ctx.aviso)
    if v.CONTROLES in bloques and ctx.controles:
        hud.dibujar_barra_controles(pantalla, ctx.controles)
    return rect_mision


# ----------------------------------------------------------------------
# Bloques
# ----------------------------------------------------------------------

def _panel(pantalla, rect):
    dibujo.panel_alfa(pantalla, rect, (*assets.COLOR_PANEL_HUD, assets.ALFA_PANEL_HUD))


def bloque_vida_habilidad(pantalla, jugador, etiqueta, con_habilidad=True):
    """Arriba a la izquierda: J1, corazones y la carga de la habilidad."""
    _panel(pantalla, assets.RECT_PANEL_VIDA_HUD)
    if etiqueta:
        dibujo.texto(pantalla, etiqueta, assets.POSICION_J1_HUD, assets.COLOR_TEAL, assets.TAMANIO_FUENTE_MEDIA,
                     negrita=True, ancla="center")
    hud.dibujar_corazones(pantalla, jugador.vida, jugador.vida_maxima, assets.POSICION_CORAZONES_HUD)
    if con_habilidad:
        hud.dibujar_habilidad(pantalla, jugador, assets.POSICION_HABILIDAD_HUD_COMPACTA, assets.ANCHO_BARRA_HABILIDAD_HUD)


def bloque_colapso(pantalla, colapso):
    """Arriba a la derecha: barra de colapso electoral y su porcentaje."""
    rect = pygame.Rect(assets.RECT_PANEL_COLAPSO_HUD)
    _panel(pantalla, rect)
    x = rect.left + assets.MARGEN_HUD
    dibujo.texto(pantalla, "Colapso", (x, rect.top + 6), assets.COLOR_TEXTO_SECUNDARIO, assets.TAMANIO_FUENTE_PEQUENA)
    dibujo.barra(pantalla, (x, rect.top + 28, assets.ANCHO_BARRA_COLAPSO_HUD, 10), colapso.valor / 100.0)
    dibujo.texto(pantalla, f"{colapso.valor:.1f}%", (rect.right - assets.MARGEN_HUD, rect.top + 33), assets.COLOR_AMARILLO,
                 assets.TAMANIO_FUENTE_NORMAL, negrita=True, ancla="midright")


def bloque_contador(pantalla, enemigos, cuartos):
    """Arriba al centro: enemigos vivos y cuartos limpios, en un chip."""
    texto = f"Enemigos {enemigos}"
    if cuartos is not None:
        texto += f"  ·  Cuartos {cuartos[0]}/{cuartos[1]}"
    color = assets.COLOR_MAGENTA if enemigos else assets.COLOR_TEAL
    dibujo.chip(pantalla, texto, assets.POSICION_CONTADOR_HUD, assets.COLOR_TEXTO_HUD, assets.COLOR_PANEL_HUD, color,
                assets.TAMANIO_FUENTE_PEQUENA, ancla="midtop", alto=26, margen=12)


def bloque_jefe(pantalla, arena):
    """Arriba al centro: nombre del jefe, vida con marcas de fase y tiempo."""
    arena.dibujar_hud(pantalla)


def bloque_titulo(pantalla, titulo, subtitulo, debajo):
    """Lugar (y subtítulo), solo con HUD detallado; bajo el contador si lo hay."""
    x, y = assets.POSICION_TITULO_HUD_COMPACTO if debajo else (640, 14)
    dibujo.texto(pantalla, titulo, (x, y), assets.COLOR_TEXTO_HUD, assets.TAMANIO_FUENTE_NORMAL, negrita=True,
                 ancla="midtop")
    if subtitulo:
        dibujo.texto(pantalla, subtitulo, (x, y + 20), assets.COLOR_TEXTO_SECUNDARIO, assets.TAMANIO_FUENTE_PEQUENA,
                     ancla="midtop")


def bloque_destino(pantalla, destino, calles_bloqueadas):
    texto = f"Destino: {destino}  ·  Calles bloqueadas: {calles_bloqueadas}"
    dibujo.chip(pantalla, texto, (640, 40), assets.COLOR_TEXTO_SECUNDARIO, assets.COLOR_PANEL_HUD,
                assets.COLOR_BORDE_PANEL, assets.TAMANIO_FUENTE_PEQUENA, ancla="midtop", alto=24, margen=10)


def bloque_minimapa(pantalla, mazmorra):
    dibujar_minimapa(pantalla, mazmorra)


def bloque_mision_linea(pantalla, mision):
    """La misión en una línea bajo el panel de vida; retorna su rect (hover)."""
    pendiente = mision.objetivo_pendiente
    texto = f"MISIÓN · {mision.titulo}"
    if pendiente is not None:
        texto += f"  ›  {pendiente.texto}"
    f = fuente(assets.TAMANIO_FUENTE_PEQUENA, True)
    while f.size(texto)[0] > assets.ANCHO_MAXIMO_LINEA_MISION - 24 and len(texto) > 8:
        texto = texto[:-2].rstrip() + "…"
    return dibujo.chip(pantalla, texto, assets.POSICION_LINEA_MISION, assets.COLOR_TITULO_MISION, assets.COLOR_PANEL_HUD,
                       assets.COLOR_BORDE_MISION, assets.TAMANIO_FUENTE_PEQUENA, alto=assets.ALTO_LINEA_MISION, margen=12)


def bloque_mision(pantalla, mision, transcurrido, compacto):
    """Panel completo de la misión (mouse, Tab o HUD detallado)."""
    rect = assets.RECT_PANEL_MISION_COMBATE if compacto else assets.RECT_PANEL_MISION_CIUDAD
    return mision_render.dibujar_panel_mision(pantalla, mision, rect, transcurrido, compacto=compacto)


def bloque_cintillo(pantalla, titulares, tiempo):
    from src.ui import ciudad_render

    ciudad_render.dibujar_cintillo(pantalla, titulares, tiempo)


def bloque_aviso(pantalla, texto, color, centro):
    dibujo.chip(pantalla, texto, centro, assets.COLOR_TEXTO_HUD, assets.COLOR_PANEL_HUD, color,
                assets.TAMANIO_FUENTE_NORMAL, ancla="center", alto=34, margen=14)
