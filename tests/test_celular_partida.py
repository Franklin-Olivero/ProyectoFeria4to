"""Celular del modo Online dentro del juego (Online/celular_partida.py): el
loop real de Main con un servidor de verdad en 127.0.0.1, y la sala de espera."""

import os
import time

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402
import pytest  # noqa: E402

from src.core.entrada import EntradaTeclado  # noqa: E402
from src.core.escenas import Escena  # noqa: E402
from Online import disposicion_celular, lobby  # noqa: E402
from Online.celular_partida import ControlCelular  # noqa: E402
from Online.chat_celular import SALA  # noqa: E402
from Online.cliente import Cliente  # noqa: E402
from Online.servidor import Servidor  # noqa: E402
from Online.sesion_red import EntradaTecladoRed  # noqa: E402
from tests.test_presentacion_online import _Fin, _Reloj, _locales, _tecla, correr  # noqa: E402,F401
from tests.test_reunion_online import _RedReunion, _impostor_j2, _texto, _clic  # noqa: E402

BOTON_CIUDAD = disposicion_celular.rect_boton(Escena.CIUDAD, 2)


def _local_de(funcion, nombre):
    """Variable local `nombre` de la función `funcion` que está corriendo más arriba en la pila."""
    import inspect
    for marco in inspect.stack():
        if marco.function == funcion:
            return marco.frame.f_locals[nombre]
    raise LookupError(funcion)


@pytest.fixture
def red_real():
    servidor = Servidor()
    servidor.iniciar(0, interfaz="127.0.0.1")
    cliente = Cliente()
    assert cliente.conectar("127.0.0.1", servidor.puerto)
    limite = time.monotonic() + 5
    while not cliente.celular.sincronizado and time.monotonic() < limite:
        time.sleep(0.01)
    try:
        yield servidor, cliente
    finally:
        cliente.detener()
        servidor.detener()


def _esperar(condicion, limite_s=5.0):
    fin = time.monotonic() + limite_s
    while time.monotonic() < fin:
        if condicion():
            return True
        time.sleep(0.01)
    return condicion()


def _red_con_servidor(servidor, **kwargs):
    red = _RedReunion(**kwargs)
    red.servidor = servidor  # como AdaptadorOnlineHost: el celular usa servidor.celular
    return red


def test_sin_red_no_hay_celular(correr):
    vistos = {}

    def guion(n, loc):
        vistos["celular"] = loc.get("celular", "falta")
        return n >= 3

    correr(_RedReunion(cuando=10_000, espejo=False), guion, id_local=0, preparar=_impostor_j2)
    assert vistos["celular"] is None  # el adaptador de prueba no tiene servidor: sin celular


def test_c_abre_escribe_y_envia_sin_tocar_el_juego(correr, red_real):
    servidor, cliente = red_real
    red = _red_con_servidor(servidor, cuando=10_000, espejo=False)
    vistos = {}

    def guion(n, loc):
        celular = loc["celular"]
        if n == 3:
            _tecla(pygame.K_c)
            _texto("c")  # la "c" de la tecla que lo abrió no se escribe
        if n == 5:
            vistos["abierto"] = celular.abierto
            _tecla(pygame.K_TAB)  # a la lista de chats
        if n == 6:
            _clic(dict(celular._dibujado.contactos)[SALA].center)  # el chat de la sala
        if n == 7:
            _texto("hola")
            _tecla(pygame.K_r)  # no convoca la reunión
            _tecla(pygame.K_RETURN)
        if n == 10:
            vistos["reunion"] = red.reuniones.numero
            _tecla(pygame.K_ESCAPE)  # del chat vuelve a la lista
            _tecla(pygame.K_ESCAPE)  # cierra el celular, no abre la pausa
        if n == 12:
            vistos["cerrado"] = not celular.abierto
            vistos["pausa"] = loc["pausa"].abierta
            return True
        return False

    correr(red, guion, id_local=0, preparar=_impostor_j2)
    assert vistos["abierto"] and vistos["cerrado"] and not vistos["pausa"]
    assert vistos["reunion"] == 0
    assert [m.texto for m in servidor.celular.mensajes() if m.tipo == "jugador"] == ["hola"]
    assert _esperar(lambda: any(m.texto == "hola" for m in cliente.celular.mensajes()))


