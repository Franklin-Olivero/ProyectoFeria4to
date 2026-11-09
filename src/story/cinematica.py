"""Cinemáticas del modo historia (lógica pura, sin Pygame).

Una cinemática es una secuencia de `Toma`s: la intro del juego, la tarjeta
de cada capítulo, la entrada al jefe, la crisis de reputación, la redención,
la caída del Servidor Central y los finales. Cada toma dice qué ilustración
o video se ve (`fondo`, `video`), qué efecto la anima (`efecto`) y qué texto
se escribe debajo.

Ritmo de lectura, la regla más importante:
    - Una toma con texto NUNCA se va mientras se escribe. El texto aparece
      letra a letra; Enter lo revela completo y otro Enter pasa a la siguiente.
    - En modo MANUAL (predeterminado) el texto espera al jugador sin límite;
      las animaciones ambientales siguen mientras tanto.
    - En modo AUTOMATICO avanza sola tras `tiempo_lectura`: 150 palabras por
      minuto + 2 s, nunca menos de 7 s si hay diálogo, y solo cuando el texto
      terminó de escribirse.
    - Una toma sin texto (título, video solo) usa su `duracion`; duración 0
      significa que espera Enter en cualquier modo (COMENZAR MISIÓN).
    - Esc salta la cinemática, salvo la última toma si espera Enter.
    - Un texto largo se parte en varias tomas (paginar_texto): nunca se recorta.

Nada aquí depende de archivos: si falta el video se usa la ilustración, y si
falta la ilustración el dibujo (src/ui/cinematica_render.py) usa su fallback.
"""

from dataclasses import dataclass, field, replace

from src.core.assets import (
    DURACION_TARJETA_CAPITULO,
    FONDO_CRISIS,
    FONDO_CONFIANZA_PERDIDA,
    FONDO_REDENCION,
    VIDEO_CRISIS,
    VIDEO_JEFE,
    VIDEO_REDENCION,
    FONDO_CIUDADANOS,
    FONDO_PANTALLAS_NOVA,
    FONDO_POR_FINAL,
    FONDO_POR_ZONA,
    FONDO_PROLOGO,
    FONDO_SERVIDOR_CAIDO,
)
from src.story.dialogo import HABLANTE_JUGADOR, RETRATO_JUGADOR, _cumple, paginar_texto

# Efectos que conoce el render.
EFECTO_PANEO = "paneo"
EFECTO_GLITCH = "glitch"
EFECTO_NOTIFICACIONES = "notificaciones"
EFECTO_CAOS = "caos"
EFECTO_RETRATO = "retrato"
EFECTO_TITULO = "titulo"
EFECTO_TARJETA = "tarjeta"
EFECTO_OBJETIVOS = "objetivos"
EFECTO_TITULARES = "titulares"  # publicaciones de Civitas contra el protagonista
EFECTOS = (EFECTO_PANEO, EFECTO_GLITCH, EFECTO_NOTIFICACIONES, EFECTO_CAOS, EFECTO_RETRATO,
           EFECTO_TITULO, EFECTO_TARJETA, EFECTO_OBJETIVOS, EFECTO_TITULARES)

HABLANTE_NARRADOR = "NARRADOR"
HABLANTE_NOVA = "NOVA_404"
HABLANTE_MENSAJE = "MENSAJE"

ESPERA_ENTER = 0.0  # duración de una toma que no avanza sola

MODO_MANUAL = "manual"
MODO_AUTOMATICO = "automatico"
VELOCIDAD_TEXTO_NORMAL = 28.0  # caracteres por segundo
PALABRAS_POR_SEGUNDO = 150 / 60
PAUSA_LECTURA = 2.0  # s extra tras leer
LECTURA_MINIMA_DIALOGO = 7.0  # s
RETARDO_TEXTO = 0.35  # s antes de empezar a escribir
MAX_CARACTERES_SUBTITULO = 240  # caben en la caja de subtítulo (ver tests)


