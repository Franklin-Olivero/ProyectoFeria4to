"""Modo Online, segunda parte del impostor: el expulsado como fantasma, el
fin de la partida por votación, el botón SABOTEAR (publicación viral), el
aviso de versión y la terminal que arma el invitado cuando llega tarde."""

import os
import time
from types import SimpleNamespace

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402
import pytest  # noqa: E402

from src.core import assets  # noqa: E402
from src.core.balance import (  # noqa: E402
    BLOQUEO_POST_SABOTAJE, COOLDOWN_POST_SABOTAJE, DURACION_POST_SABOTAJE, EFECTOS_POST_SABOTAJE_FRENADO,
    EFECTOS_POST_SABOTAJE_VIRAL, JUGADORES_MINIMOS_VICTORIA_IMPOSTOR,
)
from src.core.entrada import InputJugador  # noqa: E402
from src.core.equipo import jugador_mas_cercano, jugadores_en_combate, todos_caidos  # noqa: E402
from src.core.escenas import Escena  # noqa: E402
from src.dungeon.partida import Partida  # noqa: E402
from src.entities.candidato import Candidato  # noqa: E402
from src.entities.player import Ciudadano  # noqa: E402
from src.story import contenido  # noqa: E402
from src.ui.terminal_decision import (  # noqa: E402
    CONFIRMAR, DERECHA, DETONACION, IZQUIERDA, PURIFICACION_EXITOSA, construir_arbol_publicacion,
)
from Online import reunion_render  # noqa: E402
from Online.cliente import Cliente  # noqa: E402
from Online.post_sabotaje import ControlSabotajes, VistaSabotaje, vista_de_dict as vista_sabotaje  # noqa: E402
from Online.protocolo import DECISION_NAV, INPUT, SABOTAJE  # noqa: E402
from Online.reunion import EXPULSADO, GANA_IMPOSTOR, GANA_TRIPULACION, SALTAR, ControlReuniones, VistaReunion  # noqa: E402
from Online.servidor import Servidor  # noqa: E402
from Online.sesion_red import VERSION_ESTADO, AdaptadorOnlineHost, AdaptadorOnlineJoin, posts_sabotaje  # noqa: E402
from tests.test_presentacion_online import _tecla, correr  # noqa: E402,F401
from tests.test_reunion_online import _RedReunion, _impostor_j2  # noqa: E402


# ----------------------------------------------------------------------
# El expulsado es un fantasma
# ----------------------------------------------------------------------

def _equipo(cantidad=3):
    return [Ciudadano(100 + 40 * i, 100) for i in range(cantidad)]


def test_los_enemigos_no_ven_al_fantasma_y_no_sostiene_al_equipo():
    jugadores = _equipo()
    jugadores[0].expulsado = True
    assert jugadores[0] not in jugadores_en_combate(jugadores)
    assert jugador_mas_cercano((100, 100), jugadores) is not jugadores[0]  # el más cercano es el fantasma
    for jugador in jugadores[1:]:
        jugador.vida = 0
    assert todos_caidos(jugadores)  # el fantasma sigue "vivo", pero no cuenta


def test_al_fantasma_no_le_entra_ningun_golpe():
    fantasma = Ciudadano(0, 0)
    fantasma.expulsado = True
    vida = fantasma.vida
    fantasma.recibir_dano(50)
    assert fantasma.vida == vida


class _Lector:
    def __init__(self, pedido):
        self.pedido = pedido

    def leer(self):
        return self.pedido


