"""Decoración y edificios de Ciudad Nova (sin pygame): el layout no
superpone props, no tapa caminos ni puertas, las farolas guardan su
espaciado, la semilla fija da siempre la misma ciudad, las bancas van en
pares, el grafo sigue conexo con pesos de su largo real, y cada edificio
tiene una huella dentro del mapa, sin solaparse y con escala entera."""

import os
import subprocess
import sys
from collections import Counter, defaultdict

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, RAIZ)

from src.core import assets  # noqa: E402
from src.core.balance import (  # noqa: E402
    ESPACIADO_FAROLAS,
    METROS_POR_CASILLA,
    METROS_POR_PUNTO_DE_PESO,
    PESO_MINIMO_CIUDAD,
    TAM_CASILLA,
)
from src.dungeon import ciudad_mapa as cm  # noqa: E402
from src.dungeon import layout_decoracion as ld  # noqa: E402
from src.dungeon.grafo_ciudad import GrafoCiudad  # noqa: E402

PROPS = cm.DECORACION


def _generar_de_nuevo(semilla=None):
    argumentos = dict(edificios=cm.EDIFICIOS.values())
    if semilla is not None:
        argumentos["semilla"] = semilla
    return ld.generar(cm.MAPA, cm.CALLES, [(t.puntos, t.seccion) for t in cm.TRAMOS], cm.NODOS_CALLE.values(),
                      cm.ENTRADAS.values(), cm.SPAWN, cm.PLAZA, cm.PARQUE, cm.SENDEROS_PARQUE, cm.JARDINES,
                      **argumentos)


# ----------------------------------------------------------------------
# Layout
# ----------------------------------------------------------------------

def test_modulos_no_importan_pygame():
    codigo = "import sys, src.dungeon.layout_decoracion, src.core.puntajes_roles; print('pygame' in sys.modules)"
    salida = subprocess.run([sys.executable, "-c", codigo], cwd=RAIZ, capture_output=True, text=True, check=True)
    assert salida.stdout.strip() == "False"


def test_hay_de_todo_y_ningun_prop_se_superpone():
    casillas = [p.casilla for p in PROPS]
    assert len(casillas) == len(set(casillas))
    tipos = Counter(p.tipo for p in PROPS)
    for tipo in ("farola", "banca", "arbol", "jardinera", "basurero", "buzon", "hidrante"):
        assert tipos[tipo] > 0, tipo


def test_ningun_prop_sobre_un_camino_una_puerta_o_una_barricada():
    prohibidas = set(cm.NODOS_CALLE.values()) | {cm.SPAWN} | set(cm.SENDEROS_PARQUE) | set(cm.BARRICADAS_ALCALDIA)
    for t in cm.TRAMOS:
        prohibidas |= set(cm.casillas_de_tramo(t.puntos)) | set(t.seccion)
    for col, fila in cm.ENTRADAS.values():
        for dc in (-1, 0, 1):
            for df in (0, 1, 2):
                prohibidas.add((col + dc, fila + df))  # la puerta y el paso frente a ella
    for prop in PROPS:
        assert prop.casilla not in prohibidas, prop
        assert cm.casilla(*prop.casilla) not in cm.CALLES, prop
        assert cm.casilla(*prop.casilla) not in (cm.EDIFICIO, cm.ENTRADA, cm.CASA), prop


def test_props_sobre_casillas_validas():
    for prop in PROPS:
        letra = cm.casilla(*prop.casilla)
        if prop.tipo == "arbol":
            assert letra in (cm.PASTO, cm.ARBOL, cm.ACERA), prop  # pasto, seto o rincón de la Plaza
        else:
            assert letra in (cm.PASTO, cm.ACERA), prop


