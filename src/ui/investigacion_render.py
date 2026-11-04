"""Pantalla de investigación del infiltrado, capítulo 3 (solo presentación).

Tres tarjetas, una por cuenta sospechosa, con su descripción y sus
pistas; la seleccionada lleva borde amarillo y flecha. Al acusar, la
tarjeta se tiñe (teal si era la coordinadora, magenta si no) y abajo
aparece el veredicto con sus efectos. Lee una Investigacion
(src/story/investigacion.py); no la modifica.
"""

from src.core import assets
from src.ui import dibujo

TITULO = "¿Quién coordinó la campaña de NOVA_404?"
SUBTITULO = "Tres cuentas difundieron los rumores. Revisa horarios y conexiones: la popularidad no es prueba."
TEXTO_ACUSAR = "Enter: señalar esta cuenta"
TEXTO_SEGUIR = "Enter: continuar"


def dibujar_investigacion(pantalla, investigacion):
    pantalla.fill(assets.COLOR_FONDO)
    dibujo.texto(pantalla, TITULO, (40, 36), assets.COLOR_TEXTO_HUD, assets.TAMANIO_FUENTE_GRANDE, negrita=True)
    dibujo.texto(pantalla, SUBTITULO, (40, 82), assets.COLOR_TEXTO_SECUNDARIO, assets.TAMANIO_FUENTE_NORMAL)
    resultado = investigacion.resultado
    for indice, (cuenta, rect) in enumerate(zip(investigacion.cuentas, assets.RECTS_TARJETA_SOSPECHOSO)):
        seleccionada = indice == investigacion.indice
        borde = assets.COLOR_BORDE_SOSPECHOSO_SELECCIONADO if seleccionada else assets.COLOR_BORDE_SOSPECHOSO
        relleno = assets.COLOR_FONDO_SOSPECHOSO
        if resultado is not None and cuenta["id"] == resultado.cuenta["id"]:
            borde = assets.COLOR_ACUSADO_CORRECTO if resultado.correcto else assets.COLOR_ACUSADO_ERRADO
        panel = dibujo.panel(pantalla, rect, relleno, borde, 3 if seleccionada else 1, radio=8)
        x, y = panel.left + 18, panel.top + 16
        dibujo.texto(pantalla, cuenta["nombre"], (x, y), assets.COLOR_TEXTO_HUD, assets.TAMANIO_FUENTE_MEDIA, negrita=True)
        y += 30
        y = dibujo.parrafo(pantalla, cuenta["descripcion"], (x, y), panel.width - 36, assets.COLOR_TEXTO_SECUNDARIO,
                           assets.TAMANIO_FUENTE_NORMAL, interlineado=4)
        y += 10
        dibujo.texto(pantalla, "Pistas", (x, y), assets.COLOR_AMARILLO, assets.TAMANIO_FUENTE_NORMAL, negrita=True)
        y += 24
        for pista in cuenta["pistas"]:
            y = dibujo.parrafo(pantalla, f"• {pista}", (x, y), panel.width - 36, assets.COLOR_TEXTO_HUD,
                               assets.TAMANIO_FUENTE_PEQUENA, interlineado=3) + 6
        if resultado is not None and cuenta["id"] == resultado.cuenta["id"]:
            etiqueta = "COORDINADORA" if resultado.correcto else cuenta["veredicto"].upper()
            dibujo.chip(pantalla, etiqueta, (panel.right - 14, panel.top + 14), assets.COLOR_FONDO, borde, borde,
                        ancla="topright")
        if seleccionada and resultado is None:
            dibujo.texto(pantalla, "▲", (panel.centerx, panel.bottom + 10), assets.COLOR_BORDE_SOSPECHOSO_SELECCIONADO,
                         assets.TAMANIO_FUENTE_MEDIA, ancla="midtop")
    if resultado is None:
        chip = dibujo.chip(pantalla, "← →", (560, 686), ancla="midright")
        dibujo.texto(pantalla, "elegir cuenta", (chip.right + 8, chip.centery), assets.COLOR_TEXTO_SECUNDARIO, ancla="midleft")
        dibujo.chip(pantalla, TEXTO_ACUSAR, (720, 686), ancla="midleft")
        return
    color = assets.COLOR_ACUSADO_CORRECTO if resultado.correcto else assets.COLOR_ACUSADO_ERRADO
    panel = dibujo.panel(pantalla, assets.RECT_VEREDICTO_INVESTIGACION, assets.COLOR_FONDO_PANEL, color, 2, radio=8)
    y = dibujo.parrafo(pantalla, resultado.texto, (panel.left + 16, panel.top + 10), panel.width - 32,
                       assets.COLOR_TEXTO_HUD, assets.TAMANIO_FUENTE_NORMAL, interlineado=4)
    signo = "+" if resultado.reputacion >= 0 else "−"
    dibujo.texto(pantalla, f"Reputación {signo}{abs(resultado.reputacion)}  ·  Puntos +{resultado.puntos}",
                 (panel.left + 16, y + 2), color, assets.TAMANIO_FUENTE_PEQUENA, negrita=True)
    dibujo.chip(pantalla, TEXTO_SEGUIR, (640, 686), ancla="center")
