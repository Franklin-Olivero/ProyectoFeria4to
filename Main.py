"""Punto de entrada del juego.

El flujo de la partida es una máquina de estados explícita (Escena,
src/core/escenas.py):

    MAPA_CIUDAD --(ENTER en una zona)--> MAZMORRA --(cuarto final limpio)--> DECISION
    DECISION --(resultado)--> MAPA_CIUDAD
    MAPA_CIUDAD --(ENTER en Alcaldía, si está desbloqueada)--> JEFE --(jefe muere)--> VICTORIA
    VICTORIA --(ENTER)--> MAPA_CIUDAD           VICTORIA --(ESC)--> salir
    cualquiera --(colapso al 100%)--> DERROTA --(ENTER)--> partida nueva en MAPA_CIUDAD

El combate (MAZMORRA y JEFE) usa el mismo loop: la mazmorra de varios
cuartos y la arena del jefe exponen rect, enemigos, actualizar,
dibujar y manejar_evento. Solo el cuarto final de una mazmorra normal
tiene minijuego de decisión.
"""

import sys

import pygame

from src.core import assets
from src.core.config import FPS, crear_pantalla, crear_reloj
from src.core.equipo import registrar_kill_equipo
from src.core.escenas import ESCENAS_DE_COMBATE, Escena, escena_tras_colapso
from src.dungeon.arena_jefe import ArenaJefe
from src.dungeon.cuarto import FASE_DECISION, FASE_RESUELTO
from src.dungeon.grafo_ciudad import ZONA_FINAL, ZONAS
from src.dungeon.mazmorra import Mazmorra
from src.dungeon.mazmorra_final import VICTORIA as MAZMORRA_FINAL_GANADA
from src.dungeon.mazmorra_jugable import MazmorraJugable
from src.dungeon.partida import Partida
from src.entities.candidato import Candidato
from src.entities.influencer import Influencer
from src.entities.periodista import Periodista
from src.entities.player import Ciudadano
from src.ui.mapa_ciudad import SelectorZona
from src.ui.mapa_ciudad_render import dibujar_mapa_ciudad
from src.ui.mapa_render import dibujar_minimapa
from src.ui.pantalla_derrota import dibujar_derrota
from src.ui.pantalla_victoria import dibujar_victoria
from src.ui.seleccion_rol import dibujar_seleccion
from src.ui.terminal_decision import CONFIRMAR, DERECHA, IZQUIERDA
from src.ui.terminal_decision_render import dibujar_terminal

TECLA_DISPARAR = pygame.K_SPACE
TECLA_HABILIDAD = pygame.K_f
TECLA_MINIMAPA = pygame.K_m
TECLAS_CONFIRMAR = (pygame.K_RETURN, pygame.K_KP_ENTER)
TECLA_SALIR = pygame.K_ESCAPE

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

# Teclas del mapa de la ciudad -> dirección para cambiar de zona.
TECLAS_MAPA = {
    pygame.K_LEFT: IZQUIERDA,
    pygame.K_RIGHT: DERECHA,
}


