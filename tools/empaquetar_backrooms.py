"""Empaqueta del pack Backrooms SOLO lo que el juego usa, por grade.

    python tools/empaquetar_backrooms.py                    # grades de GRADES_EN_REPO (hum)
    python tools/empaquetar_backrooms.py --grades emergency nightshot   # bajo demanda (no se commitean)
    python tools/empaquetar_backrooms.py --listar           # qué grades hay en _packs/ y qué les falta

Lee el pack de _packs/extraidos/ (fuera de git; la licencia no deja
redistribuirlo) y escribe assets/backrooms/<grade>/:
    tiles.png, props.png, animaciones.png, luces.png   (atlas recortados)
    atlas.json                                          (rects; ver src/ui/rutas_backrooms.py)

Qué se usa sale de las composiciones de COMPOSICIONES_EN_USO
(src/dungeon/datos/composiciones/) armadas con compositor_interior, de las
plantillas de PLANTILLAS_EN_USO (src/dungeon/datos/plantillas/) y de EXTRA.
Para cada animación se incluye también su versión quieta (rutas_backrooms.
prop_estatico_de o la "estatico" de la composición): si al grade le falta
la animación, el juego dibuja esa.

Límites: ningún archivo > 5 MB y assets/backrooms < 40 MB (si se pasa, el
script lo dice y termina con error). Sin pygame-ce instalado no corre.
"""

import argparse
import json
import os
import re
import sys

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, RAIZ)
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame  # noqa: E402

from src.core import assets  # noqa: E402
from src.dungeon import compositor_interior  # noqa: E402
from src.ui import rutas_backrooms  # noqa: E402

PACKS = os.path.join(RAIZ, "_packs", "extraidos")
GRADES_EN_REPO = ("hum",)
COMPOSICIONES_EN_USO = ("lobby_hotel",)
PLANTILLAS_EN_USO = ()  # p. ej. ("vacancy_inn",) cuando una mazmorra la use
EXTRA = {"tiles": [], "props": [], "animaciones": [], "luces": []}
MAX_ARCHIVO = 5 * 1024 * 1024
MAX_TOTAL = 40 * 1024 * 1024
ANCHO_ATLAS = 512  # px de ancho de las hojas de props/animaciones/luces
COLUMNAS_TILES = 16


def carpeta_base(grade):
    """Carpeta con tiles/, props/ y light_pools/ del grade, o None."""
    candidatas = [os.path.join(PACKS, f"backrooms_palette_{grade}_v1.0", "backrooms", grade)]
    if grade == "hum":
        candidatas.insert(0, os.path.join(PACKS, "backrooms_v1.0", "backrooms", "hum"))
    return next((c for c in candidatas if os.path.isdir(os.path.join(c, "tiles"))), None)


def carpeta_animaciones(grade):
    candidatas = [os.path.join(PACKS, f"backrooms_palette_{grade}_animations_v1.0", "backrooms", grade, "animations"),
                  os.path.join(PACKS, "backrooms_animations_v1.0", "backrooms", grade, "animations")]
    return next((c for c in candidatas if os.path.isdir(os.path.join(c, "strips"))), None)


def leer_frames_txt():
    """{animación: (cuadros, ancho, alto, ms)} de frames.txt."""
    ruta = os.path.join(PACKS, "backrooms_v1.0", "backrooms", "frames.txt")
    tabla = {}
    if not os.path.exists(ruta):
        return tabla
    patron = re.compile(r"^(\S+)\s+(\d+) frames\s+(\d+)x(\d+)\s+\d+ fps \((\d+) ms/frame\)")
    with open(ruta, encoding="utf-8") as archivo:
        for linea in archivo:
            m = patron.match(linea.strip())
            if m:
                tabla[m[1]] = (int(m[2]), int(m[3]), int(m[4]), int(m[5]))
    return tabla


