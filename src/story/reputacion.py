"""Reputación individual y valoración de acciones (lógica pura, sin Pygame).

La reputación mide cómo percibe Ciudad Nova a CADA jugador: un entero de
-100 a +100 que empieza en 0. Tres ideas sostienen el sistema:

    1. Una acción no es buena o mala por su nombre. Se valora con la tabla
       balance.VALORACION_ACCIONES según la veracidad REAL de la publicación
       y lo que el jugador podía saber (estado de evidencia): compartir algo
       verdadero y comprobado suma; reportarlo sin razón resta; equivocarse
       sin pruebas pesa menos que difundir sabiendo que es falso.
    2. El cambio tiene consecuencias: el nivel (referente, confiable, neutral,
       cuestionada, crisis) altera diálogos, alcance de las correcciones en el
       grafo social, pruebas que exige la terminal y reacciones de la ciudad.
    3. A -60 o menos se abre una crisis, que se resuelve con la misión de
       redención (src/story/redencion.py) o con su rechazo.

Reglas contra dobles recompensas: un cambio con `clave` se cobra una sola
vez (`aplicar` lo ignora si la clave ya se usó); las penalizaciones sin
clave sí se repiten. Todo cambio pasa por `aplicar`.
"""

from dataclasses import dataclass

from src.core.balance import (
    AFECTADOS_POR_PUNTO_BONO,
    BONO_MAXIMO_ALCANCE,
    MULTIPLICADOR_GRAVEDAD,
    NIVELES_REPUTACION,
    PENALIZACION_MAXIMA_ALCANCE,
    PENALIZACION_POR_AFECTADO,
    REPUTACION_INICIAL,
    REPUTACION_MAXIMA,
    REPUTACION_MINIMA,
    UMBRAL_CRISIS_REPUTACION,
    VALORACION_ACCIONES,
)

# Veracidad real de una publicación (a partir del veredicto del contenido).
VERAZ = "veraz"
ENGANOSA = "enganosa"
# Lo que el jugador podía saber al decidir (a partir del estado de evidencia).
SIN_SABER = "sin_saber"
INDICIOS = "indicios"
SABIA = "sabia"
_INDICE_CONOCIMIENTO = {SIN_SABER: 0, INDICIOS: 1, SABIA: 2}
_CONOCIMIENTO_POR_ESTADO = {"sin_pruebas": SIN_SABER, "parcial": INDICIOS, "verificado": SABIA, "desmentido": SABIA}

# Estados de la crisis de un jugador.
SIN_CRISIS = "sin_crisis"
CRISIS_PENDIENTE = "crisis_pendiente"  # espera a una pausa segura para presentarse
EN_REDENCION = "en_redencion"
REDIMIDO = "redimido"
RECHAZADA = "rechazada"
FALLIDA = "fallida"
ESTADOS_SIN_VOZ = (RECHAZADA, FALLIDA)


def clase_veracidad(veredicto):
    """"cierto" es veraz; lo falso, fuera de contexto o sin verificar se
    trata como engañoso: difundirlo sin comprobar tiene el mismo riesgo."""
    return VERAZ if veredicto == "cierto" else ENGANOSA


def conocimiento_de(estado_evidencia):
    return _CONOCIMIENTO_POR_ESTADO.get(estado_evidencia, SIN_SABER)


def valorar_accion(accion, veredicto, estado_evidencia, gravedad="media"):
    """Puntos de reputación de `accion`. Acción sin valorar = 0. O(1)."""
    tabla = VALORACION_ACCIONES.get(accion)
    if tabla is None:
        return 0
    valor = tabla[clase_veracidad(veredicto)][_INDICE_CONOCIMIENTO[conocimiento_de(estado_evidencia)]]
    if valor < 0:
        return round(valor * MULTIPLICADOR_GRAVEDAD.get(gravedad, 1.0))
    return valor


def ajuste_por_alcance(delta, afectados):
    """El grafo social modula el cambio: quien dañó a más gente pierde más
    y quien informó a más gente gana un poco más (`afectados` sale del BFS)."""
    if delta < 0:
        return delta - min(PENALIZACION_MAXIMA_ALCANCE, afectados * PENALIZACION_POR_AFECTADO)
    if delta > 0:
        return delta + min(BONO_MAXIMO_ALCANCE, afectados // AFECTADOS_POR_PUNTO_BONO)
    return 0


def nivel_de(valor):
    """(id, nombre) del tramo al que pertenece `valor`."""
    for identificador, nombre, minimo in NIVELES_REPUTACION:
        if valor >= minimo:
            return identificador, nombre
    return NIVELES_REPUTACION[-1][:2]


@dataclass(frozen=True)
class CambioReputacion:
    """Un cambio ya aplicado (lo que anima el indicador y guarda el historial)."""

    antes: int
    despues: int
    mensaje: str = ""
    motivo: str = ""  # de dónde vino ("Colegio", "Segunda oportunidad"...)
    clave: str | None = None

    @property
    def delta(self):
        return self.despues - self.antes

    @property
    def nivel_antes(self):
        return nivel_de(self.antes)[0]

    @property
    def nivel_despues(self):
        return nivel_de(self.despues)[0]


class ReputacionJugador:
    def __init__(self, valor=REPUTACION_INICIAL):
        self.valor = valor
        self.historial = []  # CambioReputacion en orden
        self.cobradas = set()  # claves de recompensas ya aplicadas
        self.pendientes = []  # cambios que la interfaz aún no presentó
        self.contador = 0  # cambios aplicados (el invitado detecta novedades con él)
        self.tope = REPUTACION_MAXIMA  # baja tras redimirse: la huella queda
        self.estado_crisis = SIN_CRISIS
        self.redenciones = 0  # misiones completadas

    @property
    def nivel(self):
        return nivel_de(self.valor)[0]

    @property
    def nombre_nivel(self):
        return nivel_de(self.valor)[1]

    @property
    def sin_voz(self):
        """Rechazó o falló la redención: ya no decide por la ciudad."""
        return self.estado_crisis in ESTADOS_SIN_VOZ

    def aplicar(self, delta, mensaje="", motivo="", clave=None):
        """Suma `delta` acotando a [-100, tope]. Retorna el CambioReputacion,
        o None si la clave ya se cobró o quien cambia ya no tiene voz. O(1)."""
        if self.sin_voz or (clave is not None and clave in self.cobradas):
            return None
        if clave is not None:
            self.cobradas.add(clave)
        antes = self.valor
        self.valor = max(REPUTACION_MINIMA, min(self.tope, antes + int(delta)))
        cambio = CambioReputacion(antes, self.valor, mensaje, motivo, clave)
        self.historial.append(cambio)
        self.pendientes.append(cambio)
        self.contador += 1
        self._revisar_crisis()
        return cambio

    def _revisar_crisis(self):
        if self.valor <= UMBRAL_CRISIS_REPUTACION and self.estado_crisis in (SIN_CRISIS, REDIMIDO):
            self.estado_crisis = CRISIS_PENDIENTE

    def tomar_pendiente(self):
        return self.pendientes.pop(0) if self.pendientes else None

    @property
    def crisis_pendiente(self):
        return self.estado_crisis == CRISIS_PENDIENTE

    def peor_cambio(self):
        """El cambio negativo más grande del historial, o None."""
        negativos = [c for c in self.historial if c.delta < 0]
        return min(negativos, key=lambda c: c.delta) if negativos else None