def main():
    pygame.init()
    pantalla = crear_pantalla()
    reloj = crear_reloj()
    fuente_hud = pygame.font.Font(None, assets.TAMANIO_FUENTE_HUD)
    fuente_titulo = pygame.font.Font(None, assets.TAMANIO_FUENTE_TITULO_VICTORIA)
    fuente_mapa = pygame.font.Font(None, assets.TAMANIO_FUENTE_MAPA)
    fuente_minimapa = pygame.font.Font(None, assets.TAMANIO_FUENTE_MINIMAPA)
    partida = Partida()
    clase_rol = _elegir_rol(pantalla, reloj, fuente_hud)
    if clase_rol is None:
        pygame.quit()
        sys.exit()
    jugador = clase_rol(0, 0)
    # Todos los jugadores de la partida (por ahora solo uno); se usa para
    # repartir la carga compartida de equipo en cada kill.
    jugadores = [jugador]
    selector = _nuevo_selector(partida)

    escena = Escena.MAPA_CIUDAD
    mazmorra = None  # MazmorraJugable de la zona que se está recorriendo
    arena = None
    mostrar_minimapa = True
    # Mensaje central del mapa: (texto, color) del último resultado o "Bloqueada".
    mensaje_mapa = None
    tiempo_mensaje_mapa = 0.0
    # Se dibuja el mundo aquí y se copia a la pantalla con la sacudida;
    # el HUD va directo a la pantalla para que no tiemble.
    lienzo = pygame.Surface(pantalla.get_size())

    proyectiles_jugador = []
    proyectiles_enemigos = []

    ejecutando = True
    while ejecutando:
        dt = reloj.tick(FPS) / 1000
        tiempo_mensaje_mapa = max(0.0, tiempo_mensaje_mapa - dt)

        # --- Input, según la escena ------------------------------------
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                ejecutando = False
            elif evento.type != pygame.KEYDOWN:
                continue
            elif escena == Escena.MAPA_CIUDAD:
                if evento.key in TECLAS_MAPA:
                    selector.mover(TECLAS_MAPA[evento.key])
                elif evento.key in TECLAS_CONFIRMAR:
                    destino = selector.seleccionada
                    if destino == ZONA_FINAL and not partida.alcaldia_desbloqueada():
                        mensaje_mapa = (f"{ZONA_FINAL}: Bloqueada", assets.COLOR_MENSAJE_DERROTA)
                        tiempo_mensaje_mapa = assets.DURACION_MENSAJE_MAPA
                        continue
                    partida.viajar(destino)
                    proyectiles_jugador.clear()
                    proyectiles_enemigos.clear()
                    _curar(jugador)
                    if destino == ZONA_FINAL:
                        arena = ArenaJefe(partida.colapso, jugador)
                        escena = Escena.JEFE
                    elif partida.ciudad.tiene_mazmorra_normal(destino):
                        mazmorra = MazmorraJugable(
                            Mazmorra(partida.ciudad.reportes(destino), destino)
                        )
                        mazmorra.colocar_en_entrada(jugador)
                        escena = Escena.MAZMORRA
                    # La Plaza no tiene mazmorra: solo se viaja hasta ella.
            elif escena == Escena.DECISION:
                if evento.key in TECLAS_TERMINAL:
                    mazmorra.cuarto.terminal.navegar(TECLAS_TERMINAL[evento.key])
            elif escena in (Escena.VICTORIA, Escena.DERROTA):
                if evento.key in TECLAS_CONFIRMAR:
                    if escena == Escena.DERROTA:
                        # Partida completa nueva, con el mismo rol.
                        partida.reiniciar()
                        jugador = type(jugador)(0, 0)
                        jugadores = [jugador]
                        selector = _nuevo_selector(partida)
                        mensaje_mapa = None
                    arena = None
                    mazmorra = None
                    escena = Escena.MAPA_CIUDAD
                    proyectiles_jugador.clear()
                    proyectiles_enemigos.clear()
                elif evento.key == TECLA_SALIR:
                    ejecutando = False
            elif evento.key == TECLA_HABILIDAD:
                if jugador.puede_usar_habilidad():
                    escenario = _escenario_activo(escena, arena, mazmorra)
                    jugador.usar_habilidad(escenario.enemigos, proyectiles_jugador)
            elif evento.key == TECLA_MINIMAPA and escena == Escena.MAZMORRA:
                mostrar_minimapa = not mostrar_minimapa
            else:
                _escenario_activo(escena, arena, mazmorra).manejar_evento(evento)

        # --- Actualización, según la escena ----------------------------
        escenario = _escenario_activo(escena, arena, mazmorra)
        jugador.actualizar_habilidad(dt)

        if escena in ESCENAS_DE_COMBATE:
            _frame_de_combate(
                dt, jugador, jugadores, escenario, proyectiles_jugador, proyectiles_enemigos
            )
            if escena == Escena.MAZMORRA:
                if mazmorra.cambio_de_cuarto:
                    proyectiles_jugador.clear()
                if mazmorra.cuarto.fase == FASE_DECISION:
                    escena = Escena.DECISION
            elif escena == Escena.JEFE and arena.mazmorra.estado == MAZMORRA_FINAL_GANADA:
                escena = Escena.VICTORIA
        elif escena == Escena.DECISION:
            # El combate terminó: se descartan los proyectiles en vuelo.
            proyectiles_jugador.clear()
            proyectiles_enemigos.clear()
            terminal = mazmorra.cuarto.terminal
            terminal.actualizar(dt)
            if terminal.resultado is not None:
                partida.registrar_decision(partida.ubicacion, terminal.resultado)
                mazmorra.cuarto.fase = FASE_RESUELTO
                mazmorra = None
                mensaje_mapa = (
                    f"{partida.ubicacion}: {terminal.resultado}",
                    assets.COLOR_TEXTO_HUD,
                )
                tiempo_mensaje_mapa = assets.DURACION_MENSAJE_MAPA
                escena = Escena.MAPA_CIUDAD
        # VICTORIA y DERROTA: el mundo queda quieto hasta ENTER o ESC.

        if escena != Escena.DERROTA:
            escena = escena_tras_colapso(escena, partida.colapso)

        # --- Dibujo ----------------------------------------------------
        pantalla.fill(assets.COLOR_FONDO)
        if escena in (Escena.MAPA_CIUDAD, Escena.DERROTA):
            dibujar_mapa_ciudad(pantalla, partida, selector.seleccionada, fuente_hud, fuente_mapa)
            _dibujar_hud_mapa(pantalla, fuente_hud, partida)
            if tiempo_mensaje_mapa > 0 and mensaje_mapa is not None and escena == Escena.MAPA_CIUDAD:
                texto, color = mensaje_mapa
                superficie = fuente_hud.render(texto, True, color)
                pantalla.blit(superficie, superficie.get_rect(center=assets.POSICION_MENSAJE_MAPA))
            if escena == Escena.DERROTA:
                dibujar_derrota(pantalla, fuente_titulo, fuente_hud)
            pygame.display.flip()
            continue

        escenario = _escenario_activo(escena, arena, mazmorra)
        lienzo.fill(assets.COLOR_FONDO)
        escenario.dibujar(lienzo)
        jugador.dibujar(lienzo)
        for proyectil in proyectiles_jugador:
            proyectil.dibujar(lienzo)
        for proyectil in proyectiles_enemigos:
            proyectil.dibujar(lienzo)
        sacudida = arena.mazmorra.desplazamiento_sacudida() if escena == Escena.JEFE else (0, 0)
        pantalla.blit(lienzo, sacudida)

        if escena == Escena.DECISION:
            dibujar_terminal(pantalla, mazmorra.cuarto.terminal, fuente_hud)
        if escena == Escena.VICTORIA:
            dibujar_victoria(pantalla, fuente_titulo, fuente_hud)
        _dibujar_hud(pantalla, fuente_hud, partida.colapso, jugador)
        if escena in (Escena.MAZMORRA, Escena.DECISION) and mostrar_minimapa:
            dibujar_minimapa(pantalla, mazmorra.mazmorra, fuente_minimapa)
        if escena == Escena.JEFE:
            arena.dibujar_hud(pantalla, fuente_hud)
        pygame.display.flip()

    pygame.quit()
    sys.exit()


