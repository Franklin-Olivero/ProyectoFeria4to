"""Estado de la interfaz del celular del modo Online (lógica pura, sin pygame).

El celular es una ventana sobre la partida: se abre con C (o con un clic en su
botón) y tiene dos apps, Inicio (el feed en vivo de Civitas) y Chat (el chat
de la sala). Mientras está abierto, el teclado y el ratón son suyos. Aquí vive
solo lo que la interfaz recuerda de un cuadro al siguiente: si está abierto,
qué app se ve, lo que se está escribiendo, cuánto se desplazó cada lista, los
"me gusta" propios y las cifras que se están animando. El chat y el feed
llegan de afuera (Online/chat_celular.py y Online/feed_celular.py), quién
escribe se describe con un Perfil y el dibujo está en Online/celular_render.py.

Por qué se "traga" una letra: al abrir con la tecla C, SDL manda primero el
KEYDOWN y enseguida el TEXTINPUT "c". Si el celular abre directo en el Chat,
esa "c" se escribiría sola en la caja. Se ignora UNA vez y solo si llega en
los VENTANA_TRAGAR_TECLA segundos siguientes; después la "c" se escribe normal.

Estructuras de datos (para la exposición):
    me_gusta   conjunto (set) de ids de publicaciones con corazón propio:
               alternar y consultar un "me gusta" cuesta O(1).
    _cifras    diccionario clave -> animación "+N" de una estadística, usado
               como caché LRU: cada consulta saca la clave y la vuelve a meter
               (queda de última, O(1)) y al pasar de MAX_CIFRAS_RECORDADAS se
               olvida la primera, que es la que hace más tiempo no se dibuja.
               Así no crece sin límite aunque el feed publique durante horas.
"""

import math
from dataclasses import dataclass

FEED = "feed"
CHAT = "chat"
APPS = (FEED, CHAT)

DURACION_APERTURA = 0.22  # s de la animación de abrir/cerrar (deslizarse desde abajo)
DURACION_CIFRA = 0.9  # s que dura el "+N" de una estadística que subió
VENTANA_TRAGAR_TECLA = 0.25  # s: el TEXTINPUT de la letra con que se abrió se ignora
LARGO_MAXIMO_POR_DEFECTO = 80  # la fachada pasa chat_celular.MAX_LARGO_MENSAJE_CELULAR

# Animación de las cifras (notar_cifra).
VENTANA_ACUMULAR_CIFRA = 0.3  # s: dos subidas así de seguidas se suman en un solo "+N"
OLVIDO_CIFRA = 0.5  # s sin dibujarse: el próximo valor es punto de partida (no se vio subir)
MAX_CIFRAS_RECORDADAS = 400  # tope del diccionario de cifras (LRU)


@dataclass(frozen=True)
class Perfil:
    """Cómo se muestra un jugador en el celular (nombre, color y muñeco)."""

    etiqueta: str  # "J2 · Candidato"
    color: tuple  # color del jugador (RGB)
    rol: str | None = None  # "candidato" (clave de sprite) o None
    apariencia: object = None  # src.core.apariencia.Apariencia o None
    fantasma: bool = False  # expulsado por votación: solo lee


