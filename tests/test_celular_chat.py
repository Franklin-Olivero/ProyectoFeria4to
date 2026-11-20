"""Celular del modo Online: el chat de la sala y el reloj compartido
(Online/chat_celular.py, lógica pura). Limpiar el texto, la cola acotada
ordenada por número, recibir sin duplicar ni desordenar, el sync, los no
leídos, el anti-spam y los silenciados que hace cumplir el host."""

import json
import os
import subprocess
import sys
import threading
from itertools import count

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pytest  # noqa: E402

from Online.chat_celular import (  # noqa: E402
    EVENTO_CHAT, EVENTO_SYNC, INTERVALO_MINIMO_CHAT_S, JUGADOR, MAX_LARGO_MENSAJE_CELULAR, MAX_MENSAJES_CELULAR,
    MAX_RELOJ_SYNC_S, SISTEMA_ENTRO, SISTEMA_SALIO, CanalCelular, HistorialChat, MensajeChat, limpiar_texto,
)

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


class _Reloj:
    """Reloj inyectable: solo avanza cuando el test lo mueve (valores exactos en binario)."""

    def __init__(self, inicio=100.0):
        self.ahora = inicio

    def __call__(self):
        return self.ahora

    def avanzar(self, segundos):
        self.ahora += segundos


def _mensaje(numero, autor=1, texto="hola", segundos=1.0, tipo=JUGADOR):
    return MensajeChat(numero, autor, texto, segundos, tipo)


def _numeros(mensajes):
    return [m.numero for m in mensajes]


def test_modulo_no_importa_pygame():
    codigo = "import sys, Online.chat_celular; print('pygame' in sys.modules)"
    salida = subprocess.run([sys.executable, "-c", codigo], cwd=RAIZ, capture_output=True, text=True, check=True)
    assert salida.stdout.strip() == "False"


def test_las_constantes_del_contrato():
    assert MAX_LARGO_MENSAJE_CELULAR == 80 and MAX_MENSAJES_CELULAR == 200 and INTERVALO_MINIMO_CHAT_S == 0.3
    assert (JUGADOR, SISTEMA_ENTRO, SISTEMA_SALIO) == ("jugador", "entro", "salio")
    assert (EVENTO_SYNC, EVENTO_CHAT) == ("sync", "chat")


# ----------------------------------------------------------------------
# Limpiar el texto
# ----------------------------------------------------------------------

@pytest.mark.parametrize("texto, esperado", [
    ("  hola   equipo ", "hola equipo"),
    ("a\nb\tc\r\nd", "a b c d"),  # un solo renglón
    ("\x00\x07hola\x1b", "hola"),  # caracteres de control fuera
    ("hola  mundo", "hola mundo"),  # espacios raros también se colapsan
    ("¡Hola! ¿Vamos a la Alcaldía? Ñandú", "¡Hola! ¿Vamos a la Alcaldía? Ñandú"),  # tildes, ñ y signos se quedan
    ("x" * 200, "x" * MAX_LARGO_MENSAJE_CELULAR),
    ("a" * 79 + " bcd", "a" * 79),  # el corte no deja un espacio al final
    ("", ""), ("   \n\t ", ""),
    (None, ""), (5, ""), (["hola"], ""), (b"hola", ""),
])
def test_limpiar_texto(texto, esperado):
    assert limpiar_texto(texto) == esperado


# ----------------------------------------------------------------------
# MensajeChat: ida y vuelta por la red y tolerancia a basura
# ----------------------------------------------------------------------

def test_mensaje_ida_y_vuelta():
    mensaje = MensajeChat(3, 1, "hola", 12.3456, JUGADOR)
    datos = mensaje.a_dict()
    assert datos == {"n": 3, "a": 1, "t": "hola", "s": 12.35, "k": JUGADOR}
    assert json.loads(json.dumps(datos)) == datos  # cabe en el JSON del protocolo
    assert MensajeChat.de_dict(datos) == MensajeChat(3, 1, "hola", 12.35, JUGADOR)
    sistema = MensajeChat(4, 2, "", 7.0, SISTEMA_SALIO)
    assert MensajeChat.de_dict(sistema.a_dict()) == sistema


