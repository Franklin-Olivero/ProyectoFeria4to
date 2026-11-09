"""Auto-tiling "blob" de 47 piezas para los terrenos del pack Backrooms (puro).

Cada terreno (muro de hotel, alfombra, agua...) es un wangset "mixed" de
Tiled: cada tile declara, para sus 8 vecinos, si el terreno continúa hacia
ese lado. Orden de Tiled: arriba, arriba-der, der, abajo-der, abajo,
abajo-izq, izq, arriba-izq. Una esquina solo cuenta si sus dos lados
también continúan (si no, la pieza no existe en un blob de 47).

    wangid(ocupado, col, fila, borde_es_terreno) -> tupla de 8 (0/1)
    resolver(grilla, tabla, borde_es_terreno)    -> filas de ids (-1 vacío)

`grilla` son filas de bool (True = la celda es de ese terreno) y `tabla`
la de terrenos_backrooms.json: {"1,0,1,0,0,0,0,0": id, ...}. Si una
combinación faltara en el pack, se usa la pieza que coincide en más lados
(nunca se queda un hueco). Muros: el borde del mapa cuenta como muro
(siguen fuera de la vista); alfombras: el borde no cuenta.
"""

# (dx, dy) de cada posición del wangid, en el orden de Tiled.
VECINOS = ((0, -1), (1, -1), (1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1))
LADOS = (0, 2, 4, 6)
ESQUINAS = {1: (0, 2), 3: (2, 4), 5: (4, 6), 7: (6, 0)}  # esquina -> sus dos lados


def wangid(grilla, col, fila, borde_es_terreno=False):
    alto, ancho = len(grilla), len(grilla[0])

    def ocupado(c, f):
        if 0 <= c < ancho and 0 <= f < alto:
            return bool(grilla[f][c])
        return borde_es_terreno

    valores = [1 if ocupado(col + dx, fila + dy) else 0 for dx, dy in VECINOS]
    for esquina, (a, b) in ESQUINAS.items():
        if not (valores[a] and valores[b]):
            valores[esquina] = 0
    return tuple(valores)


def clave(wang):
    return ",".join(str(v) for v in wang)


def _mas_parecida(tabla, wang):
    mejor, mejor_puntos = None, -1
    for texto, id_tile in tabla.items():
        candidato = tuple(int(v) for v in texto.split(","))
        puntos = sum(2 if i in LADOS else 1 for i in range(8) if candidato[i] == wang[i])
        if puntos > mejor_puntos:
            mejor, mejor_puntos = id_tile, puntos
    return mejor


def pieza(tabla, wang):
    """Id de la pieza del terreno para `wang` (o la más parecida)."""
    id_tile = tabla.get(clave(wang))
    return id_tile if id_tile is not None else _mas_parecida(tabla, wang)


def resolver(grilla, tabla, borde_es_terreno=False):
    """Filas de ids de tile: la pieza correcta en cada celda ocupada, -1 en el resto."""
    return [[pieza(tabla, wangid(grilla, c, f, borde_es_terreno)) if grilla[f][c] else -1
             for c in range(len(grilla[0]))]
            for f in range(len(grilla))]
