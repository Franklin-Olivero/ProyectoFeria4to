"""Feed en vivo de la app Civitas del celular (modo Online, lógica pura, sin pygame).

Qué muestra: una transmisión EN VIVO con su chat, publicaciones de Ciudad Nova
cuyos me gusta / compartidos / comentarios suben solos, el último comentario
de cada una y notificaciones que bajan desde arriba. Nada de eso viaja por la
red: todas las PCs ven LO MISMO porque el feed es una función determinista de
(semilla, segundos). El host sortea la semilla y lleva el reloj
(Online/chat_celular.CanalCelular); cada invitado los recibe al conectarse y
simula igual.

Cómo: simulación de eventos discretos. Todo lo que "pasa" en el feed es un
evento con su instante: la próxima publicación, el próximo comentario, el
próximo mensaje del chat en vivo, la próxima notificación, la próxima
transmisión y el próximo hito de cada publicación ("ya pasa los 10 mil me
gusta"). Los eventos pendientes esperan en una cola de prioridad: el MinHeap
del proyecto (src/structures/min_heap.py) con prioridad (instante, número de
evento). avanzar(t) saca siempre el más próximo mientras su instante sea <= t,
lo aplica y agenda los que provoca (el siguiente de su flujo, el hito de una
publicación nueva...). Por qué un montículo: los eventos se crean
desordenados (un hito puede caer dentro de 4 minutos y el próximo comentario
dentro de 3 s) y hay que aplicarlos estrictamente en orden de tiempo;
insertar y extraer el mínimo cuestan O(log n), con n = eventos pendientes
(unas decenas: uno por flujo más un hito por publicación), sin reordenar nada.

Determinismo: el azar es un random.Random(semilla) propio que SOLO se usa al
crear el feed y al procesar un evento, y los eventos se procesan siempre en el
mismo orden (el del montículo; el número de evento desempata dos del mismo
instante). Por eso llegar a t en un paso o en mil da exactamente el mismo
estado: el host avanza cuadro a cuadro, el invitado que entra tarde avanza de
golpe hasta el reloj del host, y los dos ven lo mismo.

Los números no son eventos: Publicacion.estadisticas(t) es una fórmula cerrada
de la edad (una curva 1 - e^(-edad/tau) que se frena sola, más un goteo
lineal), evaluada por "ticks" de 0.35-0.9 s para que salten como en vivo.
Es O(1), pura y nunca baja.

Contenido: Online/datos/celular.json (publicaciones, comentarios, chat en vivo,
transmisiones, notificaciones, hashtags...) más lo reutilizable de
content/campaign.json (ciudadanos, candidatos, cuentas, rumores, reacciones y
titulares). Si falta un archivo o está roto se usa CONTENIDO_RESPALDO.

    feed = FeedCelular(semilla)              -> 5 publicaciones viejas + una transmisión en curso
    feed.avanzar(segundos)                   -> [Notificacion nuevas] (procesa los eventos hasta ahí)
    feed.publicaciones / en_vivo / notificaciones / total_publicaciones
    publicacion.estadisticas(t)              -> (me gusta, compartidos, comentarios)
    cargar_contenido()                       -> dict del contenido (cacheado)
"""

import collections
import json
import math
import os
import random
import unicodedata
from dataclasses import dataclass, field

from src.structures.min_heap import MinHeap

CARPETA = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(CARPETA)
RUTA_CELULAR = os.path.join(CARPETA, "datos", "celular.json")  # relativa a este archivo, no al cwd
RUTA_CAMPANIA = os.path.join(RAIZ, "content", "campaign.json")

# --- Topes: cuánto se guarda (todo lo demás se olvida) ---
MAX_PUBLICACIONES = 25
MAX_COMENTARIOS_VISIBLES = 3
MAX_MENSAJES_VIVO = 6
MAX_NOTIFICACIONES = 5

# --- Ritmos (s): intervalo U(a, b) entre un evento y el siguiente de cada flujo ---
RITMO_PUBLICACION = (16.0, 34.0)
RITMO_COMENTARIO = (2.0, 5.0)
RITMO_MENSAJE_VIVO = (1.0, 2.6)
RITMO_NOTIFICACION = (6.0, 13.0)
RITMO_TRANSMISION = (240.0, 420.0)

# --- Qué hay en el feed ---
TIPOS = ("rumor", "verificada", "opinion", "oficial", "campana", "vida")
ETIQUETA_POR_TIPO = {"rumor": "Sin fuente", "verificada": "Verificado", "oficial": "Oficial", "campana": "Campaña",
                     "opinion": "", "vida": ""}
ETIQUETAS = ("Sin fuente", "Verificado", "Oficial", "Campaña", "")
ICONOS = ("corazon", "compartir", "comentario", "tendencia", "mencion", "vivo")
ICONO_VIVO = "vivo"  # solo cuando empieza una transmisión
ICONO_HITO = "corazon"  # "la publicación de X ya pasa los 10 mil me gusta"
ICONOS_PERIODICOS = ("corazon", "compartir", "comentario", "tendencia", "mencion")
# Ilustraciones de assets/story que pueden ir de foto (las demás son spoilers de la campaña).
FOTOS_PERMITIDAS = ("capitulo_colegio", "capitulo_hospital", "capitulo_medios", "ciudadanos_civitas", "elecciones",
                    "pantallas_nova", "portada")
FOTO_POR_ZONA = {"Colegio": "capitulo_colegio", "Hospital": "capitulo_hospital", "Empresa de Medios": "capitulo_medios"}
MARCADORES = ("nombre", "cuenta", "hashtag", "lema", "titulo", "cifra")  # {marcador} que se rellena en los textos

# Qué tan seguido sale cada cosa (pesos relativos).
PESOS_TIPO = {"rumor": 5, "verificada": 4, "opinion": 4, "oficial": 2, "campana": 3, "vida": 4}
PESOS_ICONO = {"corazon": 4, "compartir": 3, "comentario": 3, "tendencia": 3, "mencion": 2}
PESOS_COMENTARIO_POR_POSICION = (6, 5, 4, 3, 2, 2, 1, 1)  # la más nueva recibe más comentarios
PROBABILIDAD_COMENTARIO_DEL_TIPO = 0.65  # si no, un comentario general (sirve para cualquier publicación)

