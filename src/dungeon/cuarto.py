"""Lógica y dibujo de un cuarto de mazmorra: puertas y enemigos.

Comportamiento real: mientras existan enemigos VIVOS en el cuarto, las
4 puertas (N, S, E, W) permanecen bloqueadas; en cuanto el último
enemigo muere, las puertas se abren. Los enemigos traen su propia IA
(árbol de comportamiento, ver src/entities/enemy.py); este módulo solo
los posiciona y decide el estado de las puertas.

Cuántos enemigos aparecen y qué tan rápidos son NO es fijo: al crear el
cuarto se clasifican los reportes de toxicidad de la zona con el árbol
N-ario (ver src/dungeon/clasificador_toxicidad.py) y el nivel
resultante decide la dificultad. De qué tipo es cada uno (perseguidor,
tirador, curandero) lo decide composicion_cuarto
(src/entities/tipos_enemigo.py) según ese tramo, y dónde aparece,
posiciones_spawn (src/dungeon/spawn.py): siempre a una distancia segura
del punto por donde entra el jugador, con los curanderos más atrás.

Mientras `congelado` sea True (gracia de entrada, la pone la mazmorra
jugable) todos sus enemigos quedan quietos.

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

import random

import pygame

from src.core import assets
from src.core.equipo import jugador_mas_cercano
from src.dungeon.clasificador_toxicidad import (
    calcular_nivel_toxicidad,
    construir_arbol_reportes,
    nivel_a_dificultad,
)
from src.dungeon.spawn import posiciones_spawn
from src.entities.enemigos import crear_enemigo
from src.entities.tipos_enemigo import composicion_cuarto
from src.entities.variantes_enemigo import elegir_variantes
from src.ui import cuarto_render, temas_mazmorra
from src.ui.terminal_decision import TerminalDecision, construir_arbol_publicacion

ANCHO_CUARTO = assets.ANCHO_CUARTO
ALTO_CUARTO = assets.ALTO_CUARTO

TECLA_DEBUG_ELIMINAR_ENEMIGO = pygame.K_k

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


def centro_puerta(rect_cuarto, direccion):
    """Centro de la puerta `direccion` sobre el borde del cuarto."""
    r = rect_cuarto
    return {"N": (r.centerx, r.top), "S": (r.centerx, r.bottom),
            "E": (r.right, r.centery), "W": (r.left, r.centery)}[direccion]


# Dirección de la puerta -> hacia dónde queda el interior del cuarto.
HACIA_ADENTRO = {"N": (0, 1), "S": (0, -1), "E": (-1, 0), "W": (1, 0)}


def punto_llegada(rect_cuarto, direccion):
    """Dónde aparece el jugador al entrar por la puerta `direccion`:
    DISTANCIA_APARICION_PUERTA px hacia dentro desde su centro."""
    x, y = centro_puerta(rect_cuarto, direccion)
    dx, dy = HACIA_ADENTRO[direccion]
    distancia = assets.DISTANCIA_APARICION_PUERTA
    return (x + dx * distancia, y + dy * distancia)


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
        punto_entrada=None,
        rng=None,
        es_cuarto_inicial=False,
        usos_variantes=None,
        fabrica_arbol=None,
        semilla_visual=0,
        duracion_terminal=None,
    ):
        self.nombre_zona = nombre_zona
        self.rect = pygame.Rect(0, 0, ANCHO_CUARTO, ALTO_CUARTO)
        self.rect.center = assets.CENTRO_CUARTO

        if nivel_toxicidad is None:
            nivel_toxicidad = calcular_nivel_toxicidad(construir_arbol_reportes(reportes, nombre_zona))
        self.nivel_toxicidad = nivel_toxicidad
        self.dificultad = dificultad if dificultad is not None else nivel_a_dificultad(nivel_toxicidad)
        self.es_final = es_final
        # Defensa extra: función sin argumentos que dice si la decisión
        # puede empezar (la mazmorra exige el sello cumplido). None = sí.
        self.permitir_decision = permitir_decision
        # Quién arma el árbol de la terminal al abrirse (modo historia:
        # el escenario de la zona con la evidencia reunida). None = el
        # árbol fijo "Publicación Viral" de siempre.
        self.fabrica_arbol = fabrica_arbol if fabrica_arbol is not None else construir_arbol_publicacion
        self.semilla_visual = semilla_visual  # distingue el arte de cada cuarto de la mazmorra
        self.duracion_terminal = duracion_terminal

        self.fase = FASE_COMBATE
        self.terminal = None
        self.congelado = False  # gracia de entrada (ver gracia_entrada.py)

        self.puertas = self._crear_puertas(direcciones_puertas)
        # Veces que cada variante apareció en la mazmorra (la comparte la
        # mazmorra para que cada cuarto traiga caras distintas).
        self.usos_variantes = usos_variantes if usos_variantes is not None else {}
        self.enemigos = self._crear_enemigos_iniciales(
            punto_entrada if punto_entrada is not None else self.rect.center,
            rng if rng is not None else random.Random(),
            es_cuarto_inicial,
        )
        self._actualizar_estado_puertas()

    def _crear_puertas(self, direcciones):
        rects = {}
        for direccion in DIRECCIONES:
            horizontal = direccion in ("N", "S")
            ancho, alto = ((assets.ANCHO_PUERTA, assets.GROSOR_PUERTA) if horizontal
                           else (assets.GROSOR_PUERTA, assets.ANCHO_PUERTA))
            rects[direccion] = pygame.Rect(0, 0, ancho, alto)
            rects[direccion].center = centro_puerta(self.rect, direccion)
        return {direccion: Puerta(direccion, rects[direccion]) for direccion in direcciones}

    def _crear_enemigos_iniciales(self, punto_entrada, rng, es_cuarto_inicial):
        """Tipos según composicion_cuarto y posiciones según
        posiciones_spawn (lejos de `punto_entrada`). Las posiciones vienen
        de la más cercana a la más lejana y los tipos con los curanderos
        al final: así los curanderos quedan detrás de los demás.

        La velocidad base es la de assets por el `multiplicador_velocidad`
        de la dificultad; cada tipo la multiplica por la suya.
        """
        tipos = composicion_cuarto(self.dificultad, self.es_final, rng, es_cuarto_inicial)
        r = self.rect
        posiciones = posiciones_spawn((r.left, r.top, r.right, r.bottom), punto_entrada, len(tipos), rng)
        velocidad = assets.VELOCIDAD_ENEMIGO * self.dificultad["multiplicador_velocidad"]
        variantes = elegir_variantes(tipos, rng, self.usos_variantes)
        return [crear_enemigo(tipo, x, y, velocidad, variante=variante)
                for tipo, variante, (x, y) in zip(tipos, variantes, posiciones)]

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
            if self.duracion_terminal is None:
                self.terminal = TerminalDecision(self.fabrica_arbol())
            else:
                self.terminal = TerminalDecision(self.fabrica_arbol(), self.duracion_terminal, descender_resultados=True)
            self.terminal.iniciar()

    def actualizar(self, dt, jugadores, proyectiles_enemigos):
        """Corre un tick de IA para cada enemigo vivo y refresca las puertas.

        Cada enemigo apunta al jugador en pie más cercano (en solitario,
        siempre el único). `proyectiles_enemigos` es la lista de salida
        donde los enemigos agregan los proyectiles que disparan (ver
        Enemigo._disparar_a_objetivo).
        """
        for enemigo in self.enemigos:
            enemigo.congelado = self.congelado
            enemigo.aliados = self.enemigos
            objetivo = jugador_mas_cercano(enemigo.rect.center, jugadores)
            enemigo.actualizar(dt, objetivo, proyectiles_enemigos)
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
        # Piso, muros y grafitis (cacheados por cuarto): más grafitis a
        # mayor toxicidad. La semilla fija hace que cada cuarto conserve
        # sus manchas al volver a él.
        semilla = round(self.nivel_toxicidad * 100) + len(self.puertas) * 7
        grafitis = 1 + int(self.nivel_toxicidad // 35)
        tema = assets.TEMA_POR_ZONA.get(self.nombre_zona)
        if tema is not None:
            # Escenario propio del lugar: cada cuarto se pinta una vez y se reconoce.
            self.reloj_visual = pygame.time.get_ticks() / 1000.0
            fondo = temas_mazmorra.fondo(self.rect, tema, self.semilla_visual, tuple(self.puertas), self.nivel_toxicidad)
            pantalla.blit(fondo, (0, assets.Y_MUNDO_TEMA))
            temas_mazmorra.dibujar_animado(pantalla, self.rect, tema, self.reloj_visual)
        else:
            fondo = cuarto_render.fondo_cuarto(self.rect, semilla, grafitis)
            pantalla.blit(fondo, cuarto_render.origen_fondo(self.rect))

        for puerta in self.puertas.values():
            cuarto_render.dibujar_puerta(pantalla, puerta, self.rect)

        if self.es_final:
            cuarto_render.dibujar_terminal_cuarto(
                pantalla, self.rect, bloqueada=bool(self.enemigos), cantidad_enemigos=len(self.enemigos)
            )

        for enemigo in self.enemigos:
            enemigo.dibujar(pantalla)