def test_el_fantasma_camina_pero_no_dispara_ni_usa_habilidad_ni_dash():
    import Main
    from src.dungeon.mazmorra import Mazmorra
    from src.dungeon.mazmorra_jugable import MazmorraJugable
    pygame.display.init()
    pygame.display.set_mode((1280, 720))
    jugadores = [Ciudadano(0, 0), Candidato(0, 0)]
    mazmorra = MazmorraJugable(Mazmorra(Partida().ciudad.reportes("Colegio"), "Colegio", semilla=3))
    mazmorra.colocar_en_entrada(jugadores)
    fantasma = jugadores[0]
    fantasma.expulsado = True
    fantasma.carga_habilidad = 10 ** 6
    x_antes = fantasma.posicion.x
    proyectiles = [[], []]
    pedido = InputJugador(movimiento=(1.0, 0.0), disparando=True, habilidad=True, dash=True)
    for _ in range(10):
        Main._frame_de_combate(0.05, jugadores, [_Lector(pedido), _Lector(InputJugador())], mazmorra, proyectiles, [],
                               SimpleNamespace(agregar=lambda *a, **k: None), SimpleNamespace(emitir=lambda *a: None))
    assert fantasma.posicion.x > x_antes  # camina
    assert proyectiles[0] == [] and not fantasma.dash.activo  # pero no pelea


# ----------------------------------------------------------------------
# Fin de la partida por votación
# ----------------------------------------------------------------------

def _votacion(total, expulsados_antes, votos, impostor):
    control = ControlReuniones(recarga=0, duracion=60, duracion_resultado=1)
    control.expulsados.update(expulsados_antes)
    activos = list(range(total))
    assert control.convocar(next(i for i in activos if i not in control.expulsados), activos)
    for votante, objetivo in votos.items():
        control.votar(votante, objetivo)
    control.actualizar(60.0, es_impostor=lambda i: i == impostor, total=total)
    return control


@pytest.mark.parametrize("total", [2, 3, 4])
def test_expulsar_al_impostor_gana_la_tripulacion_con_cualquier_cantidad(total):
    votos = {i: 1 for i in range(total) if i != 1}
    control = _votacion(total, (), votos, impostor=1)
    assert control.fin == GANA_TRIPULACION and control.impostor == 1 and control.en_curso


def test_con_tres_jugadores_expulsar_un_inocente_le_da_la_victoria_al_impostor():
    assert JUGADORES_MINIMOS_VICTORIA_IMPOSTOR == 2
    control = _votacion(3, (), {0: 2, 1: 2}, impostor=1)
    assert control.expulsados == {2} and control.fin == GANA_IMPOSTOR and control.impostor == 1


def test_con_cuatro_jugadores_hacen_falta_dos_inocentes():
    primera = _votacion(4, (), {0: 3, 1: 3, 2: 3}, impostor=1)
    assert primera.fin is None and primera.expulsados == {3}
    segunda = _votacion(4, (3,), {0: 2, 1: 2}, impostor=1)
    assert segunda.fin == GANA_IMPOSTOR


def test_con_dos_jugadores_si_el_impostor_queda_en_pie_gana_al_instante():
    control = _votacion(2, (), {1: 0}, impostor=1)
    assert control.expulsados == {0} and control.fin == GANA_IMPOSTOR and control.impostor == 1


def test_con_dos_jugadores_un_empate_no_termina_nada():
    control = _votacion(2, (), {0: 1, 1: 0}, impostor=1)
    assert control.expulsados == set() and control.fin is None


def test_terminada_la_partida_nada_mas_corre_ni_se_convoca():
    control = _votacion(3, (), {0: 1, 2: 1}, impostor=1)
    recarga = control.recarga_restante
    control.actualizar(100.0, total=3)
    assert control.recarga_restante == recarga and not control.puede_convocar(0, [0, 2])
    datos = control.a_dict()
    assert datos["fin"] == GANA_TRIPULACION and datos["impostor"] == 1


def test_los_textos_del_final_dependen_de_quien_mira():
    assert reunion_render.textos_fin(GANA_TRIPULACION, False)[1:] == ("Has descubierto al impostor", "Civitas se ha salvado")
    assert reunion_render.textos_fin(GANA_IMPOSTOR, False)[:2] == ("El impostor quedó en pie", "y él destruyó Civitas")
    assert reunion_render.textos_fin(GANA_IMPOSTOR, True) == (
        "¡Felicidades!", "Has eliminado a los demás jugadores", "Has destruido Civitas con éxito")
    assert reunion_render.textos_fin(GANA_TRIPULACION, True)[0] == "Te descubrieron"