# --- Cómo suben los números (por tipo de publicación) ---
# (me gusta objetivo mínimo, máximo, tau mínima, máxima): los rumores y las campañas son lo más viral.
CRECIMIENTO_POR_TIPO = {
    "rumor": (30_000, 120_000, 90.0, 200.0),
    "campana": (30_000, 120_000, 90.0, 200.0),
    "oficial": (5_000, 25_000, 120.0, 300.0),
    "verificada": (3_000, 20_000, 150.0, 400.0),
    "opinion": (800, 8_000, 120.0, 400.0),
    "vida": (800, 6_000, 150.0, 400.0),
}
PROPORCION_COMPARTIDOS = (0.08, 0.30)  # objetivo de compartidos = me gusta x U(...)
PROPORCION_COMENTARIOS = (0.04, 0.15)
FACTOR_TAU_COMPARTIDOS = 1.6  # se comparte y se comenta más despacio de lo que se da me gusta
FACTOR_TAU_COMENTARIOS = 1.3
PERIODO_TICK = (0.35, 0.9)  # s entre saltos de los números
GOTEO_ME_GUSTA = (1.5, 3.0)  # por tick: hasta la publicación más tranquila suma varias unidades por salto
GOTEO_COMPARTIDOS = (0.2, 1.0)
GOTEO_COMENTARIOS = (0.2, 0.6)
BASE_ME_GUSTA = (0, 40)  # lo que ya tiene al aparecer
BASE_COMPARTIDOS = (0, 8)
BASE_COMENTARIOS = (1, 6)
UMBRAL_TENDENCIA_POR_MINUTO = 5000  # me gusta por minuto para el chip "Tendencia" (solo lo más viral)
HITOS_ME_GUSTA = ((10_000, "10 mil"), (100_000, "100 mil"))  # (umbral, cómo se escribe en la notificación)
HORIZONTE_HITOS = 600.0  # s: un hito más lejano no se agenda (para entonces la publicación ya salió del feed)
MARGEN_TICK = 0.001  # s: el hito se agenda justo después del tick para que el número ya haya cruzado

# --- Estado inicial y transmisiones ---
PUBLICACIONES_INICIALES = 5
EDAD_PUBLICACIONES_INICIALES = (30.0, 900.0)  # creadas entre -900 y -30 s: el feed nunca arranca vacío
DURACION_TRANSMISION_INICIAL = (20.0, 150.0)  # cuánto lleva la transmisión que ya está en curso
ESPECTADORES_BASE = (400, 2_500)
ESPECTADORES_OBJETIVO = (6_000, 30_000)
TAU_ESPECTADORES = (60.0, 180.0)
PERIODO_ESPECTADORES = (0.5, 1.1)
GOTEO_ESPECTADORES = (1.0, 6.0)
MAX_SEGUNDOS_FEED = 24 * 3600.0  # un reloj absurdo (basura de red) nunca congela el juego simulando días

# --- Al juntar el contenido ---
LEMA_GENERICO = "Por Ciudad Nova"  # si una plantilla de campaña pide {lema} y el autor no es candidato
TIPOS_PERSONA_POR_DEFECTO = ("opinion", "vida")  # un ciudadano con un rol sin mapear
# Cuentas de red_cuentas (campaign.json) según su papel en el capítulo 3; el "origen" no sale (spoiler).
TIPOS_POR_CLASE_DE_CUENTA = {"amplificador": ("rumor",), "error": ("opinion", "vida"), "victima": ("vida",)}
# Reacciones de campaign.json según el nivel de reputación de quien las recibe.
TIPO_POR_NIVEL_DE_REACCION = {"referente": "verificada", "confiable": "verificada", "neutral": "opinion",
                              "cuestionada": "rumor", "crisis": "rumor"}

# Eventos de la simulación (lo que guarda el montículo).
EV_PUBLICACION = "publicacion"
EV_COMENTARIO = "comentario"
EV_MENSAJE_VIVO = "mensaje_vivo"
EV_NOTIFICACION = "notificacion"
EV_TRANSMISION = "transmision"
EV_HITO = "hito"


def texto_hace(segundos):
    """Cuánto hace, como en las redes: "ahora" (< 60 s), "hace 3 min", "hace 2 h", "hace 1 d"."""
    if segundos < 60:
        return "ahora"
    if segundos < 3600:
        return f"hace {int(segundos // 60)} min"
    if segundos < 86_400:
        return f"hace {int(segundos // 3600)} h"
    return f"hace {int(segundos // 86_400)} d"


def usuario_de(nombre):
    """"Darío Mena" -> "@dario_mena" (sin tildes ni eñes, minúsculas, _ entre
    palabras). Una cuenta ("@...") se deja igual."""
    if nombre.startswith("@"):
        return nombre
    plano = unicodedata.normalize("NFKD", nombre).encode("ascii", "ignore").decode("ascii").lower()
    palabras = "".join(c if c.isalnum() else " " for c in plano).split()
    return "@" + "_".join(palabras) if palabras else "@vecino_nova"


def hashtag_de(lema):
    """"Puente Ciudadano" -> "#PuenteCiudadano"."""
    palabras = "".join(c if c.isalnum() else " " for c in lema).split()
    return "#" + "".join(p[:1].upper() + p[1:] for p in palabras) if palabras else ""


def rellenar(plantilla, **valores):
    """Cambia cada {clave} por su valor. Con replace y no con format: una llave
    suelta en el contenido no rompe nada."""
    for clave, valor in valores.items():
        plantilla = plantilla.replace("{" + clave + "}", valor)
    return plantilla


@dataclass
class Comentario:
    autor: str
    texto: str
    segundos: float


