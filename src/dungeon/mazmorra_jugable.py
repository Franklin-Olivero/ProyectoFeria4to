"""Cuerpo Pygame de una mazmorra normal de varios cuartos.

Envuelve a Mazmorra (lógica pura sobre el grafo, src/dungeon/mazmorra.py)
y le da un Cuarto físico a cada nodo:
    - crea el Cuarto la primera vez que se entra, con las puertas que
      dicta el grafo, la toxicidad/dificultad del nodo y si es el final;
    - guarda los cuartos ya creados, así un cuarto limpiado sigue limpio
      (sus enemigos no reaparecen) al volver a él;
    - detecta cuando un jugador toca una puerta ABIERTA y pasa a todo el
      equipo al cuarto vecino, junto a la puerta opuesta (en cooperativo,
      uno al lado del otro);
    - informa a la Mazmorra si quedan enemigos vivos (propagación) y
      qué cuartos se limpiaron;
    - sella las puertas que llevan al cuarto final mientras queden
      cuartos pendientes y avisa con un mensaje breve al tocarlas o al
      desbloquearse el final;
    - da un segundo de gracia (GraciaEntrada) al empezar y en cada
      cuarto al que se entra: el cuarto queda `congelado` mientras dure
      y Main.py bloquea las armas del jugador;
    - crea cada cuarto sabiendo por qué puerta entra el jugador, para
      que sus enemigos aparezcan lejos de ese punto, con un rng propio
      (derivado de la semilla de la mazmorra) para la composición.

Expone la misma interfaz que Cuarto y ArenaJefe (rect, enemigos,
actualizar, dibujar, manejar_evento), así Main.py usa el mismo loop.
"""

import random

from src.audio import eventos_sonido
from src.core import assets
from src.dungeon.clasificador_toxicidad import enemigos_para_equipo
from src.core.equipo import jugadores_en_combate
from src.dungeon.cuarto import HACIA_ADENTRO, Cuarto, punto_llegada
from src.dungeon.gracia_entrada import GraciaEntrada
from src.dungeon.mazmorra import OPUESTA

TEXTO_FINAL_DESBLOQUEADO = "Cuarto final desbloqueado"
TEXTO_PUERTA_SELLADA = "Limpia todos los cuartos primero"


