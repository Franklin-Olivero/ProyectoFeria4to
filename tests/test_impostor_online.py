"""Impostor del modo Online: sorteo en el host, viaje por la red, pantalla de
revelación con la ropa de los vestidores, lobby y propagación a la partida."""

import os
import random
import time
from types import SimpleNamespace

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame  # noqa: E402
import pytest  # noqa: E402

from src.core import assets  # noqa: E402
from src.core.apariencia import Apariencia  # noqa: E402
from src.entities.candidato import Candidato  # noqa: E402
from src.entities.influencer import Influencer  # noqa: E402
from src.entities.periodista import Periodista  # noqa: E402
from src.entities.player import Ciudadano  # noqa: E402
from src.ui import sprites  # noqa: E402
from Online import lobby, pantalla_rol, registro_errores  # noqa: E402
from Online.cliente import Cliente  # noqa: E402
from Online.pantalla_rol import (  # noqa: E402
    alfa_del_velo, mostrar_pantalla_revelacion_rol, textos_revelacion, tiempo_al_omitir,
)
from Online.protocolo import (  # noqa: E402
    BIENVENIDA, INICIAR, deserializar_buffer, msg_bienvenida, msg_iniciar,
)
from Online.servidor import Servidor  # noqa: E402
from Online.sesion_red import ConfigSesionHost, ConfigSesionJoin, _ids_de_partida  # noqa: E402

CLASES_ROL = [Ciudadano, Influencer, Periodista, Candidato]
ROPA = Apariencia(piel=6, cabeza="candidato", traje="influencer")
DURACION = assets.DURACION_REVELACION
FUNDIDO = assets.DURACION_FUNDIDO_REVELACION


def _servidor_con(*ids):
    servidor = Servidor()
    for jid in ids:
        servidor.sala.conectar(jid)
    return servidor


def _esperar(condicion, limite_s=5.0):
    fin = time.monotonic() + limite_s
    while time.monotonic() < fin:
        if condicion():
            return True
        time.sleep(0.02)
    return condicion()


@pytest.fixture
def azar_intacto():
    """Los tests que siembran `random` no alteran a los que vienen después."""
    estado = random.getstate()
    yield
    random.setstate(estado)


@pytest.fixture
def forzar_impostor(monkeypatch):
    """forzar_impostor(id): el sorteo elige a ese jugador."""
    def forzar(id_jugador):
        monkeypatch.setattr(random, "choice", lambda jugadores: id_jugador)
    return forzar


# ----------------------------------------------------------------------
# Sorteo en el host
# ----------------------------------------------------------------------

@pytest.mark.parametrize("ids", [(0, 1), (0, 1, 2), (0, 1, 2, 3), (0, 2, 3)],
                         ids=["2 jugadores", "3 jugadores", "4 jugadores", "con hueco en los ids"])
def test_el_host_sortea_a_uno_entre_todos_los_conectados(monkeypatch, ids):
    candidatos = []
    monkeypatch.setattr(random, "choice", lambda jugadores: candidatos.extend(jugadores) or jugadores[-1])
    servidor = _servidor_con(*ids)
    servidor.marcar_iniciado()
    assert candidatos == list(ids)
    assert servidor.id_impostor == ids[-1]
    assert servidor.iniciado


@pytest.mark.parametrize("cantidad", [2, 3, 4])
def test_el_sorteo_es_justo(azar_intacto, cantidad):
    random.seed(20261126)
    ids = list(range(cantidad))
    veces = dict.fromkeys(ids, 0)
    sorteos = 3000
    for _ in range(sorteos):
        servidor = _servidor_con(*ids)
        servidor.marcar_iniciado()
        veces[servidor.id_impostor] += 1
    for jid in ids:
        assert veces[jid] / sorteos == pytest.approx(1 / cantidad, abs=0.04)


def test_el_impostor_se_sortea_una_sola_vez_por_partida(forzar_impostor):
    servidor = _servidor_con(0, 1, 2)
    forzar_impostor(1)
    servidor.marcar_iniciado()
    forzar_impostor(2)
    servidor.marcar_iniciado()
    assert servidor.sortear_impostor() == 1


def test_antes_de_iniciar_no_hay_impostor():
    assert _servidor_con(0, 1).id_impostor is None


def test_una_sala_vacia_no_rompe_el_sorteo():
    servidor = Servidor()
    servidor.marcar_iniciado()
    assert servidor.id_impostor is None and servidor.iniciado


# ----------------------------------------------------------------------
# Protocolo y red
# ----------------------------------------------------------------------

