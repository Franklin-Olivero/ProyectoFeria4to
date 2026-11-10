"""Única puerta por la que el render de Ciudad Nova pide imágenes.

Cada imagen se pide por id "origen:nombre" (ver assets.ASSETS_CIUDAD_PERMITIDOS):

    ciudad:<pieza>     pieza del atlas de los packs cyberpunk (calzada, banqueta, agua)
    urbano:<nombre>    prop del pack urbano (farolas, bancas, papeleras...)
    arbol:<número>     árbol de Trees_Vol2
    backrooms:<tipo>   prop del pack Backrooms (antena, conos, letrero)

    imagen(id)     -> Surface (cacheada) o None si falta el archivo; ArteNoPermitido
                      si el id no está en la lista blanca: lo que no está en la
                      lista no se dibuja, aunque el pack lo tenga
    permitido(id)  -> True si el id está en la lista blanca
    pedidos        -> ids pedidos desde que arrancó el juego (para los tests)

Antes de entregar la imagen aplica el ajuste de paleta del id
(assets.AJUSTE_PALETA_CIUDAD) o el de su origen (AJUSTE_PALETA_POR_ORIGEN)
con cargador_assets.ajustar_paleta: una sola función para bajar la
saturación de lo que el pack trae demasiado vivo.
"""

from src.core import assets
from src.ui import cargador_assets, cargador_backrooms

_cache = {}
pedidos = set()


class ArteNoPermitido(ValueError):
    """Se pidió dibujar en la ciudad algo que no está en la lista blanca."""


def permitido(id_arte):
    return id_arte in assets.ASSETS_CIUDAD_PERMITIDOS


def _cargar(origen, nombre):
    if origen == "ciudad":
        return cargador_assets.pieza_ciudad(nombre)
    if origen == "urbano":
        return cargador_assets.prop_urbano(nombre)
    if origen == "arbol":
        return cargador_assets.arbol(int(nombre))
    if origen == "backrooms":
        from src.dungeon.zonas_ciudad import PROPS_BACKROOMS
        pack = PROPS_BACKROOMS[nombre]
        if cargador_backrooms.disponible(assets.GRADE_CIUDAD) and cargador_backrooms.tiene_prop(assets.GRADE_CIUDAD, pack):
            return cargador_backrooms.prop(assets.GRADE_CIUDAD, "", pack, assets.ESCALA_BACKROOMS)
        return None
    raise ArteNoPermitido(f"origen de arte desconocido: {origen!r}")


def imagen(id_arte):
    """La imagen del id (con el ajuste de paleta), o None si falta el archivo."""
    if not permitido(id_arte):
        raise ArteNoPermitido(f"{id_arte!r} no está en assets.ASSETS_CIUDAD_PERMITIDOS")
    pedidos.add(id_arte)
    if id_arte not in _cache:
        origen, nombre = id_arte.split(":", 1)
        superficie = _cargar(origen, nombre)
        if superficie is not None:
            por_origen = assets.AJUSTE_PALETA_POR_ORIGEN.get(origen, (1.0, 1.0))
            saturacion, brillo = assets.AJUSTE_PALETA_CIUDAD.get(id_arte, por_origen)
            superficie = cargador_assets.ajustar_paleta(superficie, saturacion, brillo)
        _cache[id_arte] = superficie
    return _cache[id_arte]


def limpiar_cache():
    _cache.clear()