def test_de_dict_vuelve_a_limpiar_el_texto():
    base = {"n": 1, "a": 2, "s": 0.5, "k": JUGADOR}
    assert MensajeChat.de_dict(dict(base, t="  hola\n  mundo ")).texto == "hola mundo"
    assert MensajeChat.de_dict(dict(base, t="z" * 500)).texto == "z" * MAX_LARGO_MENSAJE_CELULAR
    # Los del sistema no traen texto: lo arma la interfaz ("J3 entró a la sala").
    assert MensajeChat.de_dict(dict(base, t="texto colado", k=SISTEMA_ENTRO)).texto == ""
    assert MensajeChat.de_dict(dict(base, t="ok", extra=[1, 2])) is not None  # claves de más no molestan


VALIDO = {"n": 1, "a": 2, "t": "hola", "s": 1.5, "k": JUGADOR}


@pytest.mark.parametrize("basura", [
    None, "hola", 5, [], [1, 2, "hola"], {},
    dict(VALIDO, n=0), dict(VALIDO, n=-3), dict(VALIDO, n=True), dict(VALIDO, n="3"), dict(VALIDO, n=2.0),
    dict(VALIDO, n=None),
    dict(VALIDO, a=16), dict(VALIDO, a=-1), dict(VALIDO, a=True), dict(VALIDO, a=None), dict(VALIDO, a=1.0),
    dict(VALIDO, s=float("nan")), dict(VALIDO, s=float("inf")), dict(VALIDO, s="1"), dict(VALIDO, s=None),
    dict(VALIDO, s=False), dict(VALIDO, s=10**400),
    dict(VALIDO, k="otro"), dict(VALIDO, k=None), dict(VALIDO, k=["jugador"]),
    {"n": 1, "a": 2, "t": "hola", "s": 1.5},  # sin tipo
    dict(VALIDO, t=""), dict(VALIDO, t="   "), dict(VALIDO, t=None), dict(VALIDO, t=5),  # JUGADOR sin texto
])
def test_de_dict_tolera_basura(basura):
    assert MensajeChat.de_dict(basura) is None


# ----------------------------------------------------------------------
# HistorialChat: cola acotada ordenada por número
# ----------------------------------------------------------------------

def test_el_host_numera_1_2_3_y_limpia():
    historial = HistorialChat()
    assert len(historial) == 0 and historial.ultimo_numero() == 0 and historial.mensajes() == ()
    primero = historial.publicar(0, "  hola  ", 1.0)
    assert primero == MensajeChat(1, 0, "hola", 1.0, JUGADOR)
    assert historial.publicar(1, "", 2.0) is None  # vacío: no sale ni gasta número
    assert historial.publicar(1, "chao", 2.0, tipo="inventado") is None
    assert historial.publicar(99, "chao", 2.0) is None  # autor fuera de rango
    assert historial.publicar(1, "vamos", 3.0).numero == 2
    entro = historial.publicar(2, "lo que sea", 4.0, tipo=SISTEMA_ENTRO)
    assert (entro.numero, entro.texto, entro.tipo) == (3, "", SISTEMA_ENTRO)
    assert _numeros(historial.mensajes()) == [1, 2, 3] and historial.ultimo_numero() == 3 and len(historial) == 3


def test_tope_descarta_los_mas_viejos():
    historial = HistorialChat(maximo=5)
    for i in range(8):
        historial.publicar(1, f"mensaje {i}", float(i))
    assert _numeros(historial.mensajes()) == [4, 5, 6, 7, 8] and historial.ultimo_numero() == 8
    assert historial.publicar(1, "otro", 9.0).numero == 9  # la numeración sigue aunque se descarten
    grande = HistorialChat()
    for i in range(MAX_MENSAJES_CELULAR + 40):
        grande.publicar(i % 4, f"m{i}", float(i))
    assert len(grande) == MAX_MENSAJES_CELULAR
    assert _numeros(grande.mensajes()) == list(range(41, MAX_MENSAJES_CELULAR + 41))


def test_recibir_sin_duplicar_y_desordenado():
    historial = HistorialChat()
    assert historial.recibir(_mensaje(3)) and historial.recibir(_mensaje(1)) and historial.recibir(_mensaje(2))
    assert not historial.recibir(_mensaje(3, texto="otro texto"))  # mismo número: ya estaba (llegó en el SYNC)
    assert not historial.recibir({"n": 4, "a": 1, "t": "hola", "s": 1.0, "k": JUGADOR})  # un dict no: de_dict primero
    assert historial.recibir(_mensaje(7)) and historial.recibir(_mensaje(5))
    assert _numeros(historial.mensajes()) == [1, 2, 3, 5, 7] and historial.ultimo_numero() == 7
    assert historial.mensajes()[2].texto == "hola"  # ganó el primero


