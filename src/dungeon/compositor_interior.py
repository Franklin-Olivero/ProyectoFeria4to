"""Arma una plantilla de interior Backrooms a partir de una composición (puro).

Una composición (src/dungeon/datos/composiciones/<id>.json) describe un
interior a mano con rectángulos, no tile por tile:

    id, ancho, alto (en tiles), tile (px nativos)
    piso:      {"variantes": [ids]}              el suelo base, alternando variantes
    muro:      {"terreno", "rects": [[col, fila, ancho, alto]],
                "cara": {"izquierda": [id_arriba, id_abajo], "derecha": [...], "medio": [[...], ...]}}
    alfombras: [{"terreno", "rect": [col, fila, ancho, alto]}]
    objetos:   [{"nombre", "tipo": "prop"|"animacion", "x", "y", ...}]   (se copian tal cual)
    luces, puestos, ...                          (extras que usa quien dibuja; se copian)

El resultado tiene el mismo formato que las plantillas convertidas de los
.tmx (tools/convertir_tmx.py), así el mismo dibujante sirve para las dos:
capas de abajo hacia arriba (piso, muro, alfombra, cara de muro), objetos
con (x, y) = esquina inferior izquierda en px nativos.

El muro es la "tapa" de 16 px (auto-tiling blob, src/dungeon/autotile.py)
y bajo cada tramo de tapa que da al suelo se pone su cara de 32 px: dos
filas de tiles, con piezas propias en los extremos. El borde del mapa
cuenta como muro.
"""

from src.dungeon import autotile

VACIO = -1
ALTO_CARA = 2  # filas de tiles de la cara de un muro (32 px)


def _grilla(ancho, alto, rects):
    grilla = [[False] * ancho for _ in range(alto)]
    for col, fila, w, h in rects:
        for f in range(max(0, fila), min(alto, fila + h)):
            for c in range(max(0, col), min(ancho, col + w)):
                grilla[f][c] = True
    return grilla


def celdas_de_cara(muro):
    """{(col, fila de la tapa)}: tapas de muro con suelo justo debajo."""
    alto, ancho = len(muro), len(muro[0])
    return {(c, f) for f in range(alto - 1) for c in range(ancho) if muro[f][c] and not muro[f + 1][c]}


def capa_caras(muro, estilo):
    """Capa con la cara (2 filas) bajo cada tapa que da al suelo. Los
    extremos de cada tramo usan las piezas "izquierda"/"derecha"; el medio
    alterna las pares de "medio"."""
    alto, ancho = len(muro), len(muro[0])
    capa = [[VACIO] * ancho for _ in range(alto)]
    tapas = celdas_de_cara(muro)
    for c, f in sorted(tapas):
        # En el borde del mapa el muro sigue fuera de la vista: no es un extremo.
        izquierda = c > 0 and (c - 1, f) not in tapas
        derecha = c < ancho - 1 and (c + 1, f) not in tapas
        if izquierda and "izquierda" in estilo:
            par = estilo["izquierda"]
        elif derecha and "derecha" in estilo:
            par = estilo["derecha"]
        else:
            medios = estilo["medio"]
            par = medios[c % len(medios)]
        for i in range(ALTO_CARA):
            if f + 1 + i < alto and not muro[f + 1 + i][c]:
                capa[f + 1 + i][c] = par[i]
    return capa


def componer(composicion, terrenos):
    """Plantilla (dict) de la composición, con las tablas de
    terrenos_backrooms.json (`terrenos["wang"]`)."""
    ancho, alto = composicion["ancho"], composicion["alto"]
    muro_def = composicion.get("muro")
    muro = _grilla(ancho, alto, muro_def["rects"] if muro_def else [])

    variantes = composicion["piso"]["variantes"]
    piso = [[VACIO if muro[f][c] else variantes[(c + 2 * f) % len(variantes)] for c in range(ancho)]
            for f in range(alto)]
    capas = [{"nombre": "piso", "tiles": piso}]
    if muro_def:
        tabla = terrenos["wang"][muro_def["terreno"]]
        capas.append({"nombre": "muro", "tiles": autotile.resolver(muro, tabla, borde_es_terreno=True)})
    for i, alfombra in enumerate(composicion.get("alfombras", [])):
        grilla = _grilla(ancho, alto, [alfombra["rect"]])
        tabla = terrenos["wang"][alfombra["terreno"]]
        capas.append({"nombre": f"alfombra_{i}", "tiles": autotile.resolver(grilla, tabla)})
    if muro_def and "cara" in muro_def:
        capas.append({"nombre": "cara_muro", "tiles": capa_caras(muro, muro_def["cara"])})

    usados = {t for capa in capas for fila in capa["tiles"] for t in fila if t != VACIO}
    animaciones = terrenos.get("animaciones", {})
    plantilla = {
        "id": composicion["id"],
        "ancho": ancho, "alto": alto, "tile": composicion.get("tile", 16),
        "capas": capas,
        "objetos": list(composicion.get("objetos", [])),
        "animaciones_tiles": {k: v for k, v in animaciones.items() if int(k) in usados},
    }
    for extra in ("luces", "luz_puesto", "puestos", "polvo"):
        if extra in composicion:
            plantilla[extra] = composicion[extra]
    return plantilla


def tiles_usados(plantilla):
    """Ids de tile que la plantilla dibuja (incluidos los cuadros de sus animaciones)."""
    usados = {t for capa in plantilla["capas"] for fila in capa["tiles"] for t in fila if t != VACIO}
    for cuadros in plantilla.get("animaciones_tiles", {}).values():
        usados.update(c for c, _ in cuadros)
    return usados