def _frame_de_combate(dt, jugador, jugadores, escenario, proyectiles_jugador, proyectiles_enemigos):
    """Un frame de combate, igual en la mazmorra y en la arena."""
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


def _escenario_activo(escena, arena, mazmorra):
    """Lugar físico activo: la arena mientras dure la pelea final; si no,
    la mazmorra normal (None en el mapa)."""
    return arena if escena in (Escena.JEFE, Escena.VICTORIA) else mazmorra


def _nuevo_selector(partida):
    """Selector del mapa apuntando a la primera zona después de la ubicación."""
    selector = SelectorZona(ZONAS, partida.ubicacion)
    selector.mover(DERECHA)
    return selector


def _curar(jugador):
    """Cada mazmorra (normal o final) se empieza con la vida llena."""
    jugador.vida = jugador.vida_maxima
    jugador.invulnerabilidad.reiniciar()


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


def _dibujar_hud(pantalla, fuente, colapso, jugador):
    texto_colapso = fuente.render(colapso.texto(), True, assets.COLOR_TEXTO_HUD)
    pantalla.blit(texto_colapso, assets.POSICION_TEXTO_COLAPSO)

    texto_carga = fuente.render(
        f"Carga: {jugador.carga_habilidad:g}/{jugador.carga_maxima}",
        True,
        assets.COLOR_TEXTO_HUD,
    )
    pantalla.blit(texto_carga, assets.POSICION_TEXTO_CARGA)


def _dibujar_hud_mapa(pantalla, fuente, partida):
    lineas = [
        (partida.colapso.texto(), assets.POSICION_TEXTO_COLAPSO),
        (f"Ubicación: {partida.ubicacion}", assets.POSICION_TEXTO_UBICACION),
        (
            f"Completadas: {partida.progreso.mazmorras_completadas}",
            assets.POSICION_TEXTO_COMPLETADAS,
        ),
    ]
    for texto, posicion in lineas:
        pantalla.blit(fuente.render(texto, True, assets.COLOR_TEXTO_HUD), posicion)


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
