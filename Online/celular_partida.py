"""El celular del modo Online dentro del juego: la fachada `ControlCelular`.

Es lo único que Main.py (la partida) y Online/lobby.py (la sala de espera)
conocen del celular. Junta las piezas:

    Online/chat_celular.py         el canal de red de la sala (chat + semilla y
                                   reloj del feed) que tienen el Servidor y el Cliente
    Online/feed_celular.py         el feed en vivo (simulación determinista)
    Online/celular.py              lo que la interfaz recuerda entre cuadros
    Online/disposicion_celular.py  dónde va el botón, el globo y el celular
    Online/celular_render.py       el dibujo y el ratón

Quien lo usa llama, una vez por cuadro, a `manejar_evento` (por cada
evento), `actualizar` y `dibujar`, diciendo si el celular está `disponible`
(el mundo en marcha, sin reunión, diálogo ni pausa) y en qué lugar está
(una Escena o disposicion_celular.SALA).

Con el celular abierto:
    - el teclado, el ratón y el control son del celular (manejar_evento
      devuelve True y quien llama hace `continue`);
    - el personaje local se queda quieto: las entradas Online de esta PC
      (EntradaTecladoRed / EntradaLocalCliente, Online/sesion_red.py) quedan
      `bloqueada` y devuelven un pedido quieto. El mundo NO se pausa: es
      Online, y en el host el combate de todos sigue corriendo.

Regla del modo Online: el celular nunca tumba la partida. Cada punto de
entrada atrapa sus errores, los anota en Online/errores_online.log
(Online/registro_errores.py) y, si estaba abierto, lo cierra. Los módulos
del feed y del dibujo se importan al primer uso: si faltaran, simplemente no
hay celular (el resto del juego sigue igual).
"""

import importlib

import pygame

from src.core import assets
from src.core.entrada import InputJugador
from src.core.escenas import Escena
from src.ui import hud

from Online import disposicion_celular, registro_errores
from Online.celular import CHAT, FEED, Celular, Contacto, Perfil
from Online.chat_celular import COMENTARIO, JUGADOR, MAX_LARGO_MENSAJE_CELULAR, SALA, SISTEMA_ENTRO, SISTEMA_SALIO

TECLA_CELULAR = pygame.K_c  # abre el celular (y lo cierra desde Inicio: en el Chat la "c" se escribe)
LETRA_CELULAR = "c"  # su TEXTINPUT, que se traga al abrir con la tecla (Online/celular.py)
BOTON_MANDO_CELULAR = pygame.CONTROLLER_BUTTON_BACK  # Share en el DualShock 4
TECLAS_ENVIAR = (pygame.K_RETURN, pygame.K_KP_ENTER)
MODIFICADORES_SIN_C = pygame.KMOD_CTRL | pygame.KMOD_ALT  # Ctrl+C / Alt+C no abren el celular

PASO_RUEDA = 48  # px por muesca de la rueda del ratón
PASO_FLECHA = 40  # px por ↑ ↓ (o la cruceta)
PASO_PAGINA = 320  # px por RePág / AvPág

DURACION_AVISO = 4.0  # s del globo "J2 · Candidato: hola" junto al botón (celular cerrado)
ESPERA_SONIDO = 1.5  # s mínimos entre dos sonidos de mensaje nuevo
SONIDO_MENSAJE = "notificacion"  # assets.SONIDOS
ESCENAS_PELIGRO = (Escena.MAZMORRA, Escena.JEFE)  # franja ámbar: el personaje está quieto entre enemigos
RESPUESTAS_RESPALDO = ("¡Hola!", "¡Vamos!", "Ayuda", "Cuidado")
ALTO_MINIMO_BOTON_GRANDE = 60  # más bajo, el botón se dibuja compacto (la píldora de la sala)

