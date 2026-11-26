"""Apariencias de los vestidores por la red: el GrafoSala guarda una por
jugador y la manda con el lobby, ELEGIR_APARIENCIA viaja por el protocolo
y, con servidor y clientes reales en 127.0.0.1, cada invitado solo se
viste a sí mismo y todos ven lo que eligieron los demás."""

import json
import os
import socket
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest  # noqa: E402

from Online.cliente import Cliente  # noqa: E402
from Online.protocolo import (  # noqa: E402
    BIENVENIDA, ELEGIR_APARIENCIA, LOBBY, GrafoSala, deserializar_buffer,
    msg_elegir_apariencia, msg_lobby,
)
from Online.servidor import Servidor  # noqa: E402
from src.core.apariencia import PREDETERMINADA, Apariencia  # noqa: E402

VESTIDO = Apariencia(piel=5, cabeza="candidato", traje="periodista")


def _sala(*ids):
    sala = GrafoSala()
    for jid in ids:
        sala.conectar(jid)
    return sala


def _apariencias(sala_dict):
    """{id: Apariencia} de un lobby recibido por red."""
    sala = GrafoSala.de_dict(sala_dict)
    return {jid: sala.apariencia_de(jid) for jid in sala.jugadores()}


# --- GrafoSala y protocolo (sin red) -------------------------------------

def test_conectar_deja_la_apariencia_predeterminada():
    sala = _sala(0, 1)
    assert sala.apariencia_de(0) == PREDETERMINADA
    assert sala.apariencia_de(1) == PREDETERMINADA
    assert sala.apariencia_de(3) == PREDETERMINADA  # nunca se conectó


def test_elegir_apariencia_con_una_apariencia_o_con_el_dict_de_la_red():
    sala = _sala(0, 1, 2)
    sala.elegir_apariencia(0, VESTIDO)
    assert sala.apariencia_de(0) == VESTIDO
    # El dict que llega por red se valida campo por campo.
    sala.elegir_apariencia(1, {"piel": 99, "cabeza": "influencer", "traje": "astronauta"})
    assert sala.apariencia_de(1) == Apariencia(cabeza="influencer")
    assert isinstance(sala.apariencia_de(1), Apariencia)
    sala.elegir_apariencia(2, VESTIDO.a_dict())
    assert sala.apariencia_de(2) == VESTIDO
    # Cada nodo guarda la suya.
    sala.elegir_apariencia(0, PREDETERMINADA)
    assert sala.apariencia_de(0) == PREDETERMINADA
    assert sala.apariencia_de(2) == VESTIDO


def test_desconectar_borra_la_apariencia():
    sala = _sala(0, 1)
    sala.elegir_apariencia(1, VESTIDO)
    sala.desconectar(1)
    assert 1 not in sala._apariencias
    assert sala.apariencia_de(1) == PREDETERMINADA
    assert [jugador["id"] for jugador in sala.a_dict()["jugadores"]] == [0]
    sala.conectar(1)  # quien vuelve con ese id llega con la de su rol
    assert sala.apariencia_de(1) == PREDETERMINADA
    sala.desconectar(5)  # alguien que no está: no lanza


def test_a_dict_incluye_la_apariencia_de_cada_jugador():
    sala = _sala(0, 1)
    sala.elegir_rol(0, "Candidato")
    sala.elegir_apariencia(0, VESTIDO)
    colores = {"pelo": None, "ropa": None, "pantalon": None, "zapatos": None}  # HAIR, SHIRT, PANTS y SHOES sin tocar
    assert sala.a_dict() == {"jugadores": [
        {"id": 0, "rol": "Candidato", "apariencia": {"piel": 5, "cabeza": "candidato", "traje": "periodista", **colores}},
        {"id": 1, "rol": None, "apariencia": {"piel": None, "cabeza": None, "traje": None, **colores}},
    ]}
    assert json.loads(json.dumps(sala.a_dict())) == sala.a_dict()  # viaja como JSON


def test_de_dict_ida_y_vuelta():
    sala = _sala(0, 1, 2)
    sala.elegir_rol(1, "Periodista")
    sala.elegir_apariencia(1, VESTIDO)
    sala.elegir_apariencia(2, Apariencia(piel=0))
    copia = GrafoSala.de_dict(json.loads(json.dumps(sala.a_dict())))
    assert copia.jugadores() == [0, 1, 2]
    assert [copia.apariencia_de(jid) for jid in (0, 1, 2)] == [PREDETERMINADA, VESTIDO, Apariencia(piel=0)]
    assert copia.rol_de(1) == "Periodista"
    assert copia.a_dict() == sala.a_dict()


