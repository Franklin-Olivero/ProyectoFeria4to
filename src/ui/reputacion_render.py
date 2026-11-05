"""Indicador de reputación: el momento en que una decisión pesa (presentación).

    IndicadorReputacion: animación de un CambioReputacion, sin pygame en su
        lógica: la barra viaja del valor anterior al nuevo y el texto entra
        después. Enter completa la animación; otro Enter cierra.
    dibujar_indicador: velo oscuro, nombre de la zona, gran "REPUTACIÓN +25",
        barra con la marca del valor anterior, cambio de nivel y mensaje.
    dibujar_chip_reputacion: valor y nivel en el HUD de la ciudad.

No tapa toda la pantalla: la escena se sigue viendo debajo del velo.
"""

import pygame

from src.core import assets
from src.story.reputacion import nivel_de
from src.ui import dibujo, kit, layout

DURACION_BARRA = 1.4  # s que tarda la barra en llegar al nuevo valor
RETARDO_MENSAJE = 0.9


class IndicadorReputacion:
    def __init__(self, cambio):
        self.cambio = cambio
        self.tiempo = 0.0
        self.cerrado = False

    @property
    def terminado(self):
        return self.tiempo >= DURACION_BARRA + RETARDO_MENSAJE

    @property
    def valor_mostrado(self):
        """Valor animado desde `antes` hasta `despues` (ease-out). O(1)."""
        t = min(1.0, self.tiempo / DURACION_BARRA)
        suave = 1 - (1 - t) ** 3
        return round(self.cambio.antes + (self.cambio.despues - self.cambio.antes) * suave)

    def actualizar(self, dt):
        self.tiempo += dt

    def avanzar(self):
        """Enter: primero completa la animación; luego cierra."""
        if self.terminado:
            self.cerrado = True
        else:
            self.tiempo = DURACION_BARRA + RETARDO_MENSAJE


def dibujar_indicador(pantalla, indicador):
    cambio = indicador.cambio
    delta = cambio.delta
    color = assets.COLOR_VERIFICADO if delta > 0 else assets.COLOR_NOVA if delta < 0 else assets.COLOR_TEXTO_SECUNDARIO
    kit.velo(pantalla, round(190 * min(1.0, indicador.tiempo / 0.3)))
    rect = layout.entrada(assets.RECT_INDICADOR_REPUTACION, indicador.tiempo, distancia=18)
    kit.panel(pantalla, rect, color, alfa=246, radio=12, filo="arriba")
    cx = rect.centerx
    y = rect.top + 26
    if cambio.motivo:
        kit.rotulo(pantalla, cambio.motivo, (cx, y), assets.COLOR_TEXTO_SECUNDARIO, ancla="midtop")
    y += 26
    signo = "+" if delta > 0 else "−" if delta < 0 else "±"
    dibujo.texto(pantalla, f"REPUTACIÓN {signo}{abs(delta)}", (cx, y), color, assets.TAMANIO_FUENTE_GRANDE,
                 negrita=True, ancla="midtop")
    y += 58
    barra = pygame.Rect(rect.left + 56, y, rect.width - 112, 14)
    valor = indicador.valor_mostrado
    kit.barra_reputacion(pantalla, barra, valor, valor_marca=cambio.antes)
    dibujo.texto(pantalla, "−100", (barra.left, barra.bottom + 12), assets.COLOR_TEXTO_APAGADO, assets.TAMANIO_FUENTE_PEQUENA)
    dibujo.texto(pantalla, "+100", (barra.right, barra.bottom + 12), assets.COLOR_TEXTO_APAGADO, assets.TAMANIO_FUENTE_PEQUENA,
                 ancla="topright")
    nombre = nivel_de(valor)[1]
    dibujo.texto(pantalla, f"{valor:+d}  ·  {nombre}", (cx, barra.bottom + 12), assets.color_reputacion(valor),
                 assets.TAMANIO_FUENTE_NORMAL, negrita=True, ancla="midtop")
    if indicador.tiempo > RETARDO_MENSAJE:
        caja = pygame.Rect(rect.left + 56, barra.bottom + 46, rect.width - 112, 78)
        layout.parrafo_en_caja(pantalla, cambio.mensaje, caja, assets.COLOR_TEXTO_HUD, assets.TAMANIO_FUENTE_MEDIA,
                               interlineado=5, centrado=True)
    if cambio.nivel_antes != cambio.nivel_despues and indicador.terminado:
        kit.rotulo(pantalla, "Tu nivel cambió", (cx, rect.bottom - 62), assets.COLOR_ALERTA, ancla="midtop")
    if indicador.terminado:
        kit.tecla(pantalla, "Enter", "continuar", (cx, rect.bottom - 26), ancla="center")


def dibujar_chip_reputacion(pantalla, valor, posicion=assets.POSICION_CHIP_REPUTACION, etiqueta="Reputación", ancho=148):
    """Lectura de reputación en el HUD: rótulo, valor con signo y barra mínima."""
    x, y = posicion
    color = assets.color_reputacion(valor)
    kit.panel(pantalla, (x - 12, y - 10, ancho + 24, 48), color, alfa=222, radio=8)
    kit.rotulo(pantalla, etiqueta, (x, y), assets.COLOR_TEXTO_SECUNDARIO)
    dibujo.texto(pantalla, f"{valor:+d}", (x + ancho, y - 1), color, assets.TAMANIO_FUENTE_NORMAL, negrita=True, ancla="topright")
    kit.barra_reputacion(pantalla, pygame.Rect(x, y + 20, ancho, 6), valor, mostrar_tramos=False)