def tiempo_lectura(texto, minimo=LECTURA_MINIMA_DIALOGO):
    """Segundos para leer `texto` sin prisa: 150 palabras/min + 2 s, con un
    mínimo de 7 s en una toma con diálogo. Puro, O(n)."""
    if not texto:
        return 0.0
    return max(minimo, len(texto.split()) / PALABRAS_POR_SEGUNDO + PAUSA_LECTURA)


@dataclass
class Toma:
    id: str
    duracion: float = 5.0
    fondo: str | None = None
    efecto: str = EFECTO_PANEO
    texto: str = ""
    hablante: str | None = None
    retrato: str | None = None
    titulo: str = ""
    subtitulo: str = ""
    superior: str = ""  # rótulo pequeño sobre el título ("CAPÍTULO 1")
    objetivos: list = field(default_factory=list)
    sonido: str | None = None  # efecto que suena al empezar la toma
    video: str | None = None  # id de assets/story/video/<id>/ (fallback: `fondo`)
    lineas: list = field(default_factory=list)  # textos extra del efecto (titulares, contexto)

    @property
    def espera(self):
        return self.duracion <= ESPERA_ENTER


def paginar_tomas(tomas):
    """Una toma con texto muy largo se vuelve varias: el texto nunca se recorta."""
    resultado = []
    for toma in tomas:
        paginas = paginar_texto(toma.texto, MAX_CARACTERES_SUBTITULO) if toma.texto else [toma.texto]
        for numero, pagina in enumerate(paginas):
            resultado.append(replace(toma, texto=pagina, id=toma.id if numero == 0 else f"{toma.id}_{numero + 1}",
                                     sonido=toma.sonido if numero == 0 else None))
    return resultado


class Cinematica:
    def __init__(self, tomas, titulo="", saltable=True, modo=MODO_MANUAL, velocidad=VELOCIDAD_TEXTO_NORMAL):
        self.tomas = paginar_tomas(tomas)
        self.titulo = titulo
        self.saltable = saltable
        self.modo = modo
        self.velocidad = velocidad
        self.indice = 0
        self.tiempo = 0.0  # s dentro de la toma actual
        self.tiempo_texto = 0.0  # s de escritura (Enter lo adelanta)
        self.sonido_pendiente = self.tomas[0].sonido if self.tomas else None

    def configurar_lectura(self, velocidad=None, modo=None):
        """Modo y velocidad elegidos en Ajustes (los pone Main.py)."""
        if velocidad is not None:
            self.velocidad = velocidad
        if modo is not None:
            self.modo = modo

    # ------------------------------------------------------------------
    @property
    def terminada(self):
        return self.indice >= len(self.tomas)

    @property
    def actual(self):
        return None if self.terminada else self.tomas[self.indice]

    @property
    def caracteres_visibles(self):
        toma = self.actual
        if toma is None:
            return 0
        return min(len(toma.texto), int(max(0.0, self.tiempo_texto - RETARDO_TEXTO) * self.velocidad))

    @property
    def texto_completo(self):
        toma = self.actual
        return toma is None or self.caracteres_visibles >= len(toma.texto)

    def duracion_efectiva(self, toma=None):
        """Segundos que dura la toma por sí sola, o None si espera a Enter."""
        toma = toma if toma is not None else self.actual
        if toma is None or toma.espera:
            return None
        if toma.texto:
            if self.modo == MODO_MANUAL:
                return None
            return max(toma.duracion, tiempo_lectura(toma.texto), RETARDO_TEXTO + len(toma.texto) / self.velocidad)
        return toma.duracion

    @property
    def esperando_enter(self):
        """True si el jugador es quien debe continuar (para el indicador)."""
        return self.duracion_efectiva() is None and self.texto_completo

    @property
    def fraccion(self):
        """0-1 del avance de la toma actual (0 si espera a Enter)."""
        duracion = self.duracion_efectiva()
        if not duracion:
            return 0.0
        return max(0.0, min(1.0, self.tiempo / duracion))

    @property
    def progreso(self):
        return min(self.indice + 1, len(self.tomas)), len(self.tomas)

    def tomar_sonido(self):
        """Nombre del efecto que debe sonar ahora (una sola vez), o None."""
        sonido, self.sonido_pendiente = self.sonido_pendiente, None
        return sonido

    # ------------------------------------------------------------------
    def actualizar(self, dt):
        """Avanza el reloj; solo pasa de toma si no espera a Enter y el
        texto ya terminó de escribirse. O(1)."""
        if self.terminada:
            return
        self.tiempo += dt
        self.tiempo_texto += dt
        duracion = self.duracion_efectiva()
        if duracion is not None and self.tiempo >= duracion and self.texto_completo:
            self._siguiente()

    def avanzar(self):
        """Enter: revela el texto si aún se escribe; si ya está completo,
        pasa a la siguiente toma (la de objetivos cierra la cinemática)."""
        if self.terminada:
            return
        if not self.texto_completo:
            toma = self.actual
            self.tiempo_texto = RETARDO_TEXTO + len(toma.texto) / self.velocidad + 0.01
            return
        self._siguiente()

    def saltar(self):
        """Esc: salta al final. Si la última toma espera Enter (objetivos),
        se queda en ella para que el jugador lea qué debe hacer."""
        if self.terminada or not self.saltable:
            return
        ultima = len(self.tomas) - 1
        if self.tomas[ultima].espera and self.indice < ultima:
            self.indice = ultima
            self.tiempo = 0.0
            self.tiempo_texto = 0.0
            self.sonido_pendiente = self.tomas[ultima].sonido
        else:
            self.indice = len(self.tomas)

    def _siguiente(self):
        self.indice += 1
        self.tiempo = 0.0
        self.tiempo_texto = 0.0
        self.sonido_pendiente = self.actual.sonido if not self.terminada else None


