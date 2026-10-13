"""Punto de entrada del juego."""

import sys

import pygame

from src.core import assets
from src.core.colapso import ColapsoElectoral
from src.core.config import COLOR_FONDO, FPS, crear_pantalla, crear_reloj
from src.dungeon.cuarto import Cuarto
from src.entities.player import Jugador

TECLA_DISPARAR = pygame.K_SPACE


def main():
    pygame.init()
    pantalla = crear_pantalla()
    reloj = crear_reloj()
    fuente_hud = pygame.font.Font(None, assets.TAMANIO_FUENTE_HUD)
    colapso = ColapsoElectoral()
    cuarto = Cuarto()
    # Evita restar el éxito en cada frame una vez limpio el cuarto.
    cuarto_purificado = False
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

        # Cuarto limpio al 100% = mazmorra purificada (por ahora hay un
        # solo cuarto). sumar_fallo() se conectará cuando exista una
        # condición real de incursión fallida (minijuego del cuarto final).
        if not cuarto.enemigos and not cuarto_purificado:
            colapso.restar_exito()
            cuarto_purificado = True

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
        texto_colapso = fuente_hud.render(colapso.texto(), True, assets.COLOR_TEXTO_HUD)
        pantalla.blit(texto_colapso, assets.POSICION_TEXTO_COLAPSO)
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
