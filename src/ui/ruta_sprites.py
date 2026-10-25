"""Dónde buscar el arte real de cada sprite (lógica pura, sin Pygame).

Separado de src/ui/sprites.py para poder probar la regla de fallback
sin cargar imágenes: si el PNG existe se usa; si no, el pixel art
dibujado en código.
"""

import os

from src.core import assets


def ruta_sprite_enemigo(id_sprite, carpeta=None, existe=os.path.exists):
    """Ruta de `<carpeta>/<id_sprite>.png` si el archivo existe; si no,
    None (= usar el placeholder). `carpeta` por defecto es
    assets.RUTA_SPRITES_ENEMIGOS; `existe` se inyecta en los tests."""
    carpeta = assets.RUTA_SPRITES_ENEMIGOS if carpeta is None else carpeta
    ruta = os.path.join(carpeta, f"{id_sprite}.png")
    return ruta if existe(ruta) else None