def uso():
    """{"tiles": set, "props": set, "animaciones": {nombre: estático o None}, "luces": set}."""
    with open(os.path.join(RAIZ, assets.RUTA_TERRENOS_BACKROOMS), encoding="utf-8") as archivo:
        terrenos = json.load(archivo)
    plantillas = []
    for nombre in COMPOSICIONES_EN_USO:
        with open(os.path.join(RAIZ, assets.RUTA_COMPOSICIONES, f"{nombre}.json"), encoding="utf-8") as archivo:
            plantillas.append(compositor_interior.componer(json.load(archivo), terrenos))
    for nombre in PLANTILLAS_EN_USO:
        with open(os.path.join(RAIZ, "src", "dungeon", "datos", "plantillas", f"{nombre}.json"),
                  encoding="utf-8") as archivo:
            plantillas.append(json.load(archivo))
    usados = {"tiles": set(EXTRA["tiles"]), "props": set(EXTRA["props"]),
              "animaciones": {n: None for n in EXTRA["animaciones"]}, "luces": set(EXTRA["luces"])}
    for plantilla in plantillas:
        usados["tiles"] |= compositor_interior.tiles_usados(plantilla)
        for obj in plantilla["objetos"]:
            if obj["tipo"] == "animacion":
                usados["animaciones"][obj["nombre"]] = obj.get("estatico")
            else:
                usados["props"].add(obj["nombre"])
            if obj.get("apagado"):
                usados["props"].add(obj["apagado"])
        usados["luces"] |= {luz["nombre"] for luz in plantilla.get("luces", [])}
        if plantilla.get("luz_puesto"):
            usados["luces"].add(plantilla["luz_puesto"])
    return usados


class Estante:
    """Empaquetado por estantes: piezas de izquierda a derecha, fila nueva al llenarse."""

    def __init__(self, ancho):
        self.ancho, self.x, self.y, self.alto_fila, self.piezas = ancho, 0, 0, 0, []

    def poner(self, superficie):
        w, h = superficie.get_size()
        if self.x + w > self.ancho:
            self.x, self.y, self.alto_fila = 0, self.y + self.alto_fila + 1, 0
        rect = (self.x, self.y, w, h)
        self.piezas.append((superficie, rect))
        self.x += w + 1
        self.alto_fila = max(self.alto_fila, h)
        return list(rect)

    def guardar(self, ruta):
        if not self.piezas:
            return False
        alto = self.y + self.alto_fila
        hoja = pygame.Surface((self.ancho, max(1, alto)), pygame.SRCALPHA)
        hoja.fill((0, 0, 0, 0))
        for superficie, rect in self.piezas:
            hoja.blit(superficie, rect[:2])
        pygame.image.save(hoja, ruta)
        return True


