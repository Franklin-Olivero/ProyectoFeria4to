"""Zonas de Ciudad Nova: identidad de cada barrio por datos (puro, sin Pygame).

Cada zona es un conjunto de rectángulos de casillas con su identidad
visual: especies de árbol, modelo de farola y de banca, los tipos de prop
que solo ella usa (mobiliario discreto del pack urbano) y los props
colocados a mano (los "hitos" de la zona). Las reglas generales (farolas
cada N casillas, bancas en pares, árboles agrupados en los jardines) viven
en src/dungeon/layout_decoracion.py y le preguntan a zona_de() qué modelo
o especie toca en cada casilla.

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
COMERCIAL = "comercial"
RESIDENCIAL = "residencial"
LIMINAL = "liminal"

# Lote reservado para la parte 2 (mazmorras del nuevo mundo): (col, fila,
# ancho, alto). Está bajo el Cruce Sur y se entra por su banqueta (fila
# 40); queda libre para 1-2 aristas nuevas del grafo (Cruce Sur - Distrito
# Liminal) y una entrada tipo grieta/ascensor, sin construir.
LIMINAL_RESERVADO = (22, 41, 7, 5)
ACCESO_LIMINAL = ((24, 40), (25, 40), (26, 40))


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
    arboles: tuple = ()  # especies (números del pack Trees_Vol2, ver assets.ARBOLES_CIUDAD)
    farola: str = "farola"
    banca: str = "banca"
    identidad: tuple = ()  # tipos de prop propios de la zona
    hitos: tuple = field(default_factory=tuple)


ZONAS = {
    LIMINAL: Zona(
        "Distrito Liminal (reservado)", (LIMINAL_RESERVADO,),
        identidad=("cono", "letrero_prohibido"),
        hitos=(Hito("cono", (22, 42)), Hito("cono", (28, 42)), Hito("letrero_prohibido", (22, 45)),
               Hito("cono", (28, 45))),
    ),
    PLAZA: Zona(
        "Plaza central", ((23, 19, 15, 13),), arboles=(27, 67), farola="farola_ornamental",
        identidad=("carrito_comida", "jardinera", "maceta_grande"),
        hitos=(Hito("carrito_comida", (27, 31)), Hito("carrito_comida", (33, 31)),
               Hito("maceta_grande", (24, 20)), Hito("maceta_grande", (36, 31))),
    ),
    PARQUE: Zona(
        "Parque Central", ((38, 11, 15, 12),), arboles=(9, 12, 15, 18, 24, 30, 47, 52, 53),
        farola="farola_farol",
        identidad=("estanque", "bebedero_pajaros", "mesa_sombrilla", "casita_pajaros"),
        hitos=(
            Hito("arbol", (46, 15), variante=24), Hito("arbol", (49, 15), variante=24),  # sauces junto a la alberca
            Hito("bebedero_pajaros", (40, 13)), Hito("mesa_sombrilla", (41, 20)), Hito("mesa_sombrilla", (48, 20)),
            Hito("casita_pajaros", (51, 12)),
        ),
    ),
    COMERCIAL: Zona(
        "Paseo comercial", ((27, 32, 11, 6),), arboles=(57, 62), farola="farola_jardin",
        identidad=("mesa_cafe", "parada_bus", "maceta_flores"),
        hitos=(
            # Terrazas en la mitad sur del paseo (la mitad norte queda libre).
            Hito("mesa_cafe", (29, 35)), Hito("mesa_cafe", (31, 35)), Hito("mesa_cafe", (33, 35)),
            Hito("maceta_flores", (35, 35)), Hito("maceta_flores", (37, 35)), Hito("parada_bus", (27, 33)),
        ),
    ),
    CIVICA: Zona(
        "Zona cívica", ((21, 1, 36, 8),), arboles=(1, 3, 5, 7), farola="farola_ornamental",
        identidad=("fuente", "jardinera_flores", "bolardo", "jardinera_larga"),
        hitos=(
            # Plaza de la Alcaldía: fuente chica al centro, bancas enfrentadas, flores y bolardos.
            Hito("banca", (39, 4), "E"), Hito("banca", (44, 4), "O"),
            Hito("jardinera_flores", (39, 2)), Hito("jardinera_flores", (44, 2)),
            Hito("bolardo", (39, 6)), Hito("bolardo", (44, 6)),
        ),
    ),
    ESCOLAR: Zona(
        "Zona escolar", ((1, 1, 20, 22), (21, 9, 12, 14)), arboles=(43, 44, 49, 64, 69), farola="farola_baja",
        banca="banca_corta",
        identidad=("bicicletero", "bicicleta", "cartelera", "letrero_bienvenida", "bebedero"),
        hitos=(
            # Jardín del Colegio: bicicletero y bienvenida junto a la entrada, cartelera y bebedero.
            Hito("bicicletero", (11, 14)), Hito("bicicleta", (13, 14)),
            Hito("letrero_bienvenida", (18, 14)), Hito("cartelera", (22, 14)), Hito("bebedero", (10, 19)),
        ),
    ),
    HOSPITAL: Zona(
        "Zona hospitalaria", ((1, 29, 22, 17),), arboles=(18, 52, 57, 67), farola="farola_curva",
        identidad=("banca_parada", "cartel_parada", "maceta_planta", "basurero_verde"),
        hitos=(
            # Parada frente al Hospital y macetas en su banqueta.
            Hito("banca_parada", (10, 37)), Hito("cartel_parada", (11, 37)),
            Hito("maceta_planta", (17, 37)), Hito("maceta_planta", (19, 37)), Hito("basurero_verde", (8, 34)),
        ),
    ),
    MEDIOS: Zona(
        "Zona de medios", ((40, 29, 13, 17), (27, 38, 13, 8)), arboles=(12, 33, 62), farola="farola_jardin",
        identidad=("kiosco_digital", "armario_electrico", "antena", "reciclaje"),
        hitos=(
            Hito("kiosco_digital", (44, 41)), Hito("kiosco_digital", (49, 41)), Hito("armario_electrico", (40, 41)),
            Hito("antena", (50, 44), ancho=2), Hito("reciclaje", (36, 41)),
        ),
    ),
    RESIDENCIAL: Zona(
        "Barrio residencial", ((53, 1, 10, 45),), arboles=(9, 15, 53, 69), farola="farola",
        identidad=("buzon_azul", "parrilla", "cerca_madera"),
        hitos=(
            # Patios de los apartamentos del este y buzones en la banqueta.
            Hito("parrilla", (60, 18)), Hito("cerca_madera", (61, 18)),
            Hito("cerca_madera", (61, 42)), Hito("buzon_azul", (56, 13)), Hito("buzon_azul", (56, 39)),
        ),
    ),
}
# Tipos de identidad mínimos que cada zona construida debe mostrar (el
# lote liminal está vacío a propósito).
MINIMO_IDENTIDAD = 3
ORDEN_ZONAS = (LIMINAL, PLAZA, PARQUE, COMERCIAL, CIVICA, ESCOLAR, HOSPITAL, MEDIOS, RESIDENCIAL)

# Props de Backrooms que usa la ciudad (tipo -> nombre en el pack).
PROPS_BACKROOMS = {
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
