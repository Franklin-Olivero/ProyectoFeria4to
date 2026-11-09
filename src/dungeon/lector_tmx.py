"""Lector de mapas y tilesets de Tiled (.tmx / .tsx), puro (sin Pygame).

Solo lo usa el conversor tools/convertir_tmx.py: en runtime el juego lee
las plantillas JSON propias (src/dungeon/datos/plantillas/), nunca los
.tmx originales del pack.

    leer_tmx(ruta) / leer_tmx_texto(xml)  -> MapaTmx
    leer_tsx(ruta) / leer_tsx_texto(xml)  -> TilesetTmx
    separar_gid(gid)                       -> (gid limpio, volteo_h, volteo_v, volteo_d)
    tileset_de_gid(mapa, gid)              -> (RefTileset, id local) o None

Capas de tiles en CSV, base64 (sin comprimir, zlib o gzip) o XML <tile>.
Objetos con sus propiedades. En los objetos-tile de Tiled, (x, y) es la
esquina inferior izquierda: `y` es donde el objeto toca el suelo.
"""

import base64
import gzip
import os
import struct
import xml.etree.ElementTree as ET
import zlib
from dataclasses import dataclass, field

# Bits altos del gid: volteos y rotación (Tiled los guarda en el mismo entero).
VOLTEO_H = 0x80000000
VOLTEO_V = 0x40000000
VOLTEO_D = 0x20000000
ROTACION_HEX = 0x10000000
MASCARA_GID = ~(VOLTEO_H | VOLTEO_V | VOLTEO_D | ROTACION_HEX) & 0xFFFFFFFF


@dataclass
class RefTileset:
    firstgid: int
    source: str  # ruta del .tsx relativa al .tmx ("" si va incrustado)
    incrustado: "TilesetTmx | None" = None


@dataclass
class CapaTiles:
    nombre: str
    ancho: int
    alto: int
    datos: list  # gids en orden fila por fila (0 = vacío)
    propiedades: dict = field(default_factory=dict)

    def gid(self, columna, fila):
        return self.datos[fila * self.ancho + columna]


@dataclass
class ObjetoTmx:
    id: int
    nombre: str
    tipo: str
    x: float
    y: float
    ancho: float
    alto: float
    gid: int = 0  # 0 = no es objeto-tile (rectángulo, punto...)
    propiedades: dict = field(default_factory=dict)


@dataclass
class GrupoObjetos:
    nombre: str
    objetos: list
    propiedades: dict = field(default_factory=dict)


@dataclass
class MapaTmx:
    ancho: int  # en tiles
    alto: int
    ancho_tile: int
    alto_tile: int
    tilesets: list  # [RefTileset] ordenados por firstgid
    capas: list  # [CapaTiles | GrupoObjetos] en el orden del archivo (de abajo hacia arriba)
    propiedades: dict = field(default_factory=dict)

    def capa(self, nombre):
        return next((c for c in self.capas if c.nombre == nombre), None)

    @property
    def capas_tiles(self):
        return [c for c in self.capas if isinstance(c, CapaTiles)]

    @property
    def grupos(self):
        return [c for c in self.capas if isinstance(c, GrupoObjetos)]


@dataclass
class TileTmx:
    id: int
    propiedades: dict = field(default_factory=dict)
    imagen: str = ""  # tilesets de colección: imagen propia de cada tile
    ancho: int = 0
    alto: int = 0
    animacion: list = field(default_factory=list)  # [(id local, ms)]


@dataclass
class TilesetTmx:
    nombre: str
    ancho_tile: int
    alto_tile: int
    cantidad: int
    columnas: int  # 0 = colección de imágenes
    imagen: str = ""  # tilesets de una sola imagen
    tiles: dict = field(default_factory=dict)  # id local -> TileTmx (solo los que traen datos)


def separar_gid(gid):
    """(gid sin banderas, volteo horizontal, vertical, diagonal)."""
    return gid & MASCARA_GID, bool(gid & VOLTEO_H), bool(gid & VOLTEO_V), bool(gid & VOLTEO_D)


def tileset_de_gid(mapa, gid):
    """(RefTileset, id local) del tileset al que pertenece `gid`, o None si es 0."""
    limpio = separar_gid(gid)[0]
    if limpio == 0:
        return None
    elegido = None
    for ref in mapa.tilesets:
        if ref.firstgid <= limpio:
            elegido = ref
    if elegido is None:
        return None
    return elegido, limpio - elegido.firstgid


def _valor(tipo, texto):
    if tipo == "int" or tipo == "object":
        return int(texto)
    if tipo == "float":
        return float(texto)
    if tipo == "bool":
        return texto == "true"
    return texto