@dataclass
class Publicacion:
    """Una publicación del feed. Sus números NO se guardan: se calculan con
    estadisticas(t), una fórmula de la edad, así son iguales en todas las PCs
    y nadie tiene que actualizarlos cuadro a cuadro."""

    id: int  # creciente (el primero 1)
    autor: str  # nombre visible: "Ana Pardo", "Valeria Ortiz", "@DatosNovaHoy"
    usuario: str  # "@ana_pardo", "@DatosNovaHoy"
    tipo: str  # uno de TIPOS
    texto: str
    foto: str | None  # ilustración de assets/story (FOTOS_PERMITIDAS) o None
    etiqueta: str  # chip: "Sin fuente", "Verificado", "Oficial", "Campaña" o ""
    creada: float  # s del reloj del feed (negativa = ya existía al empezar)
    base: tuple  # (me gusta, compartidos, comentarios) al publicarse
    objetivo: tuple  # cuánto más puede sumar cada uno con la curva
    tau: tuple  # constante de tiempo (s) de cada curva
    periodo: float  # s entre ticks: los números saltan como en vivo
    goteo: tuple  # suma lineal por tick (nunca se quedan quietos del todo)
    comentarios: list = field(default_factory=list)  # [Comentario] los últimos 3, el más nuevo al final

    def edad(self, t):
        return max(0.0, t - self.creada)

    def tick(self, t):
        """Cuántos saltos de los números van desde que se publicó."""
        return math.floor(self.edad(t) / self.periodo)

    def valor_en_tick(self, indice, k):
        """Estadística `indice` (0 me gusta, 1 compartidos, 2 comentarios) en el
        tick k: base + objetivo * (1 - e^(-a/tau)) + k * goteo, con a = k * periodo.
        Cada término es no decreciente en k, así que la suma nunca baja."""
        curva = self.objetivo[indice] * (1.0 - math.exp(-(k * self.periodo) / self.tau[indice]))
        return self.base[indice] + math.floor(curva) + math.floor(k * self.goteo[indice])

    def estadisticas(self, t):
        """(me gusta, compartidos, comentarios) en el instante t: enteros, O(1),
        pura y no decreciente en t."""
        k = self.tick(t)
        return tuple(self.valor_en_tick(i, k) for i in range(3))

    def me_gusta_por_minuto(self, t):
        """Ritmo actual de me gusta: la derivada de la curva (objetivo/tau * e^(-edad/tau)) más el goteo."""
        curva = self.objetivo[0] / self.tau[0] * math.exp(-self.edad(t) / self.tau[0])
        return 60.0 * (curva + self.goteo[0] / self.periodo)

    def en_tendencia(self, t):
        return self.me_gusta_por_minuto(t) > UMBRAL_TENDENCIA_POR_MINUTO

    def hace(self, t):
        return texto_hace(self.edad(t))

    def primer_tick_con(self, indice, umbral, hasta):
        """Primer tick en que la estadística `indice` llega a `umbral`, o None si
        no llega antes del instante `hasta`. Como nunca baja, se busca con
        búsqueda binaria: O(log k) evaluaciones en vez de recorrer tick a tick."""
        alto = self.tick(hasta)
        if self.valor_en_tick(indice, alto) < umbral:
            return None
        bajo = -1  # invariante: valor(bajo) < umbral <= valor(alto) (valor(-1) se toma como -infinito)
        while alto - bajo > 1:
            medio = (bajo + alto) // 2
            if self.valor_en_tick(indice, medio) >= umbral:
                alto = medio
            else:
                bajo = medio
        return alto


@dataclass
class MensajeVivo:
    autor: str
    texto: str
    segundos: float


@dataclass
class Transmision:
    id: int
    titulo: str  # "Debate de candidatos a la Alcaldía"
    autor: str
    usuario: str
    foto: str | None
    inicio: float
    base_espectadores: int
    objetivo_espectadores: int
    tau: float
    periodo: float
    mensajes: collections.deque = field(default_factory=lambda: collections.deque(maxlen=MAX_MENSAJES_VIVO))
    goteo: float = 0.0  # espectadores por tick (como el goteo de las publicaciones)

    def duracion(self, t):
        return max(0.0, t - self.inicio)

    def espectadores(self, t):
        """Misma fórmula por ticks que las publicaciones: no decreciente dentro de la transmisión."""
        k = math.floor(self.duracion(t) / self.periodo)
        curva = self.objetivo_espectadores * (1.0 - math.exp(-(k * self.periodo) / self.tau))
        return self.base_espectadores + math.floor(curva) + math.floor(k * self.goteo)


@dataclass(frozen=True)
class Notificacion:
    id: int
    texto: str
    icono: str  # uno de ICONOS
    segundos: float


class _Mazo:
    """Baraja: saca sin repetir hasta agotar y entonces vuelve a barajar con el
    azar del feed (sigue siendo determinista). Así no sale la misma publicación
    ni el mismo comentario dos veces seguidas. sacar() es O(1) amortizado:
    barajar cuesta O(n) una vez cada n sacadas."""

    def __init__(self, elementos, azar):
        self._elementos = list(elementos)
        self._azar = azar
        self._pila = []
        self._ultimo = None

    def sacar(self):
        if not self._pila:
            self._pila = list(self._elementos)
            self._azar.shuffle(self._pila)
            if len(self._pila) > 1 and self._pila[-1] == self._ultimo:
                self._pila[0], self._pila[-1] = self._pila[-1], self._pila[0]  # tampoco se repite al rebarajar
        self._ultimo = self._pila.pop()
        return self._ultimo