def test_iniciar_y_bienvenida_llevan_al_impostor():
    mensajes, _ = deserializar_buffer(msg_iniciar({"escena": "CIUDAD"}, id_impostor=2)
                                      + msg_bienvenida(1, {}, iniciado=True, id_impostor=2))
    assert mensajes[0]["tipo"] == INICIAR and mensajes[0]["id_impostor"] == 2
    assert mensajes[0]["estado_partida"] == {"escena": "CIUDAD"}
    assert mensajes[1]["tipo"] == BIENVENIDA and mensajes[1]["id_impostor"] == 2
    assert deserializar_buffer(msg_iniciar())[0][0]["id_impostor"] is None


def test_el_cliente_guarda_al_impostor_antes_de_avisar_que_inicio():
    """El lobby sale de la sala apenas ve `iniciado`, desde otro hilo: si el
    impostor llegara después, el impostor creería que no lo es."""
    vistos = []

    class ClienteEspia(Cliente):
        def __setattr__(self, nombre, valor):
            if nombre == "iniciado" and valor:
                vistos.append(self.id_impostor)
            super().__setattr__(nombre, valor)

    ClienteEspia()._procesar({"tipo": INICIAR, "id_impostor": 3})
    ClienteEspia()._procesar({"tipo": BIENVENIDA, "id": 1, "sala": {}, "iniciado": True, "id_impostor": 2})
    assert vistos == [3, 2]


def test_un_host_sin_impostor_no_rompe_al_cliente():
    cliente = Cliente()
    cliente._procesar({"tipo": INICIAR})  # versión anterior del juego
    assert cliente.iniciado and cliente.id_impostor is None


def test_todos_reciben_al_mismo_impostor_y_solo_al_iniciar():
    servidor = Servidor()
    assert servidor.iniciar(0, interfaz="127.0.0.1") is not None
    clientes = [Cliente() for _ in range(3)]
    try:
        for cliente in clientes:
            assert cliente.conectar("127.0.0.1", servidor.puerto)
        assert _esperar(lambda: all(c.id_jugador is not None for c in clientes))
        assert all(c.id_impostor is None and not c.unido_en_curso for c in clientes)
        servidor.marcar_iniciado()
        servidor.enviar_a_todos(msg_iniciar(servidor.estado_partida, id_impostor=servidor.id_impostor))
        assert _esperar(lambda: all(c.iniciado for c in clientes))
        assert {c.id_impostor for c in clientes} == {servidor.id_impostor}
        # Cada PC compara con su propio id: exactamente uno se ve impostor.
        ids_locales = [0] + [c.id_jugador for c in clientes]
        assert sum(jid == servidor.id_impostor for jid in ids_locales) == 1
        assert not any(c.unido_en_curso for c in clientes)
    finally:
        for cliente in clientes:
            cliente.detener()
        servidor.detener()


def test_quien_se_une_con_la_partida_en_curso_tambien_lo_recibe(forzar_impostor):
    servidor = Servidor()
    assert servidor.iniciar(0, interfaz="127.0.0.1") is not None
    forzar_impostor(0)
    servidor.marcar_iniciado()
    cliente = Cliente()
    vistos = []
    try:
        assert cliente.conectar("127.0.0.1", servidor.puerto)
        assert _esperar(lambda: cliente.iniciado)
        vistos.append(cliente.id_impostor)  # ya en el primer instante en que el lobby ve `iniciado`
        assert vistos == [0]
        assert cliente.unido_en_curso
    finally:
        cliente.detener()
        servidor.detener()


# ----------------------------------------------------------------------
# Pantalla de revelación: textos y línea de tiempo (puro)
# ----------------------------------------------------------------------

def test_textos_del_impostor_y_del_tripulante():
    assert textos_revelacion(True, "Candidato") == (
        None, "IMPOSTOR", "Evita que los demás completen sus tareas saboteándolos")
    assert textos_revelacion(False, "Influencer") == (
        "Tu rol es", "Influencer", "Completa tus tareas y descubre al impostor")
    assert textos_revelacion(False, "Ingeniero", "Puede usar los ductos")[2] == "Puede usar los ductos"
    # La habilidad del rol nunca le quita su subtítulo al impostor.
    assert textos_revelacion(True, "Candidato", "Debate Rebotante")[2] == assets.TEXTO_SUBTITULO_IMPOSTOR


def test_colores_pedidos():
    assert assets.COLOR_IMPOSTOR == (0xFF, 0x1A, 0x1A)
    assert assets.COLOR_TRIPULANTE == (0x70, 0xE5, 0xFF)
    assert assets.COLOR_FONDO_TRIPULANTE == (0x0B, 0x0E, 0x14)


