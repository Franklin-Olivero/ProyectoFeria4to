"""Adaptador de sesión para el modo Online de Civitas.

Conecta el juego existente (Main.py, que ya maneja la partida local)
con la red (Online/servidor.py y Online/cliente.py). En cada frame:

    - El host corre autoritativamente la lógica de la partida y lee el input
      del invitado inyectándolo en la simulación.
    - El host serializa periódicamente las posiciones, vidas, enemigos,
      colapso y cambios de escena/mazmorra y lo envía a todos los invitados.
    - El invitado corre su vista local sin lag de input, envía sus comandos
      al host y aplica las actualizaciones de estado y teletransporte recibidas.
    - Soporta reconexión en caliente: si un invitado se desconecta y vuelve
      a entrar con el mismo código, el servidor lo detecta y lo sincroniza
      inmediatamente al juego activo sin dejarlo atrapado en el lobby.
    - Sincronización de mazmorras: si el anfitrión o el invitado entran a
      una mazmorra, ambos son teletransportados juntos a la misma zona.
"""

import time
import math

from Online.protocolo import (
    INPUT, ESTADO, DESCONEXION, ENTRAR_MAZMORRA, CAMBIO_ESCENA, CAMBIO_CUARTO,
    crear_mensaje, serializar, deserializar_buffer, msg_estado, msg_input,
    msg_cambio_escena, msg_cambio_cuarto, msg_entrar_mazmorra, ROLES,
)


def serializar_input(pedido):
    """Convierte un InputJugador en un dict serializable para enviar por red.

    Campos: dirección de movimiento (dx, dy), si está disparando,
    punto de apuntado (px, py), si pidió habilidad y si pidió dash.
    """
    return {
        "dx": round(pedido.direccion.x, 3) if pedido.direccion else 0,
        "dy": round(pedido.direccion.y, 3) if pedido.direccion else 0,
        "disparando": pedido.disparando,
        "px": round(pedido.punto.x, 1) if pedido.punto else None,
        "py": round(pedido.punto.y, 1) if pedido.punto else None,
        "habilidad": pedido.habilidad,
        "dash": pedido.dash,
    }


def deserializar_input(datos):
    """Reconstruye un InputJugador (namedtuple-like) desde un dict de red."""
    return _InputRed(
        dx=datos.get("dx", 0),
        dy=datos.get("dy", 0),
        disparando=datos.get("disparando", False),
        px=datos.get("px"),
        py=datos.get("py"),
        habilidad=datos.get("habilidad", False),
        dash=datos.get("dash", False),
    )


class _InputRed:
    """Sustituto ligero de InputJugador para datos que llegan por red."""

    def __init__(self, dx=0, dy=0, disparando=False, px=None, py=None,
                 habilidad=False, dash=False):
        from pygame import Vector2
        self.direccion = Vector2(dx, dy) if (dx or dy) else None
        self.disparando = disparando
        self.punto = Vector2(px, py) if px is not None else None
        self.habilidad = habilidad
        self.dash = dash


def serializar_estado(jugadores, escenario, colapso, escena_nombre="CIUDAD", zona=None, cuarto_idx=0):
    """Crea un snapshot completo del estado del juego para enviar a los invitados."""
    estado = {
        "t": time.time(),
        "escena": escena_nombre,
        "zona": zona,
        "cuarto_idx": cuarto_idx,
        "jugadores": [
            {
                "x": round(j.posicion.x, 1),
                "y": round(j.posicion.y, 1),
                "vida": j.vida,
                "vida_max": j.vida_maxima,
                "caminando": getattr(j, "caminando_en_ciudad", False),
            }
            for j in jugadores
        ],
        "colapso": round(colapso.valor, 2) if colapso is not None else 0.0,
    }
    if escenario is not None and hasattr(escenario, "enemigos"):
        estado["enemigos"] = [
            {
                "x": e.rect.centerx,
                "y": e.rect.centery,
                "vida": e.vida,
                "vivo": e.vivo,
            }
            for e in escenario.enemigos
        ]
    return estado


