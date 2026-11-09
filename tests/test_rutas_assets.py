"""Rutas de assets declaradas en src/core/assets.py y salud de assets/.

Sin pygame: solo comprueba que cada archivo al que apunta assets.py exista
(si se mueve un archivo sin repuntar su ruta, el juego caería en silencio
al placeholder y nadie lo notaría) y que el repo no cargue zips ni
archivos de más de 5 MB (los packs completos viven en _packs/, fuera de git).
"""

import os
import re
import shutil
import subprocess
import sys

import pytest

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, RAIZ)

from src.core import assets  # noqa: E402

MAX_BYTES_ARCHIVO = 5 * 1024 * 1024
ROLES = ("ciudadano", "influencer", "periodista", "candidato")


def _existe(ruta):
    return os.path.exists(os.path.join(RAIZ, ruta))


def _rutas_declaradas():
    """(id, ruta) de todo archivo o carpeta que assets.py promete."""
    rutas = []
    for nombre in dir(assets):
        valor = getattr(assets, nombre)
        if nombre.startswith("RUTA_") and isinstance(valor, str) and valor.startswith("assets"):
            rutas.append((nombre, valor))
    rutas += [(f"SONIDOS[{i}]", ruta) for i, (ruta, _) in assets.SONIDOS.items()]
    rutas += [(f"MUSICA[{i}]", ruta) for i, ruta in assets.MUSICA.items()]
    for nombre, arte in assets.ARTE_VARIANTE.items():
        for tira in (arte["tira_mov"], arte["tira_ataque"]):
            rutas.append((f"variante {nombre} {tira}", assets.ruta_tira_variante(nombre, tira)))
    if assets.JEFE_V2:
        for tira in ("Idle", "Walk"):
            rutas.append((f"jefe {tira}", assets.ruta_tira_variante(assets.JEFE_V2, tira)))
    for pieza, (archivo, _) in assets.PIEZAS_COLEGIO.items():
        rutas.append((f"colegio {pieza}", os.path.join(assets.RUTA_COLEGIO, archivo)))
    hojas = [(assets.RUTA_SPRITES_JUGADORES, rol) for rol in ROLES]
    hojas += [(assets.RUTA_SPRITES_ENEMIGOS, id_) for id_ in assets.ID_SPRITE_ENEMIGO.values()]
    hojas += [(assets.RUTA_SPRITES_JEFE, assets.ID_SPRITE_JEFE)]
    hojas += [(assets.RUTA_SPRITES_CUARTO, id_) for id_ in
              (assets.ID_SPRITE_CUARTO, assets.ID_SPRITE_PUERTA, assets.ID_SPRITE_CHARCO)]
    for carpeta, id_ in hojas:
        rutas.append((f"hoja {id_}", os.path.join(carpeta, f"{id_}.png")))
        rutas.append((f"atlas {id_}", os.path.join(carpeta, f"{id_}.atlas.json")))
    rutas += [(f"retrato {rol}", os.path.join(assets.RUTA_SPRITES_RETRATOS, f"{rol}.png")) for rol in ROLES]
    rutas += [(f"receta {rol}", os.path.join(assets.RUTA_RECETAS_SPRITES, f"{rol}.pixel.json"))
              for rol in assets.ROLES_APARIENCIA]
    for numero, _, _ in assets.ARBOLES_LOBBY:
        rutas.append((f"arbol {numero}", os.path.join(assets.RUTA_ARBOLES, f"arbol_{numero:02d}.png")))
    fondos = {v for n, v in vars(assets).items() if n.startswith("FONDO_") and isinstance(v, str)}
    fondos |= set(assets.FONDO_POR_ZONA.values()) | set(assets.FONDO_POR_FINAL.values())
    rutas += [(f"fondo {f}", os.path.join(assets.RUTA_FONDOS_HISTORIA, f"{f}.png")) for f in sorted(fondos)]
    return rutas


@pytest.mark.parametrize("id_, ruta", _rutas_declaradas())
def test_cada_ruta_declarada_existe(id_, ruta):
    assert _existe(ruta), f"{id_}: falta {ruta}"


def _rastreados():
    if shutil.which("git") is None or not os.path.isdir(os.path.join(RAIZ, ".git")):
        pytest.skip("sin git")
    salida = subprocess.run(["git", "ls-files", "-z"], cwd=RAIZ, capture_output=True, check=True).stdout
    return [r for r in salida.decode("utf-8").split("\0") if r]


def test_no_hay_zips_rastreados():
    assert [r for r in _rastreados() if r.lower().endswith(".zip")] == []


def test_ningun_archivo_rastreado_pesa_mas_de_5_mb():
    grandes = []
    for r in _rastreados():
        ruta = os.path.join(RAIZ, r)
        if os.path.isfile(ruta) and os.path.getsize(ruta) > MAX_BYTES_ARCHIVO:
            grandes.append((r, os.path.getsize(ruta)))
    assert grandes == []


def test_nombres_de_assets_en_minusculas_sin_espacios_ni_simbolos():
    valido = re.compile(r"^[a-z0-9_./]+$")
    malos = [r for r in _rastreados() if r.startswith("assets/") and not valido.match(r)]
    assert malos == []
