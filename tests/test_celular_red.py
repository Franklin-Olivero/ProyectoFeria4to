"""Celular del modo Online por la red de verdad (Servidor y Cliente en
127.0.0.1): el SYNC al conectarse (misma semilla, reloj cercano e
historial), el chat del host y de los invitados (el autor lo pone la
conexión), "entró / salió de la sala", el anti-spam y los silenciados que
hace cumplir el host, que CELULAR no ensucia las colas de mensajes, las
entradas bloqueadas con el celular abierto y VERSION_ESTADO."""

import os
import socket
import threading
import time
from types import SimpleNamespace

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402
import pytest  # noqa: E402

from Online import chat_celular, registro_errores  # noqa: E402
from Online.chat_celular import (  # noqa: E402
    EVENTO_CHAT, EVENTO_SYNC, JUGADOR, SISTEMA_ENTRO, SISTEMA_SALIO, CanalCelular,
)
from Online.cliente import Cliente  # noqa: E402
from Online.protocolo import (  # noqa: E402
    BIENVENIDA, CELULAR, ESTADO, INICIAR, PING, crear_mensaje, deserializar_buffer, msg_celular, msg_estado,
    serializar,
)
from Online.servidor import Servidor  # noqa: E402
from Online.sesion_red import VERSION_ESTADO, AdaptadorOnlineHost, EntradaLocalCliente, EntradaTecladoRed  # noqa: E402
from src.core.entrada import EJE_MAXIMO, InputJugador  # noqa: E402
from src.core.escenas import Escena  # noqa: E402


# ----------------------------------------------------------------------
# Ayudas
# ----------------------------------------------------------------------

def _esperar(condicion, limite_s=5.0):
    """Repite la condición hasta que se cumpla (o se acabe el límite): la red
    tarda lo que tarda, nunca un sleep fijo largo."""
    fin = time.monotonic() + limite_s
    while time.monotonic() < fin:
        if condicion():
            return True
        time.sleep(0.02)
    return condicion()


def _abrir_servidor():
    servidor = Servidor()
    assert servidor.iniciar(0, interfaz="127.0.0.1") is not None, servidor.error
    return servidor


def _unir(servidor, invitados):
    """Conecta un invitado y espera su BIENVENIDA y su SYNC del celular.
    Queda en `invitados` antes de conectar: el finally lo detiene siempre."""
    cliente = Cliente()
    invitados.append(cliente)
    assert cliente.conectar("127.0.0.1", servidor.puerto), cliente.error
    assert _esperar(lambda: cliente.id_jugador is not None and cliente.celular.sincronizado)
    return cliente


def _cerrar(servidor, invitados):
    for cliente in invitados:
        cliente.detener()
    servidor.detener()


def _textos(canal, autor=None):
    """Textos de los mensajes de jugadores (de `autor`, si se da), en orden."""
    return [m.texto for m in canal.mensajes() if m.tipo == JUGADOR and (autor is None or m.autor == autor)]


def _sistema(canal):
    return [(m.tipo, m.autor) for m in canal.mensajes() if m.tipo != JUGADOR]


def _dicts(canal):
    """El historial tal como viaja: dos PCs con el mismo chat dan la misma lista."""
    return [m.a_dict() for m in canal.mensajes()]


def _frame_host(host):
    """Un frame de AdaptadorOnlineHost.actualizar (lo de la partida, aparte)."""
    return host.actualizar(Escena.CIUDAD, None, None, 0.0, 0.016, SimpleNamespace(), None, [], None)


def _sin_partida(host, monkeypatch):
    """El adaptador solo con lo que hace `actualizar` antes de sincronizar la
    partida (reuniones, celular, sabotajes): lo que se prueba aquí."""
    monkeypatch.setattr(host, "_actualizar", lambda escena, arena, mazmorra, fundido, *resto:
                        (escena, arena, mazmorra, fundido))


@pytest.fixture
def errores(monkeypatch):
    """Lo que se anotaría en Online/errores_online.log: el celular no debe dejar nada."""
    anotados = []
    monkeypatch.setattr(registro_errores, "registrar", lambda contexto, error=None: anotados.append(contexto))
    return anotados


@pytest.fixture
def sin_anti_spam(monkeypatch):
    """Para que el mismo autor pueda escribir varias veces seguidas."""
    monkeypatch.setattr(chat_celular, "INTERVALO_MINIMO_CHAT_S", 0.0)


def test_version_estado_sube_a_5_por_el_celular():
    assert VERSION_ESTADO == 5


