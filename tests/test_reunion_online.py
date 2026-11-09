"""Reunión de emergencia del modo Online: la votación pura, el host que la
lleva, el invitado que la refleja, la red de verdad, el loop real de Main
(tecla R, clic, chat, votos, mundo en pausa) y el dibujo."""

import os
import time
from types import SimpleNamespace

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402
import pytest  # noqa: E402

from src.core import assets  # noqa: E402
from src.core.balance import (  # noqa: E402
    COOLDOWN_REUNION, DURACION_REUNION, MAX_LARGO_MENSAJE_REUNION, MAX_MENSAJES_REUNION,
)
from src.core.escenas import Escena  # noqa: E402
from src.entities.candidato import Candidato  # noqa: E402
from src.entities.player import Ciudadano  # noqa: E402
from src.ui import dibujo  # noqa: E402
from src.ui.terminal_decision import CONFIRMAR, DERECHA, TerminalDecision, construir_arbol_publicacion  # noqa: E402
from Online import reunion_render  # noqa: E402
from Online.cliente import Cliente  # noqa: E402
from Online.protocolo import DECISION_NAV, DESCONEXION, REUNION  # noqa: E402
from Online.reunion import (  # noqa: E402
    CONVOCAR, EMPATE, ESCRIBIR, EXPULSADO, SALTADA, SALTAR, SIN_VOTOS, VOTAR,
    ControlReuniones, Reunion, VistaReunion, contar_votos, limpiar_mensaje, vista_de_dict,
)
from Online.servidor import Servidor  # noqa: E402
from Online.sesion_red import AdaptadorOnlineHost, AdaptadorOnlineJoin  # noqa: E402
from tests.test_presentacion_online import _Red, _tecla, correr  # noqa: E402,F401


def test_lo_pedido_un_minuto_para_hablar_y_el_boton_cada_60_segundos():
    assert COOLDOWN_REUNION == 60.0 and DURACION_REUNION == 60.0


# ----------------------------------------------------------------------
# Contar votos: solo los emitidos
# ----------------------------------------------------------------------

@pytest.mark.parametrize("votos, esperado", [
    ({0: 1, 2: 1, 1: 0}, (1, EXPULSADO)),
    ({0: 1, 1: 0}, (None, EMPATE)),
    ({0: 1, 1: SALTAR}, (None, EMPATE)),  # empatar con saltar no expulsa
    ({0: SALTAR, 1: SALTAR, 2: 1}, (None, SALTADA)),
    ({}, (None, SIN_VOTOS)),
    ({2: 0}, (0, EXPULSADO)),  # los que no votaron no le suman a nadie
])
def test_contar_votos(votos, esperado):
    expulsado, motivo, conteo = contar_votos(votos)
    assert (expulsado, motivo) == esperado
    assert sum(conteo.values()) == len(votos)


def test_un_voto_por_jugador_sin_cambiarlo_y_solo_a_candidatos():
    reunion = Reunion(0, [0, 1, 2])
    assert reunion.votar(0, 1) and not reunion.votar(0, 2)  # no se cambia
    assert not reunion.votar(5, 1)  # no está en la partida
    assert not reunion.votar(1, 7) and not reunion.votar(1, "nadie")
    assert reunion.votar(1, SALTAR)
    assert reunion.votos == {0: 1, 1: SALTAR}


def test_termina_al_minuto_o_cuando_todos_votaron():
    reunion = Reunion(0, [0, 1, 2], duracion=60)
    reunion.votar(0, 1)
    reunion.actualizar(59.9)
    assert not reunion.terminada
    reunion.actualizar(0.2)
    assert reunion.terminada and reunion.resultado()[:2] == (1, EXPULSADO)  # el que no votó, no cuenta
    rapida = Reunion(0, [0, 1])
    rapida.votar(0, 1)
    rapida.votar(1, 0)
    assert rapida.terminada and rapida.restante > 59  # ya votaron todos


def test_quien_se_desconecta_no_frena_la_votacion():
    reunion = Reunion(0, [0, 1, 2])
    reunion.votar(0, 2)
    reunion.votar(1, 2)
    assert not reunion.terminada
    reunion.olvidar(2)
    assert reunion.terminada