class FeedCelular:
    """El feed de la app Civitas como simulación de eventos discretos (ver el
    docstring del módulo). Mismo (semilla, contenido) y mismo t => mismo estado.

    Complejidad: avanzar(t) cuesta O(e log n), con e = eventos que caen hasta t
    y n = eventos pendientes en el montículo; leer el estado es O(1) y cada
    número en pantalla es O(1) (estadisticas(t))."""

    def __init__(self, semilla, contenido=None):
        self.semilla = semilla
        self._azar = random.Random(semilla)
        self._contenido = contenido if contenido is not None else cargar_contenido()
        self._eventos = MinHeap()  # prioridad (instante, número de evento) -> (tipo de evento, dato)
        self._numero_evento = 0
        self._publicaciones = collections.deque()  # la más nueva a la izquierda
        self._por_id = {}  # id -> Publicacion que sigue en el feed
        self._mazos = {}
        self._plantillas = {tipo: [p for p in self._contenido.get("publicaciones", ()) if p.get("tipo") == tipo]
                            for tipo in TIPOS}
        self._manejadores = {
            EV_PUBLICACION: self._evento_publicacion,
            EV_COMENTARIO: self._evento_comentario,
            EV_MENSAJE_VIVO: self._evento_mensaje_vivo,
            EV_NOTIFICACION: self._evento_notificacion,
            EV_TRANSMISION: self._evento_transmision,
            EV_HITO: self._evento_hito,
        }
        self.t = 0.0
        self.en_vivo = None
        self.notificaciones = []  # las últimas MAX_NOTIFICACIONES, la más nueva al final
        self.total_publicaciones = 0
        self._ultima_notificacion = 0
        self._ultima_transmision = 0
        self._estado_inicial()

    @property
    def publicaciones(self):
        """Las publicaciones que siguen en el feed, la más NUEVA primero (copia)."""
        return list(self._publicaciones)

    # ------------------------------------------------------------------
    # El reloj
    # ------------------------------------------------------------------

    def avanzar(self, t):
        """Procesa EN ORDEN los eventos con instante <= t y devuelve las
        Notificacion nuevas. Si t <= self.t (o no es un número) no hace nada.

        El MinHeap no tiene "mirar el mínimo sin sacarlo": se saca y, si todavía
        no le toca, se devuelve con la MISMA prioridad (única), así el orden no
        cambia. Eso es un O(log n) extra por llamada, no por evento."""
        if isinstance(t, bool) or not isinstance(t, (int, float)) or not math.isfinite(t):
            return []
        t = min(float(t), MAX_SEGUNDOS_FEED)
        if t <= self.t:
            return []
        nuevas = []
        while not self._eventos.esta_vacio():
            prioridad, evento = self._eventos.extraer_minimo()
            instante = prioridad[0]
            if instante > t:
                self._eventos.insertar(prioridad, evento)
                break
            tipo, dato = evento
            notificacion = self._manejadores[tipo](instante, dato)
            if notificacion is not None:
                nuevas.append(notificacion)
        self.t = t
        return nuevas

    def _agendar(self, instante, tipo, dato=None):
        """Mete un evento al montículo, O(log n). La prioridad (instante, número)
        es única: el número desempata dos eventos del mismo instante por orden de
        creación, igual en todas las PCs."""
        self._numero_evento += 1
        self._eventos.insertar((instante, self._numero_evento), (tipo, dato))

    def _estado_inicial(self):
        """5 publicaciones "viejas" con algún comentario y una transmisión ya
        empezada con su chat, para que el feed nunca arranque vacío; luego, el
        primer evento de cada flujo."""
        edades = sorted((self._azar.uniform(*EDAD_PUBLICACIONES_INICIALES) for _ in range(PUBLICACIONES_INICIALES)),
                        reverse=True)
        for edad in edades:  # de la más vieja a la más nueva: los ids crecen con el tiempo
            publicacion = self._publicar(-edad)
            if publicacion is not None:
                cantidad = self._azar.randint(1, MAX_COMENTARIOS_VISIBLES)
                for instante in sorted(self._azar.uniform(-edad, 0.0) for _ in range(cantidad)):
                    self._comentar(publicacion, instante)
        self.en_vivo = self._nueva_transmision(-self._azar.uniform(*DURACION_TRANSMISION_INICIAL))
        instantes, instante = [], 0.0
        for _ in range(MAX_MENSAJES_VIVO):
            instante -= self._azar.uniform(*RITMO_MENSAJE_VIVO)
            if instante <= self.en_vivo.inicio:
                break
            instantes.append(instante)
        for instante in reversed(instantes):
            self._mensaje_vivo(instante)
        self._agendar(self._azar.uniform(*RITMO_PUBLICACION), EV_PUBLICACION)
        self._agendar(self._azar.uniform(*RITMO_COMENTARIO), EV_COMENTARIO)
        self._agendar(self._azar.uniform(*RITMO_MENSAJE_VIVO), EV_MENSAJE_VIVO)
        self._agendar(self._azar.uniform(*RITMO_NOTIFICACION), EV_NOTIFICACION)
        self._agendar(self.en_vivo.inicio + self._azar.uniform(*RITMO_TRANSMISION), EV_TRANSMISION)
        for publicacion in list(self._publicaciones):
            self._agendar_hito(publicacion, 0.0)

    # ------------------------------------------------------------------
    # Un manejador por tipo de evento: aplica el evento y agenda lo que sigue
    # ------------------------------------------------------------------

    def _evento_publicacion(self, instante, _dato):
        publicacion = self._publicar(instante)
        if publicacion is not None:
            self._agendar_hito(publicacion, instante)
        self._agendar(instante + self._azar.uniform(*RITMO_PUBLICACION), EV_PUBLICACION)
        return None

    def _evento_comentario(self, instante, _dato):
        recientes = [p for p, _ in zip(self._publicaciones, PESOS_COMENTARIO_POR_POSICION)]
        if recientes:
            pesos = PESOS_COMENTARIO_POR_POSICION[:len(recientes)]
            self._comentar(self._azar.choices(recientes, weights=pesos)[0], instante)
        self._agendar(instante + self._azar.uniform(*RITMO_COMENTARIO), EV_COMENTARIO)
        return None

    def _evento_mensaje_vivo(self, instante, _dato):
        self._mensaje_vivo(instante)
        self._agendar(instante + self._azar.uniform(*RITMO_MENSAJE_VIVO), EV_MENSAJE_VIVO)
        return None

    def _evento_notificacion(self, instante, _dato):
        por_icono = self._contenido.get("notificaciones_por_icono", {})
        iconos = [icono for icono in ICONOS_PERIODICOS if por_icono.get(icono)]
        notificacion = None
        if iconos:
            icono = self._azar.choices(iconos, weights=[PESOS_ICONO[i] for i in iconos])[0]
            plantilla = self._sacar(("notificaciones", icono), por_icono[icono])
            notificacion = self._notificar(self._rellenar_al_azar(plantilla), icono, instante)
        self._agendar(instante + self._azar.uniform(*RITMO_NOTIFICACION), EV_NOTIFICACION)
        return notificacion

    def _evento_transmision(self, instante, _dato):
        self.en_vivo = self._nueva_transmision(instante)
        self._agendar(instante + self._azar.uniform(*RITMO_TRANSMISION), EV_TRANSMISION)
        plantillas = self._contenido.get("notificaciones_por_icono", {}).get(ICONO_VIVO)
        if not plantillas:
            return None
        plantilla = self._sacar(("notificaciones", ICONO_VIVO), plantillas)
        texto = rellenar(plantilla, nombre=self.en_vivo.autor, titulo=self.en_vivo.titulo)
        return self._notificar(self._rellenar_al_azar(texto), ICONO_VIVO, instante)

    def _evento_hito(self, instante, dato):
        id_publicacion, indice = dato
        publicacion = self._por_id.get(id_publicacion)
        plantillas = self._contenido.get("hitos")
        if publicacion is None or not plantillas:
            return None  # ya salió del feed: el hito se descarta
        texto = rellenar(self._sacar("hitos", plantillas), nombre=publicacion.autor, cifra=HITOS_ME_GUSTA[indice][1])
        self._agendar_hito(publicacion, instante, desde=indice + 1)
        return self._notificar(self._rellenar_al_azar(texto), ICONO_HITO, instante)

    def _agendar_hito(self, publicacion, ahora, desde=0):
        """Agenda el próximo umbral de me gusta que la publicación cruzará dentro
        de HORIZONTE_HITOS (búsqueda binaria sobre sus ticks). Los que ya pasó se
        saltan; si uno no llega a tiempo, los mayores tampoco."""
        for indice in range(desde, len(HITOS_ME_GUSTA)):
            umbral = HITOS_ME_GUSTA[indice][0]
            if publicacion.estadisticas(ahora)[0] >= umbral:
                continue
            tick = publicacion.primer_tick_con(0, umbral, ahora + HORIZONTE_HITOS)
            if tick is not None:
                self._agendar(publicacion.creada + tick * publicacion.periodo + MARGEN_TICK, EV_HITO,
                              (publicacion.id, indice))
            return

    # ------------------------------------------------------------------
    # Crear cosas (todas usan el azar en un orden fijo)
    # ------------------------------------------------------------------

    def _publicar(self, instante):
        tipos = [tipo for tipo in TIPOS if self._plantillas[tipo]]
        if not tipos:
            return None
        tipo = self._azar.choices(tipos, weights=[PESOS_TIPO[t] for t in tipos])[0]
        plantilla = self._sacar(("publicaciones", tipo), self._plantillas[tipo])
        if plantilla.get("usuario"):
            autor, usuario = plantilla.get("autor") or plantilla["usuario"], plantilla["usuario"]
        else:
            autores = self._contenido.get("autores", {}).get(tipo)
            autor, usuario = self._sacar(("autores", tipo), autores) if autores else ("Civitas", "@CivitasOficial")
        minimo, maximo, tau_minima, tau_maxima = CRECIMIENTO_POR_TIPO[tipo]
        me_gusta = self._azar.randint(minimo, maximo)
        tau = self._azar.uniform(tau_minima, tau_maxima)
        objetivo = (me_gusta, round(me_gusta * self._azar.uniform(*PROPORCION_COMPARTIDOS)),
                    round(me_gusta * self._azar.uniform(*PROPORCION_COMENTARIOS)))
        base = (self._azar.randint(*BASE_ME_GUSTA), self._azar.randint(*BASE_COMPARTIDOS),
                self._azar.randint(*BASE_COMENTARIOS))
        goteo = (self._azar.uniform(*GOTEO_ME_GUSTA), self._azar.uniform(*GOTEO_COMPARTIDOS),
                 self._azar.uniform(*GOTEO_COMENTARIOS))
        periodo = self._azar.uniform(*PERIODO_TICK)
        lema = self._contenido.get("lemas", {}).get(autor, LEMA_GENERICO)
        texto = self._rellenar_al_azar(rellenar(plantilla["texto"], lema=lema))
        self.total_publicaciones += 1
        publicacion = Publicacion(self.total_publicaciones, autor, usuario, tipo, texto, plantilla.get("foto"),
                                  plantilla.get("etiqueta", ETIQUETA_POR_TIPO[tipo]), instante, base, objetivo,
                                  (tau, tau * FACTOR_TAU_COMPARTIDOS, tau * FACTOR_TAU_COMENTARIOS), periodo, goteo)
        if len(self._publicaciones) >= MAX_PUBLICACIONES:
            vieja = self._publicaciones.pop()  # la más vieja sale del feed (y sus hitos pendientes se descartan)
            del self._por_id[vieja.id]
        self._publicaciones.appendleft(publicacion)
        self._por_id[publicacion.id] = publicacion
        return publicacion

    def _comentar(self, publicacion, instante):
        personas = self._contenido.get("personas")
        if not personas:
            return
        autor = self._sacar("personas", personas)
        if autor == publicacion.autor:
            autor = self._sacar("personas", personas)  # nadie se comenta a sí mismo (el mazo no repite)
        del_tipo = self._contenido.get("comentarios_por_tipo", {}).get(publicacion.tipo)
        generales = self._contenido.get("comentarios")
        if del_tipo and (not generales or self._azar.random() < PROBABILIDAD_COMENTARIO_DEL_TIPO):
            texto = self._sacar(("comentarios", publicacion.tipo), del_tipo)
        elif generales:
            texto = self._sacar("comentarios", generales)
        else:
            return
        publicacion.comentarios.append(Comentario(autor, texto, instante))
        del publicacion.comentarios[:-MAX_COMENTARIOS_VISIBLES]

    def _mensaje_vivo(self, instante):
        apodos, textos = self._contenido.get("apodos"), self._contenido.get("mensajes_vivo")
        if apodos and textos and self.en_vivo is not None:
            self.en_vivo.mensajes.append(MensajeVivo(self._sacar("apodos", apodos),
                                                     self._sacar("mensajes_vivo", textos), instante))

    def _nueva_transmision(self, inicio):
        transmisiones = self._contenido.get("transmisiones")
        datos = self._sacar("transmisiones", transmisiones) if transmisiones else {}
        autor = datos.get("autor", "@CivitasOficial")
        self._ultima_transmision += 1
        return Transmision(self._ultima_transmision, datos.get("titulo", "Civitas en vivo"), autor,
                           datos.get("usuario") or usuario_de(autor), datos.get("foto"), inicio,
                           self._azar.randint(*ESPECTADORES_BASE), self._azar.randint(*ESPECTADORES_OBJETIVO),
                           self._azar.uniform(*TAU_ESPECTADORES), self._azar.uniform(*PERIODO_ESPECTADORES),
                           goteo=self._azar.uniform(*GOTEO_ESPECTADORES))

    def _notificar(self, texto, icono, instante):
        self._ultima_notificacion += 1
        notificacion = Notificacion(self._ultima_notificacion, texto, icono, instante)
        self.notificaciones.append(notificacion)
        del self.notificaciones[:-MAX_NOTIFICACIONES]
        return notificacion

    def _rellenar_al_azar(self, plantilla):
        """Rellena {nombre} {cuenta} {hashtag} con el mazo de cada uno; solo saca
        de los mazos que la plantilla usa."""
        for marcador, clave in (("nombre", "personas"), ("cuenta", "cuentas"), ("hashtag", "hashtags")):
            opciones = self._contenido.get(clave)
            if "{" + marcador + "}" in plantilla and opciones:
                plantilla = rellenar(plantilla, **{marcador: self._sacar(clave, opciones)})
        return plantilla

    def _sacar(self, clave, elementos):
        """Saca del mazo `clave` (lo crea la primera vez; crearlo no usa el azar)."""
        mazo = self._mazos.get(clave)
        if mazo is None:
            mazo = self._mazos[clave] = _Mazo(elementos, self._azar)
        return mazo.sacar()