def test_msg_celular_ida_y_vuelta():
    mensajes, resto = deserializar_buffer(msg_celular(EVENTO_CHAT, texto="¡hola, sala!"))
    assert resto == b"" and mensajes == [{"tipo": CELULAR, "evento": EVENTO_CHAT, "texto": "¡hola, sala!"}]
    canal = CanalCelular(semilla=5)
    canal.publicar(0, "¿Vamos a la Alcaldía?")
    sync = deserializar_buffer(msg_celular(EVENTO_SYNC, **canal.a_sync()))[0][0]
    assert (sync["tipo"], sync["evento"], sync["semilla"]) == (CELULAR, EVENTO_SYNC, 5)
    assert sync["chat"] == [m.a_dict() for m in canal.mensajes()] and isinstance(sync["t"], float)


# ----------------------------------------------------------------------
# Por la red de verdad
# ----------------------------------------------------------------------

def test_al_conectarse_el_invitado_recibe_la_semilla_el_reloj_y_el_chat(errores):
    servidor = _abrir_servidor()
    invitados = []
    try:
        assert servidor.escribir_chat("  antes de que llegues ")  # sin invitados: queda en el historial
        invitado = _unir(servidor, invitados)
        canal = invitado.celular
        assert canal.semilla == servidor.celular.semilla  # mismo feed en las dos PCs
        assert abs(canal.segundos() - servidor.celular.segundos()) < 0.5  # mismo instante (salvo la latencia)
        # El historial llega en el SYNC y "J2 entró a la sala" justo después, con el número que sigue.
        assert _esperar(lambda: canal.ultimo_numero() == 2 and _dicts(canal) == _dicts(servidor.celular))
        primero, entro = canal.mensajes()
        assert (primero.numero, primero.autor, primero.texto, primero.tipo) == (1, 0, "antes de que llegues", JUGADOR)
        assert (entro.numero, entro.autor, entro.texto, entro.tipo) == (2, 1, "", SISTEMA_ENTRO)
        assert errores == []
    finally:
        _cerrar(servidor, invitados)


def test_al_unirse_a_una_partida_en_curso_el_sync_va_despues_de_iniciar_y_del_estado():
    servidor = _abrir_servidor()
    crudo = None
    try:
        servidor.marcar_iniciado({"escena": "CIUDAD"})
        servidor.ultimo_snapshot_estado = msg_estado({"v": VERSION_ESTADO})
        # Un socket crudo (sin Cliente) para ver el orden exacto en que llegan los mensajes.
        crudo = socket.create_connection(("127.0.0.1", servidor.puerto), timeout=5.0)
        mensajes, buffer = [], b""
        while not any(m.get("tipo") == CELULAR and m.get("evento") == EVENTO_CHAT for m in mensajes):
            trozo = crudo.recv(4096)
            assert trozo
            nuevos, buffer = deserializar_buffer(buffer + trozo)
            mensajes.extend(nuevos)
        orden = [(m["tipo"], m.get("evento")) for m in mensajes if m["tipo"] != PING]
        assert orden[:5] == [(BIENVENIDA, None), (INICIAR, None), (ESTADO, None), (CELULAR, EVENTO_SYNC),
                             (CELULAR, EVENTO_CHAT)]
        entro = [m for m in mensajes if m.get("evento") == EVENTO_CHAT][0]["m"]
        assert (entro["a"], entro["k"]) == (1, SISTEMA_ENTRO)
    finally:
        if crudo is not None:
            crudo.close()
        servidor.detener()


def test_el_host_escribe_y_el_invitado_lo_recibe(errores):
    servidor = _abrir_servidor()
    invitados = []
    try:
        invitado = _unir(servidor, invitados)
        assert servidor.escribir_chat("  hola   equipo ")
        assert _esperar(lambda: _textos(invitado.celular, autor=0) == ["hola equipo"])
        for vacio in ("", "   \n ", None, 42):
            assert not servidor.escribir_chat(vacio)
        assert _textos(servidor.celular) == ["hola equipo"] and errores == []
    finally:
        _cerrar(servidor, invitados)


