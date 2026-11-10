"""Ciudad Nova por zonas (sin pygame): props sin solaparse, huellas de
edificios válidas, edificios vecinos distintos, grafo intacto, puertas
alcanzables desde la Plaza, identidad de cada zona, farolas por zona,
área verde, cero solapes y el lote reservado del Distrito Liminal."""

import os
import subprocess
import sys

import pytest

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, RAIZ)

from src.core import assets  # noqa: E402
from src.core.balance import (  # noqa: E402
    METROS_POR_CASILLA,
    METROS_POR_PUNTO_DE_PESO,
    MIN_FRACCION_VERDE_CIUDAD,
    PESO_MINIMO_CIUDAD,
)
from src.dungeon import casas_ciudad, huellas_ciudad as hc, layout_decoracion as ld, zonas_ciudad as zc  # noqa: E402
from src.dungeon import ciudad_mapa as cm  # noqa: E402
from src.dungeon.grafo_ciudad import GrafoCiudad  # noqa: E402

PROPS = cm.DECORACION
HUELLAS_CASAS = [huella for huella, _ in cm.CASAS]


def _celdas(huella):
    col, fila, ancho, alto = huella
    return {(c, f) for c in range(col, col + ancho) for f in range(fila, fila + alto)}


def _con_letra(letra):
    return {(c, f) for f, linea in enumerate(cm.MAPA) for c, ch in enumerate(linea) if ch == letra}


def test_modulos_puros_sin_pygame():
    codigo = ("import sys, src.dungeon.zonas_ciudad, src.dungeon.casas_ciudad, src.dungeon.autotile_ciudad, "
              "src.dungeon.huellas_ciudad, src.core.medicion_paleta, src.dungeon.ciudad_mapa; "
              "print('pygame' in sys.modules)")
    salida = subprocess.run([sys.executable, "-c", codigo], cwd=RAIZ, capture_output=True, text=True, check=True)
    assert salida.stdout.strip() == "False"


# (a) Props: ninguno se superpone con otro, con una puerta ni con un camino.

def test_a_ninguna_huella_de_prop_se_superpone_ni_pisa_puertas_caminos_o_agua():
    vistas = set()
    puertas = set()
    for col, fila in cm.ENTRADAS.values():
        puertas |= {(col + dc, fila + df) for dc in (-1, 0, 1) for df in (0, 1, 2)}
    caminos = set(cm.SENDEROS_PARQUE) | set(cm.NODOS_CALLE.values()) | {cm.SPAWN} | set(zc.ACCESO_LIMINAL)
    caminos |= cm.ACCESOS_BOLSILLOS
    for t in cm.TRAMOS:
        caminos |= set(cm.casillas_de_tramo(t.puntos)) | set(t.seccion)
    for prop in PROPS:
        celdas = set(prop.casillas)
        assert not celdas & vistas, prop
        assert not celdas & puertas, prop
        assert not celdas & caminos, prop
        for celda in celdas:
            permitidas = (cm.PASTO, cm.ACERA, cm.JARDIN, cm.CAMELLON) if prop.tipo == "arbol" else (cm.PASTO, cm.ACERA)
            assert cm.casilla(*celda) in permitidas, prop
        vistas |= celdas


# (b) Huellas de edificios dentro del mapa y sin solapes.

def test_b_huellas_de_edificios_y_casas_dentro_del_mapa_y_sin_solaparse():
    todas = list(cm.EDIFICIOS.values()) + HUELLAS_CASAS
    ocupadas = set()
    for huella in todas:
        col, fila, ancho, alto = huella
        assert 0 < col and 0 < fila and col + ancho < cm.COLUMNAS and fila + alto < cm.FILAS, huella
        assert ancho >= 2 and alto >= 2, huella
        celdas = _celdas(huella)
        assert not celdas & ocupadas, huella
        ocupadas |= celdas


def test_b_las_casas_cubren_exactamente_las_h_del_mapa():
    assert set().union(*(_celdas(h) for h in HUELLAS_CASAS)) == _con_letra(cm.CASA)


def test_b_pocos_edificios_y_bien_separados():
    """4 edificios de zona y como máximo 6 secundarios; ninguno toca a otro."""
    assert len(cm.EDIFICIOS) == 4 and len(cm.CASAS) <= 6
    huellas = list(cm.EDIFICIOS.values()) + HUELLAS_CASAS
    for i, a in enumerate(huellas):
        for b in huellas[i + 1:]:
            assert casas_ciudad.vecinas([a, b], distancia=0) == [], (a, b)


