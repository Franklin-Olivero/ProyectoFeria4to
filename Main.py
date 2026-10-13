"""Punto de entrada del juego.

El flujo de la partida es una máquina de estados explícita (Escena):

    MAZMORRA --(último enemigo muere)--> DECISION --(resultado)--> MAZMORRA
    MAZMORRA --(B, si está desbloqueada)--> JEFE --(jefe muere)--> VICTORIA
    VICTORIA --(ENTER)--> MAZMORRA nueva       VICTORIA --(ESC)--> salir

El combate (MAZMORRA y JEFE) usa el mismo loop: el cuarto normal y la
arena del jefe exponen rect, enemigos, actualizar, dibujar y
manejar_evento. Solo el cuarto normal tiene minijuego de decisión.
"""

import sys
from enum import Enum

import pygame

from src.core import assets
from src.core.colapso import ColapsoElectoral
from src.core.config import FPS, crear_pantalla, crear_reloj
from src.core.equipo import registrar_kill_equipo
from src.dungeon.arena_jefe import ArenaJefe
from src.dungeon.cuarto import FASE_DECISION, FASE_RESUELTO, Cuarto
from src.dungeon.mazmorra_final import VICTORIA as MAZMORRA_FINAL_GANADA
from src.dungeon.mazmorra_final import esta_desbloqueada
from src.dungeon.progreso import ProgresoPartida
from src.entities.candidato import Candidato
from src.entities.influencer import Influencer
from src.entities.periodista import Periodista
from src.entities.player import Ciudadano
from src.ui.pantalla_victoria import dibujar_victoria
from src.ui.seleccion_rol import dibujar_seleccion
from src.ui.terminal_decision import CONFIRMAR, DERECHA, IZQUIERDA
from src.ui.terminal_decision_render import dibujar_terminal

TECLA_DISPARAR = pygame.K_SPACE
TECLA_HABILIDAD = pygame.K_f
TECLA_MAZMORRA_FINAL = pygame.K_b
TECLAS_CONFIRMAR = (pygame.K_RETURN, pygame.K_KP_ENTER)
TECLA_SALIR = pygame.K_ESCAPE

DISTANCIA_INICIO_JUGADOR = 40  # px desde el borde inferior del cuarto

# Teclas de la pantalla de selección -> clase del rol a instanciar.
ROLES_POR_TECLA = {
    pygame.K_1: Ciudadano,
    pygame.K_2: Influencer,
    pygame.K_3: Periodista,
    pygame.K_4: Candidato,
}

# Teclas de la terminal de decisión -> dirección de navegación.
TECLAS_TERMINAL = {
    pygame.K_LEFT: IZQUIERDA,
    pygame.K_RIGHT: DERECHA,
    pygame.K_RETURN: CONFIRMAR,
    pygame.K_KP_ENTER: CONFIRMAR,
}


class Escena(Enum):
    MAZMORRA = "mazmorra"  # combate en el cuarto normal (y paseo tras resolverlo)
    DECISION = "decision"  # terminal de decisión: input solo para la terminal
    JEFE = "jefe"  # combate en la arena del jefe final
    VICTORIA = "victoria"  # jefe derrotado: ENTER o ESC, sin combate


ESCENAS_DE_COMBATE = (Escena.MAZMORRA, Escena.JEFE)