def test_recibir_respeta_el_tope():
    historial = HistorialChat(maximo=3)
    for numero in (5, 7, 8):
        assert historial.recibir(_mensaje(numero))
    assert not historial.recibir(_mensaje(2))  # más viejo que todo con la cola llena: no queda
    assert _numeros(historial.mensajes()) == [5, 7, 8]
    assert historial.recibir(_mensaje(6))  # desordenado: entra en su lugar y sale el más viejo
    assert _numeros(historial.mensajes()) == [6, 7, 8]
    assert historial.recibir(_mensaje(9))  # el más nuevo, al final
    assert _numeros(historial.mensajes()) == [7, 8, 9]
    assert not historial.recibir(_mensaje(6))  # el que salió por el tope no vuelve a entrar
    assert not historial.recibir(_mensaje(8))  # repetido
    assert _numeros(historial.mensajes()) == [7, 8, 9] and len(historial) == 3


def test_reemplazar_deja_exactamente_esos():
    historial = HistorialChat(maximo=4)
    historial.publicar(1, "viejo", 1.0)
    historial.reemplazar([_mensaje(9), _mensaje(2, texto="primero"), "basura", _mensaje(2, texto="repetido"),
                          None, _mensaje(5)])
    assert _numeros(historial.mensajes()) == [2, 5, 9] and historial.mensajes()[0].texto == "primero"
    assert not historial.recibir(_mensaje(5)) and historial.recibir(_mensaje(6))
    historial.reemplazar([_mensaje(1), _mensaje(3)])
    assert historial.recibir(_mensaje(2))  # el set de números también se rehízo: el 2 ya no está
    assert _numeros(historial.mensajes()) == [1, 2, 3]
    historial.reemplazar(_mensaje(n) for n in range(1, 11))  # acotado: los 4 más nuevos
    assert _numeros(historial.mensajes()) == [7, 8, 9, 10] and not historial.recibir(_mensaje(8))
    historial.reemplazar([])
    assert len(historial) == 0 and historial.ultimo_numero() == 0


def test_no_leidos_solo_cuenta_mensajes_de_otros():
    historial = HistorialChat()
    historial.publicar(0, "mio", 1.0)  # 1: propio (host)
    historial.publicar(1, "de J2", 2.0)  # 2
    historial.publicar(2, "", 3.0, tipo=SISTEMA_ENTRO)  # 3: del sistema, no cuenta
    historial.publicar(2, "de J3", 4.0)  # 4
    historial.publicar(1, "otra vez J2", 5.0)  # 5
    assert historial.no_leidos(0, 0) == 3
    assert historial.no_leidos(4, 0) == 1
    assert historial.no_leidos(5, 0) == 0
    assert historial.no_leidos(0, 1) == 2  # J2 no cuenta los suyos: el del host y el de J3
    assert historial.no_leidos(None, 0) == 3  # leido_hasta roto: como si no hubiera leído nada


def test_a_lista_es_el_historial_del_sync():
    historial = HistorialChat()
    historial.publicar(0, "hola", 1.25)
    historial.publicar(3, "", 2.5, tipo=SISTEMA_SALIO)
    lista = historial.a_lista()
    assert lista == [{"n": 1, "a": 0, "t": "hola", "s": 1.25, "k": JUGADOR},
                     {"n": 2, "a": 3, "t": "", "s": 2.5, "k": SISTEMA_SALIO}]
    copia = HistorialChat()
    copia.reemplazar(MensajeChat.de_dict(datos) for datos in lista)
    assert copia.mensajes() == historial.mensajes()


# ----------------------------------------------------------------------
# CanalCelular: lo que comparte la red de la sala
# ----------------------------------------------------------------------

def test_el_canal_publica_con_su_reloj_y_numera():
    reloj = _Reloj(50.0)
    canal = CanalCelular(semilla=1234, reloj=reloj)
    assert canal.semilla == 1234 and canal.sincronizado and canal.leido_hasta == 0 and canal.silenciados == set()
    reloj.avanzar(2.5)
    mensaje = canal.publicar(1, "  hola  sala ")
    assert mensaje == MensajeChat(1, 1, "hola sala", 2.5, JUGADOR)
    assert canal.publicar(2, "   ") is None  # vacío
    for autor_roto in ("1", None, True, 1.0, [1]):
        assert canal.publicar(autor_roto, "hola") is None
    assert canal.publicar(2, "hola", tipo="inventado") is None
    assert canal.publicar(2, "yo también").numero == 2
    assert canal.ultimo_numero() == 2 and len(canal.mensajes()) == 2