def test_clic_en_el_boton_abre_y_un_mensaje_ajeno_suena(correr, red_real):
    servidor, cliente = red_real
    red = _red_con_servidor(servidor, cuando=10_000, espejo=False)
    sonidos = []
    vistos = {}

    def guion(n, loc):
        if n == 3:
            cliente.escribir_chat("¿quién fue?")
        if n == 30:
            vistos["no_leidos"] = loc["celular"].no_leidos()
            _clic(pygame.Rect(BOTON_CIUDAD).center)
        if n == 33:
            vistos["abierto_en"] = (loc["celular"].abierto, loc["celular"].estado.app)
            return True
        return False

    def preparar(sesion):
        _impostor_j2(sesion)
        sesion.audio = type("Audio", (), {"reproducir": lambda self, n: sonidos.append(n),
                                          "musica": lambda self, n: None, "actualizar": lambda self, dt: None,
                                          "procesar_eventos": lambda self: None,
                                          "atenuar_musica": lambda self, a: None})()

    correr(red, guion, id_local=0, preparar=preparar)
    assert vistos["no_leidos"] == 1
    assert vistos["abierto_en"] == (True, "chat")  # con mensajes sin leer abre en el Chat
    assert "notificacion" in sonidos


def test_con_el_celular_abierto_la_entrada_local_queda_quieta(red_real):
    servidor, _ = red_real
    entrada = EntradaTecladoRed()
    sesion = type("S", (), {"entradas": [entrada], "jugadores": [], "id_local": 0})()
    adaptador = type("A", (), {"servidor": servidor})()
    celular = ControlCelular.para_partida(sesion, adaptador, None)
    evento = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_c, mod=0, unicode="c")
    assert celular.manejar_evento(evento, True, Escena.MAZMORRA)
    assert entrada.bloqueada
    pedido = entrada.leer(_Teclas({pygame.K_d, pygame.K_SPACE}), (True, False, False), (900, 300))
    assert pedido.movimiento == (0.0, 0.0) and not pedido.disparando
    celular.manejar_evento(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, mod=0, unicode=""),
                           True, Escena.MAZMORRA)
    celular.actualizar(1 / 60, True, Escena.MAZMORRA)
    assert not entrada.bloqueada


class _Teclas:
    def __init__(self, apretadas):
        self.apretadas = apretadas

    def __getitem__(self, tecla):
        return tecla in self.apretadas


def test_se_cierra_solo_cuando_deja_de_estar_disponible(red_real):
    servidor, _ = red_real
    celular = ControlCelular.para_sala(servidor, lambda jid: None)
    celular.manejar_evento(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_c, mod=0, unicode="c"), True,
                           disposicion_celular.SALA)
    assert celular.abierto
    celular.actualizar(1 / 60, False, disposicion_celular.SALA)  # p. ej. empezó una reunión
    assert not celular.abierto
    # En la terminal de decisión no hay celular.
    assert not celular.manejar_evento(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_c, mod=0, unicode="c"),
                                      True, Escena.DECISION)


def test_en_la_sala_c_abre_enter_envia_y_esc_no_sale(red_real):
    servidor, cliente = red_real
    pygame.font.init()
    pantalla = pygame.display.set_mode((1280, 720))
    pygame.event.clear()
    cuadros = {"n": 0}

    def presentar():
        cuadros["n"] += 1
        n = cuadros["n"]
        if n == 3:
            _tecla(pygame.K_c)
            _texto("c")
            _tecla(pygame.K_TAB)
        if n == 30:  # ya terminó de subir
            celular = _local_de("pantalla_sala_espera", "celular")
            _clic(dict(celular._dibujado.contactos)[SALA].center)
        if n == 32:
            _texto("listos")
            _tecla(pygame.K_RETURN)
            _tecla(pygame.K_ESCAPE)  # vuelve a la lista de chats
            _tecla(pygame.K_ESCAPE)  # cierra el celular: NO sale de la sala
        if n == 35:
            raise _Fin

    try:
        resultado = lobby.pantalla_sala_espera(pantalla, _Reloj(), presentar, [None] * 4, True, servidor, "127.0.0.1")
    except _Fin:
        resultado = "siguió en la sala"
    assert resultado == "siguió en la sala"
    assert [m.texto for m in servidor.celular.mensajes() if m.tipo == "jugador"] == ["listos"]
    assert _esperar(lambda: any(m.texto == "listos" for m in cliente.celular.mensajes()))


