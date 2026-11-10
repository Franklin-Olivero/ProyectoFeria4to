"""Zonas de Ciudad Nova: identidad de cada barrio por datos (puro, sin Pygame).

Cada zona es un conjunto de rectángulos de casillas con su identidad
visual: especies de árbol, modelo de farola y de banca, los tipos de prop
que solo ella usa (la mayoría, máquinas y objetos del pack DECORATIONS
cyberpunk) y los props colocados a mano (los "hitos" de la zona). Las
reglas generales (farolas cada N casillas, bancas en pares, árboles en
el camellón y los jardines) viven en src/dungeon/layout_decoracion.py y
le preguntan a zona_de() qué modelo o especie toca en cada casilla.

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
# ancho, alto). Está bajo el Cruce Sur y se entra por su acera (fila 40);
# queda libre para 1-2 aristas nuevas del grafo (Cruce Sur - Distrito
# Liminal) y una entrada tipo grieta/ascensor, que hoy es solo un dibujo
# en el suelo (assets.PIEZA_GRIETA_LIMINAL).
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
    arboles: tuple = ()  # especies (números del pack Trees_Vol2)
    farola: str = "farola"
    banca: str = "banca"
    identidad: tuple = ()  # tipos de prop propios de la zona
    hitos: tuple = field(default_factory=tuple)


ZONAS = {
    LIMINAL: Zona(
        "Distrito Liminal (reservado)", (LIMINAL_RESERVADO,),
        identidad=("cono", "letrero_prohibido"),
        hitos=(Hito("cono", (22, 41)), Hito("cono", (28, 41)), Hito("letrero_prohibido", (22, 45)),
               Hito("cono", (28, 45))),
    ),
    PLAZA: Zona(
        "Plaza central", ((23, 19, 15, 13),), arboles=(75, 84), farola="farola_ornamental",
        identidad=("farol_datos", "carrito_comida", "jardinera"),
        hitos=(Hito("farol_datos", (23, 19)), Hito("farol_datos", (37, 19)), Hito("carrito_comida", (27, 31)),
               Hito("carrito_comida", (33, 31))),
    ),
    PARQUE: Zona(
        "Parque de la Laguna", ((40, 11, 13, 12),), arboles=(9, 12, 15, 18, 27, 30, 33, 47, 53, 62),
        farola="farola_farol",
        identidad=("estanque", "bebedero_pajaros", "mesa_sombrilla"),
        hitos=(
            Hito("arbol", (44, 20), variante=24), Hito("arbol", (40, 21), variante=24),  # sauces junto al agua
            Hito("bebedero_pajaros", (50, 13)), Hito("mesa_sombrilla", (48, 19)), Hito("mesa_sombrilla", (50, 19)),
        ),
    ),
    COMERCIAL: Zona(
        "Paseo comercial", ((27, 32, 11, 6),), arboles=(36, 38), farola="farola_jardin",
        identidad=("expendedora", "kiosco_neon", "maquina_snacks", "cajero", "mesa_cafe"),
        hitos=(
            # Terrazas en la mitad sur del paseo (la mitad norte queda libre) y máquinas al fondo.
            Hito("mesa_cafe", (29, 35)), Hito("mesa_cafe", (31, 35)), Hito("mesa_cafe", (33, 35)),
            Hito("expendedora", (28, 35)), Hito("kiosco_neon", (37, 35)), Hito("cajero", (35, 35)),
            Hito("maquina_snacks", (27, 32)),
        ),
    ),
    CIVICA: Zona(
        "Zona cívica", ((21, 1, 17, 8), (40, 1, 17, 8)), arboles=(1, 3, 5, 7, 87), farola="farola_ornamental",
        identidad=("fuente", "totem_info", "pedestal_civico", "urna_digital", "bolardo"),
        hitos=(
            # Plaza de la Alcaldía: fuente de datos al centro, bancas enfrentadas, tótem y pedestal.
            Hito("banca", (40, 4), "E"), Hito("banca", (45, 4), "O"),
            Hito("totem_info", (40, 2)), Hito("pedestal_civico", (45, 2)),
            Hito("urna_digital", (45, 6)), Hito("bolardo", (40, 6)),
        ),
    ),
    ESCOLAR: Zona(
        "Zona escolar", ((1, 1, 20, 22), (21, 9, 12, 14)), arboles=(43, 44, 49, 64), farola="farola_baja",
        banca="banca_corta",
        identidad=("casillero_escolar", "caja_material", "terminal_estudio", "bicicletero", "bicicleta"),
        hitos=(
            # Patio del Colegio: casilleros y cajas en el borde de la cancha, bicicletero junto a la entrada.
            Hito("casillero_escolar", (10, 18)), Hito("casillero_escolar", (11, 18)),
            Hito("caja_material", (20, 18)), Hito("terminal_estudio", (20, 13)),
            Hito("bicicletero", (11, 13)), Hito("bicicleta", (12, 13)), Hito("bicicleta", (13, 13)),
            Hito("banca_corta", (17, 18), "N"), Hito("banca_corta", (18, 18), "N"),
        ),
    ),
    HOSPITAL: Zona(
        "Zona hospitalaria", ((1, 29, 22, 17),), arboles=(42, 52, 57, 72), farola="farola_curva",
        identidad=("dispensador_medico", "equipo_medico", "botiquin", "banca_parada", "cartel_parada"),
        hitos=(
            # Jardín del Hospital (da a la Plaza) y parada frente a su puerta.
            Hito("dispensador_medico", (20, 31)), Hito("equipo_medico", (22, 35)), Hito("botiquin", (20, 35)),
            Hito("banca_parada", (10, 37)), Hito("cartel_parada", (11, 37)),
        ),
    ),
    MEDIOS: Zona(
        "Zona de medios", ((40, 29, 13, 17), (27, 38, 13, 8)), arboles=(78, 81, 84, 90), farola="farola_jardin",
        identidad=("servidor", "baliza_senal", "consola_noticias", "monitor_medios", "antena"),
        hitos=(
            Hito("servidor", (40, 41)), Hito("consola_noticias", (36, 41)), Hito("monitor_medios", (33, 41)),
            Hito("baliza_senal", (52, 41)), Hito("antena", (44, 44), ancho=2),
            Hito("servidor", (50, 44)),
        ),
    ),
    RESIDENCIAL: Zona(
        "Barrio residencial", ((53, 1, 10, 45),), arboles=(57, 62, 67, 69), farola="farola",
        identidad=("generador", "aire_ac", "contenedor", "medidor", "buzon_azul"),
        hitos=(
            Hito("generador", (56, 12)), Hito("aire_ac", (56, 20)), Hito("contenedor", (56, 30)),
            Hito("medidor", (56, 38)), Hito("buzon_azul", (56, 14)),
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
