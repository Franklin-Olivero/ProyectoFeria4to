"""Secuencia de diálogo del modo historia (lógica pura, sin Pygame).

Una lista de líneas del contenido ({hablante, texto, retrato,
por_rol, requiere}) se convierte en la secuencia que ve un jugador
concreto: el hablante "JUGADOR" toma el nombre de su rol, `por_rol`
reemplaza el texto por la variante del rol si existe, y `requiere`
filtra líneas según las pistas de NOVA_404 ({"pistas_min": n},
{"pistas_max": n}) o la reputación del jugador ({"reputacion_min": n},
{"reputacion_max": n}).

Lectura al ritmo del jugador: con `velocidad` (caracteres por segundo) el
texto se escribe poco a poco; ENTER primero lo revela completo y, ya
completo, pasa a la siguiente página. Un texto largo se parte en páginas
(`paginar_texto`) en vez de recortarse con puntos suspensivos. La tecla de
salto termina la secuencia. El dibujo vive en src/ui/dialogo_render.py.
"""

from dataclasses import dataclass

HABLANTE_JUGADOR = "JUGADOR"
RETRATO_JUGADOR = "jugador"
# Caracteres por página: cabe en el panel de diálogo a su tamaño de letra
# (lo comprueba tests/test_cinematicas_lectura.py con la fuente real).
MAX_CARACTERES_PAGINA = 230
EMOCION_PREOCUPADO_HASTA = -20  # reputación con la que el retrato se ve preocupado
EMOCION_DECIDIDO_DESDE = 20


@dataclass(frozen=True)
class Linea:
    hablante: str
    texto: str
    retrato: str | None = None  # "civitas", "nova", id de rol o None


def _cumple(requisitos, pistas, reputacion=0):
    if not requisitos:
        return True
    if "pistas_min" in requisitos and pistas < requisitos["pistas_min"]:
        return False
    if "pistas_max" in requisitos and pistas > requisitos["pistas_max"]:
        return False
    if "reputacion_min" in requisitos and reputacion < requisitos["reputacion_min"]:
        return False
    if "reputacion_max" in requisitos and reputacion > requisitos["reputacion_max"]:
        return False
    return True


def paginar_texto(texto, maximo=MAX_CARACTERES_PAGINA):
    """Parte `texto` en páginas de a lo sumo `maximo` caracteres, cortando
    al final de una oración si se puede y si no entre palabras. O(n)."""
    if len(texto) <= maximo:
        return [texto]
    paginas, actual = [], ""
    for palabra in texto.split(" "):
        candidato = f"{actual} {palabra}".strip()
        if len(candidato) <= maximo:
            actual = candidato
            continue
        corte = max(actual.rfind(". "), actual.rfind("? "), actual.rfind("! "))
        if corte >= maximo // 2:
            paginas.append(actual[: corte + 1])
            actual = f"{actual[corte + 2:]} {palabra}".strip()
        else:
            paginas.append(actual)
            actual = palabra
    if actual:
        paginas.append(actual)
    return paginas


def resolver_lineas(lineas, rol=None, nombre_rol="Tú", pistas=0, reputacion=0):
    """Líneas concretas para el rol `rol` (clave "periodista"...) con
    `pistas` reunidas y `reputacion`. Las largas salen en varias páginas. O(L)."""
    resultado = []
    for datos in lineas:
        if not _cumple(datos.get("requiere"), pistas, reputacion):
            continue
        texto = datos.get("por_rol", {}).get(rol, datos["texto"])
        hablante = datos["hablante"]
        retrato = datos.get("retrato")
        if hablante == HABLANTE_JUGADOR:
            hablante = nombre_rol
        if retrato == RETRATO_JUGADOR:
            retrato = rol
            # El rostro del protagonista refleja cómo lo ve la ciudad.
            if rol is not None and reputacion <= EMOCION_PREOCUPADO_HASTA:
                retrato = f"{rol}_preocupado"
            elif rol is not None and reputacion >= EMOCION_DECIDIDO_DESDE:
                retrato = f"{rol}_decidido"
        for pagina in paginar_texto(texto):
            resultado.append(Linea(hablante, pagina, retrato))
    return resultado


class DialogoSecuencia:
    def __init__(self, lineas, rol=None, nombre_rol="Tú", pistas=0, titulo="", fondo=None, reputacion=0):
        self.lineas = resolver_lineas(lineas, rol, nombre_rol, pistas, reputacion)
        self.titulo = titulo
        self.fondo = fondo  # id de ilustración (assets.FONDO_*) o None
        self.indice = 0
        self.velocidad = None  # caracteres/s; None = sin efecto de escritura
        self.tiempo_texto = 0.0

    def configurar_lectura(self, velocidad=None, **_):
        """Velocidad de escritura elegida en Ajustes (la pone Main.py)."""
        self.velocidad = velocidad

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

    @property
    def caracteres_visibles(self):
        linea = self.actual
        if linea is None:
            return 0
        if self.velocidad is None:
            return len(linea.texto)
        return min(len(linea.texto), int(self.tiempo_texto * self.velocidad))

    @property
    def texto_completo(self):
        linea = self.actual
        return linea is None or self.caracteres_visibles >= len(linea.texto)

    def actualizar(self, dt):
        self.tiempo_texto += dt

    def avanzar(self):
        """ENTER: revela el texto si aún se escribe; si no, siguiente página."""
        if self.terminado:
            return
        if not self.texto_completo:
            self.tiempo_texto = len(self.actual.texto) / self.velocidad + 0.01
            return
        self.indice += 1
        self.tiempo_texto = 0.0

    def saltar(self):
        self.indice = len(self.lineas)