@pytest.mark.parametrize("fin, local", [(GANA_TRIPULACION, 0), (GANA_TRIPULACION, 1), (GANA_IMPOSTOR, 0), (GANA_IMPOSTOR, 1)])
def test_dibujar_el_final(fin, local):
    pygame.font.init()
    pantalla = pygame.Surface((1280, 720))
    vista = VistaReunion(fin=fin, impostor=1, expulsado=1, motivo=EXPULSADO, votos=((0, 1),))
    reunion_render.dibujar_fin_partida(pantalla, vista, [Ciudadano(0, 0), Candidato(0, 0)], local, 1.2)


# ----------------------------------------------------------------------
# La publicación del botón SABOTEAR, sola
# ----------------------------------------------------------------------

def test_lo_que_se_pidio_poco_tiempo_y_el_impostor_espera_un_poco():
    assert DURACION_POST_SABOTAJE <= 30 and 0 < BLOQUEO_POST_SABOTAJE < DURACION_POST_SABOTAJE
    assert COOLDOWN_POST_SABOTAJE > 0


def test_el_boton_espera_al_empezar_y_despues_de_cada_sabotaje():
    control = ControlSabotajes(4, recarga=75)
    assert not control.sabotear()
    control.actualizar(75)
    assert control.sabotear() and control.activo and control.numero == 1
    assert not control.sabotear()  # ya hay una
    control.navegar(CONFIRMAR)  # Verificar: la frenan
    cerrado = control.actualizar(0.1)
    assert cerrado == {"res": PURIFICACION_EXITOSA, "op": "Verificar", "i": control.resultado["i"]}
    assert control.en_curso and not control.activo and control.recarga_restante == 75
    assert control.actualizar(control.duracion_resultado) is None and not control.en_curso
    control.actualizar(74)
    assert not control.sabotear()


def test_el_impostor_elige_recien_despues_de_su_bloqueo_y_puede_elegir_una_mala():
    control = ControlSabotajes(1, recarga=0, bloqueo=5)
    control.sabotear()
    assert not control.navegar(DERECHA, es_impostor=True)
    control.actualizar(5.0)
    assert control.navegar(DERECHA, es_impostor=True)  # Me gusta
    assert control.navegar(CONFIRMAR, es_impostor=True)
    assert control.actualizar(0.0)["res"] == DETONACION


def test_la_tripulacion_elige_desde_el_primer_segundo():
    control = ControlSabotajes(1, recarga=0)
    control.sabotear()
    for direccion in (DERECHA, DERECHA, DERECHA, CONFIRMAR):  # Reportar
        assert control.navegar(direccion)
    assert control.actualizar(0.0) == {"res": PURIFICACION_EXITOSA, "op": "Reportar", "i": 0}


def test_si_nadie_elige_el_rumor_se_vuelve_viral():
    control = ControlSabotajes(1, recarga=0, duracion=20)
    control.sabotear()
    assert control.actualizar(19.9) is None
    assert control.actualizar(0.2) == {"res": DETONACION, "op": None, "i": 0}


def test_no_repite_publicacion_hasta_usarlas_todas():
    import random
    control = ControlSabotajes(4, recarga=0, duracion_resultado=0, azar=random.Random(3))
    vistas = []
    for _ in range(4):
        control.sabotear()
        vistas.append(control.indice_post)
        control.navegar(CONFIRMAR)
        control.actualizar(0.0)
        control.recarga_restante = 0
    assert sorted(vistas) == [0, 1, 2, 3]


def test_la_vista_viaja_y_tolera_basura():
    control = ControlSabotajes(2, recarga=0)
    control.sabotear()
    control.navegar(DERECHA)
    control.actualizar(3.0)
    vista = vista_sabotaje(control.a_dict())
    assert vista.activo and vista.seleccion == 1 and vista.nodo == 0 and vista.bloqueo == pytest.approx(2.0)
    assert vista.restante == pytest.approx(17.0) and vista.en_curso
    vista = vista_sabotaje({"rcd": "x", "post": {"i": -1}, "res": {"res": "otra cosa"}})
    assert vista == VistaSabotaje(recarga=COOLDOWN_POST_SABOTAJE)
    assert vista_sabotaje(None) == VistaSabotaje()