def aplicar_estado_remoto(estado, jugadores, escenario=None, colapso=None, id_local=1):
    """Aplica un snapshot recibido por red a los jugadores y mundo locales."""
    datos_jugadores = estado.get("jugadores", [])
    for i, datos in enumerate(datos_jugadores):
        if i < len(jugadores):
            j = jugadores[i]
            if i != id_local:
                # Jugador remoto: actualizar posición autoritativa
                j.posicion.x = datos["x"]
                j.posicion.y = datos["y"]
                j.caminando_en_ciudad = datos.get("caminando", False)
            else:
                # Jugador local: reconciliación suave si hay desfasaje extremo (>150 px)
                dist_cuad = (j.posicion.x - datos["x"]) ** 2 + (j.posicion.y - datos["y"]) ** 2
                if dist_cuad > 22500:
                    j.posicion.x = datos["x"]
                    j.posicion.y = datos["y"]
            # La vida es autoritativa del host para todos
            j.vida = datos["vida"]

    if colapso is not None and "colapso" in estado:
        colapso.valor = estado["colapso"]

    if escenario is not None and hasattr(escenario, "enemigos") and "enemigos" in estado:
        datos_enemigos = estado["enemigos"]
        for e, datos in zip(escenario.enemigos, datos_enemigos):
            e.vida = datos.get("vida", e.vida)
            e.vivo = datos.get("vivo", e.vivo)
            e.rect.centerx = datos.get("x", e.rect.centerx)
            e.rect.centery = datos.get("y", e.rect.centery)


class _MandoFicticio:
    """Simula un mando siempre conectado para que el bucle de Main.py no falle nunca."""
    def attached(self):
        return True

    def get_axis(self, *args):
        return 0.0

    def get_button(self, *args):
        return False


class EntradaRed:
    """Entrada remota para que el Host lea el input de un invitado específico."""

    def __init__(self, adaptador, id_jugador=1):
        self.adaptador = adaptador
        self.id_jugador = id_jugador
        self.mando = _MandoFicticio()

    def leer(self, *args, **kwargs):
        from src.core.entrada import InputJugador
        inp = self.adaptador.recibir_input(self.id_jugador)
        if inp is None:
            return InputJugador()
        return InputJugador(
            movimiento=(inp.direccion.x, inp.direccion.y) if inp.direccion else (0.0, 0.0),
            punto_apuntado=inp.punto,
            disparando=inp.disparando,
            habilidad=inp.habilidad,
            dash=inp.dash,
        )


class EntradaLocalCliente:
    """Entrada del jugador local en la máquina invitada: lee teclado/mouse y envía por red."""

    def __init__(self, adaptador, id_jugador=1):
        self.adaptador = adaptador
        self.id_jugador = id_jugador
        self.mando = _MandoFicticio()
        from src.core.entrada import _Pulsos
        self._pulsos = _Pulsos()

    def leer(self, teclas=None, botones_mouse=None, punto_mouse=None):
        import pygame
        from src.core.entrada import (
            InputJugador, direccion_teclado, TECLAS_DASH, TECLA_DISPARAR,
            CLICK_DISPARA, TECLA_HABILIDAD,
        )
        if teclas is None:
            teclas = pygame.key.get_pressed()
        if botones_mouse is None:
            botones_mouse = pygame.mouse.get_pressed()
        if punto_mouse is None and pygame.mouse.get_focused():
            punto_mouse = pygame.mouse.get_pos()

        dash = any(teclas[tecla] for tecla in TECLAS_DASH)
        pedido = InputJugador(
            movimiento=direccion_teclado(teclas),
            punto_apuntado=punto_mouse,
            disparando=bool(teclas[TECLA_DISPARAR] or (CLICK_DISPARA and botones_mouse[0])),
            habilidad=self._pulsos.pulso("habilidad", bool(teclas[TECLA_HABILIDAD])),
            dash=self._pulsos.pulso("dash", dash),
        )
        if self.adaptador is not None:
            self.adaptador.enviar_input(pedido)
        return pedido


class EntradaRemotaHost:
    """Ranura en el cliente para el Host (J1): su posición se actualiza por estado."""

    def __init__(self, adaptador, id_jugador=0):
        self.adaptador = adaptador
        self.id_jugador = id_jugador
        self.mando = _MandoFicticio()

    def leer(self, *args, **kwargs):
        from src.core.entrada import InputJugador
        return InputJugador()


