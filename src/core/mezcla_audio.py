"""Reglas de la mezcla de audio (lógica pura, sin Pygame).

Lo que src/core/audio.py decide antes de tocar el mezclador, separado
para probarlo sin dispositivo de audio:

    - resolver_ruta / categoria: de un ID a su archivo y su grupo de
      volumen, con None si el ID no existe o falta el archivo (el gestor
      entonces no reproduce nada: fallback silencioso).
    - volumen_final: preferencia del jugador * categoría * ganancia del ID.
    - LimitadorSonidos: anti-spam por ID (máximo de copias sonando a la
      vez e intervalo mínimo entre dos reproducciones).
"""

import os

from src.core import assets
from src.core.balance import (
    GANANCIA_MUSICA,
    GANANCIA_SONIDO,
    INTERVALO_MINIMO_SONIDO,
    MAX_SIMULTANEOS_SONIDO,
    VOLUMEN_CATEGORIA,
)


def resolver_ruta(id_sonido, catalogo=None, existe=os.path.exists):
    """Ruta del archivo de `id_sonido` si el ID existe y el archivo está;
    si no, None. `catalogo` es assets.SONIDOS (o assets.MUSICA para la
    música); `existe` se puede reemplazar en los tests."""
    catalogo = assets.SONIDOS if catalogo is None else catalogo
    entrada = catalogo.get(id_sonido)
    if entrada is None:
        return None
    ruta = entrada[0] if isinstance(entrada, tuple) else entrada
    return ruta if existe(ruta) else None


def categoria(id_sonido):
    """Grupo de volumen del efecto (sfx o ui); sfx si no se conoce."""
    entrada = assets.SONIDOS.get(id_sonido)
    return entrada[1] if entrada is not None else assets.CATEGORIA_SFX


def a_fraccion(porcentaje):
    """Porcentaje 0-100 de la interfaz -> 0.0-1.0 (0 silencia, nunca más de 1)."""
    return max(0, min(100, porcentaje)) / 100


def volumen_final(id_sonido, porcentaje_preferencia, silenciado=False, es_musica=False):
    """Volumen 0.0-1.0 con el que debe sonar `id_sonido`."""
    if silenciado:
        return 0.0
    if es_musica:
        grupo, ganancia = assets.CATEGORIA_MUSICA, GANANCIA_MUSICA.get(id_sonido, 1.0)
    else:
        grupo, ganancia = categoria(id_sonido), GANANCIA_SONIDO.get(id_sonido, 1.0)
    return min(1.0, a_fraccion(porcentaje_preferencia) * VOLUMEN_CATEGORIA[grupo] * ganancia)


class LimitadorSonidos:
    """Anti-spam por ID de sonido.

    permitir(id, ahora, sonando) es True si el sonido puede salir ahora:
    pasó al menos `intervalo` s desde la última vez y hay menos de
    `maximo` copias sonando (`sonando` lo cuenta el mezclador). Si lo
    permite, registra `ahora` como la última reproducción. O(1).
    """

    def __init__(self, maximo=MAX_SIMULTANEOS_SONIDO, intervalo=INTERVALO_MINIMO_SONIDO):
        self.maximo = maximo
        self.intervalo = intervalo
        self._ultima = {}  # id -> segundo de la última reproducción

    def permitir(self, id_sonido, ahora, sonando=0):
        ultima = self._ultima.get(id_sonido)
        if ultima is not None and ahora - ultima < self.intervalo:
            return False
        if sonando >= self.maximo:
            return False
        self._ultima[id_sonido] = ahora
        return True
