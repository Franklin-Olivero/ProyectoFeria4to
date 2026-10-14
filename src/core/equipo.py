"""Reglas de equipo entre jugadores (sin Pygame).

Sinergia de carga: cuando un jugador mata a un enemigo, él recibe la
kill completa y cada aliado recibe CARGA_COMPARTIDA de una kill. Así un
equipo que coopera llena sus habilidades antes que uno que juega solo.
"""

from src.core.balance import CARGA_COMPARTIDA


def registrar_kill_equipo(asesino, aliados):
    """Da la kill completa a `asesino` y CARGA_COMPARTIDA a cada aliado.

    `aliados` puede incluir al propio asesino (por ejemplo, la lista de
    todos los jugadores): se le salta para no darle carga doble. Con un
    solo jugador no hace nada extra.
    """
    asesino.registrar_kill()
    for aliado in aliados:
        if aliado is not asesino:
            aliado.sumar_carga(CARGA_COMPARTIDA)
