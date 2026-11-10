"""Mide cuánto de Ciudad Nova sale de los packs nuevos y cuánto cambió el plano.

    python tools/medir_assets_ciudad.py
    python tools/medir_assets_ciudad.py --referencia <commit>   # plano con el que comparar

Casillas: cada casilla de la panorámica se cuenta según quién la dibuja:
la casa o el edificio que la cubre (sprites completos antiguos: pixel art
y pack escolar) o, si no, su suelo (tiles_ciudad.origen: la calzada y las
banquetas de los packs cyberpunk o el pasto en pixel art). Props:
decoracion_ciudad.origen (todos del arte antiguo: pack urbano, árboles,
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
    from src.ui import tiles_ciudad

    conteo = {"nuevo": 0, "antiguo": 0}
    for fila in range(ciudad_mapa.FILAS):
        for col in range(ciudad_mapa.COLUMNAS):
            origen = None
            huellas = [h for h, _ in ciudad_mapa.CASAS] + list(ciudad_mapa.EDIFICIOS.values())
            if any(_dentro(huella, col, fila) for huella in huellas):
                origen = "antiguo"  # sprites completos: los packs nuevos no traen edificios
            conteo[origen or tiles_ciudad.origen(col, fila)] += 1
    return conteo


def medir_props():
    from src.ui import decoracion_ciudad

    conteo = {"nuevo": 0, "antiguo": 0}
    for prop in decoracion_ciudad.todos():
        conteo[decoracion_ciudad.origen(prop)] += 1
    return conteo


def piezas_sin_uso():
    """Piezas del atlas que el render de la ciudad no pidió (render panorámico)."""
    from src.core import assets
    from src.dungeon.partida import Partida
    from src.ui import arte_ciudad, ciudad_render

    with open(assets.RUTA_ATLAS_CIUDAD_JSON, encoding="utf-8") as archivo:
        piezas = set(json.load(archivo)["piezas"])
    ciudad_render.render_panoramico(Partida())
    usadas = {id_arte.split(":", 1)[1] for id_arte in arte_ciudad.pedidos if id_arte.startswith("ciudad:")}
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
    print(f"Total (casillas + props):  {_porcentaje(total):.1f} % de packs nuevos"
          " (de los packs nuevos solo se usa la calzada, la banqueta y el agua: lo demás es a propósito)")
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
