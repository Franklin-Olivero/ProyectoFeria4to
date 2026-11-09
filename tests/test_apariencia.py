"""Vestidores del lobby online: la Apariencia (pura), el jugador armado por
partes con las recetas de Pixelbolt (src/ui/receta_jugador.py, puro) y su
dibujo cacheado en sprites.py.

La regresión clave: con la apariencia predeterminada las recetas
reconstruyen píxel a píxel la hoja PNG de cada rol. Los demás tests
comparan contra esas mismas hojas: la cabeza o el traje prestados se ven
como en la hoja del rol que los presta y el accesorio siempre es el del rol."""

import dataclasses
import itertools
import json
import os
import shutil
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

import pygame  # noqa: E402
import pytest  # noqa: E402

from src.core import assets, balance  # noqa: E402
from src.core.apariencia import PREDETERMINADA, Apariencia  # noqa: E402
from src.ui import receta_jugador, sprites  # noqa: E402

ROLES = assets.ROLES_APARIENCIA
CARPETA_RECETAS = os.path.join(RAIZ, assets.RUTA_RECETAS_SPRITES)
CARPETA_HOJAS = os.path.join(RAIZ, assets.RUTA_SPRITES_JUGADORES)
ANCHO, ALTO = 16, 20  # cuadro de jugador
ALTO_PARTE = 10  # filas de la cabeza y del traje en el cuadro de vista previa
PIEL_CIUDADANO = (200, 144, 90)
PIEL_CLARA = (242, 200, 160)  # Influencer, Periodista y Candidato
COLOR = (1, 2, 3)
VESTIDO = Apariencia(piel=6, cabeza="ciudadano", traje="influencer")


@pytest.fixture(autouse=True)
def cache_limpio():
    sprites.limpiar_cache_hojas()
    yield
    sprites.limpiar_cache_hojas()


@pytest.fixture(scope="module")
def recetas():
    return {rol: receta_jugador.leer_receta(rol, CARPETA_RECETAS) for rol in ROLES}


@pytest.fixture(scope="module")
def hojas():
    """{rol: ({nombre_del_cuadro: cuadro}, atlas)} de las hojas PNG reales."""
    return {rol: _leer_hoja(rol) for rol in ROLES}


# --- Ayudas: hojas, Surfaces y recetas -----------------------------------

def _color(pixel):
    """Píxel de una Surface como en un cuadro armado: None si es
    transparente, RGB si es opaco (un alfa intermedio nunca coincide)."""
    if pixel.a == 0:
        return None
    return tuple(pixel)[:3] if pixel.a == 255 else tuple(pixel)


def _leer_hoja(rol):
    imagen = pygame.image.load(os.path.join(CARPETA_HOJAS, f"{rol}.png"))
    with open(os.path.join(CARPETA_HOJAS, f"{rol}.atlas.json"), encoding="utf-8") as archivo:
        atlas = json.load(archivo)
    cuadros = {}
    for nombre, datos in atlas["frames"].items():
        r = datos["frame"]
        cuadros[nombre] = tuple(
            tuple(_color(imagen.get_at((r["x"] + x, r["y"] + y))) for x in range(r["w"]))
            for y in range(r["h"]))
    return cuadros, atlas


