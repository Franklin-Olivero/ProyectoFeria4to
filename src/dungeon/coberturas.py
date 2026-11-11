"""Coberturas rompibles de un cuarto (lógica pura, sin Pygame).

Los muebles de una mazmorra (pupitres, camillas, escritorios, columnas...)
son sólidos: ni jugadores ni enemigos los atraviesan y frenan las balas de
cualquiera. Cada impacto les quita vida; al llegar a cero se rompen y
dejan de estorbar. Sirven para cubrirse, pero no para siempre.

    Cobertura              un objeto: imagen, hitbox, vida y etapa de daño
    hitbox_de(rect)        la base sólida de una imagen (vista 3/4)
    crear(plan)            lista de Cobertura desde [(nombre, rect, solido, hitbox)]
    solidas(coberturas)    hitboxes de las que siguen en pie
    separar(...)           mueve un cuerpo sin atravesarlas (resbala por el eje libre)
    expulsar(...)          saca un cuerpo que quedó dentro de una
    golpeada(rect, cobs)   la primera cobertura en pie que toca un rect (una bala)

Todos los rects son tuplas (x, y, ancho, alto) en px de pantalla.
Los números (vida por clase, fracción de hitbox, etapas) viven en balance.py.
"""

from src.core.balance import (
    CLASE_COBERTURA,
    CLASE_COBERTURA_PREDETERMINADA,
    DURACION_GOLPE_COBERTURA,
    FRACCION_HITBOX_COBERTURA,
    FRACCIONES_ETAPA_COBERTURA,
    MARGEN_LATERAL_HITBOX_COBERTURA,
    MARGEN_MURO_COBERTURA,
    OBJETOS_SIN_HITBOX,
    VIDA_COBERTURA,
)

ETAPA_ROTA = len(FRACCIONES_ETAPA_COBERTURA) + 1  # 0 = intacta ... la última = rota


def es_solido(nombre):
    """¿El objeto `nombre` tiene hitbox? Los chicos del piso son solo decoración."""
    return nombre not in OBJETOS_SIN_HITBOX


def vida_de(nombre):
    return VIDA_COBERTURA[CLASE_COBERTURA.get(nombre, CLASE_COBERTURA_PREDETERMINADA)]


def hitbox_de(rect, techo=None, muro=0):
    """Base sólida de la imagen `rect`: su parte de abajo, un poco más angosta.
    La parte de arriba es la altura del objeto: se puede pasar por detrás.
    `techo` = y donde empieza el piso (el pie del muro de arriba): si la
    base queda a menos de MARGEN_MURO_COBERTURA de él, el mueble está contra
    la pared y su hitbox sube hasta el muro (detrás no cabe nadie). `muro`
    = alto de la cara del muro sobre el piso: los personajes pueden pisar
    esa franja, así que la hitbox la cubre también."""
    x, y, ancho, alto = rect
    alto_base = max(8, round(alto * FRACCION_HITBOX_COBERTURA))
    margen = MARGEN_LATERAL_HITBOX_COBERTURA if ancho > 4 * MARGEN_LATERAL_HITBOX_COBERTURA else 0
    arriba = y + alto - alto_base
    if techo is not None and arriba - techo < MARGEN_MURO_COBERTURA:
        arriba = min(arriba, techo - muro)
    return (x + margen, arriba, ancho - 2 * margen, y + alto - arriba)


class Cobertura:
    """Un mueble sólido con vida. `rect` es su imagen; `hitbox`, su base."""

    def __init__(self, nombre, rect, vida=None, hitbox=None):
        self.nombre = nombre
        self.rect = tuple(rect)
        self.hitbox = tuple(hitbox) if hitbox is not None else hitbox_de(self.rect)
        self.vida_maxima = vida if vida is not None else vida_de(nombre)
        self.vida = self.vida_maxima
        self.tiempo_golpe = 0.0  # s que le quedan de temblor tras el último impacto

    @property
    def rota(self):
        return self.vida <= 0

    @property
    def fraccion_vida(self):
        return max(0.0, self.vida / self.vida_maxima)

    @property
    def etapa(self):
        """0 intacta, 1 agrietada, 2 muy dañada, ETAPA_ROTA rota. O(1)."""
        if self.rota:
            return ETAPA_ROTA
        return sum(self.fraccion_vida <= limite for limite in FRACCIONES_ETAPA_COBERTURA)

    def recibir_impacto(self, danio=1):
        """Le quita `danio` de vida. True si este impacto la rompió."""
        if self.rota:
            return False
        self.vida = max(0, self.vida - danio)
        self.tiempo_golpe = DURACION_GOLPE_COBERTURA
        return self.rota

    def romper(self):
        """La destruye de golpe (el jefe la aplasta). True si estaba en pie."""
        return self.recibir_impacto(self.vida)

    def actualizar(self, dt):
        self.tiempo_golpe = max(0.0, self.tiempo_golpe - dt)