class AdaptadorOnlineHost:
    """El host usa este adaptador para enviar estado, recibir inputs y sincronizar mazmorras."""

    def __init__(self, servidor):
        self.servidor = servidor
        self._ultimos_inputs = {}  # id_jugador -> InputRed
        self._contador_frames = 0
        self._intervalo_estado = 2  # enviar estado cada 2 frames (~30 Hz)
        self._ultima_escena = None
        self._ultima_zona = None
        self._ultimo_cuarto = 0

    def recibir_input(self, id_jugador=1):
        """Retorna el último InputRed de un jugador remoto específico."""
        for msg in self.servidor.leer_mensajes():
            tipo = msg.get("tipo")
            if tipo == INPUT:
                jid = msg.get("id", 1)
                self._ultimos_inputs[jid] = deserializar_input(msg.get("input", {}))
            elif tipo == DESCONEXION:
                jid = msg.get("id", 1)
                self._ultimos_inputs.pop(jid, None)
        return self._ultimos_inputs.get(id_jugador)

    def actualizar(self, escena, arena, mazmorra, fundido, dt, sesion, partida, jugadores, jugador):
        """Ejecuta la sincronización autoritativa del Host en cada frame."""
        from src.core.escenas import Escena
        from src.core import assets
        from src.engine.combate import ArenaJefe, MazmorraJugable
        from src.engine.mazmorras import Mazmorra

        # 1. Procesar mensajes recibidos de los clientes
        for msg in self.servidor.leer_mensajes():
            tipo = msg.get("tipo")
            if tipo == INPUT:
                jid = msg.get("id", 1)
                self._ultimos_inputs[jid] = deserializar_input(msg.get("input", {}))
            elif tipo == DESCONEXION:
                jid = msg.get("id", 1)
                self._ultimos_inputs.pop(jid, None)
            elif tipo == ENTRAR_MAZMORRA:
                # Un invitado pidió entrar a una mazmorra: teletransportar a todos
                zona = msg.get("zona")
                if zona and escena == Escena.CIUDAD:
                    from Main import limpiar_combate, _curar
                    partida.entrar(zona)
                    limpiar_combate()
                    _curar(jugadores)
                    if zona == "Alcaldía" or (hasattr(assets, "ZONA_FINAL") and zona == assets.ZONA_FINAL):
                        arena = ArenaJefe(partida.colapso, jugadores)
                        escena = Escena.JEFE
                        mazmorra = None
                    else:
                        mazmorra = MazmorraJugable(Mazmorra(partida.ciudad.reportes(zona), zona))
                        mazmorra.colocar_en_entrada(jugadores)
                        escena = Escena.MAZMORRA
                        arena = None
                    fundido = assets.DURACION_FUNDIDO
                    self.servidor.actualizar_estado_partida(escena=escena.name, zona=zona, cuarto_idx=0)
                    self.servidor.enviar_a_todos(msg_cambio_escena(escena.name, zona=zona, cuarto_idx=0))

        # 2. Detectar si el Host cambió de escena o entró a una mazmorra
        zona_actual = mazmorra.mazmorra.nombre_zona if mazmorra else (arena.mazmorra.nombre_zona if arena else None)
        cuarto_actual = mazmorra.indice_cuarto if mazmorra else 0

        if escena != self._ultima_escena or zona_actual != self._ultima_zona:
            self._ultima_escena = escena
            self._ultima_zona = zona_actual
            self._ultimo_cuarto = cuarto_actual
            self.servidor.actualizar_estado_partida(escena=escena.name, zona=zona_actual, cuarto_idx=cuarto_actual)
            self.servidor.enviar_a_todos(msg_cambio_escena(escena.name, zona=zona_actual, cuarto_idx=cuarto_actual))

        elif mazmorra is not None and getattr(mazmorra, "indice_cuarto", 0) != self._ultimo_cuarto:
            self._ultimo_cuarto = mazmorra.indice_cuarto
            self.servidor.actualizar_estado_partida(cuarto_idx=self._ultimo_cuarto)
            self.servidor.enviar_a_todos(msg_cambio_cuarto(self._ultimo_cuarto))

        # 3. Transmisión periódica del snapshot de estado
        self._contador_frames += 1
        if self._contador_frames % self._intervalo_estado == 0:
            from Main import _escenario_activo
            escenario = _escenario_activo(escena, arena, mazmorra)
            estado = serializar_estado(
                jugadores, escenario, partida.colapso,
                escena_nombre=escena.name, zona=zona_actual,
                cuarto_idx=cuarto_actual,
            )
            datos_bytes = msg_estado(estado)
            self.servidor.ultimo_snapshot_estado = datos_bytes
            self.servidor.enviar_a_todos(datos_bytes)

        return escena, arena, mazmorra, fundido

    def actualizar_ciudad(self, dt, partida, jugadores, jugador):
        """En la ciudad, actualiza las posiciones de los invitados remotos si se mueven."""
        for jid in range(1, len(jugadores)):
            inp = self.recibir_input(jid)
            if inp is not None and inp.direccion:
                j = jugadores[jid]
                velocidad = 180 * dt
                nueva_pos = j.posicion + inp.direccion * velocidad
                if not partida.es_solida(nueva_pos.x, nueva_pos.y):
                    j.posicion = nueva_pos
                    j.caminando_en_ciudad = True
            elif jid < len(jugadores):
                jugadores[jid].caminando_en_ciudad = False

    def detener(self):
        self.servidor.detener()


