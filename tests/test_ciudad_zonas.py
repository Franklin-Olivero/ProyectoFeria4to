"""Ciudad Nova por zonas (sin pygame): props sin solaparse, huellas de
edificios y casas válidas, casas vecinas distintas, grafo intacto, puertas
alcanzables desde la Plaza, identidad de cada zona, farolas por zona,
agua y el lote reservado del Distrito Liminal."""

import os
import subprocess
import sys

import pytest

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, RAIZ)

from src.core import assets  # noqa: E402
from src.core.balance import METROS_POR_CASILLA, METROS_POR_PUNTO_DE_PESO, PESO_MINIMO_CIUDAD  # noqa: E402
from src.dungeon import agua_ciudad, casas_ciudad, layout_decoracion as ld, zonas_ciudad as zc  # noqa: E402
from src.dungeon import ciudad_mapa as cm  # noqa: E402
from src.dungeon.grafo_ciudad import GrafoCiudad  # noqa: E402

PROPS = cm.DECORACION
HUELLAS_CASAS = [huella for huella, _ in cm.CASAS]


def _celdas(huella):
    col, fila, ancho, alto = huella
    return {(c, f) for c in range(col, col + ancho) for f in range(fila, fila + alto)}


def test_modulos_puros_sin_pygame():
    codigo = ("import sys, src.dungeon.zonas_ciudad, src.dungeon.casas_ciudad, src.dungeon.agua_ciudad, "
              "src.dungeon.ciudad_mapa; print('pygame' in sys.modules)")
    salida = subprocess.run([sys.executable, "-c", codigo], cwd=RAIZ, capture_output=True, text=True, check=True)
    assert salida.stdout.strip() == "False"


# (a) Props: ninguno se superpone con otro, con una puerta ni con un camino.

def test_a_ninguna_huella_de_prop_se_superpone_ni_pisa_puertas_caminos_o_agua():
    vistas = set()
    puertas = set()
    for col, fila in cm.ENTRADAS.values():
        puertas |= {(col + dc, fila + df) for dc in (-1, 0, 1) for df in (0, 1, 2)}
    caminos = set(cm.SENDEROS_PARQUE) | set(cm.NODOS_CALLE.values()) | {cm.SPAWN} | set(zc.ACCESO_LIMINAL)
    for t in cm.TRAMOS:
        caminos |= set(cm.casillas_de_tramo(t.puntos)) | set(t.seccion)
    for prop in PROPS:
        celdas = set(prop.casillas)
        assert not celdas & vistas, prop
        assert not celdas & puertas, prop
        assert not celdas & caminos, prop
        for celda in celdas:
            assert cm.casilla(*celda) in (cm.PASTO, cm.ACERA, cm.ARBOL), prop
        vistas |= celdas


# (b) Huellas de edificios dentro del mapa y sin solapes.

def test_b_huellas_de_edificios_y_casas_dentro_del_mapa_y_sin_solaparse():
    todas = list(cm.EDIFICIOS.values()) + HUELLAS_CASAS
    ocupadas = set()
    for huella in todas:
        col, fila, ancho, alto = huella
        assert 0 < col and 0 < fila and col + ancho < cm.COLUMNAS and fila + alto < cm.FILAS, huella
        celdas = _celdas(huella)
        assert not celdas & ocupadas, huella
        ocupadas |= celdas


def test_b_las_casas_cubren_exactamente_las_h_del_mapa():
    hs = {(c, f) for f, linea in enumerate(cm.MAPA) for c, letra in enumerate(linea) if letra == cm.CASA}
    assert set().union(*(_celdas(h) for h in HUELLAS_CASAS)) == hs


# (c) Ningún par de edificios vecinos idénticos.

def test_c_dos_plantillas_cualesquiera_difieren_lo_suficiente():
    nombres = list(assets.ESTILOS_CASA)
    for i, a in enumerate(nombres):
        for b in nombres[i + 1:]:
            assert casas_ciudad.diferencia(assets.ESTILOS_CASA[a], assets.ESTILOS_CASA[b]) >= \
                assets.VARIACION_MINIMA_ESTILOS, (a, b)


