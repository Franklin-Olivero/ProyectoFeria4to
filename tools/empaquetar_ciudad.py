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

RECETA dice, por nombre de pieza, de qué lámina y rect (px) sale y si se
le quita el fondo (`llave`: flood fill desde el borde con los píxeles
parecidos al color de fondo de la lámina; así el interior oscuro de un
prop no se agujerea). Solo los recortes van al repo (assets/ciudad/), nunca
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


# --- Suelo: texturas 1:1 (se repiten por casilla) ---------------------------
_receta("asfalto", EDGES, 1, (560, 808, 96, 96))  # malla oscura fina
_receta("acera", ROADS, 4, (34, 800, 48, 96))  # losa gris del tramo recto
_receta("plaza", EDGES, 1, (60, 832, 96, 96))  # losas claras con junta
_receta("plaza_borde", EDGES, 1, (552, 552, 96, 96))  # rejilla gris con esquinas de peligro
_receta("pasto_tecno", FLOORS, 3, (244, 644, 96, 96))  # placas verdes (jardines y camellón)
# --- Marcas viales y bordes (tiras) ------------------------------------------
_receta("bordillo", ROADS, 3, (40, 236, 96, 12))  # franja de peligro amarilla/negra
_receta("linea_carril", ROADS, 4, (119, 830, 7, 48))  # línea amarilla del tramo recto
_receta("cebra", ROADS, 4, (606, 284, 48, 36))  # barras blancas del cruce claro
_receta("borde_metal", CORNERS, 5, (14, 14, 12, 96))  # canto metálico (canal, camellón)
# --- Agua neón del canal (LIQUIDS 13: piscina de datos) ----------------------
_receta("agua", LIQUIDS, 13, (452, 440, 32, 48))
_receta("agua_b", LIQUIDS, 13, (552, 440, 32, 48))
# --- Techos y fachadas ---------------------------------------------------------
# Techos: 11 marcos de CORNERS 5 (el 10 no se usa: muy parecido al 8).
for i, (x, y) in enumerate(((14, 14), (270, 14), (526, 14), (782, 14), (14, 270), (270, 270), (526, 270),
                            (782, 270), (14, 526), (270, 526), (526, 526), (782, 526))):
    if i != 10:
        _receta(f"techo_{i}", CORNERS, 5, (x, y, 200, 200))
_receta("fachada_neon", WALLS, 1, (690, 50, 285, 96))
_receta("fachada_tienda", WALLS, 1, (690, 268, 285, 84))
_receta("fachada_roja", WALLS, 1, (690, 384, 285, 96))
_receta("fachada_vidrio", WALLS, 1, (690, 530, 285, 96))
_receta("fachada_granate", WALLS, 1, (690, 660, 285, 96))
_receta("fachada_noche", WALLS, 1, (690, 846, 285, 96))
_receta("fachada_franja", WALLS, 1, (690, 192, 285, 52))  # también la valla neón de los muros
_receta("puerta_roja", WALLS, 1, (396, 524, 92, 104))
_receta("puerta_vidrio", WALLS, 1, (52, 524, 168, 104))
_receta("pilar_morado", WALLS, 1, (526, 48, 134, 304))
_receta("pilar_cian", WALLS, 1, (528, 528, 120, 444))
# --- Placas especiales: cruces y monumento -------------------------------------
_receta("cruce_especial", ROADS, 2, (34, 34, 212, 212))
_receta("grieta_liminal", LIQUIDS, 9, (412, 652, 96, 96))
# Emblemas de los cruces: el cuadro central de cuatro placas de PATHS ROADS (2).
for _i, (_x, _y) in enumerate(((280, 30), (780, 30), (780, 280), (280, 780))):
    _receta(f"emblema_cruce_{_i}", ROADS, 2, (_x + 62, _y + 62, 96, 96))

# --- Props (DECORATIONS 1 y 4): grilla regular de 6x6 sobre fondo liso ---------
# Se les quita el fondo y se reducen a la mitad (factor entero): la lámina
# dibuja cada objeto a ~2x la densidad de píxel del juego (ESCALA_PIXEL 3).


def _celda(lamina_n, fila, col):
    if lamina_n == 1:
        return (22 + col * 162, 14 + fila * 165, 162, 165)
    return (14 + col * 166, 14 + fila * 166, 166, 166)


PROPS = {
    # comercial
    "expendedora": (1, 0, 0), "kiosco_neon": (1, 0, 1), "maquina_snacks": (1, 3, 3), "cajero": (4, 1, 3),
    # medios
    "servidor": (1, 0, 2), "baliza_senal": (1, 3, 5), "consola_noticias": (4, 2, 5), "monitor_medios": (4, 0, 5),
    # hospitalaria
    "dispensador_medico": (4, 1, 1), "equipo_medico": (4, 1, 4), "botiquin": (4, 4, 2),
    # escolar
    "casillero_escolar": (4, 0, 4), "caja_material": (4, 4, 1), "terminal_estudio": (1, 1, 0),
    # cívica
    "totem_info": (1, 0, 3), "pedestal_civico": (4, 5, 5), "urna_digital": (1, 4, 4),
    # residencial
    "generador": (1, 2, 0), "aire_ac": (1, 1, 4), "contenedor": (1, 4, 3), "medidor": (4, 0, 0),
    # avenidas y parque
    "transformador": (1, 5, 3), "caja_electrica": (1, 1, 1), "farol_datos": (1, 4, 5),
}
for _nombre, (_lam, _fila, _col) in PROPS.items():
    _receta(_nombre, DECOS, _lam, _celda(_lam, _fila, _col), llave=True, tolerancia=30, reduccion=2)


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