# ----------------------------------------------------------------------
# Repost, abrir una publicación y comentar
# ----------------------------------------------------------------------

def test_repost_y_me_gusta_tienen_su_animacion():
    from Online.celular import DURACION_GOLPE, Celular
    celular = Celular()
    assert celular.alternar_repost(5) and celular.alternar_me_gusta(5)
    assert celular.golpe((5, 1)) == 0.0 and celular.golpe((5, 0)) == 0.0
    celular.actualizar(DURACION_GOLPE / 2)
    assert 0.4 < celular.golpe((5, 1)) < 0.6
    celular.actualizar(DURACION_GOLPE)
    assert celular.golpe((5, 1)) is None
    assert not celular.alternar_repost(5) and 5 not in celular.reposts


def test_comentar_en_una_publicacion_abierta():
    from Online.celular import CHAT, Celular
    celular = Celular()
    celular.abrir()
    celular.abrir_publicacion(7)
    celular.escribir("muy bueno")
    assert celular.texto == "" and celular.texto_comentario == "muy bueno"  # no se mezcla con el chat
    assert celular.comentar(12.0) == "muy bueno" and celular.texto_comentario == ""  # lo publica el host
    celular.abrir_conversacion(1)
    celular.escribir("hola")
    assert celular.texto == "hola" and celular.app == CHAT


def test_los_comentarios_de_antes_son_iguales_en_todas_las_pcs():
    from Online.feed_celular import MAX_COMENTARIOS_DETALLE, MIN_COMENTARIOS_DETALLE, FeedCelular
    host, invitado = FeedCelular(99), FeedCelular(99)
    host.avanzar(400)
    for t in range(1, 401):
        invitado.avanzar(t)
    for a, b in zip(host.publicaciones, invitado.publicaciones):
        uno, otro = host.comentarios_anteriores(a), invitado.comentarios_anteriores(b)
        assert MIN_COMENTARIOS_DETALLE <= len(uno) <= MAX_COMENTARIOS_DETALLE
        assert [(c.autor, c.texto) for c in uno] == [(c.autor, c.texto) for c in otro]
        assert all(c.autor != a.autor for c in uno)


def test_clic_abre_la_publicacion_comenta_y_esc_vuelve(correr, red_real):
    servidor, _ = red_real
    red = _red_con_servidor(servidor, cuando=10_000, espejo=False)
    vistos = {}

    def guion(n, loc):
        celular = loc["celular"]
        if n == 3:
            _tecla(pygame.K_c)
        if n == 12:
            dibujo = celular._dibujado
            _clic(dibujo.reposts[0][1].center)
            vistos["id"] = dibujo.publicaciones[0][0]
            _clic(dibujo.publicaciones[0][1].center)
        if n == 15:
            vistos["abierta"] = celular.estado.publicacion_abierta
            vistos["repost"] = set(celular.estado.reposts)
            _texto("cierto")
            _tecla(pygame.K_c)  # al comentar, la C no cierra el celular
            _tecla(pygame.K_RETURN)
        if n == 18:
            _tecla(pygame.K_ESCAPE)  # vuelve al feed, no cierra
        if n == 20:
            vistos["fin"] = (celular.abierto, celular.estado.publicacion_abierta)
            return True
        return False

    correr(red, guion, id_local=0, preparar=_impostor_j2)
    assert vistos["abierta"] == vistos["id"] and len(vistos["repost"]) == 1
    assert vistos["fin"][:2] == (True, None)
    comentarios = [(m.autor, m.publicacion, m.texto) for m in servidor.celular.mensajes() if m.tipo == "comentario"]
    assert comentarios == [(0, vistos["id"], "cierto")]  # viaja por la red: lo ven todos



