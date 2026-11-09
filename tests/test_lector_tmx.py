"""Lector de Tiled (src/dungeon/lector_tmx.py) con mapas sintéticos mínimos, sin pygame."""

import base64
import os
import struct
import sys
import zlib

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.dungeon import lector_tmx  # noqa: E402

MAPA_CSV = """<?xml version="1.0" encoding="UTF-8"?>
<map version="1.10" orientation="orthogonal" width="3" height="2" tilewidth="16" tileheight="16" infinite="0">
 <properties><property name="zona" value="hotel"/><property name="nivel" type="int" value="3"/></properties>
 <tileset firstgid="1" source="../hum/tiled/tiles.tsx"/>
 <tileset firstgid="100" source="../hum/tiled/props.tsx"/>
 <layer id="1" name="piso" width="3" height="2">
  <data encoding="csv">
1,2,0,
0,3,2147483652
</data>
 </layer>
 <objectgroup id="2" name="objetos">
  <object id="7" name="sofa" gid="105" x="32" y="48" width="42" height="24">
   <properties><property name="solido" type="bool" value="true"/></properties>
  </object>
  <object id="8" name="zona_spawn" type="spawn" x="10" y="12" width="20" height="20"/>
 </objectgroup>
</map>
"""


def _mapa_base64(compresion):
    crudo = struct.pack("<4I", 1, 0, 0, 7)
    if compresion == "zlib":
        crudo = zlib.compress(crudo)
    atributo = f' compression="{compresion}"' if compresion else ""
    datos = base64.b64encode(crudo).decode()
    return f"""<map width="2" height="2" tilewidth="16" tileheight="16">
 <tileset firstgid="1" source="t.tsx"/>
 <layer name="capa" width="2" height="2"><data encoding="base64"{atributo}>{datos}</data></layer>
</map>"""


def test_lee_tamanio_tilesets_y_propiedades_del_mapa():
    mapa = lector_tmx.leer_tmx_texto(MAPA_CSV)
    assert (mapa.ancho, mapa.alto, mapa.ancho_tile, mapa.alto_tile) == (3, 2, 16, 16)
    assert [(t.firstgid, t.source) for t in mapa.tilesets] == [(1, "../hum/tiled/tiles.tsx"), (100, "../hum/tiled/props.tsx")]
    assert mapa.propiedades == {"zona": "hotel", "nivel": 3}


def test_capa_csv_en_orden_de_filas():
    capa = lector_tmx.leer_tmx_texto(MAPA_CSV).capa("piso")
    assert capa.datos[:5] == [1, 2, 0, 0, 3]
    assert capa.gid(1, 1) == 3


def test_gid_con_volteo_se_separa_en_gid_y_banderas():
    capa = lector_tmx.leer_tmx_texto(MAPA_CSV).capa("piso")
    assert lector_tmx.separar_gid(capa.gid(2, 1)) == (4, True, False, False)


def test_objetos_con_gid_tipo_y_propiedades():
    grupo = lector_tmx.leer_tmx_texto(MAPA_CSV).capa("objetos")
    sofa, spawn = grupo.objetos
    assert (sofa.nombre, sofa.gid, sofa.x, sofa.y, sofa.ancho, sofa.alto) == ("sofa", 105, 32, 48, 42, 24)
    assert sofa.propiedades == {"solido": True}
    assert (spawn.tipo, spawn.gid) == ("spawn", 0)


def test_tileset_de_gid_elige_el_firstgid_mas_alto_que_no_lo_pasa():
    mapa = lector_tmx.leer_tmx_texto(MAPA_CSV)
    ref, local = lector_tmx.tileset_de_gid(mapa, 105)
    assert (ref.firstgid, local) == (100, 5)
    ref, local = lector_tmx.tileset_de_gid(mapa, 2147483652)  # 4 volteado
    assert (ref.firstgid, local) == (1, 3)
    assert lector_tmx.tileset_de_gid(mapa, 0) is None


@pytest.mark.parametrize("compresion", [None, "zlib"])
def test_capas_base64_con_y_sin_zlib(compresion):
    capa = lector_tmx.leer_tmx_texto(_mapa_base64(compresion)).capa("capa")
    assert capa.datos == [1, 0, 0, 7]


def test_capa_con_cantidad_equivocada_falla():
    roto = MAPA_CSV.replace("0,3,2147483652", "0,3")
    with pytest.raises(ValueError):
        lector_tmx.leer_tmx_texto(roto)


def test_mapa_infinito_no_soportado():
    with pytest.raises(ValueError):
        lector_tmx.leer_tmx_texto('<map infinite="1" width="1" height="1" tilewidth="16" tileheight="16"/>')


def test_tsx_de_coleccion_con_nombres_y_animacion():
    tsx = """<tileset name="props" tilewidth="64" tileheight="64" tilecount="2" columns="0">
     <tile id="0"><properties><property name="name" value="hotel_sofa"/></properties>
      <image source="../props/hotel/hotel_sofa.png" width="42" height="24"/></tile>
     <tile id="1"><image source="a.png" width="8" height="8"/>
      <animation><frame tileid="1" duration="83"/><frame tileid="0" duration="120"/></animation></tile>
    </tileset>"""
    tileset = lector_tmx.leer_tsx_texto(tsx)
    assert tileset.columnas == 0 and tileset.cantidad == 2
    assert tileset.tiles[0].propiedades["name"] == "hotel_sofa"
    assert (tileset.tiles[0].ancho, tileset.tiles[0].alto) == (42, 24)
    assert tileset.tiles[1].animacion == [(1, 83), (0, 120)]
