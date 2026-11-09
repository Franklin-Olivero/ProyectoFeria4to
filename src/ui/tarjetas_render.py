"""Tarjetas de Civitas del modo historia (solo presentación).

    - dibujar_tarjeta_evidencia: una prueba encontrada (título, fuente y
      fragmento), con el chip "PISTA NOVA_404" si la trae. Aparece unos
      segundos en combate al limpiar un cuarto y en la pantalla de
      resultado.
No modifican ningún estado.
"""

from src.core import assets
from src.ui import dibujo, layout

TEXTO_PISTA = "PISTA NOVA_404"
TEXTO_EVIDENCIA = "Evidencia encontrada"


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