"""Burbuja Comunitaria del Ciudadano (lógica pura, sin pygame).

La habilidad (F / L1) abre un domo alrededor del Ciudadano durante
DURACION_BURBUJA segundos. Mientras dura:
    - frena los proyectiles enemigos (también los del jefe): el que entra al
      domo se deshace;
    - cura a los aliados que estén adentro (también al Ciudadano):
      CURACION_BURBUJA_POR_S vida por segundo, sin pasar de su vida máxima.
      A un caído (sin vida) no lo levanta y al expulsado (fantasma) no lo toca.
Sinergia del rol: "el Ciudadano sostiene".

`aplicar_burbujas` la llama el frame de combate (Main._frame_de_combate)
después de mover los proyectiles enemigos y antes de ver si golpean a
alguien. Es O(b · (p + j)) con b burbujas activas, p proyectiles y j jugadores.
"""

import math

from src.core.balance import CURACION_BURBUJA_POR_S


def _centro(cuerpo):
    return cuerpo.rect.center


def dentro(burbuja_de, punto):
    """¿`punto` está dentro del domo del Ciudadano `burbuja_de`?"""
    return math.dist(_centro(burbuja_de), punto) <= burbuja_de.radio_burbuja


def burbujas_activas(jugadores):
    """Los jugadores con la burbuja abierta (solo el Ciudadano la tiene)."""
    return [j for j in jugadores if getattr(j, "burbuja_activa", False) and j.vida > 0
            and not getattr(j, "expulsado", False)]


def aplicar_burbujas(jugadores, proyectiles_enemigos, dt):
    """Frena los proyectiles enemigos que entraron a un domo y cura a quien
    esté adentro. Devuelve los puntos donde se frenó un proyectil (para el
    efecto visual)."""
    activas = burbujas_activas(jugadores)
    if not activas:
        return []
    frenados = []
    for proyectil in proyectiles_enemigos:
        if proyectil.vivo and any(dentro(b, proyectil.rect.center) for b in activas):
            proyectil.vivo = False
            frenados.append(proyectil.rect.center)
    proyectiles_enemigos[:] = [p for p in proyectiles_enemigos if p.vivo]
    curacion = CURACION_BURBUJA_POR_S * max(0.0, dt)
    for jugador in jugadores:
        if jugador.vida <= 0 or getattr(jugador, "expulsado", False):
            continue
        if any(dentro(b, _centro(jugador)) for b in activas):
            jugador.vida = min(jugador.vida_maxima, jugador.vida + curacion)
    return frenados
