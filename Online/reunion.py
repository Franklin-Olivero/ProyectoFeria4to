"""Reunión de emergencia del modo Online (lógica pura, sin pygame).

Cualquier jugador que no fue expulsado aprieta REPORTAR (se puede cada
COOLDOWN_REUNION segundos) y el juego se detiene para todos: el equipo tiene
DURACION_REUNION segundos para hablar por el chat y votar a quién cree que
es el impostor, o saltar. Al acabarse el tiempo (o cuando ya votaron
todos) solo cuentan los votos emitidos: quien no votó no le suma a nadie.
Si alguien tiene más votos que cualquier otro y que los saltos, queda
expulsado: se vuelve un fantasma (src/core/equipo.py), ya no mueve la
terminal de decisión, no vota ni convoca, y todos ven si era el impostor.

Fin de la partida: si expulsan al impostor, gana la tripulación ("Civitas
se ha salvado"). Si expulsan inocentes hasta que quedan solo el impostor y
uno más, gana el impostor ("El impostor quedó en pie"); con 2 jugadores
basta con expulsar al otro (JUGADORES_MINIMOS_VICTORIA_IMPOSTOR = 2).

El host lleva todo (autoritativo) y lo manda en el ESTADO (`a_dict`); cada
invitado solo lo muestra (`vista_de_dict`) y le pide al host convocar,
votar o escribir. Todo es O(J) con J <= 4 jugadores, salvo el chat (O(M)
con M <= MAX_MENSAJES_REUNION mensajes).
"""

from dataclasses import dataclass

from src.core.balance import (
    COOLDOWN_REUNION, DURACION_REUNION, DURACION_RESULTADO_REUNION, JUGADORES_MINIMOS_VICTORIA_IMPOSTOR,
    MAX_LARGO_MENSAJE_REUNION, MAX_MENSAJES_REUNION,
)

SALTAR = "saltar"  # voto en blanco: no expulsar a nadie

# Lo que un invitado le pide al host (mensaje REUNION, campo "evento").
CONVOCAR = "convocar"
VOTAR = "votar"
ESCRIBIR = "chat"

# Cómo terminó una votación.
EXPULSADO = "expulsado"  # alguien tuvo más votos que nadie (y que los saltos)
EMPATE = "empate"  # los más votados empataron (también con saltar)
SALTADA = "saltada"  # ganó saltar
SIN_VOTOS = "sin_votos"  # nadie votó

# Quién ganó la partida Online por votación.
GANA_TRIPULACION = "tripulacion"
GANA_IMPOSTOR = "impostor"


def contar_votos(votos):
    """`votos`: {votante: objetivo (índice) o SALTAR}; solo los emitidos.
    Retorna (expulsado o None, motivo, conteo {objetivo: votos})."""
    conteo = {}
    for objetivo in votos.values():
        conteo[objetivo] = conteo.get(objetivo, 0) + 1
    if not conteo:
        return None, SIN_VOTOS, conteo
    maximo = max(conteo.values())
    primeros = [objetivo for objetivo, cantidad in conteo.items() if cantidad == maximo]
    if len(primeros) > 1:
        return None, EMPATE, conteo
    if primeros[0] == SALTAR:
        return None, SALTADA, conteo
    return primeros[0], EXPULSADO, conteo


def limpiar_mensaje(texto):
    """Un renglón imprimible de a lo sumo MAX_LARGO_MENSAJE_REUNION
    caracteres, o "" si no queda nada."""
    if not isinstance(texto, str):
        return ""
    texto = "".join(c if c.isprintable() else " " for c in texto)
    return " ".join(texto.split())[:MAX_LARGO_MENSAJE_REUNION]


class Reunion:
    """Una reunión en curso: reloj, votos y chat."""

    def __init__(self, convocante, votantes, duracion=DURACION_REUNION):
        self.convocante = convocante
        self.candidatos = tuple(sorted(votantes))  # a quién se puede votar (los no expulsados)
        self.votantes = set(votantes)  # quién puede votar todavía (conectados, no expulsados)
        self.duracion = duracion
        self.restante = duracion
        self.votos = {}  # votante -> objetivo o SALTAR
        self.chat = []  # [(autor, texto)], los últimos MAX_MENSAJES_REUNION

    def votar(self, votante, objetivo):
        """Un voto por jugador y no se cambia. True si se contó."""
        if self.terminada or votante not in self.votantes or votante in self.votos:
            return False
        if objetivo != SALTAR and objetivo not in self.candidatos:
            return False
        self.votos[votante] = objetivo
        return True

    def escribir(self, autor, texto):
        """Agrega un mensaje al chat; False si queda vacío o no puede escribir."""
        texto = limpiar_mensaje(texto)
        if not texto or self.terminada or autor not in self.candidatos:
            return False
        self.chat.append((autor, texto))
        del self.chat[:-MAX_MENSAJES_REUNION]
        return True

    def olvidar(self, indice):
        """Se desconectó: ya no se espera su voto (el que emitió, cuenta)."""
        self.votantes.discard(indice)

    def actualizar(self, dt):
        self.restante = max(0.0, self.restante - dt)

    @property
    def terminada(self):
        """Se acabó el minuto o ya votaron todos los que podían."""
        return self.restante <= 0.0 or self.votantes <= set(self.votos)

    def resultado(self):
        return contar_votos(self.votos)