def test_el_chat_limpia_recorta_y_guarda_los_ultimos():
    assert limpiar_mensaje("  hola\n\tequipo  ") == "hola equipo"
    assert limpiar_mensaje("x" * 500) == "x" * MAX_LARGO_MENSAJE_REUNION
    assert limpiar_mensaje(None) == "" and limpiar_mensaje("   ") == ""
    reunion = Reunion(0, [0, 1])
    assert not reunion.escribir(0, "   ") and not reunion.escribir(9, "hola")
    for numero in range(MAX_MENSAJES_REUNION + 5):
        assert reunion.escribir(numero % 2, f"m{numero}")
    assert len(reunion.chat) == MAX_MENSAJES_REUNION and reunion.chat[-1][1] == f"m{MAX_MENSAJES_REUNION + 4}"


def test_el_boton_espera_60_s_al_empezar_y_despues_de_cada_reunion():
    control = ControlReuniones(recarga=60, duracion=60, duracion_resultado=6)
    assert not control.puede_convocar(0, [0, 1])
    control.actualizar(60)
    assert control.puede_convocar(0, [0, 1])
    assert not control.puede_convocar(0, [0])  # solo no hay con quién hablar
    assert control.convocar(0, [0, 1, 2]) and control.numero == 1
    assert not control.convocar(1, [0, 1, 2])  # ya hay una
    control.actualizar(30)
    assert control.recarga_restante == 0 and control.reunion.restante == 30  # en la reunión el botón no recarga
    control.actualizar(30)  # se acabó el minuto sin votos
    assert control.reunion is None and control.resultado["mot"] == SIN_VOTOS
    assert control.en_curso and control.recarga_restante == 60  # se ve el resultado
    control.actualizar(6)
    assert not control.en_curso
    control.actualizar(59)
    assert not control.puede_convocar(0, [0, 1, 2])
    control.actualizar(1)
    assert control.puede_convocar(0, [0, 1, 2])


def test_expulsar_al_impostor_lo_revela_y_se_acaban_las_reuniones():
    control = ControlReuniones(recarga=0, duracion=60, duracion_resultado=1)
    control.convocar(0, [0, 1, 2])
    control.votar(0, 2)
    control.votar(1, 2)
    control.votar(2, 0)
    control.actualizar(0.0, es_impostor=lambda i: i == 2)
    assert control.expulsados == {2} and control.impostor_descubierto
    assert control.resultado == {"exp": 2, "mot": EXPULSADO, "imp": True, "votos": [[0, 2], [1, 2], [2, 0]]}
    control.actualizar(1)
    control.recarga_restante = 0
    assert not control.puede_convocar(0, [0, 1, 2])


def test_el_expulsado_no_vota_ni_convoca_y_no_es_candidato():
    control = ControlReuniones(recarga=0, duracion=60, duracion_resultado=0)
    control.expulsados.add(1)
    assert not control.puede_convocar(1, [0, 1, 2])
    control.convocar(0, [0, 1, 2])
    assert control.reunion.candidatos == (0, 2)
    assert not control.votar(1, 0) and not control.votar(0, 1) and not control.escribir(1, "yo no fui")


def test_la_vista_viaja_por_el_estado_y_tolera_basura():
    control = ControlReuniones(recarga=0, duracion=60, duracion_resultado=5)
    control.convocar(1, [0, 1])
    control.escribir(0, "fue J2")
    control.votar(0, 1)
    vista = vista_de_dict(control.a_dict())
    assert vista.activa and vista.convocante == 1 and vista.candidatos == (0, 1) and vista.votaron == (0,)
    assert vista.chat == ((0, "fue J2"),) and vista.en_curso and not vista.mostrando_resultado
    control.votar(1, 1)
    control.actualizar(0.0, es_impostor=lambda i: i == 1)
    vista = vista_de_dict(control.a_dict())
    assert not vista.activa and vista.mostrando_resultado and vista.expulsado == 1 and vista.era_impostor
    assert vista.votos == ((0, 1), (1, 1)) and vista.expulsados == (1,) and vista.impostor_descubierto
    roto = {"rcd": "x", "exp": [1, "a", -3, True], "reu": {"t": float("nan"), "cand": "no", "chat": [[0, 5], [1, "ok"], "z"]},
            "res": {"mot": "inventado"}}
    vista = vista_de_dict(roto)
    assert vista.recarga == COOLDOWN_REUNION and vista.expulsados == (1,) and vista.chat == ((1, "ok"),)
    assert vista.activa and vista.candidatos == () and not vista.mostrando_resultado
    assert vista_de_dict(None) == VistaReunion()


