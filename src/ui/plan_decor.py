"""Dónde va cada objeto decorativo de un cuarto (puro: sin pygame).

Recibe las reglas de la variante del cuarto (assets.DECORADO_VARIANTE), el
tamaño de cada imagen y las zonas que no se pueden tapar, y devuelve una
lista de (nombre, (x, y, w, h)). Lo dibuja src/ui/decor_mazmorra.py.

Reglas de juego que garantiza (y prueba tests/test_decor_mazmorra.py):
    - todo objeto queda dentro del piso;
    - ninguno toca las zonas libres (puertas y centro de la mazmorra);
    - ninguno entra al centro de combate: el rectángulo del piso recortado
      `banda` px por cada lado queda vacío, así la decoración vive junto a
      los muros y las esquinas;
    - dos objetos nunca se encimen (quedan a `separacion` px o más).

Lugares de una regla (lugar, objetos, cantidad):
    "fondo"    de izquierda a derecha junto al muro de arriba;
    "costados" por el muro izquierdo y el derecho, de arriba abajo;
    "esquinas" en las esquinas de abajo;
    "sueltos"  al azar, solo dentro de la franja junto a los muros.
"""


def choca(a, b, margen=0):
    """¿Se tocan los rects (x, y, w, h) a y b, dejando `margen` px entre ellos?"""
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return (ax < bx + bw + margen and bx < ax + aw + margen
            and ay < by + bh + margen and by < ay + ah + margen)


def dentro(a, b):
    """¿El rect a cabe entero en b?"""
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return ax >= bx and ay >= by and ax + aw <= bx + bw and ay + ah <= by + bh


def centro_libre(piso, banda):
    """El rectángulo de combate que la decoración no puede pisar."""
    x, y, w, h = piso
    return (x + banda, y + banda, max(0, w - 2 * banda), max(0, h - 2 * banda))


def planificar(reglas, tamanos, piso, libres, banda, rng, separacion=10):
    """Lista de (nombre, rect). `tamanos` = {nombre: (w, h)}: un objeto sin
    tamaño (su imagen falta) simplemente no se coloca."""
    px, py, pw, ph = piso
    centro = centro_libre(piso, banda)
    ocupados = [tuple(r) for r in libres]
    colocados = []

    def intentar(nombre, x, y):
        w, h = tamanos[nombre]
        rect = (round(x), round(y), w, h)
        if not dentro(rect, piso) or choca(rect, centro):
            return False
        if any(choca(rect, otro, separacion) for otro in ocupados):
            return False
        ocupados.append(rect)
        colocados.append((nombre, rect))
        return True

    for lugar, objetos, cantidad in reglas:
        objetos = [o for o in objetos if o in tamanos]
        if not objetos:
            continue
        if lugar == "fondo":
            _fondo(objetos, cantidad, tamanos, piso, rng, separacion, intentar)
        elif lugar == "costados":
            _costados(objetos, cantidad, tamanos, piso, rng, separacion, intentar)
        elif lugar == "esquinas":
            _esquinas(objetos, cantidad, tamanos, piso, intentar)
        elif lugar == "sueltos":
            _sueltos(objetos, cantidad, tamanos, piso, rng, intentar)
    return colocados


def _fondo(objetos, cantidad, tamanos, piso, rng, separacion, intentar):
    px, py, pw, _ = piso
    x = px + rng.randint(6, 40)
    i = puestos = 0
    while x < px + pw and puestos < cantidad:
        nombre = objetos[i % len(objetos)]
        if intentar(nombre, x, py + 4):
            puestos += 1
            i += 1
            x += tamanos[nombre][0] + separacion + rng.randint(4, 30)
        else:
            x += 16


def _costados(objetos, cantidad, tamanos, piso, rng, separacion, intentar):
    px, py, pw, ph = piso
    for lado in (0, 1):
        y = py + rng.randint(70, 120)
        i = lado  # el muro derecho empieza en otro objeto: no son espejos
        puestos = 0
        while y < py + ph and puestos < cantidad:
            nombre = objetos[i % len(objetos)]
            w, h = tamanos[nombre]
            x = px + 6 if lado == 0 else px + pw - w - 6
            if intentar(nombre, x, y):
                puestos += 1
                i += 1
                y += h + separacion + rng.randint(10, 40)
            else:
                y += 16


def _esquinas(objetos, cantidad, tamanos, piso, intentar):
    px, py, pw, ph = piso
    for k, nombre in enumerate(objetos[:cantidad]):
        w, h = tamanos[nombre]
        for paso in range(8):  # si la esquina está ocupada, se corre hacia el centro
            dx = 6 + paso * 24
            x = px + dx if k % 2 == 0 else px + pw - w - dx
            if intentar(nombre, x, py + ph - h - 6):
                break


def _sueltos(objetos, cantidad, tamanos, piso, rng, intentar):
    px, py, pw, ph = piso
    for _ in range(cantidad):
        nombre = rng.choice(objetos)
        w, h = tamanos[nombre]
        for _ in range(40):
            x = rng.randint(px, max(px, px + pw - w))
            y = rng.randint(py, max(py, py + ph - h))
            if intentar(nombre, x, y):
                break
