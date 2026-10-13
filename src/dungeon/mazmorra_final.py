"""Mazmorra final: la pelea contra el "Servidor Central" (lógica pura, sin Pygame).

Un solo cuarto grande, sin minijuego de decisión: se gana solo
peleando. La toxicidad es siempre la máxima (NIVEL_TOXICIDAD_FINAL) y
pasa por el mismo clasificador que los cuartos normales
(nivel_a_dificultad); de ahí sale el tope de súbditos vivos y su
velocidad.

Reglas:
    - Temporizador de TIEMPO_LIMITE_JEFE segundos.
    - Tiempo agotado o jugador muerto -> derrota: colapso.sumar_fallo()
      y la pelea se reinicia desde cero.
    - Jefe muerto -> victoria: colapso.restar_exito() una sola vez.

La parte física (rects, proyectiles de Pygame, súbditos y dibujo) vive
en src/dungeon/arena_jefe.py.
"""

import random

from src.core import assets
from src.core.balance import (
    COLAPSO_DESBLOQUEO,
    MAZMORRAS_PARA_DESBLOQUEO,
    NIVEL_TOXICIDAD_FINAL,
    TIEMPO_LIMITE_JEFE,
)
from src.dungeon.clasificador_toxicidad import nivel_a_dificultad
from src.entities.jefe import Jefe, SalidaJefe

EN_COMBATE = "combate"
VICTORIA = "victoria"

TEXTO_VICTORIA = "Servidor Central purificado"
TEXTO_DERROTA = "Derrota: la pelea se reinicia"


def esta_desbloqueada(colapso, mazmorras_completadas):
    """La mazmorra final se abre si el colapso supera el 80% (la ciudad
    está al borde) o si ya se completó al menos una mazmorra normal."""
    return (
        colapso.valor > COLAPSO_DESBLOQUEO
        or mazmorras_completadas >= MAZMORRAS_PARA_DESBLOQUEO
    )


class MazmorraFinal:
    def __init__(self, colapso, limites, rng=None):
        """`limites` = (izquierda, arriba, derecha, abajo) del cuarto grande."""
        self.colapso = colapso
        self.limites = limites
        self.rng = rng or random.Random()
        self.nivel_toxicidad = NIVEL_TOXICIDAD_FINAL
        self.dificultad = nivel_a_dificultad(self.nivel_toxicidad)

        self.derrotas = 0
        self.tiempo_mensaje_derrota = 0.0
        self.tiempo_sacudida = 0.0
        # True el frame en que se reinicia la pelea: la arena limpia
        # súbditos y proyectiles y cura al jugador.
        self.reinicio_pendiente = False
        self._preparar_pelea()

    def _preparar_pelea(self):
        izquierda, arriba, derecha, abajo = self.limites
        self.jefe = Jefe((izquierda + derecha) / 2, arriba + (abajo - arriba) / 4, self.limites, self.rng)
        self.charcos = []
        self.tiempo_restante = TIEMPO_LIMITE_JEFE
        self.estado = EN_COMBATE
        self.salida = SalidaJefe()

    def actualizar(self, dt, jugador):
        """Un frame de la pelea. `jugador` necesita posicion.x/.y, vivo y recibir_dano()."""
        self.tiempo_mensaje_derrota = max(0.0, self.tiempo_mensaje_derrota - dt)
        self.tiempo_sacudida = max(0.0, self.tiempo_sacudida - dt)
        self.salida = SalidaJefe()
        if self.estado != EN_COMBATE:
            return

        self.tiempo_restante = max(0.0, self.tiempo_restante - dt)
        self.jefe.actualizar(dt, (jugador.posicion.x, jugador.posicion.y), self.salida)
        if self.jefe.eventos:
            # Cambio de fase o escudo roto: sacudida corta de pantalla.
            self.tiempo_sacudida = assets.SHAKE_DURACION
            self.jefe.eventos.clear()

        self._actualizar_charcos(dt, jugador)

        if not self.jefe.vivo:
            self.estado = VICTORIA
            self.colapso.restar_exito()
        elif self.tiempo_restante <= 0 or not jugador.vivo:
            self._derrota()

    def _actualizar_charcos(self, dt, jugador):
        self.charcos.extend(self.salida.charcos)
        danio = 0.0
        for charco in self.charcos:
            charco.actualizar(dt)
            danio += charco.danio_para(jugador.posicion.x, jugador.posicion.y, dt)
        self.charcos = [charco for charco in self.charcos if charco.vivo]
        if danio > 0:
            # Respeta la invulnerabilidad pero no la abre (daño continuo).
            jugador.recibir_dano(danio, inicia_invulnerabilidad=False)

    def _derrota(self):
        self.colapso.sumar_fallo()
        self.derrotas += 1
        self.tiempo_mensaje_derrota = assets.DURACION_MENSAJE
        self.reinicio_pendiente = True
        self._preparar_pelea()

    def texto_mensaje(self):
        """Mensaje central a mostrar ahora (o None)."""
        if self.estado == VICTORIA:
            return TEXTO_VICTORIA
        if self.tiempo_mensaje_derrota > 0:
            return TEXTO_DERROTA
        return None

    def desplazamiento_sacudida(self):
        """(dx, dy) en píxeles para sacudir la pantalla; (0, 0) si no hay sacudida."""
        if self.tiempo_sacudida <= 0:
            return (0, 0)
        intensidad = assets.SHAKE_INTENSIDAD
        return (
            self.rng.randint(-intensidad, intensidad),
            self.rng.randint(-intensidad, intensidad),
        )
