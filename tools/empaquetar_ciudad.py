"""Empaqueta el arte de exteriores de Ciudad Nova desde los packs nuevos.

    python tools/empaquetar_ciudad.py               # -> assets/ciudad/atlas.png + atlas.json
    python tools/empaquetar_ciudad.py --catalogo    # -> _packs/trabajo_ciudad/catalogo_*.png (para elegir props)

Los packs (PATHS__ROADS, EDGES__BORDERS, CORNERS, WALLS, FLOORS_INTERIOR,
LIQUIDS, DECORATIONS) son láminas de 1024 px sin grilla de tiles real ni
canal alfa: celdas de ~170-216 px dibujadas sin una escala de píxel común.
Por eso no se usan "tiles" del pack tal cual: se recortan TEXTURAS y
PIEZAS a escala 1:1 (factor entero 1, igual para toda la ciudad) y el
juego arma cada casilla de 48 px por auto-tiling compuesto
(src/dungeon/autotile_ciudad.py + src/ui/tiles_ciudad.py).

RECETA dice, por nombre de pieza, de qué lámina y rect (px) sale, si se
gira (`girar`, grados) y si se le quita el fondo (`llave`: flood fill desde
el borde con los píxeles parecidos al color de fondo de la lámina). Solo los recortes van al repo (assets/ciudad/), nunca
las láminas: el script es reproducible desde _packs/extraidos/.
"""

import argparse
import json
import os
import sys

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(RAIZ)
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame  # noqa: E402

PACKS = os.path.join("_packs", "extraidos")
SALIDA = os.path.join("assets", "ciudad")
TRABAJO = os.path.join("_packs", "trabajo_ciudad")
ANCHO_ATLAS = 1024
MARGEN = 2  # px entre piezas del atlas

ROADS = ("paths_roads", "PATHS  ROADS ({}).png")
EDGES = ("edges_borders", "EDGES & BORDERS ({}).png")
CORNERS = ("corners", "CORNERS ({}).png")
WALLS = ("walls", "WALLS ({}).png")
FLOORS = ("floors_interior", "FLOORS (INTERIOR) ({}).png")
LIQUIDS = ("liquids", "LIQUIDS ({}).png")
DECOS = ("decorations", "DECORATIONS ({}).png")

# Láminas cuyos props se separan solos (fondo liso) para el catálogo.
LAMINAS_PROPS = ((DECOS, 1), (DECOS, 3), (DECOS, 4), (WALLS, 1))

# nombre -> (pack, número de lámina, (x, y, w, h), opciones)
RECETA = {}


def _receta(nombre, pack, numero, rect, **opciones):
    RECETA[nombre] = (pack, numero, rect, opciones)


# Solo lo que la ciudad usa (assets.ASSETS_CIUDAD_PERMITIDOS): la calzada
# completa sale de UNA celda de PATHS ROADS (4), el tramo recto gris de
# (28, 778), así asfalto, bordillo, banqueta y línea central combinan; la
# cebra, del cruce claro de la misma lámina; el agua de la alberca, de
# LIQUIDS 13 (el cargador le baja la saturación). Nada de maquinaria,
# techos, fachadas ni placas: los edificios son sprites completos.
_receta("asfalto", ROADS, 4, (128, 790, 12, 192))  # franja lisa entre las líneas amarillas
_receta("acera", ROADS, 4, (32, 812, 48, 96))  # losas grises de la banqueta (bajo la tapa de registro)
_receta("bordillo", ROADS, 4, (84, 790, 12, 192), girar=-90)  # borde banqueta-calzada (banqueta arriba)
_receta("linea_carril", ROADS, 4, (119, 830, 7, 48))  # línea central amarilla
_receta("cebra", ROADS, 4, (606, 284, 48, 36))  # barras blancas del paso de cebra
_receta("agua", LIQUIDS, 13, (452, 440, 32, 48))  # agua de la alberca y las fuentes


def ruta_lamina(pack, numero):
    carpeta, patron = pack
    return os.path.join(PACKS, carpeta, patron.format(numero))


_laminas = {}


def lamina(pack, numero):
    ruta = ruta_lamina(pack, numero)
    if ruta not in _laminas:
        _laminas[ruta] = pygame.image.load(ruta).convert_alpha()
    return _laminas[ruta]


def color_fondo(imagen):
    """Color más común del borde de la lámina (su fondo liso)."""
    ancho, alto = imagen.get_size()
    conteo = {}
    for i in range(0, ancho, 4):
        for punto in ((i, 0), (i, alto - 1)):
            c = tuple(imagen.get_at(punto))[:3]
            conteo[c] = conteo.get(c, 0) + 1
    for j in range(0, alto, 4):
        for punto in ((0, j), (ancho - 1, j)):
            c = tuple(imagen.get_at(punto))[:3]
            conteo[c] = conteo.get(c, 0) + 1
    return max(conteo, key=conteo.get)


