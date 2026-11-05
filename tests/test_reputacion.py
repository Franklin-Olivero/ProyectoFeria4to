"""Reputación individual: rangos, valoración con matices, consecuencias,
recompensas sin duplicar, crisis y sincronización con los invitados (sin pygame)."""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest  # noqa: E402

from src.core.balance import (  # noqa: E402
    NIVELES_REPUTACION,
    REPORTES_POR_ZONA,
    REPUTACION_INICIAL,
    UMBRAL_CRISIS_REPUTACION,
    ZONA_COLEGIO,
    ZONA_EMPRESA_MEDIOS,
    ZONA_HOSPITAL,
)
from src.dungeon.mazmorra import Mazmorra  # noqa: E402
from src.dungeon.partida import Partida  # noqa: E402
from src.story.escenarios import DESMENTIDO, PARCIAL, SIN_PRUEBAS, VERIFICADO  # noqa: E402
from src.story.reputacion import (  # noqa: E402
    CRISIS_PENDIENTE,
    SIN_CRISIS,
    ReputacionJugador,
    ajuste_por_alcance,
    nivel_de,
    valorar_accion,
)
from src.ui.terminal_decision import CONFIRMAR, DERECHA, TerminalDecision  # noqa: E402


def _mazmorra_lista(zona, semilla=0):
    m = Mazmorra(REPORTES_POR_ZONA[zona], zona, semilla=semilla)
    for cuarto in m.grafo.nodos():
        if cuarto != m.cuarto_final:
            m.marcar_limpiado(cuarto)
    m.entrar(m.cuarto_final)
    return m


def _decidir(partida, zona, *pasos, pruebas=3, semilla=0):
    for _ in range(pruebas):
        partida.campania.revelar_evidencia(zona)
    terminal = TerminalDecision(partida.fabrica_arbol(zona)(), 15.0)
    terminal.iniciar()
    for paso in pasos:
        terminal.navegar(paso)
    assert partida.cerrar_mazmorra(_mazmorra_lista(zona, semilla), terminal.resultado, terminal)
    return partida.campania.ultimo_cambio_reputacion


COMPARTIR = (DERECHA, CONFIRMAR, CONFIRMAR)
VERIFICAR_PUBLICAR = (CONFIRMAR, CONFIRMAR, CONFIRMAR)


def test_reputacion_inicial_es_neutral():
    assert REPUTACION_INICIAL == 0
    r = ReputacionJugador()
    assert r.valor == 0 and r.nivel == "neutral" and r.nombre_nivel == "Reputación neutral"
    assert Partida().campania.reputacion == 0


@pytest.mark.parametrize("valor, nivel", [
    (100, "referente"), (60, "referente"), (59, "confiable"), (20, "confiable"), (19, "neutral"),
    (-19, "neutral"), (-20, "cuestionada"), (-59, "cuestionada"), (-60, "crisis"), (-100, "crisis"),
])
def test_tramos_de_reputacion(valor, nivel):
    assert nivel_de(valor)[0] == nivel


def test_niveles_son_configurables_y_estan_en_balance():
    assert [n[0] for n in NIVELES_REPUTACION] == ["referente", "confiable", "neutral", "cuestionada", "crisis"]


def test_limites_entre_menos_cien_y_cien():
    r = ReputacionJugador()
    r.aplicar(500)
    assert r.valor == 100
    r.aplicar(-5000)
    assert r.valor == -100


def test_reputacion_positiva_y_negativa_quedan_en_el_historial():
    r = ReputacionJugador()
    subir = r.aplicar(25, "Bien", "Colegio")
    assert subir.delta == 25 and r.valor == 25
    bajar = r.aplicar(-30, "Mal", "Hospital")
    assert bajar.delta == -30 and r.valor == -5
    assert r.peor_cambio() is bajar
    assert r.tomar_pendiente() is subir and r.tomar_pendiente() is bajar and r.tomar_pendiente() is None


def test_recompensa_con_clave_no_se_duplica_pero_las_penalizaciones_si():
    r = ReputacionJugador()
    assert r.aplicar(20, clave="decision:Colegio") is not None
    assert r.aplicar(20, clave="decision:Colegio") is None
    assert r.valor == 20
    r.aplicar(-5)
    r.aplicar(-5)
    assert r.valor == 10


# --------------------------------------------------------------- matices


