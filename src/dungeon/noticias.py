"""Titulares del cintillo "Breaking News Civitas" (lógica pura, sin Pygame).

generar_titulares(estado) arma los titulares a partir del estado real
de la partida; el cintillo de la escena CIUDAD solo los desplaza.
"""

from dataclasses import dataclass, field

from src.core.balance import COLAPSO_TITULAR_ALTO

TITULAR_SIN_NOVEDADES = "Sin novedades en Ciudad Nova: todas las calles abiertas"
TITULAR_CALLE_BLOQUEADA = "ÚLTIMA HORA: barricada entre {a} y {b} por saturación"
TITULAR_COLAPSO_ALTO = "Colapso electoral en {valor:.1f}%: la ciudad al borde"
TITULAR_ALCALDIA_ABIERTA = "La Alcaldía abre sus puertas: el Servidor Central espera"
TITULAR_ALCALDIA_SELLADA = "La Alcaldía sigue sellada: se pide purificar una mazmorra"
TITULAR_TOXICIDAD = "{zona}: toxicidad {nivel:.0f}"


@dataclass
class EstadoNoticias:
    toxicidad: dict = field(default_factory=dict)  # {zona: nivel 0-100}
    calles_bloqueadas: list = field(default_factory=list)  # [(a, b)]
    colapso: float = 0.0
    alcaldia_abierta: bool = False


def generar_titulares(estado):
    """Lista de titulares, del más urgente al menos urgente:
    barricadas, colapso alto, estado de la Alcaldía y la toxicidad de
    cada zona (de mayor a menor). Sin barricadas ni colapso alto, el
    primero es TITULAR_SIN_NOVEDADES."""
    titulares = [TITULAR_CALLE_BLOQUEADA.format(a=a, b=b) for a, b in estado.calles_bloqueadas]
    if estado.colapso >= COLAPSO_TITULAR_ALTO:
        titulares.append(TITULAR_COLAPSO_ALTO.format(valor=estado.colapso))
    if not titulares:
        titulares.append(TITULAR_SIN_NOVEDADES)
    titulares.append(TITULAR_ALCALDIA_ABIERTA if estado.alcaldia_abierta else TITULAR_ALCALDIA_SELLADA)
    for zona, nivel in sorted(estado.toxicidad.items(), key=lambda par: -par[1]):
        titulares.append(TITULAR_TOXICIDAD.format(zona=zona, nivel=nivel))
    return titulares
