"""Periodista: el rol que expone.

Ataque: rayo lineal perforante. No se destruye al primer impacto:
sigue en línea recta y daña una sola vez a cada enemigo que cruce.
Habilidad: Fact-Checking, un rayo perforante que además quita el
escudo de anonimato de cada enemigo alcanzado (antes de dañarlo), para
dejarlo vulnerable a daño normal.
"""

import pygame

from src.core import assets
from src.entities.player import JugadorBase
from src.entities.projectile import Proyectil


class RayoPerforante(Proyectil):
    """Proyectil rápido que atraviesa enemigos.

    Guarda los enemigos ya golpeados para no dañar al mismo varias
    veces mientras lo atraviesa (el choque dura varios frames).
    """

    def __init__(self, posicion, direccion, danio, quita_escudo=False):
        color = assets.COLOR_RAYO_FACT_CHECK if quita_escudo else assets.COLOR_RAYO_PERIODISTA
        super().__init__(
            posicion=posicion,
            direccion=direccion,
            velocidad=assets.VELOCIDAD_RAYO,
            danio=danio,
            color=color,
            tamanio=assets.TAMANIO_RAYO,
        )
        self.quita_escudo = quita_escudo
        self.golpeados = []

    def al_impactar(self, enemigo):
        if enemigo in self.golpeados:
            return
        self.golpeados.append(enemigo)
        if self.quita_escudo:
            enemigo.escudo_anonimato = False
        enemigo.recibir_dano(self.danio)
        # A diferencia del Proyectil base, sigue vivo: perfora.

    def dibujar(self, pantalla):
        cola = self.posicion - self.direccion * assets.LARGO_ESTELA_RAYO
        pygame.draw.line(pantalla, self.color, cola, self.posicion, assets.GROSOR_ESTELA_RAYO)
        super().dibujar(pantalla)


class Periodista(JugadorBase):
    rol = "periodista"
    COLOR = assets.COLOR_PERIODISTA
    NOMBRE = "Periodista"
    NOMBRE_HABILIDAD = "Fact-Checking"

    def ataque_basico(self):
        return [RayoPerforante(self.rect.center, self.direccion_mirada, self.danio)]

    def usar_habilidad(self, enemigos=(), proyectiles_salida=None):
        """Fact-Checking: dispara un rayo perforante que quita escudos."""
        if not self._gastar_carga():
            return False
        rayo = RayoPerforante(
            self.rect.center, self.direccion_mirada, self.danio, quita_escudo=True
        )
        if proyectiles_salida is not None:
            proyectiles_salida.append(rayo)
        return True