# ----------------------------------------------------------------------
# Guiones
# ----------------------------------------------------------------------


def _toma_desde_datos(datos, rol, nombre_rol, pistas=0, reputacion=0):
    """Toma concreta a partir de un diccionario del contenido (misma
    convención que los diálogos: por_rol, requiere, JUGADOR -> rol)."""
    if not _cumple(datos.get("requiere"), pistas, reputacion):
        return None
    texto = datos.get("por_rol", {}).get(rol, datos.get("texto", ""))
    hablante = datos.get("hablante")
    retrato = datos.get("retrato")
    if hablante == HABLANTE_JUGADOR:
        hablante = nombre_rol
    if retrato == RETRATO_JUGADOR:
        retrato = rol
    efecto = datos.get("efecto", EFECTO_PANEO)
    if efecto not in EFECTOS:
        efecto = EFECTO_PANEO
    return Toma(
        id=datos["id"],
        duracion=float(datos.get("duracion", 5.0)),
        fondo=datos.get("fondo"),
        efecto=efecto,
        texto=texto,
        hablante=hablante,
        retrato=retrato,
        titulo=datos.get("titulo", ""),
        subtitulo=datos.get("subtitulo", ""),
        superior=datos.get("superior", ""),
        objetivos=list(datos.get("objetivos", [])),
        sonido=datos.get("sonido"),
        video=datos.get("video"),
    )


def guion_intro(contenido, rol=None, nombre_rol="Tú"):
    """La cinemática inicial (content/campaign.json, "cinematica_intro")
    más la pantalla de objetivos ("objetivos_intro"), que espera Enter."""
    tomas = []
    for datos in contenido.get("cinematica_intro", []):
        toma = _toma_desde_datos(datos, rol, nombre_rol)
        if toma is not None:
            tomas.append(toma)
    objetivos = contenido.get("objetivos_intro", [])
    if objetivos:
        tomas.append(Toma("objetivos", ESPERA_ENTER, FONDO_PROLOGO, EFECTO_OBJETIVOS,
                          titulo="TU MISIÓN", objetivos=list(objetivos), sonido="mision"))
    return Cinematica(tomas, titulo=contenido.get("titulo", ""))


