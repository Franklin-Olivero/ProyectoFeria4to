"""Punto de entrada del juego."""

import sys

import pygame

from src.core.config import COLOR_FONDO, FPS, crear_pantalla, crear_reloj
from src.dungeon.cuarto import Cuarto
from src.entities.player import Jugador

TECLA_DISPARAR = pygame.K_SPACE


def main():
    pygame.init()
    pantalla = crear_pantalla()
    reloj = crear_reloj()
    cuarto = Cuarto()
    jugador = Jugador(cuarto.rect.centerx, cuarto.rect.bottom - 40)

    proyectiles_jugador = []
    proyectiles_enemigos = []

    ejecutando = True
    while ejecutando:
        dt = reloj.tick(FPS) / 1000

        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                ejecutando = False
            elif evento.type == pygame.KEYDOWN and evento.key == TECLA_DISPARAR:
                proyectiles_jugador.extend(jugador.disparar_abanico())
            else:
                cuarto.manejar_evento(evento)

        teclas = pygame.key.get_pressed()
        jugador.manejar_movimiento(teclas, dt, cuarto.rect)
        cuarto.actualizar(dt, jugador, proyectiles_enemigos)

        _actualizar_proyectiles(proyectiles_jugador, dt, cuarto.rect)
        _actualizar_proyectiles(proyectiles_enemigos, dt, cuarto.rect)

        _resolver_colisiones_contra_enemigos(proyectiles_jugador, cuarto.enemigos)
        _resolver_colision_contra_jugador(proyectiles_enemigos, jugador)

        pantalla.fill(COLOR_FONDO)
        cuarto.dibujar(pantalla)
        jugador.dibujar(pantalla)
        for proyectil in proyectiles_jugador:
            proyectil.dibujar(pantalla)
        for proyectil in proyectiles_enemigos:
            proyectil.dibujar(pantalla)
        pygame.display.flip()

    pygame.quit()
    sys.exit()


def _actualizar_proyectiles(proyectiles, dt, limites):
    for proyectil in proyectiles:
        proyectil.actualizar(dt, limites)
    proyectiles[:] = [proyectil for proyectil in proyectiles if proyectil.vivo]


def _resolver_colisiones_contra_enemigos(proyectiles, enemigos):
    for proyectil in proyectiles:
        if not proyectil.vivo:
            continue
        for enemigo in enemigos:
            if enemigo.vivo and proyectil.colisiona_con(enemigo.rect):
                enemigo.recibir_dano(proyectil.danio)
                proyectil.vivo = False
                break


def _resolver_colision_contra_jugador(proyectiles, jugador):
    for proyectil in proyectiles:
        if proyectil.colisiona_con(jugador.rect):
            jugador.recibir_dano(proyectil.danio)
            proyectil.vivo = False


if __name__ == "__main__":
    main()