def test_misma_accion_vale_distinto_segun_la_verdad_y_lo_que_se_sabia():
    # Compartir algo falso sabiéndolo es peor que equivocarse sin pruebas.
    assert valorar_accion("compartir", "falso", DESMENTIDO) < valorar_accion("compartir", "falso", SIN_PRUEBAS) < 0
    # Compartir algo verdadero y comprobado suma.
    assert valorar_accion("compartir", "cierto", VERIFICADO) == 15
    # Reportar algo verdadero perjudica injustamente; reportar algo falso con pruebas suma.
    assert valorar_accion("reportar", "cierto", VERIFICADO) == -20
    assert valorar_accion("reportar", "falso", DESMENTIDO) == 25
    # Ignorar no siempre es malo: sin pruebas, no amplificar no castiga.
    assert valorar_accion("ignorar", "falso", SIN_PRUEBAS) == 0
    assert valorar_accion("ignorar", "falso", DESMENTIDO) < 0
    # Insistir sabiendo que es falso es lo peor que se puede hacer.
    assert valorar_accion("insistir", "falso", DESMENTIDO) == -35


def test_gravedad_solo_escala_el_dano():
    assert valorar_accion("compartir", "falso", DESMENTIDO, "alta") < valorar_accion("compartir", "falso", DESMENTIDO, "baja")
    assert valorar_accion("compartir", "cierto", VERIFICADO, "alta") == valorar_accion("compartir", "cierto", VERIFICADO, "baja")


def test_alcance_real_ajusta_el_cambio():
    assert ajuste_por_alcance(-10, 3) == -13
    assert ajuste_por_alcance(-10, 50) == -15  # con tope
    assert ajuste_por_alcance(9, 7) == 11
    assert ajuste_por_alcance(0, 7) == 0


def test_decision_en_el_juego_depende_de_las_pruebas():
    con = Partida()
    con.campania.semilla = 4
    con.campania.reiniciar()
    sin = Partida()
    sin.campania.semilla = 4
    sin.campania.reiniciar()
    cambio_con = _decidir(con, ZONA_COLEGIO, *COMPARTIR, pruebas=3)
    cambio_sin = _decidir(sin, ZONA_COLEGIO, *COMPARTIR, pruebas=0)
    assert cambio_con.delta < cambio_sin.delta < 0
    assert "sabías" in cambio_con.mensaje and "mala intención" in cambio_sin.mensaje


def test_hospital_premia_compartir_lo_verdadero_y_castiga_reportarlo():
    bien = Partida()
    cambio = _decidir(bien, ZONA_HOSPITAL, *COMPARTIR)
    assert cambio.delta >= 15 and bien.campania.ultima_consecuencia.exito
    mal = Partida()
    cambio = _decidir(mal, ZONA_HOSPITAL, DERECHA, DERECHA, CONFIRMAR, DERECHA, CONFIRMAR, CONFIRMAR)
    assert cambio.delta <= -25 and not mal.campania.ultima_consecuencia.exito
    assert "denuncia falsa" in cambio.mensaje


def test_ninguna_opcion_es_correcta_en_todas_las_zonas():
    """El jugador no puede memorizar una respuesta: "Compartir" purifica una
    publicación verdadera y detona las engañosas."""
    resultados = {}
    for zona in (ZONA_COLEGIO, ZONA_HOSPITAL, ZONA_EMPRESA_MEDIOS):
        partida = Partida()
        _decidir(partida, zona, *COMPARTIR)
        resultados[zona] = partida.campania.ultima_consecuencia.exito
    assert resultados == {ZONA_COLEGIO: False, ZONA_HOSPITAL: True, ZONA_EMPRESA_MEDIOS: False}


def test_el_mensaje_siempre_existe_y_nombra_la_consecuencia():
    partida = Partida()
    cambio = _decidir(partida, ZONA_COLEGIO, *VERIFICAR_PUBLICAR)
    assert cambio.delta > 0 and cambio.mensaje and cambio.motivo == ZONA_COLEGIO
    assert partida.campania.ultima_consecuencia.reputacion == cambio.delta


def test_recompensa_de_zona_no_se_duplica_al_repetirla():
    partida = Partida()
    primero = _decidir(partida, ZONA_COLEGIO, *VERIFICAR_PUBLICAR)
    valor = partida.campania.reputacion
    _decidir(partida, ZONA_COLEGIO, *VERIFICAR_PUBLICAR, semilla=1)
    assert primero.delta > 0
    assert partida.campania.reputacion == valor


# --------------------------------------------------------------- consecuencias sociales


