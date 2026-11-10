"""Huellas de Ciudad Nova: solapes y área verde (lógica pura, sin Pygame).

Nada se monta sobre nada: cada edificio, casa, prop y elemento especial
(fuentes, alberca) ocupa su huella y dos huellas nunca se tocan. Las
únicas superposiciones permitidas son visuales y se resuelven por orden Y:
sombras, copas de árboles sobre la banqueta y halos de luz.

    huellas_ciudad(mapa_mod)       -> [(nombre, frozenset de casillas)] de todo lo que ocupa lugar
    solapes(elementos)             -> pares (nombre_a, nombre_b) cuyas casillas se pisan
    solapes_rects(rects)           -> pares (nombre_a, nombre_b) cuyos rects (x, y, w, h) se cruzan
    fraccion_verde(mapa, verdes, calles) -> vegetación / área no vial

`mapa_mod` es el módulo src/dungeon/ciudad_mapa (se pasa para no
importarlo aquí y poder probar con mapas chicos).
"""


def _celdas(col, fila, ancho, alto):
    return frozenset((c, f) for c in range(col, col + ancho) for f in range(fila, fila + alto))


def huellas_ciudad(mapa_mod):
    """Todo lo que ocupa casillas en la ciudad, con un nombre legible."""
    elementos = [(f"edificio {zona}", _celdas(*huella)) for zona, huella in mapa_mod.EDIFICIOS.items()]
    elementos += [(f"casa {i} ({estilo})", _celdas(*huella)) for i, (huella, estilo) in enumerate(mapa_mod.CASAS)]
    for nombre in ("FUENTE_PLAZA", "FUENTE_CIVICA", "ALBERCA"):
        elementos.append((nombre.lower(), _celdas(*getattr(mapa_mod, nombre))))
    elementos += [(f"{p.tipo} {p.casilla}", frozenset(p.casillas)) for p in mapa_mod.DECORACION]
    return elementos


def solapes(elementos):
    """Pares de elementos cuyas casillas se pisan. O(total de casillas)."""
    dueno = {}
    pares = []
    for nombre, casillas in elementos:
        chocados = {dueno[c] for c in casillas if c in dueno}
        pares += [(otro, nombre) for otro in sorted(chocados)]
        for casilla in casillas:
            dueno.setdefault(casilla, nombre)
    return pares


def _cruzan(a, b):
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return ax < bx + bw and bx < ax + aw and ay < by + bh and by < ay + ah


def solapes_rects(rects):
    """Pares (nombre_a, nombre_b) de rects (x, y, w, h) que se cruzan
    (tocarse por un borde no cuenta). O(n²): son unos cientos."""
    lista = list(rects)
    return [(a, b) for i, (a, ra) in enumerate(lista) for b, rb in lista[i + 1:] if _cruzan(ra, rb)]


def fraccion_verde(mapa, verdes, calles):
    """Fracción del área no vial (todo lo que no es calle) que es vegetación."""
    no_vial = verde = 0
    for linea in mapa:
        for letra in linea:
            if letra in calles:
                continue
            no_vial += 1
            verde += letra in verdes
    return verde / no_vial if no_vial else 0.0