def test_farolas_a_intervalos_regulares_en_cada_acera():
    """En cada línea de acera (misma fila o misma columna), dos farolas
    seguidas están a un múltiplo exacto de ESPACIADO_FAROLAS."""
    for t in cm.TRAMOS:
        for (c0, f0), (c1, f1) in zip(t.puntos, t.puntos[1:]):
            horizontal = f0 == f1
            for lado in (-2, 2):
                linea = sorted(
                    p.casilla[0] if horizontal else p.casilla[1]
                    for p in PROPS if p.tipo == "farola" and not ld._dentro(cm.PLAZA, p.casilla)
                    and (p.casilla[1] == f0 + lado if horizontal else p.casilla[0] == c0 + lado)
                    and (min(c0, c1) <= p.casilla[0] <= max(c0, c1) if horizontal else min(f0, f1) <= p.casilla[1] <= max(f0, f1))
                )
                for a, b in zip(linea, linea[1:]):
                    assert (b - a) % ESPACIADO_FAROLAS == 0 and b - a >= ESPACIADO_FAROLAS, (t.a, t.b, lado, linea)


def test_las_avenidas_tienen_farolas_en_ambas_aceras():
    for t in cm.TRAMOS:
        (c0, f0), (c1, f1) = t.puntos[0], t.puntos[1]
        if abs(c1 - c0) + abs(f1 - f0) < 2 * ESPACIADO_FAROLAS:
            continue
        for lado in (-2, 2):
            hay = [p for p in PROPS if p.tipo == "farola"
                   and (p.casilla[1] == f0 + lado if f0 == f1 else p.casilla[0] == c0 + lado)]
            assert hay, (t.a, t.b, lado)


def test_misma_semilla_misma_ciudad_y_otra_semilla_otros_arboles():
    assert _generar_de_nuevo() == PROPS
    otra = _generar_de_nuevo(semilla=7)
    arboles = {(p.casilla, p.variante) for p in PROPS if p.tipo == "arbol"}
    assert arboles != {(p.casilla, p.variante) for p in otra if p.tipo == "arbol"}


def test_bancas_de_la_plaza_en_pares_simetricos_mirando_al_centro():
    col, fila, ancho, alto = cm.PLAZA
    cx, cy = col + ancho // 2, fila + alto // 2
    bancas = {p.casilla: p for p in PROPS if p.tipo == "banca" and ld._dentro(cm.PLAZA, p.casilla)}
    assert len(bancas) >= 4
    for (c, f), banca in bancas.items():
        assert (2 * cx - c, f) in bancas and (c, 2 * cy - f) in bancas  # espejo en x y en y
        assert banca.orientacion == (ld.SUR if f < cy else ld.NORTE)


def test_bancas_del_parque_enfrentadas_al_sendero():
    bancas = [p for p in PROPS if p.tipo == "banca" and ld._dentro(cm.PARQUE, p.casilla)
              and not ld._dentro(cm.PLAZA, p.casilla)]
    assert bancas
    for banca in bancas:
        c, f = banca.casilla
        frente = (c, f + 1) if banca.orientacion == ld.SUR else (c, f - 1)
        assert frente in cm.SENDEROS_PARQUE, banca


def test_arboles_del_parque_agrupados_sin_tocarse_ni_pisar_el_sendero():
    arboles = [p.casilla for p in PROPS if p.tipo == "arbol" and ld._dentro(cm.PARQUE, p.casilla)
               and cm.casilla(*p.casilla) == cm.PASTO]
    assert len(arboles) >= 5
    for i, a in enumerate(arboles):
        for b in arboles[i + 1:]:
            assert max(abs(a[0] - b[0]), abs(a[1] - b[1])) >= 2
        assert all(abs(a[0] - s[0]) + abs(a[1] - s[1]) > 1 for s in cm.SENDEROS_PARQUE)


