"""Tests de los escenarios de decisión del modo historia (sin pygame).

Cubren: carga y validación del contenido, forma del árbol por zona,
estado de evidencia, consecuencia por hoja y por tiempo agotado, y que
la evidencia cambia el resultado de la misma opción.
"""

import copy
import os
import subprocess
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest  # noqa: E402

from src.core.balance import ZONA_COLEGIO, ZONA_EMPRESA_MEDIOS, ZONA_HOSPITAL  # noqa: E402
from src.story import contenido  # noqa: E402
from src.story.escenarios import (  # noqa: E402
    DESMENTIDO,
    ESTADOS_EVIDENCIA,
    PARCIAL,
    SIN_PRUEBAS,
    VERIFICADO,
    EscenarioDecision,
    estado_evidencia,
)
from src.ui.terminal_decision import (  # noqa: E402
    CONFIRMAR,
    DERECHA,
    DETONACION,
    PURIFICACION_EXITOSA,
    TerminalDecision,
)

ZONAS = (ZONA_COLEGIO, ZONA_HOSPITAL, ZONA_EMPRESA_MEDIOS)
# Verificar va primero: es la opción segura que queda bajo el cursor.
OPCIONES_RAIZ = ["Verificar", "Me gusta", "Compartir", "Reportar", "Ignorar"]


@pytest.fixture(scope="module")
def datos():
    return contenido.cargar()


def test_los_modulos_de_historia_no_importan_pygame():
    raiz = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    codigo = ("import sys, src.story.campania, src.story.escenarios, src.story.estado_ciudad, "
              "src.story.dialogo, src.story.contenido, src.story.reputacion, src.story.redencion, "
              "src.story.investigacion, src.story.cinematica; print('pygame' in sys.modules)")
    salida = subprocess.run([sys.executable, "-c", codigo], cwd=raiz, capture_output=True, text=True, check=True)
    assert salida.stdout.strip() == "False"


def test_contenido_valido_y_con_las_tres_zonas(datos):
    assert set(ZONAS) <= set(datos["escenarios"])
    assert set(ZONAS) | {"Alcaldía"} <= set(datos["capitulos"])
    assert len(datos["pistas"]) == 3


@pytest.mark.parametrize("romper", [
    lambda d: d["escenarios"][ZONA_COLEGIO]["opciones"][0]["hijos"][0].update(resultado="exito"),
    lambda d: d["escenarios"][ZONA_COLEGIO]["opciones"][1]["efectos"].update(karma=3),
    lambda d: d["pistas"].update(no_existe="x"),
    lambda d: d["red_cuentas"].update(origen="nadie"),
    lambda d: d["escenarios"][ZONA_COLEGIO]["opciones"][1].update(accion="troll"),
    lambda d: d["finales"].pop("confianza_perdida"),
    lambda d: d["red_social"]["conexiones"].append(["ana", "ana"]),
    lambda d: d["escenarios"][ZONA_HOSPITAL].pop("tiempo_agotado"),
    lambda d: d["mensajes_reputacion"].pop("me_gusta"),
])
def test_contenido_roto_lanza_error_claro(datos, romper):
    copia = copy.deepcopy(datos)
    romper(copia)
    with pytest.raises(contenido.ContenidoInvalido):
        contenido.validar(copia)


def test_estado_de_evidencia():
    assert estado_evidencia(0, 3, "falso") == SIN_PRUEBAS
    assert estado_evidencia(2, 3, "falso") == PARCIAL
    assert estado_evidencia(3, 3, "falso") == DESMENTIDO
    assert estado_evidencia(3, 3, "fuera_de_contexto") == DESMENTIDO
    assert estado_evidencia(3, 3, "cierto") == VERIFICADO
    assert estado_evidencia(3, 3, "sin_verificar") == PARCIAL


@pytest.mark.parametrize("zona", ZONAS)
def test_arbol_de_cada_zona_tiene_dos_niveles_y_hojas_validas(datos, zona):
    escenario = EscenarioDecision(datos["escenarios"][zona], DESMENTIDO)
    raiz = escenario.arbol.raiz
    assert [h.etiqueta for h in raiz.hijos] == OPCIONES_RAIZ
    por_etiqueta = {h.etiqueta: h for h in raiz.hijos}
    assert len(por_etiqueta["Verificar"].hijos) == 2 and len(por_etiqueta["Reportar"].hijos) == 2  # nivel intermedio
    hojas = [h for h in escenario.arbol.preorden() if h in (PURIFICACION_EXITOSA, DETONACION)]
    assert len(hojas) == len(escenario.hojas) == 7
    assert PURIFICACION_EXITOSA in hojas and DETONACION in hojas
    # Todos los ids son únicos (insertar lo exige) y por niveles arranca en la raíz.
    assert escenario.arbol.por_niveles()[0] == escenario.titulo