def test_el_invitado_escribe_y_todos_lo_ven_con_el_autor_de_su_conexion(sin_anti_spam, errores):
    servidor = _abrir_servidor()
    invitados = []
    try:
        j2 = _unir(servidor, invitados)
        j3 = _unir(servidor, invitados)
        assert (j2.id_jugador, j3.id_jugador) == (1, 2)
        assert j2.escribir_chat("  soy J2 ")
        # Armado a mano para hacerse pasar por el host: trae id, autor y hasta un "m" ya numerado.
        falso = crear_mensaje(CELULAR, evento=EVENTO_CHAT, texto="me hago pasar por el host", id=0, autor=0, a=0,
                              m={"n": 99, "a": 0, "t": "falso", "s": 0, "k": JUGADOR})
        j2._enviar(serializar(falso))
        esperado = ["soy J2", "me hago pasar por el host"]
        for canal in (servidor.celular, j2.celular, j3.celular):  # también quien lo escribió lo ve volver
            assert _esperar(lambda canal=canal: _textos(canal, autor=1) == esperado)
        assert _textos(servidor.celular, autor=0) == [] and "falso" not in _textos(j3.celular)
        # Las tres PCs con el mismo historial: mismos números, autores y textos.
        assert _esperar(lambda: _dicts(j2.celular) == _dicts(servidor.celular) == _dicts(j3.celular))
        assert [m.numero for m in servidor.celular.mensajes()] == [1, 2, 3, 4]  # 2 "entró" + 2 mensajes
        assert errores == []
    finally:
        _cerrar(servidor, invitados)


def test_entro_y_salio_de_la_sala(errores):
    servidor = _abrir_servidor()
    invitados = []
    try:
        j2 = _unir(servidor, invitados)
        j3 = _unir(servidor, invitados)
        for canal in (servidor.celular, j2.celular, j3.celular):
            assert _esperar(lambda canal=canal: (SISTEMA_ENTRO, 2) in _sistema(canal))
        j3.detener()
        for canal in (servidor.celular, j2.celular):
            assert _esperar(lambda canal=canal: (SISTEMA_SALIO, 2) in _sistema(canal))
        servidor._desconectar_cliente(2)  # su desconexión se nota otra vez: el aviso no se repite
        assert _sistema(servidor.celular) == [(SISTEMA_ENTRO, 1), (SISTEMA_ENTRO, 2), (SISTEMA_SALIO, 2)]
        assert all(m.texto == "" for m in servidor.celular.mensajes())  # el texto lo arma la interfaz
        assert _esperar(lambda: _dicts(j2.celular) == _dicts(servidor.celular))
        assert errores == []
    finally:
        _cerrar(servidor, invitados)


def test_el_host_aplica_el_anti_spam_por_autor(errores):
    servidor = _abrir_servidor()
    invitados = []
    try:
        j2 = _unir(servidor, invitados)
        assert j2.escribir_chat("uno") and j2.escribir_chat("dos")  # pegados: el host los ve a < 0.3 s
        j2.enviar_posicion_lobby(5, 6)  # va detrás por la misma conexión: al llegar, el chat ya se atendió
        assert _esperar(lambda: servidor.posiciones_lobby.get(1) == (5, 6))
        assert _textos(servidor.celular) == ["uno"]
        assert servidor.escribir_chat("el host no espera a J2")  # el anti-spam es por autor
        assert _esperar(lambda: _textos(j2.celular) == ["uno", "el host no espera a J2"])
        assert errores == []
    finally:
        _cerrar(servidor, invitados)


def test_el_expulsado_queda_silenciado_y_lo_hace_cumplir_el_host(sin_anti_spam, errores, monkeypatch):
    servidor = _abrir_servidor()
    invitados = []
    try:
        j2 = _unir(servidor, invitados)  # id de red 1
        j3 = _unir(servidor, invitados)  # id de red 2
        # Orden de la partida distinto al de los ids: el índice 1 es el id de red 2 (j3).
        host = AdaptadorOnlineHost(servidor, ids_red=[0, 2, 1])
        _sin_partida(host, monkeypatch)
        host.reuniones.expulsados.add(1)
        assert _frame_host(host) == (Escena.CIUDAD, None, None, 0.0)
        assert servidor.celular.silenciados == {2}

        assert j3.escribir_chat("soy un fantasma")  # su PC lo manda; el host no lo publica
        j3.enviar_posicion_lobby(12, 34)  # va detrás por la misma conexión
        assert _esperar(lambda: servidor.posiciones_lobby.get(2) == (12, 34))
        assert j2.escribir_chat("yo sí puedo")
        for canal in (j2.celular, j3.celular):  # el fantasma lee igual
            assert _esperar(lambda canal=canal: _textos(canal) == ["yo sí puedo"])
        assert _textos(servidor.celular) == ["yo sí puedo"]

        host.reuniones.expulsados.add(0)  # el host también puede quedar expulsado
        _frame_host(host)
        assert servidor.celular.silenciados == {0, 2} and not servidor.escribir_chat("el host expulsado")

        host.reuniones.expulsados.clear()
        _frame_host(host)
        assert servidor.celular.silenciados == set()
        assert j3.escribir_chat("ya puedo hablar")
        assert _esperar(lambda: _textos(j2.celular, autor=2) == ["ya puedo hablar"])
        assert errores == []
    finally:
        _cerrar(servidor, invitados)


