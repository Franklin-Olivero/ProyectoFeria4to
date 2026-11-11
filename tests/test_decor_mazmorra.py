"""Decoración de mazmorra con arte generado: reglas de colocación y archivos.

El planificador (src/ui/plan_decor.py) es puro: se prueba sin pygame que
la decoración nunca tape puertas ni el centro de combate. Luego, con SDL
dummy, que cada objeto nombrado en assets.DECORADO_VARIANTE exista y que
los fondos de cada tema y las fachadas de la ciudad se armen.
"""

import os
import random
import sys

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, RAIZ)
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

from src.core import assets  # noqa: E402
from src.ui import plan_decor  # noqa: E402

PISO = (140, 98, 1000, 524)
BANDA = assets.BANDA_DECOR_MAZMORRA


def _tamanos(reglas, lado=(60, 90)):
    rng = random.Random(1)
    return {n: (rng.randint(*lado), rng.randint(*lado)) for _, objetos, _ in reglas for n in objetos}


def test_planificador_respeta_piso_centro_puertas_y_separacion():
    puertas = [(590, 98, 100, 100), (590, 556, 100, 66), (1050, 306, 90, 108), (140, 306, 90, 108)]
    for (tema, variante), reglas in assets.DECORADO_VARIANTE.items():
        for semilla in range(8):
            plan = plan_decor.planificar(reglas, _tamanos(reglas), PISO, puertas, BANDA,
                                         random.Random(semilla), assets.SEPARACION_PROPS)
            assert plan, (tema, variante)
            centro = plan_decor.centro_libre(PISO, BANDA)
            for i, (nombre, rect) in enumerate(plan):
                assert plan_decor.dentro(rect, PISO), nombre
                assert not plan_decor.choca(rect, centro), (tema, variante, nombre)
                assert not any(plan_decor.choca(rect, p) for p in puertas), nombre
                for _, otro in plan[i + 1:]:
                    assert not plan_decor.choca(rect, otro, assets.SEPARACION_PROPS - 1)


def test_planificador_sin_imagenes_no_coloca_nada():
    reglas = assets.DECORADO_VARIANTE[("hospital", "sala")]
    assert plan_decor.planificar(reglas, {}, PISO, [], BANDA, random.Random(0)) == []


def test_cantidad_moderada_por_cuarto():
    for reglas in assets.DECORADO_VARIANTE.values():
        assert sum(cantidad if lugar != "costados" else 2 * cantidad for lugar, _, cantidad in reglas) <= 22


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
