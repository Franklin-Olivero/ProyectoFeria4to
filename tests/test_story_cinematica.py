"""Cinemáticas, misiones y capa de interfaz del modo historia (sin ventana)."""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.core.balance import REPORTES_POR_ZONA, ZONA_COLEGIO  # noqa: E402
from src.dungeon.mazmorra import Mazmorra  # noqa: E402
from src.dungeon.partida import Partida  # noqa: E402
from src.story import cinematica as cine  # noqa: E402
from src.story.misiones import RastreadorMisiones, mision_actual, mision_ciudad, mision_mazmorra, siguiente_zona  # noqa: E402
from src.ui.elecciones_render import fraccion_conteo  # noqa: E402
from src.ui.layout import fraccion_entrada, modal_prioritario, recortar_lineas  # noqa: E402
from src.ui.menu_principal import EXTRAS, VER_INTRO, VISTA_MENU, MenuPrincipal  # noqa: E402
from src.ui.navegacion import CONFIRMAR, VOLVER  # noqa: E402
from src.core.preferencias import Preferencias  # noqa: E402


# ----------------------------------------------------------------------
# Cinematica
# ----------------------------------------------------------------------


def test_intro_tiene_las_escenas_del_guion_y_termina_en_objetivos():
    partida = Partida()
    c = partida.campania.cinematica_intro("periodista", "Periodista")
    ids = [t.id for t in c.tomas]
    assert ids[:5] == ["ciudad", "civitas", "grieta", "caos", "amenaza"]
    assert ids[-1] == "objetivos" and c.tomas[-1].espera and len(c.tomas[-1].objetivos) == 5
    protagonista = next(t for t in c.tomas if t.id == "protagonista")
    assert protagonista.hablante == "Periodista" and protagonista.retrato == "periodista"
    assert "documentarlo" in protagonista.texto  # variante por rol
    # En avance automático dura entre 75 y 110 s sin contar los objetivos.
    c.configurar_lectura(modo=cine.MODO_AUTOMATICO)
    assert 75 <= sum(c.duracion_efectiva(t) or 0 for t in c.tomas) <= 110
    # La intro cuenta como prólogo visto: ni se repite ni aparece el prólogo en texto.
    assert partida.campania.cinematica_intro() is None
    assert partida.campania.dialogo_prologo() is None


def test_las_tomas_avanzan_solas_y_enter_salta_a_la_siguiente():
    c = cine.Cinematica([cine.Toma("a", 1.0), cine.Toma("b", 2.0), cine.Toma("fin", cine.ESPERA_ENTER)])
    assert c.actual.id == "a"
    c.actualizar(0.5)
    assert c.actual.id == "a" and abs(c.fraccion - 0.5) < 1e-9
    c.actualizar(0.6)
    assert c.actual.id == "b"
    c.avanzar()
    assert c.actual.id == "fin" and c.fraccion == 0.0
    c.actualizar(100)  # una toma que espera Enter no avanza sola
    assert c.actual.id == "fin" and not c.terminada
    c.avanzar()
    assert c.terminada and c.actual is None


def test_saltar_respeta_la_pantalla_de_objetivos():
    c = cine.Cinematica([cine.Toma("a", 1.0), cine.Toma("b", 2.0), cine.Toma("fin", cine.ESPERA_ENTER)])
    c.saltar()
    assert not c.terminada and c.actual.id == "fin"
    c.saltar()
    assert c.terminada
    sin_objetivos = cine.Cinematica([cine.Toma("a", 1.0), cine.Toma("b", 2.0)])
    sin_objetivos.saltar()
    assert sin_objetivos.terminada


def test_los_sonidos_de_toma_se_entregan_una_sola_vez():
    c = cine.Cinematica([cine.Toma("a", 1.0, sonido="viral"), cine.Toma("b", 1.0, sonido="glitch")])
    assert c.tomar_sonido() == "viral" and c.tomar_sonido() is None
    c.avanzar()
    assert c.tomar_sonido() == "glitch"


def test_presentacion_de_zona_tarjeta_y_dialogo_una_sola_vez():
    partida = Partida()
    tarjeta, dialogo = partida.campania.presentacion_zona(ZONA_COLEGIO, "candidato", "Candidato")
    assert tarjeta.tomas[0].efecto == cine.EFECTO_TARJETA and tarjeta.tomas[0].superior == "CAPÍTULO 1"
    assert dialogo is not None and "doble" in dialogo.lineas[1].texto  # variante del Candidato
    assert partida.campania.presentacion_zona(ZONA_COLEGIO) == (None, None)
    jefe, sin_dialogo = partida.campania.presentacion_zona("Alcaldía")
    assert sin_dialogo is None and jefe.tomas[-1].efecto == cine.EFECTO_TARJETA
    assert "0 de 3" in jefe.tomas[1].texto