# ----------------------------------------------------------------------
# Contenido
# ----------------------------------------------------------------------

# Mínimo pero completo (mismo formato que Online/datos/celular.json): con esto
# el feed funciona aunque falten los dos archivos.
CONTENIDO_RESPALDO = {
    "cuentas": [
        {"usuario": "@CivitasOficial", "tipos": ["oficial", "verificada"]},
        {"usuario": "@NovaNoticias", "tipos": ["verificada", "vida"]},
        {"usuario": "@CadenaNovaYa", "tipos": ["rumor"]},
        {"usuario": "@CampanaNovaUnida", "tipos": ["campana"]},
    ],
    "personas": [
        {"nombre": "Ana Pardo", "tipos": ["opinion", "vida"]},
        {"nombre": "Beto Ruiz", "tipos": ["vida", "opinion"]},
        {"nombre": "Camila Osorio", "tipos": ["opinion"]},
    ],
    "apodos": ["vecina_del_sur", "lector_nova"],
    "publicaciones": [
        {"tipo": "rumor", "texto": "Me llegó por un grupo: mañana no hay buses en toda Ciudad Nova. Pásenlo por si acaso.",
         "foto": None, "etiqueta": "Sin fuente"},
        {"tipo": "verificada", "texto": "Antes de compartir: ¿quién lo publica?, ¿de cuándo es?, ¿otro medio lo confirma?",
         "foto": None, "etiqueta": "Verificado"},
        {"tipo": "opinion", "texto": "Hoy casi reenvío una noticia de hace tres años. Primero la fecha, después el resto.",
         "foto": None, "etiqueta": ""},
        {"tipo": "oficial", "texto": "Este domingo hay elecciones. Consulta tu puesto de votación solo en canales oficiales.",
         "foto": "elecciones", "etiqueta": "Oficial"},
        {"tipo": "campana", "texto": "Te esperamos en el debate del jueves en la Plaza. Trae tus preguntas.",
         "foto": None, "etiqueta": "Campaña"},
        {"tipo": "vida", "texto": "Atardecer naranja sobre la Plaza. Ciudad Nova a veces se pone bonita sin avisar.",
         "foto": None, "etiqueta": ""},
    ],
    "comentarios": ["Gracias por compartir.", "¿De cuándo es esto?", "Primero leo completo, después opino.",
                    "En mi barrio también se habla de esto."],
    "mensajes_vivo": ["¡Hola desde el sur!", "Se escucha perfecto.", "Excelente pregunta.", "Gracias por transmitir."],
    "transmisiones": [{"titulo": "Debate de candidatos a la Alcaldía", "foto": "elecciones", "autor": "@NovaNoticias"}],
    "notificaciones": [
        {"icono": "corazon", "texto": "{nombre} le dio me gusta a una publicación"},
        {"icono": "compartir", "texto": "{nombre} compartió una publicación de {cuenta}"},
        {"icono": "comentario", "texto": "{nombre} comentó una publicación"},
        {"icono": "tendencia", "texto": "Tendencia en Ciudad Nova: {hashtag}"},
        {"icono": "mencion", "texto": "{nombre} te mencionó en un comentario"},
        {"icono": "vivo", "texto": "{nombre} está en vivo: {titulo}"},
    ],
    "hitos": ["La publicación de {nombre} ya pasa los {cifra} me gusta"],
    "hashtags": ["#VerificaAntesDeCompartir", "#CiudadNova"],
    "respuestas_rapidas": ["¡Hola!", "¡Vamos!", "Ayuda", "Cuidado"],
}

