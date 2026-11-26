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


def componer(cuadro_cabeza, partes_cabeza, cuadro_cuerpo, partes_cuerpo):
    """(cuadro, partes) con la cabeza del primero sobre el cuerpo del
    segundo (del tamaño del cuerpo). Si a alguno no se le encuentra la
    cabeza, devuelve el cuerpo tal cual."""
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
        for x in range(max(0, b0 - 1), min(ancho, b1 + 2)):
            cuadro[y][x] = None
            partes[y][x] = None

    # 3. La cabeza elegida.
    alto_c, ancho_c = len(partes_cabeza), len(partes_cabeza[0])

    def es_mano(x, y):
        return (partes_cabeza[y][x] == PIEL and y >= cuello_c - ALTO_ZONA_MANOS
                and (x < a0 + MARGEN_MANOS or x > a1 - MARGEN_MANOS))

    def de_la_cabeza(x, y):
        return partes_cabeza[y][x] in PARTES_CABEZA and not es_mano(x, y)

    def toca_la_cabeza(x, y):
        """Contornos, ojos y brillos: sin parte, pero pegados al pelo o la cara."""
        return any(0 <= vy < alto_c and 0 <= vx < ancho_c and de_la_cabeza(vx, vy)
                   for vy in (y - 1, y, y + 1) for vx in (x - 1, x, x + 1))

    for y in range(alto_c):
        for x in range(ancho_c):
            color, parte = cuadro_cabeza[y][x], partes_cabeza[y][x]
            if color is None:
                continue
            if parte in PARTES_CABEZA:
                if es_mano(x, y):
                    continue
            elif not toca_la_cabeza(x, y):
                continue  # el accesorio o la mano de ese personaje
            arriba = y < cuello_c and a0 - 1 <= x <= a1 + 1
            melena = y >= cuello_c and parte == PELO
            if not (arriba or melena):
                continue
            nx, ny = x + dx, y + dy
            if 0 <= nx < ancho and 0 <= ny < alto:
                cuadro[ny][nx] = color
                partes[ny][nx] = parte
    return tuple(tuple(fila) for fila in cuadro), tuple(tuple(fila) for fila in partes)
