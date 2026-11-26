"""Vestidor: pestañas COLOR, HAIR, SHIRT, PANTS y SHOES (lógica pura).

Estilo Among Us: cada pestaña es una cuadrícula de opciones y la primera
siempre es AUTO (el color del dibujo). Moverse por la cuadrícula equipa al
instante: la vista previa y los demás jugadores ven el cambio en el
momento. Sin pygame, para probarse en aislado; el dibujo y el ratón viven
en Online/personalizacion_render.py.

    COLOR  AUTO + assets.TONOS_PIEL        -> Apariencia.piel      (tono de piel)
    HAIR   AUTO + assets.TONOS_PELO        -> Apariencia.pelo      (color del cabello)
    SHIRT  AUTO + assets.COLORES_ROPA      -> Apariencia.ropa      (color de la camisa)
    PANTS  AUTO + assets.COLORES_PANTALON  -> Apariencia.pantalon  (color del pantalón)
    SHOES  AUTO + assets.COLORES_ZAPATOS   -> Apariencia.zapatos   (color de los zapatos)

Cada color tiñe esa parte del personaje de Higgsfield conservando sus
sombras (src/ui/tinte_jugador.py). Navegar, cambiar de pestaña y elegir
son O(1) (las listas de opciones tienen a lo sumo 10 elementos).
"""

from src.core import assets
from src.core.apariencia import PREDETERMINADA

COLOR = "COLOR"
HAIR = "HAIR"
SHIRT = "SHIRT"
PANTS = "PANTS"
SHOES = "SHOES"
PESTANAS = (COLOR, HAIR, SHIRT, PANTS, SHOES)
CAMPO_DE_PESTANA = {COLOR: "piel", HAIR: "pelo", SHIRT: "ropa", PANTS: "pantalon", SHOES: "zapatos"}
COLUMNAS = 5  # opciones por fila de la cuadrícula

# Paleta de cada pestaña, en el orden de assets.
PALETA_DE_PESTANA = {COLOR: assets.TONOS_PIEL, HAIR: assets.TONOS_PELO, SHIRT: assets.COLORES_ROPA,
                     PANTS: assets.COLORES_PANTALON, SHOES: assets.COLORES_ZAPATOS}
NOMBRES_COLOR = {
    HAIR: ("Negro", "Castaño", "Café claro", "Rubio", "Pelirrojo", "Canoso", "Azul", "Rosa", "Morado"),
    SHIRT: ("Morado Civitas", "Rojo", "Naranja", "Amarillo", "Verde", "Turquesa", "Celeste", "Rosa", "Negro"),
    PANTS: ("Mezclilla", "Negro", "Gris", "Café", "Verde oliva", "Beige", "Vino", "Morado", "Blanco"),
    SHOES: ("Rojo", "Negro", "Blanco", "Azul", "Amarillo", "Verde", "Morado", "Café", "Naranja"),
}
PARTE_DE_PESTANA = {HAIR: "Cabello", SHIRT: "Camisa", PANTS: "Pantalón", SHOES: "Zapatos"}


def opciones(pestana):
    """Valores que ofrece `pestana`, en orden; el primero (None) es AUTO."""
    return (None, *range(len(PALETA_DE_PESTANA[pestana])))


def color_de_opcion(pestana, valor):
    """RGB de la muestra de una opción (None para AUTO)."""
    if valor is None:
        return None
    return PALETA_DE_PESTANA[pestana][valor]


def nombre_rol(rol):
    """'periodista' -> 'Periodista'."""
    return rol.capitalize()


def texto_opcion(pestana, valor, rol):
    """Qué es la opción `valor` de `pestana` para un jugador de rol `rol`."""
    if pestana == COLOR:
        return "Auto: piel original" if valor is None else f"Tono {valor + 1}"
    parte = PARTE_DE_PESTANA[pestana]
    if valor is None:
        return f"Auto: {parte.lower()} original ({nombre_rol(rol)})"
    return f"{parte}: {NOMBRES_COLOR[pestana][valor]}"


def etiqueta_opcion(pestana, valor):
    """Rótulo corto bajo cada casilla de la cuadrícula."""
    if valor is None:
        return "AUTO"
    if pestana in NOMBRES_COLOR:
        return NOMBRES_COLOR[pestana][valor]
    return f"Tono {valor + 1}"


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
