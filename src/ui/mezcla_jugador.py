"""Mezclar personajes: la cabeza de uno sobre el cuerpo de otro (lógica pura, sin pygame).

Pestañas HAT (cabeza) y SKIN (cuerpo) del vestidor. Las hojas de jugador
de Higgsfield (assets/sprites/jugadores/<rol>.png) tienen todas 40 px de
alto y los mismos cuadros (quieto, paso_a, paso_b, dash), pero distinto
ancho, porque el accesorio del rol cae a un lado (el cartel del Ciudadano,
el aro de luz de la Influencer). Su mapa de partes (<rol>.partes.png) dice
qué píxel es pelo, piel, ropa, pantalón o zapatos; eso basta para cortar:

    cuello   el primer renglón con ropa: lo de arriba es la cabeza.
    columnas las del pelo por encima del cuello (las manos levantadas no).

Componer un cuadro:
    1. Se parte del cuadro del CUERPO (con su accesorio, sus manos y su ancho).
    2. Se borra su cabeza: por encima de su cuello, en las columnas de su pelo.
    3. Se pega la cabeza elegida alineando el centro del pelo y el cuello: el
       pelo, la cara y los contornos que los tocan (no las manos de ese
       personaje ni su accesorio), y el pelo que cae por debajo del cuello.
El mapa de partes se compone igual, así el cuadro mezclado se tiñe con los
colores del vestidor como uno original (src/ui/tinte_jugador.py).

Un cuadro es una tupla de filas y cada fila una tupla de RGBA (o None); un
mapa de partes, filas de nombres de parte (o None). Componer cuesta
O(ancho * alto) por cuadro y se hace una sola vez por combinación (caché en
src/ui/sprites.py).
"""

PELO = "pelo"
PIEL = "piel"
ROPA = "ropa"
PARTES_CABEZA = (PELO, PIEL)
ALTO_ZONA_MANOS = 7  # renglones sobre el cuello donde una piel al costado es una mano, no la cara
MARGEN_MANOS = 3  # columnas desde el borde del pelo que ya cuentan como "al costado"
ALTO_MELENA = 4  # renglones bajo el cuello que puede bajar el pelo (más abajo eran mechones sueltos)
ALCANCE_ENCERRADO = 6  # columnas a cada lado donde buscar pelo o cara para un ojo o un lente
LUZ_MAXIMA_CONTORNO = 70  # un píxel sin parte más oscuro que esto es contorno (el cartel y el aro son claros)


def _es_contorno(color):
    return 0.299 * color[0] + 0.587 * color[1] + 0.114 * color[2] < LUZ_MAXIMA_CONTORNO


def zona_cabeza(partes):
    """(cuello, x0, x1) de un cuadro: renglón donde empieza la ropa y
    columnas del pelo por encima. None si el cuadro no tiene ropa o pelo."""
    cuello = next((y for y, fila in enumerate(partes) if ROPA in fila), None)
    if cuello is None:
        return None
    columnas = [x for y in range(cuello) for x, parte in enumerate(partes[y]) if parte == PELO]
    if not columnas:
        return None
    return cuello, min(columnas), max(columnas)