def test_guiones_de_cierre_segun_el_final():
    for clave in ("renace", "dividida", "arquitecto"):
        c = cine.guion_final(clave, "Título", "Texto")
        assert c.tomas[0].efecto == cine.EFECTO_TARJETA and c.tomas[-1].espera
    assert cine.guion_caida_servidor().tomas[0].hablante == cine.HABLANTE_NOVA
    assert cine.guion_derrota_global().tomas[0].efecto == cine.EFECTO_GLITCH


# ----------------------------------------------------------------------
# Misiones
# ----------------------------------------------------------------------


def test_mision_de_la_ciudad_apunta_a_la_siguiente_zona_pendiente():
    partida = Partida()
    campania = partida.campania
    mision = mision_ciudad(campania, partida)
    assert mision.titulo == "INVESTIGA EL COLEGIO"
    assert mision.objetivo_pendiente.id == "purificar_Colegio"
    assert not next(o for o in mision.objetivos if o.id == "alcaldia").activo
    # Purificar el Colegio mueve la misión al Hospital.
    from src.ui.terminal_decision import CONFIRMAR as OK, TerminalDecision
    for _ in range(3):
        campania.revelar_evidencia(ZONA_COLEGIO)  # con las 3 pruebas la aclaración purifica
    escenario = campania.preparar_escenario(ZONA_COLEGIO)
    terminal = TerminalDecision(escenario.arbol, 15)
    terminal.iniciar()
    for _ in range(3):
        terminal.navegar(OK)  # Verificar -> Publicar aclaración -> hoja
    consecuencia = escenario.consecuencia_para(terminal)
    assert consecuencia.exito
    campania.aplicar_consecuencia(ZONA_COLEGIO, consecuencia)
    assert siguiente_zona(campania) == "Hospital"
    assert mision_ciudad(campania, partida).titulo == "INVESTIGA EL HOSPITAL"


def test_mision_de_mazmorra_muestra_progreso_real_y_el_rastreador_avisa_solo_novedades():
    partida = Partida()
    m = Mazmorra(REPORTES_POR_ZONA[ZONA_COLEGIO], ZONA_COLEGIO, semilla=3)
    mision = mision_mazmorra(partida.campania, m)
    cuartos = next(o for o in mision.objetivos if o.id == "cuartos")
    assert cuartos.progreso == "1/5" and not cuartos.hecho  # la entrada ya cuenta
    assert next(o for o in mision.objetivos if o.id == "pruebas").progreso == "0/3"
    rastreador = RastreadorMisiones()
    assert rastreador.novedades(mision) == []  # primera vez: solo registra
    for cuarto in m.grafo.nodos():
        if cuarto != m.cuarto_final:
            m.limpiados.add(cuarto)
    for _ in range(3):
        partida.campania.revelar_evidencia(ZONA_COLEGIO)
    nuevos = rastreador.novedades(mision_mazmorra(partida.campania, m))
    assert {o.id for o in nuevos} == {"cuartos", "pruebas"}
    assert rastreador.novedades(mision_mazmorra(partida.campania, m)) == []
    # La misión se deriva de la escena: en la ciudad vuelve a ser la de la campaña.
    assert mision_actual("ciudad", partida.campania, partida, m).titulo == "INVESTIGA EL COLEGIO"
    assert mision_actual("decision", partida.campania, partida, m).pista.startswith("Elige")


# ----------------------------------------------------------------------
# Capa de interfaz y menú
# ----------------------------------------------------------------------


def test_helpers_puros_de_layout():
    assert modal_prioritario({"estado", "dialogo"}) == "dialogo"
    assert modal_prioritario({"cinematica", "ayuda"}) == "cinematica"
    assert modal_prioritario(set()) is None
    assert fraccion_entrada(0) == 0 and fraccion_entrada(10) == 1
    assert recortar_lineas(["a", "b", "c"], 2) == ["a", "b…"]
    assert recortar_lineas(["a"], 3) == ["a"]
    assert fraccion_conteo(0) == 0 and fraccion_conteo(99) == 1


def test_extras_permite_volver_a_ver_la_introduccion():
    menu = MenuPrincipal(False, Preferencias())
    menu.confirmar(EXTRAS)
    while menu.actualizar(1 / 60) is None and menu.pulsado is not None:
        pass
    assert menu.vista != VISTA_MENU
    assert menu.accion(CONFIRMAR) is not None
    assert menu.actualizar(1 / 60) == VER_INTRO
    assert menu.vista == VISTA_MENU
    menu.confirmar(EXTRAS)
    while menu.pulsado is not None:
        menu.actualizar(1 / 60)
    assert menu.accion(VOLVER) is not None and menu.vista == VISTA_MENU