def test_b_cada_edificio_de_zona_tiene_jardin_al_frente_y_sendero():
    for zona, (col, fila, ancho, alto) in cm.EDIFICIOS.items():
        puerta_col, puerta_fila = cm.ENTRADAS[zona]
        frente = fila + alto
        assert cm.casilla(puerta_col, frente) in (cm.ACERA, cm.BARRICADA), zona  # el sendero
        jardin = [cm.casilla(c, frente) for c in range(col, col + ancho) if abs(c - puerta_col) > 1]
        assert jardin and all(letra == cm.JARDIN for letra in jardin), zona


# (c) Ningún par de edificios vecinos idénticos.

def test_c_dos_estilos_cualesquiera_difieren_lo_suficiente():
    nombres = list(assets.ESTILOS_CASA)
    for i, a in enumerate(nombres):
        for b in nombres[i + 1:]:
            assert casas_ciudad.diferencia(assets.ESTILOS_CASA[a], assets.ESTILOS_CASA[b]) >= \
                assets.VARIACION_MINIMA_ESTILOS, (a, b)


def test_c_ningun_edificio_secundario_repite_estilo():
    estilos = [estilo for _, estilo in cm.CASAS]
    assert len(set(estilos)) == len(estilos)
    assert all(estilo in assets.ESTILOS_CASA for estilo in estilos)


def test_c_los_edificios_de_zona_tienen_paletas_distintas():
    paletas = [tuple(sorted(assets.PALETA_FACHADA_ZONA[z].items())) for z in assets.PALETA_FACHADA_ZONA]
    assert len(set(paletas)) == len(paletas) == 3  # Hospital, Medios y Alcaldía; el Colegio es el pack escolar


def test_c_cada_casa_y_sus_ventanas_caben_en_la_fachada():
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

def test_e_puertas_bolsillos_y_lote_liminal_se_alcanzan_desde_la_plaza():
    grafo = cm.grafo_casillas(cm.es_solida)
    alcanzables = set(grafo.bfs(cm.NODOS_CALLE[cm.ZONA_PLAZA])[0])
    for zona, (col, fila) in cm.ENTRADAS.items():
        if zona != cm.ZONA_ALCALDIA:  # la Alcaldía empieza sellada
            assert (col, fila + 1) in alcanzables, zona
    col, fila, ancho, alto = cm.PLAZA_CIVICA
    assert (col + 2, fila + alto - 1) in alcanzables  # la plaza de la Alcaldía
    assert set(cm.SENDEROS_PARQUE) <= alcanzables  # los dos parques
    col, fila, ancho, _ = cm.PASEO_COMERCIAL
    assert all((c, fila) in alcanzables for c in range(col, col + ancho))  # la mitad norte del paseo, libre
    assert cm.ACCESOS_BOLSILLOS <= alcanzables
    col, fila, ancho, alto = zc.LIMINAL_RESERVADO
    for celda in _celdas((col + 1, fila, ancho - 2, alto)):  # todo menos las esquinas con conos
        assert celda in alcanzables, celda


def test_e_los_bolsillos_no_rodean_barricadas():
    todas = frozenset(c for t in cm.TRAMOS for c in t.seccion) | cm.BARRICADAS_ALCALDIA
    cortado = cm.grafo_casillas(lambda c, f: cm.es_solida(c, f, todas))
    for casilla in cm.NODOS_CALLE.values():
        _, alcanzables, _ = cortado.bfs(casilla)
        assert set(cm.NODOS_CALLE.values()) & set(alcanzables) == {casilla}


# (f) Identidad de cada zona.

def _presentes(id_zona):
    tipos = {p.tipo for p in PROPS if zc.zona_de(*p.base) == id_zona}
    for letra, nombre in ((cm.FUENTE, "fuente"), (cm.AGUA, "estanque")):
        if any(zc.zona_de(c, f) == id_zona for c, f in _con_letra(letra)):
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
    especies = [frozenset(z.arboles) for i, z in zc.ZONAS.items() if z.arboles]
    assert len(set(especies)) == len(especies)  # ninguna zona copia las especies de otra
    for zona in zc.ZONAS.values():
        assert set(zona.arboles) <= set(assets.ARBOLES_CIUDAD), zona.nombre


