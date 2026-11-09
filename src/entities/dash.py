"""Dash: desplazamiento corto y rápido con invulnerabilidad (sin Pygame).

Estado del dash de un jugador, como lógica pura para probarla aislada:

    iniciar(direccion)   arranca el dash si el cooldown lo permite y fija
                         la dirección (no cambia aunque el input cambie)
    actualizar(dt)       descuenta la duración y el cooldown

Mientras está activo, JugadorBase multiplica su velocidad por
`velocidad_multiplicador`, no dispara ni usa la habilidad
(`puede_disparar`) y no recibe daño si DASH_INVULNERABLE.

El cooldown cuenta desde el inicio del dash: con DASH_DURACION = 0.12 y
DASH_COOLDOWN = 5.0, entre el fin de un dash y el siguiente pasan 4.88 s.
`fraccion_cooldown` y `tiempo_listo` alimentan el indicador del HUD
(src/ui/hud.py), que no guarda estado propio.
Todas las operaciones son O(1).
"""

import math

from src.core.balance import DASH_COOLDOWN, DASH_DURACION, DASH_INVULNERABLE, DASH_VELOCIDAD_MULT


class Dash:
    def __init__(self):
        self.activo = False  # True durante el desplazamiento
        self.cooldown_restante = 0.0  # segundos hasta poder dashear de nuevo
        self.tiempo_restante = 0.0  # segundos que le quedan al dash actual
        self.direccion = (0.0, 0.0)  # unitaria, fijada al iniciar
        # Segundos desde que el cooldown terminó (para el destello del HUD).
        # Empieza "hace mucho": al arrancar la partida no hay destello.
        self.tiempo_listo = math.inf

    @property
    def disponible(self):
        return not self.activo and self.cooldown_restante <= 0

    def iniciar(self, direccion):
        """Inicia un dash hacia `direccion` (x, y). Retorna True si
        arrancó; False si está en cooldown, ya activo o la dirección es nula."""
        largo = math.hypot(direccion[0], direccion[1])
        if not self.disponible or largo == 0:
            return False
        self.direccion = (direccion[0] / largo, direccion[1] / largo)
        self.activo = True
        self.tiempo_restante = DASH_DURACION
        self.cooldown_restante = DASH_COOLDOWN
        return True

    def actualizar(self, dt):
        """Descuenta los timers; al acabarse la duración, el dash termina."""
        if self.cooldown_restante > 0:
            self.cooldown_restante = max(0.0, self.cooldown_restante - dt)
            if self.cooldown_restante == 0:
                self.tiempo_listo = 0.0  # recién disponible
        else:
            self.tiempo_listo += dt
        if self.activo:
            self.tiempo_restante -= dt
            if self.tiempo_restante <= 0:
                self.tiempo_restante = 0.0
                self.activo = False

    def reiniciar(self):
        self.__init__()

    @property
    def fraccion_cooldown(self):
        """0.0 = listo, 1.0 = recién usado. Para el indicador del HUD."""
        return self.cooldown_restante / DASH_COOLDOWN

    @property
    def velocidad_multiplicador(self):
        return DASH_VELOCIDAD_MULT if self.activo else 1.0

    @property
    def puede_disparar(self):
        """Durante el dash no se dispara ni se usa la habilidad."""
        return not self.activo

    @property
    def invulnerable(self):
        return self.activo and DASH_INVULNERABLE