# ----------------------------------------------------------------------
# El host
# ----------------------------------------------------------------------

class _ServidorFalso:
    def __init__(self):
        self.cola = []

    def leer_mensajes(self):
        mensajes, self.cola = self.cola, []
        return mensajes


def _host(impostor=1, escena=Escena.CIUDAD, recarga=0.0):
    host = AdaptadorOnlineHost(_ServidorFalso(), ids_red=[0, 1, 2])
    host.reuniones = ControlReuniones(recarga=recarga, duracion=60, duracion_resultado=2)
    jugadores = [Ciudadano(0, 0), Candidato(0, 0), Ciudadano(0, 0)]
    if impostor is not None:
        jugadores[impostor].es_impostor = True
    host._preparar_frame(SimpleNamespace(), None, jugadores)
    host._escena = escena
    return host


def _mensaje(host, id_red, evento, **datos):
    host.servidor.cola.append({"tipo": REUNION, "evento": evento, "id": id_red, **datos})
    host._procesar_mensajes()


def test_el_host_atiende_convocar_votar_y_escribir_de_los_invitados():
    host = _host()
    _mensaje(host, 2, CONVOCAR)
    vista = host.estado_reunion()
    assert vista.activa and vista.convocante == 2 and host.reunion_en_curso()
    _mensaje(host, 1, ESCRIBIR, texto="yo vi a J3 mover el cursor")
    _mensaje(host, 1, VOTAR, objetivo=2)
    _mensaje(host, 2, VOTAR, objetivo=True)  # basura: no cuenta
    _mensaje(host, 2, VOTAR, objetivo=SALTAR)
    assert host.votar_reunion(0, 1)  # el host vota desde Main
    host.reuniones.actualizar(0.0, host._es_impostor)  # el frame siguiente
    assert host.reuniones.reunion is None  # votaron todos
    vista = host.estado_reunion()
    assert vista.mostrando_resultado and vista.chat == () and vista.motivo == EMPATE  # 1 a J3, 1 a J2, 1 salto


def test_el_host_solo_convoca_con_impostor_y_con_el_mundo_en_marcha():
    assert not _host(impostor=None).convocar_reunion(0)
    assert not _host(escena=Escena.RESULTADO).convocar_reunion(0)
    assert not _host(recarga=10).convocar_reunion(0)
    assert _host(escena=Escena.DECISION).convocar_reunion(0)


def _mazmorra_en_decision():
    terminal = TerminalDecision(construir_arbol_publicacion(), duracion=45.0)
    terminal.iniciar()
    return SimpleNamespace(cuarto=SimpleNamespace(terminal=terminal))


def test_en_la_reunion_nadie_mueve_la_terminal_y_el_bloqueo_no_corre():
    host = _host(impostor=0, escena=Escena.DECISION)
    mazmorra = _mazmorra_en_decision()
    host._seguir_sabotaje(Escena.DECISION, mazmorra, 0.0)
    restante = host.restante_sabotaje()
    host.convocar_reunion(1)
    host.servidor.cola.append({"tipo": DECISION_NAV, "dir": DERECHA, "id": 2})
    host._procesar_mensajes()
    assert host._solicitudes_decision == [] and host.puede_navegar(2) is False
    host.servidor.cola = []
    host.actualizar(Escena.DECISION, None, mazmorra, 0.0, 5.0, SimpleNamespace(), None, host._jugadores, None)
    assert host.restante_sabotaje() == restante  # el impostor no gana tiempo en la reunión


def test_el_expulsado_ya_no_mueve_la_terminal():
    host = _host(impostor=1, escena=Escena.DECISION)
    host.reuniones.expulsados.add(1)
    host.servidor.cola.append({"tipo": DECISION_NAV, "dir": CONFIRMAR, "id": 1})
    host._procesar_mensajes()
    assert host._solicitudes_decision == [] and not host.puede_navegar(1) and host.expulsado(1)
    assert host.puede_navegar(2) and not host.expulsado(2)


def test_el_estado_lleva_la_reunion_y_quien_se_va_no_frena_la_votacion():
    host = _host()
    host.convocar_reunion(0)
    host.votar_reunion(0, 1)
    host.votar_reunion(1, 1)
    datos = host.reuniones.a_dict()
    assert datos["reu"]["vot"] == [0, 1] and datos["n"] == 1
    host.servidor.cola.append({"tipo": DESCONEXION, "id": 2})
    host._procesar_mensajes()
    assert host.reuniones.reunion.terminada