@pytest.mark.parametrize("zona", ZONAS)
def test_la_forma_del_arbol_no_depende_de_la_evidencia(datos, zona):
    """Host e invitado (Online) comparten ids aunque tengan otra evidencia."""
    escenarios = [EscenarioDecision(datos["escenarios"][zona], e) for e in ESTADOS_EVIDENCIA]
    ids = [sorted(e.hojas) for e in escenarios]
    assert all(i == ids[0] for i in ids)
    opciones = 1 + len(OPCIONES_RAIZ)
    assert all(e.arbol.por_niveles()[:opciones] == escenarios[0].arbol.por_niveles()[:opciones] for e in escenarios)
    assert [h.id for h in escenarios[0].arbol.raiz.hijos] == [h.id for h in escenarios[-1].arbol.raiz.hijos]


def _navegar(escenario, *pasos):
    terminal = TerminalDecision(escenario.arbol, 15.0)
    terminal.iniciar()
    for paso in pasos:
        terminal.navegar(paso)
    return terminal


def test_misma_opcion_distinto_resultado_segun_evidencia(datos):
    con_pruebas = EscenarioDecision(datos["escenarios"][ZONA_COLEGIO], DESMENTIDO)
    sin_pruebas = EscenarioDecision(datos["escenarios"][ZONA_COLEGIO], SIN_PRUEBAS)
    camino = ("Verificar", "Publicar aclaración con el comunicado")
    assert con_pruebas.consecuencia_por_camino(*camino).resultado == PURIFICACION_EXITOSA
    assert sin_pruebas.consecuencia_por_camino(*camino).resultado == DETONACION
    assert con_pruebas.consecuencia_por_camino(*camino).puntos > sin_pruebas.consecuencia_por_camino(*camino).puntos


def test_terminal_sobre_el_escenario_llega_a_la_consecuencia_de_la_hoja(datos):
    escenario = EscenarioDecision(datos["escenarios"][ZONA_COLEGIO], DESMENTIDO)
    terminal = _navegar(escenario, CONFIRMAR, CONFIRMAR, CONFIRMAR)  # Verificar -> Publicar aclaración -> hoja
    assert terminal.resultado == PURIFICACION_EXITOSA
    consecuencia = escenario.consecuencia_para(terminal)
    assert consecuencia.exito and consecuencia.opcion == "Verificar"
    assert consecuencia.efectos["desinformacion"] < 0

    terminal = _navegar(escenario, DERECHA, DERECHA, CONFIRMAR, CONFIRMAR)  # Compartir -> hoja
    assert terminal.resultado == DETONACION
    consecuencia = escenario.consecuencia_para(terminal)
    assert consecuencia.opcion == "Compartir" and consecuencia.efectos["desinformacion"] > 0

    terminal = _navegar(escenario, DERECHA, CONFIRMAR, CONFIRMAR)  # Me gusta -> hoja
    assert terminal.resultado == DETONACION
    consecuencia = escenario.consecuencia_para(terminal)
    assert consecuencia.opcion == "Me gusta" and consecuencia.accion == "me_gusta"


# ----------------------------------------------------------------- Me gusta


@pytest.mark.parametrize("zona", ZONAS)
def test_me_gusta_es_la_segunda_opcion_y_es_una_hoja(datos, zona):
    opcion = datos["escenarios"][zona]["opciones"][1]
    assert opcion["etiqueta"] == "Me gusta" and opcion["accion"] == "me_gusta" and "hijos" not in opcion
    escenario = EscenarioDecision(datos["escenarios"][zona], SIN_PRUEBAS)
    me_gusta = escenario.arbol.raiz.hijos[1]
    assert me_gusta.etiqueta == "Me gusta" and len(me_gusta.hijos) == 1 and not me_gusta.hijos[0].hijos
    assert escenario.hojas[me_gusta.hijos[0].id].accion == "me_gusta"


def _estados_de(datos, zona):
    final = VERIFICADO if datos["escenarios"][zona]["veredicto"] == "cierto" else DESMENTIDO
    return (SIN_PRUEBAS, PARCIAL, final)


def _magnitud(efectos):
    return sum(abs(delta) for delta in efectos.values())


@pytest.mark.parametrize("zona, esperado", [
    (ZONA_COLEGIO, DETONACION),  # captura recortada: el me gusta la amplifica
    (ZONA_HOSPITAL, PURIFICACION_EXITOSA),  # pedido verdadero: el me gusta ayuda, poco
    (ZONA_EMPRESA_MEDIOS, DETONACION),  # encuesta falsa
])
def test_me_gusta_depende_de_lo_que_dice_la_publicacion_y_pesa_menos_que_compartir(datos, zona, esperado):
    """Un me gusta amplifica como un compartir más suave: mismo desenlace que
    Compartir con cualquier evidencia, pero cada efecto (y los puntos) pesa menos."""
    for estado in _estados_de(datos, zona):
        escenario = EscenarioDecision(datos["escenarios"][zona], estado)
        me_gusta = escenario.consecuencia_por_camino("Me gusta")
        compartir = escenario.consecuencia_por_camino("Compartir")
        assert me_gusta.resultado == compartir.resultado == esperado, estado
        assert me_gusta.accion == "me_gusta" and me_gusta.texto and me_gusta.texto != compartir.texto
        for indicador, delta in me_gusta.efectos.items():
            referencia = compartir.efectos.get(indicador, 0)
            assert delta * referencia > 0 and abs(delta) < abs(referencia), (estado, indicador)
        assert 0 < _magnitud(me_gusta.efectos) < _magnitud(compartir.efectos)
        assert me_gusta.puntos <= compartir.puntos
        if esperado == PURIFICACION_EXITOSA:
            assert me_gusta.puntos < compartir.puntos


