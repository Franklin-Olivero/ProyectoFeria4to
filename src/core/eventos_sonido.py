"""Cola de eventos sonoros (lógica pura, sin Pygame).

Las entidades y la lógica del juego no conocen el mezclador: cuando pasa
algo que suena (un disparo, un enemigo que muere, una barricada que se
levanta) llaman a `emitir(id)` con un ID de assets.SONIDOS. Main.py
vacía la cola una vez por frame con `drenar()` y le pasa cada ID al
gestor de audio (src/core/audio.py), que decide si suena (anti-spam,
silencio, dispositivo).

Así la lógica se sigue probando sin audio: emitir es solo agregar a una
cola. La cola tiene tope (MAXIMO_PENDIENTES): si nadie la vacía (tests,
servidor sin pantalla) los eventos viejos se descartan solos.
"""

from collections import deque

MAXIMO_PENDIENTES = 64

_pendientes = deque(maxlen=MAXIMO_PENDIENTES)


def emitir(id_sonido):
    """Pide que suene `id_sonido` en el próximo frame. O(1)."""
    if id_sonido:
        _pendientes.append(id_sonido)


def drenar():
    """Lista de los IDs pendientes, en orden de llegada, y vacía la cola."""
    eventos = list(_pendientes)
    _pendientes.clear()
    return eventos
