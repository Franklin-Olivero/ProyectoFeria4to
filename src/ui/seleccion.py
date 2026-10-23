"""Menú de inicio: modo de juego y elección de rol (lógica pura, sin Pygame).

Flujo (lo maneja Main.py; el dibujo vive en src/ui/seleccion_rol.py):

    Modo: "1 jugador" / "2 jugadores"  --Enter-->  Roles  --todos listos-->  partida
                                       <--Esc---

En la pantalla de roles cada jugador tiene su propio cursor sobre las
4 tarjetas: lo mueve, confirma y puede arrepentirse mientras el otro
sigue eligiendo. La partida empieza cuando todos confirmaron. Dos
jugadores pueden elegir el mismo rol.
"""

from src.ui.terminal_decision import DERECHA, IZQUIERDA

UN_JUGADOR = 1
DOS_JUGADORES = 2
MODOS = (UN_JUGADOR, DOS_JUGADORES)


class SelectorModo:
    """Opción resaltada en la pantalla de modo (da la vuelta en los extremos)."""

    def __init__(self):
        self.indice = 0

    @property
    def seleccionado(self):
        return MODOS[self.indice]

    def mover(self, direccion):
        if direccion in (IZQUIERDA, DERECHA):
            self.indice = (self.indice + 1) % len(MODOS)

    def elegir(self, modo):
        self.indice = MODOS.index(modo)


class CursorRol:
    """Cursor de un jugador sobre las tarjetas de rol."""

    def __init__(self, cantidad_roles, inicial=0):
        self.cantidad = cantidad_roles
        self.indice = inicial
        self.confirmado = False

    def mover(self, direccion):
        """Solo se mueve mientras no haya confirmado."""
        if self.confirmado:
            return
        if direccion == IZQUIERDA:
            self.indice = (self.indice - 1) % self.cantidad
        elif direccion == DERECHA:
            self.indice = (self.indice + 1) % self.cantidad

    def confirmar(self):
        self.confirmado = True

    def cancelar(self):
        self.confirmado = False

    def elegir(self, indice):
        """Atajo (teclas 1-4): salta a esa tarjeta y confirma."""
        self.indice = indice
        self.confirmado = True


class SeleccionRoles:
    """Un cursor por jugador. J1 empieza en la primera tarjeta y J2 en la
    última, para que no arranquen encimados."""

    def __init__(self, cantidad_jugadores, cantidad_roles):
        self.cursores = [
            CursorRol(cantidad_roles, 0 if i == 0 else cantidad_roles - 1)
            for i in range(cantidad_jugadores)
        ]

    @property
    def lista(self):
        return all(cursor.confirmado for cursor in self.cursores)

    def indices(self):
        return [cursor.indice for cursor in self.cursores]