def _propiedades(nodo):
    contenedor = nodo.find("properties")
    if contenedor is None:
        return {}
    salida = {}
    for prop in contenedor.findall("property"):
        texto = prop.get("value")
        if texto is None:
            texto = prop.text or ""
        salida[prop.get("name")] = _valor(prop.get("type", "string"), texto)
    return salida


def _decodificar_datos(nodo, cantidad):
    codificacion = nodo.get("encoding")
    compresion = nodo.get("compression")
    if codificacion == "csv":
        datos = [int(v) for v in (nodo.text or "").replace("\n", "").split(",") if v.strip()]
    elif codificacion == "base64":
        crudo = base64.b64decode((nodo.text or "").strip())
        if compresion == "zlib":
            crudo = zlib.decompress(crudo)
        elif compresion == "gzip":
            crudo = gzip.decompress(crudo)
        elif compresion:
            raise ValueError(f"compresión no soportada: {compresion}")
        datos = list(struct.unpack(f"<{len(crudo) // 4}I", crudo))
    elif codificacion is None:
        datos = [int(t.get("gid", 0)) for t in nodo.findall("tile")]
    else:
        raise ValueError(f"codificación no soportada: {codificacion}")
    if len(datos) != cantidad:
        raise ValueError(f"la capa trae {len(datos)} tiles y debía traer {cantidad}")
    return datos


def _leer_tileset(raiz):
    tileset = TilesetTmx(
        nombre=raiz.get("name", ""),
        ancho_tile=int(raiz.get("tilewidth", 0)),
        alto_tile=int(raiz.get("tileheight", 0)),
        cantidad=int(raiz.get("tilecount", 0)),
        columnas=int(raiz.get("columns", 0)),
    )
    imagen = raiz.find("image")
    if imagen is not None:
        tileset.imagen = imagen.get("source", "")
    for nodo in raiz.findall("tile"):
        tile = TileTmx(id=int(nodo.get("id")), propiedades=_propiedades(nodo))
        img = nodo.find("image")
        if img is not None:
            tile.imagen = img.get("source", "")
            tile.ancho = int(img.get("width", 0))
            tile.alto = int(img.get("height", 0))
        anim = nodo.find("animation")
        if anim is not None:
            tile.animacion = [(int(f.get("tileid")), int(f.get("duration"))) for f in anim.findall("frame")]
        tileset.tiles[tile.id] = tile
    return tileset


def leer_tsx_texto(xml):
    return _leer_tileset(ET.fromstring(xml))


def leer_tsx(ruta):
    return _leer_tileset(ET.parse(ruta).getroot())


def leer_tmx_texto(xml):
    raiz = ET.fromstring(xml)
    if raiz.get("infinite", "0") == "1":
        raise ValueError("los mapas infinitos (por trozos) no están soportados")
    mapa = MapaTmx(
        ancho=int(raiz.get("width")),
        alto=int(raiz.get("height")),
        ancho_tile=int(raiz.get("tilewidth")),
        alto_tile=int(raiz.get("tileheight")),
        tilesets=[],
        capas=[],
        propiedades=_propiedades(raiz),
    )
    for nodo in raiz:
        if nodo.tag == "tileset":
            ref = RefTileset(int(nodo.get("firstgid")), nodo.get("source", ""))
            if not ref.source:
                ref.incrustado = _leer_tileset(nodo)
            mapa.tilesets.append(ref)
        elif nodo.tag == "layer":
            ancho, alto = int(nodo.get("width")), int(nodo.get("height"))
            datos = _decodificar_datos(nodo.find("data"), ancho * alto)
            mapa.capas.append(CapaTiles(nodo.get("name", ""), ancho, alto, datos, _propiedades(nodo)))
        elif nodo.tag == "objectgroup":
            objetos = []
            for obj in nodo.findall("object"):
                objetos.append(ObjetoTmx(
                    id=int(obj.get("id", 0)),
                    nombre=obj.get("name", ""),
                    tipo=obj.get("type", obj.get("class", "")),
                    x=float(obj.get("x", 0)),
                    y=float(obj.get("y", 0)),
                    ancho=float(obj.get("width", 0)),
                    alto=float(obj.get("height", 0)),
                    gid=int(obj.get("gid", 0)),
                    propiedades=_propiedades(obj),
                ))
            mapa.capas.append(GrupoObjetos(nodo.get("name", ""), objetos, _propiedades(nodo)))
    mapa.tilesets.sort(key=lambda r: r.firstgid)
    return mapa


def leer_tmx(ruta):
    with open(ruta, encoding="utf-8") as archivo:
        return leer_tmx_texto(archivo.read())


def ruta_tileset(ruta_tmx, ref):
    """Ruta en disco del .tsx de `ref`, resuelta respecto del .tmx."""
    return os.path.normpath(os.path.join(os.path.dirname(ruta_tmx), ref.source))