def tarjeta_capitulo(numero, titulo, zona=None, duracion=DURACION_TARJETA_CAPITULO, ubicacion="", contexto="", objetivo=""):
    """Tarjeta de presentación del capítulo: número, nombre, ubicación,
    contexto breve y objetivo. Se lee con calma y Enter la pasa de inmediato."""
    superior = f"CAPÍTULO {numero}" if numero < 4 else "CAPÍTULO FINAL"
    lineas = [texto for texto in (contexto, objetivo) if texto]
    return Cinematica([Toma(f"tarjeta_{numero}", duracion, FONDO_POR_ZONA.get(zona), EFECTO_TARJETA,
                            titulo=titulo.upper(), superior=superior, subtitulo=ubicacion or zona or "",
                            lineas=lineas, sonido="transicion")])


def guion_entrada_jefe(pistas, total_pistas, capitulo=None):
    """Entrada a la Alcaldía: el Servidor Central se revela y NOVA_404
    habla; el texto del protagonista cambia según cuántas pistas lleva."""
    if pistas >= total_pistas:
        rastro = ("Tienes las tres pistas: el recorte firmado, el ataque a la enfermera y la raíz "
                  "en la red de la Alcaldía. Todo apunta aquí.")
    else:
        rastro = (f"Tienes {pistas} de {total_pistas} pistas. El rastro está incompleto, "
                  "pero termina en este servidor.")
    capitulo = capitulo or {}
    return Cinematica([
        Toma("jefe_1", 7.0, FONDO_POR_ZONA["Alcaldía"], EFECTO_PANEO, hablante=HABLANTE_NARRADOR, video=VIDEO_JEFE,
             texto="Bajo la Alcaldía late el Servidor Central: la máquina que amplifica cada rumor de Civitas.",
             sonido="transicion"),
        Toma("jefe_2", 7.0, FONDO_POR_ZONA["Alcaldía"], EFECTO_PANEO, hablante=HABLANTE_NARRADOR, texto=rastro),
        Toma("jefe_3", 7.0, FONDO_POR_ZONA["Alcaldía"], EFECTO_GLITCH, hablante=HABLANTE_NOVA, retrato="nova",
             texto="Llegas tarde. La ciudad ya cree lo que yo quise que creyera.", sonido="glitch"),
        Toma("jefe_4", DURACION_TARJETA_CAPITULO, FONDO_POR_ZONA["Alcaldía"], EFECTO_TARJETA, superior="CAPÍTULO FINAL",
             titulo="LA ÚLTIMA TRANSMISIÓN", subtitulo=capitulo.get("ubicacion", ""),
             lineas=[capitulo.get("contexto", ""), "Tres fases, 180 segundos. Todo ataque se puede esquivar."],
             sonido="viral"),
    ])


def guion_crisis(datos, nombre, rol=None):
    """Cinemática de la caída: titulares de Civitas sobre el protagonista,
    la narración y la mediadora que le ofrece reparar el daño. Después Main
    muestra la EleccionCrisis (src/story/redencion.py). `datos`: content
    "redencion"."""
    mentora = datos["mentora"]
    titulares = [t.format(nombre=nombre) for t in datos["titulares"]]
    return Cinematica([
        Toma("crisis_titulares", 7.0, FONDO_CRISIS, EFECTO_TITULARES, hablante="CIVITAS", video=VIDEO_CRISIS,
             texto="Tu nombre es tendencia en Ciudad Nova, y no por una buena razón.", lineas=titulares, sonido="crisis"),
        Toma("crisis_huella", 7.0, FONDO_CRISIS, EFECTO_RETRATO, hablante=HABLANTE_NARRADOR,
             retrato=f"{rol}_preocupado" if rol else None,
             texto=datos["narracion"]),
        Toma("crisis_mentora", 7.0, FONDO_REDENCION, EFECTO_RETRATO, hablante=mentora["nombre"], retrato=mentora["retrato"],
             texto=datos["dialogo_mentora"], sonido="notificacion"),
    ])


