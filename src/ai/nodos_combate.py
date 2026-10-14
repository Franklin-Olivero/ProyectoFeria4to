"""Nodos de behavior tree para los tipos de enemigo (lógica pura, sin Pygame).

Complementan a Selector/Sequence/Action de src/ai/behavior_tree.py con
nodos reutilizables. Cada uno trabaja sobre un "agente" por duck typing
(no importan ninguna clase de entities/), así se prueban con un objeto
falso cualquiera. Lo que cada nodo le pide al agente:

    xy, objetivo_xy        posiciones (x, y) del agente y de su objetivo
    dt                     segundos del frame actual
    mover(dx, dy, factor)  avanzar en la dirección unitaria (dx, dy) a
                           `factor` veces su velocidad durante dt
    recarga_disparo, telegrafia, disparar_hacia_objetivo()   (DispararApuntado)
    cooldown_cura, aliados, al_curar(aliado)                  (CurarAliado)

Los nodos de acción que tienen cooldown retornan EXITO aunque estén
esperando, para que la Sequence que los contiene no se corte (misma
regla que Enemigo._disparar_a_objetivo).
"""

import math

from src.ai.behavior_tree import EXITO, FALLO, Node


def distancia(a, b):
    return math.dist(a, b)


def direccion(desde, hacia):
    """Vector unitario (dx, dy) de `desde` a `hacia`; (0, 0) si coinciden."""
    dx, dy = hacia[0] - desde[0], hacia[1] - desde[1]
    largo = math.hypot(dx, dy)
    if largo == 0:
        return (0.0, 0.0)
    return (dx / largo, dy / largo)


def punto_detras(aliados_xy, jugador_xy, separacion):
    """Punto `separacion` px detrás del centro de los aliados, en la
    dirección opuesta al jugador: donde se esconde el curandero. Sin
    aliados retorna None."""
    if not aliados_xy:
        return None
    cx = sum(x for x, _ in aliados_xy) / len(aliados_xy)
    cy = sum(y for _, y in aliados_xy) / len(aliados_xy)
    dx, dy = direccion(jugador_xy, (cx, cy))
    return (cx + dx * separacion, cy + dy * separacion)


class DistanciaMenorQue(Node):
    """Condición: EXITO si el agente está a menos de `umbral` px de su objetivo."""

    def __init__(self, agente, umbral):
        self.agente = agente
        self.umbral = umbral

    def tick(self):
        return EXITO if distancia(self.agente.xy, self.agente.objetivo_xy) < self.umbral else FALLO


class Huir(Node):
    """Acción: se aleja de su objetivo a su velocidad. Siempre EXITO."""

    def __init__(self, agente):
        self.agente = agente

    def tick(self):
        dx, dy = direccion(self.agente.objetivo_xy, self.agente.xy)
        self.agente.mover(dx, dy)
        return EXITO


class MantenerDistancia(Node):
    """Acción: mantiene `rango` ± `tolerancia` px al objetivo. Más cerca,
    retrocede; más lejos, se acerca; dentro de la banda, orbita
    (perpendicular) a `factor_orbita` de su velocidad. Siempre EXITO."""

    def __init__(self, agente, rango, tolerancia, factor_orbita):
        self.agente = agente
        self.rango = rango
        self.tolerancia = tolerancia
        self.factor_orbita = factor_orbita

    def tick(self):
        a = self.agente
        d = distancia(a.xy, a.objetivo_xy)
        hacia_x, hacia_y = direccion(a.xy, a.objetivo_xy)
        if d < self.rango - self.tolerancia:
            a.mover(-hacia_x, -hacia_y)
        elif d > self.rango + self.tolerancia:
            a.mover(hacia_x, hacia_y)
        else:
            a.mover(-hacia_y, hacia_x, self.factor_orbita)
        return EXITO


class DispararApuntado(Node):
    """Acción con cadencia y telegrafía: cuando el cooldown llega a 0 el
    agente se "carga" `telegrafia_s` segundos (agente.telegrafia > 0,
    el render lo resalta) y recién entonces dispara hacia su objetivo y
    reinicia el cooldown a `cadencia_s`. Siempre EXITO."""

    def __init__(self, agente, cadencia_s, telegrafia_s):
        self.agente = agente
        self.cadencia_s = cadencia_s
        self.telegrafia_s = telegrafia_s

    def tick(self):
        a = self.agente
        if a.telegrafia > 0:
            a.telegrafia = max(0.0, a.telegrafia - a.dt)
            if a.telegrafia == 0:
                a.disparar_hacia_objetivo()
                a.recarga_disparo = self.cadencia_s
            return EXITO
        a.recarga_disparo = max(0.0, a.recarga_disparo - a.dt)
        if a.recarga_disparo == 0:
            a.telegrafia = self.telegrafia_s
        return EXITO


class CurarAliado(Node):
    """Acción: cada `intervalo_s`, cura `fraccion` de la vida máxima al
    aliado más herido dentro de `radio`. Nunca a sí mismo, nunca a algo
    sin `curable` (el jefe) y como mucho `max_curas` veces a cada aliado.
    Si no hay a quién curar, espera listo. Siempre EXITO."""

    def __init__(self, agente, intervalo_s, fraccion, radio, max_curas):
        self.agente = agente
        self.intervalo_s = intervalo_s
        self.fraccion = fraccion
        self.radio = radio
        self.max_curas = max_curas

    def candidatos(self):
        a = self.agente
        return [
            aliado for aliado in a.aliados
            if aliado is not a
            and getattr(aliado, "curable", False)
            and aliado.vivo
            and aliado.vida < aliado.vida_maxima
            and aliado.curaciones_recibidas < self.max_curas
            and distancia(a.xy, aliado.xy) <= self.radio
        ]

    def tick(self):
        a = self.agente
        a.cooldown_cura = max(0.0, a.cooldown_cura - a.dt)
        if a.cooldown_cura > 0:
            return EXITO
        heridos = self.candidatos()
        if not heridos:
            return EXITO
        objetivo = min(heridos, key=lambda aliado: aliado.vida / aliado.vida_maxima)
        objetivo.vida = min(objetivo.vida_maxima, objetivo.vida + objetivo.vida_maxima * self.fraccion)
        objetivo.curaciones_recibidas += 1
        a.al_curar(objetivo)
        a.cooldown_cura = self.intervalo_s
        return EXITO
