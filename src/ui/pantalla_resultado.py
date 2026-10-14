"""Pantalla de resultado de una mazmorra normal (solo presentación).

Se muestra justo después de la terminal de decisión, antes de volver
al mapa de la ciudad: fondo teal para Purificación Exitosa y magenta
para Detonación, una ilustración en pixel art, la barra de colapso con
el valor anterior y el nuevo, y el botón de continuar (ENTER, que
atiende Main.py en la escena RESULTADO).
"""

from dataclasses import dataclass

import pygame

from src.core import assets
from src.ui import dibujo, sprites
from src.ui.terminal_decision import PURIFICACION_EXITOSA

# Explicación según la opción elegida en la terminal.
EXPLICACIONES = {
    "Verificar": "Contrastaste la publicación con la fuente oficial. La zona queda purificada.",
    "Reportar": "Reportaste la publicación antes de que siguiera creciendo. La zona queda purificada.",
    "Compartir": "Compartiste el rumor y se propagó. La zona detonó y la incursión falló.",
    "Ignorar": "Ignoraste la publicación y siguió creciendo. La zona detonó y la incursión falló.",
}
EXPLICACION_TIEMPO = "Se acabó el tiempo sin decidir. La publicación se propagó y la incursión falló."
EXPLICACION_EXITO = "La zona queda purificada."
EXPLICACION_FALLO = "La zona detonó y la incursión falló."


@dataclass
class ResultadoMazmorra:
    resultado: str  # PURIFICACION_EXITOSA o DETONACION
    opcion: str | None  # etiqueta de la opción elegida (None si se agotó el tiempo)
    colapso_antes: float
    colapso_despues: float
    zona: str

    @property
    def exito(self):
        return self.resultado == PURIFICACION_EXITOSA

    @property
    def explicacion(self):
        if self.opcion is None:
            return EXPLICACION_TIEMPO
        return EXPLICACIONES.get(self.opcion, EXPLICACION_EXITO if self.exito else EXPLICACION_FALLO)


def dibujar_resultado(pantalla, info):
    exito = info.exito
    acento = assets.COLOR_TEAL if exito else assets.COLOR_MAGENTA
    pantalla.fill(assets.COLOR_FONDO_EXITO if exito else assets.COLOR_FONDO_FALLO)
    cx = pantalla.get_width() // 2

    dibujo.texto(pantalla, "Resultado de la mazmorra", (cx, 70), assets.COLOR_TEXTO_SECUNDARIO,
                 assets.TAMANIO_FUENTE_NORMAL, ancla="center")
    titulo = "Purificación exitosa" if exito else "Detonación"
    dibujo.texto(pantalla, titulo, (cx, 118), acento, assets.TAMANIO_FUENTE_ENORME, negrita=True, ancla="center")
    dibujo.parrafo(pantalla, info.explicacion, (cx, 158), 640, assets.COLOR_TEXTO_HUD,
                   assets.TAMANIO_FUENTE_MEDIA, interlineado=6, centrado=True)

    _dibujar_ilustracion(pantalla, exito)
    _dibujar_barra(pantalla, info, acento)

    boton = dibujo.panel(pantalla, assets.RECT_BOTON_RESULTADO, acento, None, 0, radio=6)
    dibujo.texto(pantalla, "Volver al mapa de la ciudad", boton.center, assets.COLOR_FONDO,
                 assets.TAMANIO_FUENTE_MEDIA, negrita=True, ancla="center")
    chip = dibujo.chip(pantalla, "Enter", (cx - 40, boton.bottom + 36), ancla="midright")
    dibujo.texto(pantalla, "para continuar", (chip.right + 8, chip.centery), assets.COLOR_TEXTO_SECUNDARIO,
                 assets.TAMANIO_FUENTE_NORMAL, ancla="midleft")