def test_me_gusta_en_hospital_ayuda_mucho_menos_que_compartir_los_datos(datos):
    """Con todas las pruebas, compartir el pedido con los datos comprobados es lo
    que llena el banco de sangre; un me gusta no muestra la prueba."""
    escenario = EscenarioDecision(datos["escenarios"][ZONA_HOSPITAL], VERIFICADO)
    me_gusta = escenario.consecuencia_por_camino("Me gusta")
    con_datos = escenario.consecuencia_por_camino("Verificar", "Compartir el pedido con los datos comprobados")
    assert me_gusta.exito and con_datos.exito
    assert me_gusta.puntos * 2 < con_datos.puntos
    assert _magnitud(me_gusta.efectos) * 2 < _magnitud(con_datos.efectos)
    # Más pruebas, mejor me gusta: el desenlace no cambia, la fuerza sí.
    puntos = [EscenarioDecision(datos["escenarios"][ZONA_HOSPITAL], e).consecuencia_por_camino("Me gusta").puntos
              for e in (SIN_PRUEBAS, PARCIAL, VERIFICADO)]
    assert puntos == sorted(puntos) and len(set(puntos)) == 3


def test_tiempo_agotado_a_mitad_del_arbol_es_consecuencia_de_tiempo(datos):
    escenario = EscenarioDecision(datos["escenarios"][ZONA_EMPRESA_MEDIOS], PARCIAL)
    terminal = _navegar(escenario, CONFIRMAR)  # baja a "Verificar" y se queda
    terminal.actualizar(20.0)
    assert terminal.resultado == DETONACION
    consecuencia = escenario.consecuencia_para(terminal)
    assert consecuencia.resultado == DETONACION
    assert consecuencia.texto == datos["escenarios"][ZONA_EMPRESA_MEDIOS]["tiempo_agotado"]["texto"]


def test_reportar_abusivo_detona_aunque_haya_pruebas(datos):
    escenario = EscenarioDecision(datos["escenarios"][ZONA_COLEGIO], DESMENTIDO)
    abusivo = escenario.consecuencia_por_camino("Reportar", "Reportar en masa a la cuenta")
    assert abusivo.resultado == DETONACION and abusivo.efectos["conflictos"] > 0


def test_crud_y_recorridos_del_arbol_sobre_un_escenario(datos):
    """Inserción, búsqueda, eliminación y los recorridos sobre el árbol
    real de una zona (material de la guía de sustentación)."""
    escenario = EscenarioDecision(datos["escenarios"][ZONA_COLEGIO], DESMENTIDO)
    arbol = escenario.arbol
    total = len(arbol.preorden())
    assert total == len(arbol.postorden()) == len(arbol.por_niveles()) == len(arbol.inorden())
    # Búsqueda por id: la raíz es 0 y la primera opción es 1.
    assert arbol.buscar(0) is arbol.raiz and arbol.buscar(1).etiqueta == "Verificar"
    assert arbol.buscar(999) is None
    # Inserción: una opción nueva cuelga de la raíz al final.
    arbol.insertar(0, 999, "Pedir contexto")
    assert arbol.raiz.hijos[-1].etiqueta == "Pedir contexto" and len(arbol.preorden()) == total + 1
    with pytest.raises(ValueError):
        arbol.insertar(0, 1, "id repetido")
    # Eliminación: quitar "Compartir" se lleva su hoja (subárbol completo).
    id_compartir = next(h.id for h in arbol.raiz.hijos if h.etiqueta == "Compartir")
    assert arbol.eliminar(id_compartir)
    quedan = ["Verificar", "Me gusta", "Reportar", "Ignorar", "Pedir contexto"]
    assert [h.etiqueta for h in arbol.raiz.hijos] == quedan
    assert len(arbol.preorden()) == total + 1 - 2
    assert not arbol.eliminar(id_compartir)
    # Recorridos: preorden empieza por la raíz, postorden termina en ella,
    # por niveles lista primero las opciones de primer nivel.
    assert arbol.preorden()[0] == escenario.titulo and arbol.postorden()[-1] == escenario.titulo
    assert arbol.por_niveles()[1:1 + len(quedan)] == quedan