@pytest.mark.parametrize("tiempo, alfa", [
    (0.0, 255),  # empieza en negro
    (FUNDIDO / 2, 128),
    (FUNDIDO, 0),  # ya se ve todo
    (DURACION / 2, 0),
    (DURACION - FUNDIDO, 0),
    (DURACION - FUNDIDO / 2, 128),
    (DURACION, 255),  # termina en negro
    (DURACION + 1, 255),
])
def test_fundido_de_entrada_y_de_salida(tiempo, alfa):
    assert alfa_del_velo(tiempo, DURACION) == pytest.approx(alfa, abs=1)


def test_omitir_salta_al_fundido_de_salida_y_solo_tras_el_minimo():
    minimo = assets.TIEMPO_MINIMO_OMITIR_REVELACION
    assert minimo == 2.0
    assert tiempo_al_omitir(minimo - 0.01, DURACION) == minimo - 0.01
    assert tiempo_al_omitir(minimo, DURACION) == DURACION - FUNDIDO
    # Ya dentro del fundido de salida no retrocede.
    assert tiempo_al_omitir(DURACION - 0.1, DURACION) == DURACION - 0.1


# ----------------------------------------------------------------------
# Pantalla de revelación: el bucle, con reloj y eventos falsos
# ----------------------------------------------------------------------

MS_POR_CUADRO = 40  # cuadros simulados largos: la línea de tiempo es la misma y corre más rápido


class _RelojFalso:
    def tick_busy_loop(self, _fps):
        return MS_POR_CUADRO

    tick = tick_busy_loop


def _tecla(tecla):
    return pygame.event.Event(pygame.KEYDOWN, key=tecla, mod=0, unicode="")


class _Revelacion:
    """Corre la pantalla sin ventana y sin esperar; guarda una copia de la
    imagen en cada segundo pedido y cuenta los cuadros presentados."""

    def __init__(self, monkeypatch, eventos=None, capturar_en=()):
        pygame.font.init()
        self.pantalla = pygame.Surface((1280, 720))
        self.cuadros = 0
        self.eventos = eventos or {}
        self.pendientes = {round(s * 1000 / MS_POR_CUADRO): s for s in capturar_en}
        self.capturas = {}
        self._leidos = 0
        monkeypatch.setattr(pygame.event, "get", self._leer_eventos)

    def _leer_eventos(self):
        self._leidos += 1
        return self.eventos.get(self._leidos, [])

    def presentar(self):
        self.cuadros += 1
        if self.cuadros in self.pendientes:
            self.capturas[self.pendientes[self.cuadros]] = self.pantalla.copy()

    def correr(self, es_impostor=False, nombre_rol="Ciudadano", apariencia=None, **opciones):
        return mostrar_pantalla_revelacion_rol(self.pantalla, _RelojFalso(), es_impostor, nombre_rol, apariencia,
                                               presentar=self.presentar, **opciones)


def _colores(superficie):
    return {tuple(superficie.get_at((x, y)))[:3] for x in range(0, 1280, 3) for y in range(0, 720, 3)}


def test_dura_lo_pedido_y_presenta_cada_cuadro(monkeypatch):
    revelacion = _Revelacion(monkeypatch)
    assert revelacion.correr() is True
    assert revelacion.cuadros * MS_POR_CUADRO / 1000 == pytest.approx(DURACION, abs=MS_POR_CUADRO / 1000)


def test_empieza_y_termina_en_negro(monkeypatch):
    primer_cuadro = MS_POR_CUADRO / 1000
    revelacion = _Revelacion(monkeypatch, capturar_en=[primer_cuadro, 1.5])
    revelacion.correr(es_impostor=True)
    assert _colores(revelacion.pantalla) == {(0, 0, 0)}  # el último cuadro
    # Un píxel del título, que a mitad de la pantalla brilla, al empezar casi no se ve.
    x, y = next((x, 142) for x in range(1280) if revelacion.capturas[1.5].get_at((x, 142))[:3] == assets.COLOR_IMPOSTOR)
    assert max(revelacion.capturas[primer_cuadro].get_at((x, y))[:3]) < 30


def test_omitir_antes_de_2_segundos_no_hace_nada(monkeypatch):
    normal = _Revelacion(monkeypatch)
    normal.correr()
    temprano = round(1.0 * 1000 / MS_POR_CUADRO)
    apurada = _Revelacion(monkeypatch, eventos={temprano: [_tecla(pygame.K_SPACE)]})
    assert apurada.correr() is True
    assert apurada.cuadros == normal.cuadros


