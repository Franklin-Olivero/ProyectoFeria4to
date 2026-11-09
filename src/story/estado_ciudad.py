"""Indicadores de Ciudad Nova (lógica pura, sin Pygame).

Siete enteros acotados a [INDICADOR_MINIMO, INDICADOR_MAXIMO]:
informacion_verificada, confianza, convivencia, bienestar_digital,
participacion_responsable (buenos), desinformacion y conflictos
(malos). Solo cambian por `aplicar(efectos)`, que recibe un diccionario
{indicador: delta} y devuelve los deltas que de verdad se aplicaron
(acotados), para mostrarlos en pantalla.

Relación con el Colapso Electoral: son medidas distintas. El colapso
(src/core/colapso.py) sigue siendo la barra de derrota y la mueve
Partida.registrar_decision; estos indicadores describen CÓMO quedó la
ciudad y deciden el final y las elecciones simuladas.
"""

from src.core.balance import INDICADOR_MAXIMO, INDICADOR_MINIMO, INDICADORES_INICIALES
from src.story.contenido import INDICADORES, INDICADORES_BUENOS, INDICADORES_MALOS

NOMBRES_INDICADORES = {
    "informacion_verificada": "Información verificada",
    "confianza": "Confianza",
    "convivencia": "Convivencia",
    "bienestar_digital": "Bienestar digital",
    "participacion_responsable": "Participación responsable",
    "desinformacion": "Desinformación",
    "conflictos": "Conflictos",
}


def acotar(valor):
    return max(INDICADOR_MINIMO, min(INDICADOR_MAXIMO, int(round(valor))))


class EstadoCiudad:
    def __init__(self, valores=None):
        base = dict(INDICADORES_INICIALES)
        if valores:
            base.update(valores)
        self.valores = {nombre: acotar(base[nombre]) for nombre in INDICADORES}

    def valor(self, nombre):
        return self.valores[nombre]

    def aplicar(self, efectos):
        """Suma cada delta (acotando) y retorna {indicador: delta real}.
        Un indicador desconocido lanza KeyError: el contenido se valida
        al cargar, así que aquí sería un error de programación."""
        aplicados = {}
        for nombre, delta in efectos.items():
            if nombre not in self.valores:
                raise KeyError(f"Indicador desconocido: {nombre!r}")
            antes = self.valores[nombre]
            self.valores[nombre] = acotar(antes + delta)
            aplicados[nombre] = self.valores[nombre] - antes
        return aplicados

    def salud(self):
        """Promedio 0-100 que resume la ciudad: los indicadores buenos
        suman y los malos restan (100 - valor)."""
        buenos = [self.valores[n] for n in INDICADORES_BUENOS]
        malos = [INDICADOR_MAXIMO - self.valores[n] for n in INDICADORES_MALOS]
        return round(sum(buenos + malos) / len(buenos + malos))

    def como_dict(self):
        return dict(self.valores)

    def filas(self):
        """[(nombre legible, valor, es_bueno)] en orden fijo, para los paneles."""
        return [(NOMBRES_INDICADORES[n], self.valores[n], n in INDICADORES_BUENOS) for n in INDICADORES]