def test_las_publicaciones_del_contenido_son_validas():
    posts = posts_sabotaje()
    assert len(posts) >= 3
    for post in posts:
        assert all(post[clave] for clave in contenido.CLAVES_POST)
    datos = dict(contenido.cargar())
    datos["sabotajes"] = [{"usuario": "@x"}]
    with pytest.raises(contenido.ContenidoInvalido):
        contenido.validar(datos)


# ----------------------------------------------------------------------
# El host y el invitado
# ----------------------------------------------------------------------

class _ServidorFalso:
    def __init__(self):
        self.cola = []

    def leer_mensajes(self):
        mensajes, self.cola = self.cola, []
        return mensajes


def _host(impostor=1, escena=Escena.MAZMORRA):
    host = AdaptadorOnlineHost(_ServidorFalso(), ids_red=[0, 1, 2])
    host.sabotajes = ControlSabotajes(len(posts_sabotaje()), recarga=0)
    host.reuniones = ControlReuniones(recarga=0)
    jugadores = [Ciudadano(0, 0), Candidato(0, 0), Ciudadano(0, 0)]
    jugadores[impostor].es_impostor = True
    host._preparar_frame(SimpleNamespace(), None, jugadores)
    host._escena = escena
    return host


def test_solo_el_impostor_sabotea_y_con_el_mundo_en_marcha():
    assert not _host().sabotear(0)  # un tripulante
    assert not _host(escena=Escena.DECISION).sabotear(1)  # en la terminal ya hay decisión
    expulsado = _host()
    expulsado.reuniones.expulsados.add(1)
    assert not expulsado.sabotear(1)
    en_reunion = _host()
    en_reunion.convocar_reunion(0)
    assert not en_reunion.sabotear(1)
    host = _host()
    host.servidor.cola.append({"tipo": SABOTAJE, "id": 1})
    host._procesar_mensajes()
    assert host.sabotajes.activo
    assert not host.convocar_reunion(0)  # con la publicación en curso no hay reunión


def test_las_teclas_de_todos_van_a_la_publicacion_y_el_impostor_espera():
    host = _host()
    host.sabotear(1)
    for id_red, direccion in ((1, DERECHA), (2, DERECHA), (2, DERECHA)):
        host.servidor.cola.append({"tipo": DECISION_NAV, "dir": direccion, "id": id_red})
    host._procesar_mensajes()
    assert host.sabotajes.terminal.indice_seleccionado == 2  # el del impostor no contó
    assert host._solicitudes_decision == []  # no fue a la terminal de la mazmorra
    host.reuniones.expulsados.add(0)
    assert not host.navegar_sabotaje(0, DERECHA)


def test_quien_perdio_la_voz_tampoco_elige_en_la_publicacion():
    host = _host()
    host._partida = SimpleNamespace(campania=SimpleNamespace(puede_decidir=lambda indice: indice != 0))
    host.sabotear(1)
    assert not host.navegar_sabotaje(0, DERECHA)
    assert host.navegar_sabotaje(2, DERECHA)


def _partida():
    partida = Partida()
    partida.campania.prologo_visto = True
    return partida


@pytest.mark.parametrize("pasos, frenada", [((CONFIRMAR,), True), ((DERECHA, CONFIRMAR), False)])
def test_el_host_aplica_los_efectos_una_sola_vez(pasos, frenada):
    host = _host()
    partida = _partida()
    antes = dict(partida.campania.estado.como_dict())
    colapso = partida.colapso.valor
    host.sabotear(1)
    for paso in pasos:
        host.navegar_sabotaje(0, paso)
    for _ in range(3):
        host.actualizar(Escena.MAZMORRA, None, None, 0.0, 0.1, SimpleNamespace(), partida, host._jugadores, None)
    despues = partida.campania.estado.como_dict()
    efectos = EFECTOS_POST_SABOTAJE_FRENADO if frenada else EFECTOS_POST_SABOTAJE_VIRAL
    for indicador, delta in efectos.items():
        assert despues[indicador] - antes[indicador] == pytest.approx(delta, abs=1)
    assert (partida.colapso.valor > colapso) == (not frenada)