# ----------------------------------------------------------------------
# El invitado
# ----------------------------------------------------------------------

class _ClienteFalso:
    conectado = True

    def __init__(self):
        self.enviados = []

    def enviar_reunion(self, evento, **datos):
        self.enviados.append((evento, datos))


def _invitado():
    cliente = _ClienteFalso()
    invitado = AdaptadorOnlineJoin(cliente, id_local=1, ids_red=[0, 1])
    jugadores = [Ciudadano(0, 0), Candidato(0, 0)]
    jugadores[0].es_impostor = True
    invitado._preparar_frame(SimpleNamespace(), None, jugadores)
    partida = SimpleNamespace(colapso=SimpleNamespace(valor=0.0),
                              campania=SimpleNamespace(aplicar_resumen_red=lambda datos: None))
    return invitado, cliente, partida, jugadores


def test_el_invitado_refleja_la_reunion_y_le_pide_todo_al_host():
    invitado, cliente, partida, jugadores = _invitado()
    assert invitado.convocar_reunion(1) and cliente.enviados == [(CONVOCAR, {})]
    assert not invitado.votar_reunion(1, 0)  # sin reunión no hay votación
    control = ControlReuniones(recarga=0)
    control.convocar(0, [0, 1])
    invitado._aplicar({"reu": control.a_dict()}, Escena.CIUDAD, None, None, partida, jugadores)
    assert invitado.reunion_en_curso() and not invitado.puede_navegar(1)
    assert not invitado.convocar_reunion(1)  # ya hay una
    assert invitado.votar_reunion(1, SALTAR) and invitado.escribir_reunion(1, "  fue el host ")
    assert cliente.enviados[1:] == [(VOTAR, {"objetivo": SALTAR}), (ESCRIBIR, {"texto": "fue el host"})]
    control.votar(1, SALTAR)
    invitado._aplicar({"reu": control.a_dict()}, Escena.CIUDAD, None, None, partida, jugadores)
    assert not invitado.votar_reunion(1, 0)  # el host ya contó su voto
    control.expulsados.add(1)
    control.reunion = None
    invitado._aplicar({"reu": control.a_dict()}, Escena.DECISION, None, None, partida, jugadores)
    assert invitado.expulsado(1) and not invitado.puede_navegar(1)


# ----------------------------------------------------------------------
# Por la red de verdad
# ----------------------------------------------------------------------

def _esperar(condicion, limite_s=5.0):
    fin = time.monotonic() + limite_s
    while time.monotonic() < fin:
        if condicion():
            return True
        time.sleep(0.02)
    return condicion()


def test_por_red_el_invitado_convoca_chatea_y_vota():
    servidor = Servidor()
    assert servidor.iniciar(0, interfaz="127.0.0.1") is not None
    cliente = Cliente()
    try:
        assert cliente.conectar("127.0.0.1", servidor.puerto)
        assert _esperar(lambda: cliente.id_jugador == 1)
        host = AdaptadorOnlineHost(servidor, ids_red=[0, 1])
        host.reuniones = ControlReuniones(recarga=0)
        jugadores = [Ciudadano(0, 0), Candidato(0, 0)]
        jugadores[0].es_impostor = True
        host._preparar_frame(SimpleNamespace(), None, jugadores)
        host._escena = Escena.MAZMORRA

        cliente.enviar_reunion(CONVOCAR)
        assert _esperar(lambda: host._procesar_mensajes() or host.reunion_en_curso())
        cliente.enviar_reunion(ESCRIBIR, texto="el host movió el cursor a Compartir")
        cliente.enviar_reunion(VOTAR, objetivo=0)
        assert _esperar(lambda: host._procesar_mensajes() or 1 in host.reuniones.reunion.votos)
        assert host.reuniones.reunion.chat == [(1, "el host movió el cursor a Compartir")]
        host.votar_reunion(0, 1)  # el impostor acusa al otro: empate
        host.reuniones.actualizar(0.0, host._es_impostor)
        assert host.estado_reunion().motivo == EMPATE and not host.reuniones.expulsados
    finally:
        cliente.detener()
        servidor.detener()