def crear(plan):
    """Coberturas de un plan [(nombre, rect, solido[, hitbox])]: solo las
    sólidas. Sin `hitbox` en el plan, cada una calcula la suya (hitbox_de)."""
    return [Cobertura(nombre, rect, hitbox=resto[0] if resto else None)
            for nombre, rect, solido, *resto in plan if solido]


def solidas(coberturas):
    """Hitboxes de las coberturas que siguen en pie."""
    return [c.hitbox for c in coberturas if not c.rota]


def se_tocan(a, b):
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return ax < bx + bw and bx < ax + aw and ay < by + bh and by < ay + ah


def golpeada(rect, coberturas):
    """La primera cobertura en pie cuya hitbox toca `rect`, o None. O(n)."""
    for cobertura in coberturas:
        if not cobertura.rota and se_tocan(rect, cobertura.hitbox):
            return cobertura
    return None


def _cuerpo(centro, tamanio):
    ancho, alto = tamanio
    return (centro[0] - ancho / 2, centro[1] - alto / 2, ancho, alto)


def separar(anterior, nuevo, tamanio, obstaculos):
    """Mueve un cuerpo de `tamanio` (ancho, alto) del centro `anterior` al
    centro `nuevo` sin atravesar `obstaculos` (hitboxes).

    Los ejes se resuelven por separado, primero x y luego y: contra un
    mueble el cuerpo se detiene en ese eje y resbala por el otro.
    Devuelve (x, y, choco_x, choco_y). O(n) con n obstáculos."""
    ancho, alto = tamanio
    x, y = anterior
    choco_x = choco_y = False
    nx = nuevo[0]
    for ox, oy, ow, oh in obstaculos:
        if se_tocan(_cuerpo((nx, y), tamanio), (ox, oy, ow, oh)):
            # Se queda pegado a la cara del mueble que mira a donde venía.
            nx = ox - ancho / 2 if nx > x else ox + ow + ancho / 2
            if nx == x:
                nx = ox - ancho / 2 if x < ox + ow / 2 else ox + ow + ancho / 2
            choco_x = True
    x = nx
    ny = nuevo[1]
    for ox, oy, ow, oh in obstaculos:
        if se_tocan(_cuerpo((x, ny), tamanio), (ox, oy, ow, oh)):
            ny = oy - alto / 2 if ny > y else oy + oh + alto / 2
            if ny == y:
                ny = oy - alto / 2 if y < oy + oh / 2 else oy + oh + alto / 2
            choco_y = True
    return (x, ny, choco_x, choco_y)


def expulsar(centro, tamanio, obstaculos, limites=None, vueltas=4):
    """Saca un cuerpo que quedó dentro de un mueble (apareció ahí, lo
    empujaron): lo corre por el lado más corto. `limites` (izq, arriba,
    der, abajo) impide sacarlo del cuarto: si el lado más corto da contra
    el muro, sale por otro. Devuelve el centro libre (o el mejor hallado)."""
    ancho, alto = tamanio
    x, y = centro
    for _ in range(vueltas):
        dentro_de = [o for o in obstaculos if se_tocan(_cuerpo((x, y), tamanio), o)]
        if not dentro_de:
            break
        ox, oy, ow, oh = dentro_de[0]
        salidas = [
            (abs(x - (ox - ancho / 2)), (ox - ancho / 2, y)),
            (abs(x - (ox + ow + ancho / 2)), (ox + ow + ancho / 2, y)),
            (abs(y - (oy - alto / 2)), (x, oy - alto / 2)),
            (abs(y - (oy + oh + alto / 2)), (x, oy + oh + alto / 2)),
        ]
        if limites is not None:
            izq, arriba, der, abajo = limites
            salidas = [s for s in salidas
                       if izq + ancho / 2 <= s[1][0] <= der - ancho / 2
                       and arriba + alto / 2 <= s[1][1] <= abajo - alto / 2] or salidas
        x, y = min(salidas, key=lambda s: s[0])[1]
    return (x, y)