def test_con_todos_escribiendo_a_la_vez_todas_las_pcs_ven_el_mismo_chat(sin_anti_spam, errores):
    servidor = _abrir_servidor()
    invitados = []
    try:
        j2 = _unir(servidor, invitados)
        j3 = _unir(servidor, invitados)
        por_autor = 15
        resultados = []  # lo que devolvió cada escribir_chat (un assert dentro de un hilo no haría fallar el test)

        def escribir(conexion, nombre):
            for i in range(por_autor):
                resultados.append(conexion.escribir_chat(f"{nombre} {i}"))

        # El host escribe desde "pygame" mientras el hilo del servidor publica lo de los invitados.
        hilos = [threading.Thread(target=escribir, args=par) for par in ((servidor, "host"), (j2, "J2"), (j3, "J3"))]
        for hilo in hilos:
            hilo.start()
        for hilo in hilos:
            hilo.join(10)
        assert resultados == [True] * (3 * por_autor)
        total = 2 + 3 * por_autor  # dos "entró" + los mensajes
        canales = (servidor.celular, j2.celular, j3.celular)
        assert _esperar(lambda: all(canal.ultimo_numero() == total for canal in canales))
        assert _esperar(lambda: _dicts(j2.celular) == _dicts(servidor.celular) == _dicts(j3.celular))
        assert [m.numero for m in servidor.celular.mensajes()] == list(range(1, total + 1))
        for nombre, autor in (("host", 0), ("J2", 1), ("J3", 2)):  # cada uno en el orden en que escribió
            assert _textos(j3.celular, autor=autor) == [f"{nombre} {i}" for i in range(por_autor)]
        assert errores == []
    finally:
        _cerrar(servidor, invitados)


def test_los_mensajes_celular_no_van_a_las_colas_de_mensajes(errores):
    servidor = _abrir_servidor()
    invitados = []
    try:
        j2 = _unir(servidor, invitados)
        assert servidor.escribir_chat("hola") and j2.escribir_chat("hola host")
        assert _esperar(lambda: _textos(j2.celular) == ["hola", "hola host"])
        tipos_invitado = {m.get("tipo") for m in j2.leer_mensajes()}
        assert BIENVENIDA in tipos_invitado and CELULAR not in tipos_invitado
        assert CELULAR not in {m.get("tipo") for m in servidor.leer_mensajes()}
        assert errores == []
    finally:
        _cerrar(servidor, invitados)


def test_el_invitado_no_escribe_sin_conexion_ni_texto():
    assert not Cliente().escribir_chat("hola")  # nunca se conectó
    servidor = _abrir_servidor()
    invitados = []
    try:
        j2 = _unir(servidor, invitados)
        for vacio in ("", "  \t ", None, ["hola"]):
            assert not j2.escribir_chat(vacio)
        j2.desconectar()
        assert not j2.escribir_chat("ya me fui")
    finally:
        _cerrar(servidor, invitados)


def test_mensajes_celular_rotos_no_rompen_ni_ensucian_la_cola(errores):
    cliente = Cliente()
    for basura in ({"tipo": CELULAR, "evento": EVENTO_SYNC, "semilla": "x", "t": None, "chat": 5},
                   {"tipo": CELULAR, "evento": EVENTO_CHAT, "m": "basura"},
                   {"tipo": CELULAR, "evento": EVENTO_CHAT},
                   {"tipo": CELULAR, "evento": "inventado"},
                   {"tipo": CELULAR}):
        cliente._procesar(basura)
    assert cliente.mensajes == [] and not cliente.celular.sincronizado and cliente.celular.mensajes() == ()
    cliente._procesar({"tipo": CELULAR, "evento": EVENTO_CHAT, "m": {"n": 1, "a": 0, "t": "hola", "s": 1.0, "k": JUGADOR}})
    assert _textos(cliente.celular) == ["hola"] and cliente.mensajes == []

    servidor = Servidor()  # sin abrir la sala: _procesar atiende igual (no hay a quién difundir)
    semilla = servidor.celular.semilla
    servidor._procesar(1, {"tipo": CELULAR, "evento": "inventado", "texto": "no"})
    servidor._procesar(1, {"tipo": CELULAR, "evento": EVENTO_CHAT, "texto": ["basura"]})
    servidor._procesar(1, {"tipo": CELULAR, "evento": EVENTO_SYNC, "semilla": 5, "t": 1.0, "chat": []})
    assert servidor.celular.mensajes() == () and servidor.celular.semilla == semilla  # nadie sincroniza al host
    servidor._procesar(1, {"tipo": CELULAR, "evento": EVENTO_CHAT, "texto": "hola", "id": 3})
    assert [(m.autor, m.texto) for m in servidor.celular.mensajes()] == [(1, "hola")]
    assert servidor.mensajes_host == [] and errores == []


