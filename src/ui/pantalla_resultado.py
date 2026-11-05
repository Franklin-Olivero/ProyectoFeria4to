"""Pantalla de consecuencias de una mazmorra normal (solo presentación).

Se muestra después de la terminal, antes de volver a Ciudad Nova. Sobre la
ilustración de la zona: qué ocurrió (el texto narrativo manda) y tres paneles
de lectura rápida: tu decisión, cómo cambió la ciudad y el colapso electoral.
Enter continúa (lo atiende Main.py en la escena RESULTADO).
"""

from dataclasses import dataclass, field

import pygame

from src.core import assets
from src.story.escenarios import NOMBRES_ESTADO_EVIDENCIA
from src.ui import dibujo, indicadores_render, kit, layout, sprites
from src.ui.terminal_decision import PURIFICACION_EXITOSA

# Explicación según la opción elegida en la terminal.
EXPLICACIONES = {
    "Verificar": "Contrastaste la publicación con la fuente oficial. La zona queda purificada.",
    "Reportar": "Reportaste la publicación antes de que siguiera creciendo. La zona queda purificada.",
    "Compartir": "Compartiste el rumor y se propagó. La zona detonó y la incursión falló.",
    "Ignorar": "Ignoraste la publicación y siguió creciendo. La zona detonó y la incursión falló.",
    "Derrota": "Todo el equipo cayó en combate. La zona detonó y la incursión falló.",
}
EXPLICACION_TIEMPO = "Se acabó el tiempo sin decidir. La publicación se propagó y la incursión falló."
EXPLICACION_EXITO = "La zona queda purificada."
EXPLICACION_FALLO = "La zona detonó y la incursión falló."

_RECT_DECISION = pygame.Rect(56, 300, 380, 280)
_RECT_DELTAS = pygame.Rect(450, 300, 380, 280)
_RECT_COLAPSO = pygame.Rect(844, 300, 380, 280)


@dataclass
class ResultadoMazmorra:
    resultado: str  # PURIFICACION_EXITOSA o DETONACION
    opcion: str | None  # etiqueta de la opción elegida (None si se agotó el tiempo)
    colapso_antes: float
    colapso_despues: float
    zona: str
    # Modo historia: la Consecuencia del escenario (texto, efectos,
    # reputación, puntos) y los deltas reales sobre los indicadores.
    consecuencia: object = None
    deltas: dict = field(default_factory=dict)
    texto: str = ""  # invitado: la explicación que mandó el host

    @property
    def exito(self):
        return self.resultado == PURIFICACION_EXITOSA

    @property
    def explicacion(self):
        if self.consecuencia is not None:
            return self.consecuencia.texto
        if self.texto:
            return self.texto
        if self.opcion is None:
            return EXPLICACION_TIEMPO
        return EXPLICACIONES.get(self.opcion, EXPLICACION_EXITO if self.exito else EXPLICACION_FALLO)


