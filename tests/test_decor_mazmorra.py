"""Objetos de mazmorra con arte generado: reglas de colocación y archivos.

El planificador (src/ui/plan_decor.py) es puro: se prueba sin pygame que
ningún objeto tape puertas ni el centro donde aparece el jugador, que los
de la franja de los muros no entren al medio y que las coberturas del
centro dejen paso entre ellas. Luego, con SDL dummy, que cada objeto
nombrado en assets.DECORADO_VARIANTE exista y que los fondos de cada tema
y las fachadas de la ciudad se armen.
"""

import os
import random
import sys

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, RAIZ)
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

from src.core import assets  # noqa: E402
from src.core.balance import PASO_MINIMO_COBERTURA  # noqa: E402
from src.dungeon.coberturas import es_solido, hitbox_de  # noqa: E402
from src.ui import plan_decor  # noqa: E402

PISO = (140, 98, 1000, 524)
BANDA = assets.BANDA_DECOR_MAZMORRA
PUERTAS = [(590, 98, 100, 100), (590, 556, 100, 66), (1050, 306, 90, 108), (140, 306, 90, 108)]
CENTRO_APARICION = (538, 257, 204, 186)  # donde aparece el jugador y cae la evidencia


def _tamanos(reglas, lado=(60, 90)):
    rng = random.Random(1)
    return {n: (rng.randint(*lado), rng.randint(*lado)) for _, objetos, _ in reglas for n in objetos}


def _del_centro(reglas):
    return {n for lugar, objetos, _ in reglas if lugar == "centro" for n in objetos}


def _planes():
    libres = PUERTAS + [CENTRO_APARICION]
    for (tema, variante), reglas in assets.DECORADO_VARIANTE.items():
        for semilla in range(8):
            plan = plan_decor.planificar(reglas, _tamanos(reglas), PISO, libres, BANDA, random.Random(semilla),
                                         assets.SEPARACION_PROPS, PASO_MINIMO_COBERTURA)
            yield (tema, variante), reglas, plan


def test_planificador_respeta_piso_puertas_aparicion_y_separacion():
    for clave, reglas, plan in _planes():
        assert plan, clave
        for i, (nombre, rect) in enumerate(plan):
            assert plan_decor.dentro(rect, PISO), nombre
            assert not any(plan_decor.choca(rect, p) for p in PUERTAS), (clave, nombre)
            assert not plan_decor.choca(rect, CENTRO_APARICION), (clave, nombre)
            for _, otro in plan[i + 1:]:
                assert not plan_decor.choca(rect, otro, assets.SEPARACION_PROPS - 1)


def test_solo_las_coberturas_del_centro_entran_al_medio_del_cuarto():
    medio = plan_decor.centro_libre(PISO, BANDA)
    for clave, reglas, plan in _planes():
        del_centro = _del_centro(reglas)
        for nombre, rect in plan:
            if plan_decor.choca(rect, medio):
                assert nombre in del_centro, (clave, nombre)


def test_las_coberturas_del_centro_dejan_paso_y_van_en_pares_espejo():
    """Entre dos bases del centro (y hasta los muros) cabe el enemigo más
    ancho; y cada una tiene su gemela al otro lado del eje del cuarto."""
    medio = plan_decor.centro_libre(PISO, BANDA)
    eje = PISO[0] + PISO[2] // 2
    con_centro = 0
    for clave, reglas, plan in _planes():
        centrales = [(n, r) for n, r in plan if plan_decor.choca(r, medio)]
        con_centro += bool(centrales)
        for i, (nombre, rect) in enumerate(centrales):
            base = hitbox_de(rect)
            x, y, w, h = base
            assert x - PISO[0] >= PASO_MINIMO_COBERTURA and PISO[0] + PISO[2] - (x + w) >= PASO_MINIMO_COBERTURA
            assert y - PISO[1] >= PASO_MINIMO_COBERTURA and PISO[1] + PISO[3] - (y + h) >= PASO_MINIMO_COBERTURA
            for _, otro in centrales[i + 1:]:
                assert not plan_decor.choca(base, hitbox_de(otro), PASO_MINIMO_COBERTURA - 1), clave
            espejo = (2 * eje - rect[0] - rect[2], rect[1], rect[2], rect[3])
            assert (nombre, espejo) in centrales, (clave, nombre)
    assert con_centro >= len(assets.DECORADO_VARIANTE) * 6  # casi todos los cuartos tienen dónde cubrirse