def test_el_invitado_refleja_la_publicacion_y_manda_sus_teclas():
    enviados = []
    cliente = SimpleNamespace(conectado=True, enviar_decision_nav=enviados.append,
                              enviar_sabotaje=lambda: enviados.append("sabotaje"))
    invitado = AdaptadorOnlineJoin(cliente, id_local=1, ids_red=[0, 1])
    jugadores = [Ciudadano(0, 0), Candidato(0, 0)]
    jugadores[1].es_impostor = True
    invitado._preparar_frame(SimpleNamespace(), None, jugadores)
    partida = SimpleNamespace(colapso=SimpleNamespace(valor=0.0),
                              campania=SimpleNamespace(aplicar_resumen_red=lambda datos: None))
    assert invitado.sabotear(1) and enviados == ["sabotaje"]
    control = ControlSabotajes(len(posts_sabotaje()), recarga=0)
    control.sabotear()
    control.navegar(DERECHA)
    invitado._aplicar({"sbp": control.a_dict(), "v": VERSION_ESTADO}, Escena.MAZMORRA, None, None, partida, jugadores)
    terminal = invitado.terminal_sabotaje()
    assert invitado.estado_sabotaje().activo and terminal.indice_seleccionado == 1
    assert invitado.evento_red_en_curso() and invitado.post_sabotaje(control.indice_post) is not None
    assert not invitado.navegar_sabotaje(1, CONFIRMAR)  # él es el impostor y sigue bloqueado
    control.actualizar(BLOQUEO_POST_SABOTAJE)
    invitado._aplicar({"sbp": control.a_dict()}, Escena.MAZMORRA, None, None, partida, jugadores)
    assert invitado.navegar_sabotaje(1, CONFIRMAR) and enviados[-1] == CONFIRMAR
    terminal.navegar(IZQUIERDA)  # la copia está congelada: solo la mueve el host
    assert terminal.indice_seleccionado == 1
    invitado._aplicar({}, Escena.MAZMORRA, None, None, partida, jugadores)
    assert invitado.terminal_sabotaje() is None and not invitado.evento_red_en_curso()


def _esperar(condicion, limite_s=5.0):
    fin = time.monotonic() + limite_s
    while time.monotonic() < fin:
        if condicion():
            return True
        time.sleep(0.02)
    return condicion()


def test_por_red_el_invitado_impostor_sabotea_y_el_host_navega():
    servidor = Servidor()
    assert servidor.iniciar(0, interfaz="127.0.0.1") is not None
    cliente = Cliente()
    try:
        assert cliente.conectar("127.0.0.1", servidor.puerto)
        assert _esperar(lambda: cliente.id_jugador == 1)
        host = AdaptadorOnlineHost(servidor, ids_red=[0, 1])
        host.sabotajes = ControlSabotajes(len(posts_sabotaje()), recarga=0)
        jugadores = [Ciudadano(0, 0), Candidato(0, 0)]
        jugadores[1].es_impostor = True
        host._preparar_frame(SimpleNamespace(), None, jugadores)
        host._escena = Escena.CIUDAD
        cliente.enviar_sabotaje()
        assert _esperar(lambda: host._procesar_mensajes() or host.sabotajes.activo)
        assert host.navegar_sabotaje(0, DERECHA)
        assert host.navegar_sabotaje(0, DERECHA)
        assert host.navegar_sabotaje(0, DERECHA)
        assert host.navegar_sabotaje(0, CONFIRMAR)  # la tripulación reporta a tiempo
        assert host.sabotajes.actualizar(0.0)["res"] == PURIFICACION_EXITOSA
    finally:
        cliente.detener()
        servidor.detener()


# ----------------------------------------------------------------------
# Aviso de versión y terminal del invitado que llega tarde
# ----------------------------------------------------------------------

def test_el_host_avisa_si_un_invitado_tiene_otra_version():
    host = _host()
    assert host.aviso_version() is None
    host.servidor.cola.append({"tipo": INPUT, "id": 1, "input": {"v": VERSION_ESTADO}})
    host.servidor.cola.append({"tipo": INPUT, "id": 2, "input": {}})  # código viejo: no manda versión
    host._procesar_mensajes()
    assert "J3" in host.aviso_version()


