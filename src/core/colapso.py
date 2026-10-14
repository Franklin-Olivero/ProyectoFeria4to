"""Variable global de Colapso Electoral (sin dependencias de Pygame).

Barra 0.0%-100.0%: sube +0.2 por cada incursión fallida o muerte del
equipo en una mazmorra y baja -0.1 por cada mazmorra purificada.
Viajar por la ciudad también lo sube (`sumar`, costo de la ruta; ver
src/dungeon/partida.py). Si llega a 100% la partida se pierde
(`esta_colapsado()`): Main.py muestra la derrota global "Colapso total"
y ENTER reinicia la partida completa. Todavía no persiste entre
ejecuciones.
"""

COLAPSO_MINIMO = 0.0
COLAPSO_MAXIMO = 100.0
INCREMENTO_POR_FALLO = 0.2
DECREMENTO_POR_EXITO = 0.1


class ColapsoElectoral:
    """Porcentaje de colapso acotado siempre a [0.0, 100.0]."""

    def __init__(self, valor_inicial=COLAPSO_MINIMO):
        self.valor = self._acotar(valor_inicial)

    @staticmethod
    def _acotar(valor):
        return max(COLAPSO_MINIMO, min(COLAPSO_MAXIMO, valor))

    def sumar_fallo(self):
        """Incursión fallida o muerte del equipo: +0.2 (sin pasar de 100)."""
        self.valor = self._acotar(self.valor + INCREMENTO_POR_FALLO)

    def restar_exito(self):
        """Mazmorra purificada: -0.1 (sin bajar de 0)."""
        self.valor = self._acotar(self.valor - DECREMENTO_POR_EXITO)

    def sumar(self, cantidad):
        """Suma una cantidad arbitraria (p. ej. el costo de un viaje), acotada."""
        self.valor = self._acotar(self.valor + cantidad)

    def esta_colapsado(self):
        """True si la barra llegó al 100%: derrota global de la partida.

        Se compara con un decimal (el que muestra el HUD) porque sumar
        +0.2 en float puede dejar el valor en 99.9999... y no en 100.0.
        """
        return round(self.valor, 1) >= COLAPSO_MAXIMO

    def texto(self):
        return f"Colapso: {self.valor:.1f}%"