def guion_redencion(datos, rol=None, nombre="Tú"):
    """Cinemática de recuperación al completar la misión."""
    return Cinematica([
        Toma("redencion_1", 7.0, FONDO_REDENCION, EFECTO_RETRATO, hablante=datos["mentora"]["nombre"], video=VIDEO_REDENCION,
             retrato=datos["mentora"]["retrato"], texto=datos["mensaje_recuperacion"], sonido="redencion"),
        Toma("redencion_2", 7.0, FONDO_REDENCION, EFECTO_RETRATO, hablante=HABLANTE_NARRADOR,
             retrato=f"{rol}_decidido" if rol else None, texto=datos["recuperacion"]),
    ])


def guion_rechazo(datos, final):
    """El protagonista se niega: NOVA_404 lo usa de ejemplo y aparece el final."""
    return Cinematica([
        Toma("rechazo_nova", 7.0, FONDO_PANTALLAS_NOVA, EFECTO_GLITCH, hablante=HABLANTE_NOVA, retrato="nova",
             texto=datos["mensaje_rechazo"], sonido="glitch"),
        Toma("rechazo_tarjeta", 5.0, FONDO_CONFIANZA_PERDIDA, EFECTO_TARJETA, superior="FINAL",
             titulo=final["titulo"].upper(), sonido="derrota"),
        Toma("rechazo_texto", 7.0, FONDO_CONFIANZA_PERDIDA, EFECTO_PANEO, hablante=HABLANTE_NARRADOR, texto=final["texto"]),
    ], saltable=True)


def guion_caida_servidor():
    """Tras derrotar al jefe: el servidor se apaga y la ciudad vuelve a votar."""
    return Cinematica([
        Toma("caida_1", 7.0, FONDO_POR_ZONA["Alcaldía"], EFECTO_GLITCH, hablante=HABLANTE_NOVA,
             texto="Error 404. Señal perdida.", sonido="glitch"),
        Toma("caida_2", 7.0, FONDO_SERVIDOR_CAIDO, EFECTO_PANEO, hablante=HABLANTE_NARRADOR,
             texto="El Servidor Central se apaga. Los rebotes automáticos se detienen y, por primera vez en "
                   "días, Civitas queda en silencio.", sonido="victoria"),
        Toma("caida_3", 7.0, FONDO_PROLOGO, EFECTO_PANEO, hablante=HABLANTE_NARRADOR,
             texto="Amanece en Ciudad Nova. Hoy la ciudad elige alcalde, y vota con lo que tú le ayudaste a creer."),
    ])


def guion_final(clave, titulo, texto, epilogo=""):
    """Revelación del final (renace / dividida / arquitecto): tarjeta con
    el nombre del final y luego su texto, que espera Enter para cerrar.
    `epilogo`: línea extra si el protagonista pasó por la redención."""
    fondo = FONDO_POR_FINAL.get(clave, FONDO_PROLOGO)
    sonido = "derrota" if clave == "dividida" else "victoria"
    return Cinematica([
        Toma("final_tarjeta", 5.0, fondo, EFECTO_TARJETA, superior="FINAL", titulo=titulo.upper(), sonido=sonido),
        Toma("final_texto", ESPERA_ENTER, fondo, EFECTO_PANEO, hablante=HABLANTE_NARRADOR,
             texto=f"{texto} {epilogo}".strip()),
    ])


def guion_derrota_global():
    return Cinematica([
        Toma("colapso", 7.0, FONDO_PANTALLAS_NOVA, EFECTO_GLITCH, hablante=HABLANTE_NOVA,
             texto="Ya no hace falta que publique nada. Ustedes lo hacen por mí.", sonido="derrota"),
    ])


FONDOS_INTRO_OPCIONALES = (FONDO_CIUDADANOS, FONDO_PANTALLAS_NOVA, FONDO_SERVIDOR_CAIDO)