@pytest.mark.parametrize("tecla", [pygame.K_SPACE, pygame.K_RETURN, pygame.K_KP_ENTER])
def test_espacio_o_enter_omiten_despues_de_2_segundos_con_fundido(monkeypatch, tecla):
    cuadro = round(2.2 * 1000 / MS_POR_CUADRO)
    revelacion = _Revelacion(monkeypatch, eventos={cuadro: [_tecla(tecla)]})
    assert revelacion.correr() is True
    # Termina medio segundo después de omitir: el fundido no se corta.
    assert revelacion.cuadros - cuadro == pytest.approx(FUNDIDO * 1000 / MS_POR_CUADRO, abs=1)
    assert _colores(revelacion.pantalla) == {assets.COLOR_VELO_REVELACION}


def test_otra_tecla_no_omite(monkeypatch):
    normal = _Revelacion(monkeypatch)
    normal.correr()
    cuadro = round(2.2 * 1000 / MS_POR_CUADRO)
    revelacion = _Revelacion(monkeypatch, eventos={cuadro: [_tecla(pygame.K_ESCAPE)]})
    revelacion.correr()
    assert revelacion.cuadros == normal.cuadros


def test_cerrar_la_ventana_termina_de_inmediato(monkeypatch):
    revelacion = _Revelacion(monkeypatch, eventos={10: [pygame.event.Event(pygame.QUIT)]})
    assert revelacion.correr() is False
    assert revelacion.cuadros == 9


def test_el_impostor_ve_titulo_rojo_y_ovalo_rojo(monkeypatch):
    revelacion = _Revelacion(monkeypatch, capturar_en=[1.5])
    revelacion.correr(es_impostor=True, nombre_rol="Candidato")
    imagen = revelacion.capturas[1.5]
    colores = _colores(imagen)
    assert assets.COLOR_IMPOSTOR in colores
    assert assets.COLOR_TRIPULANTE not in colores
    assert imagen.get_at((5, 5))[:3] == (0, 0, 0)  # las esquinas siguen negras
    r, g, b = imagen.get_at((480, 360))[:3]  # junto al avatar, dentro del óvalo
    assert r > 20 and r > 4 * max(g, b, 1)


def test_el_tripulante_ve_fondo_limpio_y_texto_cian(monkeypatch):
    revelacion = _Revelacion(monkeypatch, capturar_en=[1.5])
    revelacion.correr(nombre_rol="Influencer")
    imagen = revelacion.capturas[1.5]
    colores = _colores(imagen)
    assert assets.COLOR_TRIPULANTE in colores
    assert assets.COLOR_IMPOSTOR not in colores
    # Sin óvalo: donde el impostor tiene el resplandor aquí está el fondo.
    assert imagen.get_at((480, 360))[:3] == assets.COLOR_FONDO_TRIPULANTE
    assert imagen.get_at((5, 5))[:3] == assets.COLOR_FONDO_TRIPULANTE


@pytest.mark.parametrize("es_impostor", [True, False], ids=["impostor", "tripulante"])
def test_el_avatar_se_ve_con_la_ropa_de_los_vestidores(monkeypatch, es_impostor):
    """Lo que pidió el usuario: el mismo sprite vestido que en la sala, píxel a píxel."""
    revelacion = _Revelacion(monkeypatch, capturar_en=[1.5])
    revelacion.correr(es_impostor=es_impostor, nombre_rol="Periodista", apariencia=ROPA, reducir_movimiento=True)
    imagen = revelacion.capturas[1.5]
    vestido = sprites.sprite_jugador((1, 2, 3), escala=assets.ESCALA_AVATAR_REVELACION, rol="periodista", apariencia=ROPA)
    sin_ropa = sprites.sprite_jugador((1, 2, 3), escala=assets.ESCALA_AVATAR_REVELACION, rol="periodista")
    rect = vestido.get_rect(center=assets.CENTRO_REVELACION)
    distintos_a_sin_ropa = 0
    for x in range(0, rect.width, 5):
        for y in range(0, rect.height, 5):
            color = vestido.get_at((x, y))
            if color.a == 255:
                assert imagen.get_at((rect.x + x, rect.y + y))[:3] == color[:3]
            if color != sin_ropa.get_at((x, y)):
                distintos_a_sin_ropa += 1
    assert distintos_a_sin_ropa > 0  # la ropa cambia el sprite: la comparación sí distingue