def _leer_surface(superficie, escala):
    """Cuadro de una Surface escalada: un píxel de sprite por bloque."""
    return tuple(
        tuple(_color(superficie.get_at((x * escala, y * escala)))
              for x in range(superficie.get_width() // escala))
        for y in range(superficie.get_height() // escala))


def _diferencias(cuadro, esperado):
    """[(x, y, obtenido, esperado)] de dos cuadros del mismo tamaño."""
    return [(x, y, a, b) for y, (fila, fila_esperada) in enumerate(zip(cuadro, esperado))
            for x, (a, b) in enumerate(zip(fila, fila_esperada)) if a != b]


def _cuadro_receta(receta, nombre):
    return next(c for c in receta["frames"] if c["name"] == nombre)


def _accesorio(receta):
    """Símbolo del accesorio: el único que no es cabeza ni traje."""
    (simbolo,) = [s for s in receta["symbols"] if s not in assets.SIMBOLOS_CABEZA + assets.SIMBOLOS_TRAJE]
    return simbolo


def _letras(receta, op):
    """{(x, y): letra} opacas del símbolo de `op`, tomado de `receta`."""
    return {(op["x"] + dx, op["y"] + dy): letra
            for dy, fila in enumerate(receta["symbols"][op["symbol"]])
            for dx, letra in enumerate(fila) if letra != "."}


def _sello(receta, nombre, simbolos):
    """{(x, y): letra} que estampan `simbolos` en el cuadro `nombre`."""
    letras = {}
    for op in _cuadro_receta(receta, nombre)["ops"]:
        if op["symbol"] in simbolos:
            letras.update(_letras(receta, op))
    return letras


def _filas(receta, nombre, simbolos):
    """Filas del cuadro `nombre` que ocupan los sellos de `simbolos`."""
    filas = set()
    for op in _cuadro_receta(receta, nombre)["ops"]:
        if op["symbol"] in simbolos:
            filas.update(range(op["y"], op["y"] + len(receta["symbols"][op["symbol"]])))
    return filas


def _piel_visible(recetas, rol, apariencia, nombre):
    """Píxeles que quedan con la letra de piel en el cuadro del rol vestido:
    mismas estampas y orden que su receta, la cabeza y el traje de las
    recetas elegidas y el accesorio del rol."""
    letras = {}
    for op in _cuadro_receta(recetas[rol], nombre)["ops"]:
        simbolo = op["symbol"]
        if simbolo in assets.SIMBOLOS_CABEZA:
            fuente = apariencia.cabeza_para(rol)
        elif simbolo in assets.SIMBOLOS_TRAJE:
            fuente = apariencia.traje_para(rol)
        else:
            fuente = rol
        letras.update(_letras(recetas[fuente], op))
    return {p for p, letra in letras.items() if letra == assets.SIMBOLO_PIEL}


def _vestido_por_cuadro(recetas, rol, apariencia):
    """{nombre_del_cuadro: cuadro armado} del rol vestido con `apariencia`."""
    vestido = {}
    for animacion, (cuadros, _) in receta_jugador.armar_animaciones(recetas, rol, apariencia).items():
        vestido.update(zip(recetas[rol]["animations"][animacion]["frames"], cuadros))
    return vestido


def _pixeles():
    return itertools.product(range(ALTO), range(ANCHO))


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
    assert PREDETERMINADA.a_dict() == {"piel": None, "cabeza": None, "traje": None}
    assert VESTIDO.a_dict() == {"piel": 6, "cabeza": "ciudadano", "traje": "influencer"}
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


# --- Recetas (receta_jugador, puro) --------------------------------------

def test_los_4_roles_jugables_prestan_partes():
    assert set(ROLES) == set(balance.STATS_POR_ROL)


@pytest.mark.parametrize("rol", ROLES)
def test_leer_receta_de_los_4_roles(rol):
    receta = receta_jugador.leer_receta(rol)  # carpeta por defecto: la que usa el juego
    assert receta is not None
    assert receta == receta_jugador.leer_receta(rol, CARPETA_RECETAS)
    assert (receta["width"], receta["height"]) == (ANCHO, ALTO)
    assert assets.SIMBOLO_PIEL in receta["palette"]
    assert set(assets.SIMBOLOS_CABEZA + assets.SIMBOLOS_TRAJE) <= set(receta["symbols"])
    assert _accesorio(receta)  # un único accesorio
    assert any(c["name"] == assets.CUADRO_VISTA_PREVIA for c in receta["frames"])


def test_leer_receta_que_no_existe_es_none(tmp_path):
    assert receta_jugador.leer_receta("astronauta") is None
    assert receta_jugador.leer_receta("ciudadano", str(tmp_path)) is None
    assert receta_jugador.leer_receta("ciudadano", str(tmp_path / "no_existe")) is None


@pytest.mark.parametrize("contenido", [b"{roto", b"", b"[1, 2", b"\xff\xfe basura"])
def test_leer_receta_con_json_roto_es_none(tmp_path, contenido):
    (tmp_path / "rota.pixel.json").write_bytes(contenido)
    assert receta_jugador.leer_receta("rota", str(tmp_path)) is None


RECETA_MINIMA = {
    "width": 16, "height": 20, "palette": {"s": "#c8905a"},
    "symbols": {"cabeza": ["ss"]}, "frames": [{"name": "quieto", "ops": []}],
}


def _sin(clave):
    return {k: v for k, v in RECETA_MINIMA.items() if k != clave}


def test_leer_receta_minima(tmp_path):
    # Control de los casos de abajo: con la forma completa sí se lee.
    (tmp_path / "minima.pixel.json").write_text(json.dumps(RECETA_MINIMA), encoding="utf-8")
    assert receta_jugador.leer_receta("minima", str(tmp_path)) == RECETA_MINIMA


@pytest.mark.parametrize("datos", [
    [RECETA_MINIMA], "receta", 42, None,
    _sin("palette"), _sin("symbols"), _sin("frames"), _sin("width"), _sin("height"),
    {**RECETA_MINIMA, "palette": ["#c8905a"]},
    {**RECETA_MINIMA, "symbols": "cabeza"},
    {**RECETA_MINIMA, "frames": []},
    {**RECETA_MINIMA, "width": "16"},
    {**RECETA_MINIMA, "height": 20.0},
])
def test_leer_receta_sin_forma_de_receta_es_none(tmp_path, datos):
    (tmp_path / "rara.pixel.json").write_text(json.dumps(datos), encoding="utf-8")
    assert receta_jugador.leer_receta("rara", str(tmp_path)) is None


def test_color_hex():
    assert receta_jugador.color_hex("#c8905a") == PIEL_CIUDADANO
    assert receta_jugador.color_hex("#F2C8A0") == PIEL_CLARA
    assert receta_jugador.color_hex("f2c8a0") == PIEL_CLARA
    assert receta_jugador.color_hex("#000000") == (0, 0, 0)
    assert receta_jugador.color_hex("#ffffff") == (255, 255, 255)


def test_piel_original(recetas):
    assert receta_jugador.piel_original(recetas["ciudadano"]) == PIEL_CIUDADANO
    assert receta_jugador.piel_original(recetas["influencer"]) == PIEL_CLARA
    for rol in ROLES:  # la pestaña COLOR incluye el tono de cada hoja
        assert receta_jugador.piel_original(recetas[rol]) in assets.TONOS_PIEL
    assert receta_jugador.piel_original({"palette": {"k": "#100e1e"}}) is None


def test_tono_de_piel(recetas):
    tono = receta_jugador.tono_de_piel
    assert tono(PREDETERMINADA, recetas, "ciudadano") == PIEL_CIUDADANO
    assert tono(PREDETERMINADA, recetas, "candidato") == PIEL_CLARA
    # Sin elegir, la de la cabeza que lleva puesta; elegida, la elegida.
    assert tono(Apariencia(cabeza="ciudadano"), recetas, "candidato") == PIEL_CIUDADANO
    assert tono(Apariencia(piel=0, cabeza="ciudadano"), recetas, "candidato") == assets.TONOS_PIEL[0]
    for i, color in enumerate(assets.TONOS_PIEL):
        assert tono(Apariencia(piel=i), recetas, "influencer") == color


@pytest.mark.parametrize("rol", ROLES)
def test_la_predeterminada_reconstruye_la_hoja_png_pixel_a_pixel(rol, recetas, hojas):
    cuadros_png, atlas = hojas[rol]
    armadas = receta_jugador.armar_animaciones(recetas, rol, PREDETERMINADA)
    assert set(armadas) == set(atlas["animations"])
    for animacion, datos in atlas["animations"].items():
        cuadros, duraciones = armadas[animacion]
        assert duraciones == [atlas["frames"][nombre]["duration"] for nombre in datos["frames"]]
        assert len(cuadros) == len(datos["frames"])
        for cuadro, nombre in zip(cuadros, datos["frames"]):
            assert len(cuadro) == ALTO and all(len(fila) == ANCHO for fila in cuadro)
            diferencias = _diferencias(cuadro, cuadros_png[nombre])
            assert not diferencias, (animacion, nombre, diferencias[:5])


def test_las_recetas_estampan_cabeza_y_traje_en_el_mismo_sitio(recetas):
    """Lo que permite prestar partes (y comparar con la hoja de otro rol):
    en cada cuadro las 4 recetas ponen la cabeza y el traje en el mismo
    sitio, la cabeza no comparte filas con el traje y nada de ningún traje
    se estampa encima del accesorio de un rol."""
    partes = assets.SIMBOLOS_CABEZA + assets.SIMBOLOS_TRAJE
    for nombre in (c["name"] for c in recetas[ROLES[0]]["frames"]):
        sitios = {tuple((op["symbol"], op["x"], op["y"]) for op in _cuadro_receta(recetas[rol], nombre)["ops"]
                        if op["symbol"] in partes) for rol in ROLES}
        assert len(sitios) == 1, nombre
        for rol, otro in itertools.product(ROLES, repeat=2):
            assert not _filas(recetas[rol], nombre, assets.SIMBOLOS_CABEZA) & _filas(
                recetas[otro], nombre, assets.SIMBOLOS_TRAJE)
            accesorio = _accesorio(recetas[rol])
            orden = [op["symbol"] for op in _cuadro_receta(recetas[rol], nombre)["ops"]]
            encima = orden[orden.index(accesorio) + 1:]
            assert not set(_sello(recetas[rol], nombre, (accesorio,))) & set(_sello(recetas[otro], nombre, encima))


@pytest.mark.parametrize("campo, simbolos", [("cabeza", assets.SIMBOLOS_CABEZA), ("traje", assets.SIMBOLOS_TRAJE)])
@pytest.mark.parametrize("rol, otro", list(itertools.permutations(ROLES, 2)))
def test_la_parte_prestada_se_ve_como_en_la_hoja_del_otro_rol(campo, simbolos, rol, otro, recetas, hojas):
    """En las filas de la parte (fuera de los accesorios) el cuadro es el de
    la hoja del otro rol; el resto del cuerpo y el accesorio, los de la hoja
    propia (la piel del accesorio combina con la cabeza puesta)."""
    apariencia = PREDETERMINADA.con(campo, otro)
    piel = receta_jugador.piel_original(recetas[apariencia.cabeza_para(rol)])
    propias, ajenas = hojas[rol][0], hojas[otro][0]
    diferencias = []
    for nombre, cuadro in _vestido_por_cuadro(recetas, rol, apariencia).items():
        filas_parte = _filas(recetas[rol], nombre, simbolos)
        accesorio = _sello(recetas[rol], nombre, (_accesorio(recetas[rol]),))
        accesorio_ajeno = _sello(recetas[otro], nombre, (_accesorio(recetas[otro]),))
        for y, x in _pixeles():
            if (x, y) in accesorio:
                esperado = piel if accesorio[(x, y)] == assets.SIMBOLO_PIEL else propias[nombre][y][x]
            elif y in filas_parte:
                if (x, y) in accesorio_ajeno:
                    continue  # en la hoja del otro rol ahí está su accesorio
                esperado = ajenas[nombre][y][x]
            else:
                esperado = propias[nombre][y][x]
            if cuadro[y][x] != esperado:
                diferencias.append((nombre, x, y, cuadro[y][x], esperado))
        assert cuadro != propias[nombre], nombre  # la parte sí cambió
    assert not diferencias, diferencias[:5]


@pytest.mark.parametrize("rol", ROLES)
def test_el_accesorio_siempre_es_el_del_rol(rol, recetas, hojas):
    accesorio = _accesorio(recetas[rol])
    for cabeza, traje in itertools.product(ROLES, repeat=2):
        apariencia = Apariencia(cabeza=cabeza, traje=traje)
        piel = receta_jugador.piel_original(recetas[cabeza])
        for nombre, cuadro in _vestido_por_cuadro(recetas, rol, apariencia).items():
            for (x, y), letra in _sello(recetas[rol], nombre, (accesorio,)).items():
                esperado = piel if letra == assets.SIMBOLO_PIEL else hojas[rol][0][nombre][y][x]
                assert cuadro[y][x] == esperado, (apariencia, nombre, x, y)


@pytest.mark.parametrize("rol", ROLES)
def test_la_piel_elegida_pinta_solo_la_piel(rol, recetas, hojas):
    """Con piel=i cada píxel de piel queda con TONOS_PIEL[i] y ningún otro
    píxel de la hoja cambia."""
    propias = hojas[rol][0]
    for i, tono in enumerate(assets.TONOS_PIEL):
        apariencia = Apariencia(piel=i)
        for nombre, cuadro in _vestido_por_cuadro(recetas, rol, apariencia).items():
            piel = _piel_visible(recetas, rol, apariencia, nombre)
            assert piel, nombre
            for y, x in _pixeles():
                esperado = tono if (x, y) in piel else propias[nombre][y][x]
                assert cuadro[y][x] == esperado, (i, nombre, x, y)


def test_la_piel_elegida_pinta_la_cabeza_prestada_y_la_mano_del_candidato(recetas):
    mano = _accesorio(recetas["candidato"])
    for i, tono in enumerate(assets.TONOS_PIEL):
        for cabeza in ROLES:
            apariencia = Apariencia(piel=i, cabeza=cabeza)
            for nombre, cuadro in _vestido_por_cuadro(recetas, "candidato", apariencia).items():
                piel_mano = [p for p, letra in _sello(recetas["candidato"], nombre, (mano,)).items()
                             if letra == assets.SIMBOLO_PIEL]
                assert piel_mano
                assert {cuadro[y][x] for x, y in piel_mano} == {tono}
                assert {cuadro[y][x] for x, y in _piel_visible(recetas, "candidato", apariencia, nombre)} == {tono}


def test_sin_piel_elegida_la_mano_del_candidato_toma_el_tono_de_la_cabeza(recetas):
    apariencia = Apariencia(cabeza="ciudadano")
    mano = _accesorio(recetas["candidato"])
    for nombre, cuadro in _vestido_por_cuadro(recetas, "candidato", apariencia).items():
        piel = _piel_visible(recetas, "candidato", apariencia, nombre)
        piel_mano = {p for p, letra in _sello(recetas["candidato"], nombre, (mano,)).items()
                     if letra == assets.SIMBOLO_PIEL}
        assert piel_mano and piel_mano <= piel
        assert {cuadro[y][x] for x, y in piel} == {PIEL_CIUDADANO}


def test_armar_animaciones_sin_alguna_receta_es_none(recetas):
    def sin(rol):
        return {r: receta for r, receta in recetas.items() if r != rol}

    armar = receta_jugador.armar_animaciones
    assert armar(sin("candidato"), "candidato", PREDETERMINADA) is None
    assert armar({**recetas, "candidato": None}, "candidato", PREDETERMINADA) is None
    assert armar(sin("influencer"), "candidato", Apariencia(cabeza="influencer")) is None
    assert armar(sin("periodista"), "candidato", Apariencia(traje="periodista")) is None
    assert armar(recetas, "astronauta", PREDETERMINADA) is None
    # Una receta que no se usa no hace falta.
    assert armar(sin("influencer"), "candidato", Apariencia(cabeza="ciudadano", traje="periodista")) is not None


@pytest.mark.parametrize("rol", ROLES)
def test_armar_parte_es_la_cabeza_o_el_traje_de_la_hoja_sin_accesorio(rol, recetas, hojas):
    quieto = hojas[rol][0][assets.CUADRO_VISTA_PREVIA]
    accesorio = _sello(recetas[rol], assets.CUADRO_VISTA_PREVIA, (_accesorio(recetas[rol]),))
    for simbolos in (assets.SIMBOLOS_CABEZA, assets.SIMBOLOS_TRAJE):
        parte = receta_jugador.armar_parte(recetas, rol, simbolos, None)
        assert len(parte) == ALTO_PARTE and all(len(fila) == ANCHO for fila in parte)
        arriba = min(_filas(recetas[rol], assets.CUADRO_VISTA_PREVIA, simbolos))
        for y, x in itertools.product(range(ALTO_PARTE), range(ANCHO)):
            if (x, arriba + y) not in accesorio:
                assert parte[y][x] == quieto[arriba + y][x], (simbolos, x, y)


def test_armar_parte_con_y_sin_piel(recetas):
    tono = assets.TONOS_PIEL[0]
    original = receta_jugador.armar_parte(recetas, "ciudadano", assets.SIMBOLOS_CABEZA, None)
    pintada = receta_jugador.armar_parte(recetas, "ciudadano", assets.SIMBOLOS_CABEZA, tono)
    piel = {(x, y) for y, fila in enumerate(original) for x, color in enumerate(fila) if color == PIEL_CIUDADANO}
    assert piel
    for y, x in itertools.product(range(ALTO_PARTE), range(ANCHO)):
        assert pintada[y][x] == (tono if (x, y) in piel else original[y][x]), (x, y)
    # El traje no tiene piel: un tono no lo cambia.
    traje = receta_jugador.armar_parte(recetas, "periodista", assets.SIMBOLOS_TRAJE, None)
    assert receta_jugador.armar_parte(recetas, "periodista", assets.SIMBOLOS_TRAJE, tono) == traje


def test_armar_parte_sin_receta_o_vacia_es_none(recetas):
    assert receta_jugador.armar_parte(recetas, "astronauta", assets.SIMBOLOS_CABEZA, None) is None
    assert receta_jugador.armar_parte({**recetas, "ciudadano": None}, "ciudadano", assets.SIMBOLOS_TRAJE, None) is None
    assert receta_jugador.armar_parte(recetas, "ciudadano", ("sombrero",), None) is None


# --- Dibujo cacheado (sprites.py) ----------------------------------------

def test_sprite_jugador_vestido_mide_lo_mismo_que_la_hoja():
    for escala in (1, 2, assets.ESCALA_PIXEL):
        vestido = sprites.sprite_jugador(COLOR, escala, rol="candidato", apariencia=VESTIDO)
        assert vestido.get_size() == (ANCHO * escala, ALTO * escala)
        assert vestido.get_size() == sprites.sprite_jugador(COLOR, escala, rol="candidato").get_size()


def test_sprite_jugador_vestido_dibuja_el_jugador_armado(recetas):
    hoja = _leer_surface(sprites.sprite_jugador(COLOR, 2, rol="candidato"), 2)
    for apariencia in (VESTIDO, Apariencia(piel=0), Apariencia(cabeza="ciudadano"), Apariencia(traje="periodista")):
        cuadros, _ = receta_jugador.armar_animaciones(recetas, "candidato", apariencia)["caminar"]
        vestido = _leer_surface(sprites.sprite_jugador(COLOR, 2, rol="candidato", apariencia=apariencia), 2)
        assert vestido == cuadros[0]
        assert vestido != hoja, apariencia


def test_sprite_jugador_con_la_predeterminada_es_la_misma_surface_de_la_hoja():
    for opciones in ({}, {"tiempo": 0.16, "caminando": True}, {"dash": True}):
        hoja = sprites.sprite_jugador(COLOR, rol="periodista", **opciones)
        for apariencia in (None, PREDETERMINADA, Apariencia()):
            assert sprites.sprite_jugador(COLOR, rol="periodista", apariencia=apariencia, **opciones) is hoja


def test_sprite_jugador_vestido_camina_y_hace_dash(recetas):
    armadas = receta_jugador.armar_animaciones(recetas, "influencer", VESTIDO)
    caminar, _ = armadas["caminar"]

    def cuadro(**opciones):
        superficie = sprites.sprite_jugador(COLOR, 2, rol="influencer", apariencia=VESTIDO, **opciones)
        return _leer_surface(superficie, 2)

    assert cuadro() == caminar[0]
    assert cuadro(tiempo=0.16, caminando=True) == caminar[1]  # paso_a
    assert cuadro(tiempo=0.46, caminando=True) == caminar[3]  # paso_b
    assert cuadro(tiempo=0.16) == caminar[0]  # quieto: siempre el primero
    assert cuadro(dash=True) == armadas["dash"][0][0]
    assert caminar[1] != caminar[0] and armadas["dash"][0][0] != caminar[0]


def test_sprite_jugador_vestido_se_arma_una_vez_por_apariencia():
    vestido = sprites.sprite_jugador(COLOR, rol="ciudadano", apariencia=Apariencia(piel=2, traje="candidato"))
    # La Apariencia es la clave de la caché: otra instancia igual da la misma Surface.
    assert sprites.sprite_jugador(COLOR, rol="ciudadano", apariencia=Apariencia(piel=2, traje="candidato")) is vestido
    assert sprites.sprite_jugador(COLOR, rol="ciudadano", apariencia=Apariencia(piel=3, traje="candidato")) is not vestido


def test_sin_recetas_sprite_jugador_cae_a_la_hoja_png(tmp_path, monkeypatch):
    monkeypatch.setattr(assets, "RUTA_RECETAS_SPRITES", str(tmp_path))
    sprites.limpiar_cache_hojas()
    for opciones in ({}, {"tiempo": 0.16, "caminando": True}, {"dash": True}):
        hoja = sprites.sprite_jugador(COLOR, rol="candidato", **opciones)
        assert hoja.get_size() == (ANCHO * assets.ESCALA_PIXEL, ALTO * assets.ESCALA_PIXEL)
        assert sprites.sprite_jugador(COLOR, rol="candidato", apariencia=VESTIDO, **opciones) is hoja
    assert sprites.sprite_parte_jugador(assets.SIMBOLOS_CABEZA, "candidato") is None


def test_si_falta_la_receta_de_la_parte_elegida_cae_a_la_hoja(tmp_path, monkeypatch):
    for rol in ROLES:
        if rol != "ciudadano":
            shutil.copy(os.path.join(CARPETA_RECETAS, f"{rol}.pixel.json"), tmp_path)
    monkeypatch.setattr(assets, "RUTA_RECETAS_SPRITES", str(tmp_path))
    sprites.limpiar_cache_hojas()
    hoja = sprites.sprite_jugador(COLOR, rol="candidato")
    assert sprites.sprite_jugador(COLOR, rol="candidato", apariencia=Apariencia(cabeza="ciudadano")) is hoja
    assert sprites.sprite_jugador(COLOR, rol="candidato", apariencia=Apariencia(cabeza="influencer")) is not hoja


def test_sin_rol_la_apariencia_se_ignora():
    muneco = sprites.sprite_jugador(COLOR, rol=None)
    assert muneco.get_size() == (12 * assets.ESCALA_PIXEL, 16 * assets.ESCALA_PIXEL)  # dibujado en código
    assert sprites.sprite_jugador(COLOR, rol=None, apariencia=VESTIDO) is muneco
    assert sprites.sprite_jugador(COLOR, rol=None, apariencia=VESTIDO, tiempo=0.16, caminando=True) is muneco


def test_sprite_parte_jugador(recetas):
    for rol in ROLES:
        for simbolos in (assets.SIMBOLOS_CABEZA, assets.SIMBOLOS_TRAJE):
            for escala in (1, assets.ESCALA_PIXEL):
                parte = sprites.sprite_parte_jugador(simbolos, rol, escala=escala)
                assert parte.get_size() == (ANCHO * escala, ALTO_PARTE * escala)
            parte = sprites.sprite_parte_jugador(simbolos, rol, escala=1)
            assert _leer_surface(parte, 1) == receta_jugador.armar_parte(recetas, rol, simbolos, None)
    tono = assets.TONOS_PIEL[0]
    original = sprites.sprite_parte_jugador(assets.SIMBOLOS_CABEZA, "ciudadano", escala=1)
    pintada = sprites.sprite_parte_jugador(assets.SIMBOLOS_CABEZA, "ciudadano", tono, escala=1)
    colores_originales = {c for fila in _leer_surface(original, 1) for c in fila}
    colores_pintados = {c for fila in _leer_surface(pintada, 1) for c in fila}
    assert PIEL_CIUDADANO in colores_originales and tono not in colores_originales
    assert tono in colores_pintados and PIEL_CIUDADANO not in colores_pintados
    # Un color como lista o como tupla es la misma vista previa.
    assert sprites.sprite_parte_jugador(assets.SIMBOLOS_CABEZA, "ciudadano", list(tono), escala=1) is pintada
    assert sprites.sprite_parte_jugador(assets.SIMBOLOS_CABEZA, "astronauta") is None


def test_limpiar_cache_hojas_olvida_recetas_vestidos_y_partes():
    vestido = sprites.sprite_jugador(COLOR, rol="candidato", apariencia=VESTIDO)
    parte = sprites.sprite_parte_jugador(assets.SIMBOLOS_TRAJE, "periodista")
    assert sprites._cache_recetas and sprites._cache_vestidos and sprites._cache_partes
    sprites.limpiar_cache_hojas()
    assert not sprites._cache_recetas and not sprites._cache_vestidos and not sprites._cache_partes
    # Se vuelven a armar: otra Surface con los mismos píxeles.
    otro = sprites.sprite_jugador(COLOR, rol="candidato", apariencia=VESTIDO)
    assert otro is not vestido
    assert _leer_surface(otro, assets.ESCALA_PIXEL) == _leer_surface(vestido, assets.ESCALA_PIXEL)
    assert sprites.sprite_parte_jugador(assets.SIMBOLOS_TRAJE, "periodista") is not parte