def formatear_cifra(n):
    """Una estadística como la muestran las redes: 987, "1.2 mil", "12 mil",
    "123 mil", "1.2 M", "12 M". Se trunca (nunca se redondea hacia arriba):
    9 999 es "9.9 mil", no "10 mil", y la cifra mostrada nunca baja cuando el
    número sube. Sin ".0": 3 000 es "3 mil". Negativos, None o cualquier cosa
    que no sea un número dan "0"."""
    if isinstance(n, bool) or not isinstance(n, (int, float)):
        return "0"
    if isinstance(n, float) and not math.isfinite(n):
        return "0"
    n = int(n)
    if n <= 0:
        return "0"
    if n < 1_000:
        return str(n)
    if n < 10_000:
        return _con_decimal(n // 100, "mil")
    if n < 1_000_000:
        return f"{n // 1_000} mil"
    if n < 10_000_000:
        return _con_decimal(n // 100_000, "M")
    return f"{n // 1_000_000} M"


def _con_decimal(decimas, unidad):
    """12 decimas -> "1.2 <unidad>"; 30 -> "3 <unidad>" (sin ".0")."""
    enteros, decimal = divmod(decimas, 10)
    return f"{enteros} {unidad}" if decimal == 0 else f"{enteros}.{decimal} {unidad}"


def _numero(valor, por_defecto=0.0):
    """float finito o `por_defecto` (la interfaz nunca se rompe por un dato raro)."""
    try:
        valor = float(valor)
    except (TypeError, ValueError):
        return por_defecto
    return valor if math.isfinite(valor) else por_defecto


class Celular:
    """Lo que la interfaz del celular recuerda entre cuadros.

    abierto               si se ve el celular (lo decide quien lo usa).
    app                   FEED o CHAT (FEED al empezar).
    texto                 lo que se está escribiendo en el chat.
    scroll_feed           px desplazados desde ARRIBA del feed (>= 0).
    scroll_chat           px desplazados desde ABAJO del chat (0 = pegado al
                          último mensaje; más = mensajes más viejos).
    apertura              0..1 de la animación de abrir (1 = abierto del todo).
    reloj                 s acumulados en actualizar (para las animaciones).
    respuesta_rapida      chip de respuesta rápida enfocado con el control.
    me_gusta              ids de publicaciones con corazón propio (solo esta PC).
    publicaciones_vistas  feed.total_publicaciones que ya se vio arriba del todo
                          (si llegan más estando abajo: píldora "Nuevas").
    mensajes_vistos       número del último mensaje del chat que se vio pegado
                          abajo (None = el chat nunca se dibujó: al primer dibujo
                          cuenta como visto lo que ya había).
    ancla_feed, ancla_chat  los usa el dibujo para que la vista no salte cuando
                          llega contenido nuevo mientras se lee más abajo/arriba.
    """

    def __init__(self, largo_maximo=LARGO_MAXIMO_POR_DEFECTO, reducir_movimiento=False):
        self.largo_maximo = max(1, int(_numero(largo_maximo, LARGO_MAXIMO_POR_DEFECTO)))
        self.reducir_movimiento = bool(reducir_movimiento)
        self.abierto = False
        self.app = FEED
        self.texto = ""
        self.scroll_feed = 0.0
        self.scroll_chat = 0.0
        self.apertura = 0.0
        self.reloj = 0.0
        self.respuesta_rapida = 0
        self.me_gusta = set()
        self.publicaciones_vistas = 0
        self.mensajes_vistos = None
        self.ancla_feed = None
        self.ancla_chat = None
        self._letra_a_tragar = None  # letra con la que se abrió (en minúscula) o None
        self._tragar_hasta = 0.0  # reloj hasta el que se traga esa letra
        self._cifras = {}  # clave -> [valor, delta acumulado, inicio de la animación o None, último dibujo]

    @property
    def visible(self):
        """True mientras haya algo que dibujar: abierto o cerrándose (animación)."""
        return self.abierto or self.apertura > 0.0

    # ------------------------------------------------------------------
    # Abrir, cerrar y cambiar de app
    # ------------------------------------------------------------------

    def abrir(self, app=None, por_tecla=None):
        """Abre el celular (en `app` si se indica). `por_tecla`: la letra con la
        que se abrió ("c"); su TEXTINPUT se ignora durante VENTANA_TRAGAR_TECLA."""
        self.abierto = True
        if app in APPS:
            self.app = app
        if por_tecla:
            self._letra_a_tragar = str(por_tecla).lower()
            self._tragar_hasta = self.reloj + VENTANA_TRAGAR_TECLA
        else:
            self._letra_a_tragar = None
        if self.reducir_movimiento:
            self.apertura = 1.0

    def cerrar(self):
        """Cierra el celular. Lo que se estaba escribiendo se conserva (borrador)."""
        self.abierto = False
        self._letra_a_tragar = None
        if self.reducir_movimiento:
            self.apertura = 0.0

    def alternar(self, por_tecla=None):
        if self.abierto:
            self.cerrar()
        else:
            self.abrir(por_tecla=por_tecla)

    def cambiar_app(self, app=None):
        """Pasa a `app` (FEED o CHAT); None = la otra."""
        if app is None:
            app = CHAT if self.app == FEED else FEED
        if app in APPS:
            self.app = app

    # ------------------------------------------------------------------
    # Escribir en el chat
    # ------------------------------------------------------------------

    def debe_ignorar_texto(self, texto):
        """True (una sola vez) si `texto` es la letra con que se abrió el
        celular y llegó dentro de la ventana; quien llama no la escribe."""
        if self._letra_a_tragar is None or self.reloj > self._tragar_hasta:
            return False
        if str(texto).lower() != self._letra_a_tragar:
            return False
        self._letra_a_tragar = None
        return True

    def escribir(self, texto):
        """Agrega `texto` sin saltos de línea ni caracteres de control, sin
        pasar de largo_maximo. True si se agregó algo."""
        if not isinstance(texto, str):
            return False
        limpio = "".join(c for c in texto if c.isprintable())
        espacio = self.largo_maximo - len(self.texto)
        if not limpio or espacio <= 0:
            return False
        self.texto += limpio[:espacio]
        return True

    def borrar(self):
        """Retroceso: quita la última letra."""
        self.texto = self.texto[:-1]

    def tomar_mensaje(self):
        """Enter: devuelve lo escrito (sin espacios en los extremos) y vacía la
        caja; None si no había nada que mandar."""
        mensaje = self.texto.strip()
        self.texto = ""
        return mensaje or None

    # ------------------------------------------------------------------
    # Desplazamiento
    # ------------------------------------------------------------------

    def desplazar(self, delta_px):
        """Desplaza la app activa: en el feed, + baja; en el chat, + sube a
        los mensajes viejos. Nunca queda negativo; el máximo lo pone
        limitar_scroll (lo llama el dibujo, que sabe cuánto mide la lista)."""
        delta = _numero(delta_px)
        if self.app == CHAT:
            self.scroll_chat = max(0.0, self.scroll_chat + delta)
        else:
            self.scroll_feed = max(0.0, self.scroll_feed + delta)

    def limitar_scroll(self, app, alto_contenido, alto_visible):
        """Deja el desplazamiento de `app` entre 0 y lo que sobra de la lista."""
        maximo = max(0.0, _numero(alto_contenido) - _numero(alto_visible))
        if app == CHAT:
            self.scroll_chat = min(max(0.0, self.scroll_chat), maximo)
        elif app == FEED:
            self.scroll_feed = min(max(0.0, self.scroll_feed), maximo)

    def ir_a_lo_nuevo(self):
        """Clic en la píldora "Nuevas publicaciones" / "Nuevos mensajes": el
        feed vuelve arriba del todo y el chat, al último mensaje."""
        if self.app == CHAT:
            self.scroll_chat = 0.0
            self.ancla_chat = None
        else:
            self.scroll_feed = 0.0
            self.ancla_feed = None

    # ------------------------------------------------------------------
    # Me gusta y respuestas rápidas
    # ------------------------------------------------------------------

    def alternar_me_gusta(self, id_publicacion):
        """Pone o quita el corazón propio. True si quedó con me gusta. O(1)."""
        if id_publicacion in self.me_gusta:
            self.me_gusta.discard(id_publicacion)
            return False
        self.me_gusta.add(id_publicacion)
        return True

    def mover_respuesta(self, paso, cantidad):
        """Cruceta ← →: mueve el foco entre `cantidad` respuestas rápidas (da la vuelta)."""
        try:
            cantidad = int(cantidad)
            paso = int(paso)
        except (TypeError, ValueError):
            return
        if cantidad <= 0:
            self.respuesta_rapida = 0
            return
        self.respuesta_rapida = (self.respuesta_rapida + paso) % cantidad

    # ------------------------------------------------------------------
    # Cifras que suben ("+N")
    # ------------------------------------------------------------------

    def notar_cifra(self, clave, valor):
        """Registra el valor que se está dibujando de una estadística (clave
        p. ej. (id_publicacion, 0)). Si subió, arranca su animación "+N" (si
        la anterior empezó hace menos de VENTANA_ACUMULAR_CIFRA, se suma a
        ella: dos saltos casi juntos se ven como uno). Devuelve (delta,
        fracción que queda de 1 a 0) mientras dura la animación, si no None.

        La primera vez que ve una clave solo la guarda, y lo mismo si hace
        más de OLVIDO_CIFRA s que no se dibuja (celular cerrado, otra app o
        la tarjeta fuera de la vista): ese salto no se vio subir. Con
        reducir_movimiento siempre None. O(1): ver el docstring del módulo."""
        try:
            valor = int(valor)
        except (TypeError, ValueError, OverflowError):
            return None
        estado = self._cifras.pop(clave, None)  # sacar y volver a meter = la más reciente
        if estado is None or self.reloj - estado[3] > OLVIDO_CIFRA:
            estado = [valor, 0, None, self.reloj]
        else:
            anterior, delta, inicio, _ = estado
            if valor > anterior:
                acumula = inicio is not None and self.reloj - inicio <= VENTANA_ACUMULAR_CIFRA
                estado = [valor, (delta if acumula else 0) + valor - anterior, self.reloj, self.reloj]
            elif valor < anterior:  # bajó (p. ej. se quitó el me gusta): sin "+N"
                estado = [valor, 0, None, self.reloj]
            else:
                estado[3] = self.reloj
        self._cifras[clave] = estado
        while len(self._cifras) > MAX_CIFRAS_RECORDADAS:
            del self._cifras[next(iter(self._cifras))]  # la que hace más tiempo no se dibuja
        if self.reducir_movimiento or estado[2] is None:
            return None
        transcurrido = self.reloj - estado[2]
        if transcurrido >= DURACION_CIFRA:
            return None
        return estado[1], 1.0 - transcurrido / DURACION_CIFRA

    # ------------------------------------------------------------------
    # Cada cuadro
    # ------------------------------------------------------------------

    def actualizar(self, dt):
        """Avanza el reloj, la animación de abrir/cerrar (hacia 1 si está
        abierto, hacia 0 si no; con reducir_movimiento salta) y vence la
        ventana de la letra que se traga."""
        dt = _numero(dt)
        if dt <= 0:
            return
        self.reloj += dt
        if self.reducir_movimiento:
            self.apertura = 1.0 if self.abierto else 0.0
        elif self.abierto:
            self.apertura = min(1.0, self.apertura + dt / DURACION_APERTURA)
        else:
            self.apertura = max(0.0, self.apertura - dt / DURACION_APERTURA)
        if self._letra_a_tragar is not None and self.reloj > self._tragar_hasta:
            self._letra_a_tragar = None