def main():
    pygame.init()
    pantalla = crear_pantalla()
    reloj = crear_reloj()
    fuente_hud = pygame.font.Font(None, assets.TAMANIO_FUENTE_HUD)
    fuente_titulo = pygame.font.Font(None, assets.TAMANIO_FUENTE_TITULO_VICTORIA)
    colapso = ColapsoElectoral()
    progreso = ProgresoPartida()
    clase_rol = _elegir_rol(pantalla, reloj, fuente_hud)
    if clase_rol is None:
        pygame.quit()
        sys.exit()
    cuarto = Cuarto()
    jugador = clase_rol(0, 0)
    _colocar_en_cuarto(jugador, cuarto)
    # Todos los jugadores de la partida (por ahora solo uno); se usa para
    # repartir la carga compartida de equipo en cada kill.
    jugadores = [jugador]

    escena = Escena.MAZMORRA
    arena = None
    tiempo_mensaje_bloqueada = 0.0
    # Se dibuja el mundo aquí y se copia a la pantalla con la sacudida;
    # el HUD va directo a la pantalla para que no tiemble.
    lienzo = pygame.Surface(pantalla.get_size())

    proyectiles_jugador = []
    proyectiles_enemigos = []

    ejecutando = True
    while ejecutando:
        dt = reloj.tick(FPS) / 1000
        tiempo_mensaje_bloqueada = max(0.0, tiempo_mensaje_bloqueada - dt)
        # Lugar físico activo: la arena mientras dure la pelea final.
        escenario = arena if escena in (Escena.JEFE, Escena.VICTORIA) else cuarto

        # --- Input, según la escena ------------------------------------
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                ejecutando = False
            elif evento.type != pygame.KEYDOWN:
                continue
            elif escena == Escena.DECISION:
                if evento.key in TECLAS_TERMINAL:
                    cuarto.terminal.navegar(TECLAS_TERMINAL[evento.key])
            elif escena == Escena.VICTORIA:
                if evento.key in TECLAS_CONFIRMAR:
                    # Nuevo ciclo: mazmorra nueva, colapso y progreso se conservan.
                    cuarto = Cuarto()
                    arena = None
                    escena = Escena.MAZMORRA
                    escenario = cuarto
                    jugador.vida = jugador.vida_maxima
                    jugador.invulnerabilidad.reiniciar()
                    _colocar_en_cuarto(jugador, cuarto)
                    proyectiles_jugador.clear()
                    proyectiles_enemigos.clear()
                elif evento.key == TECLA_SALIR:
                    ejecutando = False
            elif evento.key == TECLA_HABILIDAD:
                if jugador.puede_usar_habilidad():
                    jugador.usar_habilidad(escenario.enemigos, proyectiles_jugador)
            elif evento.key == TECLA_MAZMORRA_FINAL and escena == Escena.MAZMORRA:
                if esta_desbloqueada(colapso, progreso.mazmorras_completadas):
                    arena = ArenaJefe(colapso, jugador)
                    escena = Escena.JEFE
                    escenario = arena
                    proyectiles_jugador.clear()
                    proyectiles_enemigos.clear()
                else:
                    tiempo_mensaje_bloqueada = assets.DURACION_MENSAJE
            else:
                escenario.manejar_evento(evento)

        # --- Actualización, según la escena ----------------------------
        jugador.actualizar_habilidad(dt)

        if escena in ESCENAS_DE_COMBATE:
            _frame_de_combate(
                dt, jugador, jugadores, escenario, proyectiles_jugador, proyectiles_enemigos
            )
            if escena == Escena.MAZMORRA and cuarto.fase == FASE_DECISION:
                escena = Escena.DECISION
            elif escena == Escena.JEFE and arena.mazmorra.estado == MAZMORRA_FINAL_GANADA:
                escena = Escena.VICTORIA
        elif escena == Escena.DECISION:
            # El combate terminó: se descartan los proyectiles en vuelo.
            proyectiles_jugador.clear()
            proyectiles_enemigos.clear()
            cuarto.terminal.actualizar(dt)
            if cuarto.terminal.resultado is not None:
                progreso.registrar_decision(cuarto.terminal.resultado, colapso)
                cuarto.fase = FASE_RESUELTO
                escena = Escena.MAZMORRA
        # Escena.VICTORIA: el mundo queda quieto hasta ENTER o ESC.

        # --- Dibujo ----------------------------------------------------
        lienzo.fill(assets.COLOR_FONDO)
        escenario.dibujar(lienzo)
        jugador.dibujar(lienzo)
        for proyectil in proyectiles_jugador:
            proyectil.dibujar(lienzo)
        for proyectil in proyectiles_enemigos:
            proyectil.dibujar(lienzo)
        sacudida = arena.mazmorra.desplazamiento_sacudida() if escena == Escena.JEFE else (0, 0)
        pantalla.fill(assets.COLOR_FONDO)
        pantalla.blit(lienzo, sacudida)

        if escena == Escena.DECISION:
            dibujar_terminal(pantalla, cuarto.terminal, fuente_hud)
        if escena == Escena.VICTORIA:
            dibujar_victoria(pantalla, fuente_titulo, fuente_hud)
        # El resultado de la decisión solo tiene sentido en su propio cuarto,
        # y la barra del jefe solo mientras se pelea (no en la victoria).
        _dibujar_hud(pantalla, fuente_hud, colapso, jugador, cuarto, escenario is cuarto)
        if escena == Escena.JEFE:
            arena.dibujar_hud(pantalla, fuente_hud)
        if tiempo_mensaje_bloqueada > 0:
            texto = fuente_hud.render(
                "Mazmorra final: Bloqueada", True, assets.COLOR_MENSAJE_DERROTA
            )
            pantalla.blit(texto, assets.POSICION_MENSAJE_BLOQUEADA)
        pygame.display.flip()

    pygame.quit()
    sys.exit()