class AdaptadorOnlineJoin:
    """El invitado usa este adaptador para enviar input, recibir estado y sincronizar mazmorras."""

    def __init__(self, cliente, id_local=1):
        self.cliente = cliente
        self.id_local = id_local
        self._ultimo_estado = None
        self._contador_frames = 0

    def enviar_input(self, pedido):
        """Serializa el input local y lo envía al host."""
        datos = serializar_input(pedido)
        self.cliente.enviar_input(datos)

    def recibir_estado(self):
        """Retorna el último estado recibido del host, o None."""
        for msg in self.cliente.leer_mensajes():
            if msg.get("tipo") == ESTADO:
                self._ultimo_estado = msg.get("estado")
        return self._ultimo_estado

    def actualizar(self, escena, arena, mazmorra, fundido, dt, sesion, partida, jugadores, jugador):
        """Sincroniza la escena local con la del host y aplica snapshots."""
        from src.core.escenas import Escena
        from src.core import assets
        from src.engine.combate import ArenaJefe, MazmorraJugable, revivir_caidos
        from src.engine.mazmorras import Mazmorra

        for msg in self.cliente.leer_mensajes():
            tipo = msg.get("tipo")

            if tipo == CAMBIO_ESCENA:
                esc_nom = msg.get("escena")
                zona = msg.get("zona")
                cuarto = msg.get("cuarto", 0)

                if esc_nom == "MAZMORRA" and zona:
                    if escena != Escena.MAZMORRA or (mazmorra and mazmorra.mazmorra.nombre_zona != zona):
                        partida.entrar(zona)
                        from Main import limpiar_combate, _curar
                        limpiar_combate()
                        _curar(jugadores)
                        mazmorra = MazmorraJugable(Mazmorra(partida.ciudad.reportes(zona), zona))
                        mazmorra.colocar_en_entrada(jugadores)
                        if cuarto > 0 and hasattr(mazmorra, "indice_cuarto"):
                            for _ in range(cuarto):
                                if not mazmorra.es_ultimo_cuarto:
                                    mazmorra.avanzar_cuarto()
                        escena = Escena.MAZMORRA
                        arena = None
                        fundido = assets.DURACION_FUNDIDO

                elif esc_nom == "JEFE":
                    if escena != Escena.JEFE:
                        from Main import limpiar_combate, _curar
                        limpiar_combate()
                        _curar(jugadores)
                        arena = ArenaJefe(partida.colapso, jugadores)
                        escena = Escena.JEFE
                        mazmorra = None
                        fundido = assets.DURACION_FUNDIDO

                elif esc_nom == "CIUDAD":
                    if escena != Escena.CIUDAD:
                        from Main import _volver_a_la_ciudad, limpiar_combate
                        arena = None
                        mazmorra = None
                        escena = _volver_a_la_ciudad(jugador, partida)
                        fundido = assets.DURACION_FUNDIDO
                        limpiar_combate()

                elif esc_nom == "DECISION":
                    escena = Escena.DECISION

                elif esc_nom == "RESULTADO":
                    escena = Escena.RESULTADO

            elif tipo == CAMBIO_CUARTO:
                cuarto = msg.get("cuarto", 0)
                if mazmorra is not None and getattr(mazmorra, "indice_cuarto", 0) != cuarto:
                    from Main import limpiar_combate
                    while mazmorra.indice_cuarto < cuarto and not mazmorra.es_ultimo_cuarto:
                        mazmorra.avanzar_cuarto()
                    limpiar_combate()
                    revivir_caidos(jugadores)
                    for j in jugadores:
                        j.detener()

            elif tipo == ESTADO:
                self._ultimo_estado = msg.get("estado", {})
                from Main import _escenario_activo
                escenario = _escenario_activo(escena, arena, mazmorra)

                # Si el estado recibido indica una mazmorra y el cliente aún está en la ciudad, sincronizar
                esc_estado = self._ultimo_estado.get("escena")
                zona_estado = self._ultimo_estado.get("zona")
                if esc_estado == "MAZMORRA" and escena != Escena.MAZMORRA and zona_estado:
                    partida.entrar(zona_estado)
                    from Main import limpiar_combate, _curar
                    limpiar_combate()
                    _curar(jugadores)
                    mazmorra = MazmorraJugable(Mazmorra(partida.ciudad.reportes(zona_estado), zona_estado))
                    mazmorra.colocar_en_entrada(jugadores)
                    escena = Escena.MAZMORRA
                    arena = None
                    fundido = assets.DURACION_FUNDIDO

                aplicar_estado_remoto(self._ultimo_estado, jugadores, escenario, partida.colapso, id_local=self.id_local)

        return escena, arena, mazmorra, fundido

    def actualizar_ciudad(self, dt, partida, jugadores, jugador):
        """En la ciudad, revisa si el invitado pulsa E frente a una entrada para solicitar ingreso."""
        import pygame
        from src.core import ciudad_mapa
        teclas = pygame.key.get_pressed()
        posicion = (jugador.posicion.x, jugador.posicion.y)
        zona = ciudad_mapa.entrada_cercana(posicion)
        if zona is not None and teclas[pygame.K_e]:
            self.cliente.enviar_entrar_mazmorra(zona)

    def detener(self):
        self.cliente.desconectar()


