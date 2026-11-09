"""Convierte mapas .tmx del pack Backrooms en plantillas JSON propias.

    python tools/convertir_tmx.py                      # los mapas de MAPAS
    python tools/convertir_tmx.py --mapas showroom office_maze
    python tools/convertir_tmx.py --pack otra/ruta/backrooms

Lee los .tmx/.tsx de _packs/extraidos/backrooms_v1.0/backrooms/ (fuera de
git) con src/dungeon/lector_tmx.py y escribe src/dungeon/datos/plantillas/
<mapa>.json. En runtime el juego solo lee esas plantillas: nunca los .tmx.

Formato de la plantilla (todo en px nativos de 16 px por tile):
    id, origen, ancho, alto, tile
    capas: [{nombre, tiles: [[id de tile o -1, ...] por fila]}]   (de abajo hacia arriba)
    objetos: [{grupo, nombre, tipo: "prop"|"animacion", x, y, ancho, alto}]
             (x, y) = esquina inferior izquierda: y es donde toca el suelo
    animaciones_tiles: {id: [[id cuadro, ms], ...]}  (solo las de tiles usados)
Los ids de tile son índices del atlas tileset.png del pack (16 columnas),
iguales en todos los grades.

Además escribe src/dungeon/datos/terrenos_backrooms.json desde tiles.tsx:
    wang:  {terreno: {"1,0,1,0,0,0,0,0": id}}   (blob de 47, src/dungeon/autotile.py)
    tipos: {terreno: {kind: [ids]}}            (floor, wall_face, door...)
    animaciones: {id: [[id cuadro, ms], ...]}   (tiles animados)
"""

import argparse
import json
import os
import sys

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, RAIZ)

from src.dungeon import lector_tmx  # noqa: E402

PACK = os.path.join(RAIZ, "_packs", "extraidos", "backrooms_v1.0", "backrooms")
SALIDA = os.path.join(RAIZ, "src", "dungeon", "datos", "plantillas")
# Mapas de referencia de interiores (estándar de calidad para el lobby y la parte 2).
MAPAS = ("vacancy_inn", "showroom")
TSX_TILES = "tiles.tsx"
TSX_PROPS = "props.tsx"
TSX_ANIMADOS = "animated_props.tsx"


def terrenos(ruta_tsx):
    """Tablas wang, ids por (terreno, kind) y animaciones de tiles.tsx."""
    import xml.etree.ElementTree as ET
    raiz = ET.parse(ruta_tsx).getroot()
    wang = {}
    for conjunto in raiz.iter("wangset"):
        tabla = {}
        for wt in conjunto.findall("wangtile"):
            tabla.setdefault(wt.get("wangid"), int(wt.get("tileid")))
        wang[conjunto.get("name")] = tabla
    tileset = lector_tmx.leer_tsx(ruta_tsx)
    tipos, animaciones = {}, {}
    for id_local, tile in sorted(tileset.tiles.items()):
        conjunto = tile.propiedades.get("set", "_")
        tipo = tile.propiedades.get("kind", "_")
        tipos.setdefault(conjunto, {}).setdefault(tipo, []).append(id_local)
        if tile.animacion:
            animaciones[str(id_local)] = [[c, ms] for c, ms in tile.animacion]
    return {"origen": "Backrooms Liminal Interiors (bubbabba), hum/tiled/tiles.tsx",
            "wang": wang, "tipos": tipos, "animaciones": animaciones}


def _nombre_de_tile(tileset, id_local):
    tile = tileset.tiles.get(id_local)
    if tile is None:
        return None
    if "name" in tile.propiedades:
        return tile.propiedades["name"]
    return os.path.splitext(os.path.basename(tile.imagen))[0] or None


