"""Animación de los personajes armada desde los cuadros que ya existen (lógica pura, sin pygame).

Las hojas de Higgsfield traen solo 4 cuadros (quieto, paso_a, paso_b y dash):
al caminar solo cambiaban los pies y quieto el personaje era una foto. Sin
dibujar arte nuevo, con el mapa de partes de cada hoja (qué píxel es pelo,
piel, ropa, pantalón o zapatos) se arman ciclos con más vida:

    caminar   8 cuadros: en cada pisada el cuerpo baja un píxel y la cabeza
              lo sigue con un cuadro de retraso (rebote con peso), y entre
              pisadas vuelve a subir.
    respirar  quieto: los hombros bajan y suben despacio (respiración) y cada
              tanto parpadea (los ojos se cierran un instante).
    dash      el cuadro de dash con el cuerpo agachado (impulso).

Cómo se mueve una parte: `bajar` corre hacia abajo los renglones de arriba
(la cabeza, o la cabeza y el torso) y deja fijo lo de abajo; lo que baja se
dibuja encima. Los ojos se encuentran como píxeles sin parte encerrados por
piel en la franja de la cara, y `parpadear` los cierra: piel encima y una
línea oscura abajo (el párpado).

Un cuadro es una tupla de filas de RGBA (o None) y su mapa de partes, filas de
nombres de parte (o None). Todo es O(ancho * alto) por cuadro y se arma una
sola vez por personaje (caché en src/ui/sprites.py).
"""

PELO, PIEL, ROPA, PANTALON = "pelo", "piel", "ropa", "pantalon"

# Ciclos: (cuadro base, cuánto baja el cuerpo, cuánto baja además la cabeza, ¿parpadea?, ms).
CICLO_CAMINAR = (
    ("paso_a", 1, 0, False, 75), ("paso_a", 1, 1, False, 75), ("quieto", 0, 1, False, 75), ("quieto", 0, 0, False, 75),
    ("paso_b", 1, 0, False, 75), ("paso_b", 1, 1, False, 75), ("quieto", 0, 1, False, 75), ("quieto", 0, 0, False, 75),
)
CICLO_RESPIRAR = (
    ("quieto", 0, 0, False, 700), ("quieto", 0, 1, False, 350), ("quieto", 1, 0, False, 800),
    ("quieto", 0, 1, False, 350), ("quieto", 0, 0, False, 900), ("quieto", 0, 0, True, 130),
    ("quieto", 0, 0, False, 1100), ("quieto", 0, 1, False, 350), ("quieto", 1, 0, False, 800),
    ("quieto", 0, 1, False, 350), ("quieto", 0, 0, True, 110), ("quieto", 0, 0, False, 150),
    ("quieto", 0, 0, True, 110),  # doble parpadeo de vez en cuando
)
CICLO_DASH = (("dash", 1, 1, False, 120),)
ANIMACION_RESPIRAR = "respirar"

LUZ_OJO = 150  # un píxel de ojo más claro que esto es brillo (al cerrar se vuelve piel)
ALTO_MAXIMO_OJO = 5


def _luz(color):
    return 0.299 * color[0] + 0.587 * color[1] + 0.114 * color[2]


def zonas(partes):
    """(cuello, cadera): primer renglón con ropa y primer renglón con
    pantalón (None si no hay)."""
    cuello = next((y for y, fila in enumerate(partes) if ROPA in fila), None)
    cadera = next((y for y, fila in enumerate(partes) if PANTALON in fila), None)
    return cuello, cadera


def bajar(cuadro, partes, hasta, dy):
    """Corre `dy` píxeles hacia abajo los renglones de arriba de `hasta` (lo
    de abajo queda quieto; lo que baja se dibuja encima)."""
    if dy <= 0 or hasta is None or hasta <= 0:
        return cuadro, partes
    alto = len(cuadro)
    nuevo = [list(fila) for fila in cuadro]
    nuevas = [list(fila) for fila in partes]
    for y in range(min(hasta + dy, alto)):  # se vacía lo que se mueve
        if y < hasta:
            nuevo[y] = [None] * len(cuadro[y])
            nuevas[y] = [None] * len(partes[y])
    for y in range(hasta - 1, -1, -1):
        destino = y + dy
        if destino >= alto:
            continue
        for x, color in enumerate(cuadro[y]):
            if color is not None:
                nuevo[destino][x] = color
                nuevas[destino][x] = partes[y][x]
    return tuple(tuple(f) for f in nuevo), tuple(tuple(f) for f in nuevas)