_cache = {}  # "por_defecto" -> contenido de los archivos del repo (se leen una sola vez)


def cargar_contenido(ruta=None, ruta_campania=None):
    """Contenido del feed: Online/datos/celular.json (`ruta`; por defecto
    relativa a ESTE archivo) más lo reutilizable de content/campaign.json.
    Tolerante: lo que falte o esté roto sale de CONTENIDO_RESPALDO. Sin rutas
    se lee una sola vez (el feed se recrea cada vez que un invitado sincroniza
    y no hay que tocar el disco en medio de la partida). No modificar el dict
    devuelto: se comparte.

    Devuelve un dict con: "autores" {tipo: [(nombre, usuario)]}, "publicaciones"
    [dict tipo/texto/foto/etiqueta (+ autor/usuario si es fijo)], "comentarios"
    [str] (sirven para cualquier publicación), "comentarios_por_tipo" {tipo: [str]},
    "mensajes_vivo" [str], "transmisiones" [dict titulo/foto/autor/usuario],
    "notificaciones" [plantilla], "notificaciones_por_icono" {icono: [plantilla]},
    "hitos" [plantilla], "hashtags" [str], "respuestas_rapidas" [str],
    "personas" [nombre], "cuentas" [@usuario], "apodos" [str] y "lemas" {nombre: lema}."""
    por_defecto = ruta is None and ruta_campania is None
    if por_defecto and "por_defecto" in _cache:
        return _cache["por_defecto"]
    propio = _leer_json(ruta or RUTA_CELULAR)
    campania = _leer_json(ruta_campania or RUTA_CAMPANIA)
    contenido = _armar_contenido(propio if isinstance(propio, dict) else {},
                                 campania if isinstance(campania, dict) else {})
    if por_defecto:
        _cache["por_defecto"] = contenido
    return contenido


def _leer_json(ruta):
    try:
        with open(ruta, encoding="utf-8") as archivo:
            return json.load(archivo)
    except (OSError, ValueError):
        return None