def dibujar_resultado(pantalla, info):
    exito = info.exito
    acento = assets.COLOR_VERIFICADO if exito else assets.COLOR_NOVA
    fondo = sprites.fondo_historia(assets.FONDO_POR_ZONA[info.zona], pantalla.get_size()) if info.zona in assets.FONDO_POR_ZONA else None
    if fondo is not None:
        pantalla.blit(fondo, (0, 0))
    else:
        pantalla.fill(assets.COLOR_NOCHE)
    kit.velo(pantalla, 205)

    kit.rotulo(pantalla, f"Consecuencias · {info.zona}", (56, 44), assets.COLOR_TEXTO_SECUNDARIO)
    titulo = "Purificación exitosa" if exito else "Detonación"
    dibujo.texto(pantalla, titulo, (56, 66), acento, assets.TAMANIO_FUENTE_ENORME, negrita=True)
    layout.parrafo_en_caja(pantalla, info.explicacion, pygame.Rect(56, 138, 1168, 100), assets.COLOR_TEXTO_HUD,
                           assets.TAMANIO_FUENTE_TITULO, interlineado=8)

    _dibujar_decision(pantalla, info, acento)
    if info.consecuencia is not None:
        indicadores_render.dibujar_deltas(pantalla, _RECT_DELTAS, info.deltas)
    else:
        kit.panel(pantalla, _RECT_DELTAS, assets.COLOR_CIVITAS)
    _dibujar_colapso(pantalla, info, acento)
    kit.tecla(pantalla, "Enter", "continuar", (pantalla.get_width() // 2, 620), ancla="center")


def _dibujar_decision(pantalla, info, acento):
    kit.panel(pantalla, _RECT_DECISION, acento)
    x, y = _RECT_DECISION.left + 22, _RECT_DECISION.top + 18
    kit.rotulo(pantalla, "Tu decisión", (x, y), assets.COLOR_TEXTO_SECUNDARIO)
    c = info.consecuencia
    camino = " › ".join(c.camino) if c is not None and c.camino else (info.opcion or "Sin decidir (tiempo agotado)")
    y = layout.parrafo_en_caja(pantalla, camino, pygame.Rect(x, y + 22, _RECT_DECISION.width - 44, 72), assets.COLOR_TEXTO_HUD,
                               assets.TAMANIO_FUENTE_MEDIA, negrita=True, interlineado=4) + 10
    if c is None:
        return
    kit.rotulo(pantalla, "Pruebas al decidir", (x, y), assets.COLOR_TEXTO_SECUNDARIO)
    dibujo.texto(pantalla, NOMBRES_ESTADO_EVIDENCIA.get(c.estado_evidencia, c.estado_evidencia), (x, y + 20), assets.COLOR_TEXTO_HUD,
                 assets.TAMANIO_FUENTE_NORMAL)
    y += 54
    kit.rotulo(pantalla, "Tu reputación", (x, y), assets.COLOR_TEXTO_SECUNDARIO)
    signo = "+" if c.reputacion > 0 else "−" if c.reputacion < 0 else "±"
    color = assets.COLOR_VERIFICADO if c.reputacion > 0 else assets.COLOR_NOVA if c.reputacion < 0 else assets.COLOR_TEXTO_SECUNDARIO
    dibujo.texto(pantalla, f"{signo}{abs(c.reputacion)}", (x, y + 18), color, assets.TAMANIO_FUENTE_TITULO, negrita=True)
    dibujo.texto(pantalla, f"Puntos +{c.puntos}", (_RECT_DECISION.right - 22, y + 22), assets.COLOR_TEXTO_SECUNDARIO,
                 assets.TAMANIO_FUENTE_NORMAL, ancla="topright")


def _dibujar_colapso(pantalla, info, acento):
    kit.panel(pantalla, _RECT_COLAPSO, assets.COLOR_ALERTA)
    x, y = _RECT_COLAPSO.left + 22, _RECT_COLAPSO.top + 18
    kit.rotulo(pantalla, "Colapso electoral", (x, y), assets.COLOR_TEXTO_SECUNDARIO)
    dibujo.texto(pantalla, f"{info.colapso_despues:.1f} %", (x, y + 22), acento, assets.TAMANIO_FUENTE_GRANDE, negrita=True)
    barra = pygame.Rect(x, y + 84, _RECT_COLAPSO.width - 44, 12)
    dibujo.barra(pantalla, barra, info.colapso_despues / 100.0)
    x_antes = barra.left + round(barra.width * info.colapso_antes / 100.0)
    pygame.draw.line(pantalla, assets.COLOR_TEXTO_HUD, (x_antes, barra.top - 4), (x_antes, barra.bottom + 3), 2)
    delta = info.colapso_despues - info.colapso_antes
    signo = "+" if delta >= 0 else "−"
    dibujo.texto(pantalla, f"{signo}{abs(delta):.1f} % respecto a antes", (x, barra.bottom + 10), assets.COLOR_TEXTO_HUD,
                 assets.TAMANIO_FUENTE_NORMAL)
    nota = "Cada zona purificada aleja la ciudad del colapso." if info.exito else "Si llega a 100 %, Ciudad Nova cae."
    layout.parrafo_en_caja(pantalla, nota, pygame.Rect(x, barra.bottom + 40, _RECT_COLAPSO.width - 44, 60), assets.COLOR_TEXTO_SECUNDARIO,
                           assets.TAMANIO_FUENTE_NORMAL, interlineado=4)
