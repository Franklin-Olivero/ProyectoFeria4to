"""Convierte imágenes generadas con Higgsfield en piezas de juego (solo pygame).

    # Hoja de objetos sobre fondo verde -> un PNG transparente por objeto
    python tools/procesar_higgsfield.py props hoja.png assets/mazmorras/hospital/props \\
        --nombres camilla,gabinete,monitor --alto 40 --colores 20

    # Textura de piso -> baldosa repetible a resolución de pixel art
    python tools/procesar_higgsfield.py textura piso.png assets/mazmorras/hospital/piso.png \\
        --lado 128 --recorte 1 --banda 0.06 --colores 14

    # Edificio de la ciudad -> fachada del tamaño exacto de su huella
    python tools/procesar_higgsfield.py fachada edificio.png assets/ciudad/fachadas/hospital.png \\
        --ancho 264 --alto 144

    # Muro visto de frente -> franja repetible en horizontal (la cara del muro)
    python tools/procesar_higgsfield.py muro muro.png assets/mazmorras/hospital/muro.png \\
        --alto 18 --y0 0.45 --y1 1

Por qué hace falta: la IA entrega imágenes de 1024 px con "píxeles" de tamaño
irregular, colores casi iguales por miles y bordes suavizados. El juego dibuja
pixel art a 1 píxel de arte = 3 px de pantalla, así que cada pieza se:

    1. separa del fondo verde (clave de croma) y del resto de objetos
       (componentes conexos sobre la máscara: cada objeto es una isla);
    2. reduce a su tamaño en píxeles de arte (--alto o --lado) con promedio;
    3. cuantiza a una paleta corta (k-medias a mano, --colores) para que
       tenga los bloques planos del pixel art comprado;
    4. binariza el alfa (sin bordes semitransparentes) y, si es textura,
       se vuelve repetible mezclando cada borde con el opuesto.

Los objetos se nombran en orden de lectura (filas de arriba abajo, luego de
izquierda a derecha), el mismo orden en que el prompt los pide.
"""

import argparse
import os
import random
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
import pygame  # noqa: E402

UMBRAL_ALFA = 128
AREA_MINIMA = 900  # px de la imagen original: ignora motas sueltas


# ----------------------------------------------------------------------
# Croma y componentes
# ----------------------------------------------------------------------

def es_fondo(color):
    r, g, b = color[:3]
    return g > 110 and g - max(r, b) > 45


def quitar_verde(imagen):
    """Vuelve transparente el fondo verde y le quita el tinte verde al borde."""
    ancho, alto = imagen.get_size()
    for y in range(alto):
        for x in range(ancho):
            r, g, b, a = imagen.get_at((x, y))
            if es_fondo((r, g, b)):
                imagen.set_at((x, y), (0, 0, 0, 0))
            elif g - max(r, b) > 12:
                imagen.set_at((x, y), (r, max(r, b), b, a))


def componentes(imagen, paso=2, margen=6):
    """Rectángulos de cada isla opaca (BFS sobre una rejilla de `paso` px)."""
    ancho, alto = imagen.get_size()
    w, h = ancho // paso, alto // paso
    opaco = [[imagen.get_at((x * paso, y * paso))[3] >= UMBRAL_ALFA for x in range(w)] for y in range(h)]
    visto = [[False] * w for _ in range(h)]
    cajas = []
    for y0 in range(h):
        for x0 in range(w):
            if not opaco[y0][x0] or visto[y0][x0]:
                continue
            cola = [(x0, y0)]
            visto[y0][x0] = True
            minx = maxx = x0
            miny = maxy = y0
            celdas = 0
            while cola:
                x, y = cola.pop()
                celdas += 1
                minx, maxx, miny, maxy = min(minx, x), max(maxx, x), min(miny, y), max(maxy, y)
                for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                    if 0 <= nx < w and 0 <= ny < h and opaco[ny][nx] and not visto[ny][nx]:
                        visto[ny][nx] = True
                        cola.append((nx, ny))
            if celdas * paso * paso >= AREA_MINIMA:
                cajas.append(pygame.Rect(minx * paso, miny * paso, (maxx - minx + 1) * paso, (maxy - miny + 1) * paso))
    return _fusionar_cercanas(cajas, margen)


