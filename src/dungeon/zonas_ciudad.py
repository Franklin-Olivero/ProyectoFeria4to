"""Zonas de Ciudad Nova: identidad de cada barrio por datos (puro, sin Pygame).

Cada zona es un conjunto de rectángulos de casillas con su identidad
visual: especies de árbol, modelo de farola y de banca, los tipos de prop
que solo ella usa y los props colocados a mano (los "hitos" de la zona).
Las reglas generales (farolas cada N casillas, bancas en pares, árboles
agrupados) viven en src/dungeon/layout_decoracion.py y le preguntan a
zona_de() qué modelo o especie toca en cada casilla.

    ZONAS                -> {id: Zona}
    zona_de(col, fila)   -> id de la zona (la primera cuyo rect la contiene) o AVENIDA
    LIMINAL_RESERVADO    -> lote vacío para el futuro Distrito Liminal
    PROPS_BACKROOMS      -> props del pack Backrooms que usa la ciudad (los empaqueta
                            tools/empaquetar_backrooms.py)

Casillas en (columna, fila) de ciudad_mapa.MAPA. Un prop de varias
casillas declara su huella (ancho, alto) desde su casilla superior
izquierda; su imagen se apoya en el borde inferior de la huella.
"""

from dataclasses import dataclass, field

AVENIDA = "avenida"
PLAZA = "plaza"
PARQUE = "parque"
ESCOLAR = "escolar"
HOSPITAL = "hospital"
MEDIOS = "medios"
CIVICA = "civica"
RESIDENCIAL = "residencial"
LIMINAL = "liminal"

# Lote reservado para la parte 2 (mazmorras del nuevo mundo): (col, fila,
# ancho, alto). Se llega por la abertura del seto bajo el Cruce Sur; queda
# libre para 1-2 aristas nuevas del grafo y una entrada tipo grieta/ascensor.
LIMINAL_RESERVADO = (28, 41, 8, 5)
ACCESO_LIMINAL = ((31, 40), (32, 40), (33, 40))


@dataclass(frozen=True)
class Hito:
    """Prop puesto a mano: tipo, casilla superior izquierda, orientación y huella."""
    tipo: str
    casilla: tuple
    orientacion: str = "S"
    ancho: int = 1
    alto: int = 1
    variante: int = 0  # árboles: número del pack


@dataclass(frozen=True)
class Zona:
    nombre: str
    rects: tuple  # ((col, fila, ancho, alto), ...)
    arboles: tuple = ()  # especies (números del pack Trees_Vol2)
    farola: str = "farola"
    banca: str = "banca"
    identidad: tuple = ()  # tipos de prop propios de la zona
    hitos: tuple = field(default_factory=tuple)


