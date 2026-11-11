"""Dónde va cada objeto de un cuarto (puro: sin pygame).

Recibe las reglas de la variante del cuarto (assets.DECORADO_VARIANTE), el
tamaño de cada imagen y las zonas que no se pueden tapar, y devuelve una
lista de (nombre, (x, y, w, h)). Los dibuja src/ui/decor_mazmorra.py (los
chicos, horneados en el fondo) y src/ui/cobertura_render.py (los sólidos:
son las coberturas rompibles de src/dungeon/coberturas.py).

Reglas de juego que garantiza (y prueba tests/test_decor_mazmorra.py):
    - todo objeto queda dentro del piso;
    - ninguno toca las zonas libres (puertas, centro donde se aparece y,
      en el cuarto final, la terminal);
    - los de "fondo", "costados", "esquinas" y "sueltos" viven junto a los
      muros: no entran al rectángulo del piso recortado `banda` px por lado;
    - los de "centro" son las coberturas del medio del cuarto: van en
      ranuras simétricas y dejan `paso` px o más entre sus bases y hasta
      los muros (cabe el enemigo más ancho), y `paso_muebles` px hasta la
      base de cualquier otro objeto (cabe el jugador);
    - dos objetos nunca se enciman (quedan a `separacion` px o más);
    - ningún hueco entre dos bases enfrentadas, ni entre una base y un
      muro, queda "a medias": o mide menos de `cerrado` px (no entra ni el
      jugador) o `paso` px o más (entra cualquier enemigo). No hay rincón
      donde el jugador quepa y quien lo persigue no.

Lugares de una regla (lugar, objetos, cantidad):
    "fondo"    de izquierda a derecha junto al muro de arriba;
    "costados" por el muro izquierdo y el derecho, de arriba abajo;
    "esquinas" en las esquinas de abajo;
    "sueltos"  al azar, solo dentro de la franja junto a los muros;
    "centro"   en las ranuras del medio, por pares espejo (izquierda y
               derecha llevan el mismo objeto).
"""

from src.dungeon.coberturas import es_solido, hitbox_de

# Formaciones del centro: cada una es una lista de filas (altura, distancia).
# altura "alta": la base queda bajo los muebles del muro de arriba;
# altura "baja": la base queda sobre el muro de abajo. `distancia` = px
# del centro del cuarto al borde interior del objeto (el par es espejo).
FORMACIONES_CENTRO = (
    (("alta", 260), ("baja", 120)),  # en X: lejos arriba, cerca abajo
    (("alta", 120), ("baja", 260)),  # en X invertida
    (("alta", 190), ("baja", 190)),  # dos columnas
)
BASE_FILA_ALTA = 216  # px del borde superior del piso al tope de la base (bajo el mueble más alto del muro, con paso)
BASE_FILA_BAJA = 80  # px del borde inferior del piso al fondo de la base
ALTO_CARA_MURO = 36  # px de la cara del muro de arriba (temas_mazmorra.ALTO_CARA_MURO * P)
# El plan se arma en la rejilla de 3 px del fondo pintado y el cuarto real
# puede quedar corrido 2-3 px: los huecos se exigen con este margen.
TOLERANCIA_PLAN = 4
AJUSTE_DISTANCIA_CENTRO = 36  # px que se corre un par que no cabe donde pide la formación


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


def base(rect, piso):
    """Base sólida de un objeto en este piso (la hitbox de su cobertura).
    Contra el muro de arriba, llega hasta el borde del cuarto."""
    return hitbox_de(rect, piso[1], ALTO_CARA_MURO)


def hueco_a_medias(a, b, cerrado, paso):
    """¿Entre las bases a y b queda un pasillo donde cabe el jugador pero no
    un enemigo ancho? Solo cuenta si están enfrentadas (se solapan en un
    eje): el hueco es la distancia en el otro. O(1)."""
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    dx = max(bx - (ax + aw), ax - (bx + bw))
    dy = max(by - (ay + ah), ay - (by + bh))
    if dx < 0 and dy < 0:
        return False  # se enciman: eso lo decide `choca`
    if dy < 0:
        return cerrado <= dx < paso
    if dx < 0:
        return cerrado <= dy < paso
    return False  # en diagonal: no forman pasillo


def hueco_al_muro(b, piso, cerrado, paso):
    """Lo mismo contra los cuatro muros del piso."""
    x, y, w, h = b
    px, py, pw, ph = piso
    arriba = y - py  # negativo: está contra el muro de arriba (su base lo cubre)
    return any(cerrado <= hueco < paso for hueco in (x - px, arriba, px + pw - (x + w), py + ph - (y + h)))