def test_el_invitado_avisa_si_el_host_tiene_otra_version():
    invitado, _, partida, jugadores = _invitado_simple()
    invitado._aplicar({"v": VERSION_ESTADO}, Escena.CIUDAD, None, None, partida, jugadores)
    assert invitado.aviso_version() is None
    invitado._aplicar({"v": VERSION_ESTADO - 1}, Escena.CIUDAD, None, None, partida, jugadores)
    assert "host" in invitado.aviso_version()


def _invitado_simple():
    cliente = SimpleNamespace(conectado=True, enviar_input=lambda datos: None)
    invitado = AdaptadorOnlineJoin(cliente, id_local=1, ids_red=[0, 1])
    jugadores = [Ciudadano(0, 0), Candidato(0, 0)]
    invitado._preparar_frame(SimpleNamespace(), None, jugadores)
    partida = SimpleNamespace(colapso=SimpleNamespace(valor=0.0),
                              campania=SimpleNamespace(aplicar_resumen_red=lambda datos: None))
    return invitado, cliente, partida, jugadores


def test_el_invitado_manda_su_version_en_cada_input():
    enviados = []
    invitado, cliente, _, _ = _invitado_simple()
    cliente.enviar_input = enviados.append
    invitado.enviar_input(InputJugador())
    assert enviados[-1]["v"] == VERSION_ESTADO


def test_el_invitado_que_llega_tarde_arma_la_terminal_de_la_historia():
    invitado, _, _, _ = _invitado_simple()
    partida = _partida()
    arbol_historia = partida.fabrica_arbol("Colegio")
    cuarto = SimpleNamespace(terminal=None, fase=None, fabrica_arbol=arbol_historia, duracion_terminal=45.0)
    escena = invitado._seguir_decision(SimpleNamespace(cuarto=cuarto), {"nodo": 0, "idx": 0, "t": 40.0})
    assert escena == Escena.DECISION
    etiquetas = [hijo.etiqueta for hijo in cuarto.terminal.arbol.raiz.hijos]
    assert etiquetas == [hijo.etiqueta for hijo in arbol_historia().raiz.hijos]
    assert cuarto.terminal.arbol.raiz.etiqueta != construir_arbol_publicacion().raiz.etiqueta  # no el árbol fijo
    assert cuarto.terminal.descender_resultados


# ----------------------------------------------------------------------
# En el loop real de Main
# ----------------------------------------------------------------------