def _fusionar_cercanas(cajas, margen=6):
    """Une islas que se tocan casi (una sombra o una pata separada del cuerpo)."""
    cambiado = True
    while cambiado:
        cambiado = False
        for i in range(len(cajas)):
            for j in range(i + 1, len(cajas)):
                if cajas[i].inflate(margen * 2, margen * 2).colliderect(cajas[j]):
                    cajas[i] = cajas[i].union(cajas[j])
                    del cajas[j]
                    cambiado = True
                    break
            if cambiado:
                break
    return cajas


def orden_lectura(cajas):
    """Filas por solapamiento vertical, luego de izquierda a derecha."""
    cajas = sorted(cajas, key=lambda r: r.centery)
    filas = []
    for caja in cajas:
        for fila in filas:
            if abs(fila[0].centery - caja.centery) < max(fila[0].height, caja.height) * 0.5:
                fila.append(caja)
                break
        else:
            filas.append([caja])
    return [c for fila in filas for c in sorted(fila, key=lambda r: r.x)]


# ----------------------------------------------------------------------
# Reducción y paleta
# ----------------------------------------------------------------------

def reducir(imagen, ancho, alto):
    """Promedio por área (smoothscale) y alfa binario."""
    chica = pygame.transform.smoothscale(imagen, (max(1, ancho), max(1, alto)))
    for y in range(chica.get_height()):
        for x in range(chica.get_width()):
            r, g, b, a = chica.get_at((x, y))
            chica.set_at((x, y), (r, g, b, 255 if a >= UMBRAL_ALFA else 0))
    return chica