def test_el_avatar_no_necesita_apariencia_ni_un_rol_con_hoja(monkeypatch):
    assert _Revelacion(monkeypatch).correr(apariencia=None) is True
    assert _Revelacion(monkeypatch).correr(nombre_rol="Ingeniero", descripcion_rol="Puede usar los ductos") is True


def test_el_avatar_flota_y_el_ovalo_pulsa(monkeypatch):
    revelacion = _Revelacion(monkeypatch, capturar_en=[1.0, 1.5])
    revelacion.correr(es_impostor=True)
    a, b = (revelacion.capturas[s] for s in (1.0, 1.5))
    assert pygame.image.tobytes(a, "RGB") != pygame.image.tobytes(b, "RGB")


@pytest.mark.parametrize("es_impostor", [True, False], ids=["impostor", "tripulante"])
def test_reducir_movimiento_deja_la_imagen_quieta(monkeypatch, es_impostor):
    revelacion = _Revelacion(monkeypatch, capturar_en=[1.0, 1.5])
    revelacion.correr(es_impostor=es_impostor, reducir_movimiento=True)
    a, b = (revelacion.capturas[s] for s in (1.0, 1.5))
    assert pygame.image.tobytes(a, "RGB") == pygame.image.tobytes(b, "RGB")


def test_un_subtitulo_largo_se_parte_dentro_de_la_zona_segura():
    pygame.font.init()
    largo = "Una descripción de rol tan larga que de ninguna manera podría caber en una sola línea de la pantalla"
    bloque = pantalla_rol._bloque_de_texto(largo, assets.TEXTO_SUBTITULO_REVELACION, assets.COLOR_TRIPULANTE)
    zona = pygame.Rect(assets.RECT_ZONA_SEGURA)
    assert len(bloque) > 1
    for superficie, centro in bloque:
        assert zona.contains(superficie.get_rect(center=centro))


@pytest.mark.parametrize("es_impostor, rol", [(True, "Influencer"), (False, "Influencer"), (False, "Periodista")])
def test_los_textos_no_pisan_al_avatar_ni_salen_de_la_zona_segura(es_impostor, rol):
    pygame.font.init()
    avatar = pygame.Rect(0, 0, 16 * assets.ESCALA_AVATAR_REVELACION, 20 * assets.ESCALA_AVATAR_REVELACION)
    avatar.center = assets.CENTRO_REVELACION
    avatar.inflate_ip(0, 2 * assets.AMPLITUD_FLOTACION_REVELACION)  # todo su recorrido al flotar
    zona = pygame.Rect(assets.RECT_ZONA_SEGURA)
    # La tinta de cada texto, sin el margen vacío de la fuente.
    rectangulos = [s.get_bounding_rect().move(s.get_rect(center=c).topleft)
                   for s, c in pantalla_rol._textos_de_pantalla(es_impostor, rol, None)]
    for rect in rectangulos:
        assert zona.contains(rect)
        assert not rect.colliderect(avatar)
    for i, rect in enumerate(rectangulos):
        assert all(not rect.colliderect(otro) for otro in rectangulos[i + 1:])


# ----------------------------------------------------------------------
# Lobby: sale por la pantalla de revelación
# ----------------------------------------------------------------------

class _RelojLobby:
    """Sin esperar el tiempo real de un frame, pero dejando correr a la red."""

    def tick(self, _fps):
        time.sleep(0.001)
        return 16

    tick_busy_loop = tick


class _TeclasSueltas:
    def __getitem__(self, _tecla):
        return False


@pytest.fixture
def sala_de_prueba(monkeypatch):
    """Parches para correr pantalla_sala_espera sin ventana: eventos por
    cuadro y todas las cajas al alcance. Retorna cómo correrla."""
    pygame.font.init()
    monkeypatch.setattr(pygame.key, "get_pressed", lambda: _TeclasSueltas())
    monkeypatch.setattr(pygame.mouse, "get_pos", lambda: (0, 0))
    monkeypatch.setattr(lobby, "_caja_cercana", lambda x, y: 0)

    def correr(conexion, es_host, guion, ip="127.0.0.1", limite_cuadros=3000):
        cuadro = {"n": 0}

        def eventos():
            cuadro["n"] += 1
            if cuadro["n"] > limite_cuadros:
                return [pygame.event.Event(pygame.QUIT)]
            paso = guion.get(cuadro["n"], [])
            return paso() if callable(paso) else paso

        monkeypatch.setattr(pygame.event, "get", eventos)
        return lobby.pantalla_sala_espera(pygame.Surface((1280, 720)), _RelojLobby(), lambda: None, CLASES_ROL,
                                          es_host, conexion, ip)

    return correr