# Con el celular abierto se lleva todo lo que viene del teclado, el ratón y
# el control. Lo demás (cerrar la ventana, conectar un control...) sigue su camino.
EVENTOS_DEL_CELULAR = frozenset({
    pygame.KEYDOWN, pygame.KEYUP, pygame.TEXTINPUT, pygame.TEXTEDITING,
    pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.MOUSEMOTION, pygame.MOUSEWHEEL,
    pygame.CONTROLLERBUTTONDOWN, pygame.CONTROLLERBUTTONUP, pygame.CONTROLLERAXISMOTION,
    pygame.JOYBUTTONDOWN, pygame.JOYBUTTONUP, pygame.JOYAXISMOTION, pygame.JOYHATMOTION,
})

_modulos = {}  # nombre -> módulo importado, o None si no se pudo (se intenta una sola vez)


def _modulo(nombre):
    """Importa al primer uso Online.feed_celular u Online.celular_render. Si
    falla, se anota y el celular queda sin usar (nunca rompe la partida)."""
    if nombre not in _modulos:
        try:
            _modulos[nombre] = importlib.import_module(nombre)
        except Exception:  # noqa: BLE001 - un celular roto no debe tumbar el juego
            registro_errores.registrar(f"importar {nombre}")
            _modulos[nombre] = None
    return _modulos[nombre]


def _render():
    return _modulo("Online.celular_render")


def _feed_modulo():
    return _modulo("Online.feed_celular")


