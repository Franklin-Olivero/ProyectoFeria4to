"""Registro de mazmorras y estado del tablero del lobby (lógica pura).

El tablero del lobby (la cartelera de la recepción del hotel) lista cada
mazmorra registrada con su nivel de toxicidad y su estado. Hoy están las
cuatro de Ciudad Nova; la parte 2 (mazmorras del nuevo mundo) solo tiene
que llamar a registrar() con las suyas.

    REGISTRO                                 -> tupla de EntradaMazmorra
    registrar(entrada)                       -> la agrega (error si el id se repite)
    filas_tablero(toxicidad_de, completadas) -> [FilaTablero] en el orden del registro

Una mazmorra normal está "completada" solo si su decisión terminó en
Purificación Exitosa (src/dungeon/progreso.py): eso es lo que trae
`completadas` (Campania.zonas_purificadas). La final, al derrotar al jefe.
"""

from dataclasses import dataclass

from src.dungeon.grafo_ciudad import ZONA_FINAL

ESTADO_PENDIENTE = "pendiente"
ESTADO_COMPLETADA = "completada"
TIPO_NORMAL = "normal"
TIPO_FINAL = "final"


@dataclass(frozen=True)
class EntradaMazmorra:
    id: str
    nombre: str  # lo que muestra el tablero
    zona: str  # clave de la zona (toxicidad, progreso)
    tipo: str = TIPO_NORMAL
    mundo: str = "ciudad_nova"


@dataclass(frozen=True)
class FilaTablero:
    id: str
    nombre: str
    toxicidad: int  # 0-100, redondeada
    estado: str
    tipo: str


_REGISTRO = [
    EntradaMazmorra("colegio", "Colegio", "Colegio"),
    EntradaMazmorra("hospital", "Hospital", "Hospital"),
    EntradaMazmorra("medios", "Empresa de Medios", "Empresa de Medios"),
    EntradaMazmorra("alcaldia", "Alcaldía", ZONA_FINAL, TIPO_FINAL),
]


def registro():
    return tuple(_REGISTRO)


def registrar(entrada):
    if any(e.id == entrada.id for e in _REGISTRO):
        raise ValueError(f"ya hay una mazmorra con id {entrada.id!r}")
    _REGISTRO.append(entrada)


def quitar(id_mazmorra):
    """Saca una entrada (lo usan las pruebas para dejar el registro como estaba)."""
    _REGISTRO[:] = [e for e in _REGISTRO if e.id != id_mazmorra]


def estado(entrada, completadas, jefe_derrotado=False):
    if entrada.tipo == TIPO_FINAL:
        return ESTADO_COMPLETADA if jefe_derrotado else ESTADO_PENDIENTE
    return ESTADO_COMPLETADA if entrada.zona in completadas else ESTADO_PENDIENTE


def filas_tablero(toxicidad_de, completadas=(), jefe_derrotado=False, entradas=None):
    """Una fila por mazmorra: `toxicidad_de(zona)` da su nivel 0-100."""
    completadas = set(completadas)
    return [FilaTablero(e.id, e.nombre, round(toxicidad_de(e.zona)), estado(e, completadas, jefe_derrotado), e.tipo)
            for e in (registro() if entradas is None else entradas)]


def resumen(filas):
    """(completadas, total) para el encabezado del tablero."""
    return sum(1 for f in filas if f.estado == ESTADO_COMPLETADA), len(filas)