def test_semilla_al_azar_si_no_la_dan():
    canal = CanalCelular()
    assert isinstance(canal.semilla, int) and 1 <= canal.semilla < 2**31
    assert CanalCelular(semilla=7).semilla == 7


def test_anti_spam_por_autor_con_reloj_inyectable():
    reloj = _Reloj()
    canal = CanalCelular(reloj=reloj)
    assert canal.publicar(1, "uno") is not None  # en t = 0
    assert canal.publicar(1, "dos") is None  # mismo instante
    assert canal.publicar(2, "otro autor") is not None  # el anti-spam es por autor
    assert canal.publicar(1, "", SISTEMA_SALIO) is not None  # los del sistema no esperan
    reloj.avanzar(0.25)
    assert canal.publicar(1, "tres") is None  # 0.25 s < INTERVALO_MINIMO_CHAT_S
    reloj.avanzar(0.25)
    assert canal.publicar(1, "cuatro") is not None  # 0.5 s desde "uno"
    reloj.avanzar(0.25)
    assert canal.publicar(1, "cinco") is None  # 0.25 s desde "cuatro"
    reloj.avanzar(0.125)
    # 0.375 s desde "cuatro": el intento rechazado no reinició la espera.
    assert canal.publicar(1, "seis") is not None
    assert canal.publicar(3, "   ") is None
    assert canal.publicar(3, "un texto vacío no gasta la espera") is not None
    assert [m.texto for m in canal.mensajes() if m.autor == 1 and m.tipo == JUGADOR] == ["uno", "cuatro", "seis"]


def test_silenciados_no_escriben_pero_si_aparecen_en_el_sistema():
    canal = CanalCelular(reloj=_Reloj())
    canal.silenciados = {2}
    assert canal.publicar(2, "soy un fantasma") is None
    assert canal.publicar(1, "yo sí puedo") is not None
    assert canal.publicar(2, "", SISTEMA_SALIO) is not None  # "J3 salió de la sala" sí se anuncia
    canal.silenciados = set()
    assert canal.publicar(2, "ya puedo hablar") is not None
    assert [m.texto for m in canal.mensajes() if m.tipo == JUGADOR] == ["yo sí puedo", "ya puedo hablar"]


def test_el_invitado_copia_semilla_reloj_y_chat_del_host():
    reloj_host = _Reloj(50.0)
    host = CanalCelular(semilla=4321, reloj=reloj_host)
    reloj_host.avanzar(80.0)
    host.publicar(0, "bienvenidos")
    host.publicar(1, "", SISTEMA_ENTRO)
    reloj_host.avanzar(10.0)
    assert host.segundos() == 90.0

    reloj_invitado = _Reloj(7.0)
    invitado = CanalCelular(sincronizado=False, reloj=reloj_invitado)
    assert not invitado.sincronizado
    reloj_invitado.avanzar(3.0)
    assert invitado.segundos() == 3.0  # antes del SYNC cuenta solo

    datos = host.a_sync()
    assert set(datos) == {"semilla", "t", "chat"} and json.loads(json.dumps(datos)) == datos
    invitado.sincronizar(datos["semilla"], datos["t"], datos["chat"])
    assert invitado.sincronizado and invitado.semilla == 4321
    assert invitado.segundos() == 90.0
    reloj_host.avanzar(5.0)
    reloj_invitado.avanzar(5.0)
    assert invitado.segundos() == host.segundos() == 95.0  # cada uno con su reloj, el mismo instante del feed
    assert invitado.mensajes() == host.mensajes() and invitado.ultimo_numero() == 2


