"""Vestidores: la Apariencia (pura), el teñido del personaje de Higgsfield
(src/ui/tinte_jugador.py, puro) y su dibujo cacheado en sprites.py.

Las hojas del jugador salen de los 4 personajes de Higgsfield
(assets/sprites/retratos/<rol>.png) con tools/generar_jugadores_higgsfield.py,
junto a un mapa de partes. La regresión clave: teñir una parte solo cambia
los píxeles de esa parte, y su color más usado queda exacto en el elegido."""

import dataclasses
import json
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame  # noqa: E402
import pytest  # noqa: E402

from src.core import assets  # noqa: E402
from src.core.apariencia import PREDETERMINADA, Apariencia  # noqa: E402
from src.ui import sprites, tinte_jugador  # noqa: E402

ROLES = assets.ROLES_APARIENCIA
CARPETA_HOJAS = os.path.join(RAIZ, assets.RUTA_SPRITES_JUGADORES)
COLOR = (1, 2, 3)
VESTIDO = Apariencia(piel=6, pelo=3, ropa=1, pantalon=5, zapatos=2)
CAMPOS = ("piel", "pelo", "ropa", "pantalon", "zapatos")


@pytest.fixture(autouse=True)
def cache_limpio():
    pygame.display.init()
    pygame.display.set_mode((1, 1))
    sprites.limpiar_cache_hojas()
    yield
    sprites.limpiar_cache_hojas()


