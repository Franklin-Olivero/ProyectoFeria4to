"""Árbol de comportamiento (behavior tree) implementado a mano, sin
librerías de terceros, para gobernar la IA de los enemigos.

Un behavior tree se re-evalúa completo una vez por frame ("tick").
Cada nodo retorna uno de tres estados:
    - EXITO: el nodo cumplió su objetivo.
    - FALLO: el nodo no pudo cumplir su objetivo.
    - EN_PROGRESO: el nodo sigue trabajando y debe volver a evaluarse
      en el próximo tick (útil para acciones que toman varios frames).

Este módulo no importa pygame: es lógica de decisión pura, reutilizable
y comprobable de forma aislada (ver tests/test_behavior_tree.py).
"""

EXITO = "SUCCESS"
FALLO = "FAILURE"
EN_PROGRESO = "RUNNING"


class Node:
    """Clase base abstracta de todo nodo del árbol de comportamiento."""

    def tick(self):
        """Evalúa el nodo para el frame actual.

        Retorna EXITO, FALLO o EN_PROGRESO. Las subclases deben
        sobreescribir este método.
        """
        raise NotImplementedError


class Selector(Node):
    """Nodo "OR": prueba a sus hijos en orden hasta que uno tenga éxito.

    Recorre `hijos` de izquierda a derecha y les hace tick():
        - Si un hijo retorna EXITO, el Selector corta ahí mismo y
          retorna EXITO (los hijos son alternativas, no pasos
          obligatorios, así que no tiene sentido seguir probando).
        - Si un hijo retorna EN_PROGRESO, el Selector retorna
          EN_PROGRESO de inmediato (ese hijo sigue "ocupando" el turno).
        - Si todos los hijos retornan FALLO, el Selector retorna FALLO.

    Complejidad por tick: O(k) en el peor caso (todos fallan), con k la
    cantidad de hijos directos; O(1) en el mejor caso (el primero tiene
    éxito).
    """

    def __init__(self, hijos):
        self.hijos = hijos

    def tick(self):
        for hijo in self.hijos:
            estado = hijo.tick()
            if estado in (EXITO, EN_PROGRESO):
                return estado
        return FALLO


class Sequence(Node):
    """Nodo "AND": ejecuta a sus hijos en orden mientras todos tengan éxito.

    Recorre `hijos` de izquierda a derecha y les hace tick():
        - Si un hijo retorna FALLO, la Sequence corta ahí mismo y
          retorna FALLO (son pasos obligatorios: si uno falla, no tiene
          sentido ejecutar los siguientes).
        - Si un hijo retorna EN_PROGRESO, la Sequence retorna
          EN_PROGRESO de inmediato.
        - Si todos los hijos retornan EXITO, la Sequence retorna EXITO.

    Complejidad por tick: O(k) en el peor caso (todos tienen éxito), con
    k la cantidad de hijos directos; O(1) en el mejor caso (el primero
    falla).
    """

    def __init__(self, hijos):
        self.hijos = hijos

    def tick(self):
        for hijo in self.hijos:
            estado = hijo.tick()
            if estado in (FALLO, EN_PROGRESO):
                return estado
        return EXITO


class Action(Node):
    """Nodo hoja: envuelve una función callback sin argumentos.

    El callback debe retornar EXITO, FALLO o EN_PROGRESO (las
    constantes de este módulo). Es el único tipo de nodo que ejecuta
    lógica de juego real; Selector y Sequence solo combinan resultados
    de sus hijos.
    """

    def __init__(self, callback):
        self.callback = callback

    def tick(self):
        return self.callback()