@pytest.fixture
def espia_revelacion(monkeypatch):
    """Reemplaza la pantalla y anota con qué se llamó. Retorna True (terminó)."""
    llamadas = []

    def espia(_pantalla, _reloj, es_impostor, nombre_rol, apariencia, **opciones):
        llamadas.append(SimpleNamespace(es_impostor=es_impostor, nombre_rol=nombre_rol, apariencia=apariencia,
                                        opciones=opciones))
        return True

    monkeypatch.setattr(lobby, "mostrar_pantalla_revelacion_rol", espia)
    return llamadas


# Abre el vestidor, elige el primer tono (índice 0) y lo cierra.
GUION_VESTIRSE = {3: [_tecla(pygame.K_e)], 5: [_tecla(pygame.K_RIGHT)], 7: [_tecla(pygame.K_e)]}
ROPA_DEL_GUION = Apariencia(piel=0)


def _host_con_invitado(rol_invitado="Influencer"):
    servidor = Servidor()
    assert servidor.iniciar(0, interfaz="127.0.0.1") is not None
    cliente = Cliente()
    assert cliente.conectar("127.0.0.1", servidor.puerto)
    assert _esperar(lambda: cliente.id_jugador is not None)
    cliente.enviar_rol(rol_invitado)
    assert _esperar(lambda: servidor.sala.rol_de(1) == rol_invitado)
    return servidor, cliente


@pytest.mark.parametrize("id_impostor, impostor_local", [(0, True), (1, False)], ids=["es el host", "es el invitado"])
def test_el_host_sortea_avisa_y_se_revela_con_su_ropa(sala_de_prueba, espia_revelacion, forzar_impostor,
                                                      id_impostor, impostor_local):
    forzar_impostor(id_impostor)
    servidor, cliente = _host_con_invitado()
    try:
        guion = {**GUION_VESTIRSE, 10: [_tecla(pygame.K_3)], 15: [_tecla(pygame.K_RETURN)]}
        resultado = sala_de_prueba(servidor, True, guion)
        assert resultado == ([Periodista, Influencer], servidor, True)
        assert len(espia_revelacion) == 1
        llamada = espia_revelacion[0]
        assert llamada.es_impostor is impostor_local
        assert llamada.nombre_rol == "Periodista"
        assert llamada.apariencia == ROPA_DEL_GUION
        assert _esperar(lambda: cliente.iniciado)
        assert cliente.id_impostor == id_impostor
        assert servidor.ids_partida == [0, 1]
    finally:
        cliente.detener()
        servidor.detener()


def test_el_clic_en_start_tambien_pasa_por_la_revelacion(sala_de_prueba, espia_revelacion, monkeypatch):
    servidor, cliente = _host_con_invitado()
    try:
        monkeypatch.setattr(pygame.mouse, "get_pos", lambda: (500, 600))  # sobre el botón de inicio
        clic = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(500, 600))
        resultado = sala_de_prueba(servidor, True, {3: [clic]})
        assert resultado == ([Ciudadano, Influencer], servidor, True)
        assert len(espia_revelacion) == 1 and servidor.id_impostor in (0, 1)
    finally:
        cliente.detener()
        servidor.detener()


@pytest.mark.parametrize("id_impostor, impostor_local", [(1, True), (0, False)], ids=["es el invitado", "es el host"])
def test_el_invitado_se_revela_con_su_ropa_al_recibir_iniciar(sala_de_prueba, espia_revelacion, forzar_impostor,
                                                              id_impostor, impostor_local):
    forzar_impostor(id_impostor)
    servidor, cliente = _host_con_invitado("Ciudadano")
    servidor.sala.elegir_rol(0, "Candidato")

    def host_inicia():
        servidor.marcar_iniciado()
        servidor.enviar_a_todos(msg_iniciar(servidor.estado_partida, id_impostor=servidor.id_impostor))
        return []

    try:
        guion = {**GUION_VESTIRSE, 10: [_tecla(pygame.K_2)], 40: host_inicia}
        resultado = sala_de_prueba(cliente, False, guion)
        assert resultado is not None and resultado[1:] == (cliente, False)
        assert len(espia_revelacion) == 1
        llamada = espia_revelacion[0]
        assert llamada.es_impostor is impostor_local
        assert llamada.apariencia == ROPA_DEL_GUION
        assert llamada.nombre_rol == "Influencer"
        assert cliente.ids_partida == [0, 1]
    finally:
        cliente.detener()
        servidor.detener()