# ----------------------------------------------------------------------
# En el loop real de Main
# ----------------------------------------------------------------------

class _RedReunion(_Red):
    """El adaptador falso de test_presentacion_online con una reunión de verdad
    (ControlReuniones), como el host: esta PC convoca y vota directo."""

    def __init__(self, duracion=30.0, duracion_resultado=0.5, **kwargs):
        super().__init__(**kwargs)
        self.reuniones = ControlReuniones(duracion=duracion, duracion_resultado=duracion_resultado)
        self.reuniones.recarga_restante = 0.0  # el botón ya está listo
        self.jugadores = []

    def actualizar(self, escena, arena, mazmorra, fundido, dt, sesion, partida, jugadores, jugador):
        self.jugadores = jugadores
        self.reuniones.actualizar(dt, lambda i: getattr(jugadores[i], "es_impostor", False))
        return super().actualizar(escena, arena, mazmorra, fundido, dt, sesion, partida, jugadores, jugador)

    def convocar_reunion(self, indice):
        return self.reuniones.convocar(indice, list(range(len(self.jugadores))))

    def votar_reunion(self, indice, objetivo):
        return self.reuniones.votar(indice, objetivo)

    def escribir_reunion(self, indice, texto):
        return self.reuniones.escribir(indice, texto)

    def estado_reunion(self):
        return vista_de_dict(self.reuniones.a_dict())

    def reunion_en_curso(self):
        return self.reuniones.en_curso

    def expulsado(self, indice):
        return indice in self.reuniones.expulsados


def _impostor_j2(sesion):
    sesion.jugadores[1].es_impostor = True
    sesion.partida.campania.intros_vistas.add("Colegio")  # sin la tarjeta del capítulo


def _texto(cadena):
    pygame.event.post(pygame.event.Event(pygame.TEXTINPUT, text=cadena))


def _clic(posicion):
    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=posicion))


def _rojos(superficie, rect, color):
    rect = pygame.Rect(rect)
    return sum(superficie.get_at((x, y))[:3] == color for x in range(rect.left, rect.right, 2)
               for y in range(rect.top, rect.bottom, 2))


def test_r_convoca_y_la_reunion_se_lleva_el_teclado(correr):
    red = _RedReunion(cuando=10_000, espejo=False)
    vistos = {}

    def guion(n, loc):
        if n == 3:
            vistos["boton"] = _rojos(pygame.display.get_surface(), assets.RECT_BOTON_REPORTAR, assets.COLOR_REPORTAR)
            _tecla(pygame.K_r)
            _texto("r")  # la "r" de la tecla también llega como texto
        if n == 5:
            vistos["sin_r"] = loc["texto_chat"]
            _texto("fue J2")
            _tecla(pygame.K_RETURN)
            _tecla(pygame.K_RIGHT)
            _tecla(pygame.K_RETURN)  # elige J2...
        if n == 7:
            vistos["armado"] = (loc["voto_armado"], dict(red.reuniones.reunion.votos))
            _tecla(pygame.K_RETURN)  # ...y confirma
        if n == 9:
            vistos["fin"] = loc["en_reunion"]
            return True
        return False

    correr(red, guion, id_local=0, preparar=_impostor_j2)
    assert vistos["boton"] > 20  # el botón listo se ve rojo
    assert red.reuniones.numero == 1 and vistos["sin_r"] == ""
    assert red.reuniones.resultado is not None or red.reuniones.reunion is not None
    assert vistos["armado"] == (1, {})  # el primer Enter solo arma el voto
    votos = dict(red.reuniones.resultado["votos"]) if red.reuniones.resultado else red.reuniones.reunion.votos
    assert votos.get(0) == 1


def test_la_reunion_pausa_la_terminal_y_las_teclas_no_la_mueven(correr):
    red = _RedReunion(cuando=3, espejo=False, en_decision=True)
    vistos = {}

    def guion(n, loc):
        if n == 5:
            red.reuniones.convocar(1, [0, 1])  # la convoca el otro jugador
        if n == 7:
            vistos["antes"] = red.mazmorra.cuarto.terminal.tiempo_restante
            _tecla(pygame.K_RIGHT)
            _tecla(pygame.K_RETURN)
        if n == 20:
            terminal = red.mazmorra.cuarto.terminal
            vistos["despues"] = (terminal.tiempo_restante, terminal.indice_seleccionado, terminal.nodo_actual is terminal.arbol.raiz)
            vistos["pantalla"] = pygame.display.get_surface().copy()
            return True
        return False

    correr(red, guion, id_local=0, preparar=_impostor_j2)
    assert vistos["despues"] == (vistos["antes"], 0, True)
    assert _rojos(vistos["pantalla"], (40, 28, 600, 70), assets.COLOR_REPORTAR) > 20  # el título de la reunión