def test_hileras_de_arboles_sobre_los_setos_lejos_de_las_fachadas():
    en_setos = [p for p in PROPS if p.tipo == "arbol" and cm.casilla(*p.casilla) == cm.ARBOL]
    assert len(en_setos) >= 20
    por_fila = defaultdict(list)
    for p in en_setos:
        por_fila[p.casilla[1]].append(p.casilla[0])
        for rect in cm.EDIFICIOS.values():
            assert ld._distancia_a_rect(p.casilla, rect) > 2, p


def test_con_la_decoracion_todo_se_alcanza_y_las_barricadas_siguen_cortando():
    grafo = cm.grafo_casillas(cm.es_solida)
    _, distancias, _ = grafo.bfs(cm.SPAWN)
    for casilla in list(cm.NODOS_CALLE.values()) + list(cm.ENTRADAS.values()):
        assert casilla in distancias, casilla
    todas = frozenset(c for t in cm.TRAMOS for c in t.seccion) | cm.BARRICADAS_ALCALDIA
    cortado = cm.grafo_casillas(lambda c, f: cm.es_solida(c, f, todas))
    for casilla in cm.NODOS_CALLE.values():
        _, alcanzables, _ = cortado.bfs(casilla)
        assert set(cm.NODOS_CALLE.values()) & set(alcanzables) == {casilla}


# ----------------------------------------------------------------------
# Grafo tras el rediseño
# ----------------------------------------------------------------------

def test_grafo_conexo_y_pesos_del_largo_real():
    ciudad = GrafoCiudad()
    assert ciudad.grafo.es_conexo()
    for t in cm.TRAMOS:
        metros = cm.largo_tramo(t) * METROS_POR_CASILLA
        esperado = max(PESO_MINIMO_CIUDAD, int(metros / METROS_POR_PUNTO_DE_PESO + 0.5))
        assert ciudad.grafo.peso(t.a, t.b) == esperado


# ----------------------------------------------------------------------
# Edificios: huellas y escala
# ----------------------------------------------------------------------

def _rect(huella):
    col, fila, ancho, alto = huella
    return col, fila, col + ancho, fila + alto


def test_huellas_dentro_del_mapa_con_margen():
    for zona, huella in cm.EDIFICIOS.items():
        c0, f0, c1, f1 = _rect(huella)
        assert c0 >= 2 and f0 >= 2 and c1 <= cm.COLUMNAS - 2 and f1 <= cm.FILAS - 2, zona
        for col in range(c0, c1):
            for fila in range(f0, f1):
                assert cm.casilla(col, fila) in (cm.EDIFICIO, cm.ENTRADA), (zona, col, fila)


def test_huellas_sin_solaparse_y_con_aire_entre_ellas():
    zonas = list(cm.EDIFICIOS)
    for i, a in enumerate(zonas):
        for b in zonas[i + 1:]:
            ac0, af0, ac1, af1 = _rect(cm.EDIFICIOS[a])
            bc0, bf0, bc1, bf1 = _rect(cm.EDIFICIOS[b])
            separadas_x = ac1 + 1 <= bc0 or bc1 + 1 <= ac0
            separadas_y = af1 + 1 <= bf0 or bf1 + 1 <= af0
            assert separadas_x or separadas_y, (a, b)


def test_puerta_en_la_base_y_acera_libre_delante():
    for zona, (col, fila) in cm.ENTRADAS.items():
        c0, f0, c1, f1 = _rect(cm.EDIFICIOS[zona])
        assert c0 <= col < c1 and fila == f1 - 1
        assert not cm.es_solida(col, fila + 1), zona  # se sale a la acera


def test_escala_entera_que_cubre_la_huella_exacta():
    for zona, (col, fila, ancho, alto) in cm.EDIFICIOS.items():
        config = assets.ARTE_EDIFICIOS[zona]
        assert isinstance(config["escala"], int) and config["escala"] >= 1
        assert (ancho * TAM_CASILLA) % config["escala"] == 0 and (alto * TAM_CASILLA) % config["escala"] == 0
    assert assets.ANCLA_EDIFICIOS == "midbottom"