def test_quien_vuelve_a_una_partida_en_curso_entra_directo(sala_de_prueba, espia_revelacion):
    servidor = Servidor()
    assert servidor.iniciar(0, interfaz="127.0.0.1") is not None
    servidor.marcar_iniciado()
    cliente = Cliente()
    try:
        assert cliente.conectar("127.0.0.1", servidor.puerto)
        assert _esperar(lambda: cliente.iniciado)
        resultado = sala_de_prueba(cliente, False, {})
        assert resultado is not None and resultado[1:] == (cliente, False)
        assert espia_revelacion == []
    finally:
        cliente.detener()
        servidor.detener()


def test_con_un_solo_jugador_no_se_inicia_ni_se_revela(sala_de_prueba, espia_revelacion):
    servidor = Servidor()
    assert servidor.iniciar(0, interfaz="127.0.0.1") is not None
    try:
        quit_ = [pygame.event.Event(pygame.QUIT)]
        assert sala_de_prueba(servidor, True, {3: [_tecla(pygame.K_RETURN)], 8: quit_}) is None
        assert espia_revelacion == []
        assert servidor.id_impostor is None and not servidor.iniciado
    finally:
        servidor.detener()


def test_motivos_para_no_iniciar():
    sala = _servidor_con(0, 1).sala
    assert "2 jugadores" in lobby._motivo_para_no_iniciar(1, sala)
    assert "elegir su rol" in lobby._motivo_para_no_iniciar(2, sala)
    sala.elegir_rol(0, "Ciudadano")
    sala.elegir_rol(1, "Candidato")
    assert lobby._motivo_para_no_iniciar(2, sala) is None


def _servidor_listo(*ids):
    servidor = _servidor_con(*ids)
    for jid in ids:
        servidor.sala.elegir_rol(jid, "Candidato")
    return servidor


def _entrar(servidor, id_local=0, es_host=True):
    pygame.font.init()
    return lobby._entrar_a_partida(pygame.Surface((1280, 720)), _RelojFalso(), lambda: None, servidor, es_host,
                                   CLASES_ROL, id_local, "Candidato", ROPA)


def test_cerrar_la_ventana_en_la_revelacion_sale_del_juego(monkeypatch):
    servidor = _servidor_listo(0, 1)
    monkeypatch.setattr(lobby, "mostrar_pantalla_revelacion_rol", lambda *a, **k: False)
    assert _entrar(servidor) is None
    assert not servidor.corriendo


def test_si_la_pantalla_falla_la_partida_arranca_igual(monkeypatch):
    def rota(*_args, **_kwargs):
        raise RuntimeError("pantalla rota")

    anotados = []
    servidor = _servidor_listo(0, 1)
    monkeypatch.setattr(lobby, "mostrar_pantalla_revelacion_rol", rota)
    monkeypatch.setattr(registro_errores, "registrar", lambda contexto, error=None: anotados.append(contexto))
    assert _entrar(servidor) == ([Candidato, Candidato], servidor, True)
    assert anotados == ["mostrar_pantalla_revelacion_rol"]


def test_si_alguien_se_va_durante_la_revelacion_cada_clase_sigue_con_su_id(monkeypatch):
    """La pantalla abre casi 4 s entre fijar las clases y armar la sesión; sin
    fijar los ids aquí, el orden caería a 0..n-1 y no al de la sala."""
    servidor = _servidor_listo(0, 2, 3)
    servidor.sala.elegir_rol(2, "Influencer")
    servidor.sala.elegir_rol(3, "Periodista")

    def se_va_uno(*_args, **_kwargs):
        servidor.sala.desconectar(2)
        return True

    monkeypatch.setattr(lobby, "mostrar_pantalla_revelacion_rol", se_va_uno)
    clases, _, _ = _entrar(servidor)
    assert clases == [Candidato, Influencer, Periodista]
    assert _ids_de_partida(servidor, len(clases)) == [0, 2, 3]


def test_el_lobby_entrega_presentar_y_reducir_movimiento(monkeypatch, espia_revelacion):
    from src.core.preferencias import Preferencias

    presentar = object()
    monkeypatch.setattr(lobby, "cargar_preferencias", lambda: Preferencias(reducir_movimiento=True))
    lobby._revelar_rol(None, None, presentar, False, "Ciudadano", ROPA)
    assert espia_revelacion[0].opciones == {"presentar": presentar, "reducir_movimiento": True}