def convertir(ruta_tmx):
    mapa = lector_tmx.leer_tmx(ruta_tmx)
    tilesets = {}
    for ref in mapa.tilesets:
        tilesets[os.path.basename(ref.source)] = (ref, lector_tmx.leer_tsx(lector_tmx.ruta_tileset(ruta_tmx, ref)))
    if TSX_TILES not in tilesets:
        raise SystemExit(f"{ruta_tmx}: no usa {TSX_TILES}")
    tiles_tsx = tilesets[TSX_TILES][1]
    avisos = []
    usados = set()

    capas, objetos = [], []
    for capa in mapa.capas:
        if isinstance(capa, lector_tmx.CapaTiles):
            filas = []
            for fila in range(capa.alto):
                salida = []
                for columna in range(capa.ancho):
                    gid = capa.gid(columna, fila)
                    limpio, h, v, d = lector_tmx.separar_gid(gid)
                    if limpio == 0:
                        salida.append(-1)
                        continue
                    ref, id_local = lector_tmx.tileset_de_gid(mapa, gid)
                    if os.path.basename(ref.source) != TSX_TILES:
                        avisos.append(f"capa {capa.nombre}: gid {limpio} no es de {TSX_TILES}")
                        salida.append(-1)
                        continue
                    if h or v or d:
                        avisos.append(f"capa {capa.nombre}: tile volteado en ({columna},{fila}); se dibuja sin voltear")
                    salida.append(id_local)
                    usados.add(id_local)
                filas.append(salida)
            capas.append({"nombre": capa.nombre, "tiles": filas})
        else:
            for obj in capa.objetos:
                if not obj.gid:
                    continue
                ref, id_local = lector_tmx.tileset_de_gid(mapa, obj.gid)
                archivo = os.path.basename(ref.source)
                if archivo not in (TSX_PROPS, TSX_ANIMADOS):
                    avisos.append(f"objeto {obj.nombre}: tileset {archivo} no soportado")
                    continue
                nombre = _nombre_de_tile(tilesets[archivo][1], id_local) or obj.nombre
                objetos.append({
                    "grupo": capa.nombre,
                    "nombre": nombre,
                    "tipo": "animacion" if archivo == TSX_ANIMADOS else "prop",
                    "x": round(obj.x), "y": round(obj.y),
                    "ancho": round(obj.ancho), "alto": round(obj.alto),
                })

    animaciones = {}
    for id_local in sorted(usados):
        tile = tiles_tsx.tiles.get(id_local)
        if tile is not None and tile.animacion:
            animaciones[str(id_local)] = [[cuadro, ms] for cuadro, ms in tile.animacion]
    nombre = os.path.splitext(os.path.basename(ruta_tmx))[0]
    plantilla = {
        "id": nombre,
        "origen": f"Backrooms Liminal Interiors (bubbabba), maps/{nombre}.tmx",
        "ancho": mapa.ancho, "alto": mapa.alto, "tile": mapa.ancho_tile,
        "capas": capas,
        "objetos": objetos,
        "animaciones_tiles": animaciones,
    }
    return plantilla, avisos


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--pack", default=PACK)
    parser.add_argument("--mapas", nargs="*", default=list(MAPAS))
    parser.add_argument("--salida", default=SALIDA)
    args = parser.parse_args()
    os.makedirs(args.salida, exist_ok=True)
    ruta_tsx = os.path.join(args.pack, "hum", "tiled", TSX_TILES)
    if os.path.exists(ruta_tsx):
        destino = os.path.join(os.path.dirname(args.salida), "terrenos_backrooms.json")
        with open(destino, "w", encoding="utf-8") as archivo:
            json.dump(terrenos(ruta_tsx), archivo, ensure_ascii=False, separators=(",", ":"))
        print(f"terrenos -> {destino}")
    for nombre in args.mapas:
        ruta = os.path.join(args.pack, "maps", f"{nombre}.tmx")
        if not os.path.exists(ruta):
            print(f"falta {ruta}: ¿está extraído backrooms_v1.0.zip en _packs/extraidos/?")
            continue
        plantilla, avisos = convertir(ruta)
        destino = os.path.join(args.salida, f"{nombre}.json")
        with open(destino, "w", encoding="utf-8") as archivo:
            json.dump(plantilla, archivo, ensure_ascii=False, separators=(",", ":"))
        print(f"{nombre}: {len(plantilla['capas'])} capas, {len(plantilla['objetos'])} objetos -> {destino}")
        for aviso in avisos[:10]:
            print("  aviso:", aviso)


if __name__ == "__main__":
    main()