@pytest.mark.parametrize("semilla, segundos, chat, semilla_final, segundos_final", [
    ("x", float("nan"), "no es una lista", 99, 2.0),
    (None, None, None, 99, 2.0),
    (True, -5.0, {"n": 1}, 99, 2.0),
    (3.5, float("inf"), 7, 99, 2.0),
    (12, MAX_RELOJ_SYNC_S + 1, None, 12, 2.0),  # reloj absurdo: el feed tendría que simularlo de golpe
    (12, "90", None, 12, 2.0),
    ("12", 90.0, None, 99, 90.0),  # la parte válida se copia igual
])
def test_un_sync_con_basura_no_rompe_nada(semilla, segundos, chat, semilla_final, segundos_final):
    reloj = _Reloj(10.0)
    invitado = CanalCelular(semilla=99, sincronizado=False, reloj=reloj)
    invitado.recibir({"n": 4, "a": 1, "t": "ya estaba", "s": 1.0, "k": JUGADOR})
    reloj.avanzar(2.0)
    invitado.sincronizar(semilla, segundos, chat)
    assert not invitado.sincronizado  # sin semilla Y reloj válidos no queda sincronizado
    assert invitado.semilla == semilla_final
    assert invitado.segundos() == segundos_final  # un reloj inválido se ignora: sigue el propio
    assert [m.texto for m in invitado.mensajes()] == ["ya estaba"]  # un chat que no es lista se ignora


def test_un_sync_descarta_solo_los_mensajes_rotos():
    invitado = CanalCelular(sincronizado=False, reloj=_Reloj())
    invitado.recibir({"n": 50, "a": 1, "t": "viejo", "s": 1.0, "k": JUGADOR})
    chat = [{"n": 2, "a": 0, "t": "hola", "s": 1.0, "k": JUGADOR}, "basura", None, {"n": -1},
            {"n": 3, "a": 1, "t": "", "s": 2.0, "k": SISTEMA_ENTRO}, {"n": 4, "a": 99, "t": "x", "s": 1.0, "k": JUGADOR},
            {"n": 2, "a": 2, "t": "repetido", "s": 1.0, "k": JUGADOR}]
    invitado.sincronizar(77, 12.5, chat)
    assert invitado.sincronizado and invitado.semilla == 77 and invitado.segundos() == 12.5
    assert [(m.numero, m.texto, m.tipo) for m in invitado.mensajes()] == [(2, "hola", JUGADOR), (3, "", SISTEMA_ENTRO)]
    invitado.sincronizar(78, 13.0, None)  # sin chat: se queda el que tiene
    assert invitado.semilla == 78 and invitado.ultimo_numero() == 3


def test_recibir_en_el_canal():
    canal = CanalCelular(sincronizado=False, reloj=_Reloj())
    datos = {"n": 1, "a": 0, "t": "  hola ", "s": 1.0, "k": JUGADOR}
    assert canal.recibir(datos) == MensajeChat(1, 0, "hola", 1.0, JUGADOR)
    assert canal.recibir(datos) is None  # repetido
    assert canal.recibir({"n": 2, "a": 0, "t": "", "s": 1.0, "k": JUGADOR}) is None
    assert canal.recibir(None) is None and canal.recibir("chat") is None
    assert canal.ultimo_numero() == 1


def test_leidos_y_no_leidos_del_canal():
    canal = CanalCelular(reloj=_Reloj())
    canal.publicar(1, "hola host")
    canal.publicar(2, "hola a todos")
    canal.publicar(0, "hola, soy el host")
    canal.publicar(3, "", SISTEMA_ENTRO)
    assert canal.no_leidos(0) == 2  # los suyos y los del sistema no cuentan
    canal.marcar_leidos()
    assert canal.leido_hasta == canal.ultimo_numero() == 4 and canal.no_leidos(0) == 0
    canal.publicar(3, "llegué")
    assert canal.no_leidos(0) == 1 and canal.no_leidos(3) == 0


def test_hilos_que_publican_a_la_vez_nunca_repiten_numero():
    canal = CanalCelular(reloj=count(0.0, 1.0).__next__)  # cada lectura del reloj avanza 1 s: sin anti-spam
    por_hilo = 60  # más que el tope entre los 4 hilos

    def escribir(autor):
        for i in range(por_hilo):
            canal.publicar(autor, f"J{autor + 1} dice {i}")

    hilos = [threading.Thread(target=escribir, args=(autor,)) for autor in range(4)]
    for hilo in hilos:
        hilo.start()
    for hilo in hilos:
        hilo.join(5)
    total = 4 * por_hilo
    assert canal.ultimo_numero() == total
    assert _numeros(canal.mensajes()) == list(range(total - MAX_MENSAJES_CELULAR + 1, total + 1))
    for autor in range(4):  # los de cada autor quedan en el orden en que los escribió
        suyos = [int(m.texto.split()[-1]) for m in canal.mensajes() if m.autor == autor]
        assert suyos == sorted(suyos)