def ojos(cuadro, partes):
    """Píxeles de los ojos: sin parte, encerrados por piel a izquierda y
    derecha, en la franja de la cara (entre el pelo y el cuello). Lista de
    grupos (cada uno un set de (x, y))."""
    cuello, _ = zonas(partes)
    if cuello is None:
        return []
    filas_piel = [y for y in range(cuello) if PIEL in partes[y]]
    if not filas_piel:
        return []
    arriba, abajo = filas_piel[0], cuello - 1
    candidatos = set()
    for y in range(arriba, abajo):
        fila = partes[y]
        for x, parte in enumerate(fila):
            if parte is not None or cuadro[y][x] is None:
                continue
            izquierda = any(fila[v] == PIEL for v in range(max(0, x - 4), x))
            derecha = any(fila[v] == PIEL for v in range(x + 1, min(len(fila), x + 5)))
            arriba_piel_o_pelo = any(partes[v][x] in (PIEL, PELO) for v in range(max(0, y - 4), y))
            if izquierda and derecha and arriba_piel_o_pelo:
                candidatos.add((x, y))
    grupos = []
    while candidatos:
        semilla = candidatos.pop()
        grupo, cola = {semilla}, [semilla]
        while cola:
            x, y = cola.pop()
            for v in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if v in candidatos:
                    candidatos.discard(v)
                    grupo.add(v)
                    cola.append(v)
        ys = [y for _, y in grupo]
        if 2 <= len(grupo) and max(ys) - min(ys) + 1 <= ALTO_MAXIMO_OJO:
            grupos.append(grupo)
    # Los dos ojos: los dos grupos más grandes, parecidos y a la misma altura.
    # Si no (p. ej. los lentes del Periodista confunden la búsqueda), no hay
    # parpadeo: mejor ojos abiertos que una mancha.
    grupos.sort(key=len, reverse=True)
    if len(grupos) < 2:
        return []
    uno, otro = grupos[0], grupos[1]
    altura = lambda g: sum(y for _, y in g) / len(g)  # noqa: E731
    if len(otro) < len(uno) * 0.6 or abs(altura(uno) - altura(otro)) > 1.5:
        return []
    return [uno, otro]


def parpadear(cuadro, partes, grupos_ojos):
    """El cuadro con los ojos cerrados: cada ojo se tapa con la piel de al
    lado y su renglón de abajo queda como una línea oscura (el párpado)."""
    if not grupos_ojos:
        return cuadro
    nuevo = [list(fila) for fila in cuadro]
    for grupo in grupos_ojos:
        abajo = max(y for _, y in grupo)
        oscuro = min((cuadro[y][x] for x, y in grupo), key=_luz)
        for x, y in grupo:
            if y == abajo:
                nuevo[y][x] = oscuro
            else:
                nuevo[y][x] = _piel_vecina(cuadro, partes, x, y) or nuevo[y][x]
    return tuple(tuple(f) for f in nuevo)


def _piel_vecina(cuadro, partes, x, y):
    fila = partes[y]
    for distancia in range(1, 6):
        for v in (x - distancia, x + distancia):
            if 0 <= v < len(fila) and fila[v] == PIEL:
                return cuadro[y][v]
    return None


def armar_cuadro(cuadros, partes, base, baja_cuerpo, baja_cabeza, parpadea, ojos_de=None):
    """Un cuadro del ciclo: el `base` con el cuerpo (todo lo de arriba de la
    cadera) `baja_cuerpo` píxeles más abajo y la cabeza (arriba del cuello)
    `baja_cabeza` más, y los ojos cerrados si `parpadea`. Devuelve (cuadro, partes)."""
    cuadro, mapa = cuadros[base], partes[base]
    grupos = (ojos_de or {}).get(base) if parpadea else None
    if parpadea:
        cuadro = parpadear(cuadro, mapa, grupos if grupos is not None else ojos(cuadro, mapa))
    cuello, cadera = zonas(mapa)
    cuadro, mapa = bajar(cuadro, mapa, cadera, baja_cuerpo)
    if cuello is not None:
        cuadro, mapa = bajar(cuadro, mapa, cuello + baja_cuerpo, baja_cabeza)
    return cuadro, mapa


def ciclos(cuadros, partes):
    """{animación: [(cuadro, partes, ms)]} con caminar, respirar y dash armados
    desde los cuadros de una hoja (los que falten se reemplazan por "quieto")."""
    disponibles = set(cuadros)
    primero = "quieto" if "quieto" in disponibles else next(iter(cuadros))
    resultado = {}
    for nombre, ciclo in (("caminar", CICLO_CAMINAR), (ANIMACION_RESPIRAR, CICLO_RESPIRAR), ("dash", CICLO_DASH)):
        lista = []
        for base, cuerpo, cabeza, parpadea, ms in ciclo:
            base = base if base in disponibles else primero
            cuadro, mapa = armar_cuadro(cuadros, partes, base, cuerpo, cabeza, parpadea)
            lista.append((cuadro, mapa, ms))
        resultado[nombre] = lista
    return resultado