def test_f_arboles_variados_pinos_frutales_otonales_y_sauces():
    especies = {p.variante for p in PROPS if p.tipo == "arbol"}
    for grupo in (assets.PINOS, assets.FRUTALES, assets.OTONALES, assets.SAUCES, assets.ARBUSTOS):
        assert especies & set(grupo), grupo
    assert len(especies) >= 15


# (g) Farolas por zona; bancas simétricas.

def test_g_cada_farola_es_el_modelo_de_su_zona():
    farolas = [p for p in PROPS if p.tipo in ld.FAROLAS]
    assert len({p.tipo for p in farolas}) >= 4  # variación de modelo entre zonas
    for p in farolas:
        hito = any(p.casilla == h.casilla for z in zc.ZONAS.values() for h in z.hitos)
        assert hito or p.tipo == zc.farola_de(*p.casilla), p


def test_g_bancas_de_la_plaza_civica_enfrentadas_y_simetricas():
    col, fila, ancho, alto = cm.PLAZA_CIVICA
    bancas = [p for p in PROPS if p.tipo == "banca" and ld._dentro(cm.PLAZA_CIVICA, p.casilla)]
    assert len(bancas) == 2
    a, b = sorted(bancas, key=lambda p: p.casilla)
    assert a.casilla[1] == b.casilla[1] and a.casilla[0] + b.casilla[0] == 2 * col + ancho - 1
    assert (a.orientacion, b.orientacion) == ("E", "O")


# (h) Más verde, cero solapes y agua discreta.

def test_h_al_menos_45_por_ciento_del_area_no_vial_es_verde():
    assert hc.fraccion_verde(cm.MAPA, cm.VERDES, cm.CALLES) >= MIN_FRACCION_VERDE_CIUDAD


def test_h_ninguna_huella_se_solapa_con_otra():
    """Edificios, casas, fuentes, alberca y props: cada casilla tiene un dueño."""
    assert hc.solapes(hc.huellas_ciudad(cm)) == []


def test_h_solapes_detecta_casillas_y_rects_compartidos():
    elementos = [("a", frozenset({(0, 0), (1, 0)})), ("b", frozenset({(1, 0)})), ("c", frozenset({(5, 5)}))]
    assert hc.solapes(elementos) == [("a", "b")]
    assert hc.solapes_rects([("a", (0, 0, 10, 10)), ("b", (10, 0, 5, 5)), ("c", (9, 9, 2, 2))]) == [("a", "c")]
    assert hc.fraccion_verde(["c.J", ":k#"], (".", "J", "k"), ("c",)) == 3 / 5


def test_h_el_agua_es_poca():
    """Solo la alberca del parque y dos fuentes chicas: nada de canales."""
    agua = _con_letra(cm.AGUA) | _con_letra(cm.FUENTE)
    assert len(agua) <= 16
    assert _con_letra(cm.AGUA) == _celdas(cm.ALBERCA)


def test_h_tapa_fachada():
    huella = (10, 2, 4, 3)  # filas 2-4
    assert ld.tapa_fachada((15, 3), [huella])  # al costado, a 2
    assert ld.tapa_fachada((12, 7), [huella])  # 3 filas bajo la fachada
    assert not ld.tapa_fachada((12, 8), [huella])
    assert not ld.tapa_fachada((20, 3), [huella])


def test_lote_liminal_vacio_conectado_y_con_espacio_para_aristas_nuevas():
    col, fila, ancho, alto = zc.LIMINAL_RESERVADO
    assert ancho >= 6 and alto >= 4
    interior = _celdas((col + 1, fila + 1, ancho - 2, alto - 2))
    assert not any(set(p.casillas) & interior for p in PROPS)  # sin construir
    assert all(not cm.es_solida(c, f) for c, f in interior)
    sur = cm.NODOS_CALLE["Cruce Sur"]
    assert min(abs(sur[0] - c) for c, _ in zc.ACCESO_LIMINAL) <= 1  # se entra justo bajo el Cruce Sur


def test_las_entradas_de_los_bolsillos_estan_libres():
    assert set(zc.ACCESO_LIMINAL) <= cm.ACCESOS_BOLSILLOS
    for casilla in cm.ACCESOS_BOLSILLOS:
        assert not cm.es_solida(*casilla), casilla