class ControlCelular:
    """Lo único que Main.py y el lobby conocen del celular."""

    def __init__(self, conexion, perfil, puede_escribir=None, reducir_movimiento=False, adaptador=None,
                 entradas_fn=None, contenido=None):
        self.conexion = conexion
        self.canal = getattr(conexion, "celular", None)  # CanalCelular del Servidor o del Cliente
        self._perfil = perfil
        self._puede_escribir = puede_escribir or (lambda: True)
        self.adaptador = adaptador
        self._entradas_fn = entradas_fn or (lambda: ())
        self._contenido = contenido
        self.estado = Celular(MAX_LARGO_MENSAJE_CELULAR, reducir_movimiento)
        self._feed = None
        self._dibujado = None  # último DibujoCelular: dónde quedó cada cosa, para el ratón
        self._aviso = None  # [MensajeChat, s que le quedan] del globo junto al botón
        self._espera_sonido = 0.0
        self._bloqueado = False  # las entradas de esta PC están quietas
        self._quieto_avisado = False  # ya se detuvo al personaje en esta apertura
        # Lo que ya estaba en el chat al crear el control (p. ej. lo de la sala
        # de espera) no se vuelve a anunciar; la insignia sí lo cuenta.
        self._ultimo_visto = self.canal.ultimo_numero() if self.canal is not None else 0

    # ------------------------------------------------------------------
    # Cómo se crea
    # ------------------------------------------------------------------

    @classmethod
    def para_partida(cls, sesion, adaptador_red, preferencias):
        """El celular de una partida Online (Main._jugar), o None si no es
        Online o la conexión no tiene celular (p. ej. un adaptador de prueba)."""
        try:
            if adaptador_red is None:
                return None
            conexion = getattr(adaptador_red, "servidor", None)
            if conexion is None:
                conexion = getattr(adaptador_red, "cliente", None)
            if getattr(conexion, "celular", None) is None or not callable(getattr(conexion, "escribir_chat", None)):
                return None

            def perfil(id_red):
                return _perfil_de_jugador(sesion, adaptador_red, id_red)

            def puede_escribir():
                # El expulsado por votación (fantasma) solo lee; el host además lo silencia.
                expulsado = getattr(adaptador_red, "expulsado", None)
                return not (callable(expulsado) and expulsado(getattr(sesion, "id_local", 0)))

            def entradas():
                # Solo las entradas de ESTA PC tienen `bloqueada` (las remotas no).
                return [e for e in (getattr(sesion, "entradas", None) or ()) if hasattr(e, "bloqueada")]

            return cls(conexion, perfil, puede_escribir, getattr(preferencias, "reducir_movimiento", False),
                       adaptador_red, entradas)
        except Exception:  # noqa: BLE001
            registro_errores.registrar("ControlCelular.para_partida")
            return None

    @classmethod
    def para_sala(cls, conexion, perfil, reducir_movimiento=False):
        """El celular de la sala de espera (Online/lobby.py)."""
        return cls(conexion, perfil, reducir_movimiento=reducir_movimiento)

    # ------------------------------------------------------------------
    # Consultas
    # ------------------------------------------------------------------

    @property
    def abierto(self):
        return self.estado.abierto

    def id_local(self):
        """Id de red de esta PC: el host es 0 (el Servidor no tiene id_jugador);
        el invitado, el que le dio el host (-1 mientras no llega: nada es propio)."""
        ident = getattr(self.conexion, "id_jugador", 0)
        return ident if isinstance(ident, int) and not isinstance(ident, bool) else -1

    def no_leidos(self):
        return self.canal.no_leidos(self.id_local()) if self.canal is not None else 0

    def controles(self):
        """La barra de controles con el celular abierto."""
        render = _render()
        if render is None:
            return []
        try:
            return render.controles(self.estado, self._puede_escribir())
        except Exception:  # noqa: BLE001
            registro_errores.registrar("ControlCelular.controles")
            return []

    def _listo(self):
        """¿Se puede usar? Hace falta el canal de red y los módulos del feed y del dibujo."""
        return self.canal is not None and _render() is not None and _feed_modulo() is not None

    def _rect_boton(self, disponible, lugar, cantidad_jugadores, hud_detallado):
        """Rect del botón, o None si ahora no hay celular (no disponible o en un lugar sin celular)."""
        if not disponible or not self._listo():
            return None
        return disposicion_celular.rect_boton(lugar, cantidad_jugadores, hud_detallado)

    def _perfil_seguro(self, id_red):
        try:
            perfil = self._perfil(id_red)
            if isinstance(perfil, Perfil):
                return perfil
        except Exception:  # noqa: BLE001
            registro_errores.registrar("ControlCelular.perfil")
        return Perfil(f"J{id_red + 1}" if isinstance(id_red, int) else "J?", assets.COLOR_TEXTO_SECUNDARIO)

    def _escribe(self):
        try:
            return bool(self._puede_escribir())
        except Exception:  # noqa: BLE001
            registro_errores.registrar("ControlCelular.puede_escribir")
            return False

    def _respuestas(self):
        """Las respuestas rápidas del chat (Online/datos/celular.json)."""
        modulo = _feed_modulo()
        try:
            respuestas = modulo.cargar_contenido().get("respuestas_rapidas") if modulo is not None else None
        except Exception:  # noqa: BLE001
            registro_errores.registrar("ControlCelular.respuestas")
            respuestas = None
        if isinstance(respuestas, (list, tuple)) and respuestas and all(isinstance(r, str) for r in respuestas):
            return tuple(respuestas)
        return RESPUESTAS_RESPALDO

    def _feed_actual(self):
        """El feed de la sala. Se rehace si cambió la semilla (el invitado se
        sincronizó con el host): así todas las PCs simulan el mismo."""
        modulo = _feed_modulo()
        if modulo is None or self.canal is None:
            return None
        semilla = self.canal.semilla
        if self._feed is None or getattr(self._feed, "semilla", None) != semilla:
            self._feed = modulo.FeedCelular(semilla, self._contenido)
            self._feed.avanzar(self.canal.segundos())
            # Lo que ya estaba al abrir no cuenta como "nuevas publicaciones".
            self.estado.publicaciones_vistas = getattr(self._feed, "total_publicaciones", 0)
            self.estado.scroll_feed = 0.0
            self.estado.ancla_feed = None
            self.estado.me_gusta.clear()
        return self._feed

    # ------------------------------------------------------------------
    # Eventos
    # ------------------------------------------------------------------

    def manejar_evento(self, evento, disponible, lugar, cantidad_jugadores=2, hud_detallado=False):
        """True si el evento era del celular (quien llama hace `continue`).
        Cerrado: solo C, el clic en su botón y Share del control. Abierto: todo
        el teclado, el ratón y el control (salvo cerrar la ventana)."""
        try:
            return self._manejar_evento(evento, disponible, lugar, cantidad_jugadores, hud_detallado)
        except Exception:  # noqa: BLE001
            registro_errores.registrar("ControlCelular.manejar_evento")
            self._cerrar()
            return False

    def _manejar_evento(self, evento, disponible, lugar, cantidad_jugadores, hud_detallado):
        rect = self._rect_boton(disponible, lugar, cantidad_jugadores, hud_detallado)
        tipo = evento.type
        if not self.estado.abierto:
            if rect is None:
                return False
            if tipo == pygame.KEYDOWN and evento.key == TECLA_CELULAR \
                    and not getattr(evento, "mod", 0) & MODIFICADORES_SIN_C:
                self._abrir(por_tecla=LETRA_CELULAR)
                return True
            if tipo == pygame.MOUSEBUTTONDOWN and evento.button == 1 and pygame.Rect(rect).collidepoint(evento.pos):
                self._abrir()
                return True
            if tipo == pygame.CONTROLLERBUTTONDOWN and evento.button == BOTON_MANDO_CELULAR:
                self._abrir()
                return True
            return False
        if rect is None:
            # Dejó de estar disponible (empezó una reunión, un diálogo...): se
            # cierra y el evento sigue su camino.
            self._cerrar()
            return False
        if tipo == pygame.KEYDOWN:
            self._tecla(evento)
        elif tipo == pygame.TEXTINPUT:
            self._texto(getattr(evento, "text", ""))
        elif tipo == pygame.MOUSEBUTTONDOWN and evento.button == 1:
            self._clic(evento.pos)
        elif tipo == pygame.MOUSEWHEEL:
            self._desplazar_lista(-getattr(evento, "y", 0) * PASO_RUEDA)
        elif tipo == pygame.CONTROLLERBUTTONDOWN:
            self._boton_mando(evento.button)
        return tipo in EVENTOS_DEL_CELULAR

    def _abrir(self, por_tecla=None):
        """Abre en el Chat si hay mensajes sin leer; si no, en la última app usada."""
        app = CHAT if self.no_leidos() > 0 else None
        self.estado.abrir(app, por_tecla=por_tecla)
        self._aviso = None
        self._quieto_avisado = False
        self._fijar_bloqueo(True)  # desde este mismo cuadro el personaje no recibe teclas

    def _cerrar(self):
        """Cierra. Las entradas se liberan en actualizar, cuando ya no está
        apretado el botón del ratón: el clic que cierra no dispara."""
        if self.estado.abierto:
            self.estado.cerrar()

    def _desplazar_lista(self, delta_arriba_negativo):
        """`delta` en el sentido del feed (+ = bajar). En el chat la lista crece
        hacia arriba (scroll_chat cuenta desde abajo): ahí el signo se invierte."""
        if self.estado.app == CHAT:
            self.estado.desplazar(-delta_arriba_negativo)
        else:
            self.estado.desplazar(delta_arriba_negativo)

    def _tecla(self, evento):
        tecla = evento.key
        if tecla == pygame.K_ESCAPE:
            if self.estado.comentando:
                self.estado.cerrar_publicacion()  # de la publicación abierta, Esc vuelve al feed
            elif self.estado.en_conversacion:
                self.estado.cerrar_conversacion()  # de un chat, Esc vuelve a la lista de chats
            else:
                self._cerrar()
        elif tecla == pygame.K_TAB:
            self.estado.cambiar_app()
        elif self.estado.comentando and tecla == pygame.K_BACKSPACE:
            self.estado.borrar()
        elif self.estado.comentando and tecla in TECLAS_ENVIAR:
            self._comentar()
        elif tecla == TECLA_CELULAR and self.estado.app == FEED and not self.estado.comentando:
            self._cerrar()  # en el Chat y al comentar la "c" se escribe (llega como TEXTINPUT)
        elif tecla == pygame.K_UP:
            self._desplazar_lista(-PASO_FLECHA)
        elif tecla == pygame.K_DOWN:
            self._desplazar_lista(PASO_FLECHA)
        elif tecla == pygame.K_PAGEUP:
            self._desplazar_lista(-PASO_PAGINA)
        elif tecla == pygame.K_PAGEDOWN:
            self._desplazar_lista(PASO_PAGINA)
        elif tecla in (pygame.K_HOME, pygame.K_END):
            self.estado.ir_a_lo_nuevo()
        elif self.estado.en_conversacion:
            if tecla == pygame.K_BACKSPACE:
                self.estado.borrar()
            elif tecla in TECLAS_ENVIAR:
                self._enviar_lo_escrito()

    def _texto(self, texto):
        if self.estado.debe_ignorar_texto(texto):
            return  # la "c" con la que se abrió
        if (self.estado.comentando or self.estado.en_conversacion) and self._escribe():
            self.estado.escribir(texto)

    def _comentar(self):
        """Comentario propio en la publicación abierta (solo en esta PC): sube
        el contador de comentarios con su "+1" y entra arriba de la lista."""
        id_publicacion = self.estado.publicacion_abierta
        comentar = getattr(self.conexion, "comentar", None)
        if self.canal is None or not callable(comentar) or not self._escribe():
            return
        texto = self.estado.comentar(self.canal.segundos())
        if texto is not None and not comentar(id_publicacion, texto):
            self.estado.texto_comentario = texto  # no salió (anti-spam o sin conexión): no se pierde

    def _clic(self, posicion):
        render = _render()
        if render is None or self._dibujado is None:
            return
        accion, dato = render.objetivo_en(self._dibujado, posicion)
        if accion in (render.FUERA, render.CERRAR):
            self._cerrar()
        elif accion == render.PESTANA:
            self.estado.cambiar_app(dato)
        elif accion == render.ENVIAR:
            if self.estado.comentando:
                self._comentar()
            else:
                self._enviar_lo_escrito()
        elif accion == render.RESPUESTA:
            self._enviar_respuesta(dato)
        elif accion == render.ME_GUSTA:
            self.estado.alternar_me_gusta(dato)
        elif accion == render.COMPARTIR:
            self.estado.alternar_repost(dato)
        elif accion == render.ABRIR:
            self.estado.abrir_publicacion(dato)
        elif accion == render.VOLVER:
            if self.estado.app == CHAT:
                self.estado.cerrar_conversacion()
            else:
                self.estado.cerrar_publicacion()
        elif accion == render.CONTACTO:
            self.estado.abrir_conversacion(dato)
        elif accion == render.NUEVAS:
            self.estado.ir_a_lo_nuevo()
        elif accion == render.ENTRADA and not self.estado.comentando:
            self.estado.cambiar_app(CHAT)

    def _boton_mando(self, boton):
        if boton in (pygame.CONTROLLER_BUTTON_B, BOTON_MANDO_CELULAR):
            self._cerrar()
        elif boton in (pygame.CONTROLLER_BUTTON_LEFTSHOULDER, pygame.CONTROLLER_BUTTON_RIGHTSHOULDER):
            self.estado.cambiar_app()
        elif boton == pygame.CONTROLLER_BUTTON_DPAD_UP:
            self._desplazar_lista(-PASO_FLECHA)
        elif boton == pygame.CONTROLLER_BUTTON_DPAD_DOWN:
            self._desplazar_lista(PASO_FLECHA)
        elif self.estado.app == CHAT:
            cantidad = len(self._respuestas())
            if boton == pygame.CONTROLLER_BUTTON_DPAD_LEFT:
                self.estado.mover_respuesta(-1, cantidad)
            elif boton == pygame.CONTROLLER_BUTTON_DPAD_RIGHT:
                self.estado.mover_respuesta(1, cantidad)
            elif boton == pygame.CONTROLLER_BUTTON_A:
                self._enviar_respuesta(self.estado.respuesta_rapida)

    # ------------------------------------------------------------------
    # Mandar al chat de la sala
    # ------------------------------------------------------------------

    def _enviar_lo_escrito(self):
        """Enter o el botón enviar. La caja se vacía solo si el mensaje salió
        (el host puede rechazarlo por el anti-spam: así no se pierde)."""
        texto = self.estado.texto.strip()
        if texto and self._enviar(texto):
            self.estado.texto = ""

    def _enviar_respuesta(self, indice):
        respuestas = self._respuestas()
        if isinstance(indice, int) and 0 <= indice < len(respuestas):
            self._enviar(respuestas[indice])

    def _enviar(self, texto):
        if not self._escribe():
            return False
        conversacion = self.estado.conversacion
        if conversacion is None:
            return False
        destino = None if conversacion == SALA else conversacion
        enviado = bool(self.conexion.escribir_chat(texto) if destino is None
                       else self.conexion.escribir_chat(texto, destino=destino))
        if enviado:
            self.estado.ir_a_lo_nuevo()  # el chat baja hasta el mensaje propio
        return enviado

    # ------------------------------------------------------------------
    # Cada cuadro
    # ------------------------------------------------------------------

    def actualizar(self, dt, disponible, lugar, jugador=None, cantidad_jugadores=2, hud_detallado=False):
        """Avanza el feed, revisa el chat y el bloqueo de las entradas.
        Devuelve los ids de sonido a reproducir (p. ej. ["notificacion"])."""
        try:
            return self._actualizar(dt, disponible, lugar, jugador, cantidad_jugadores, hud_detallado)
        except Exception:  # noqa: BLE001
            registro_errores.registrar("ControlCelular.actualizar")
            self._cerrar()
            self._fijar_bloqueo(False)
            return []

    def _actualizar(self, dt, disponible, lugar, jugador, cantidad_jugadores, hud_detallado):
        if self.canal is None:
            return []
        rect = self._rect_boton(disponible, lugar, cantidad_jugadores, hud_detallado)
        if self.estado.abierto and rect is None:
            self._cerrar()  # empezó una reunión, un diálogo, la pausa o se fue a la terminal
        self.estado.actualizar(dt)
        self._espera_sonido = max(0.0, self._espera_sonido - dt)
        if self._listo():
            feed = self._feed_actual()
            if feed is not None:
                feed.avanzar(self.canal.segundos())
        sonidos = self._revisar_chat(dt)
        self._actualizar_bloqueo(jugador, lugar)
        return sonidos

    def _revisar_chat(self, dt):
        """Mensajes nuevos: con el Chat a la vista se dan por leídos; si no,
        el de otro jugador trae el globo (celular cerrado) y un sonido."""
        id_local = self.id_local()
        en_pantalla = self.estado.conversacion if self.estado.abierto and self.estado.en_conversacion else None
        if en_pantalla is not None:
            self.canal.marcar_leidos(en_pantalla)  # solo el chat que se está viendo
        sonidos = []
        mensajes = self.canal.mensajes()
        self._comentarios_de_jugadores(mensajes, id_local)
        nuevos = [m for m in mensajes if m.numero > self._ultimo_visto]
        if nuevos:
            self._ultimo_visto = nuevos[-1].numero
            ajenos = [m for m in nuevos if m.tipo == JUGADOR and m.autor != id_local
                      and m.conversacion(id_local) not in (None, en_pantalla)]
            if ajenos:
                if not self.estado.abierto:
                    self._aviso = [ajenos[-1], DURACION_AVISO]
                if self._espera_sonido <= 0.0:
                    sonidos.append(SONIDO_MENSAJE)
                    self._espera_sonido = ESPERA_SONIDO
        if self._aviso is not None:
            self._aviso[1] -= dt
            if self._aviso[1] <= 0.0 or self.estado.abierto:
                self._aviso = None
        return sonidos

    def _comentarios_de_jugadores(self, mensajes, id_local):
        """Los comentarios que los jugadores pusieron en las publicaciones (por
        red, iguales en todas las PCs): id de la publicación -> [(Perfil, texto,
        segundos, es de esta PC)]. Los dibuja la publicación abierta."""
        comentarios = {}
        for mensaje in mensajes:
            if mensaje.tipo == COMENTARIO:
                comentarios.setdefault(mensaje.publicacion, []).append(
                    (self._perfil_seguro(mensaje.autor), mensaje.texto, mensaje.segundos, mensaje.autor == id_local))
        self.estado.comentarios_red = comentarios

    def contactos(self):
        """La lista de chats: la sala (todos) y cada jugador conectado, cada uno
        con su último mensaje y sus no leídos. O(n) en los mensajes."""
        id_local = self.id_local()
        sala = getattr(self.conexion, "sala", None)
        try:
            conectados = [j for j in sala.jugadores() if j != id_local] if sala is not None else []
        except Exception:  # noqa: BLE001
            conectados = []
        ultimos = {}
        for mensaje in self.canal.mensajes():
            conversacion = mensaje.conversacion(id_local)
            if conversacion is not None:
                ultimos[conversacion] = mensaje
        no_leidos = self.canal.no_leidos_por_conversacion(id_local)
        filas = []
        for conversacion in [SALA, *conectados]:
            perfil = None if conversacion == SALA else self._perfil_seguro(conversacion)
            etiqueta = "Sala (todos)" if perfil is None else perfil.etiqueta
            ultimo = ultimos.get(conversacion)
            filas.append(Contacto(conversacion, etiqueta, perfil, self._vista_previa(ultimo, id_local, perfil),
                                  ultimo.segundos if ultimo is not None else None, no_leidos.get(conversacion, 0)))
        return filas

    def _vista_previa(self, mensaje, id_local, perfil):
        if mensaje is None:
            return "Escríbele en privado" if perfil is not None else "Habla con todos los de la sala"
        if mensaje.tipo in (SISTEMA_ENTRO, SISTEMA_SALIO):
            accion = "entró a la sala" if mensaje.tipo == SISTEMA_ENTRO else "salió de la sala"
            return f"{self._perfil_seguro(mensaje.autor).etiqueta} {accion}"
        if mensaje.autor == id_local:
            return f"Tú: {mensaje.texto}"
        if perfil is None:  # en la sala se ve quién lo dijo
            return f"{self._perfil_seguro(mensaje.autor).etiqueta.split(' · ')[0]}: {mensaje.texto}"
        return mensaje.texto

    def _mensajes_en_pantalla(self):
        """Los mensajes del chat abierto (el privado o el de la sala)."""
        id_local = self.id_local()
        conversacion = self.estado.conversacion
        return tuple(m for m in self.canal.mensajes()
                     if conversacion is not None and m.conversacion(id_local) == conversacion)

    def _actualizar_bloqueo(self, jugador, lugar):
        """Abierto: las entradas de esta PC quedan quietas. Al abrir en la
        ciudad, además se detiene la animación de caminar y el invitado le
        avisa al host que quedó quieto. Cerrado: se liberan cuando ya no está
        apretado ningún botón del ratón (el clic que cerró no dispara)."""
        if self.estado.abierto:
            self._fijar_bloqueo(True)
            if not self._quieto_avisado:
                self._quieto_avisado = True
                self._quedarse_quieto(jugador, lugar)
        elif self._bloqueado and not any(pygame.mouse.get_pressed()[:3]):
            self._fijar_bloqueo(False)

    def _quedarse_quieto(self, jugador, lugar):
        if lugar != Escena.CIUDAD or jugador is None:
            return
        jugador.caminando_en_ciudad = False  # si no, seguiría con la animación de caminar en su lugar
        enviar_input = getattr(self.adaptador, "enviar_input", None)
        if callable(enviar_input):  # invitado: el host también lo ve quieto
            enviar_input(InputJugador())

    def _fijar_bloqueo(self, bloqueado):
        self._bloqueado = bloqueado
        for entrada in self._entradas_fn():
            entrada.bloqueada = bloqueado

    # ------------------------------------------------------------------
    # Dibujo
    # ------------------------------------------------------------------

    def dibujar(self, pantalla, disponible, lugar, cantidad_jugadores=2, hud_detallado=False):
        """Cerrado: el botón CELULAR (con la insignia de no leídos) y el globo
        del último mensaje. Abierto (o cerrándose): el celular encima de todo
        y, abierto, su barra de controles sobre la del juego."""
        try:
            self._dibujar(pantalla, disponible, lugar, cantidad_jugadores, hud_detallado)
        except Exception:  # noqa: BLE001
            registro_errores.registrar("ControlCelular.dibujar")
            self._cerrar()

    def _dibujar(self, pantalla, disponible, lugar, cantidad_jugadores, hud_detallado):
        render = _render()
        rect = self._rect_boton(disponible, lugar, cantidad_jugadores, hud_detallado)
        if render is None or rect is None:
            self._dibujado = None
            return
        if not self.estado.abierto:
            compacto = rect[3] < ALTO_MINIMO_BOTON_GRANDE
            render.dibujar_boton(pantalla, rect, self.no_leidos(), self.estado.reloj, compacto=compacto)
            if self._aviso is not None:
                mensaje, restante = self._aviso
                render.dibujar_aviso(pantalla, disposicion_celular.rect_aviso(lugar, rect),
                                     self._perfil_seguro(mensaje.autor), mensaje.texto,
                                     max(0.0, min(1.0, restante / DURACION_AVISO)))
        if not self.estado.visible:
            self._dibujado = None
            return
        feed = self._feed_actual()
        if feed is None:
            return
        cuerpo = disposicion_celular.rect_celular(self.estado.apertura)
        self._dibujado = render.dibujar_celular(
            pantalla, cuerpo, self.estado, feed, self._mensajes_en_pantalla(), self._perfil_seguro, self.id_local(),
            self._escribe(), self._respuestas(), self.canal.segundos(), en_peligro=lugar in ESCENAS_PELIGRO,
            no_leidos=self.no_leidos(), contactos=self.contactos())
        if self.estado.abierto:
            hud.dibujar_barra_controles(pantalla, render.controles(self.estado, self._escribe()))


def _perfil_de_jugador(sesion, adaptador_red, id_red):
    """Perfil del jugador con id de red `id_red` en la partida: "J2 · Candidato"
    con su color, su rol y la ropa de los vestidores. El número es su lugar en
    la partida (igual que en los paneles y la reunión), no su id de red."""
    jugadores = getattr(sesion, "jugadores", None) or []  # se lee cada vez: reiniciar la partida la cambia
    indice_de = getattr(adaptador_red, "_indice_de_id", None)
    indice = indice_de(id_red) if callable(indice_de) else id_red
    if isinstance(indice, int) and not isinstance(indice, bool) and 0 <= indice < len(jugadores):
        jugador = jugadores[indice]
        nombre = getattr(jugador, "NOMBRE", "")
        return Perfil(f"J{indice + 1} · {nombre}" if nombre else f"J{indice + 1}",
                      getattr(jugador, "COLOR", assets.COLOR_TEXTO_SECUNDARIO), getattr(jugador, "rol", None),
                      getattr(jugador, "apariencia", None), bool(getattr(jugador, "expulsado", False)))
    return Perfil(f"J{id_red + 1}" if isinstance(id_red, int) else "J?", assets.COLOR_TEXTO_SECUNDARIO)