def planificar(reglas, tamanos, piso, libres, banda, rng, separacion=10, paso=72, paso_muebles=44, cerrado=30):
    """Lista de (nombre, rect). `tamanos` = {nombre: (w, h)}: un objeto sin
    tamaño (su imagen falta) simplemente no se coloca."""
    centro = centro_libre(piso, banda)
    cerrado, paso = cerrado - TOLERANCIA_PLAN, paso + TOLERANCIA_PLAN
    ocupados = [tuple(r) for r in libres]
    bases = []  # bases sólidas ya puestas
    bases_centro = []
    colocados = []

    def registrar(nombre, rect):
        ocupados.append(rect)
        colocados.append((nombre, rect))
        if es_solido(nombre):
            bases.append(base(rect, piso))

    def intentar(nombre, x, y):
        w, h = tamanos[nombre]
        rect = (round(x), round(y), w, h)
        if not dentro(rect, piso) or choca(rect, centro):
            return False
        if any(choca(rect, otro, separacion) for otro in ocupados):
            return False
        if es_solido(nombre):
            suya = base(rect, piso)
            # Ni rincones donde solo quepa el jugador, ni una cobertura del centro sin paso.
            if hueco_al_muro(suya, piso, cerrado, paso):
                return False
            if any(hueco_a_medias(suya, otra, cerrado, paso) for otra in bases):
                return False
            if any(choca(suya, otra, paso_muebles) for otra in bases_centro):
                return False
        registrar(nombre, rect)
        return True

    def intentar_centro(nombre, x, y, solo_probar=False):
        w, h = tamanos[nombre]
        rect = (round(x), round(y), w, h)
        suya = base(rect, piso)
        px, py, pw, ph = piso
        if not dentro(suya, (px + paso, py + paso, pw - 2 * paso, ph - 2 * paso)):
            return False
        if any(choca(rect, otro, separacion) for otro in ocupados):
            return False
        if any(choca(suya, otra, paso) for otra in bases_centro):
            return False
        if any(choca(suya, otra, paso_muebles) or hueco_a_medias(suya, otra, cerrado, paso) for otra in bases):
            return False
        if not solo_probar:
            registrar(nombre, rect)
            bases_centro.append(suya)
        return True

    for lugar, objetos, cantidad in reglas:
        objetos = [o for o in objetos if o in tamanos]
        if not objetos:
            continue
        if lugar == "fondo":
            _fondo(objetos, cantidad, tamanos, piso, rng, separacion, intentar, paso)
        elif lugar == "costados":
            _costados(objetos, cantidad, tamanos, piso, rng, separacion, intentar, paso)
        elif lugar == "esquinas":
            _esquinas(objetos, cantidad, tamanos, piso, intentar)
        elif lugar == "sueltos":
            _sueltos(objetos, cantidad, tamanos, piso, rng, intentar)
        elif lugar == "centro":
            _centro(objetos, cantidad, tamanos, piso, rng, intentar_centro)
    return colocados


def _centro(objetos, cantidad, tamanos, piso, rng, intentar_centro):
    """Coberturas del medio: una formación al azar, cada fila un par espejo
    con el mismo objeto. `cantidad` = objetos en total (2 por fila)."""
    px, py, pw, ph = piso
    cx = px + pw // 2
    formacion = rng.choice(FORMACIONES_CENTRO)
    for i, (altura, distancia) in enumerate(formacion[:max(1, cantidad // 2)]):
        nombre = objetos[i % len(objetos)]
        w, h = tamanos[nombre]
        alto_base = hitbox_de((0, 0, w, h))[3]
        if altura == "alta":
            y = py + BASE_FILA_ALTA + alto_base - h
        else:
            y = py + ph - BASE_FILA_BAJA - h
        # El par va espejo: se busca la distancia más parecida a la de la
        # formación en la que caben los dos (un objeto ancho se acerca al
        # centro para no tapar las puertas de los costados).
        for d in (distancia, distancia - AJUSTE_DISTANCIA_CENTRO, distancia + AJUSTE_DISTANCIA_CENTRO,
                  distancia - 2 * AJUSTE_DISTANCIA_CENTRO, distancia - 3 * AJUSTE_DISTANCIA_CENTRO):
            if (intentar_centro(nombre, cx - d - w, y, solo_probar=True)
                    and intentar_centro(nombre, cx + d, y, solo_probar=True)):
                intentar_centro(nombre, cx - d - w, y)
                intentar_centro(nombre, cx + d, y)
                break
        else:
            # No cabe el par (en el cuarto final, la terminal ocupa un lado): el que quepa.
            intentar_centro(nombre, cx - distancia - w, y)
            intentar_centro(nombre, cx + distancia, y)


def _fondo(objetos, cantidad, tamanos, piso, rng, separacion, intentar, paso=72):
    """Hilera contra el muro de arriba, en grupos: dentro de un grupo los
    muebles van casi pegados (no cabe nadie entre ellos) y entre grupos
    queda un hueco ancho, de `paso` px o más."""
    px, py, pw, _ = piso
    x = px + rng.randint(6, 40)
    i = puestos = 0
    while x < px + pw and puestos < cantidad:
        nombre = objetos[i % len(objetos)]
        if intentar(nombre, x, py + 4):
            puestos += 1
            i += 1
            x += tamanos[nombre][0] + separacion
            x += rng.randint(0, 6) if rng.random() < 0.7 else paso + rng.randint(0, 30)
        else:
            x += 16


def _costados(objetos, cantidad, tamanos, piso, rng, separacion, intentar, paso=72):
    """Por cada muro lateral, de arriba abajo: entre la base de un mueble y
    la del siguiente quedan `paso` px o más (se entra a cubrirse entre ellos
    y cualquier enemigo también)."""
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
                siguiente = objetos[i % len(objetos)]
                alto_s = tamanos[siguiente][1]
                detras = alto_s - hitbox_de((0, 0, tamanos[siguiente][0], alto_s))[3]
                y += h + max(separacion + rng.randint(10, 40), paso - detras + rng.randint(0, 24))
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