def quitar_fondo(pieza, fondo, tolerancia=26):
    """Vuelve transparente el fondo conectado al borde de `pieza`."""
    parecido = pygame.mask.from_threshold(pieza, (*fondo, 255), (tolerancia, tolerancia, tolerancia, 255))
    ancho, alto = pieza.get_size()
    exterior = pygame.mask.Mask((ancho, alto))
    semillas = [(x, 0) for x in range(ancho)] + [(x, alto - 1) for x in range(ancho)] + \
        [(0, y) for y in range(alto)] + [(ancho - 1, y) for y in range(alto)]
    for x, y in semillas:
        if parecido.get_at((x, y)) and not exterior.get_at((x, y)):
            exterior.draw(parecido.connected_component((x, y)), (0, 0))
    salida = pieza.copy()
    for y in range(alto):
        for x in range(ancho):
            if exterior.get_at((x, y)):
                salida.set_at((x, y), (0, 0, 0, 0))
    return salida


def recortar(nombre):
    pack, numero, rect, opciones = RECETA[nombre]
    imagen = lamina(pack, numero)
    pieza = imagen.subsurface(pygame.Rect(rect)).copy()
    if opciones.get("llave"):
        pieza = quitar_fondo(pieza, color_fondo(imagen), opciones.get("tolerancia", 26))
        caja = pieza.get_bounding_rect()
        pieza = pieza.subsurface(caja).copy()
    if opciones.get("girar"):
        pieza = pygame.transform.rotate(pieza, opciones["girar"])
    reduccion = opciones.get("reduccion", 1)
    if reduccion != 1:  # reducción entera: promedio de cada bloque de reduccion x reduccion
        ancho, alto = pieza.get_width() // reduccion, pieza.get_height() // reduccion
        pieza = pygame.transform.smoothscale(pieza.subsurface((0, 0, ancho * reduccion, alto * reduccion)), (ancho, alto))
    return pieza


def empacar(piezas):
    """Estantes por altura: {nombre: rect} y el alto total."""
    orden = sorted(piezas, key=lambda n: (-piezas[n].get_height(), n))
    x = y = alto_estante = 0
    rects = {}
    for nombre in orden:
        w, h = piezas[nombre].get_size()
        if x + w > ANCHO_ATLAS:
            x, y, alto_estante = 0, y + alto_estante + MARGEN, 0
        rects[nombre] = (x, y, w, h)
        x += w + MARGEN
        alto_estante = max(alto_estante, h)
    return rects, y + alto_estante


def catalogo():
    """Separa los props de cada lámina de fondo liso y guarda una hoja con
    su número y rect, para elegirlos en RECETA."""
    os.makedirs(TRABAJO, exist_ok=True)
    letra = pygame.font.SysFont("consolas", 12, bold=True)
    for pack, numero in LAMINAS_PROPS:
        imagen = lamina(pack, numero)
        fondo = color_fondo(imagen)
        parecido = pygame.mask.from_threshold(imagen, (*fondo, 255), (26, 26, 26, 255))
        objetos = parecido.copy()
        objetos.invert()
        rects = [r for r in objetos.get_bounding_rects() if r.width >= 24 and r.height >= 24]
        hoja = imagen.copy()
        for i, r in enumerate(sorted(rects, key=lambda r: (r.y // 40, r.x))):
            pygame.draw.rect(hoja, (255, 0, 255), r, 1)
            hoja.blit(letra.render(f"{i}:{r.x},{r.y},{r.w},{r.h}", True, (255, 255, 0), (0, 0, 0)), (r.x, r.y))
        destino = os.path.join(TRABAJO, f"catalogo_{pack[0]}_{numero}.png")
        pygame.image.save(hoja, destino)
        print(destino, len(rects), "props; fondo", fondo)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--catalogo", action="store_true")
    args = parser.parse_args()
    pygame.init()
    pygame.display.set_mode((1, 1))
    faltan = sorted({ruta_lamina(p, n) for p, n, _, _ in RECETA.values() if not os.path.exists(ruta_lamina(p, n))})
    if faltan:
        sys.exit("Faltan láminas (¿pack sin extraer o dañado?):\n  " + "\n  ".join(faltan))
    if args.catalogo:
        catalogo()
        return
    piezas = {nombre: recortar(nombre) for nombre in RECETA}
    rects, alto = empacar(piezas)
    atlas = pygame.Surface((ANCHO_ATLAS, alto), pygame.SRCALPHA)
    for nombre, (x, y, _, _) in rects.items():
        atlas.blit(piezas[nombre], (x, y))
    os.makedirs(SALIDA, exist_ok=True)
    pygame.image.save(atlas, os.path.join(SALIDA, "atlas.png"))
    origen = {n: {"lamina": os.path.basename(ruta_lamina(p, k)), "rect": list(r)} for n, (p, k, r, _) in RECETA.items()}
    with open(os.path.join(SALIDA, "atlas.json"), "w", encoding="utf-8") as archivo:
        json.dump({"piezas": {n: list(r) for n, r in sorted(rects.items())}, "origen": origen}, archivo,
                  indent=1, ensure_ascii=False)
    print(f"{len(rects)} piezas -> {SALIDA}/atlas.png ({ANCHO_ATLAS}x{alto}, "
          f"{os.path.getsize(os.path.join(SALIDA, 'atlas.png')) // 1024} KB)")


if __name__ == "__main__":
    main()
