"""Cuerpo Pygame de una mazmorra normal de varios cuartos.

Envuelve a Mazmorra (lógica pura sobre el grafo, src/dungeon/mazmorra.py)
y le da un Cuarto físico a cada nodo:
    - crea el Cuarto la primera vez que se entra, con las puertas que
      dicta el grafo, la toxicidad/dificultad del nodo y si es el final;
    - guarda los cuartos ya creados, así un cuarto limpiado sigue limpio
      (sus enemigos no reaparecen) al volver a él;
    - detecta cuando el jugador toca una puerta ABIERTA, lo pasa al
      cuarto vecino y lo pone junto a la puerta opuesta;
    - informa a la Mazmorra si quedan enemigos vivos (propagación) y
      qué cuartos se limpiaron;
    - sella las puertas que llevan al cuarto final mientras queden
      cuartos pendientes y avisa con un mensaje breve al tocarlas o al
      desbloquearse el final.

Expone la misma interfaz que Cuarto y ArenaJefe (rect, enemigos,
actualizar, dibujar, manejar_evento), así Main.py usa el mismo loop.
"""

from src.core import assets
from src.dungeon.cuarto import Cuarto
from src.dungeon.mazmorra import OPUESTA

TEXTO_FINAL_DESBLOQUEADO = "Cuarto final desbloqueado"
TEXTO_PUERTA_SELLADA = "Limpia todos los cuartos primero"

# Dirección de la puerta -> hacia dónde queda el interior del cuarto.
HACIA_ADENTRO = {"N": (0, 1), "S": (0, -1), "E": (-1, 0), "W": (1, 0)}


class MazmorraJugable:
    def __init__(self, mazmorra):
        self.mazmorra = mazmorra
        self.cuartos = {}  # id de cuarto -> Cuarto ya creado
        # True el frame en que se cambia de cuarto (Main.py limpia los
        # proyectiles del jugador que quedaron en el cuarto anterior).
        self.cambio_de_cuarto = False
        # Mensaje breve para el HUD: (texto, segundos restantes) o None.
        self.mensaje = None
        self._crear_cuarto_si_falta(mazmorra.actual)
        self._sincronizar_sellos()

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
            permitir_decision=m.puede_iniciar_decision,
        )

    def actualizar(self, dt, jugador, proyectiles_enemigos):
        self.cambio_de_cuarto = False
        if self.mensaje is not None:
            texto, restante = self.mensaje
            self.mensaje = (texto, restante - dt) if restante > dt else None

        # Primero se registra el cuarto limpio (así el cuarto final, si el
        # jugador ya está en él, puede abrir la decisión este mismo frame).
        self.cuarto.actualizar(dt, jugador, proyectiles_enemigos)
        hay_enemigos = bool(self.cuarto.enemigos)
        if not hay_enemigos and self.mazmorra.marcar_limpiado(self.mazmorra.actual):
            self._avisar(TEXTO_FINAL_DESBLOQUEADO)
        self._sincronizar_sellos()
        self.mazmorra.actualizar(dt, hay_enemigos)

        puerta = self._puerta_tocada(jugador)
        if puerta is None:
            return
        if puerta.sellada:
            self._avisar(TEXTO_PUERTA_SELLADA)
            return
        self._cruzar(puerta.direccion, jugador)
        proyectiles_enemigos.clear()

    def _sincronizar_sellos(self):
        """Sella cada puerta cuyo vecino aún no se puede pisar (el final)."""
        vecinos = self.mazmorra.puertas(self.mazmorra.actual)
        for direccion, puerta in self.cuarto.puertas.items():
            puerta.sellada = not self.mazmorra.puede_entrar(vecinos[direccion])

    def _avisar(self, texto):
        self.mensaje = (texto, assets.DURACION_MENSAJE_MAZMORRA)

    def _puerta_tocada(self, jugador):
        """Puerta sin enemigos que toca el jugador (sellada o no), o None."""
        for puerta in self.cuarto.puertas.values():
            if not puerta.bloqueada and jugador.rect.colliderect(puerta.rect):
                return puerta
        return None

    def _cruzar(self, direccion, jugador):
        """Pasa al cuarto vecino y aparece junto a su puerta opuesta."""
        if self.mazmorra.mover(direccion) is None:
            return
        self._crear_cuarto_si_falta(self.mazmorra.actual)
        self._sincronizar_sellos()
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
