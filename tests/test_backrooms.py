"""Arte Backrooms sin pygame: auto-tiling, compositor, rutas por grade,
fallback, manifiesto en disco y presupuesto de tamaño."""

import json
import os
import struct
import sys

import pytest

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, RAIZ)

from src.core import assets  # noqa: E402
from src.dungeon import autotile, compositor_interior  # noqa: E402
from src.ui import rutas_backrooms as rutas  # noqa: E402

DATOS = os.path.join(RAIZ, "src", "dungeon", "datos")
CARPETA = os.path.join(RAIZ, assets.RUTA_BACKROOMS)


def _json(*partes):
    with open(os.path.join(*partes), encoding="utf-8") as archivo:
        return json.load(archivo)


@pytest.fixture(scope="module")
def terrenos():
    return _json(RAIZ, assets.RUTA_TERRENOS_BACKROOMS)


# ----------------------------------------------------------------------
# Auto-tiling y compositor
# ----------------------------------------------------------------------

def test_wangid_esquina_solo_si_sus_dos_lados_continuan():
    grilla = [[True, True], [True, False]]
    assert autotile.wangid(grilla, 0, 0) == (0, 0, 1, 0, 1, 0, 0, 0)  # abajo-der vacío: sin esquina
    lleno = [[True] * 3 for _ in range(3)]
    assert autotile.wangid(lleno, 1, 1) == (1,) * 8


def test_el_borde_cuenta_como_terreno_solo_si_se_pide():
    grilla = [[True]]
    assert autotile.wangid(grilla, 0, 0, borde_es_terreno=True) == (1,) * 8
    assert autotile.wangid(grilla, 0, 0) == (0,) * 8


@pytest.mark.parametrize("mapa, capa, borde", [
    ("vacancy_inn", "hotel_wall", True), ("vacancy_inn", "hotel_runner", False), ("showroom", "show_wall", True),
])
def test_autotile_reconstruye_las_capas_del_pack(terrenos, mapa, capa, borde):
    """Las capas de muro y alfombra de los mapas de ejemplo salen idénticas
    solo con saber qué celdas son de ese terreno."""
    plantilla = _json(DATOS, "plantillas", f"{mapa}.json")
    original = next(c["tiles"] for c in plantilla["capas"] if c["nombre"] == capa)
    grilla = [[t >= 0 for t in fila] for fila in original]
    assert autotile.resolver(grilla, terrenos["wang"][capa], borde) == original


def test_combinacion_inexistente_usa_la_pieza_mas_parecida():
    tabla = {"0,0,0,0,0,0,0,0": 10, "1,0,1,0,1,0,1,0": 20}
    assert autotile.pieza(tabla, (1, 0, 1, 0, 1, 0, 0, 0)) == 20


def test_caras_bajo_la_tapa_con_extremos_propios():
    muro = [[True] * 5, [True, False, False, False, True], [True, False, False, False, True],
            [True, False, False, False, True]]
    estilo = {"izquierda": [1, 2], "derecha": [3, 4], "medio": [[5, 6]]}
    caras = compositor_interior.capa_caras(muro, estilo)
    assert caras[1][1:4] == [1, 5, 3] and caras[2][1:4] == [2, 6, 4]
    assert caras[3] == [-1] * 5


def test_lobby_compuesto_tiene_capas_puestos_y_objetos_validos(terrenos):
    composicion = _json(RAIZ, assets.RUTA_COMPOSICIONES, f"{assets.COMPOSICION_LOBBY}.json")
    plantilla = compositor_interior.componer(composicion, terrenos)
    assert [c["nombre"] for c in plantilla["capas"]][:2] == ["piso", "muro"]
    for capa in plantilla["capas"]:
        assert len(capa["tiles"]) == composicion["alto"]
        assert all(len(fila) == composicion["ancho"] for fila in capa["tiles"])
    assert len(plantilla["puestos"]) == 4
    ids = {o["id"] for o in plantilla["objetos"] if "id" in o}
    assert all(luz["objeto"] in ids for luz in plantilla["luces"] if "objeto" in luz)
    tipos = {i for kinds in terrenos["tipos"].values() for lista in kinds.values() for i in lista}
    assert compositor_interior.tiles_usados(plantilla) <= tipos | set(range(5424))


# ----------------------------------------------------------------------
# Rutas por grade y fallback
# ----------------------------------------------------------------------

def test_cada_grade_tiene_su_carpeta_y_un_grade_desconocido_falla():
    for grade in assets.GRADES_BACKROOMS:
        assert rutas.carpeta_grade(grade, "x") == os.path.join("x", grade)
        assert rutas.ruta_hoja(grade, "tiles", "x") == os.path.join("x", grade, "tiles.png")
    with pytest.raises(ValueError):
        rutas.carpeta_grade("arcoiris")


def test_elegir_grade_cae_al_de_por_defecto_y_luego_al_primero():
    assert rutas.elegir_grade("sodium", ["hum", "sodium"]) == "sodium"
    assert rutas.elegir_grade("sodium", ["emergency", "hum"]) == "hum"
    assert rutas.elegir_grade("sodium", ["emergency"]) == "emergency"
    assert rutas.elegir_grade("hum", []) is None


