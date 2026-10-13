"""Cuerpo Pygame de una mazmorra normal de varios cuartos.

Envuelve a Mazmorra (lógica pura sobre el grafo, src/dungeon/mazmorra.py)
y le da un Cuarto físico a cada nodo:
    - crea el Cuarto la primera vez que se entra, con las puertas que
      dicta el grafo, la toxicidad/dificultad del nodo y si es el final;
    - guarda los cuartos ya creados, así un cuarto limpiado sigue limpio
      (sus enemigos no reaparecen) al volver a él;
    - detecta cuando el jugador toca una puerta ABIERTA, lo pasa al
      cuarto vecino y lo pone junto a la puerta opuesta;
    - informa a la Mazmorra si quedan enemigos vivos (propagación).

Expone la misma interfaz que Cuarto y ArenaJefe (rect, enemigos,
actualizar, dibujar, manejar_evento), así Main.py usa el mismo loop.
"""

from src.core import assets
from src.dungeon.cuarto import Cuarto
from src.dungeon.mazmorra import OPUESTA

# Dirección de la puerta -> hacia dónde queda el interior del cuarto.
HACIA_ADENTRO = {"N": (0, 1), "S": (0, -1), "E": (-1, 0), "W": (1, 0)}


class MazmorraJugable:
    def __init__(self, mazmorra):
        self.mazmorra = mazmorra
        self.cuartos = {}  # id de cuarto -> Cuarto ya creado
        # True el frame en que se cambia de cuarto (Main.py limpia los
        # proyectiles del jugador que quedaron en el cuarto anterior).
        self.cambio_de_cuarto = False
        self._crear_cuarto_si_falta(mazmorra.actual)

    @property
    def cuarto(self):
        """Cuarto físico donde está el jugador."""
        return self.cuartos[self.mazmorra.actual]

    @property
    def rect(self):
        return self.cuarto.rect

    @property
    def enemigos(self):
        return self.cuarto.enemigos

    def colocar_en_entrada(self, jugador):
        _ubicar(jugador, self.cuarto.rect.center)

    def _crear_cuarto_si_falta(self, id_cuarto):
        if id_cuarto in self.cuartos:
            return
        m = self.mazmorra
        self.cuartos[id_cuarto] = Cuarto(
            direcciones_puertas=tuple(m.puertas(id_cuarto)),
            nivel_toxicidad=m.toxicidad[id_cuarto],
            dificultad=m.dificultad[id_cuarto],
            es_final=id_cuarto == m.cuarto_final,
        )

    def actualizar(self, dt, jugador, proyectiles_enemigos):
        self.cambio_de_cuarto = False
        self.cuarto.actualizar(dt, jugador, proyectiles_enemigos)
        hay_enemigos = bool(self.cuarto.enemigos)
        if not hay_enemigos:
            self.mazmorra.marcar_limpiado(self.mazmorra.actual)
        self.mazmorra.actualizar(dt, hay_enemigos)

        direccion = self._puerta_tocada(jugador)
        if direccion is not None:
            self._cruzar(direccion, jugador)
            proyectiles_enemigos.clear()

    def _puerta_tocada(self, jugador):
        """Dirección de la puerta abierta que toca el jugador, o None."""
        for direccion, puerta in self.cuarto.puertas.items():
            if not puerta.bloqueada and jugador.rect.colliderect(puerta.rect):
                return direccion
        return None

    def _cruzar(self, direccion, jugador):
        """Pasa al cuarto vecino y aparece junto a su puerta opuesta."""
        if self.mazmorra.mover(direccion) is None:
            return
        self._crear_cuarto_si_falta(self.mazmorra.actual)
        self.cambio_de_cuarto = True
        llegada = OPUESTA[direccion]
        puerta = self.cuarto.puertas[llegada].rect
        dx, dy = HACIA_ADENTRO[llegada]
        distancia = assets.DISTANCIA_APARICION_PUERTA
        _ubicar(jugador, (puerta.centerx + dx * distancia, puerta.centery + dy * distancia))

    def manejar_evento(self, evento):
        self.cuarto.manejar_evento(evento)

    def dibujar(self, pantalla):
        self.cuarto.dibujar(pantalla)


def _ubicar(jugador, centro):
    jugador.rect.center = (round(centro[0]), round(centro[1]))
    jugador.posicion.update(jugador.rect.center)
