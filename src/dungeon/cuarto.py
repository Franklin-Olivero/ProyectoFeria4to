"""Lógica y dibujo de un cuarto de mazmorra: puertas y enemigos.

Comportamiento real: mientras existan enemigos VIVOS en el cuarto, las
4 puertas (N, S, E, W) permanecen bloqueadas; en cuanto el último
enemigo muere, las puertas se abren. Los enemigos traen su propia IA
(árbol de comportamiento, ver src/entities/enemy.py); este módulo solo
los posiciona y decide el estado de las puertas.

Cuántos enemigos aparecen y qué tan rápidos son NO es fijo: al crear el
cuarto se clasifican los reportes de toxicidad de la zona con el árbol
N-ario (ver src/dungeon/clasificador_toxicidad.py) y el nivel
resultante decide la dificultad.

Fases del cuarto: "combate" mientras queden enemigos; al morir el
último pasa a "decision" e instancia el minijuego de decisión
(src/ui/terminal_decision.py); el loop principal lo pasa a "resuelto"
cuando la terminal da un resultado.
"""

import pygame

from src.core import assets
from src.dungeon.clasificador_toxicidad import (
    calcular_nivel_toxicidad,
    construir_arbol_reportes,
    nivel_a_dificultad,
)
from src.entities.enemy import Enemigo
from src.ui.terminal_decision import TerminalDecision, construir_arbol_publicacion

ANCHO_CUARTO = 500
ALTO_CUARTO = 400

GROSOR_MURO = 4
COLOR_MURO = (200, 200, 210)

ANCHO_PUERTA = 80
GROSOR_PUERTA = 20
COLOR_PUERTA_BLOQUEADA = (200, 30, 30)
COLOR_PUERTA_ABIERTA = (30, 180, 60)

TECLA_DEBUG_ELIMINAR_ENEMIGO = pygame.K_k

SEPARACION_VERTICAL_ENEMIGOS = 60

FASE_COMBATE = "combate"
FASE_DECISION = "decision"
FASE_RESUELTO = "resuelto"

# Reportes simulados de la zona del cuarto de prueba (un colegio con
# ciberbullying). Hardcodeados a propósito: el resultado es determinista
# y fácil de sustentar. Promedio de gravedad = 3.6 -> nivel 65.0 -> tramo
# medio (3 enemigos, velocidad x1.0).
NOMBRE_ZONA_EJEMPLO = "Colegio Distrital"
REPORTES_ZONA_EJEMPLO = [
    {"id": 1, "tipo": "comentario", "gravedad": 2},
    {"id": 2, "tipo": "publicacion_viral", "gravedad": 4},
    {"id": 3, "tipo": "denuncia", "gravedad": 5},
    {"id": 4, "tipo": "comentario", "gravedad": 3},
    {"id": 5, "tipo": "publicacion_viral", "gravedad": 4},
]


class Puerta:
    """Una puerta del cuarto: su rectángulo y si está bloqueada o abierta."""

    def __init__(self, direccion, rect):
        self.direccion = direccion
        self.rect = rect
        self.bloqueada = True

    def color(self):
        return COLOR_PUERTA_BLOQUEADA if self.bloqueada else COLOR_PUERTA_ABIERTA