class ControlReuniones:
    """El botón REPORTAR, la reunión en curso, su resultado y los expulsados.
    Lo tiene el host; el ESTADO lleva `a_dict()` a los invitados."""

    def __init__(self, recarga=COOLDOWN_REUNION, duracion=DURACION_REUNION,
                 duracion_resultado=DURACION_RESULTADO_REUNION):
        self.recarga = recarga
        self.duracion = duracion
        self.duracion_resultado = duracion_resultado
        self.recarga_restante = recarga  # la primera también espera: nadie sabe nada al empezar
        self.reunion = None
        self.resultado = None  # el de la última votación, mientras se muestra
        self.resultado_restante = 0.0
        self.expulsados = set()
        self.impostor_descubierto = False
        self.numero = 0  # reuniones convocadas: el invitado nota cuándo empieza otra
        self.fin = None  # GANA_TRIPULACION o GANA_IMPOSTOR: la partida terminó
        self.impostor = None  # índice del impostor, que se revela al terminar

    @property
    def en_curso(self):
        """Hay reunión, se está mostrando su resultado o terminó la partida:
        el mundo espera."""
        return self.fin is not None or self.reunion is not None or self.resultado_restante > 0.0

    def puede_convocar(self, indice, activos):
        """`activos`: índices de los jugadores conectados."""
        votantes = [i for i in activos if i not in self.expulsados]
        return (not self.en_curso and not self.impostor_descubierto and self.recarga_restante <= 0.0
                and indice in votantes and len(votantes) >= 2)

    def convocar(self, indice, activos):
        """Empieza una reunión si se puede. True si empezó."""
        if not self.puede_convocar(indice, activos):
            return False
        self.reunion = Reunion(indice, [i for i in activos if i not in self.expulsados], self.duracion)
        self.resultado = None
        self.numero += 1
        return True

    def votar(self, indice, objetivo):
        return self.reunion is not None and self.reunion.votar(indice, objetivo)

    def escribir(self, indice, texto):
        return self.reunion is not None and self.reunion.escribir(indice, texto)

    def olvidar(self, indice):
        if self.reunion is not None:
            self.reunion.olvidar(indice)

    def actualizar(self, dt, es_impostor=lambda indice: False, total=0):
        """El reloj de la reunión, el del resultado o el del botón (uno a la
        vez). `total`: jugadores de la partida (para saber si gana el impostor)."""
        if self.fin is not None:
            return  # la partida terminó: nada más corre
        if self.reunion is not None:
            self.reunion.actualizar(dt)
            if self.reunion.terminada:
                self._cerrar(es_impostor, total)
        elif self.resultado_restante > 0.0:
            self.resultado_restante = max(0.0, self.resultado_restante - dt)
        else:
            self.recarga_restante = max(0.0, self.recarga_restante - dt)

    def _cerrar(self, es_impostor, total=0):
        expulsado, motivo, _ = self.reunion.resultado()
        era_impostor = expulsado is not None and bool(es_impostor(expulsado))
        impostor = next((i for i in self.reunion.candidatos if es_impostor(i)), None)
        if expulsado is not None:
            self.expulsados.add(expulsado)
            self.impostor_descubierto = self.impostor_descubierto or era_impostor
        if era_impostor:
            self.fin, self.impostor = GANA_TRIPULACION, expulsado
        elif (expulsado is not None and impostor is not None and total >= JUGADORES_MINIMOS_VICTORIA_IMPOSTOR
              and total - len(self.expulsados) <= 2):
            self.fin, self.impostor = GANA_IMPOSTOR, impostor  # quedan él y uno más
        self.resultado = {"exp": expulsado, "mot": motivo, "imp": era_impostor,
                          "votos": sorted([votante, objetivo] for votante, objetivo in self.reunion.votos.items())}
        self.reunion = None
        self.resultado_restante = self.duracion_resultado
        self.recarga_restante = self.recarga

    def a_dict(self):
        """Lo que viaja en el ESTADO (claves cortas, solo listas y números)."""
        datos = {"rcd": round(self.recarga_restante, 2), "exp": sorted(self.expulsados),
                 "desc": self.impostor_descubierto, "n": self.numero}
        if self.reunion is not None:
            r = self.reunion
            datos["reu"] = {"t": round(r.restante, 2), "dur": r.duracion, "conv": r.convocante,
                            "cand": list(r.candidatos), "vot": sorted(r.votos), "chat": [list(m) for m in r.chat]}
        elif self.resultado is not None and self.resultado_restante > 0.0:
            datos["res"] = dict(self.resultado, tr=round(self.resultado_restante, 2))
        if self.fin is not None:
            datos["fin"] = self.fin
            datos["impostor"] = self.impostor
            if self.resultado is not None:
                datos["res"] = dict(self.resultado, tr=0)  # los votos, para la pantalla final
        return datos