def test_grades_disponibles_segun_lo_que_hay_en_disco():
    existe = {rutas.ruta_atlas("emergency", "r"), rutas.ruta_atlas("hum", "r")}.__contains__
    assert rutas.grades_disponibles("r", existe) == ["hum", "emergency"]


def test_atlas_faltante_o_roto_da_none(tmp_path):
    assert rutas.leer_atlas("hum", str(tmp_path)) is None
    os.makedirs(tmp_path / "hum")
    (tmp_path / "hum" / "atlas.json").write_text("{roto", encoding="utf-8")
    assert rutas.leer_atlas("hum", str(tmp_path)) is None


def test_rects_y_nombres_de_props():
    atlas = {"tiles": {"7": [16, 0]}, "props": {"hotel_lobby_sofa": [0, 0, 42, 24]}, "luces": {}, "animaciones": {}}
    assert rutas.rect_tile(atlas, 7) == (16, 0, 16, 16)
    assert rutas.rect_tile(atlas, 8) is None
    assert rutas.nombre_prop("hotel", "lobby_sofa") == "hotel_lobby_sofa"
    assert rutas.nombre_prop("hotel", "hotel_lobby_sofa") == "hotel_lobby_sofa"
    assert rutas.rect_prop(atlas, rutas.nombre_prop("hotel", "lobby_sofa")) == (0, 0, 42, 24)
    assert rutas.rect_prop(None, "x") is None


def test_version_quieta_de_una_animacion():
    props = {"hotel_sconce_lit", "hotel_vacancy_sign_neon", "office_crt"}
    assert rutas.prop_estatico_de("hotel_sconce_flicker_lit", props) == "hotel_sconce_lit"
    assert rutas.prop_estatico_de("hotel_vacancy_sign_neon_blink", props) == "hotel_vacancy_sign_neon"
    assert rutas.prop_estatico_de("office_crt_static", props) == "office_crt"
    assert rutas.prop_estatico_de("lab_nada_glow", props) is None


def test_cuadro_por_tiempo_recorre_y_repite():
    assert [rutas.cuadro_por_tiempo([100, 100, 200], t) for t in (0, 0.15, 0.25, 0.39, 0.41)] == [0, 1, 2, 2, 0]
    info = {"rect": [10, 20, 96, 32], "ancho": 32, "alto": 32}
    assert rutas.rect_cuadro(info, 2) == (74, 20, 32, 32)


# ----------------------------------------------------------------------
# Manifiesto en disco y presupuesto
# ----------------------------------------------------------------------

def _tamanio_png(ruta):
    with open(ruta, "rb") as archivo:
        cabecera = archivo.read(24)
    return struct.unpack(">II", cabecera[16:24])


def _grades_en_repo():
    return [g for g in assets.GRADES_BACKROOMS if os.path.exists(os.path.join(CARPETA, g, "atlas.json"))]


def test_hay_al_menos_el_grade_del_lobby():
    assert assets.GRADE_LOBBY in _grades_en_repo()


@pytest.mark.parametrize("grade", _grades_en_repo())
def test_cada_entrada_del_atlas_cae_dentro_de_su_hoja(grade):
    atlas = rutas.leer_atlas(grade, CARPETA)
    for tipo, entradas in atlas.items():
        if tipo not in assets.HOJAS_BACKROOMS or not entradas:
            continue
        ruta = rutas.ruta_hoja(grade, tipo, CARPETA)
        assert os.path.exists(ruta), ruta
        ancho, alto = _tamanio_png(ruta)
        for nombre, valor in entradas.items():
            if tipo == "tiles":
                rect = rutas.rect_tile(atlas, nombre)
            elif tipo == "animaciones":
                rect = tuple(valor["rect"])
                assert valor["cuadros"] * valor["ancho"] == rect[2] and len(valor["ms"]) == valor["cuadros"]
            else:
                rect = tuple(valor)
            x, y, w, h = rect
            assert 0 <= x and 0 <= y and x + w <= ancho and y + h <= alto, (tipo, nombre)


def test_el_atlas_del_lobby_trae_todo_lo_que_la_escena_dibuja(terrenos):
    composicion = _json(RAIZ, assets.RUTA_COMPOSICIONES, f"{assets.COMPOSICION_LOBBY}.json")
    plantilla = compositor_interior.componer(composicion, terrenos)
    atlas = rutas.leer_atlas(assets.GRADE_LOBBY, CARPETA)
    assert {str(t) for t in compositor_interior.tiles_usados(plantilla)} <= set(atlas["tiles"])
    for obj in plantilla["objetos"]:
        quieto = obj.get("estatico") or obj["nombre"]
        assert quieto in atlas["props"] or obj["nombre"] in atlas["animaciones"], obj["nombre"]
        if obj.get("apagado"):
            assert obj["apagado"] in atlas["props"]
    luces = {luz["nombre"] for luz in plantilla["luces"]} | {plantilla["luz_puesto"]}
    assert luces <= set(atlas["luces"])


def test_presupuesto_de_assets_backrooms():
    total = 0
    for raiz, _, archivos in os.walk(CARPETA):
        for nombre in archivos:
            tamanio = os.path.getsize(os.path.join(raiz, nombre))
            assert tamanio <= 5 * 1024 * 1024, nombre
            total += tamanio
    assert total < 40 * 1024 * 1024