class ConfigSesionHost:
    """Configura la sesión para el Host."""

    def __init__(self, conexion, clases):
        self.conexion = conexion
        self.clases = clases
        self.mando = _MandoFicticio()

    def configurar_sesion(self, sesion):
        from src.core.entrada import EntradaTeclado
        adaptador = AdaptadorOnlineHost(self.conexion)
        sesion.adaptador_red = adaptador
        sesion.id_local = 0
        entradas = [EntradaTeclado()]
        for jid in range(1, len(self.clases)):
            entradas.append(EntradaRed(adaptador, id_jugador=jid))
        sesion.entradas = entradas
        return sesion


class ConfigSesionJoin:
    """Configura la sesión para el Invitado."""

    def __init__(self, conexion, clases, id_local=1):
        self.conexion = conexion
        self.clases = clases
        self.id_local = id_local
        self.mando = _MandoFicticio()

    def configurar_sesion(self, sesion):
        adaptador = AdaptadorOnlineJoin(self.conexion, id_local=self.id_local)
        sesion.adaptador_red = adaptador
        sesion.id_local = self.id_local
        entradas = []
        for jid in range(len(self.clases)):
            if jid == self.id_local:
                entradas.append(EntradaLocalCliente(adaptador, id_jugador=jid))
            else:
                entradas.append(EntradaRemotaHost(adaptador, id_jugador=jid))
        sesion.entradas = entradas
        return sesion


def preparar_sesion_online(clases, mando, conexion, es_host):
    """Inicializa la configuración de red y prepara las entradas para Host o Join."""
    if es_host:
        config = ConfigSesionHost(conexion, clases)
        return clases, mando, config
    else:
        id_local = conexion.id_jugador if getattr(conexion, "id_jugador", None) is not None else 1
        config = ConfigSesionJoin(conexion, clases, id_local=id_local)
        return clases, mando, config
