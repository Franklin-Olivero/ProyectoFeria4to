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

Dentro de una mazmorra de varios cuartos (src/dungeon/mazmorra.py)
cada cuarto recibe además qué puertas existen (solo donde el grafo
tiene pasillo), su toxicidad/dificultad ya calculadas y si es el
cuarto final.

Fases del cuarto: "combate" mientras queden enemigos; al morir el
último, el cuarto final pasa a "decision" e instancia el minijuego de
decisión (src/ui/terminal_decision.py) y un cuarto intermedio pasa a
"limpio". El loop principal pasa el final a "resuelto" cuando la
terminal da un resultado.
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

TECLA_DEBUG_ELIMINAR_ENEMIGO = pygame.K_k

SEPARACION_VERTICAL_ENEMIGOS = 60

FASE_COMBATE = "combate"
FASE_DECISION = "decision"
FASE_RESUELTO = "resuelto"
FASE_LIMPIO = "limpio"  # cuarto intermedio sin enemigos: no hay decisión

DIRECCIONES = ("N", "S", "E", "W")

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
    """Una puerta del cuarto: su rectángulo y su estado.

    bloqueada: hay enemigos vivos en el cuarto.
    sellada: lleva al cuarto final y todavía quedan cuartos pendientes
        (lo decide la mazmorra, no los enemigos de este cuarto).
    """

    def __init__(self, direccion, rect):
        self.direccion = direccion
        self.rect = rect
        self.bloqueada = True
        self.sellada = False

    @property
    def cruzable(self):
        return not self.bloqueada and not self.sellada

    def color(self):
        if self.bloqueada:
            return assets.COLOR_PUERTA_BLOQUEADA
        if self.sellada:
            return assets.COLOR_PUERTA_SELLADA
        return assets.COLOR_PUERTA_ABIERTA


class Cuarto:
    """Un cuarto con hasta 4 puertas y una lista de enemigos.

    Las puertas están bloqueadas mientras queden enemigos vivos, y se
    abren automáticamente en cuanto el último muere. La cantidad y
    velocidad de los enemigos sale del nivel de toxicidad de `reportes`,
    salvo que se pasen `nivel_toxicidad` y/o `dificultad` ya calculados
    (lo hace la mazmorra multi-cuarto). `direcciones_puertas` dice qué
    puertas existen; `es_final` si al limpiarlo aparece la decisión.
    """

    def __init__(
        self,
        reportes=REPORTES_ZONA_EJEMPLO,
        nombre_zona=NOMBRE_ZONA_EJEMPLO,
        direcciones_puertas=DIRECCIONES,
        nivel_toxicidad=None,
        dificultad=None,
        es_final=True,
        permitir_decision=None,
    ):
        ancho_ventana = pygame.display.get_surface().get_width()
        alto_ventana = pygame.display.get_surface().get_height()

        self.rect = pygame.Rect(0, 0, ANCHO_CUARTO, ALTO_CUARTO)
        self.rect.center = (ancho_ventana // 2, alto_ventana // 2)

        if nivel_toxicidad is None:
            nivel_toxicidad = calcular_nivel_toxicidad(construir_arbol_reportes(reportes, nombre_zona))
        self.nivel_toxicidad = nivel_toxicidad
        self.dificultad = dificultad if dificultad is not None else nivel_a_dificultad(nivel_toxicidad)
        self.es_final = es_final
        # Defensa extra: función sin argumentos que dice si la decisión
        # puede empezar (la mazmorra exige el sello cumplido). None = sí.
        self.permitir_decision = permitir_decision

        self.fase = FASE_COMBATE
        self.terminal = None

        self.puertas = self._crear_puertas(direcciones_puertas)
        self.enemigos = self._crear_enemigos_iniciales()
        self._actualizar_estado_puertas()

    def _crear_puertas(self, direcciones):
        r = self.rect

        rect_n = pygame.Rect(0, 0, assets.ANCHO_PUERTA, assets.GROSOR_PUERTA)
        rect_n.center = (r.centerx, r.top)

        rect_s = pygame.Rect(0, 0, assets.ANCHO_PUERTA, assets.GROSOR_PUERTA)
        rect_s.center = (r.centerx, r.bottom)

        rect_e = pygame.Rect(0, 0, assets.GROSOR_PUERTA, assets.ANCHO_PUERTA)
        rect_e.center = (r.right, r.centery)

        rect_w = pygame.Rect(0, 0, assets.GROSOR_PUERTA, assets.ANCHO_PUERTA)
        rect_w.center = (r.left, r.centery)

        rects = {"N": rect_n, "S": rect_s, "E": rect_e, "W": rect_w}
        return {direccion: Puerta(direccion, rects[direccion]) for direccion in direcciones}

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
        """Sin enemigos en fase de combate: el cuarto final arranca el
        minijuego de decisión; uno intermedio solo queda limpio."""
        if self.fase == FASE_COMBATE and not self.enemigos:
            if not self.es_final:
                self.fase = FASE_LIMPIO
                return
            if self.permitir_decision is not None and not self.permitir_decision():
                return  # se reintenta cada frame (ver actualizar)
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
        else:
            self._verificar_fin_combate()

    def eliminar_un_enemigo(self):
        """Debug: quita un enemigo de la lista y refresca el estado de las puertas."""
        if self.enemigos:
            self.enemigos.pop()
            self._actualizar_estado_puertas()

    def manejar_evento(self, evento):
        if evento.type == pygame.KEYDOWN and evento.key == TECLA_DEBUG_ELIMINAR_ENEMIGO:
            self.eliminar_un_enemigo()

    def dibujar(self, pantalla):
        pygame.draw.rect(pantalla, assets.COLOR_MURO, self.rect, assets.GROSOR_MURO)

        for puerta in self.puertas.values():
            pygame.draw.rect(pantalla, puerta.color(), puerta.rect)
            if puerta.sellada and not puerta.bloqueada:
                # Una X sobre la puerta: cerrada por cuartos pendientes.
                r = puerta.rect
                for inicio, fin in ((r.topleft, r.bottomright), (r.bottomleft, r.topright)):
                    pygame.draw.line(
                        pantalla, assets.COLOR_X_PUERTA_SELLADA, inicio, fin,
                        assets.GROSOR_X_PUERTA_SELLADA,
                    )

        for enemigo in self.enemigos:
            enemigo.dibujar(pantalla)
