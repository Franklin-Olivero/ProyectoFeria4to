"""Vestidor del lobby online: pestañas COLOR, HAT y SKIN (lógica pura).

Estilo Among Us: cada pestaña es una cuadrícula de opciones y la primera
siempre es AUTO (lo del rol). Moverse por la cuadrícula equipa al
instante, como las flechas en la laptop de roles: la vista previa y los
demás jugadores ven el cambio en el momento. Sin pygame, para probarse en
aislado; el dibujo y el ratón viven en Online/personalizacion_render.py.

    COLOR  AUTO + assets.TONOS_PIEL        -> Apariencia.piel
    HAT    AUTO + assets.ROLES_APARIENCIA  -> Apariencia.cabeza
    SKIN   AUTO + assets.ROLES_APARIENCIA  -> Apariencia.traje

Navegar, cambiar de pestaña y elegir son O(1) (las listas de opciones
tienen a lo sumo 9 elementos).
"""

from src.core import assets
from src.core.apariencia import PREDETERMINADA

COLOR = "COLOR"
HAT = "HAT"
SKIN = "SKIN"
PESTANAS = (COLOR, HAT, SKIN)
CAMPO_DE_PESTANA = {COLOR: "piel", HAT: "cabeza", SKIN: "traje"}
COLUMNAS = 5  # opciones por fila de la cuadrícula


def opciones(pestana):
    """Valores que ofrece `pestana`, en orden; el primero (None) es AUTO."""
    if pestana == COLOR:
        return (None, *range(len(assets.TONOS_PIEL)))
    return (None, *assets.ROLES_APARIENCIA)


def nombre_rol(rol):
    """'periodista' -> 'Periodista'."""
    return rol.capitalize()


def texto_opcion(pestana, valor, rol):
    """Qué es la opción `valor` de `pestana` para un jugador de rol `rol`."""
    if pestana == COLOR:
        return "Auto: piel original" if valor is None else f"Tono {valor + 1}"
    parte = "Cabeza" if pestana == HAT else "Traje"
    if valor is None:
        return f"Auto: {parte.lower()} de tu rol ({nombre_rol(rol)})"
    return f"{parte} de {nombre_rol(valor)}"


def etiqueta_opcion(pestana, valor):
    """Rótulo corto bajo cada casilla de la cuadrícula."""
    if valor is None:
        return "AUTO"
    return f"Tono {valor + 1}" if pestana == COLOR else nombre_rol(valor)


class Vestidor:
    """Estado del modal abierto: la apariencia que se está armando y la
    pestaña visible. La casilla resaltada siempre es la opción equipada."""

    def __init__(self, apariencia=PREDETERMINADA, pestana=COLOR):
        self.apariencia = apariencia
        self.pestana = pestana if pestana in PESTANAS else COLOR

    @property
    def opciones(self):
        return opciones(self.pestana)

    def indice_elegido(self, pestana=None):
        """Casilla equipada en `pestana` (por defecto la visible)."""
        pestana = pestana or self.pestana
        valor = getattr(self.apariencia, CAMPO_DE_PESTANA[pestana])
        valores = opciones(pestana)
        return valores.index(valor) if valor in valores else 0

    def ir_a_pestana(self, indice):
        """Muestra la pestaña número `indice` (0 = COLOR). True si cambió."""
        if not 0 <= indice < len(PESTANAS) or PESTANAS[indice] == self.pestana:
            return False
        self.pestana = PESTANAS[indice]
        return True

    def pestana_siguiente(self, paso=1):
        """Pestaña de al lado, en ciclo (paso -1 = la anterior)."""
        indice = (PESTANAS.index(self.pestana) + paso) % len(PESTANAS)
        return self.ir_a_pestana(indice)

    def elegir(self, indice):
        """Equipa la opción `indice` de la pestaña visible. True si la
        apariencia cambió (hay que sincronizarla con la sala)."""
        valores = self.opciones
        if not 0 <= indice < len(valores):
            return False
        nueva = self.apariencia.con(CAMPO_DE_PESTANA[self.pestana], valores[indice])
        cambio = nueva != self.apariencia
        self.apariencia = nueva
        return cambio

    def mover(self, dx, dy):
        """Flechas en la cuadrícula de COLUMNAS columnas: ← → recorren
        todas las opciones en ciclo; ↑ ↓ cambian de fila (si la fila de
        abajo está incompleta, ↓ va a su última casilla). Equipa la nueva
        casilla y retorna True si la apariencia cambió."""
        total = len(self.opciones)
        indice = self.indice_elegido()
        if dx:
            indice = (indice + dx) % total
        if dy:
            destino = indice + dy * COLUMNAS
            if 0 <= destino < total:
                indice = destino
            elif dy > 0 and indice // COLUMNAS < (total - 1) // COLUMNAS:
                indice = total - 1
        return self.elegir(indice)
