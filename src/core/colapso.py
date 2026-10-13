"""Variable global de Colapso Electoral (sin dependencias de Pygame).

Barra 0.0%-100.0%: sube +0.2 por cada incursión fallida o muerte del
equipo en una mazmorra y baja -0.1 por cada mazmorra purificada.
Todavía no persiste entre ejecuciones.
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

    def texto(self):
        return f"Colapso: {self.valor:.1f}%"