class _RedCompleta(_RedReunion):
    """La red falsa de las reuniones, más el botón SABOTEAR (como el host)."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.sabotajes = ControlSabotajes(len(posts_sabotaje()), recarga=0, duracion_resultado=0.2)

    def actualizar(self, escena, arena, mazmorra, fundido, dt, sesion, partida, jugadores, jugador):
        self.sabotajes.actualizar(dt)
        return super().actualizar(escena, arena, mazmorra, fundido, dt, sesion, partida, jugadores, jugador)

    def sabotear(self, indice):
        return getattr(self.jugadores[indice], "es_impostor", False) and self.sabotajes.sabotear()

    def navegar_sabotaje(self, indice, direccion):
        return self.sabotajes.navegar(direccion, getattr(self.jugadores[indice], "es_impostor", False))

    def estado_sabotaje(self):
        return vista_sabotaje(self.sabotajes.a_dict())

    def terminal_sabotaje(self):
        return self.sabotajes.terminal

    def post_sabotaje(self, indice_post):
        return posts_sabotaje()[indice_post]

    def evento_red_en_curso(self):
        return self.reuniones.en_curso or self.sabotajes.en_curso


def _impostor_local(sesion):
    sesion.jugadores[sesion.id_local].es_impostor = True
    sesion.partida.campania.intros_vistas.add("Colegio")


def test_q_del_impostor_lanza_la_publicacion_y_las_flechas_la_mueven(correr):
    red = _RedCompleta(cuando=10_000, espejo=False)
    vistos = {}

    def guion(n, loc):
        if n == 3:
            _tecla(pygame.K_q)
        if n == 5:
            vistos["activa"] = red.sabotajes.activo
            vistos["pantalla"] = pygame.display.get_surface().copy()
            _tecla(pygame.K_RIGHT)  # el impostor todavía está bloqueado
        if n == 7:
            vistos["bloqueado"] = (red.sabotajes.terminal.indice_seleccionado, loc["aviso_sabotaje"] > 0)
            red.sabotajes.bloqueo_restante = 0.0
            _tecla(pygame.K_RIGHT)
            _tecla(pygame.K_RETURN)  # Me gusta: la vuelve viral
        if n == 9:
            vistos["resultado"] = (red.sabotajes.resultado or {}).get("res")
            return True
        return False

    correr(red, guion, id_local=0, preparar=_impostor_local)
    assert vistos["activa"] and vistos["bloqueado"] == (0, True) and vistos["resultado"] == DETONACION
    rect = pygame.Rect(assets.RECT_CELULAR_FEED)
    assert vistos["pantalla"].get_at((rect.left + 2, rect.centery))[:3] != (0, 0, 0)  # se dibujó el celular


def test_un_tripulante_no_tiene_boton_sabotear(correr):
    red = _RedCompleta(cuando=10_000, espejo=False)

    def guion(n, loc):
        if n == 3:
            _tecla(pygame.K_q)
        return n >= 5

    correr(red, guion, id_local=0, preparar=_impostor_j2)  # el impostor es J2, esta PC es J1
    assert not red.sabotajes.activo and red.sabotajes.numero == 0


def test_la_publicacion_detiene_el_combate(correr, monkeypatch):
    import Main
    combate = []
    original = Main._frame_de_combate
    monkeypatch.setattr(Main, "_frame_de_combate", lambda *a, **k: combate.append(1) or original(*a, **k))
    red = _RedCompleta(cuando=3, espejo=False)
    vistos = {}

    def guion(n, loc):
        if n == 30:
            vistos["antes"] = len(combate)
            red.sabotajes.sabotear()
        if n == 45:
            vistos["durante"] = len(combate)
            return True
        return False

    correr(red, guion, id_local=0, preparar=_impostor_j2)
    assert vistos["antes"] > 0 and vistos["durante"] == vistos["antes"]


def test_al_terminar_la_partida_enter_vuelve_al_menu_tras_unos_segundos(correr):
    import Main
    red = _RedCompleta(cuando=10_000, espejo=False)
    vistos = {}

    def guion(n, loc):
        if n == 3:
            red.reuniones.fin, red.reuniones.impostor = GANA_TRIPULACION, 1
        if n == 10:
            _tecla(pygame.K_RETURN)  # muy pronto: no sale
        if n == 20:
            vistos["sigue"] = True
        if n == 160:
            _tecla(pygame.K_RETURN)
        return False

    sesion, cuadros = correr(red, guion, id_local=0, preparar=_impostor_j2, maximo=400)
    assert vistos.get("sigue") and 160 <= cuadros < 400
    assert getattr(sesion, "partida_online_terminada", False)
    assert Main.MENU == "menu"


def test_los_demas_no_ven_el_panel_del_fantasma_pero_el_si(correr):
    red = _RedCompleta(cuando=3, espejo=False)
    red.reuniones.expulsados.add(1)
    vistos = {}

    def guion(n, loc):
        if n == 30:
            vistos["pantalla"] = pygame.display.get_surface().copy()
            vistos["fantasma"] = loc["jugadores"][1].expulsado
            return True
        return False

    correr(red, guion, id_local=0, preparar=_impostor_j2)
    assert vistos["fantasma"]
    rect = pygame.Rect(assets.RECTS_PANEL_JUGADOR[1])
    color_j2 = Candidato.COLOR
    bordes = sum(vistos["pantalla"].get_at((x, rect.top + 1))[:3] == color_j2 for x in range(rect.left, rect.right))
    assert bordes == 0  # el panel de J2 (fantasma) no se dibujó en la PC de J1