def empaquetar(grade, usados, frames):
    base = carpeta_base(grade)
    if base is None:
        return None, [f"{grade}: no está extraído en _packs/extraidos/ (zip dañado o ausente)"]
    animaciones_dir = carpeta_animaciones(grade)
    avisos = []
    if animaciones_dir is None and usados["animaciones"]:
        avisos.append(f"{grade}: sin carpeta de animaciones; se usan las versiones quietas")
    destino = rutas_backrooms.carpeta_grade(grade, os.path.join(RAIZ, assets.RUTA_BACKROOMS))
    os.makedirs(destino, exist_ok=True)
    atlas = {"grade": grade, "credito": assets.CREDITO_BACKROOMS, "tiles": {}, "props": {}, "animaciones": {},
             "luces": {}}

    # Tiles: copiados a una grilla de 16 columnas en el orden de su id.
    tileset = pygame.image.load(os.path.join(base, "tiles", "tileset.png"))
    lado = assets.TAM_TILE_BACKROOMS
    ids = sorted(usados["tiles"])
    filas = (len(ids) + COLUMNAS_TILES - 1) // COLUMNAS_TILES
    hoja_tiles = pygame.Surface((COLUMNAS_TILES * lado, max(1, filas) * lado), pygame.SRCALPHA)
    hoja_tiles.fill((0, 0, 0, 0))
    columnas_origen = tileset.get_width() // lado
    for i, id_tile in enumerate(ids):
        origen = ((id_tile % columnas_origen) * lado, (id_tile // columnas_origen) * lado, lado, lado)
        pos = ((i % COLUMNAS_TILES) * lado, (i // COLUMNAS_TILES) * lado)
        hoja_tiles.blit(tileset, pos, origen)
        atlas["tiles"][str(id_tile)] = list(pos)
    pygame.image.save(hoja_tiles, os.path.join(destino, assets.HOJAS_BACKROOMS["tiles"]))

    # Props (más las versiones quietas de las animaciones), desde props_sheet.
    with open(os.path.join(base, "props", "props_sheet.json"), encoding="utf-8") as archivo:
        hoja_json = json.load(archivo)
    hoja_props = pygame.image.load(os.path.join(base, "props", "props_sheet.png"))
    props = set(usados["props"])
    for nombre, estatico in usados["animaciones"].items():
        quieto = estatico or rutas_backrooms.prop_estatico_de(nombre, hoja_json)
        if quieto:
            props.add(quieto)
        else:
            avisos.append(f"{grade}: la animación {nombre} no tiene versión quieta")
    estante = Estante(ANCHO_ATLAS)
    for nombre in sorted(props, key=lambda n: (-hoja_json.get(n, {}).get("h", 0), n)):
        if nombre not in hoja_json:
            avisos.append(f"{grade}: falta el prop {nombre}")
            continue
        r = hoja_json[nombre]
        atlas["props"][nombre] = estante.poner(hoja_props.subsurface((r["x"], r["y"], r["w"], r["h"])).copy())
    estante.guardar(os.path.join(destino, assets.HOJAS_BACKROOMS["props"]))

    # Animaciones: la tira horizontal de cada una (strips/<nombre>.png).
    estante = Estante(ANCHO_ATLAS * 2)
    for nombre in sorted(usados["animaciones"]):
        ruta = os.path.join(animaciones_dir, "strips", f"{nombre}.png") if animaciones_dir else None
        if ruta is None or not os.path.exists(ruta) or nombre not in frames:
            continue
        cuadros, ancho, alto, ms = frames[nombre]
        tira = pygame.image.load(ruta)
        if tira.get_size() != (cuadros * ancho, alto):
            avisos.append(f"{grade}: la tira {nombre} mide {tira.get_size()} y frames.txt dice {cuadros}x{ancho}x{alto}")
            continue
        atlas["animaciones"][nombre] = {"rect": estante.poner(tira), "cuadros": cuadros, "ancho": ancho,
                                        "alto": alto, "ms": [ms] * cuadros}
    estante.guardar(os.path.join(destino, assets.HOJAS_BACKROOMS["animaciones"]))

    # Halos de luz (light_pools/<nombre>.png).
    estante = Estante(ANCHO_ATLAS)
    for nombre in sorted(usados["luces"]):
        ruta = os.path.join(base, "light_pools", f"{nombre}.png")
        if not os.path.exists(ruta):
            avisos.append(f"{grade}: falta la luz {nombre}")
            continue
        atlas["luces"][nombre] = estante.poner(pygame.image.load(ruta))
    estante.guardar(os.path.join(destino, assets.HOJAS_BACKROOMS["luces"]))

    # Hojas vacías de una corrida anterior: fuera, para que el atlas no mienta.
    for tipo, archivo in assets.HOJAS_BACKROOMS.items():
        ruta = os.path.join(destino, archivo)
        if not atlas[tipo] and os.path.exists(ruta):
            os.remove(ruta)
    with open(os.path.join(destino, assets.ARCHIVO_ATLAS_BACKROOMS), "w", encoding="utf-8") as archivo:
        json.dump(atlas, archivo, ensure_ascii=False, indent=1, sort_keys=True)
    return destino, avisos


def tamanio_carpeta(carpeta):
    total, grandes = 0, []
    for raiz, _, archivos in os.walk(carpeta):
        for nombre in archivos:
            ruta = os.path.join(raiz, nombre)
            total += os.path.getsize(ruta)
            if os.path.getsize(ruta) > MAX_ARCHIVO:
                grandes.append(ruta)
    return total, grandes


def listar():
    for grade in assets.GRADES_BACKROOMS:
        base, anim = carpeta_base(grade), carpeta_animaciones(grade)
        print(f"{grade:10s} base: {'sí' if base else 'NO'}   animaciones: {'sí' if anim else 'NO'}")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--grades", nargs="*", default=list(GRADES_EN_REPO))
    parser.add_argument("--listar", action="store_true")
    args = parser.parse_args()
    if args.listar:
        listar()
        return 0
    pygame.init()
    pygame.display.set_mode((1, 1))
    usados = uso()
    print(f"en uso: {len(usados['tiles'])} tiles, {len(usados['props'])} props, "
          f"{len(usados['animaciones'])} animaciones, {len(usados['luces'])} luces")
    frames = leer_frames_txt()
    for grade in args.grades:
        destino, avisos = empaquetar(grade, usados, frames)
        for aviso in avisos:
            print("  aviso:", aviso)
        if destino:
            total, _ = tamanio_carpeta(destino)
            print(f"{grade}: {total / 1024:.0f} KB -> {destino}")
    total, grandes = tamanio_carpeta(os.path.join(RAIZ, assets.RUTA_BACKROOMS))
    print(f"assets/backrooms: {total / 1024 / 1024:.2f} MB")
    if grandes or total > MAX_TOTAL:
        print("ERROR: excede el presupuesto (archivo > 5 MB o carpeta > 40 MB):", grandes)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