def _frame_de_combate(dt, jugador, jugadores, escenario, proyectiles_jugador, proyectiles_enemigos):
    """Un frame de combate, igual en el cuarto normal y en la arena."""
    jugador.actualizar_invulnerabilidad(dt)
    teclas = pygame.key.get_pressed()
    jugador.manejar_movimiento(teclas, dt, escenario.rect)
    # Disparo sostenido: el jugador decide cuántos volleys salen según
    # su cooldown (cadencia del rol + buff por kill).
    proyectiles_jugador.extend(jugador.actualizar_disparo(dt, teclas[TECLA_DISPARAR]))
    escenario.actualizar(dt, jugador, proyectiles_enemigos)

    _actualizar_proyectiles(proyectiles_jugador, dt, escenario.rect)
    _actualizar_proyectiles(proyectiles_enemigos, dt, escenario.rect)

    _resolver_colisiones_contra_enemigos(
        proyectiles_jugador, escenario.enemigos, jugador, jugadores
    )
    _resolver_colision_contra_jugador(proyectiles_enemigos, jugador)


def _colocar_en_cuarto(jugador, cuarto):
    jugador.rect.center = (cuarto.rect.centerx, cuarto.rect.bottom - DISTANCIA_INICIO_JUGADOR)
    jugador.posicion.update(jugador.rect.center)


def _elegir_rol(pantalla, reloj, fuente):
    """Pantalla previa al loop: espera 1-4 y retorna la clase elegida
    (None si se cierra la ventana)."""
    fuente_stats = pygame.font.Font(None, assets.TAMANIO_FUENTE_SELECCION)
    clases_rol = list(ROLES_POR_TECLA.values())
    while True:
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                return None
            if evento.type == pygame.KEYDOWN and evento.key in ROLES_POR_TECLA:
                return ROLES_POR_TECLA[evento.key]

        pantalla.fill(assets.COLOR_FONDO)
        dibujar_seleccion(pantalla, clases_rol, fuente, fuente_stats)
        pygame.display.flip()
        reloj.tick(FPS)


def _dibujar_hud(pantalla, fuente, colapso, jugador, cuarto, mostrar_resultado):
    texto_colapso = fuente.render(colapso.texto(), True, assets.COLOR_TEXTO_HUD)
    pantalla.blit(texto_colapso, assets.POSICION_TEXTO_COLAPSO)

    texto_carga = fuente.render(
        f"Carga: {jugador.carga_habilidad:g}/{jugador.carga_maxima}",
        True,
        assets.COLOR_TEXTO_HUD,
    )
    pantalla.blit(texto_carga, assets.POSICION_TEXTO_CARGA)

    if mostrar_resultado and cuarto.fase == FASE_RESUELTO:
        texto_resultado = fuente.render(
            f"Resultado: {cuarto.terminal.resultado}", True, assets.COLOR_TEXTO_HUD
        )
        pantalla.blit(texto_resultado, assets.POSICION_TEXTO_RESULTADO)


def _actualizar_proyectiles(proyectiles, dt, limites):
    for proyectil in proyectiles:
        proyectil.actualizar(dt, limites)
    proyectiles[:] = [proyectil for proyectil in proyectiles if proyectil.vivo]


def _resolver_colisiones_contra_enemigos(proyectiles, enemigos, jugador, jugadores):
    """Delega cada choque en `proyectil.al_impactar(enemigo)`, que cada
    tipo de proyectil del rol define (destruirse, perforar, empujar,
    área...). Cada enemigo que muere da la kill completa a `jugador` y
    carga compartida al resto de `jugadores` (ver src/core/equipo.py)."""
    for proyectil in proyectiles:
        for enemigo in enemigos:
            if not proyectil.vivo:
                break
            if enemigo.vivo and proyectil.colisiona_con(enemigo.rect):
                proyectil.al_impactar(enemigo)
                if not enemigo.vivo:
                    registrar_kill_equipo(jugador, jugadores)


def _resolver_colision_contra_jugador(proyectiles, jugador):
    """Un proyectil hostil que toca al jugador se consume siempre; si el
    jugador está invulnerable, recibir_dano() no le resta vida."""
    for proyectil in proyectiles:
        if proyectil.colisiona_con(jugador.rect):
            jugador.recibir_dano(proyectil.danio)
            proyectil.vivo = False


if __name__ == "__main__":
    main()