def test_el_adaptador_con_un_servidor_sin_celular_sigue_igual(errores, monkeypatch):
    host = AdaptadorOnlineHost(SimpleNamespace(leer_mensajes=lambda: []), ids_red=[0, 1])
    _sin_partida(host, monkeypatch)
    host.reuniones.expulsados.add(1)
    assert _frame_host(host) == (Escena.CIUDAD, None, None, 0.0) and errores == []


# ----------------------------------------------------------------------
# Con el celular abierto el personaje local se queda quieto
# ----------------------------------------------------------------------

class _Teclas(dict):
    """Teclas apretadas para EntradaTeclado.leer (las demás, sueltas)."""

    def __missing__(self, tecla):
        return False


class _Mando:
    """Control de PS4 de prueba: stick izquierdo a la derecha, R2 a fondo y todos los botones apretados."""

    def __init__(self, conectado=True):
        self.conectado = conectado

    def attached(self):
        return self.conectado

    def get_axis(self, eje):
        return EJE_MAXIMO if eje in (pygame.CONTROLLER_AXIS_LEFTX, pygame.CONTROLLER_AXIS_TRIGGERRIGHT) else 0

    def get_button(self, boton):
        return True


class _AdaptadorQueEscucha:
    """Lo que la entrada del invitado le manda al host en cada frame."""

    def __init__(self):
        self.enviados = []

    def enviar_input(self, pedido, contadores=None):
        self.enviados.append((pedido, contadores))


BOTONES = (True, False, False)
PUNTO = (300, 200)


def test_con_el_celular_abierto_la_entrada_del_host_queda_quieta():
    entrada = EntradaTecladoRed(mando=_Mando(conectado=False))
    assert entrada.bloqueada is False  # cerrado: como siempre
    libre = entrada.leer(_Teclas({pygame.K_d: True, pygame.K_SPACE: True}), BOTONES, PUNTO)
    assert libre.movimiento == (1.0, 0.0) and libre.disparando and libre.punto_apuntado == PUNTO

    entrada.bloqueada = True
    escribiendo = _Teclas({pygame.K_d: True, pygame.K_SPACE: True, pygame.K_f: True, pygame.K_LSHIFT: True})
    for conectado in (False, True):  # con el teclado y con el control
        entrada.mando.conectado = conectado
        assert entrada.leer(escribiendo, BOTONES, PUNTO) == InputJugador()
        assert entrada.ultimo == InputJugador()  # lo que ven los invitados también está quieto
    assert (entrada.pulsos_habilidad, entrada.pulsos_dash) == (0, 0)

    # Se cierra con la F y el Shift todavía abajo (se usaron para escribir): no son pulsaciones nuevas.
    entrada.bloqueada = False
    entrada.mando.conectado = False
    despues = entrada.leer(escribiendo, BOTONES, PUNTO)
    assert despues.movimiento == (1.0, 0.0) and despues.disparando
    assert not despues.habilidad and not despues.dash
    entrada.mando.conectado = True
    con_control = entrada.leer(_Teclas(), BOTONES, PUNTO)
    assert con_control.movimiento == (1.0, 0.0) and con_control.disparando and not con_control.habilidad


def test_con_el_celular_abierto_el_invitado_queda_quieto_y_el_host_tambien_lo_ve_quieto():
    adaptador = _AdaptadorQueEscucha()
    entrada = EntradaLocalCliente(adaptador, id_jugador=1, mando=_Mando(conectado=False))
    assert entrada.bloqueada is False
    libre = entrada.leer(_Teclas({pygame.K_d: True, pygame.K_f: True}), BOTONES, PUNTO)
    assert libre.movimiento == (1.0, 0.0) and libre.habilidad
    assert adaptador.enviados[-1] == (libre, (1, 0))

    entrada.bloqueada = True
    for conectado in (False, True):
        entrada.mando.conectado = conectado
        quieto = entrada.leer(_Teclas({pygame.K_w: True, pygame.K_SPACE: True, pygame.K_LSHIFT: True}), BOTONES, PUNTO)
        assert quieto == InputJugador()
        assert adaptador.enviados[-1] == (InputJugador(), (1, 0))  # se le manda igual: el host lo ve quieto
    assert len(adaptador.enviados) == 3