def test_de_verdad_del_lobby_a_la_pantalla_con_su_firma_real(sala_de_prueba, forzar_impostor, monkeypatch):
    """Sin espía: el host inicia y la pantalla real corre hasta el final."""
    forzar_impostor(0)
    servidor, cliente = _host_con_invitado()
    avatares = []
    original = sprites.sprite_jugador

    def espia_sprite(*args, **kwargs):
        if kwargs.get("escala") == assets.ESCALA_AVATAR_REVELACION:
            avatares.append(kwargs)
        return original(*args, **kwargs)

    monkeypatch.setattr(sprites, "sprite_jugador", espia_sprite)
    try:
        guion = {**GUION_VESTIRSE, 15: [_tecla(pygame.K_RETURN)]}
        assert sala_de_prueba(servidor, True, guion, limite_cuadros=10000) == ([Ciudadano, Influencer], servidor, True)
        assert len(avatares) == 1
        assert avatares[0]["rol"] == "ciudadano"
        assert avatares[0]["apariencia"] == ROPA_DEL_GUION
    finally:
        cliente.detener()
        servidor.detener()


# ----------------------------------------------------------------------
# La partida sabe quién es el impostor
# ----------------------------------------------------------------------

def _sesion(*clases):
    return SimpleNamespace(jugadores=[clase(0, 0) for clase in clases])


def _impostores(sesion):
    return [jugador.es_impostor for jugador in sesion.jugadores]


def test_un_jugador_nuevo_no_es_impostor():
    assert Ciudadano(0, 0).es_impostor is False


@pytest.mark.parametrize("id_impostor, esperado", [(0, [True, False, False]), (2, [False, True, False]),
                                                   (3, [False, False, True])])
def test_el_host_marca_al_jugador_de_ese_id_de_red(id_impostor, esperado):
    servidor = _servidor_con(0, 2, 3)
    servidor.id_impostor = id_impostor
    clases = [Ciudadano, Influencer, Periodista]
    sesion = ConfigSesionHost(servidor, clases, ids_red=[0, 2, 3]).configurar_sesion(_sesion(*clases))
    assert sesion.id_impostor == id_impostor
    assert _impostores(sesion) == esperado


def test_el_invitado_marca_al_mismo_jugador_que_el_host():
    cliente = Cliente()
    cliente.id_jugador = 2
    cliente.id_impostor = 3
    clases = [Ciudadano, Influencer, Periodista]
    config = ConfigSesionJoin(cliente, clases, id_local=1, ids_red=[0, 2, 3])
    sesion = config.configurar_sesion(_sesion(*clases))
    assert sesion.id_impostor == 3
    assert _impostores(sesion) == [False, False, True]


def test_sin_ids_red_empareja_por_lo_que_fijo_el_lobby():
    servidor = _servidor_con(0, 1)  # la sala ya cambió: se fue el 3 y llegó el 1
    servidor.ids_partida = [0, 3]
    servidor.id_impostor = 3
    clases = [Ciudadano, Candidato]
    sesion = ConfigSesionHost(servidor, clases).configurar_sesion(_sesion(*clases))
    assert _impostores(sesion) == [False, True]


@pytest.mark.parametrize("conexion", [SimpleNamespace(), None, "no soy una conexión"], ids=["vacia", "none", "texto"])
def test_sin_impostor_nadie_queda_marcado_ni_se_rompe_la_sesion(monkeypatch, conexion):
    monkeypatch.setattr(registro_errores, "registrar", lambda *a, **k: None)
    clases = [Ciudadano, Candidato]
    sesion = ConfigSesionHost(conexion, clases, ids_red=[0, 1]).configurar_sesion(_sesion(*clases))
    assert sesion.id_impostor is None
    assert _impostores(sesion) == [False, False]


def test_una_sesion_sin_jugadores_no_se_rompe(monkeypatch):
    monkeypatch.setattr(registro_errores, "registrar", lambda *a, **k: None)
    sesion = SimpleNamespace()
    servidor = _servidor_con(0, 1)
    servidor.id_impostor = 1
    ConfigSesionHost(servidor, [Ciudadano, Candidato], ids_red=[0, 1]).configurar_sesion(sesion)
    assert sesion.id_impostor == 1


def test_la_partida_nueva_tras_la_derrota_global_conserva_al_impostor():
    import Main

    jugadores = [Ciudadano(0, 0), Candidato(0, 0)]
    jugadores[1].es_impostor = True
    nuevos = Main._jugadores_nuevos(jugadores)
    assert [j.es_impostor for j in nuevos] == [False, True]
    assert nuevos[1] is not jugadores[1]


def test_una_partida_local_no_tiene_impostor():
    import Main

    sesion = Main._nueva_sesion([Ciudadano, Candidato], None)
    assert sesion.id_impostor is None
    assert _impostores(sesion) == [False, False]