def _leer_surface(superficie, escala=1):
    return tuple(
        tuple(None if superficie.get_at((x * escala, y * escala)).a == 0
              else tuple(superficie.get_at((x * escala, y * escala)))[:3]
              for x in range(superficie.get_width() // escala))
        for y in range(superficie.get_height() // escala))


def _colores(cuadro):
    return {c for fila in cuadro for c in fila if c is not None}


# --- Apariencia (pura) ---------------------------------------------------

def test_la_predeterminada_no_cambia_nada():
    assert PREDETERMINADA == Apariencia(None, None, None)
    assert PREDETERMINADA.es_predeterminada()
    assert Apariencia().es_predeterminada()
    # piel=0 es un tono elegido (el más claro), no "sin elegir".
    for apariencia in (Apariencia(piel=0), Apariencia(cabeza="ciudadano"), Apariencia(traje="candidato")):
        assert not apariencia.es_predeterminada()


def test_con_cambia_un_solo_campo_y_deja_el_original():
    con_piel = PREDETERMINADA.con("piel", 3)
    assert con_piel == Apariencia(piel=3)
    assert PREDETERMINADA == Apariencia()
    completa = con_piel.con("cabeza", "influencer").con("traje", "periodista")
    assert completa == Apariencia(3, "influencer", "periodista")
    assert con_piel == Apariencia(piel=3)
    assert completa.con("cabeza", None) == Apariencia(3, None, "periodista")  # vuelve a la del rol
    assert completa.con("piel", 0).piel == 0
    with pytest.raises(TypeError):
        completa.con("mascota", "perro")  # no hay pestaña PET


def test_cabeza_y_traje_para_un_rol():
    for rol in ROLES:
        assert PREDETERMINADA.cabeza_para(rol) == rol
        assert PREDETERMINADA.traje_para(rol) == rol
    vestido = Apariencia(cabeza="candidato", traje="ciudadano")
    assert vestido.cabeza_para("influencer") == "candidato"
    assert vestido.traje_para("influencer") == "ciudadano"
    assert Apariencia(cabeza="candidato").traje_para("influencer") == "influencer"
    assert Apariencia(piel=4).cabeza_para("periodista") == "periodista"


def test_es_inmutable_y_sirve_de_clave():
    apariencia = Apariencia(piel=1, cabeza="candidato")
    with pytest.raises(dataclasses.FrozenInstanceError):
        apariencia.piel = 2
    with pytest.raises(dataclasses.FrozenInstanceError):
        apariencia.traje = "ciudadano"
    assert apariencia == Apariencia(piel=1, cabeza="candidato")
    cache = {apariencia: "armada"}
    assert cache[Apariencia(piel=1, cabeza="candidato")] == "armada"
    assert Apariencia(piel=1, cabeza="periodista") not in cache
    assert len({PREDETERMINADA, Apariencia(), Apariencia(None, None, None)}) == 1


def test_a_dict_y_de_dict_ida_y_vuelta_por_json():
    vacios = {"pelo": None, "ropa": None, "pantalon": None, "zapatos": None}
    assert PREDETERMINADA.a_dict() == {"piel": None, "cabeza": None, "traje": None, **vacios}
    viejo = Apariencia(piel=6, cabeza="ciudadano", traje="influencer")
    assert viejo.a_dict() == {"piel": 6, "cabeza": "ciudadano", "traje": "influencer", **vacios}
    assert VESTIDO.a_dict() == {"piel": 6, "cabeza": None, "traje": None, "pelo": 3, "ropa": 1, "pantalon": 5,
                                "zapatos": 2}
    for piel in (None, *range(len(assets.TONOS_PIEL))):
        for cabeza in (None, *ROLES):
            for traje in (None, *ROLES):
                apariencia = Apariencia(piel, cabeza, traje)
                assert Apariencia.de_dict(json.loads(json.dumps(apariencia.a_dict()))) == apariencia


@pytest.mark.parametrize("piel", [True, False, -1, len(assets.TONOS_PIEL), 2.0, "3", None, [1]])
def test_de_dict_descarta_una_piel_invalida_sin_tocar_lo_demas(piel):
    datos = {"piel": piel, "cabeza": "candidato", "traje": "ciudadano"}
    assert Apariencia.de_dict(datos) == Apariencia(None, "candidato", "ciudadano")


# "Ciudadano" con mayúscula (como protocolo.ROLES) no es el nombre de una receta.
@pytest.mark.parametrize("rol", ["astronauta", "Ciudadano", "", 3, None, ["ciudadano"], {"rol": "ciudadano"}])
def test_de_dict_descarta_una_cabeza_o_un_traje_desconocido(rol):
    assert Apariencia.de_dict({"piel": 2, "cabeza": rol, "traje": "periodista"}) == Apariencia(2, None, "periodista")
    assert Apariencia.de_dict({"piel": 2, "cabeza": "periodista", "traje": rol}) == Apariencia(2, "periodista", None)


@pytest.mark.parametrize("datos", [None, [], ["piel", 1], "piel=1", 7])
def test_de_dict_de_algo_que_no_es_un_dict_es_la_predeterminada(datos):
    assert Apariencia.de_dict(datos) == PREDETERMINADA


def test_de_dict_con_claves_faltantes_o_de_mas():
    assert Apariencia.de_dict({}) == PREDETERMINADA
    assert Apariencia.de_dict({"piel": 4}) == Apariencia(piel=4)
    assert Apariencia.de_dict({"traje": "influencer"}) == Apariencia(traje="influencer")
    assert Apariencia.de_dict({"cabeza": "periodista", "mascota": "perro"}) == Apariencia(cabeza="periodista")
    for piel in range(len(assets.TONOS_PIEL)):
        assert Apariencia.de_dict({"piel": piel}).piel == piel


# --- Hojas hechas desde Higgsfield ---------------------------------------

def test_los_4_roles_tienen_personaje():
    assert ROLES == ("ciudadano", "influencer", "periodista", "candidato")
    for rol in ROLES:
        assert os.path.isfile(os.path.join(RAIZ, assets.RUTA_SPRITES_RETRATOS, f"{rol}.png"))
    assert os.path.isfile(os.path.join(RAIZ, "tools", "generar_jugadores_higgsfield.py"))


@pytest.mark.parametrize("rol", ROLES)
def test_cada_hoja_trae_atlas_y_mapa_de_partes(rol):
    hoja = pygame.image.load(os.path.join(CARPETA_HOJAS, f"{rol}.png"))
    partes = pygame.image.load(os.path.join(CARPETA_HOJAS, f"{rol}.partes.png"))
    assert hoja.get_size() == partes.get_size() and hoja.get_height() == assets.ALTO_JUGADOR_HF
    with open(os.path.join(CARPETA_HOJAS, f"{rol}.atlas.json"), encoding="utf-8") as archivo:
        atlas = json.load(archivo)
    assert set(atlas["frames"]) == {"quieto", "paso_a", "paso_b", "dash"}
    assert atlas["animations"][assets.ANIMACION_CAMINAR]["frames"] == ["quieto", "paso_a", "quieto", "paso_b"]


@pytest.mark.parametrize("rol", ROLES)
def test_el_mapa_marca_las_5_partes_solo_sobre_el_dibujo(rol):
    datos = sprites._datos_hoja(rol)
    assert datos is not None
    assert set(datos["refs"]) == set(CAMPOS)
    for nombre, cuadro in datos["cuadros"].items():
        for fila, fila_partes in zip(cuadro, datos["partes"][nombre]):
            for color, parte in zip(fila, fila_partes):
                assert parte is None or color is not None  # nunca una parte sobre un hueco


@pytest.mark.parametrize("rol", ROLES)
def test_dar_un_paso_mueve_los_pies(rol):
    datos = sprites._datos_hoja(rol)
    assert datos["cuadros"]["quieto"] != datos["cuadros"]["paso_a"] != datos["cuadros"]["paso_b"]
    arriba = len(datos["cuadros"]["quieto"]) // 2
    assert datos["cuadros"]["quieto"][:arriba] == datos["cuadros"]["paso_a"][:arriba]  # la cabeza no se mueve


# --- Teñido (tinte_jugador, puro) ----------------------------------------

def test_teñir_deja_la_referencia_exacta_y_las_sombras_en_proporcion():
    objetivo = (200, 40, 60)
    assert tinte_jugador.teñir((100, 100, 100), (100, 100, 100), objetivo) == objetivo
    sombra = tinte_jugador.teñir((50, 50, 50), (100, 100, 100), objetivo)
    brillo = tinte_jugador.teñir((150, 150, 150), (100, 100, 100), objetivo)
    assert sum(sombra) < sum(objetivo) < sum(brillo)


def test_objetivos_de_una_apariencia():
    assert tinte_jugador.objetivos(None) == {} == tinte_jugador.objetivos(PREDETERMINADA)
    assert tinte_jugador.objetivos(Apariencia(cabeza="candidato")) == {}  # el arte no se mezcla
    assert tinte_jugador.objetivos(VESTIDO) == {
        "piel": assets.TONOS_PIEL[6], "pelo": assets.TONOS_PELO[3], "ropa": assets.COLORES_ROPA[1],
        "pantalon": assets.COLORES_PANTALON[5], "zapatos": assets.COLORES_ZAPATOS[2]}


def test_parte_de_un_pixel_del_mapa():
    for parte, color in assets.COLOR_PARTE_JUGADOR.items():
        assert tinte_jugador.parte_de((*color, 255)) == parte
    assert tinte_jugador.parte_de(None) is None
    assert tinte_jugador.parte_de((255, 0, 0, 0)) is None
    assert tinte_jugador.parte_de((1, 2, 3, 255)) is None


@pytest.mark.parametrize("campo", CAMPOS)
@pytest.mark.parametrize("rol", ROLES)
def test_teñir_una_parte_solo_cambia_sus_pixeles(rol, campo):
    datos = sprites._datos_hoja(rol)
    cuadro, partes = datos["cuadros"]["quieto"], datos["partes"]["quieto"]
    objetivo = tinte_jugador.PALETAS[campo][2]
    teñido = tinte_jugador.teñir_cuadro(cuadro, partes, datos["refs"], {campo: objetivo})
    cambiados = 0
    for y, (fila, fila_teñida) in enumerate(zip(cuadro, teñido)):
        for x, (antes, despues) in enumerate(zip(fila, fila_teñida)):
            if antes != despues:
                cambiados += 1
                assert partes[y][x] == campo, (rol, campo, x, y)
    assert cambiados > 0
    assert objetivo in {tuple(c[:3]) for fila in teñido for c in fila if c is not None}


# --- sprites.py ----------------------------------------------------------

def test_escala_hd_es_la_mitad_hacia_arriba():
    assert [sprites.escala_hd(e) for e in (1, 2, 3, 4, 5, 10, 11)] == [1, 1, 2, 2, 3, 5, 6]


def test_sprite_jugador_vestido_mide_lo_mismo_que_la_hoja():
    for escala in (1, 2, 3, 5):
        vestido = sprites.sprite_jugador(COLOR, escala, rol="candidato", apariencia=VESTIDO)
        normal = sprites.sprite_jugador(COLOR, escala, rol="candidato")
        assert vestido.get_size() == normal.get_size()
        assert normal.get_height() == assets.ALTO_JUGADOR_HF * sprites.escala_hd(escala)


def test_sprite_jugador_vestido_es_la_hoja_teñida():
    datos = sprites._datos_hoja("influencer")
    esperado = tinte_jugador.teñir_cuadro(datos["cuadros"]["quieto"], datos["partes"]["quieto"], datos["refs"],
                                          tinte_jugador.objetivos(VESTIDO))
    vestido = _leer_surface(sprites.sprite_jugador(COLOR, 1, rol="influencer", apariencia=VESTIDO))
    assert vestido == tuple(tuple(None if c is None else c[:3] for c in fila) for fila in esperado)


def test_sin_colores_es_la_misma_surface_de_la_hoja():
    for opciones in ({}, {"tiempo": 0.16, "caminando": True}, {"dash": True}):
        hoja = sprites.sprite_jugador(COLOR, rol="periodista", **opciones)
        for apariencia in (PREDETERMINADA, Apariencia(cabeza="candidato", traje="ciudadano")):
            assert sprites.sprite_jugador(COLOR, rol="periodista", apariencia=apariencia, **opciones) is hoja


def test_sprite_jugador_vestido_camina_y_hace_dash():
    quieto = sprites.sprite_jugador(COLOR, 1, rol="ciudadano", apariencia=VESTIDO)
    paso = sprites.sprite_jugador(COLOR, 1, rol="ciudadano", apariencia=VESTIDO, tiempo=0.16, caminando=True)
    dash = sprites.sprite_jugador(COLOR, 1, rol="ciudadano", apariencia=VESTIDO, dash=True)
    assert _leer_surface(quieto) != _leer_surface(paso)
    assert dash.get_size() == quieto.get_size()


def test_se_tiñe_una_vez_por_combinacion_de_colores():
    vestido = sprites.sprite_jugador(COLOR, rol="ciudadano", apariencia=Apariencia(piel=2, ropa=1))
    assert sprites.sprite_jugador(COLOR, rol="ciudadano", apariencia=Apariencia(piel=2, ropa=1)) is vestido
    # cabeza / traje (de versiones viejas) no cambian el dibujo: la misma hoja teñida.
    assert sprites.sprite_jugador(COLOR, rol="ciudadano", apariencia=Apariencia(piel=2, ropa=1, traje="candidato")) \
        is vestido
    assert sprites.sprite_jugador(COLOR, rol="ciudadano", apariencia=Apariencia(piel=3, ropa=1)) is not vestido


def test_sin_mapa_de_partes_cae_a_la_hoja_sin_teñir(tmp_path, monkeypatch):
    for nombre in ("candidato.png", "candidato.atlas.json"):
        with open(os.path.join(CARPETA_HOJAS, nombre), "rb") as origen:
            (tmp_path / nombre).write_bytes(origen.read())
    monkeypatch.setattr(assets, "RUTA_SPRITES_JUGADORES", str(tmp_path))
    for opciones in ({}, {"tiempo": 0.16, "caminando": True}, {"dash": True}):
        hoja = sprites.sprite_jugador(COLOR, rol="candidato", **opciones)
        assert sprites.sprite_jugador(COLOR, rol="candidato", apariencia=VESTIDO, **opciones) is hoja
    assert sprites.sprite_parte_jugador(assets.SIMBOLOS_CABEZA, "candidato") is None


def test_sin_rol_la_apariencia_se_ignora():
    muneco = sprites.sprite_jugador(COLOR, rol=None)
    assert sprites.sprite_jugador(COLOR, rol=None, apariencia=VESTIDO) is muneco


def test_sprite_parte_jugador_es_media_hoja_teñida():
    cabeza = sprites.sprite_parte_jugador(assets.SIMBOLOS_CABEZA, "periodista", None, 2)
    traje = sprites.sprite_parte_jugador(assets.SIMBOLOS_TRAJE, "periodista", None, 2)
    assert cabeza.get_height() + traje.get_height() <= assets.ALTO_JUGADOR_HF
    assert sprites.sprite_parte_jugador(assets.SIMBOLOS_CABEZA, "periodista", None, 2) is cabeza
    oscura = sprites.sprite_parte_jugador(assets.SIMBOLOS_CABEZA, "periodista", assets.TONOS_PIEL[7], 2)
    assert oscura is not cabeza and assets.TONOS_PIEL[7] in _colores(_leer_surface(oscura))
    assert sprites.sprite_parte_jugador(assets.SIMBOLOS_CABEZA, "astronauta") is None


def test_limpiar_cache_hojas_olvida_pixeles_vestidos_y_partes():
    sprites.sprite_jugador(COLOR, rol="candidato", apariencia=VESTIDO)
    sprites.sprite_parte_jugador(assets.SIMBOLOS_TRAJE, "periodista")
    assert sprites._cache_pixeles and sprites._cache_vestidos and sprites._cache_partes
    sprites.limpiar_cache_hojas()
    assert not sprites._cache_pixeles and not sprites._cache_vestidos and not sprites._cache_partes
