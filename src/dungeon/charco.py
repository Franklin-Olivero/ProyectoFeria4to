"""Charco tóxico de la fase 3 del jefe (lógica pura, sin Pygame).

Ciclo de vida, para que sea legible y esquivable:

    aviso  (CHARCO_AVISO s)     -> solo se dibuja el contorno, no daña
    activo (CHARCO_DURACION s)  -> relleno, daña por segundo a quien esté dentro
    después                     -> vivo = False, se descarta

El dibujo vive en src/dungeon/arena_jefe.py.
"""

from src.core.balance import (
    CHARCO_AVISO,
    CHARCO_DANIO_POR_SEGUNDO,
    CHARCO_DURACION,
    CHARCO_RADIO,
)


class Charco:
    def __init__(self, x, y, radio=CHARCO_RADIO):
        self.x = x
        self.y = y
        self.radio = radio
        self.tiempo = 0.0  # segundos desde que apareció

    @property
    def en_aviso(self):
        return self.tiempo < CHARCO_AVISO

    @property
    def activo(self):
        return CHARCO_AVISO <= self.tiempo < CHARCO_AVISO + CHARCO_DURACION

    @property
    def vivo(self):
        return self.tiempo < CHARCO_AVISO + CHARCO_DURACION

    def actualizar(self, dt):
        self.tiempo += dt

    def contiene(self, x, y):
        """True si el punto (x, y) está dentro del círculo."""
        return (x - self.x) ** 2 + (y - self.y) ** 2 <= self.radio**2

    def danio_para(self, x, y, dt):
        """Daño que recibe en este frame quien está en (x, y): 0 durante
        el aviso o fuera del charco; CHARCO_DANIO_POR_SEGUNDO * dt si no."""
        if self.activo and self.contiene(x, y):
            return CHARCO_DANIO_POR_SEGUNDO * dt
        return 0.0