def _armar_contenido(propio, campania):
    """Junta las secciones (cada una cae al respaldo si falta o está rota),
    suma lo reutilizable de la campaña y rellena con el respaldo lo que le
    falte a un tipo o a un ícono, para que el feed siempre tenga de todo."""
    respaldo = CONTENIDO_RESPALDO

    def seccion(clave, leer):
        return leer(propio.get(clave)) or leer(respaldo.get(clave))

    junta = _Junta()
    for usuario, tipos in seccion("cuentas", _leer_cuentas):
        junta.sumar_cuenta(usuario, tipos)
    for nombre, tipos in seccion("personas", _leer_personas):
        junta.sumar_persona(nombre, usuario_de(nombre), tipos)
    junta.apodos.extend(seccion("apodos", _leer_textos))
    junta.comentarios.extend(seccion("comentarios", _leer_textos))
    for tipo, textos in _leer_comentarios_por_tipo(propio.get("comentarios_por_tipo")).items():
        junta.comentarios_por_tipo[tipo].extend(textos)
    junta.notificaciones.extend(seccion("notificaciones", _leer_notificaciones))
    junta.hashtags.extend(seccion("hashtags", _leer_hashtags))
    plantillas = seccion("publicaciones", _leer_publicaciones)
    transmisiones = seccion("transmisiones", _leer_transmisiones)

    _sumar_campania(junta, campania, _leer_tipos_por_rol(propio.get("tipos_por_rol")))

    for nombre, tipos in _leer_personas(respaldo["personas"]) + _leer_cuentas(respaldo["cuentas"]):
        for tipo in tipos:
            if not junta.autores[tipo]:  # un tipo sin nadie que publique toma un autor del respaldo
                junta.sumar_autor(tipo, nombre, usuario_de(nombre))
    tipos_con_plantilla = {p["tipo"] for p in plantillas + junta.publicaciones}
    plantillas += [p for p in _leer_publicaciones(respaldo["publicaciones"]) if p["tipo"] not in tipos_con_plantilla]
    iconos_con_plantilla = {icono for icono, _ in junta.notificaciones}
    junta.notificaciones += [(i, t) for i, t in _leer_notificaciones(respaldo["notificaciones"])
                             if i not in iconos_con_plantilla]

    for plantilla in plantillas:  # autor fijo de celular.json: se resuelve su @usuario
        if plantilla.get("autor"):
            plantilla["usuario"] = junta.usuario_de_autor(plantilla["autor"])
    for transmision in transmisiones:
        transmision["usuario"] = junta.usuario_de_autor(transmision["autor"])
    por_icono = {icono: [] for icono in ICONOS}
    for icono, texto in _sin_repetir(junta.notificaciones):
        por_icono[icono].append(texto)
    personas = _sin_repetir(junta.personas)
    return {
        "autores": {tipo: _sin_repetir(lista) for tipo, lista in junta.autores.items()},
        "publicaciones": _sin_repetir_por_texto(plantillas + junta.publicaciones),
        "comentarios": _sin_repetir(junta.comentarios),
        "comentarios_por_tipo": {tipo: _sin_repetir(lista) for tipo, lista in junta.comentarios_por_tipo.items()},
        "mensajes_vivo": seccion("mensajes_vivo", _leer_textos),
        "transmisiones": transmisiones,
        "notificaciones": [texto for icono in ICONOS for texto in por_icono[icono]],
        "notificaciones_por_icono": por_icono,
        "hitos": seccion("hitos", _leer_textos),
        "hashtags": _sin_repetir(junta.hashtags),
        "respuestas_rapidas": seccion("respuestas_rapidas", _leer_textos),
        "personas": personas,
        "cuentas": _sin_repetir(junta.cuentas),
        "apodos": _sin_repetir(junta.apodos + [junta.usuarios[nombre].lstrip("@") for nombre in personas]),
        "lemas": dict(junta.lemas),
    }


class _Junta:
    """Acumula el contenido mientras se arma (autores por tipo, personas que
    comentan, cuentas para las menciones...)."""

    def __init__(self):
        self.autores = {tipo: [] for tipo in TIPOS}
        self.personas = []  # nombres que comentan y rellenan {nombre}
        self.usuarios = {}  # nombre visible -> @usuario
        self.nombres = {}  # @usuario -> nombre visible
        self.cuentas = []  # @cuentas confiables para {cuenta}
        self.apodos, self.comentarios, self.notificaciones, self.hashtags = [], [], [], []
        self.comentarios_por_tipo = {tipo: [] for tipo in TIPOS}
        self.publicaciones = []  # las reutilizadas de la campaña (autor fijo)
        self.lemas = {}

    def sumar_autor(self, tipo, nombre, usuario):
        self.autores[tipo].append((nombre, usuario))
        self.usuarios.setdefault(nombre, usuario)
        self.nombres.setdefault(usuario, nombre)

    def sumar_cuenta(self, usuario, tipos):
        for tipo in tipos:
            self.sumar_autor(tipo, usuario, usuario)
        if "rumor" not in tipos:
            self.cuentas.append(usuario)

    def sumar_persona(self, nombre, usuario, tipos):
        self.personas.append(nombre)
        self.usuarios.setdefault(nombre, usuario)
        self.nombres.setdefault(usuario, nombre)
        for tipo in tipos:
            self.sumar_autor(tipo, nombre, usuario)

    def usuario_de_autor(self, autor):
        return self.usuarios.get(autor) or usuario_de(autor)


