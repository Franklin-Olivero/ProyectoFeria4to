"""Auto-tiling compuesto de Ciudad Nova (sin pygame): bordes, esquinas
internas, brazos y cruces de calle, línea central, cebras y barandas,
con mapas chicos armados a mano y sobre el mapa real."""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.dungeon import autotile_ciudad as at  # noqa: E402
from src.dungeon import ciudad_mapa as cm  # noqa: E402


def consulta(mapa, letras):
    def es(c, f):
        return 0 <= f < len(mapa) and 0 <= c < len(mapa[0]) and mapa[f][c] in letras
    return es


# Una calle vertical de 2 carriles que cruza una horizontal, con acera alrededor.
CRUCE = [
    "::cc::::",
    "::cc::::",
    "cccccccc",
    "cccccccc",
    "::cc::::",
    "::cc::::",
]
ES_CALLE = consulta(CRUCE, "c")


def test_bordes_solo_donde_cambia_el_terreno():
    assert at.bordes(ES_CALLE, 2, 0) == ("N", "O")  # el borde del mapa cuenta como distinto
    assert at.bordes(ES_CALLE, 2, 5) == ("S", "O")
    assert at.bordes(ES_CALLE, 3, 1) == ("E",)
    assert at.bordes(ES_CALLE, 5, 2) == ("N",)
    assert at.bordes(ES_CALLE, 2, 2) == ()


def test_esquinas_internas_en_las_cuatro_esquinas_del_cruce():
    assert at.esquinas_internas(ES_CALLE, 2, 2) == ("NO",)
    assert at.esquinas_internas(ES_CALLE, 3, 2) == ("NE",)
    assert at.esquinas_internas(ES_CALLE, 2, 3) == ("SO",)
    assert at.esquinas_internas(ES_CALLE, 3, 3) == ("SE",)
    assert at.esquinas_internas(ES_CALLE, 6, 2) == ()  # brazo recto: sin muescas


def test_brazos_y_cruce():
    assert at.tramo_calle(ES_CALLE, 2, 0) == "v"
    assert at.tramo_calle(ES_CALLE, 6, 3) == "h"
    for c, f in ((2, 2), (3, 2), (2, 3), (3, 3)):
        assert at.tramo_calle(ES_CALLE, c, f) == "cruce"


def test_la_linea_central_va_entre_los_dos_carriles():
    assert at.linea_carril(ES_CALLE, 2, 0) == "E" and at.linea_carril(ES_CALLE, 3, 0) == "O"
    assert at.linea_carril(ES_CALLE, 6, 2) == "S" and at.linea_carril(ES_CALLE, 6, 3) == "N"
    assert at.linea_carril(ES_CALLE, 2, 2) is None  # en el cruce no hay línea


def test_cebra_en_la_ultima_casilla_antes_del_cruce():
    sin_plaza = lambda c, f: False  # noqa: E731
    assert at.paso_cebra(ES_CALLE, sin_plaza, 2, 1) == "h"  # brazo vertical: rayas horizontales
    assert at.paso_cebra(ES_CALLE, sin_plaza, 4, 2) == "v"
    assert at.paso_cebra(ES_CALLE, sin_plaza, 2, 0) is None
    assert at.paso_cebra(ES_CALLE, sin_plaza, 6, 2) is None
    assert at.paso_cebra(ES_CALLE, sin_plaza, 2, 2) is None


def test_cebra_donde_la_calle_desemboca_en_la_plaza():
    mapa = ["pppp", "pppp", "cccc", "cccc"]
    es_plaza = consulta(mapa, "p")
    assert at.paso_cebra(consulta(mapa, "c"), es_plaza, 0, 2) is None  # la calle corre al lado
    vertical = ["pp", "cc", "cc", "cc"]
    assert at.paso_cebra(consulta(vertical, "c"), consulta(vertical, "p"), 0, 1) == "h"


def test_barandas_del_puente_dan_al_agua():
    puente = ["~~~", ":c:", ":c:", "~~~"]
    es_agua = consulta(puente, "~")
    assert at.barandas(es_agua, 1, 1) == ("N",)
    assert at.barandas(es_agua, 0, 2) == ("S",)


def test_el_canal_tiene_canto_hacia_la_tierra_y_muesca_en_la_laguna():
    mapa = [
        "::~~::",
        "::~~~~",
        "::~~~~",
    ]
    es_agua = consulta(mapa, "~")
    assert at.bordes(es_agua, 2, 0) == ("N", "O")
    assert at.esquinas_internas(es_agua, 3, 1) == ("NE",)


def test_terrenos_de_todas_las_letras_del_mapa():
    letras = {ch for linea in cm.MAPA for ch in linea}
    assert letras <= set(at.TERRENOS)
    assert at.terreno("c") == at.CALLE and at.terreno("~") == at.AGUA and at.terreno("k") == at.VERDE


def test_descriptor_en_el_mapa_real():
    """La avenida: los dos carriles de cada calzada llevan la línea central
    y un bordillo hacia afuera; el camellón queda entre ambas calzadas."""
    norte = at.descriptor(cm.MAPA, 15, 24)
    sur = at.descriptor(cm.MAPA, 15, 25)
    assert norte[0] == sur[0] == at.CALLE
    assert norte[1] == ("N",) and sur[1] == ("S",)  # acera arriba, camellón abajo
    assert norte[3][:2] == ("h", "S") and sur[3][:2] == ("h", "N")
    # Un puente de la avenida sobre el canal: la acera lleva baranda hacia el agua.
    for c in (38, 39):
        assert at.descriptor(cm.MAPA, c, 23)[3][0] == ("N",)
    # Las mismas vecinas dan el mismo descriptor (la caché del dibujo se comparte).
    assert at.descriptor(cm.MAPA, 13, 24)[:3] == at.descriptor(cm.MAPA, 15, 24)[:3]