def test_c_casas_vecinas_nunca_comparten_plantilla():
    pares = casas_ciudad.vecinas(HUELLAS_CASAS, distancia=2)
    assert pares  # hay manzanas con casas juntas
    for i, j in pares:
        assert cm.CASAS[i][1] != cm.CASAS[j][1], (cm.CASAS[i], cm.CASAS[j])


def test_c_cada_plantilla_existe_y_sus_ventanas_caben_en_la_fachada():
    for (col, fila, ancho, alto), nombre in cm.CASAS:
        estilo = assets.ESTILOS_CASA[nombre]
        for x, y, w, h in casas_ciudad.ventanas(ancho, alto, estilo["ventanas"], estilo["techo"]) + \
                casas_ciudad.vitrinas(ancho, alto) + [casas_ciudad.puerta(ancho, alto)]:
            assert 0 <= x and 0 <= y and x + w <= ancho * 16 and y + h <= alto * 16, (nombre, (x, y, w, h))


# (d) Grafo conexo y pesos == f(distancia real).

def test_d_grafo_conexo_y_pesos_del_largo_real():
    ciudad = GrafoCiudad()
    assert ciudad.grafo.es_conexo()
    for t in cm.TRAMOS:
        metros = cm.largo_tramo(t) * METROS_POR_CASILLA
        assert ciudad.grafo.peso(t.a, t.b) == max(PESO_MINIMO_CIUDAD, int(metros / METROS_POR_PUNTO_DE_PESO + 0.5))


# (e) Puertas y lugares de la ciudad alcanzables a pie desde la Plaza central.

