"""La terminal de decisión con forma de celular (src/ui/terminal_decision_render.py
y src/ui/celular_render.py): dibuja en todos sus estados, los botones de la app
son las opciones del árbol, nada tapa las zonas reservadas (indicador del
impostor, barra de controles y el botón REPORTAR chico) y nunca muestra a qué
resultado lleva una opción."""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame  # noqa: E402
import pytest  # noqa: E402

from src.core import assets  # noqa: E402
from src.dungeon.partida import Partida  # noqa: E402
from src.structures.tree import ArbolDecision  # noqa: E402
from src.ui import celular_render  # noqa: E402
from src.ui.terminal_decision import (  # noqa: E402
    CONFIRMAR, DERECHA, DETONACION, PURIFICACION_EXITOSA, TerminalDecision, construir_arbol_publicacion,
)
from src.ui.terminal_decision_render import (  # noqa: E402
    PUBLICACION, dibujar_terminal, opciones_visibles, rects_acciones, tipo_de_imagen, zona_de_subtitulo,
)
from Online.sesion_red import posts_sabotaje  # noqa: E402

ZONAS = ("Colegio", "Hospital", "Empresa de Medios")


@pytest.fixture(scope="module")
def pantalla():
    pygame.display.init()
    pygame.font.init()
    return pygame.display.set_mode((1280, 720))


def _terminal(arbol, pasos=(), restante=None):
    terminal = TerminalDecision(arbol, 45.0, descender_resultados=True)
    terminal.iniciar()
    for paso in pasos:
        terminal.navegar(paso)
    if restante is not None:
        terminal.tiempo_restante = restante
    return terminal


def _escenarios():
    partida = Partida()
    campania = partida.campania
    for zona in ZONAS:
        escenario = campania.preparar_escenario(zona, 0)
        yield zona, campania, escenario


def _estados():
    """(nombre, kwargs de dibujar_terminal, terminal) en todos los estados que importan."""
    yield "fijo", {"subtitulo": "Cuarto final"}, _terminal(construir_arbol_publicacion())
    for zona, campania, escenario in _escenarios():
        todas = campania.evidencias_de(zona)
        for cuantas in (0, 1, len(todas)):
            kwargs = {"subtitulo": f"{zona}  ·  {campania.titulo_capitulo(zona)}", "post": escenario.post,
                      "evidencias": todas[:cuantas], "total_evidencias": len(todas), "zona": zona,
                      "verificacion": escenario.resultado_verificacion, "exige_mas_pruebas": cuantas == 1,
                      "nota_decisor": "Sin voz: tu equipo decide por ti" if cuantas == 0 else ""}
            yield f"{zona}-{cuantas}", kwargs, _terminal(escenario.arbol)
        yield f"{zona}-verificar", kwargs, _terminal(escenario.arbol, (CONFIRMAR,), restante=3.0)
        yield f"{zona}-reportar", kwargs, _terminal(escenario.arbol, (DERECHA, DERECHA, DERECHA, CONFIRMAR))
    for post in posts_sabotaje():
        yield f"sabotaje-{post['usuario']}", {"subtitulo": assets.TEXTO_SUBTITULO_POST_SABOTAJE, "post": post,
                                              "zona": post.get("zona")}, _terminal(construir_arbol_publicacion())


ESTADOS = list(_estados())
ZONAS_RESERVADAS = [
    pygame.Rect(assets.RECT_INDICADOR_SABOTAJE),
    pygame.Rect(0, 720 - assets.ALTO_BARRA_CONTROLES, 1280, assets.ALTO_BARRA_CONTROLES),
    pygame.Rect(assets.RECT_BOTON_REPORTAR_TERMINAL),
]


@pytest.mark.parametrize("nombre, kwargs, terminal", ESTADOS, ids=[e[0] for e in ESTADOS])
def test_dibuja_sin_tapar_las_zonas_reservadas(pantalla, nombre, kwargs, terminal):
    dibujado = dibujar_terminal(pantalla, terminal, tiempo=0.4, **kwargs)
    for etiqueta, rect in dibujado.importantes:
        for reservada in ZONAS_RESERVADAS:
            assert not rect.colliderect(reservada), (nombre, etiqueta, rect, reservada)


