"""Dibujo de una DialogoSecuencia del modo historia (solo presentación).

Velo semitransparente sobre la escena que haya debajo (ciudad, cuarto o
arena quietos) y un panel inferior con el retrato del hablante, su
nombre, el texto en párrafo y las teclas (Enter avanza, Esc salta).
Arriba del panel va el rótulo del capítulo. Los retratos de los roles
salen de sprites.retrato_rol; Civitas y NOVA_404 tienen un icono
dibujado en código (o assets/sprites/retratos/civitas.png / nova.png
si existen). No modifica el diálogo.
"""

import math

import pygame

from src.core import assets
from src.ui import dibujo, sprites

TEXTO_CONTINUAR = "Enter: continuar"
TEXTO_SALTAR = "Esc: saltar"
TEXTO_FIN = "Enter: empezar"


def dibujar_dialogo(pantalla, dialogo, tiempo=0.0):
    linea = dialogo.actual
    if linea is None:
        return
    fondo = sprites.fondo_historia(dialogo.fondo, pantalla.get_size()) if dialogo.fondo else None
    if fondo is not None:
        # La ilustración se funde con la escena de abajo (no la tapa del todo).
        fondo = fondo.copy()
        fondo.set_alpha(assets.ALFA_FONDO_DIALOGO)
        pantalla.blit(fondo, (0, 0))
    velo = pygame.Surface(pantalla.get_size(), pygame.SRCALPHA)
    velo.fill(assets.COLOR_VELO_DIALOGO)
    pantalla.blit(velo, (0, 0))

    if dialogo.titulo:
        dibujo.chip(pantalla, dialogo.titulo, assets.POSICION_TITULO_DIALOGO, assets.COLOR_TITULO_DIALOGO,
                    assets.COLOR_FONDO_DIALOGO, assets.COLOR_TITULO_DIALOGO, assets.TAMANIO_FUENTE_MEDIA,
                    ancla="center", alto=34, margen=18)

    panel = dibujo.panel(pantalla, assets.RECT_PANEL_DIALOGO, assets.COLOR_FONDO_DIALOGO,
                         assets.COLOR_BORDE_DIALOGO, 2, radio=10)
    retrato = _retrato(linea.retrato, assets.ALTO_RETRATO_DIALOGO)
    x_texto = panel.left + 24
    if retrato is not None:
        pantalla.blit(retrato, retrato.get_rect(midleft=(panel.left + 20, panel.centery)))
        x_texto = panel.left + 20 + retrato.get_width() + 24

    dibujo.texto(pantalla, linea.hablante, (x_texto, panel.top + 18), assets.COLOR_NOMBRE_DIALOGO,
                 assets.TAMANIO_FUENTE_MEDIA, negrita=True)
    dibujo.parrafo(pantalla, linea.texto, (x_texto, panel.top + 50), panel.right - 24 - x_texto,
                   assets.COLOR_TEXTO_HUD, assets.TAMANIO_FUENTE_MEDIA, interlineado=6)

    actual, total = dialogo.progreso
    dibujo.texto(pantalla, f"{actual}/{total}", (panel.right - 20, panel.top + 18), assets.COLOR_TEXTO_SECUNDARIO,
                 assets.TAMANIO_FUENTE_PEQUENA, ancla="topright")
    # Indicador que late para invitar a seguir.
    fase = (math.sin(tiempo * 2 * math.pi / assets.DURACION_PARPADEO_INDICADOR) + 1) / 2
    visible = fase > 0.35
    ultimo = actual == total
    if visible:
        chip = dibujo.chip(pantalla, TEXTO_FIN if ultimo else TEXTO_CONTINUAR, (panel.right - 20, panel.bottom - 16),
                           assets.COLOR_TEXTO_HUD, assets.COLOR_FONDO_CHIP, assets.COLOR_BORDE_CHIP, ancla="bottomright")
    else:
        chip = pygame.Rect(panel.right - 20, panel.bottom - 16, 0, 0)
    if not ultimo:
        dibujo.chip(pantalla, TEXTO_SALTAR, (chip.left - 10 if visible else panel.right - 150, panel.bottom - 16),
                    assets.COLOR_TEXTO_SECUNDARIO, assets.COLOR_FONDO_CHIP, assets.COLOR_BORDE_CHIP, ancla="bottomright")


_cache_iconos = {}


def _retrato(id_retrato, alto):
    """Imagen del hablante: retrato del rol, PNG opcional del sistema o
    icono en código (Civitas: panel teal con "C"; NOVA_404: cuadro
    magenta con glitch). None si no hay retrato."""
    if id_retrato is None:
        return None
    imagen = sprites.retrato_rol(id_retrato, alto)
    if imagen is not None:
        return imagen
    if id_retrato in (assets.ID_RETRATO_CIVITAS, assets.ID_RETRATO_NOVA):
        return _icono_sistema(id_retrato, alto)
    # Rol sin retrato en disco: el sprite del jugador en grande.
    color = assets.COLOR_POR_ROL.get(id_retrato, assets.COLOR_TEXTO_HUD)
    return sprites.sprite_jugador(color, escala=5, rol=id_retrato)


def _icono_sistema(id_retrato, alto):
    clave = (id_retrato, alto)
    if clave in _cache_iconos:
        return _cache_iconos[clave]
    lado = alto - 20
    icono = pygame.Surface((lado, lado), pygame.SRCALPHA)
    if id_retrato == assets.ID_RETRATO_CIVITAS:
        color = assets.COLOR_RETRATO_CIVITAS
        pygame.draw.rect(icono, assets.COLOR_FONDO_PANEL, icono.get_rect(), border_radius=14)
        pygame.draw.rect(icono, color, icono.get_rect(), 3, border_radius=14)
        pygame.draw.circle(icono, color, (lado // 2, lado // 2), lado // 3, 6)
        pygame.draw.rect(icono, assets.COLOR_FONDO_PANEL, (lado * 0.62, lado * 0.42, lado * 0.3, lado * 0.16))
        dibujo.texto(icono, "CIVITAS", (lado // 2, lado - 14), color, assets.TAMANIO_FUENTE_PEQUENA,
                     negrita=True, ancla="center")
    else:
        color = assets.COLOR_RETRATO_NOVA
        pygame.draw.rect(icono, (30, 8, 20), icono.get_rect(), border_radius=6)
        pygame.draw.rect(icono, color, icono.get_rect(), 3, border_radius=6)
        # Líneas de glitch horizontales.
        for i, y in enumerate(range(12, lado - 12, 11)):
            ancho = (i * 37) % (lado - 24) + 12
            pygame.draw.rect(icono, color if i % 3 else assets.COLOR_MORADO, (8, y, ancho, 4))
        dibujo.texto(icono, "404", (lado // 2, lado // 2), assets.COLOR_TEXTO_HUD, assets.TAMANIO_FUENTE_GRANDE,
                     negrita=True, ancla="center")
    _cache_iconos[clave] = icono
    return icono