def test_cada_variante_pide_coberturas_en_el_centro_y_son_solidas():
    for clave, reglas in assets.DECORADO_VARIANTE.items():
        del_centro = _del_centro(reglas)
        assert del_centro, clave
        assert all(es_solido(n) for n in del_centro), clave


def test_planificador_sin_imagenes_no_coloca_nada():
    reglas = assets.DECORADO_VARIANTE[("hospital", "sala")]
    assert plan_decor.planificar(reglas, {}, PISO, [], BANDA, random.Random(0)) == []


def test_cantidad_moderada_por_cuarto():
    for reglas in assets.DECORADO_VARIANTE.values():
        assert sum(cantidad if lugar != "costados" else 2 * cantidad for lugar, _, cantidad in reglas) <= 26


def test_cada_objeto_nombrado_existe():
    faltan = []
    for (tema, _), reglas in assets.DECORADO_VARIANTE.items():
        for _, objetos, _ in reglas:
            for nombre in objetos:
                if nombre.startswith("pack:"):
                    assert nombre[5:] in assets.PIEZAS_COLEGIO, nombre
                    continue
                ruta = os.path.join(RAIZ, assets.RUTA_MAZMORRAS, assets.CARPETA_ARTE_TEMA[tema], "props", f"{nombre}.png")
                if not os.path.exists(ruta):
                    faltan.append(ruta)
    for tema in ("hospital", "medios", "servidor"):
        for archivo in ("piso.png", "muro.png"):
            ruta = os.path.join(RAIZ, assets.RUTA_MAZMORRAS, assets.CARPETA_ARTE_TEMA[tema], archivo)
            if not os.path.exists(ruta):
                faltan.append(ruta)
    assert not faltan, faltan


def test_variantes_por_tema_y_cada_una_tiene_reglas():
    for tema, variantes in assets.VARIANTES_CUARTO.items():
        for variante in variantes:
            assert variante == "aula" or (tema, variante) in assets.DECORADO_VARIANTE
    assert len(assets.VARIANTES_CUARTO["hospital"]) >= 3 and len(assets.VARIANTES_CUARTO["medios"]) >= 3


def test_fondos_con_arte_y_focos():
    import pygame
    pygame.init()
    pygame.display.set_mode((1, 1))
    from src.ui import decor_mazmorra, temas_mazmorra
    rect = pygame.Rect(0, 0, assets.ANCHO_CUARTO, assets.ALTO_CUARTO)
    rect.center = assets.CENTRO_CUARTO
    vistos = set()
    for tema in ("colegio", "hospital", "medios", "servidor"):
        assert decor_mazmorra.disponible(tema), tema
        for semilla in range(3):
            fondo = temas_mazmorra.fondo(rect, tema, semilla, ("N", "E", "S", "W"), 40)
            assert fondo.get_width() == 1280 // temas_mazmorra.P * temas_mazmorra.P
            vistos.add(decor_mazmorra.variante(tema, semilla))
            temas_mazmorra.dibujar_animado(pygame.Surface((1280, 720)), rect, tema, 1.5)
    assert {"aula", "biblioteca", "laboratorio", "sala", "urgencias", "estudio", "salon"} <= vistos


def test_fachadas_generadas_miden_su_huella():
    import pygame
    pygame.init()
    pygame.display.set_mode((1, 1))
    from src.core.balance import TAM_CASILLA
    from src.dungeon import ciudad_mapa
    from src.ui import cargador_assets, edificios_ciudad
    for zona, config in assets.ARTE_EDIFICIOS.items():
        if config["fuente"] != "fachada":
            continue
        _, _, ancho, alto = ciudad_mapa.EDIFICIOS[zona]
        assert cargador_assets.fachada_generada(config["ruta"], config["escala"]) is not None, zona
        assert edificios_ciudad.imagen(zona).get_size() == (ancho * TAM_CASILLA, alto * TAM_CASILLA)
