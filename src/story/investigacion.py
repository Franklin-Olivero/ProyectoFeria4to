"""Investigación del origen de la señal, capítulo 3 (lógica pura, sin Pygame).

Tras resolver la terminal de la Empresa de Medios el jugador rastrea de
dónde salen las publicaciones coordinadas. Las cuentas forman un grafo
(content/campaign.json, "red_cuentas") construido sobre el Grafo manual de
src/structures/graph.py: dos cuentas están unidas si una rebotó a la otra.

La investigación ES un recorrido en profundidad hecho a mano:

    - `pila` son las cuentas del hilo actual, de la inicial a la que se mira;
    - "seguir" una cuenta vecina no visitada la apila (bajar por el hilo);
    - "volver" desapila (backtracking cuando un hilo termina en una persona);
    - `visitadas` evita revisar dos veces la misma cuenta.

`orden_dfs_referencia` es el orden que da Grafo.dfs desde la misma cuenta:
la pantalla lo muestra al terminar para comparar el rastreo del jugador con
el del algoritmo. Al final el jugador señala la cuenta que cree que es el
origen; una vez, y sin votaciones: el resultado depende del tipo real de la
cuenta (origen, amplificador, error humano o víctima). Señalar a una persona
inocente tiene costo; ninguna elección bloquea la campaña.

En Online decide el host, que recibe las navegaciones de los invitados
(DECISION_NAV: izquierda, derecha, confirmar).
"""

from dataclasses import dataclass, field

from src.core.balance import PUNTOS_ORIGEN_RASTREADO, REPUTACION_POR_TIPO_CUENTA
from src.structures.graph import Grafo

IZQUIERDA = "izquierda"
DERECHA = "derecha"
CONFIRMAR = "confirmar"

TIPO_ORIGEN = "origen"
TIPO_AMPLIFICADOR = "amplificador"
TIPO_ERROR = "error"
TIPO_VICTIMA = "victima"
TIPOS_CUENTA = (TIPO_ORIGEN, TIPO_AMPLIFICADOR, TIPO_ERROR, TIPO_VICTIMA)

# Opciones que se ofrecen en cada cuenta.
SEGUIR = "seguir"
VOLVER = "volver"
SENALAR = "senalar"

EFECTOS_POR_TIPO = {
    TIPO_ORIGEN: {"informacion_verificada": 8, "confianza": 6, "desinformacion": -8},
    TIPO_AMPLIFICADOR: {"informacion_verificada": 2, "desinformacion": -2},
    TIPO_ERROR: {"conflictos": 6, "convivencia": -4},
    TIPO_VICTIMA: {"conflictos": 10, "convivencia": -6, "confianza": -4},
}
TEXTOS_RESULTADO = {
    TIPO_ORIGEN: "Seguiste el hilo hasta el final: 'nova_root' programa a las demás cuentas desde la red "
                 "interna de la Alcaldía. Esa es la señal.",
    TIPO_AMPLIFICADOR: "Esa cuenta rebota la señal, pero no la origina. Cayó una pieza; la máquina sigue en pie.",
    TIPO_ERROR: "Señalaste a alguien que compartió por error y ya se había retractado. El origen siguió operando.",
    TIPO_VICTIMA: "Señalaste a una víctima de la campaña. Tu denuncia le cayó encima a una persona inocente.",
}


@dataclass(frozen=True)
class OpcionInvestigacion:
    tipo: str  # SEGUIR, VOLVER o SENALAR
    etiqueta: str
    cuenta: str | None = None  # id de la cuenta vecina (solo SEGUIR)


@dataclass
class ResultadoInvestigacion:
    cuenta: dict
    correcto: bool
    tipo: str
    texto: str
    efectos: dict = field(default_factory=dict)
    reputacion: int = 0
    puntos: int = 0