def test_en_la_reunion_no_hay_combate(correr, monkeypatch):
    import Main
    combate = []
    original = Main._frame_de_combate
    monkeypatch.setattr(Main, "_frame_de_combate", lambda *a, **k: combate.append(1) or original(*a, **k))
    red = _RedReunion(cuando=3, espejo=False)
    vistos = {}

    def guion(n, loc):
        if n == 30:
            vistos["antes"] = len(combate)
            red.reuniones.convocar(1, [0, 1])
        if n == 45:
            vistos["durante"] = len(combate)
            return True
        return False

    correr(red, guion, id_local=0, preparar=_impostor_j2)
    assert vistos["antes"] > 0 and vistos["durante"] == vistos["antes"]


def test_clic_en_el_boton_convoca_y_clic_dos_veces_vota(correr):
    red = _RedReunion(cuando=10_000, espejo=False)
    vistos = {}
    centro = pygame.Rect(assets.RECT_BOTON_REPORTAR).center

    def guion(n, loc):
        if n == 3:
            _clic(centro)
        if n == 5:
            vistos["activa"] = red.reuniones.reunion is not None
            tarjeta = reunion_render.rects_candidatos(2)[1].center
            _clic(tarjeta)
            _clic(tarjeta)
        if n == 7:
            return True
        return False

    correr(red, guion, id_local=0, preparar=_impostor_j2)
    assert vistos["activa"]
    votos = dict(red.reuniones.resultado["votos"]) if red.reuniones.resultado else red.reuniones.reunion.votos
    assert votos == {0: 1}


def test_el_resultado_se_ve_y_despues_el_mundo_sigue(correr):
    red = _RedReunion(cuando=10_000, espejo=False, duracion_resultado=0.3)
    vistos = {}

    def guion(n, loc):
        if n == 3:
            red.reuniones.convocar(0, [0, 1])
            red.reuniones.votar(0, 1)
            red.reuniones.votar(1, 0)
        if n == 6:
            vistos["resultado"] = (loc["en_reunion"], red.estado_reunion().mostrando_resultado)
            vistos["pantalla"] = pygame.display.get_surface().copy()
        if n == 60:
            vistos["despues"] = (loc["en_reunion"], red.reuniones.recarga_restante > 0)
            return True
        return False

    correr(red, guion, id_local=0, preparar=_impostor_j2)
    assert vistos["resultado"] == (True, True)
    assert vistos["despues"] == (False, True)  # el botón vuelve a recargar


def test_el_expulsado_no_ve_el_boton(correr):
    red = _RedReunion(cuando=10_000, espejo=False)
    red.reuniones.expulsados.add(0)
    vistos = {}

    def guion(n, loc):
        if n == 3:
            vistos["pantalla"] = pygame.display.get_surface().copy()
            _tecla(pygame.K_r)
        if n == 5:
            return True
        return False

    correr(red, guion, id_local=0, preparar=_impostor_j2)
    rect = pygame.Rect(assets.RECT_BOTON_REPORTAR)
    assert _rojos(vistos["pantalla"], (rect.left, rect.top, rect.width, rect.height - 34), assets.COLOR_REPORTAR) == 0
    assert red.reuniones.numero == 0  # la R no convoca


def test_sin_impostor_no_hay_boton_ni_reunion(correr):
    red = _RedReunion(cuando=10_000, espejo=False)

    def guion(n, loc):
        if n == 3:
            _tecla(pygame.K_r)
        return n >= 5

    correr(red, guion, id_local=0)
    assert red.reuniones.numero == 0


# ----------------------------------------------------------------------
# El dibujo
# ----------------------------------------------------------------------

def _jugadores(cantidad):
    clases = [Ciudadano, Candidato, Ciudadano, Candidato]
    return [clases[i](0, 0) for i in range(cantidad)]