# ----------------------------------------------------------------------
# Chats privados y comentarios compartidos por red
# ----------------------------------------------------------------------

def _tres_por_red():
    servidor = Servidor()
    servidor.iniciar(0, interfaz="127.0.0.1")
    uno, dos = Cliente(), Cliente()
    assert uno.conectar("127.0.0.1", servidor.puerto) and dos.conectar("127.0.0.1", servidor.puerto)
    assert _esperar(lambda: uno.celular.sincronizado and dos.celular.sincronizado and servidor.sala.cantidad() == 3)
    return servidor, uno, dos


def test_un_privado_solo_lo_reciben_sus_dos_jugadores():
    servidor, uno, dos = _tres_por_red()
    try:
        assert uno.escribir_chat("solo para el host", destino=0)
        assert servidor.escribir_chat("solo para J2", destino=uno.id_jugador)
        assert dos.escribir_chat("para todos")
        assert _esperar(lambda: len([m for m in uno.celular.mensajes() if m.tipo == "jugador"]) == 3)
        assert _esperar(lambda: any(m.texto == "para todos" for m in dos.celular.mensajes()))
        textos_dos = [m.texto for m in dos.celular.mensajes() if m.tipo == "jugador"]
        assert textos_dos == ["para todos"]  # J3 no recibe los privados ajenos
        # Quien entra después tampoco recibe privados ajenos en su SYNC.
        tres = Cliente()
        assert tres.conectar("127.0.0.1", servidor.puerto)
        assert _esperar(lambda: tres.celular.sincronizado)
        assert [m.texto for m in tres.celular.mensajes() if m.tipo == "jugador"] == ["para todos"]
        tres.detener()
        # Cada jugador ve sus chats separados, con sus no leídos.
        assert servidor.celular.no_leidos_por_conversacion(0) == {uno.id_jugador: 1, SALA: 1}
        servidor.celular.marcar_leidos(uno.id_jugador)
        assert servidor.celular.no_leidos(0) == 1
    finally:
        uno.detener()
        dos.detener()
        servidor.detener()


def test_los_comentarios_de_un_jugador_les_llegan_a_todos():
    servidor, uno, dos = _tres_por_red()
    try:
        assert uno.comentar(4, "esto es falso")
        assert _esperar(lambda: any(m.tipo == "comentario" for m in dos.celular.mensajes()))
        comentario = next(m for m in dos.celular.mensajes() if m.tipo == "comentario")
        assert (comentario.autor, comentario.publicacion, comentario.texto) == (uno.id_jugador, 4, "esto es falso")
        assert any(m.tipo == "comentario" and m.publicacion == 4 for m in servidor.celular.mensajes())
        assert servidor.celular.no_leidos(0) == 0  # un comentario no es un mensaje de chat
    finally:
        uno.detener()
        dos.detener()
        servidor.detener()


def test_la_lista_de_chats_tiene_la_sala_y_a_cada_jugador_conectado():
    servidor, uno, dos = _tres_por_red()
    try:
        perfiles = {0: "J1 · Ciudadano", uno.id_jugador: "J2 · Candidato", dos.id_jugador: "J3 · Periodista"}
        from Online.celular import Perfil
        celular = ControlCelular.para_sala(servidor, lambda jid: Perfil(perfiles.get(jid, "?"), (200, 200, 200),
                                                                         "candidato"))
        uno.escribir_chat("hola host", destino=0)
        assert _esperar(lambda: any(m.texto == "hola host" for m in servidor.celular.mensajes()))
        contactos = celular.contactos()
        assert [c.conversacion for c in contactos] == [SALA, uno.id_jugador, dos.id_jugador]
        privado = contactos[1]
        assert privado.etiqueta == "J2 · Candidato" and privado.vista_previa == "hola host" and privado.no_leidos == 1
    finally:
        uno.detener()
        dos.detener()
        servidor.detener()