@dataclass(frozen=True)
class VistaReunion:
    """Lo que Main dibuja y consulta, igual en el host y en el invitado."""

    recarga: float = COOLDOWN_REUNION  # s que faltan para poder reportar
    expulsados: tuple = ()
    impostor_descubierto: bool = False
    numero: int = 0
    activa: bool = False  # hay votación
    restante: float = 0.0
    duracion: float = DURACION_REUNION
    convocante: int | None = None
    candidatos: tuple = ()
    votaron: tuple = ()
    chat: tuple = ()  # ((autor, texto), ...)
    expulsado: int | None = None  # resultado (mientras se muestra)
    motivo: str | None = None
    era_impostor: bool = False
    votos: tuple = ()  # ((votante, objetivo), ...) revelados al final
    resultado_restante: float = 0.0
    fin: str | None = None  # GANA_TRIPULACION o GANA_IMPOSTOR
    impostor: int | None = None  # quién era (se revela al terminar)

    @property
    def mostrando_resultado(self):
        return self.motivo is not None and self.resultado_restante > 0.0 and self.fin is None

    @property
    def en_curso(self):
        return self.fin is not None or self.activa or self.mostrando_resultado


def _numero(valor, por_defecto=0.0):
    if isinstance(valor, bool) or not isinstance(valor, (int, float)) or valor != valor:
        return por_defecto
    return max(0.0, min(1e4, float(valor)))


def _indice(valor):
    return valor if isinstance(valor, int) and not isinstance(valor, bool) and 0 <= valor < 16 else None


def _indices(valores):
    if not isinstance(valores, list):
        return ()
    return tuple(i for i in (_indice(v) for v in valores) if i is not None)


def _objetivo(valor):
    return SALTAR if valor == SALTAR else _indice(valor)


def vista_de_dict(datos):
    """VistaReunion a partir de `a_dict()` (lo que llega en el ESTADO).
    Tolera datos rotos: lo que no tiene la forma esperada se descarta."""
    if not isinstance(datos, dict):
        return VistaReunion()
    campos = {
        "recarga": _numero(datos.get("rcd"), COOLDOWN_REUNION),
        "expulsados": _indices(datos.get("exp")),
        "impostor_descubierto": datos.get("desc") is True,
        "numero": int(_numero(datos.get("n"))),
    }
    reunion = datos.get("reu")
    if isinstance(reunion, dict):
        chat = []
        for mensaje in reunion.get("chat") if isinstance(reunion.get("chat"), list) else []:
            if isinstance(mensaje, list) and len(mensaje) == 2 and _indice(mensaje[0]) is not None:
                texto = limpiar_mensaje(mensaje[1])
                if texto:
                    chat.append((mensaje[0], texto))
        campos.update(activa=True, restante=_numero(reunion.get("t")),
                      duracion=_numero(reunion.get("dur"), DURACION_REUNION) or DURACION_REUNION,
                      convocante=_indice(reunion.get("conv")), candidatos=_indices(reunion.get("cand")),
                      votaron=_indices(reunion.get("vot")), chat=tuple(chat[-MAX_MENSAJES_REUNION:]))
    if datos.get("fin") in (GANA_TRIPULACION, GANA_IMPOSTOR):
        campos.update(fin=datos["fin"], impostor=_indice(datos.get("impostor")))
    resultado = datos.get("res")
    if isinstance(resultado, dict) and resultado.get("mot") in (EXPULSADO, EMPATE, SALTADA, SIN_VOTOS):
        votos = []
        for par in resultado.get("votos") if isinstance(resultado.get("votos"), list) else []:
            if isinstance(par, list) and len(par) == 2 and _indice(par[0]) is not None and _objetivo(par[1]) is not None:
                votos.append((par[0], _objetivo(par[1])))
        expulsado = _indice(resultado.get("exp"))
        campos.update(expulsado=expulsado, motivo=resultado["mot"] if expulsado is not None or resultado["mot"] != EXPULSADO else EMPATE,
                      era_impostor=resultado.get("imp") is True and expulsado is not None, votos=tuple(votos),
                      resultado_restante=_numero(resultado.get("tr")))
    return VistaReunion(**campos)