def _dibujar_ilustracion(pantalla, exito):
    marco = dibujo.panel(pantalla, assets.RECT_ILUSTRACION_RESULTADO, assets.COLOR_MARCO_ILUSTRACION, None, 0, radio=4)
    interior = marco.inflate(-24, -24)
    # Piso de baldosas en miniatura, como el del cuarto.
    lado = 20
    pygame.draw.rect(pantalla, assets.COLOR_BALDOSA_A, interior)
    for fila, y in enumerate(range(interior.top, interior.bottom, lado)):
        for columna, x in enumerate(range(interior.left, interior.right, lado)):
            if (fila + columna) % 2:
                pygame.draw.rect(pantalla, assets.COLOR_BALDOSA_B, pygame.Rect(x, y, lado, lado).clip(interior))
    if exito:
        icono = sprites.sprite(sprites.CHULO, sprites.PALETA_CHULO, escala=6)
        destello = sprites.sprite(sprites.DESTELLO, sprites.PALETA_DESTELLO, escala=3)
        for dx, dy in ((-110, -40), (-70, 40), (90, -45), (120, 35), (40, 50)):
            pantalla.blit(destello, destello.get_rect(center=(marco.centerx + dx, marco.centery + dy)))
    else:
        icono = sprites.sprite(sprites.EXPLOSION, sprites.PALETA_EXPLOSION, escala=6)
        for dx, dy in ((-120, -50), (110, -55), (-105, 45), (115, 50)):
            pygame.draw.rect(pantalla, assets.COLOR_AMARILLO, (marco.centerx + dx, marco.centery + dy, 8, 8))
        # Grietas desde la explosión.
        for angulo in (-150, -30, 150, 30):
            inicio = pygame.Vector2(50, 0).rotate(angulo) + marco.center
            fin = pygame.Vector2(135, 0).rotate(angulo + 12) + marco.center
            pygame.draw.line(pantalla, assets.COLOR_MAGENTA, inicio, fin, 2)
    pantalla.blit(icono, icono.get_rect(center=marco.center))


def _dibujar_barra(pantalla, info, acento):
    rect = pygame.Rect(assets.RECT_BARRA_RESULTADO)
    dibujo.texto(pantalla, "Barra de colapso electoral", (rect.left, rect.top - 24), assets.COLOR_TEXTO_SECUNDARIO,
                 assets.TAMANIO_FUENTE_NORMAL)
    dibujo.texto(pantalla, f"{info.colapso_antes:.1f}% → {info.colapso_despues:.1f}%", (rect.right, rect.top - 24),
                 acento, assets.TAMANIO_FUENTE_NORMAL, negrita=True, ancla="topright")
    dibujo.barra(pantalla, rect, info.colapso_despues / 100.0)
    # Marca blanca en el valor anterior.
    x_antes = rect.left + round(rect.width * info.colapso_antes / 100.0)
    pygame.draw.line(pantalla, assets.COLOR_TEXTO_HUD, (x_antes, rect.top - 4), (x_antes, rect.bottom + 4), 3)
    dibujo.texto(pantalla, "0%", (rect.left, rect.bottom + 6), assets.COLOR_TEXTO_SECUNDARIO, assets.TAMANIO_FUENTE_PEQUENA)
    dibujo.texto(pantalla, "100%", (rect.right, rect.bottom + 6), assets.COLOR_TEXTO_SECUNDARIO,
                 assets.TAMANIO_FUENTE_PEQUENA, ancla="topright")

    delta = info.colapso_despues - info.colapso_antes
    signo = "+" if delta >= 0 else "−"
    dibujo.chip(pantalla, f"{signo}{abs(delta):.1f}%", (rect.centerx, rect.bottom + 44), acento,
                assets.COLOR_FONDO_PANEL, acento, assets.TAMANIO_FUENTE_MEDIA, ancla="center", alto=34, margen=18)
    nota = "Cada mazmorra purificada reduce el colapso." if info.exito else "Cada incursión fallida aumenta el colapso."
    dibujo.texto(pantalla, nota, (rect.centerx, rect.bottom + 84), assets.COLOR_TEXTO_SECUNDARIO,
                 assets.TAMANIO_FUENTE_NORMAL, ancla="center")
