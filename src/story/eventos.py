"""Eventos aleatorios de Ciudad Nova (sin Pygame).

Al volver a la ciudad tras resolver una zona se sortea un evento de un
conjunto pequeño (content/campaign.json, "eventos") con un
random.Random(semilla) inyectable: noticia viral, corrección
comunitaria, cuenta sospechosa o rumor reactivado. Un evento puede
exigir una condición (`requiere_detonacion`: alguna zona detonó) y
puede propagarse por la red social desde un ciudadano al azar (su
alcance real decide cuánto pesa). El azar elige QUÉ pasa; cuánto afecta
depende de las decisiones anteriores (las correcciones publicadas
reducen el rebote). El resultado es un titular para el cintillo y un
diccionario de efectos que la campaña aplica una sola vez por evento.
"""

from dataclasses import dataclass, field

from src.core.balance import DESINFORMACION_POR_ALCANZADO, VERIFICADA_POR_CORREGIDO
from src.story.red_social import CORRECCION, RUMOR


@dataclass
class EventoOcurrido:
    id: str
    titular: str
    efectos: dict = field(default_factory=dict)
    propagacion: object = None  # Propagacion si el evento viajó por la red


def eventos_posibles(eventos, hubo_detonacion):
    return [e for e in eventos if not e.get("requiere_detonacion") or hubo_detonacion]


def sortear_evento(eventos, rng, red=None, hubo_detonacion=False):
    """Elige un evento posible al azar y calcula sus efectos. Con `red`,
    un evento con "propaga": "rumor"/"correccion" viaja por BFS desde
    un ciudadano al azar y suma efectos según su alcance. Retorna
    EventoOcurrido o None si no hay eventos posibles."""
    posibles = eventos_posibles(eventos, hubo_detonacion)
    if not posibles:
        return None
    datos = rng.choice(posibles)
    efectos = dict(datos.get("efectos", {}))
    propagacion = None
    titular = datos["titulo"]
    if red is not None and datos.get("propaga") in (RUMOR, CORRECCION):
        origen = red.ciudadano_al_azar()
        if datos["propaga"] == RUMOR:
            propagacion = red.propagar(origen, tipo=RUMOR)
            efectos["desinformacion"] = efectos.get("desinformacion", 0) + int(
                propagacion.total * DESINFORMACION_POR_ALCANZADO)
        else:
            propagacion = red.corregir(origen)
            efectos["informacion_verificada"] = efectos.get("informacion_verificada", 0) + int(
                propagacion.total * VERIFICADA_POR_CORREGIDO)
        titular = f"{titular} ({red.nombre(origen)}: llegó a {propagacion.total} personas)"
    return EventoOcurrido(datos["id"], titular, efectos, propagacion)
