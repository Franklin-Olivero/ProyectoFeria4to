"""Cinemáticas del modo historia (lógica pura, sin Pygame).

Una cinemática es una secuencia de `Toma`s con duración: la intro del
juego, la tarjeta de cada capítulo, la entrada al jefe, la caída del
Servidor Central y el final. Cada toma dice qué ilustración se ve
(`fondo`, id de assets/story/<id>.png o None), qué efecto la anima
(`efecto`: paneo lento, glitch de NOVA_404, notificaciones flotantes,
caos de publicaciones, retrato del protagonista, título, tarjeta de
capítulo, pantalla de objetivos) y el subtítulo que se escribe debajo.

Controles (los mismos que un diálogo): Enter pasa a la siguiente toma,
Esc salta toda la cinemática. Una toma con duración 0 espera Enter
(el botón "COMENZAR MISIÓN"). Nada aquí depende de archivos: si falta
una ilustración, el dibujo (src/ui/cinematica_render.py) usa su
fallback y la cinemática sigue, así el arranque del juego nunca depende
de un video o de una imagen externa.
"""

from dataclasses import dataclass, field

from src.core.assets import (
    DURACION_TARJETA_CAPITULO,
    FONDO_CIUDADANOS,
    FONDO_PANTALLAS_NOVA,
    FONDO_POR_FINAL,
    FONDO_POR_ZONA,
    FONDO_PROLOGO,
    FONDO_SERVIDOR_CAIDO,
)
from src.story.dialogo import HABLANTE_JUGADOR, RETRATO_JUGADOR, _cumple

# Efectos que conoce el render.
EFECTO_PANEO = "paneo"
EFECTO_GLITCH = "glitch"
EFECTO_NOTIFICACIONES = "notificaciones"
EFECTO_CAOS = "caos"
EFECTO_RETRATO = "retrato"
EFECTO_TITULO = "titulo"
EFECTO_TARJETA = "tarjeta"
EFECTO_OBJETIVOS = "objetivos"
EFECTOS = (EFECTO_PANEO, EFECTO_GLITCH, EFECTO_NOTIFICACIONES, EFECTO_CAOS, EFECTO_RETRATO,
           EFECTO_TITULO, EFECTO_TARJETA, EFECTO_OBJETIVOS)

HABLANTE_NARRADOR = "NARRADOR"
HABLANTE_NOVA = "NOVA_404"
HABLANTE_MENSAJE = "MENSAJE"

ESPERA_ENTER = 0.0  # duración de una toma que no avanza sola


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

    @property
    def espera(self):
        return self.duracion <= ESPERA_ENTER


class Cinematica:
    def __init__(self, tomas, titulo="", saltable=True):
        self.tomas = list(tomas)
        self.titulo = titulo
        self.saltable = saltable
        self.indice = 0
        self.tiempo = 0.0  # s dentro de la toma actual
        self.sonido_pendiente = self.tomas[0].sonido if self.tomas else None

    # ------------------------------------------------------------------
    @property
    def terminada(self):
        return self.indice >= len(self.tomas)

    @property
    def actual(self):
        return None if self.terminada else self.tomas[self.indice]

    @property
    def fraccion(self):
        """0-1 del avance de la toma actual (0 si espera Enter)."""
        toma = self.actual
        if toma is None or toma.espera:
            return 0.0
        return max(0.0, min(1.0, self.tiempo / toma.duracion))

    @property
    def progreso(self):
        return min(self.indice + 1, len(self.tomas)), len(self.tomas)

    def tomar_sonido(self):
        """Nombre del efecto que debe sonar ahora (una sola vez), o None."""
        sonido, self.sonido_pendiente = self.sonido_pendiente, None
        return sonido

    # ------------------------------------------------------------------
    def actualizar(self, dt):
        """Avanza el reloj; una toma con duración pasa sola al terminar. O(1)."""
        if self.terminada:
            return
        self.tiempo += dt
        toma = self.actual
        if not toma.espera and self.tiempo >= toma.duracion:
            self._siguiente()

    def avanzar(self):
        """Enter: la toma actual termina ya (la de objetivos cierra la cinemática)."""
        if not self.terminada:
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
            self.sonido_pendiente = self.tomas[ultima].sonido
        else:
            self.indice = len(self.tomas)

    def _siguiente(self):
        self.indice += 1
        self.tiempo = 0.0
        self.sonido_pendiente = self.actual.sonido if not self.terminada else None


# ----------------------------------------------------------------------
# Guiones
# ----------------------------------------------------------------------


