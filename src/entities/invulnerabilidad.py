"""Ventana de invulnerabilidad tras recibir un golpe ("i-frames", sin Pygame).

Cuando un golpe entra, el jugador queda invulnerable
INVULNERABILIDAD_DURACION segundos: ningún daño le resta vida en ese
tiempo. La ventana no se acumula: un golpe bloqueado no la reinicia,
así que nunca se encadena una invulnerabilidad infinita.

Todos los roles la usan a través de JugadorBase.recibir_dano(), en el
cuarto normal y en la arena del jefe.
"""

from src.core import assets
from src.core.balance import INVULNERABILIDAD_DURACION


class Invulnerabilidad:
    def __init__(self, duracion=INVULNERABILIDAD_DURACION):
        self.duracion = duracion
        self.tiempo_restante = 0.0

    @property
    def activa(self):
        return self.tiempo_restante > 0

    def actualizar(self, dt):
        self.tiempo_restante = max(0.0, self.tiempo_restante - dt)

    def aplicar_golpe(self, vida, danio, inicia=True):
        """Retorna la vida que queda tras un golpe de `danio`.

        Con la ventana activa el golpe no resta nada (y no la reinicia).
        Si el golpe entra y `inicia` es True, abre la ventana. Los
        charcos usan inicia=False: respetan la ventana, pero su daño
        continuo no la abre (si no, un charco haría daño una sola vez
        cada 0.6 s).
        """
        if self.activa:
            return vida
        if inicia:
            self.tiempo_restante = self.duracion
        return vida - danio

    @property
    def visible(self):
        """Parpadeo: durante la ventana alterna visible/invisible cada
        PERIODO_PARPADEO_INVULNERABLE segundos."""
        if not self.activa:
            return True
        transcurrido = self.duracion - self.tiempo_restante
        return int(transcurrido / assets.PERIODO_PARPADEO_INVULNERABLE) % 2 == 0

    def reiniciar(self):
        self.tiempo_restante = 0.0