def test_de_dict_de_un_host_sin_vestidores():
    # Versión del juego anterior a los vestidores: los jugadores no traen "apariencia".
    sala = GrafoSala.de_dict({"jugadores": [{"id": 0, "rol": "Ciudadano"}, {"id": 1, "rol": None}]})
    assert sala.jugadores() == [0, 1]
    assert sala.rol_de(0) == "Ciudadano"
    assert sala.apariencia_de(0) == PREDETERMINADA
    assert sala.apariencia_de(1) == PREDETERMINADA


@pytest.mark.parametrize("basura", [None, "rojo", 7, [1, 2], {}, {"piel": True, "cabeza": 3, "traje": ["candidato"]}])
def test_de_dict_con_una_apariencia_basura_no_lanza(basura):
    sala = GrafoSala.de_dict({"jugadores": [{"id": 0, "rol": "Influencer", "apariencia": basura}]})
    assert sala.jugadores() == [0]
    assert sala.rol_de(0) == "Influencer"
    assert sala.apariencia_de(0) == PREDETERMINADA


def test_msg_elegir_apariencia_ida_y_vuelta():
    datos = msg_elegir_apariencia(1, VESTIDO.a_dict())
    mensajes, resto = deserializar_buffer(datos)
    assert resto == b""
    assert mensajes == [{"tipo": ELEGIR_APARIENCIA, "id": 1, "apariencia": VESTIDO.a_dict()}]
    assert Apariencia.de_dict(mensajes[0]["apariencia"]) == VESTIDO
    # TCP puede partirlo: a medias no sale nada y el trozo se guarda.
    mitad = len(datos) // 2
    assert deserializar_buffer(datos[:mitad]) == ([], datos[:mitad])
    assert deserializar_buffer(datos[:mitad] + datos[mitad:] + datos) == (mensajes * 2, b"")


def test_enviar_apariencia_manda_su_dict_con_el_id_propio():
    lado_cliente, lado_servidor = socket.socketpair()
    cliente = Cliente()
    cliente._socket, cliente.conectado, cliente.id_jugador = lado_cliente, True, 2
    try:
        cliente.enviar_apariencia(VESTIDO)
        lado_servidor.settimeout(2.0)
        mensajes, buffer = [], b""
        while not mensajes:
            trozo = lado_servidor.recv(4096)
            assert trozo
            mensajes, buffer = deserializar_buffer(buffer + trozo)
    finally:
        lado_cliente.close()
        lado_servidor.close()
    assert mensajes == [{"tipo": ELEGIR_APARIENCIA, "id": 2, "apariencia": VESTIDO.a_dict()}]


# --- Host e invitados reales en 127.0.0.1 --------------------------------

def _esperar(condicion, limite_s=5.0):
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
    """Conecta un invitado y espera a que procese su BIENVENIDA (id y sala).
    Queda en `invitados` antes de conectar: el finally lo detiene siempre."""
    cliente = Cliente()
    invitados.append(cliente)
    assert cliente.conectar("127.0.0.1", servidor.puerto), cliente.error
    assert _esperar(lambda: cliente.id_jugador is not None and cliente.id_jugador in cliente.sala.jugadores())
    return cliente


def _cerrar(servidor, invitados):
    for cliente in invitados:
        cliente.detener()
    servidor.detener()


def test_el_invitado_se_viste_y_lo_ven_el_host_y_el_mismo():
    servidor = _abrir_servidor()
    invitados = []
    try:
        invitado = _unir(servidor, invitados)
        assert invitado.id_jugador == 1
        invitado.enviar_apariencia(VESTIDO)

        # El servidor la guarda en el nodo de ESE invitado.
        assert _esperar(lambda: servidor.sala.apariencia_de(1) == VESTIDO)
        assert servidor.sala.apariencia_de(0) == PREDETERMINADA

        # El host se entera por su cola con un LOBBY que ya la trae.
        cola_host = []

        def host_recibio_lobby():
            cola_host.extend(servidor.leer_mensajes())
            return any(m.get("tipo") == LOBBY and _apariencias(m["sala"]).get(1) == VESTIDO for m in cola_host)

        assert _esperar(host_recibio_lobby)

        # Y el propio invitado la recibe de vuelta en su copia de la sala.
        assert _esperar(lambda: invitado.sala.apariencia_de(1) == VESTIDO)
        assert invitado.sala.apariencia_de(0) == PREDETERMINADA
    finally:
        _cerrar(servidor, invitados)