def _toma_desde_datos(datos, rol, nombre_rol, pistas=0):
    """Toma concreta a partir de un diccionario del contenido (misma
    convención que los diálogos: por_rol, requiere, JUGADOR -> rol)."""
    if not _cumple(datos.get("requiere"), pistas):
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


def tarjeta_capitulo(numero, titulo, zona=None, duracion=DURACION_TARJETA_CAPITULO):
    """Tarjeta de presentación del capítulo ("CAPÍTULO 1 / EL RUMOR")."""
    superior = f"CAPÍTULO {numero}" if numero < 4 else "CAPÍTULO FINAL"
    return Cinematica([Toma(f"tarjeta_{numero}", duracion, FONDO_POR_ZONA.get(zona), EFECTO_TARJETA,
                            titulo=titulo.upper(), superior=superior, subtitulo=zona or "", sonido="transicion")])


def guion_entrada_jefe(pistas, total_pistas):
    """Entrada a la Alcaldía: el Servidor Central se revela y NOVA_404
    habla; el texto del protagonista cambia según cuántas pistas lleva."""
    if pistas >= total_pistas:
        rastro = ("Tienes las tres pistas: el recorte firmado, la cuenta automatizada y la raíz "
                  "en la red de la Alcaldía. Todo apunta aquí.")
    else:
        rastro = (f"Tienes {pistas} de {total_pistas} pistas. El rastro está incompleto, "
                  "pero termina en este servidor.")
    return Cinematica([
        Toma("jefe_1", 5.5, FONDO_POR_ZONA["Alcaldía"], EFECTO_PANEO, hablante=HABLANTE_NARRADOR,
             texto="Bajo la Alcaldía late el Servidor Central: la máquina que amplifica cada rumor de Civitas.",
             sonido="transicion"),
        Toma("jefe_2", 5.0, FONDO_POR_ZONA["Alcaldía"], EFECTO_PANEO, hablante=HABLANTE_NARRADOR, texto=rastro),
        Toma("jefe_3", 5.0, FONDO_POR_ZONA["Alcaldía"], EFECTO_GLITCH, hablante=HABLANTE_NOVA,
             texto="Llegas tarde. La ciudad ya cree lo que yo quise que creyera.", sonido="glitch"),
        Toma("jefe_4", 4.0, FONDO_POR_ZONA["Alcaldía"], EFECTO_TARJETA, superior="CAPÍTULO FINAL",
             titulo="LA ÚLTIMA TRANSMISIÓN", subtitulo="Sin decisiones: solo combate. 3 fases · 180 s",
             sonido="viral"),
    ])


def guion_caida_servidor():
    """Tras derrotar al jefe: el servidor se apaga y la ciudad vuelve a votar."""
    return Cinematica([
        Toma("caida_1", 4.5, FONDO_POR_ZONA["Alcaldía"], EFECTO_GLITCH, hablante=HABLANTE_NOVA,
             texto="Error 404. Señal perdida.", sonido="glitch"),
        Toma("caida_2", 5.5, FONDO_SERVIDOR_CAIDO, EFECTO_PANEO, hablante=HABLANTE_NARRADOR,
             texto="El Servidor Central se apaga. Los rebotes automáticos se detienen y, por primera vez en "
                   "días, Civitas queda en silencio.", sonido="victoria"),
        Toma("caida_3", 5.0, FONDO_PROLOGO, EFECTO_PANEO, hablante=HABLANTE_NARRADOR,
             texto="Amanece en Ciudad Nova. Hoy la ciudad elige alcalde, y vota con lo que tú le ayudaste a creer."),
    ])


def guion_final(clave, titulo, texto):
    """Revelación del final (renace / dividida / arquitecto): tarjeta con
    el nombre del final y luego su texto, que espera Enter para cerrar."""
    fondo = FONDO_POR_FINAL.get(clave, FONDO_PROLOGO)
    sonido = "derrota" if clave == "dividida" else "victoria"
    return Cinematica([
        Toma("final_tarjeta", 3.2, fondo, EFECTO_TARJETA, superior="FINAL", titulo=titulo.upper(), sonido=sonido),
        Toma("final_texto", ESPERA_ENTER, fondo, EFECTO_PANEO, hablante=HABLANTE_NARRADOR, texto=texto),
    ])


def guion_derrota_global():
    return Cinematica([
        Toma("colapso", 4.0, FONDO_PANTALLAS_NOVA, EFECTO_GLITCH, hablante=HABLANTE_NOVA,
             texto="Ya no hace falta que publique nada. Ustedes lo hacen por mí.", sonido="derrota"),
    ])


FONDOS_INTRO_OPCIONALES = (FONDO_CIUDADANOS, FONDO_PANTALLAS_NOVA, FONDO_SERVIDOR_CAIDO)
