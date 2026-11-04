"""Misiones y objetivos visibles del modo historia (lógica pura, sin Pygame).

El jugador nunca debería adivinar qué hacer: en cada escena hay una
MISIÓN ACTUAL con objetivos en orden, cada uno con su progreso real
("Pruebas 2/3"). Nada de esto es estado nuevo: la misión se *deriva*
cada frame del estado que ya existe (Campania, Partida, la mazmorra
en curso o la arena del jefe), así no puede desincronizarse ni
duplicarse en cooperativo u Online.

    mision_actual(...) -> Mision(titulo, objetivos, pista)
    RastreadorMisiones.novedades(mision) -> objetivos recién cumplidos
        (para el aviso "Objetivo completado" y su sonido)

El orden de la campaña es Colegio -> Hospital -> Empresa de Medios ->
Alcaldía, pero el jugador puede entrar en cualquier orden: la misión de
la ciudad siempre apunta a la siguiente zona pendiente.
"""

from dataclasses import dataclass, field

from src.core.balance import ZONA_COLEGIO, ZONA_EMPRESA_MEDIOS, ZONA_HOSPITAL
from src.dungeon.grafo_ciudad import ZONA_FINAL

ORDEN_ZONAS = (ZONA_COLEGIO, ZONA_HOSPITAL, ZONA_EMPRESA_MEDIOS)
ARTICULO = {ZONA_COLEGIO: "el", ZONA_HOSPITAL: "el", ZONA_EMPRESA_MEDIOS: "la", ZONA_FINAL: "la"}


def con_articulo(zona):
    return f"{ARTICULO.get(zona, 'el')} {zona}"


# Escenas que entiende mision_actual (las mismas cadenas que Escena.value).
CIUDAD = "ciudad"
MAZMORRA = "mazmorra"
DECISION = "decision"
JEFE = "jefe"


@dataclass(frozen=True)
class Objetivo:
    id: str
    texto: str
    hecho: bool = False
    progreso: str = ""  # "2/3", "" si no aplica
    activo: bool = True  # False = todavía no toca (se muestra apagado)


@dataclass
class Mision:
    titulo: str
    objetivos: list = field(default_factory=list)
    pista: str = ""  # qué hacer ahora, en una línea

    @property
    def objetivo_pendiente(self):
        """El primer objetivo activo sin cumplir, o None si todo está hecho."""
        for objetivo in self.objetivos:
            if objetivo.activo and not objetivo.hecho:
                return objetivo
        return None

    @property
    def completada(self):
        return all(o.hecho for o in self.objetivos if o.activo)


def siguiente_zona(campania):
    """Primera zona normal sin purificar, en el orden de la campaña; None
    si las tres están purificadas."""
    purificadas = set(campania.zonas_purificadas())
    for zona in ORDEN_ZONAS:
        if zona not in purificadas:
            return zona
    return None


def mision_ciudad(campania, partida):
    """Misión mientras se camina por Ciudad Nova."""
    purificadas = set(campania.zonas_purificadas())
    objetivos = []
    for numero, zona in enumerate(ORDEN_ZONAS, start=1):
        hecha = zona in purificadas
        objetivos.append(Objetivo(f"purificar_{zona}", f"Cap. {numero}: purifica {con_articulo(zona)}", hecha))
    pistas, total = len(campania.pistas), campania.total_pistas()
    objetivos.append(Objetivo("pistas", "Reúne las pistas de NOVA_404", pistas >= total, f"{pistas}/{total}"))
    abierta = partida.alcaldia_desbloqueada()
    objetivos.append(Objetivo("alcaldia", "Entra a la Alcaldía y detén la transmisión",
                              campania.jefe_derrotado, activo=abierta or campania.jefe_derrotado))
    zona = siguiente_zona(campania)
    if campania.jefe_derrotado:
        titulo, pista = "CAMPAÑA COMPLETADA", "Puedes repetir zonas para mejorar los indicadores."
    elif abierta and zona is None:
        titulo, pista = "LA ÚLTIMA TRANSMISIÓN", "Ve a la Alcaldía y pulsa E en su puerta."
    elif abierta:
        titulo, pista = f"INVESTIGA EL {zona.upper()}", f"La Alcaldía ya está abierta; {con_articulo(zona)} aún guarda pistas."
    else:
        titulo, pista = f"INVESTIGA EL {zona.upper()}", f"Camina hasta {con_articulo(zona)} y pulsa E en su puerta (G marca la ruta)."
    return Mision(titulo, objetivos, pista)


