"""Secuencia de diálogo del modo historia (lógica pura, sin Pygame).

Una lista de líneas del contenido ({hablante, texto, retrato,
por_rol, requiere}) se convierte en la secuencia que ve un jugador
concreto: el hablante "JUGADOR" toma el nombre de su rol, `por_rol`
reemplaza el texto por la variante del rol si existe, y `requiere`
({"pistas_min": n} / {"pistas_max": n}) filtra líneas según cuántas
pistas de NOVA_404 lleva. ENTER avanza (avanzar) y una tecla de salto
termina la secuencia (saltar). El dibujo vive en
src/ui/dialogo_render.py.
"""

from dataclasses import dataclass

HABLANTE_JUGADOR = "JUGADOR"
RETRATO_JUGADOR = "jugador"


@dataclass(frozen=True)
class Linea:
    hablante: str
    texto: str
    retrato: str | None = None  # "civitas", "nova", id de rol o None


def _cumple(requisitos, pistas):
    if not requisitos:
        return True
    if "pistas_min" in requisitos and pistas < requisitos["pistas_min"]:
        return False
    if "pistas_max" in requisitos and pistas > requisitos["pistas_max"]:
        return False
    return True


def resolver_lineas(lineas, rol=None, nombre_rol="Tú", pistas=0):
    """Líneas concretas para el rol `rol` (clave "periodista"...) con
    `pistas` reunidas. O(L) con L líneas."""
    resultado = []
    for datos in lineas:
        if not _cumple(datos.get("requiere"), pistas):
            continue
        texto = datos.get("por_rol", {}).get(rol, datos["texto"])
        hablante = datos["hablante"]
        retrato = datos.get("retrato")
        if hablante == HABLANTE_JUGADOR:
            hablante = nombre_rol
        if retrato == RETRATO_JUGADOR:
            retrato = rol
        resultado.append(Linea(hablante, texto, retrato))
    return resultado


class DialogoSecuencia:
    def __init__(self, lineas, rol=None, nombre_rol="Tú", pistas=0, titulo="", fondo=None):
        self.lineas = resolver_lineas(lineas, rol, nombre_rol, pistas)
        self.titulo = titulo
        self.fondo = fondo  # id de ilustración (assets.FONDO_*) o None
        self.indice = 0

    @property
    def terminado(self):
        return self.indice >= len(self.lineas)

    @property
    def actual(self):
        return None if self.terminado else self.lineas[self.indice]

    @property
    def progreso(self):
        """(número de línea 1-based, total) para el indicador."""
        return min(self.indice + 1, len(self.lineas)), len(self.lineas)

    def avanzar(self):
        if not self.terminado:
            self.indice += 1

    def saltar(self):
        self.indice = len(self.lineas)