def test_reputacion_alta_trae_un_aporte_ciudadano_por_zona():
    c = Partida().campania
    assert c.aporte_ciudadano(ZONA_COLEGIO) is None
    c.rep(0).valor = 25
    nombre, evidencia = c.aporte_ciudadano(ZONA_HOSPITAL)
    assert nombre and evidencia["id"] == "hos_e1"
    assert c.aporte_ciudadano(ZONA_HOSPITAL) is None


def test_reputacion_cuestionada_exige_todas_las_pruebas():
    p = Partida()
    c = p.campania
    c.revelar_evidencia(ZONA_COLEGIO)
    assert c.estado_evidencia(ZONA_COLEGIO) == PARCIAL
    assert c.preparar_escenario(ZONA_COLEGIO).estado == PARCIAL
    c.rep(0).valor = -30
    escenario = c.preparar_escenario(ZONA_COLEGIO)
    assert escenario.estado == SIN_PRUEBAS and c.exige_mas_pruebas
    # Con todas las pruebas, una reputación cuestionada todavía puede decidir bien.
    c.revelar_evidencia(ZONA_COLEGIO)
    c.revelar_evidencia(ZONA_COLEGIO)
    assert c.preparar_escenario(ZONA_COLEGIO).estado == DESMENTIDO


def test_reputacion_de_referente_da_mas_tiempo_en_la_terminal():
    c = Partida().campania
    assert c.duracion_extra_terminal() == 0
    c.rep(0).valor = 70
    assert c.duracion_extra_terminal() > 0


def test_lineas_de_capitulo_cambian_con_la_reputacion():
    def textos(valor):
        p = Partida()
        p.campania.rep(0).valor = valor
        _, dialogo = p.campania.presentacion_zona(ZONA_HOSPITAL, "ciudadano", "Ciudadano")
        return " ".join(l.texto for l in dialogo.lineas)
    assert "confío en lo que vas a hacer" in textos(30)
    assert "No voy a pasarte nada" in textos(-30)
    neutral = textos(0)
    assert "confío" not in neutral and "No voy a pasarte" not in neutral


@pytest.mark.parametrize("valor, nivel", [(70, "referente"), (30, "confiable"), (0, "neutral"), (-30, "cuestionada"), (-70, "crisis")])
def test_reaccion_ciudadana_segun_nivel(valor, nivel):
    c = Partida().campania
    c.rep(0).valor = valor
    texto, nivel_real = c.reaccion_ciudadana()
    assert nivel_real == nivel and texto and "{" not in texto


def test_reaccion_negativa_nombra_a_quien_recibio_tu_rumor():
    c = Partida().campania
    c.rep(0).valor = -70
    c.red.expuestos = {"irene"}
    nombre = c.red.nombre("irene")
    assert nombre in c.reaccion_ciudadana()[0]


def test_titulares_reflejan_la_reputacion():
    c = Partida().campania
    c.rep(0).valor = -70
    assert any("críticas" in t for t in c.titulares())
    c.rep(0).valor = 70
    assert any("destacan" in t for t in c.titulares())


def test_elecciones_usan_la_reputacion_colectiva():
    c = Partida().campania
    c.rep(0).valor = 60
    c.rep(1).valor = -20
    assert c.reputacion_colectiva() == 20


# --------------------------------------------------------------- crisis


def test_crisis_se_activa_al_llegar_al_umbral_y_no_antes():
    r = ReputacionJugador()
    r.aplicar(UMBRAL_CRISIS_REPUTACION + 1)
    assert r.estado_crisis == SIN_CRISIS
    r.aplicar(-1)
    assert r.estado_crisis == CRISIS_PENDIENTE and r.crisis_pendiente


def test_una_cadena_de_decisiones_irresponsables_abre_la_crisis_en_el_juego():
    p = Partida()
    c = p.campania
    insistir = (CONFIRMAR, DERECHA, CONFIRMAR, CONFIRMAR)
    _decidir(p, ZONA_COLEGIO, *insistir)
    assert c.jugador_en_crisis() is None
    _decidir(p, ZONA_EMPRESA_MEDIOS, *insistir)
    assert c.jugador_en_crisis() == 0 and c.rep(0).valor <= UMBRAL_CRISIS_REPUTACION


def test_reinicio_de_partida_limpia_la_reputacion():
    p = Partida()
    p.campania.rep(0).aplicar(-80)
    p.campania.rep(1).aplicar(40)
    p.reiniciar()
    assert p.campania.reputacion == 0 and p.campania.jugador_en_crisis() is None
    assert p.campania.reputaciones == {} or all(r.valor == 0 for r in p.campania.reputaciones.values())