ZONAS = {
    LIMINAL: Zona(
        "Distrito Liminal (reservado)", ((28, 40, 8, 6),),
        identidad=("cono", "letrero_prohibido"),
        hitos=(Hito("cono", (28, 41)), Hito("cono", (35, 41)), Hito("letrero_prohibido", (28, 45)),
               Hito("cono", (35, 45))),
    ),
    PLAZA: Zona(
        "Plaza central", ((25, 20, 15, 11),), arboles=(75, 84), farola="farola_ornamental",
        identidad=("mesa_cafe", "carrito_comida", "jardinera"),
        hitos=(Hito("mesa_cafe", (29, 22)), Hito("mesa_cafe", (35, 22)), Hito("carrito_comida", (29, 28)),
               Hito("carrito_comida", (35, 28))),
    ),
    CIVICA: Zona(
        "Zona cívica", ((25, 1, 38, 9), (57, 10, 7, 13)), arboles=(1, 3, 5, 7, 87), farola="farola_ornamental",
        identidad=("fuente", "jardinera_flores", "bolardo", "jardinera_larga"),
        hitos=(
            # Plaza de la Alcaldía: fuente al centro, bancas enfrentadas, jardineras y faroles.
            Hito("banca", (26, 6), "E"), Hito("banca", (36, 6), "O"),
            Hito("jardinera_flores", (26, 4)), Hito("jardinera_flores", (36, 4)),
            Hito("farola_ornamental", (25, 8)), Hito("farola_ornamental", (37, 8)),
            Hito("bolardo", (26, 8)), Hito("bolardo", (36, 8)),
            # Jardín formal al este de la Alcaldía.
            Hito("jardinera_larga", (52, 5)), Hito("jardinera_larga", (52, 8)),
            Hito("arbol", (55, 5), variante=87), Hito("arbol", (55, 8), variante=87),
            Hito("bolardo", (51, 4)), Hito("bolardo", (51, 8)),
        ),
    ),
    ESCOLAR: Zona(
        "Zona escolar", ((0, 0, 25, 10), (0, 10, 7, 13)), arboles=(43, 44, 49, 64), farola="farola_baja",
        banca="banca_corta",
        identidad=("bicicletero", "bicicleta", "cartelera", "bebedero", "letrero_bienvenida", "casita_pajaros"),
        hitos=(
            # Patio del Colegio: bicicletero con bicicletas, cartelera, bebedero y bienvenida.
            Hito("bicicletero", (7, 6)), Hito("bicicleta", (8, 6)), Hito("bicicleta", (9, 6)),
            Hito("cartelera", (11, 5)), Hito("bebedero", (12, 8)), Hito("letrero_bienvenida", (10, 8)),
            Hito("banca_corta", (7, 8), "N"), Hito("banca_corta", (8, 8), "N"),
            Hito("casita_pajaros", (2, 12)), Hito("casita_pajaros", (4, 12)),
        ),
    ),
    PARQUE: Zona(
        "Parque", ((12, 15, 19, 8),), arboles=(9, 12, 15, 18, 27, 30, 33, 47, 53, 62), farola="farola_farol",
        identidad=("estanque", "bebedero_pajaros", "mesa_sombrilla"),
        hitos=(
            Hito("arbol", (20, 16), variante=24), Hito("arbol", (28, 17), variante=24),  # sauces junto al agua
            Hito("bebedero_pajaros", (15, 17)), Hito("mesa_sombrilla", (14, 21)), Hito("mesa_sombrilla", (21, 21)),
            Hito("casita_pajaros", (13, 16)),
        ),
    ),
    RESIDENCIAL: Zona(
        "Barrio residencial", ((35, 15, 18, 8),), arboles=(57, 62, 67, 69), farola="farola",
        identidad=("buzon_azul", "cerca_madera", "parrilla", "barril"),
        hitos=(
            Hito("cerca_madera", (41, 19)), Hito("cerca_madera", (42, 19)), Hito("cerca_madera", (43, 19)),
            Hito("parrilla", (42, 20)), Hito("barril", (44, 21)), Hito("buzon_azul", (44, 18)),
            Hito("buzon_azul", (44, 16)),
        ),
    ),
    HOSPITAL: Zona(
        "Zona hospitalaria", ((12, 27, 18, 9), (0, 23, 7, 24), (7, 40, 20, 7)), arboles=(42, 52, 57, 72),
        farola="farola_curva",
        identidad=("auto_van", "auto_sedan", "banca_parada", "cartel_parada", "maceta_planta"),
        hitos=(
            # Jardín ordenado junto al Hospital y estacionamiento con parada.
            Hito("maceta_planta", (25, 32)), Hito("maceta_planta", (28, 32)),
            Hito("banca_parada", (26, 33)), Hito("cartel_parada", (27, 33)),
            Hito("auto_van", (1, 24), ancho=5, alto=3), Hito("auto_sedan", (1, 36), ancho=5, alto=3),
            Hito("maceta_planta", (8, 42)), Hito("maceta_planta", (11, 42)),
        ),
    ),
    MEDIOS: Zona(
        "Zona de medios", ((35, 27, 18, 9), (57, 23, 7, 24), (37, 40, 20, 7)), arboles=(78, 81, 84, 90),
        farola="farola_jardin",
        identidad=("antena", "kiosco_digital", "maquina", "armario_electrico", "auto_hatch"),
        hitos=(
            Hito("kiosco_digital", (38, 33)), Hito("maquina", (40, 33)), Hito("armario_electrico", (36, 33)),
            Hito("antena", (61, 40), ancho=2), Hito("auto_hatch", (58, 24), ancho=5, alto=3),
            Hito("kiosco_digital", (60, 36)), Hito("maquina", (58, 37)),
            Hito("antena", (55, 42), ancho=2), Hito("armario_electrico", (53, 44)),
        ),
    ),
}
# Tipos de identidad mínimos que cada zona construida debe mostrar (el
# lote liminal está vacío a propósito).
MINIMO_IDENTIDAD = 3
ORDEN_ZONAS = (LIMINAL, PLAZA, CIVICA, ESCOLAR, PARQUE, RESIDENCIAL, HOSPITAL, MEDIOS)

# Props de Backrooms que usa la ciudad (tipo -> nombre en el pack).
PROPS_BACKROOMS = {
    "auto_van": "garage_car_van_grey",
    "auto_sedan": "garage_car_sedan_beige",
    "auto_hatch": "garage_car_hatch_teal",
    "auto_estate": "garage_car_estate_green",
    "antena": "lab_antenna_mast",
    "cono": "garage_traffic_cone",
    "letrero_prohibido": "elec_sign_keep_out",
}


def _dentro(rect, col, fila):
    c, f, ancho, alto = rect
    return c <= col < c + ancho and f <= fila < f + alto


def zona_de(col, fila):
    """Id de la zona de la casilla (en ORDEN_ZONAS: la primera que la contiene)."""
    for id_zona in ORDEN_ZONAS:
        if any(_dentro(rect, col, fila) for rect in ZONAS[id_zona].rects):
            return id_zona
    return AVENIDA


def farola_de(col, fila):
    zona = zona_de(col, fila)
    return ZONAS[zona].farola if zona in ZONAS else "farola"


def arboles_de(col, fila, por_defecto):
    zona = zona_de(col, fila)
    especies = ZONAS[zona].arboles if zona in ZONAS else ()
    return especies or por_defecto


def casillas_hito(hito):
    col, fila = hito.casilla
    return {(col + dc, fila + df) for dc in range(hito.ancho) for df in range(hito.alto)}