def _sumar_campania(junta, campania, tipos_por_rol):
    """Lo reutilizable de content/campaign.json. Cada parte se lee con cuidado
    (todo valor pasa por _texto/_dict/_lista): si algo no tiene la forma
    esperada se ignora y el resto sigue."""
    red_cuentas = [c for c in map(_dict, _lista(_dict(campania.get("red_cuentas")).get("cuentas"))) if c]
    cuenta_por_id = {_texto(c.get("id")): _texto(c.get("nombre")) for c in red_cuentas
                     if _texto(c.get("id")) and len(_texto(c.get("nombre"))) > 1
                     and _texto(c.get("nombre")).startswith("@")}  # "nova_root" no tiene @: no sale (spoiler)
    for ciudadano in map(_dict, _lista(_dict(campania.get("red_social")).get("ciudadanos"))):
        nombre = _texto(ciudadano.get("nombre"))
        if nombre:  # quien tiene cuenta en el capítulo 3 publica con ella (Elena Vidal -> @ElenaVidalRN)
            usuario = cuenta_por_id.pop(_texto(ciudadano.get("id")), "") or usuario_de(nombre)
            tipos = tipos_por_rol.get(_texto(ciudadano.get("rol")), TIPOS_PERSONA_POR_DEFECTO)
            junta.sumar_persona(nombre, usuario, tipos)
    for candidato in map(_dict, _lista(campania.get("candidatos"))):
        nombre, lema = _texto(candidato.get("nombre")), _texto(candidato.get("lema"))
        if nombre:
            junta.sumar_autor("campana", nombre, usuario_de(nombre))
            if hashtag_de(lema):
                junta.lemas[nombre] = lema
                junta.hashtags.append(hashtag_de(lema))
    for cuenta in red_cuentas:  # las que no son de ningún ciudadano, según su papel en el capítulo 3
        usuario = cuenta_por_id.get(_texto(cuenta.get("id")))
        if usuario:
            for tipo in TIPOS_POR_CLASE_DE_CUENTA.get(_texto(cuenta.get("tipo")), ()):
                junta.sumar_autor(tipo, usuario, usuario)
    posts = [(p, _texto(p.get("zona")), "rumor") for p in map(_dict, _lista(campania.get("sabotajes")))]
    for zona, escenario in _dict(campania.get("escenarios")).items():
        escenario = _dict(escenario)  # una publicación verdadera (el Hospital) no se disfraza de rumor
        tipo = "verificada" if escenario.get("veredicto") == "cierto" else "rumor"
        posts.append((_dict(escenario.get("post")), zona, tipo))
    for post, zona, tipo in posts:
        usuario, texto = _texto(post.get("usuario")), _texto(post.get("texto"))
        if len(usuario) > 1 and usuario.startswith("@") and texto and "{" not in texto:
            if tipo == "rumor":
                junta.sumar_autor("rumor", usuario, usuario)
            junta.publicaciones.append({"tipo": tipo, "texto": texto, "foto": FOTO_POR_ZONA.get(zona),
                                        "etiqueta": ETIQUETA_POR_TIPO[tipo],
                                        "autor": junta.nombres.get(usuario, usuario), "usuario": usuario})
    for nivel, reacciones in _dict(campania.get("reacciones")).items():
        tipo = TIPO_POR_NIVEL_DE_REACCION.get(nivel, "opinion")
        for reaccion in _lista(reacciones):
            texto = _texto(reaccion).removeprefix("{nombre}: ")  # "{nombre}: Te seguía..." -> "Te seguía..."
            if texto and "{" not in texto:
                junta.comentarios_por_tipo[tipo].append(texto)
    for evento in map(_dict, _lista(campania.get("eventos"))):
        titulo = _texto(evento.get("titulo"))
        if titulo and "{" not in titulo:
            junta.notificaciones.append(("tendencia", titulo))  # titulares como notificaciones de noticia


# --- Lectores tolerantes: devuelven [] / {} si el valor no tiene la forma esperada ---

def _texto(valor):
    """El texto en un solo renglón con espacios simples, o "" si no es texto."""
    return " ".join(valor.split()) if isinstance(valor, str) else ""


def _lista(valor):
    return valor if isinstance(valor, list) else []


def _dict(valor):
    return valor if isinstance(valor, dict) else {}


def _sin_repetir(elementos):
    vistos, salida = set(), []
    for elemento in elementos:
        if elemento not in vistos:
            vistos.add(elemento)
            salida.append(elemento)
    return salida


def _sin_repetir_por_texto(plantillas):
    vistos, salida = set(), []
    for plantilla in plantillas:
        if plantilla["texto"] not in vistos:
            vistos.add(plantilla["texto"])
            salida.append(plantilla)
    return salida


def _leer_textos(valor):
    return _sin_repetir(t for t in map(_texto, _lista(valor)) if t)


def _leer_tipos(valor):
    return tuple(_sin_repetir(t for t in _lista(valor) if t in TIPOS))


def _leer_cuentas(valor):
    return [(_texto(c.get("usuario")), _leer_tipos(c.get("tipos"))) for c in _lista(valor)
            if isinstance(c, dict) and len(_texto(c.get("usuario"))) > 1 and _texto(c.get("usuario")).startswith("@")]


def _leer_personas(valor):
    return [(_texto(p.get("nombre")), _leer_tipos(p.get("tipos"))) for p in _lista(valor)
            if isinstance(p, dict) and _texto(p.get("nombre")) and not _texto(p.get("nombre")).startswith("@")]


def _leer_tipos_por_rol(valor):
    return {_texto(rol): _leer_tipos(tipos) for rol, tipos in _dict(valor).items() if _texto(rol)}


def _leer_comentarios_por_tipo(valor):
    return {tipo: _leer_textos(textos) for tipo, textos in _dict(valor).items() if tipo in TIPOS}


def _leer_hashtags(valor):
    return [t for t in _leer_textos(valor) if t.startswith("#") and len(t) > 1 and " " not in t]


def _foto(valor):
    return valor if valor in FOTOS_PERMITIDAS else None


def _leer_publicaciones(valor):
    plantillas = []
    for p in _lista(valor):
        if isinstance(p, dict) and p.get("tipo") in TIPOS and _texto(p.get("texto")):
            etiqueta = p.get("etiqueta") if p.get("etiqueta") in ETIQUETAS else ETIQUETA_POR_TIPO[p["tipo"]]
            plantilla = {"tipo": p["tipo"], "texto": _texto(p["texto"]), "foto": _foto(p.get("foto")),
                         "etiqueta": etiqueta}
            if _texto(p.get("autor")):
                plantilla["autor"] = _texto(p["autor"])
            plantillas.append(plantilla)
    return plantillas


def _leer_transmisiones(valor):
    return [{"titulo": _texto(t.get("titulo")), "foto": _foto(t.get("foto")),
             "autor": _texto(t.get("autor")) or "@CivitasOficial"}
            for t in _lista(valor) if isinstance(t, dict) and _texto(t.get("titulo"))]


def _leer_notificaciones(valor):
    return [(n["icono"], _texto(n.get("texto"))) for n in _lista(valor)
            if isinstance(n, dict) and n.get("icono") in ICONOS and _texto(n.get("texto"))]