# --------------------------------------------------------------- multijugador


def test_cada_jugador_tiene_su_reputacion():
    p = Partida()
    c = p.campania
    c.registrar_actor(1)
    _decidir(p, ZONA_COLEGIO, *COMPARTIR)
    # preparar_escenario devolvió el actor al jugador local: quien confirma lo registra.
    p2 = Partida()
    c2 = p2.campania
    for _ in range(3):
        c2.revelar_evidencia(ZONA_COLEGIO)
    terminal = TerminalDecision(p2.fabrica_arbol(ZONA_COLEGIO)(), 15.0)
    terminal.iniciar()
    c2.registrar_actor(1)
    for paso in COMPARTIR:
        terminal.navegar(paso)
    p2.cerrar_mazmorra(_mazmorra_lista(ZONA_COLEGIO), terminal.resultado, terminal)
    assert c2.rep(1).valor < 0 and c2.rep(0).valor == 0


def test_quien_perdio_la_voz_no_decide_ni_cambia_su_reputacion():
    c = Partida().campania
    c.rep(1).valor = -80
    c.rep(1).estado_crisis = CRISIS_PENDIENTE
    c.rechazar_redencion(1)
    assert not c.puede_decidir(1) and c.puede_decidir(0)
    c.actor_decision = 0
    c.registrar_actor(1)
    assert c.actor_decision == 0
    assert c.rep(1).aplicar(-5) is None and c.rep(1).valor == -80


def test_sincronizacion_del_host_al_invitado():
    host = Partida().campania
    invitado = Partida().campania
    invitado.espejo = True
    host.rep(0).aplicar(-30, "Daño", "Colegio")
    host.rep(1).aplicar(-70, "Mucho daño", "Hospital")
    host.revelar_evidencia(ZONA_COLEGIO)
    host.soltar_evidencia(ZONA_COLEGIO, 3)
    host.estado.aplicar({"confianza": -5})
    host.red.expuestos = {"ana", "beto"}
    host.puntos = 77
    invitado.aplicar_resumen_red(host.resumen_red())
    assert invitado.rep(0).valor == -30 and invitado.rep(1).valor == -70
    assert invitado.rep(1).crisis_pendiente
    assert invitado.rep(1).tomar_pendiente().mensaje == "Mucho daño"  # el invitado también ve el aviso
    assert invitado.estado.valor("confianza") == host.estado.valor("confianza")
    assert invitado.evidencias_reveladas[ZONA_COLEGIO] == 1 and invitado.tomar_evidencia_nueva()["id"] == "col_e1"
    assert invitado.hay_evidencia_suelta(ZONA_COLEGIO, 3)
    assert invitado.red.expuestos == {"ana", "beto"} and invitado.puntos == 77
    # Un segundo snapshot igual no repite avisos.
    invitado.aplicar_resumen_red(host.resumen_red())
    assert invitado.rep(1).tomar_pendiente() is None


@pytest.mark.parametrize("basura", [None, "x", {"rep": "x"}, {"rep": {"a": 1}, "ind": 3, "evi": 5, "sue": 2, "exp": 9},
                                    {"rep": {"0": {"v": "mucho", "k": "z", "u": [1]}}}])
def test_datos_rotos_de_la_red_no_tumban_al_invitado(basura):
    c = Partida().campania
    c.aplicar_resumen_red(basura)
    assert c.reputacion == 0


# --------------------------------------------------------------- pruebas en el suelo


def test_la_prueba_queda_en_el_suelo_hasta_recogerla():
    c = Partida().campania
    assert c.soltar_evidencia(ZONA_COLEGIO, 2)
    assert not c.soltar_evidencia(ZONA_COLEGIO, 2)
    assert c.evidencias_reveladas.get(ZONA_COLEGIO, 0) == 0
    assert c.recoger_evidencia(ZONA_COLEGIO, 2)["id"] == "col_e1"
    assert c.recoger_evidencia(ZONA_COLEGIO, 2) is None
    assert c.evidencias_reveladas[ZONA_COLEGIO] == 1


def test_no_se_sueltan_mas_pruebas_de_las_que_tiene_la_zona():
    c = Partida().campania
    total = len(c.evidencias_de(ZONA_COLEGIO))
    sueltas = [c.soltar_evidencia(ZONA_COLEGIO, cuarto) for cuarto in range(total + 3)]
    assert sueltas.count(True) == total