@pytest.mark.parametrize("nombre, kwargs, terminal", ESTADOS, ids=[e[0] for e in ESTADOS])
def test_nunca_muestra_a_que_resultado_lleva_una_opcion(pantalla, nombre, kwargs, terminal):
    dibujado = dibujar_terminal(pantalla, terminal, tiempo=0.4, **kwargs)
    for cadena in dibujado.etiquetas_dibujadas:
        assert PURIFICACION_EXITOSA not in cadena and DETONACION not in cadena


@pytest.mark.parametrize("nombre, kwargs, terminal", ESTADOS, ids=[e[0] for e in ESTADOS])
def test_los_botones_son_las_opciones_del_nodo_y_caben_en_el_celular(pantalla, nombre, kwargs, terminal):
    dibujado = dibujar_terminal(pantalla, terminal, tiempo=0.4, **kwargs)
    opciones = [nodo.etiqueta for nodo in opciones_visibles(terminal.nodo_actual)]
    if terminal.nodo_actual is terminal.arbol.raiz:
        assert [etiqueta for etiqueta, _ in dibujado.acciones] == opciones
        for _, rect in dibujado.acciones:
            assert dibujado.pantalla_feed.contains(rect)
    else:  # segundo nivel: hoja inferior con las opciones del nodo
        assert dibujado.hoja is not None and [etiqueta for etiqueta, _ in dibujado.filas_hoja] == opciones
        for _, rect in dibujado.filas_hoja:
            assert dibujado.pantalla_feed.contains(rect)


def test_la_raiz_de_la_historia_tiene_las_acciones_de_la_app(pantalla):
    for zona, _, escenario in _escenarios():
        etiquetas = [nodo.etiqueta for nodo in escenario.arbol.raiz.hijos]
        assert etiquetas == ["Verificar", "Me gusta", "Compartir", "Reportar", "Ignorar"], zona


@pytest.mark.parametrize("etiqueta, icono", [
    ("Verificar", "lupa"), ("Me gusta", "corazon"), ("Compartir", "compartir"), ("Reportar", "bandera"),
    ("Ignorar", "saltar"), ("Reportar como suplantación, con evidencia", "bandera"), ("Algo nuevo", "puntos"),
])
def test_cada_opcion_tiene_su_icono(etiqueta, icono):
    assert celular_render.icono_para(etiqueta) == icono


@pytest.mark.parametrize("cantidad", [1, 2, 3, 4, 5, 6])
def test_los_botones_de_la_fila_no_se_pisan(cantidad):
    fila = pygame.Rect(880, 480, 356, 64)
    rects = rects_acciones(fila, cantidad)
    assert len(rects) == cantidad and all(fila.contains(r) for r in rects)
    assert not any(a.colliderect(b) for i, a in enumerate(rects) for b in rects[i + 1:])


def test_un_arbol_con_muchas_opciones_tambien_se_dibuja(pantalla):
    arbol = ArbolDecision(0, "Publicación Viral")
    for numero in range(1, 7):
        arbol.insertar(0, numero, f"Opción {numero}")
        arbol.insertar(numero, numero * 10 + 1, PURIFICACION_EXITOSA)
    dibujado = dibujar_terminal(pantalla, _terminal(arbol), "Cuarto final")
    assert len(dibujado.acciones) == 6


def test_ayudas():
    assert zona_de_subtitulo("Empresa de Medios  ·  El origen de la señal") == "Empresa de Medios"
    assert zona_de_subtitulo("Cuarto final") is None
    assert tipo_de_imagen("[captura recortada de un comunicado]") == "documento"
    assert tipo_de_imagen("[gráfico sin ficha técnica]") == "grafico"
    assert PUBLICACION["usuario"].startswith("@")


def test_el_fondo_es_el_morado_de_civitas(pantalla):
    dibujar_terminal(pantalla, _terminal(construir_arbol_publicacion()), "Cuarto final")
    color = pantalla.get_at((420, 700 - assets.ALTO_BARRA_CONTROLES))[:3]
    assert color in (assets.COLOR_FONDO_TERMINAL_CIVITAS, assets.COLOR_TRAMA_TERMINAL_CIVITAS)