def kmedias(colores, k, iteraciones=12, semilla=7):
    """Paleta de k colores para la lista de colores (r, g, b)."""
    unicos = list(set(colores))
    if len(unicos) <= k:
        return unicos
    rng = random.Random(semilla)
    centros = rng.sample(unicos, k)
    for _ in range(iteraciones):
        grupos = [[] for _ in centros]
        for c in colores:
            grupos[_mas_cercano(c, centros)].append(c)
        nuevos = []
        for centro, grupo in zip(centros, grupos):
            if grupo:
                n = len(grupo)
                nuevos.append(tuple(sum(c[i] for c in grupo) // n for i in range(3)))
            else:
                nuevos.append(centro)
        if nuevos == centros:
            break
        centros = nuevos
    return centros


def _mas_cercano(color, paleta):
    mejor, distancia = 0, None
    for i, p in enumerate(paleta):
        d = (color[0] - p[0]) ** 2 + (color[1] - p[1]) ** 2 + (color[2] - p[2]) ** 2
        if distancia is None or d < distancia:
            mejor, distancia = i, d
    return mejor


def cuantizar(imagen, k):
    colores = [imagen.get_at((x, y))[:3] for y in range(imagen.get_height()) for x in range(imagen.get_width())
               if imagen.get_at((x, y))[3]]
    if not colores:
        return
    paleta = kmedias(colores, k)
    for y in range(imagen.get_height()):
        for x in range(imagen.get_width()):
            r, g, b, a = imagen.get_at((x, y))
            if a:
                imagen.set_at((x, y), (*paleta[_mas_cercano((r, g, b), paleta)], 255))


def contorno(imagen, color=(20, 16, 30)):
    """Contorno oscuro de 1 px por fuera de la silueta, como el pack comprado."""
    ancho, alto = imagen.get_size()
    salida = pygame.Surface((ancho + 2, alto + 2), pygame.SRCALPHA)
    salida.blit(imagen, (1, 1))
    for y in range(alto + 2):
        for x in range(ancho + 2):
            if salida.get_at((x, y))[3]:
                continue
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = x + dx, y + dy
                if 0 <= nx < ancho + 2 and 0 <= ny < alto + 2 and salida.get_at((nx, ny))[3] == 255 \
                        and (nx, ny) != (x, y) and _es_original(salida, nx, ny, color):
                    salida.set_at((x, y), (*color, 255))
                    break
    return salida


def _es_original(superficie, x, y, color):
    return superficie.get_at((x, y))[:3] != color


def repetible(imagen, fraccion=0.25, vertical=True):
    """Mezcla cada borde con el opuesto (`fraccion` del lado) para que la baldosa no deje costura."""
    ancho, alto = imagen.get_size()
    base = imagen.copy()
    banda = max(2, round(ancho * fraccion))
    for y in range(alto):
        for i in range(banda):
            t = 0.5 * (1 - i / banda)
            a, b = base.get_at((i, y)), base.get_at((ancho - 1 - i, y))
            imagen.set_at((i, y), _mezcla(a, b, t))
            imagen.set_at((ancho - 1 - i, y), _mezcla(b, a, t))
    if not vertical:
        return
    base = imagen.copy()
    banda = max(2, round(alto * fraccion))
    for x in range(ancho):
        for i in range(banda):
            t = 0.5 * (1 - i / banda)
            a, b = base.get_at((x, i)), base.get_at((x, alto - 1 - i))
            imagen.set_at((x, i), _mezcla(a, b, t))
            imagen.set_at((x, alto - 1 - i), _mezcla(b, a, t))


def _mezcla(a, b, t):
    return tuple(round(a[i] * (1 - t) + b[i] * t) for i in range(3)) + (255,)


# ----------------------------------------------------------------------
# Comandos
# ----------------------------------------------------------------------

def procesar_props(entrada, carpeta, nombres, alto, colores, con_contorno, margen=6):
    imagen = pygame.image.load(entrada).convert_alpha()
    quitar_verde(imagen)
    cajas = orden_lectura(componentes(imagen, margen=margen))
    os.makedirs(carpeta, exist_ok=True)
    print(f"{len(cajas)} objetos encontrados, {len(nombres)} nombres")
    escala = None
    for i, caja in enumerate(cajas):
        nombre = nombres[i] if i < len(nombres) else f"extra_{i}"
        if nombre == "-":
            continue
        recorte = imagen.subsurface(caja).copy()
        # Una sola escala para toda la hoja: los objetos conservan sus
        # proporciones entre sí (una camilla es más grande que un monitor).
        if escala is None:
            escala = alto / max(c.height for c in cajas)
        pieza = reducir(recorte, round(caja.width * escala), round(caja.height * escala))
        cuantizar(pieza, colores)
        if con_contorno:
            pieza = contorno(pieza)
        pygame.image.save(pieza, os.path.join(carpeta, f"{nombre}.png"))
        print(f"  {nombre}: {pieza.get_size()}")


def procesar_muro(entrada, salida, alto, colores, y0, y1, oscurecer):
    """Franja frontal del muro: banda vertical [y0, y1] de la imagen, reducida
    a `alto` píxeles de arte, repetible solo en horizontal."""
    imagen = pygame.image.load(entrada).convert_alpha()
    ancho_o, alto_o = imagen.get_size()
    zona = pygame.Rect(0, round(alto_o * y0), ancho_o, round(alto_o * (y1 - y0)))
    ancho = round(zona.width * alto / zona.height)
    pieza = reducir(imagen.subsurface(zona).copy(), ancho, alto)
    cuantizar(pieza, colores)
    repetible(pieza, 0.08, vertical=False)
    if oscurecer:
        pieza.fill((oscurecer, oscurecer, oscurecer), special_flags=pygame.BLEND_RGB_MULT)
    os.makedirs(os.path.dirname(salida), exist_ok=True)
    pygame.image.save(pieza, salida)
    print(f"muro {salida}: {pieza.get_size()}")


def procesar_fachada(entrada, salida, ancho, alto, colores):
    """Edificio entero: sin el verde, recortado a su silueta y reducido a
    exactamente `ancho` x `alto` píxeles de arte (su huella en la ciudad /
    la escala entera con que se dibuja)."""
    imagen = pygame.image.load(entrada).convert_alpha()
    quitar_verde(imagen)
    silueta = imagen.get_bounding_rect(min_alpha=UMBRAL_ALFA)
    pieza = reducir(imagen.subsurface(silueta).copy(), ancho, alto)
    cuantizar(pieza, colores)
    os.makedirs(os.path.dirname(salida), exist_ok=True)
    pygame.image.save(pieza, salida)
    print(f"fachada {salida}: {pieza.get_size()}")


def procesar_textura(entrada, salida, lado, colores, recorte, banda=0.25):
    imagen = pygame.image.load(entrada).convert_alpha()
    ancho, alto = imagen.get_size()
    corte = round(min(ancho, alto) * recorte)
    zona = pygame.Rect(0, 0, corte, corte)
    zona.center = (ancho // 2, alto // 2)
    pieza = reducir(imagen.subsurface(zona).copy(), lado, lado)
    cuantizar(pieza, colores)
    repetible(pieza, banda)
    os.makedirs(os.path.dirname(salida), exist_ok=True)
    pygame.image.save(pieza, salida)
    print(f"textura {salida}: {pieza.get_size()}")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="modo", required=True)
    p = sub.add_parser("props")
    p.add_argument("entrada")
    p.add_argument("carpeta")
    p.add_argument("--nombres", default="", help="separados por coma, en orden de lectura; '-' descarta")
    p.add_argument("--alto", type=int, default=40, help="alto en píxeles de arte del objeto más alto")
    p.add_argument("--colores", type=int, default=20)
    p.add_argument("--sin-contorno", action="store_true")
    p.add_argument("--margen", type=int, default=6, help="px entre islas que se unen en un objeto")
    t = sub.add_parser("textura")
    t.add_argument("entrada")
    t.add_argument("salida")
    t.add_argument("--lado", type=int, default=32)
    t.add_argument("--colores", type=int, default=12)
    t.add_argument("--recorte", type=float, default=0.6, help="fracción central de la imagen que se usa")
    t.add_argument("--banda", type=float, default=0.25, help="fracción del borde que se mezcla con el opuesto")
    m = sub.add_parser("muro")
    m.add_argument("entrada")
    m.add_argument("salida")
    m.add_argument("--alto", type=int, default=18, help="alto en píxeles de arte de la franja")
    m.add_argument("--colores", type=int, default=16)
    m.add_argument("--y0", type=float, default=0.0, help="fracción de alto donde empieza la banda")
    m.add_argument("--y1", type=float, default=1.0)
    m.add_argument("--oscurecer", type=int, default=0, help="multiplica por N/255 (0 = no)")
    f = sub.add_parser("fachada")
    f.add_argument("entrada")
    f.add_argument("salida")
    f.add_argument("--ancho", type=int, required=True)
    f.add_argument("--alto", type=int, required=True)
    f.add_argument("--colores", type=int, default=32)
    args = parser.parse_args()
    pygame.init()
    pygame.display.set_mode((1, 1))
    if args.modo == "props":
        nombres = [n.strip() for n in args.nombres.split(",") if n.strip()]
        procesar_props(args.entrada, args.carpeta, nombres, args.alto, args.colores, not args.sin_contorno, args.margen)
    elif args.modo == "fachada":
        procesar_fachada(args.entrada, args.salida, args.ancho, args.alto, args.colores)
    elif args.modo == "muro":
        procesar_muro(args.entrada, args.salida, args.alto, args.colores, args.y0, args.y1, args.oscurecer)
    else:
        procesar_textura(args.entrada, args.salida, args.lado, args.colores, args.recorte, args.banda)


if __name__ == "__main__":
    sys.exit(main())