class MazmorraJugable:
    def __init__(self, mazmorra, fabrica_arbol=None, duracion_terminal=None):
        self.mazmorra = mazmorra
        # Modo historia: el cuarto final arma su terminal con este árbol
        # (ver Partida.fabrica_arbol); None = árbol fijo original.
        self.fabrica_arbol = fabrica_arbol
        self.duracion_terminal = duracion_terminal
        self.cuartos = {}  # id de cuarto -> Cuarto ya creado
        self.usos_variantes = {}  # variante de enemigo -> veces que apareció en la mazmorra
        # Jugadores del equipo: con 2 a 4, cada cuarto nuevo trae más enemigos
        # según su toxicidad (enemigos_para_equipo). Lo fija colocar_en_entrada.
        self.cantidad_jugadores = 1
        # True el frame en que se cambia de cuarto (Main.py limpia los
        # proyectiles del jugador que quedaron en el cuarto anterior).
        self.cambio_de_cuarto = False
        # Mensaje breve para el HUD: (texto, segundos restantes) o None.
        self.mensaje = None
        # Distancia (en cuartos) de cada uno a la entrada: la entrada y
        # sus vecinos son los "cuartos iniciales" (sin curanderos).
        _, self._distancia_entrada, _ = mazmorra.grafo.bfs(mazmorra.entrada)
        self.gracia = GraciaEntrada()
        self._crear_cuarto_si_falta(mazmorra.actual)
        self._sincronizar_sellos()
        self.gracia.iniciar()

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

    @property
    def coberturas(self):
        """Muebles sólidos del cuarto actual (ZonaCoberturas)."""
        return self.cuarto.coberturas

    def colocar_en_entrada(self, jugadores):
        self.cantidad_jugadores = max(1, len(jugadores))
        ubicar_en_fila(jugadores, self.cuarto.rect.center, (1, 0))
        self._sacar_de_muebles(jugadores)

    def _sacar_de_muebles(self, jugadores):
        """Nadie aparece dentro de una cobertura (en cooperativo la fila es ancha)."""
        for jugador in jugadores:
            self.cuarto.coberturas.sacar(jugador)

    def _crear_cuarto_si_falta(self, id_cuarto, punto_entrada=None):
        if id_cuarto in self.cuartos:
            return
        m = self.mazmorra
        self.cuartos[id_cuarto] = Cuarto(
            nombre_zona=m.nombre_zona,
            semilla_visual=id_cuarto,
            direcciones_puertas=tuple(m.puertas(id_cuarto)),
            nivel_toxicidad=m.toxicidad[id_cuarto],
            dificultad=enemigos_para_equipo(m.dificultad[id_cuarto], m.toxicidad[id_cuarto],
                                            self.cantidad_jugadores),
            es_final=id_cuarto == m.cuarto_final,
            permitir_decision=m.puede_iniciar_decision,
            punto_entrada=punto_entrada,
            rng=random.Random(m.rng.random()),
            es_cuarto_inicial=self._distancia_entrada[id_cuarto] <= 1,
            usos_variantes=self.usos_variantes,
            fabrica_arbol=self.fabrica_arbol,
            duracion_terminal=self.duracion_terminal,
        )

    def actualizar(self, dt, jugadores, proyectiles_enemigos):
        self.cambio_de_cuarto = False
        if self.mensaje is not None:
            texto, restante = self.mensaje
            self.mensaje = (texto, restante - dt) if restante > dt else None

        en_gracia = self.gracia.activa
        self.gracia.actualizar(dt)
        if en_gracia and not self.gracia.activa:
            eventos_sonido.emitir("gracia_entrada")  # terminó: armas libres
        self.cuarto.congelado = self.gracia.activa
        # Primero se registra el cuarto limpio (así el cuarto final, si el
        # jugador ya está en él, puede abrir la decisión este mismo frame).
        self.cuarto.actualizar(dt, jugadores, proyectiles_enemigos)
        hay_enemigos = bool(self.cuarto.enemigos)
        if not hay_enemigos and self.mazmorra.marcar_limpiado(self.mazmorra.actual):
            self._avisar(TEXTO_FINAL_DESBLOQUEADO)
            eventos_sonido.emitir("cuarto_final_desbloqueado")
        self._sincronizar_sellos()
        self.mazmorra.actualizar(dt, hay_enemigos)

        puerta = self._puerta_tocada(jugadores_en_combate(jugadores))
        if puerta is None:
            return
        if puerta.sellada:
            if self.mensaje is None or self.mensaje[0] != TEXTO_PUERTA_SELLADA:
                eventos_sonido.emitir("puerta_sellada")
            self._avisar(TEXTO_PUERTA_SELLADA)
            return
        self._cruzar(puerta.direccion, jugadores)
        proyectiles_enemigos.clear()

    def _sincronizar_sellos(self):
        """Sella cada puerta cuyo vecino aún no se puede pisar (el final)."""
        vecinos = self.mazmorra.puertas(self.mazmorra.actual)
        for direccion, puerta in self.cuarto.puertas.items():
            puerta.sellada = not self.mazmorra.puede_entrar(vecinos[direccion])

    def _avisar(self, texto):
        self.mensaje = (texto, assets.DURACION_MENSAJE_MAZMORRA)

    def _puerta_tocada(self, jugadores):
        """Puerta sin enemigos que toca algún jugador (sellada o no), o None."""
        for puerta in self.cuarto.puertas.values():
            if not puerta.bloqueada and any(j.rect.colliderect(puerta.rect) for j in jugadores):
                return puerta
        return None

    def _cruzar(self, direccion, jugadores):
        """Pasa al cuarto vecino, el equipo aparece junto a su puerta
        opuesta en fila a lo ancho de la puerta (los enemigos de un cuarto
        nuevo se generan lejos de ese punto) y arranca la gracia de entrada."""
        rect = self.cuarto.rect  # todos los cuartos miden y se ubican igual
        if self.mazmorra.mover(direccion) is None:
            return
        llegada = punto_llegada(rect, OPUESTA[direccion])
        self._crear_cuarto_si_falta(self.mazmorra.actual, llegada)
        self._sincronizar_sellos()
        self.cambio_de_cuarto = True
        dx, dy = HACIA_ADENTRO[OPUESTA[direccion]]
        # La fila va perpendicular a la dirección de entrada (a lo ancho de la puerta).
        ubicar_en_fila(jugadores, llegada, (-dy, dx))
        self._sacar_de_muebles(jugadores)
        self.gracia.iniciar()
        eventos_sonido.emitir("puerta")

    def manejar_evento(self, evento):
        self.cuarto.manejar_evento(evento)

    def dibujar(self, pantalla):
        self.cuarto.dibujar(pantalla)

    def dibujar_delante(self, pantalla, cuerpos):
        self.cuarto.dibujar_delante(pantalla, cuerpos)


def ubicar_en_fila(jugadores, centro, eje):
    """Reparte a los jugadores centrados en `centro`, separados
    SEPARACION_JUGADORES_COOP a lo largo de `eje` (unitario). Con uno
    solo, queda justo en `centro`."""
    separacion = assets.SEPARACION_JUGADORES_COOP
    for i, jugador in enumerate(jugadores):
        desplazamiento = (i - (len(jugadores) - 1) / 2) * separacion
        _ubicar(jugador, (centro[0] + eje[0] * desplazamiento, centro[1] + eje[1] * desplazamiento))


def _ubicar(jugador, centro):
    jugador.rect.center = (round(centro[0]), round(centro[1]))
    jugador.posicion.update(jugador.rect.center)