class Investigacion:
    def __init__(self, datos):
        self.cuentas = {c["id"]: c for c in datos["cuentas"]}
        self.inicio = datos["inicio"]
        self.origen = datos["origen"]
        self.grafo = Grafo()
        for id_cuenta in self.cuentas:
            self.grafo.agregar_nodo(id_cuenta)
        for a, b in datos["conexiones"]:
            self.grafo.agregar_arista(a, b, 1)
        self.pila = [self.inicio]
        self.visitadas = [self.inicio]  # en orden de visita
        self.indice = 0
        self.resultado = None

    # ------------------------------------------------------------------
    # Consultas
    # ------------------------------------------------------------------
    @property
    def actual(self):
        return self.pila[-1]

    @property
    def cuenta_actual(self):
        return self.cuentas[self.actual]

    @property
    def terminada(self):
        return self.resultado is not None

    def vecinas_sin_visitar(self):
        return [v for v in self.grafo.vecinos(self.actual) if v not in self.visitadas]

    def opciones(self):
        """Lo que se puede hacer en la cuenta actual, en el orden en que
        se dibuja: seguir cada vecina sin visitar, volver y señalar."""
        lista = [OpcionInvestigacion(SEGUIR, f"Seguir a {self.cuentas[v]['nombre']}", v)
                 for v in self.vecinas_sin_visitar()]
        if len(self.pila) > 1:
            lista.append(OpcionInvestigacion(VOLVER, "Volver al hilo anterior"))
        lista.append(OpcionInvestigacion(SENALAR, "Señalar esta cuenta como origen"))
        return lista

    @property
    def opcion_seleccionada(self):
        return self.opciones()[self.indice]

    def orden_dfs_referencia(self):
        """Orden del DFS del grafo desde la cuenta inicial (Grafo.dfs, pila
        explícita): con qué orden lo habría recorrido el algoritmo."""
        return self.grafo.dfs(self.inicio)

    # ------------------------------------------------------------------
    # Navegación
    # ------------------------------------------------------------------
    def navegar(self, direccion):
        """← → mueven el cursor entre las opciones (circular); Enter aplica. O(V)."""
        if self.terminada:
            return
        cantidad = len(self.opciones())
        if direccion == IZQUIERDA:
            self.indice = (self.indice - 1) % cantidad
        elif direccion == DERECHA:
            self.indice = (self.indice + 1) % cantidad
        elif direccion == CONFIRMAR:
            self._aplicar(self.opcion_seleccionada)

    def _aplicar(self, opcion):
        if opcion.tipo == SEGUIR:
            self.pila.append(opcion.cuenta)
            self.visitadas.append(opcion.cuenta)
        elif opcion.tipo == VOLVER:
            self.pila.pop()
        else:
            self.resultado = self.senalar(self.actual)
        self.indice = 0

    def a_dict(self):
        """Lo que necesita un invitado para ver el mismo rastreo."""
        return {"pila": list(self.pila), "vis": list(self.visitadas), "i": self.indice,
                "fin": None if self.resultado is None else self.resultado.cuenta["id"]}

    def copiar_de(self, datos):
        """Invitado: copia el estado del host, ignorando lo que no sean cuentas reales."""
        if not isinstance(datos, dict):
            return
        pila, visitadas = datos.get("pila"), datos.get("vis")
        pila = [c for c in pila if c in self.cuentas] if isinstance(pila, list) else []
        if pila:
            self.pila = pila
        visitadas = [c for c in visitadas if c in self.cuentas] if isinstance(visitadas, list) else []
        if visitadas:
            self.visitadas = visitadas
        if isinstance(datos.get("i"), int):
            self.indice = max(0, min(datos["i"], len(self.opciones()) - 1))
        if datos.get("fin") in self.cuentas and self.resultado is None:
            self.resultado = self.senalar(datos["fin"])

    def senalar(self, id_cuenta):
        """Resultado de señalar `id_cuenta`: depende solo de su tipo real."""
        cuenta = self.cuentas[id_cuenta]
        tipo = cuenta["tipo"]
        correcto = id_cuenta == self.origen
        return ResultadoInvestigacion(
            cuenta=cuenta,
            correcto=correcto,
            tipo=tipo,
            texto=TEXTOS_RESULTADO[tipo],
            efectos=dict(EFECTOS_POR_TIPO[tipo]),
            reputacion=REPUTACION_POR_TIPO_CUENTA[tipo],
            puntos=PUNTOS_ORIGEN_RASTREADO if correcto else 0,
        )
