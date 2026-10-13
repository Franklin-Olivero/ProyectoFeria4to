"""Punto de entrada del juego."""

import sys

import pygame

from src.core import assets
from src.core.colapso import ColapsoElectoral
from src.core.config import COLOR_FONDO, FPS, crear_pantalla, crear_reloj
from src.core.equipo import registrar_kill_equipo
from src.dungeon.cuarto import FASE_DECISION, FASE_RESUELTO, Cuarto
from src.entities.candidato import Candidato
from src.entities.influencer import Influencer
from src.entities.periodista import Periodista
from src.entities.player import Ciudadano
from src.ui.terminal_decision import (
    CONFIRMAR,
    DERECHA,
    DETONACION,
    IZQUIERDA,
    PURIFICACION_EXITOSA,
)
from src.ui.seleccion_rol import dibujar_seleccion
from src.ui.terminal_decision_render import dibujar_terminal

TECLA_DISPARAR = pygame.K_SPACE
TECLA_HABILIDAD = pygame.K_f

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


def main():
    pygame.init()
    pantalla = crear_pantalla()
    reloj = crear_reloj()
    fuente_hud = pygame.font.Font(None, assets.TAMANIO_FUENTE_HUD)
    colapso = ColapsoElectoral()
    clase_rol = _elegir_rol(pantalla, reloj, fuente_hud)
    if clase_rol is None:
        pygame.quit()
        sys.exit()
    cuarto = Cuarto()
    jugador = clase_rol(cuarto.rect.centerx, cuarto.rect.bottom - 40)
    # Todos los jugadores de la partida (por ahora solo uno); se usa para
    # repartir la carga compartida de equipo en cada kill.
    jugadores = [jugador]

    proyectiles_jugador = []
    proyectiles_enemigos = []

    ejecutando = True
    while ejecutando:
        dt = reloj.tick(FPS) / 1000

        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                ejecutando = False
            elif cuarto.fase == FASE_DECISION:
                # Durante la decisión el input va a la terminal, no al jugador.
                if evento.type == pygame.KEYDOWN and evento.key in TECLAS_TERMINAL:
                    cuarto.terminal.navegar(TECLAS_TERMINAL[evento.key])
            elif evento.type == pygame.KEYDOWN and evento.key == TECLA_HABILIDAD:
                if jugador.puede_usar_habilidad():
                    jugador.usar_habilidad(cuarto.enemigos, proyectiles_jugador)
            else:
                cuarto.manejar_evento(evento)

        jugador.actualizar_habilidad(dt)

        if cuarto.fase == FASE_DECISION:
            # El combate terminó: se descartan los proyectiles en vuelo.
            proyectiles_jugador.clear()
            proyectiles_enemigos.clear()
            cuarto.terminal.actualizar(dt)
            _aplicar_resultado_decision(cuarto, colapso)
        else:
            teclas = pygame.key.get_pressed()
            jugador.manejar_movimiento(teclas, dt, cuarto.rect)
            # Disparo sostenido: el jugador decide cuántos volleys salen
            # según su cooldown (cadencia del rol + buff por kill).
            proyectiles_jugador.extend(
                jugador.actualizar_disparo(dt, teclas[TECLA_DISPARAR])
            )
            cuarto.actualizar(dt, jugador, proyectiles_enemigos)

            _actualizar_proyectiles(proyectiles_jugador, dt, cuarto.rect)
            _actualizar_proyectiles(proyectiles_enemigos, dt, cuarto.rect)

            _resolver_colisiones_contra_enemigos(
                proyectiles_jugador, cuarto.enemigos, jugador, jugadores
            )
            _resolver_colision_contra_jugador(proyectiles_enemigos, jugador)

        pantalla.fill(COLOR_FONDO)
        cuarto.dibujar(pantalla)
        jugador.dibujar(pantalla)
        for proyectil in proyectiles_jugador:
            proyectil.dibujar(pantalla)
        for proyectil in proyectiles_enemigos:
            proyectil.dibujar(pantalla)
        if cuarto.fase == FASE_DECISION:
            dibujar_terminal(pantalla, cuarto.terminal, fuente_hud)
        _dibujar_hud(pantalla, fuente_hud, colapso, jugador, cuarto)
        pygame.display.flip()

    pygame.quit()
    sys.exit()


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

        pantalla.fill(COLOR_FONDO)
        dibujar_seleccion(pantalla, clases_rol, fuente, fuente_stats)
        pygame.display.flip()
        reloj.tick(FPS)


def _aplicar_resultado_decision(cuarto, colapso):
    """Cuando la terminal llega a una hoja (o se acaba el tiempo), aplica
    el efecto sobre el Colapso Electoral y cierra la fase de decisión."""
    resultado = cuarto.terminal.resultado
    if resultado is None:
        return
    if resultado == PURIFICACION_EXITOSA:
        colapso.restar_exito()
    elif resultado == DETONACION:
        colapso.sumar_fallo()
    cuarto.fase = FASE_RESUELTO


def _dibujar_hud(pantalla, fuente, colapso, jugador, cuarto):
    texto_colapso = fuente.render(colapso.texto(), True, assets.COLOR_TEXTO_HUD)
    pantalla.blit(texto_colapso, assets.POSICION_TEXTO_COLAPSO)

    texto_carga = fuente.render(
        f"Carga: {jugador.carga_habilidad:g}/{jugador.carga_maxima}",
        True,
        assets.COLOR_TEXTO_HUD,
    )
    pantalla.blit(texto_carga, assets.POSICION_TEXTO_CARGA)

    if cuarto.fase == FASE_RESUELTO:
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
    for proyectil in proyectiles:
        if proyectil.colisiona_con(jugador.rect):
            jugador.recibir_dano(proyectil.danio)
            proyectil.vivo = False


if __name__ == "__main__":
    main()
