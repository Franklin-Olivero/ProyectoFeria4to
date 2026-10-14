"""Segundo de gracia al entrar a un cuarto (lógica pura, sin Pygame).

Cada vez que el jugador entra a un cuarto (inicio de la mazmorra, cada
puerta cruzada y la arena del jefe) se llama a iniciar(). Mientras
`activa` sea True:
    - los enemigos del lugar quedan congelados (su behavior tree entra
      en la rama "congelado" antes que cualquier otra, incluso con
      agro_permanente): no persiguen, no disparan ni golpean;
    - el jugador solo puede moverse: no dispara ni usa la habilidad
      (Main.py le pone `armas_bloqueadas`).
Así nadie recibe daño en el instante de aparecer junto a la puerta.
"""

from src.core.balance import GRACIA_ENTRADA_CUARTO_S


class GraciaEntrada:
    def __init__(self, duracion=GRACIA_ENTRADA_CUARTO_S):
        self.duracion = duracion
        self.restante = 0.0

    def iniciar(self):
        """Arranca (o reinicia) la cuenta regresiva completa."""
        self.restante = self.duracion

    def actualizar(self, dt):
        self.restante = max(0.0, self.restante - dt)

    @property
    def activa(self):
        return self.restante > 0

    @property
    def fraccion(self):
        """1.0 al empezar, 0.0 al terminar (para el anillo de cuenta regresiva)."""
        return self.restante / self.duracion if self.duracion > 0 else 0.0
