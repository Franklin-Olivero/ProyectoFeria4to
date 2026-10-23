"""Reglas de equipo entre jugadores (sin Pygame).

Sinergia de carga: cuando un jugador mata a un enemigo, él recibe la
kill completa y cada aliado recibe CARGA_COMPARTIDA de una kill. Así un
equipo que coopera llena sus habilidades antes que uno que juega solo.

Cooperativo local: un jugador sin vida queda "caído" mientras algún
compañero siga en pie (no se mueve, no dispara, los enemigos lo
ignoran) y revive con VIDA_AL_REVIVIR al pasar al siguiente cuarto. Si
caen todos, nadie queda fuera: se comporta igual que jugando solo.
"""

import math

from src.core.balance import CARGA_COMPARTIDA, VIDA_AL_REVIVIR


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


def jugadores_en_combate(jugadores):
    """Los que siguen en pie. Si no queda ninguno, todos (como en solitario,
    donde el jugador nunca queda fuera del cuarto). O(n)."""
    vivos = [jugador for jugador in jugadores if jugador.vivo]
    return vivos or list(jugadores)


def jugador_mas_cercano(punto, jugadores):
    """El jugador en combate más cercano a `punto` (x, y): a quién
    persigue y dispara cada enemigo. O(n)."""
    return min(
        jugadores_en_combate(jugadores),
        key=lambda jugador: math.dist(punto, (jugador.posicion.x, jugador.posicion.y)),
    )


def todos_caidos(jugadores):
    return not any(jugador.vivo for jugador in jugadores)


def revivir_caidos(jugadores):
    """Al pasar de cuarto, cada caído vuelve con VIDA_AL_REVIVIR, siempre
    que algún compañero siga en pie. Retorna los que revivieron."""
    if todos_caidos(jugadores):
        return []
    revividos = [jugador for jugador in jugadores if not jugador.vivo]
    for jugador in revividos:
        jugador.vida = VIDA_AL_REVIVIR
        jugador.invulnerabilidad.reiniciar()
    return revividos