def test_e_puertas_plaza_civica_y_lote_liminal_se_alcanzan_desde_la_plaza():
    grafo = cm.grafo_casillas(cm.es_solida)
    alcanzables = set(grafo.bfs(cm.NODOS_CALLE[cm.ZONA_PLAZA])[0])
    for puerta in cm.ENTRADAS.values():
        assert puerta in alcanzables, puerta
    col, fila, ancho, alto = cm.PLAZA_CIVICA
    assert (col + ancho // 2, fila + alto - 1) in alcanzables  # frente a la fuente
    assert set(zc.ACCESO_LIMINAL) <= alcanzables
    col, fila, ancho, alto = zc.LIMINAL_RESERVADO
    for celda in _celdas((col + 1, fila, ancho - 2, alto)):  # todo menos las esquinas con conos
        assert celda in alcanzables, celda


def test_e_los_bolsillos_nuevos_no_rodean_barricadas():
    todas = frozenset(c for t in cm.TRAMOS for c in t.seccion) | cm.BARRICADAS_ALCALDIA
    cortado = cm.grafo_casillas(lambda c, f: cm.es_solida(c, f, todas))
    for casilla in cm.NODOS_CALLE.values():
        _, alcanzables, _ = cortado.bfs(casilla)
        assert set(cm.NODOS_CALLE.values()) & set(alcanzables) == {casilla}


# (f) Identidad de cada zona.

def _presentes(id_zona):
    tipos = {p.tipo for p in PROPS if zc.zona_de(*p.base) == id_zona}
    for letra, nombre in ((cm.FUENTE, "fuente"), (cm.AGUA, "estanque")):
        if any(letra == ch and zc.zona_de(c, f) == id_zona for f, linea in enumerate(cm.MAPA) for c, ch in enumerate(linea)):
            tipos.add(nombre)
    return tipos


@pytest.mark.parametrize("id_zona", [z for z in zc.ORDEN_ZONAS if z != zc.LIMINAL])
def test_f_cada_zona_muestra_su_identidad(id_zona):
    zona = zc.ZONAS[id_zona]
    assert len(set(zona.identidad) & _presentes(id_zona)) >= zc.MINIMO_IDENTIDAD, (id_zona, _presentes(id_zona))


def test_f_la_identidad_de_cada_zona_es_propia_y_tiene_su_especie_de_arbol():
    vistos = {}
    for id_zona, zona in zc.ZONAS.items():
        for tipo in zona.identidad:
            assert tipo not in vistos, (tipo, id_zona, vistos.get(tipo))
            vistos[tipo] = id_zona
    especies = [frozenset(z.arboles) for i, z in zc.ZONAS.items() if z.arboles and i != zc.PLAZA]
    assert len(set(especies)) == len(especies)  # ninguna zona copia las especies de otra
    for id_zona, zona in zc.ZONAS.items():
        arboles = [p for p in PROPS if p.tipo == "arbol" and zc.zona_de(*p.casilla) == id_zona
                   and cm.casilla(*p.casilla) == cm.PASTO]
        if zona.arboles and arboles:
            assert any(p.variante in zona.arboles for p in arboles), id_zona


# (g) Farolas por zona a intervalo constante; bancas simétricas.

def test_g_cada_farola_es_el_modelo_de_su_zona():
    farolas = [p for p in PROPS if p.tipo in ld.FAROLAS]
    assert len({p.tipo for p in farolas}) >= 4  # variación de modelo entre zonas
    for p in farolas:
        hito = any(p.casilla == h.casilla for z in zc.ZONAS.values() for h in z.hitos)
        assert hito or p.tipo == zc.farola_de(*p.casilla), p


def test_g_bancas_de_la_plaza_civica_enfrentadas_y_simetricas():
    col, fila, ancho, alto = cm.PLAZA_CIVICA
    eje = col + ancho // 2
    bancas = [p for p in PROPS if p.tipo == "banca" and ld._dentro(cm.PLAZA_CIVICA, p.casilla)]
    assert len(bancas) == 2
    a, b = sorted(bancas, key=lambda p: p.casilla)
    assert a.casilla[1] == b.casilla[1] and a.casilla[0] + b.casilla[0] == 2 * eje
    assert (a.orientacion, b.orientacion) == ("E", "O")


# Agua y lote reservado.

def test_agua_por_auto_tiling_con_tiles_del_atlas():
    terrenos = agua_ciudad.cargar_terrenos(RAIZ)
    capas = dict(agua_ciudad.capas(cm.MAPA, terrenos))
    fuente = {(c, f) for f, linea in enumerate(cm.MAPA) for c, ch in enumerate(linea) if ch == cm.FUENTE}
    assert {(c, f) for f, fila in enumerate(capas["borde_fuente"]) for c, t in enumerate(fila) if t >= 0} == fuente
    assert any(t >= 0 for fila in capas["agua_fuente"] for t in fila)
    assert any(t >= 0 for fila in capas["estanque"] for t in fila)
    from src.ui import rutas_backrooms
    atlas = rutas_backrooms.leer_atlas(assets.GRADE_CIUDAD, os.path.join(RAIZ, assets.RUTA_BACKROOMS))
    for id_tile in agua_ciudad.tiles_usados(list(capas.items()), terrenos):
        assert str(id_tile) in atlas["tiles"], id_tile


def test_lote_liminal_vacio_conectado_y_con_espacio_para_aristas_nuevas():
    col, fila, ancho, alto = zc.LIMINAL_RESERVADO
    assert ancho >= 6 and alto >= 4
    interior = _celdas((col + 1, fila + 1, ancho - 2, alto - 2))
    assert not any(set(p.casillas) & interior for p in PROPS)  # sin construir
    assert all(not cm.es_solida(c, f) for c, f in interior)
    sur = cm.NODOS_CALLE["Cruce Sur"] if "Cruce Sur" in cm.NODOS_CALLE else None
    if sur is not None:
        assert min(abs(sur[0] - c) for c, _ in zc.ACCESO_LIMINAL) <= 1