def mision_mazmorra(campania, mazmorra, en_terminal=False):
    """Misión dentro de una mazmorra normal (`mazmorra` es la Mazmorra pura)."""
    zona = mazmorra.nombre_zona
    limpios, total = mazmorra.cuartos_limpios()
    pendientes = max(0, total - 1 - len([c for c in mazmorra.limpiados if c != mazmorra.cuarto_final]))
    reveladas = campania.evidencias_reveladas.get(zona, 0)
    total_evidencias = len(campania.evidencias_de(zona))
    final_abierto = mazmorra.final_desbloqueado()
    en_final = mazmorra.actual == mazmorra.cuarto_final
    decidida = zona in campania.resultados and (en_terminal is False and mazmorra.completada)
    objetivos = [
        Objetivo("cuartos", "Limpia los cuartos infectados", final_abierto, f"{min(limpios, total - 1)}/{total - 1}"),
        Objetivo("pruebas", "Encuentra pruebas", reveladas >= total_evidencias, f"{reveladas}/{total_evidencias}"),
        Objetivo("terminal", "Llega a la terminal Civitas (cuarto final)", en_final or decidida, activo=True),
        Objetivo("decidir", "Decide qué hacer con la publicación", decidida, activo=final_abierto),
    ]
    if en_terminal:
        pista = "Elige con ← → y confirma con Enter antes de que acabe el tiempo."
    elif not final_abierto:
        pista = f"Quedan {pendientes} cuarto(s) por limpiar. El cuarto final (candado en el minimapa) se abre al terminar."
    elif not en_final:
        pista = "Cuarto final desbloqueado: síguelo en el minimapa (M)."
    else:
        pista = "Elimina a todos los enemigos para abrir la terminal."
    return Mision(f"INVESTIGA EL {zona.upper()}", objetivos, pista)


def mision_jefe(arena_final):
    """Misión en la arena (`arena_final` es la MazmorraFinal pura con .jefe)."""
    jefe = arena_final.jefe
    fase = getattr(jefe, "fase", 1)
    objetivos = [
        Objetivo("fase1", "Rompe la primera defensa del servidor", fase >= 2),
        Objetivo("fase2", "Atraviesa el escudo de anonimato", fase >= 3, activo=fase >= 2),
        Objetivo("fase3", "Apaga el Servidor Central", not jefe.vivo, activo=fase >= 3),
    ]
    pista = "Todo ataque se puede esquivar: busca el hueco de cada ráfaga y usa el dash (Shift)."
    if fase == 2:
        pista = "El escudo cae con 15 impactos; el Fact-Checking del Periodista lo rompe de golpe."
    elif fase == 3:
        pista = "Tras cada ciclo hay 1.5 s sin ataques: castígalo ahí y evita los charcos."
    return Mision("LA ÚLTIMA TRANSMISIÓN", objetivos, pista)


def mision_actual(escena, campania, partida, mazmorra=None, arena_final=None):
    """La misión que corresponde a la escena (cadena de Escena.value)."""
    if escena in (MAZMORRA, DECISION) and mazmorra is not None:
        return mision_mazmorra(campania, mazmorra, en_terminal=escena == DECISION)
    if escena == JEFE and arena_final is not None:
        return mision_jefe(arena_final)
    return mision_ciudad(campania, partida)


class RastreadorMisiones:
    """Recuerda qué objetivos ya estaban cumplidos para avisar solo de
    los nuevos. Se reinicia al cambiar de misión (título distinto), así
    los objetivos de una zona nueva no se dan por "recién cumplidos"."""

    def __init__(self):
        self.titulo = None
        self.hechos = set()

    def novedades(self, mision):
        """Objetivos que pasaron a cumplidos desde la última llamada. La
        primera vez que se ve una misión no avisa de nada (solo registra)."""
        hechos = {o.id for o in mision.objetivos if o.hecho}
        if mision.titulo != self.titulo:
            self.titulo = mision.titulo
            self.hechos = hechos
            return []
        nuevos = [o for o in mision.objetivos if o.hecho and o.id not in self.hechos]
        self.hechos = hechos
        return nuevos
