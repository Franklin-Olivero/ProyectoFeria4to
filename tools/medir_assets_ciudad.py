"""Mide cuánto de Ciudad Nova sale de los packs nuevos y cuánto cambió el plano.

    python tools/medir_assets_ciudad.py
    python tools/medir_assets_ciudad.py --referencia <commit>   # plano con el que comparar

Casillas: cada casilla de la panorámica se cuenta según quién la dibuja:
la casa o el edificio que la cubre (armados con los packs o en pixel art /
pack escolar) o, si no, su suelo (tiles_ciudad.origen: los packs cyberpunk
o el pixel art en código). Props: decoracion_ciudad.origen de cada uno
(máquinas y torre de los packs nuevos vs farolas, bancas, árboles y
Backrooms). También lista las piezas del atlas que nadie usa y el % de
casillas cuya categoría (calle, paso, pasto, construido, barrera, agua)
cambió respecto del plano de `--referencia` (por defecto, el último commit
con el plano anterior).
"""

import argparse
import ast
import json
import os
import subprocess
import sys

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, RAIZ)
os.chdir(RAIZ)
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame  # noqa: E402

REFERENCIA = "42a1369"  # "Rehacer los exteriores de Ciudad Nova por zonas": el plano anterior
CATEGORIAS = {
    **{k: "calle" for k in "c=|"}, **{k: "paso" for k in ":EX"}, ".": "pasto",
    **{k: "construido" for k in "#H"}, **{k: "barrera" for k in "TWJk"}, **{k: "agua" for k in "~F"},
}


def _dentro(rect, col, fila):
    c, f, ancho, alto = rect
    return c <= col < c + ancho and f <= fila < f + alto


def medir_casillas():
    from src.dungeon import ciudad_mapa
    from src.ui import casas_render, edificios_ciudad, tiles_ciudad

    conteo = {"nuevo": 0, "antiguo": 0}
    for fila in range(ciudad_mapa.FILAS):
        for col in range(ciudad_mapa.COLUMNAS):
            origen = None
            for indice, (huella, _) in enumerate(ciudad_mapa.CASAS):
                if _dentro(huella, col, fila):
                    origen = "nuevo" if casas_render.compuesta(indice) else "antiguo"
            for zona, huella in ciudad_mapa.EDIFICIOS.items():
                if _dentro(huella, col, fila):
                    origen = "nuevo" if edificios_ciudad.compuesto(zona) else "antiguo"
            conteo[origen or tiles_ciudad.origen(col, fila)] += 1
    return conteo


def medir_props():
    from src.ui import decoracion_ciudad

    conteo = {"nuevo": 0, "antiguo": 0}
    for prop in decoracion_ciudad.todos():
        conteo[decoracion_ciudad.origen(prop)] += 1
    return conteo


def piezas_sin_uso():
    from src.core import assets

    with open(assets.RUTA_ATLAS_CIUDAD_JSON, encoding="utf-8") as archivo:
        piezas = set(json.load(archivo)["piezas"])
    usadas = set()
    for valor in vars(assets).values():
        for texto in (valor if isinstance(valor, (tuple, list)) else (valor,)):
            if isinstance(texto, str):
                usadas.add(texto)
    for mapa in (assets.TEXTURA_TERRENO_CIUDAD, assets.PROPS_CIUDAD):
        for valor in mapa.values():
            usadas |= set(valor) if isinstance(valor, tuple) else {valor}
    for estilo in assets.ESTILOS_CASA.values():
        usadas |= {estilo["techo_pack"], estilo["fachada_pack"]}
    for config in assets.ARTE_EDIFICIOS.values():
        usadas |= {v for v in config.values() if isinstance(v, str)}
    usadas.add("puerta_vidrio")  # puerta de las casas (casas_render)
    return sorted(piezas - usadas)


def cambio_de_plano(referencia):
    from src.dungeon import ciudad_mapa

    try:
        fuente = subprocess.run(["git", "show", f"{referencia}:src/dungeon/ciudad_mapa.py"], capture_output=True,
                                text=True, encoding="utf-8", check=True).stdout
    except (OSError, subprocess.CalledProcessError):
        return None
    inicio = fuente.index("MAPA = [")
    anterior = ast.literal_eval(fuente[inicio + len("MAPA = "):fuente.index("]", inicio) + 1])
    total = cambiadas = 0
    for viejo, nuevo in zip(anterior, ciudad_mapa.MAPA):
        for a, b in zip(viejo, nuevo):
            total += 1
            cambiadas += CATEGORIAS.get(a) != CATEGORIAS.get(b)
    return cambiadas, total


def _porcentaje(conteo):
    total = conteo["nuevo"] + conteo["antiguo"]
    return 100 * conteo["nuevo"] / total if total else 0.0


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--referencia", default=REFERENCIA)
    args = parser.parse_args()
    pygame.init()
    pygame.display.set_mode((1280, 720))
    casillas, props = medir_casillas(), medir_props()
    total = {k: casillas[k] + props[k] for k in casillas}
    print(f"Casillas de la panorámica: {casillas['nuevo']} nuevas / {casillas['antiguo']} antiguas"
          f" = {_porcentaje(casillas):.1f} % de packs nuevos")
    print(f"Props:                     {props['nuevo']} nuevos / {props['antiguo']} antiguos"
          f" = {_porcentaje(props):.1f} % de packs nuevos")
    print(f"Total (casillas + props):  {_porcentaje(total):.1f} % de packs nuevos")
    sin_uso = piezas_sin_uso()
    print("Piezas del atlas sin usar:", ", ".join(sin_uso) if sin_uso else "ninguna")
    cambio = cambio_de_plano(args.referencia)
    if cambio is None:
        print(f"No se pudo leer el plano de {args.referencia} (¿sin git?)")
    else:
        cambiadas, todas = cambio
        print(f"Casillas cuya categoría cambió respecto de {args.referencia}: {cambiadas}/{todas}"
              f" = {100 * cambiadas / todas:.1f} %")


if __name__ == "__main__":
    main()