def test_el_host_se_viste_y_el_invitado_lo_ve():
    servidor = _abrir_servidor()
    invitados = []
    try:
        invitado = _unir(servidor, invitados)
        servidor.sala.elegir_apariencia(0, VESTIDO)
        servidor.enviar_a_todos(msg_lobby(servidor.sala.a_dict()))
        assert _esperar(lambda: invitado.sala.apariencia_de(0) == VESTIDO)
        assert invitado.sala.apariencia_de(1) == PREDETERMINADA
    finally:
        _cerrar(servidor, invitados)


@pytest.mark.parametrize("id_ajeno", [0, 2])
def test_un_invitado_no_puede_vestir_a_otro_jugador(id_ajeno):
    servidor = _abrir_servidor()
    invitados = []
    try:
        invitado = _unir(servidor, invitados)
        otro = _unir(servidor, invitados)
        assert (invitado.id_jugador, otro.id_jugador) == (1, 2)
        # Armado a mano con el id del host o del otro invitado, por su propio socket.
        invitado._enviar(msg_elegir_apariencia(id_ajeno, VESTIDO.a_dict()))
        # Se espera a que aparezca en cualquier nodo: si cae en el ajeno, falla al instante.
        assert _esperar(lambda: VESTIDO in [servidor.sala.apariencia_de(jid) for jid in (0, 1, 2)])
        assert [servidor.sala.apariencia_de(jid) for jid in (0, 1, 2)] == [PREDETERMINADA, VESTIDO, PREDETERMINADA]
        # Y así lo ven los demás.
        assert _esperar(lambda: otro.sala.apariencia_de(1) == VESTIDO)
        assert otro.sala.apariencia_de(id_ajeno) == PREDETERMINADA
    finally:
        _cerrar(servidor, invitados)


def test_el_que_llega_despues_recibe_las_apariencias_en_la_bienvenida():
    servidor = _abrir_servidor()
    invitados = []
    try:
        primero = _unir(servidor, invitados)
        ropa_primero = Apariencia(piel=3, traje="candidato")
        primero.enviar_apariencia(ropa_primero)
        assert _esperar(lambda: servidor.sala.apariencia_de(1) == ropa_primero)
        ropa_host = Apariencia(cabeza="periodista")
        servidor.sala.elegir_apariencia(0, ropa_host)

        nuevo = _unir(servidor, invitados)
        cola = []

        def llego_bienvenida():
            cola.extend(nuevo.leer_mensajes())
            return any(m.get("tipo") == BIENVENIDA for m in cola)

        assert _esperar(llego_bienvenida)
        bienvenida = next(m for m in cola if m.get("tipo") == BIENVENIDA)
        assert bienvenida["id"] == 2
        assert _apariencias(bienvenida["sala"]) == {0: ropa_host, 1: ropa_primero, 2: PREDETERMINADA}
        assert nuevo.sala.apariencia_de(0) == ropa_host
        assert nuevo.sala.apariencia_de(1) == ropa_primero
    finally:
        _cerrar(servidor, invitados)


def test_al_irse_un_invitado_su_apariencia_se_borra_y_no_se_hereda():
    servidor = _abrir_servidor()
    invitados = []
    try:
        primero = _unir(servidor, invitados)
        segundo = _unir(servidor, invitados)
        primero.enviar_apariencia(VESTIDO)
        assert _esperar(lambda: segundo.sala.apariencia_de(1) == VESTIDO)

        primero.detener()
        assert _esperar(lambda: segundo.sala.jugadores() == [0, 2])
        assert servidor.sala.jugadores() == [0, 2]
        assert servidor.sala.apariencia_de(1) == PREDETERMINADA

        # El siguiente que ocupa el id 1 llega con la de su rol.
        tercero = _unir(servidor, invitados)
        assert tercero.id_jugador == 1
        assert tercero.sala.apariencia_de(1) == PREDETERMINADA
        assert servidor.sala.apariencia_de(1) == PREDETERMINADA
    finally:
        _cerrar(servidor, invitados)


def test_una_apariencia_rota_por_la_red_no_tumba_al_servidor():
    servidor = _abrir_servidor()
    invitados = []
    try:
        invitado = _unir(servidor, invitados)
        invitado._enviar(msg_elegir_apariencia(1, {"piel": "rojo", "cabeza": "candidato", "traje": ["periodista"]}))
        assert _esperar(lambda: servidor.sala.apariencia_de(1) == Apariencia(cabeza="candidato"))
        # Sigue atendiendo: la siguiente elección llega a todos.
        invitado.enviar_apariencia(VESTIDO)
        assert _esperar(lambda: invitado.sala.apariencia_de(1) == VESTIDO)
        assert servidor.sala.apariencia_de(1) == VESTIDO
    finally:
        _cerrar(servidor, invitados)
