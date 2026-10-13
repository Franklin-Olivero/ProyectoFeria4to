"""Estado global de una partida (lógica pura, sin Pygame).

Agrupa lo que sobrevive entre mazmorras: el Colapso Electoral, el
progreso (mazmorras completadas), el mapa de la ciudad con sus pesos
dinámicos y la zona donde está el jugador. Main.py solo traduce teclas
a estas llamadas; así el viaje, la decisión y la derrota global se
pueden probar sin abrir ventana.
"""

from src.core.balance import COSTO_VIAJE_COLAPSO
from src.core.colapso import ColapsoElectoral
from src.dungeon.grafo_ciudad import ZONA_INICIO, GrafoCiudad
from src.dungeon.mazmorra_final import esta_desbloqueada
from src.dungeon.progreso import ProgresoPartida
from src.ui.terminal_decision import PURIFICACION_EXITOSA


class Partida:
    def __init__(self):
        self.reiniciar()

    def reiniciar(self):
        """Estado inicial: colapso 0, progreso 0, en la Plaza y la ciudad
        con sus pesos originales."""
        self.colapso = ColapsoElectoral()
        self.progreso = ProgresoPartida()
        self.ciudad = GrafoCiudad()
        self.ubicacion = ZONA_INICIO

    def alcaldia_desbloqueada(self):
        return esta_desbloqueada(self.colapso, self.progreso.mazmorras_completadas)

    def ruta_hasta(self, destino):
        """(camino, costo) más seguro desde la ubicación actual."""
        return self.ciudad.ruta_mas_segura(self.ubicacion, destino)

    def viajar(self, destino):
        """Cobra el viaje en colapso (COSTO_VIAJE_COLAPSO por unidad de
        costo de la ruta) y mueve al jugador. Retorna (camino, costo)."""
        camino, costo = self.ruta_hasta(destino)
        self.colapso.sumar(costo * COSTO_VIAJE_COLAPSO)
        self.ubicacion = destino
        return camino, costo

    def cerrar_mazmorra(self, mazmorra, resultado):
        """Único camino del juego para aplicar la decisión de una mazmorra
        normal: solo si `mazmorra.completar()` acepta (cuarto final con
        el sello cumplido y aún no completada). Así registrar_decision
        se aplica una sola vez por mazmorra. Retorna True si se aplicó."""
        if not mazmorra.completar():
            return False
        self.registrar_decision(mazmorra.nombre_zona, resultado)
        return True

    def registrar_decision(self, zona, resultado):
        """Resultado del minijuego de la mazmorra de `zona`: aplica
        colapso y progreso, y ajusta los pesos de las calles de la zona."""
        self.progreso.registrar_decision(resultado, self.colapso)
        self.ciudad.actualizar_tras_mazmorra(zona, resultado == PURIFICACION_EXITOSA)

    def hay_derrota_global(self):
        return self.colapso.esta_colapsado()