@pytest.mark.parametrize("cantidad", [2, 3, 4])
def test_las_tarjetas_caben_y_el_clic_cae_en_cada_una(cantidad):
    area = pygame.Rect(assets.RECT_CANDIDATOS_REUNION)
    rects = reunion_render.rects_candidatos(cantidad)
    assert all(area.contains(r) for r in rects)
    assert not any(a.colliderect(b) for i, a in enumerate(rects) for b in rects[i + 1:])
    candidatos = tuple(range(cantidad))
    for indice, rect in zip(candidatos, rects):
        assert reunion_render.objetivo_en(rect.center, candidatos) == indice
    assert reunion_render.objetivo_en(pygame.Rect(assets.RECT_SALTAR_REUNION).center, candidatos) == SALTAR
    assert reunion_render.objetivo_en((5, 5), candidatos) is None


def test_el_panel_no_tapa_la_barra_de_controles():
    panel = pygame.Rect(assets.RECT_PANEL_REUNION)
    assert panel.bottom <= 720 - assets.ALTO_BARRA_CONTROLES
    for rect in (assets.RECT_CANDIDATOS_REUNION, assets.RECT_SALTAR_REUNION, assets.RECT_CHAT_REUNION):
        assert panel.contains(pygame.Rect(rect))


@pytest.mark.parametrize("cantidad", [2, 4])
def test_dibujar_reunion_en_todos_sus_estados(cantidad):
    pygame.font.init()
    pantalla = pygame.Surface((1280, 720))
    jugadores = _jugadores(cantidad)
    chat = tuple((i % cantidad, "mensaje largo " * 6) for i in range(MAX_MENSAJES_REUNION))
    vista = VistaReunion(recarga=0, activa=True, restante=8.0, convocante=1, candidatos=tuple(range(cantidad)),
                         votaron=(0,), chat=chat, numero=1)
    for seleccion, armado, mi_voto in ((0, None, None), (1, 1, None), (SALTAR, SALTAR, None), (None, None, 1),
                                       (None, None, SALTAR)):
        reunion_render.dibujar_reunion(pantalla, vista, jugadores, 0, seleccion, armado, mi_voto, "hola" * 40, 1.3)
    expulsado = VistaReunion(activa=True, restante=50, candidatos=(1,), expulsados=(0,), numero=2)
    reunion_render.dibujar_reunion(pantalla, expulsado, jugadores, 0)


@pytest.mark.parametrize("vista", [
    VistaReunion(expulsado=1, motivo=EXPULSADO, era_impostor=True, votos=((0, 1), (1, 1)), resultado_restante=3),
    VistaReunion(expulsado=0, motivo=EXPULSADO, votos=((1, 0),), resultado_restante=3),
    VistaReunion(motivo=EMPATE, votos=((0, 1), (1, 0)), resultado_restante=3),
    VistaReunion(motivo=SALTADA, votos=((0, SALTAR),), resultado_restante=3),
    VistaReunion(motivo=SIN_VOTOS, resultado_restante=3),
])
def test_dibujar_resultado(vista):
    pygame.font.init()
    pantalla = pygame.Surface((1280, 720))
    reunion_render.dibujar_resultado_reunion(pantalla, vista, _jugadores(2), 0.7)
    assert vista.mostrando_resultado


def test_los_textos_del_resultado():
    jugadores = _jugadores(2)
    vista = VistaReunion(motivo=EMPATE, votos=((0, 1), (1, SALTAR)), resultado_restante=1)
    assert reunion_render._texto_votos(vista, jugadores) == ["J2 · Candidato: J1  (1)", "Saltar: J2  (1)"]
    assert reunion_render._texto_votos(VistaReunion(motivo=SIN_VOTOS), jugadores) == ["Nadie votó."]


@pytest.mark.parametrize("recarga", [0.0, 37.2])
def test_el_boton_reportar(recarga):
    pygame.font.init()
    pantalla = pygame.Surface((1280, 720))
    reunion_render.dibujar_boton_reportar(pantalla, recarga, COOLDOWN_REUNION, 0.4)
    rojos = _rojos(pantalla, assets.RECT_BOTON_REPORTAR, assets.COLOR_REPORTAR)
    assert (rojos > 50) == (recarga == 0.0)
    fuente = dibujo.fuente(assets.TAMANIO_FUENTE_NORMAL, True)
    assert fuente.size(assets.TEXTO_BOTON_REPORTAR)[0] <= pygame.Rect(assets.RECT_BOTON_REPORTAR).width - 10