class Cuarto:
    """Un cuarto con 4 puertas y una lista de enemigos.

    Las puertas están bloqueadas mientras queden enemigos vivos, y se
    abren automáticamente en cuanto el último muere. La cantidad y
    velocidad de los enemigos sale del nivel de toxicidad de `reportes`.
    """

    def __init__(self, reportes=REPORTES_ZONA_EJEMPLO, nombre_zona=NOMBRE_ZONA_EJEMPLO):
        ancho_ventana = pygame.display.get_surface().get_width()
        alto_ventana = pygame.display.get_surface().get_height()

        self.rect = pygame.Rect(0, 0, ANCHO_CUARTO, ALTO_CUARTO)
        self.rect.center = (ancho_ventana // 2, alto_ventana // 2)

        arbol_reportes = construir_arbol_reportes(reportes, nombre_zona)
        self.nivel_toxicidad = calcular_nivel_toxicidad(arbol_reportes)
        self.dificultad = nivel_a_dificultad(self.nivel_toxicidad)

        self.fase = FASE_COMBATE
        self.terminal = None

        self.puertas = self._crear_puertas()
        self.enemigos = self._crear_enemigos_iniciales()
        self._actualizar_estado_puertas()

    def _crear_puertas(self):
        r = self.rect

        rect_n = pygame.Rect(0, 0, ANCHO_PUERTA, GROSOR_PUERTA)
        rect_n.center = (r.centerx, r.top)

        rect_s = pygame.Rect(0, 0, ANCHO_PUERTA, GROSOR_PUERTA)
        rect_s.center = (r.centerx, r.bottom)

        rect_e = pygame.Rect(0, 0, GROSOR_PUERTA, ANCHO_PUERTA)
        rect_e.center = (r.right, r.centery)

        rect_w = pygame.Rect(0, 0, GROSOR_PUERTA, ANCHO_PUERTA)
        rect_w.center = (r.left, r.centery)

        return {
            "N": Puerta("N", rect_n),
            "S": Puerta("S", rect_s),
            "E": Puerta("E", rect_e),
            "W": Puerta("W", rect_w),
        }

    def _crear_enemigos_iniciales(self):
        """Reparte `cantidad_enemigos` a lo ancho del cuarto, en zigzag.

        La velocidad de cada enemigo es la base de assets multiplicada
        por el `multiplicador_velocidad` de la dificultad.
        """
        r = self.rect
        cantidad = self.dificultad["cantidad_enemigos"]
        velocidad = assets.VELOCIDAD_ENEMIGO * self.dificultad["multiplicador_velocidad"]
        enemigos = []
        for i in range(cantidad):
            x = r.left + (i + 1) * r.width // (cantidad + 1)
            y = r.centery - SEPARACION_VERTICAL_ENEMIGOS * (i % 2)
            enemigos.append(Enemigo(x, y, velocidad))
        return enemigos

    def _actualizar_estado_puertas(self):
        bloqueadas = len(self.enemigos) > 0
        for puerta in self.puertas.values():
            puerta.bloqueada = bloqueadas
        self._verificar_fin_combate()

    def _verificar_fin_combate(self):
        """Sin enemigos en fase de combate -> arranca el minijuego de decisión."""
        if self.fase == FASE_COMBATE and not self.enemigos:
            self.fase = FASE_DECISION
            self.terminal = TerminalDecision(construir_arbol_publicacion())
            self.terminal.iniciar()

    def actualizar(self, dt, jugador, proyectiles_enemigos):
        """Corre un tick de IA para cada enemigo vivo y refresca las puertas.

        `proyectiles_enemigos` es la lista de salida donde los enemigos
        agregan los proyectiles que disparan (ver Enemigo._disparar_a_objetivo).
        """
        for enemigo in self.enemigos:
            enemigo.actualizar(dt, jugador, proyectiles_enemigos)
            enemigo.mantener_dentro(self.rect)

        cantidad_antes = len(self.enemigos)
        self.enemigos = [enemigo for enemigo in self.enemigos if enemigo.vivo]
        if len(self.enemigos) != cantidad_antes:
            self._actualizar_estado_puertas()

    def eliminar_un_enemigo(self):
        """Debug: quita un enemigo de la lista y refresca el estado de las puertas."""
        if self.enemigos:
            self.enemigos.pop()
            self._actualizar_estado_puertas()

    def manejar_evento(self, evento):
        if evento.type == pygame.KEYDOWN and evento.key == TECLA_DEBUG_ELIMINAR_ENEMIGO:
            self.eliminar_un_enemigo()

    def dibujar(self, pantalla):
        pygame.draw.rect(pantalla, COLOR_MURO, self.rect, GROSOR_MURO)

        for puerta in self.puertas.values():
            pygame.draw.rect(pantalla, puerta.color(), puerta.rect)

        for enemigo in self.enemigos:
            enemigo.dibujar(pantalla)