def componer(cuadro_cabeza, partes_cabeza, cuadro_cuerpo, partes_cuerpo, escala=1.0):
    """(cuadro, partes) con la cabeza del primero sobre el cuerpo del
    segundo (del tamaño del cuerpo). Si a alguno no se le encuentra la
    cabeza, devuelve el cuerpo tal cual. `escala`: cuánto más grande que una
    hoja de 40 px es el cuadro (los retratos grandes): agranda los márgenes."""
    zona_manos = round(ALTO_ZONA_MANOS * escala)
    margen_manos = round(MARGEN_MANOS * escala)
    borde = max(1, round(escala))
    margen_x = max(1, round(escala * 0.4))  # a los lados del pelo: solo su contorno (no el cartel ni el aro de luz)
    alto_melena = max(2, round(ALTO_MELENA * escala))
    zona_c = zona_cabeza(partes_cabeza)
    zona_t = zona_cabeza(partes_cuerpo)
    if zona_c is None or zona_t is None:
        return cuadro_cuerpo, partes_cuerpo
    cuello_c, a0, a1 = zona_c
    cuello_t, b0, b1 = zona_t
    alto, ancho = len(cuadro_cuerpo), len(cuadro_cuerpo[0])
    dx = round((b0 + b1) / 2 - (a0 + a1) / 2)
    dy = cuello_t - cuello_c
    cuadro = [list(fila) for fila in cuadro_cuerpo]
    partes = [list(fila) for fila in partes_cuerpo]

    # 2. Fuera la cabeza del cuerpo.
    for y in range(min(cuello_t, alto)):
        for x in range(max(0, b0 - borde), min(ancho, b1 + borde + 1)):
            cuadro[y][x] = None
            partes[y][x] = None

    # ...y la melena del cuerpo, que cae sobre los hombros (si no, quedan
    # mechones sueltos bajo la cabeza nueva): su pelo y el contorno que lo toca.
    for y in range(cuello_t, min(alto, cuello_t + alto_melena)):
        for x in range(ancho):
            if partes_cuerpo[y][x] == PELO or (partes_cuerpo[y][x] is None and cuadro_cuerpo[y][x] is not None
                                                and _es_contorno(cuadro_cuerpo[y][x])
                                                and any(partes_cuerpo[vy][vx] == PELO
                                                        for vy in range(max(0, y - 1), min(alto, y + 2))
                                                        for vx in range(max(0, x - 1), min(ancho, x + 2)))):
                cuadro[y][x] = None
                partes[y][x] = None

    # 3. La cabeza elegida.
    alto_c, ancho_c = len(partes_cabeza), len(partes_cabeza[0])

    def es_mano(x, y):
        return (partes_cabeza[y][x] == PIEL and y >= cuello_c - zona_manos
                and (x < a0 + margen_manos or x > a1 - margen_manos))

    def de_la_cabeza(x, y):
        return partes_cabeza[y][x] in PARTES_CABEZA and not es_mano(x, y)

    def toca_la_cabeza(x, y):
        """Contornos, ojos y brillos: sin parte, pero pegados al pelo o la cara."""
        return any(0 <= vy < alto_c and 0 <= vx < ancho_c and de_la_cabeza(vx, vy)
                   for vy in range(y - borde, y + borde + 1) for vx in range(x - borde, x + borde + 1))

    alcance = max(2, round(ALCANCE_ENCERRADO * escala))

    def encerrado(x, y):
        """Ojos, lentes y brillos: con pelo o cara a la izquierda Y a la derecha."""
        fila = partes_cabeza[y]
        izquierda = any(fila[vx] in PARTES_CABEZA for vx in range(max(0, x - alcance), x))
        derecha = any(fila[vx] in PARTES_CABEZA for vx in range(x + 1, min(ancho_c, x + alcance + 1)))
        return izquierda and derecha

    def debajo_de_la_cabeza(x, y):
        """El contorno de la barbilla tiene cara justo encima; el del cuello de
        la camisa, no."""
        return any(0 <= y - k and de_la_cabeza(x, y - k) for k in range(1, borde + 1))

    elegidos = set()
    for y in range(alto_c):
        for x in range(ancho_c):
            color, parte = cuadro_cabeza[y][x], partes_cabeza[y][x]
            if color is None:
                continue
            if parte in PARTES_CABEZA:
                if es_mano(x, y):
                    continue
            elif not toca_la_cabeza(x, y) or not (_es_contorno(color) or encerrado(x, y)):
                continue  # el accesorio o la mano de ese personaje (el cartel, el aro de luz...)
            elif y >= cuello_c - 2 * borde and not debajo_de_la_cabeza(x, y):
                continue  # junto al cuello, el contorno del cuello de su camisa (no el de la barbilla)
            arriba = y < cuello_c and a0 - margen_x <= x <= a1 + margen_x
            melena = (cuello_c <= y < cuello_c + alto_melena and parte == PELO and a0 <= x <= a1)
            if arriba or melena:
                elegidos.add((x, y))
    for x, y in _pieza_mayor(elegidos):
        nx, ny = x + dx, y + dy
        if 0 <= nx < ancho and 0 <= ny < alto:
            cuadro[ny][nx] = cuadro_cabeza[y][x]
            partes[ny][nx] = partes_cabeza[y][x]
    return tuple(tuple(fila) for fila in cuadro), tuple(tuple(fila) for fila in partes)


def _pieza_mayor(pixeles):
    """La pieza conectada (8 vecinos) más grande de `pixeles`: la cabeza.
    Lo que quedó suelto alrededor (un trozo del palo del cartel o de una mano)
    se descarta. BFS con una cola: O(n)."""
    pendientes = set(pixeles)
    mayor = set()
    while pendientes:
        inicio = pendientes.pop()
        pieza = {inicio}
        cola = [inicio]
        while cola:
            x, y = cola.pop()
            for vy in (y - 1, y, y + 1):
                for vx in (x - 1, x, x + 1):
                    if (vx, vy) in pendientes:
                        pendientes.discard((vx, vy))
                        pieza.add((vx, vy))
                        cola.append((vx, vy))
        if len(pieza) > len(mayor):
            mayor = pieza
    return mayor
