"""Adaptador de sesión para el modo Online de Civitas.

Conecta el juego existente (Main.py, que ya maneja la partida local)
con la red (Online/servidor.py y Online/cliente.py). Main.py llama una
vez por frame a `sesion.adaptador_red.actualizar(...)` (y en la ciudad
también a `actualizar_ciudad(...)`); el adaptador puede cambiar la
escena, la arena, la mazmorra y el fundido que devuelve.

Arquitectura: HOST AUTORITATIVO + ESPEJO EN EL INVITADO

    - El host corre la partida completa (enemigos, jefe, daño, colapso,
      decisiones). El pedido (InputJugador) de cada invitado le llega
      por red y se aplica a su jugador como si fuera un control local
      (EntradaRed).
    - En cada frame el host manda un ESTADO completo: escena, zona,
      semilla de la mazmorra, cuarto actual, cuartos limpios, jugadores,
      enemigos, proyectiles enemigos, jefe, terminal de decisión, colapso
      e historial de decisiones. Cada estado se basta solo: si se pierde
      uno, el siguiente corrige todo (sincronización por estado, no por
      eventos sueltos).
    - El invitado NO simula enemigos ni jefe: los "congela" (modo espejo)
      y copia del estado su posición, vida y escudo. Sí mueve a su propio
      jugador sin esperar a la red (su posición manda) y a los demás con
      el último pedido que mandaron, solo para verlos caminar y disparar
      entre un estado y el siguiente.
    - Mismo mapa en las dos PCs: la mazmorra se genera con la semilla que
      elige el host (Mazmorra(..., semilla=...)) y el invitado cruza a los
      mismos cuartos, por la misma puerta y en el mismo orden.
    - Si el invitado aprieta E en una puerta, Main.py entra por su cuenta:
      el adaptador lo deshace y se lo pide al host (ENTRAR_MAZMORRA); el
      host valida y los lleva a todos.
    - Un error de red o de sincronización nunca cierra el juego: se anota
      en Online/errores_online.log (Online/registro_errores.py) y se sigue
      con el siguiente frame.

Cada jugador se identifica por su ÍNDICE en `jugadores` (0 = host). La
red usa ids de conexión (0..3); `ids_red[indice]` es el id de cada uno
(el lobby los fija al iniciar: Online/lobby.py). Con ese mismo orden,
cada PC viste a cada jugador con la apariencia de su nodo en el grafo
de sala (_vestir_jugadores); no viaja en el ESTADO porque no cambia
durante la partida. Igual con el impostor que sorteó el host al iniciar
(_asignar_impostor): llega en INICIAR y queda en la sesión y en su jugador.
"""

import functools
import math
import random
import time

import pygame

from Online import registro_errores
from Online.sabotaje import Sabotaje
from Online.reunion import CONVOCAR, ESCRIBIR, SALTAR, VOTAR, ControlReuniones, VistaReunion, limpiar_mensaje, vista_de_dict
from Online.post_sabotaje import ControlSabotajes, VistaSabotaje
from Online.post_sabotaje import vista_de_dict as vista_sabotaje_de_dict
from Online.protocolo import (
    INPUT, ESTADO, DESCONEXION, ENTRAR_MAZMORRA, CAMBIO_ESCENA, CAMBIO_CUARTO,
    DECISION_NAV, HISTORIA, REUNION, SABOTAJE, crear_mensaje, serializar, deserializar_buffer, msg_estado, msg_input,
    msg_cambio_escena, msg_cambio_cuarto, msg_entrar_mazmorra, ROLES,
)
from src.core import assets
from src.core.balance import EFECTOS_POST_SABOTAJE_FRENADO, EFECTOS_POST_SABOTAJE_VIRAL, SALTOS_CORRECCION_REDENCION
from src.core.apariencia import Apariencia
from src.core.balance import DURACION_TERMINAL_HISTORIA
from src.core.colapso import COLAPSO_MAXIMO
from src.core.entrada import EntradaMando, EntradaTeclado, InputJugador
from src.core.equipo import revivir_caidos, todos_caidos
from src.core.escenas import ESCENAS_DE_COMBATE, Escena
from src.dungeon import ciudad_mapa
from src.dungeon.arena_jefe import ArenaJefe
from src.dungeon.charco import Charco
from src.dungeon.cuarto import FASE_DECISION
from src.dungeon.grafo_ciudad import EDIFICIOS, ZONA_FINAL
from src.dungeon.mazmorra import Mazmorra
from src.dungeon.mazmorra_final import EN_COMBATE, VICTORIA
from src.dungeon.mazmorra_jugable import MazmorraJugable, ubicar_en_fila
from src.entities.enemigos import crear_enemigo
from src.entities.projectile import Proyectil, ProyectilConEstela
from src.entities.tipos_enemigo import TipoEnemigo
from src.ui.terminal_decision import (
    CONFIRMAR, DERECHA, DETONACION, IZQUIERDA, PURIFICACION_EXITOSA, TerminalDecision,
    construir_arbol_publicacion,
)
from src.ui.pantalla_resultado import ResultadoMazmorra

# Se sube cuando cambia lo que viaja por la red: el invitado la manda en su
# INPUT y el host en el ESTADO; si no coinciden, Main avisa que hay PCs con
# otro código (p. ej. una laptop sin actualizar).
VERSION_ESTADO = 4  # 4: viaja la vida de las coberturas ("cob")
INTERVALO_REPORTE_CIUDAD_S = 1 / 30  # el invitado avisa su posición en la ciudad ~30 veces por s
REPETIR_PEDIDO_ZONA_S = 0.5  # no repetir el mismo pedido de entrada antes de esto
MAX_PROYECTILES_RED = 120  # tope de proyectiles enemigos por estado (el jefe usa hasta 40)
UMBRAL_RECONCILIACION_PX = 150  # aplicar_estado_remoto: corrige al jugador local si se aleja más
DURACION_AVISO_RED = 3.0  # s de los avisos "J2 se desconectó" en la mazmorra
TEXTO_HOST_PERDIDO = "Se perdió la conexión con el anfitrión"
RESULTADOS_DECISION = (PURIFICACION_EXITOSA, DETONACION)
# Evento HISTORIA con el que un invitado avisa que abrió o cerró una escena
# de la historia (tarjeta, diálogo, cinemática): en combate el mundo lo espera.
LECTURA = "lectura"
MENU = "menu"  # mismo valor que Main.MENU: volver al menú principal
# Dónde se puede apretar REPORTAR: con el mundo en marcha (no en el resultado
# de una mazmorra ni en los finales).
ESCENAS_REUNION = (Escena.CIUDAD, Escena.MAZMORRA, Escena.DECISION, Escena.JEFE)
# Dónde el impostor puede apretar SABOTEAR (en la terminal ya hay una decisión).
ESCENAS_SABOTAJE = (Escena.CIUDAD, Escena.MAZMORRA, Escena.JEFE)
TEXTO_VERSION_INVITADO = "J{numero} tiene otra versión del juego: copien el mismo código en todas las PCs"
TEXTO_VERSION_HOST = "El host tiene otra versión del juego: copien el mismo código en todas las PCs"


def posts_sabotaje():
    """Las publicaciones del botón SABOTEAR (content/campaign.json), iguales en todas las PCs."""
    from src.story import contenido
    return contenido.cargar().get("sabotajes") or []


# =========================================================================
# Datos que llegan por red: nunca se confía en su tipo
# =========================================================================

def _numero(valor, minimo=-1e6, maximo=1e6):
    """float finito acotado a [minimo, maximo], o None si no es un número."""
    if isinstance(valor, bool) or not isinstance(valor, (int, float)):
        return None
    valor = float(valor)
    if not math.isfinite(valor):
        return None
    return max(minimo, min(maximo, valor))


def _entero(valor):
    return valor if isinstance(valor, int) and not isinstance(valor, bool) else None


def _par(valor):
    """(x, y) en float desde una tupla, lista o Vector2; None si no es un par de números finitos."""
    if valor is None:
        return None
    try:
        x, y = valor[0], valor[1]
    except (TypeError, IndexError, KeyError):
        return None
    x, y = _numero(x), _numero(y)
    return None if x is None or y is None else (x, y)


def _escena_de(nombre):
    try:
        return Escena[nombre]
    except (KeyError, TypeError):
        return None


def _zona_normal(zona):
    return zona in EDIFICIOS and zona != ZONA_FINAL


def _mover_a(cuerpo, x, y, limites=None):
    """Pone el centro de un jugador o enemigo en (x, y) sin tocar su
    velocidad (así sigue animándose). Con `limites`, no sale del cuarto."""
    cuerpo.posicion.update(x, y)
    cuerpo.rect.center = (round(x), round(y))
    if limites is not None and not limites.contains(cuerpo.rect):
        cuerpo.rect.clamp_ip(limites)
        cuerpo.posicion.update(cuerpo.rect.center)


# =========================================================================
# Input por red
# =========================================================================

def serializar_input(pedido):
    """Convierte un InputJugador (o un _InputRed) en un dict serializable.

    Campos: dirección de movimiento (dx, dy), si está disparando, punto de
    apuntado del mouse en el mundo (px, py), dirección de apuntado del
    stick (ax, ay), y los pulsos de habilidad y dash.
    """
    if hasattr(pedido, "movimiento"):
        movimiento = _par(pedido.movimiento) or (0.0, 0.0)
        punto = _par(pedido.punto_apuntado)
        apuntado = _par(getattr(pedido, "direccion_apuntado", None))
    else:  # _InputRed: direccion y punto son Vector2 o None
        movimiento = _par(getattr(pedido, "direccion", None)) or (0.0, 0.0)
        punto = _par(getattr(pedido, "punto", None))
        apuntado = _par(getattr(pedido, "apuntado", None))
    return {
        "dx": round(movimiento[0], 3),
        "dy": round(movimiento[1], 3),
        "disparando": bool(pedido.disparando),
        "px": round(punto[0], 1) if punto else None,
        "py": round(punto[1], 1) if punto else None,
        "ax": round(apuntado[0], 3) if apuntado else None,
        "ay": round(apuntado[1], 3) if apuntado else None,
        "habilidad": bool(pedido.habilidad),
        "dash": bool(pedido.dash),
    }


def deserializar_input(datos):
    """Reconstruye un _InputRed (namedtuple-like) desde un dict de red."""
    if not isinstance(datos, dict):
        datos = {}
    return _InputRed(
        dx=_numero(datos.get("dx"), -1.0, 1.0) or 0.0,
        dy=_numero(datos.get("dy"), -1.0, 1.0) or 0.0,
        disparando=bool(datos.get("disparando", False)),
        px=_numero(datos.get("px")),
        py=_numero(datos.get("py")),
        habilidad=bool(datos.get("habilidad", False)),
        dash=bool(datos.get("dash", False)),
        ax=_numero(datos.get("ax"), -1.0, 1.0),
        ay=_numero(datos.get("ay"), -1.0, 1.0),
    )


class _InputRed:
    """Sustituto ligero de InputJugador para datos que llegan por red."""

    def __init__(self, dx=0, dy=0, disparando=False, px=None, py=None,
                 habilidad=False, dash=False, ax=None, ay=None):
        self.direccion = pygame.Vector2(dx, dy) if (dx or dy) else None
        self.disparando = disparando
        self.punto = pygame.Vector2(px, py) if px is not None and py is not None else None
        self.apuntado = pygame.Vector2(ax, ay) if ax is not None and ay is not None and (ax or ay) else None
        self.habilidad = habilidad
        self.dash = dash


def _input_jugador(datos, habilidad=False, dash=False):
    """InputJugador listo para JugadorBase.manejar_input() desde un dict de
    red; los pulsos (habilidad, dash) los decide quien llama."""
    dx = _numero(datos.get("dx"), -1.0, 1.0) or 0.0
    dy = _numero(datos.get("dy"), -1.0, 1.0) or 0.0
    largo = math.hypot(dx, dy)
    if largo > 1.0:
        dx, dy = dx / largo, dy / largo
    px, py = _numero(datos.get("px")), _numero(datos.get("py"))
    ax, ay = _numero(datos.get("ax"), -1.0, 1.0), _numero(datos.get("ay"), -1.0, 1.0)
    return InputJugador(
        movimiento=(dx, dy),
        punto_apuntado=(px, py) if px is not None and py is not None else None,
        direccion_apuntado=(ax, ay) if ax is not None and ay is not None and (ax or ay) else None,
        disparando=bool(datos.get("disparando")),
        habilidad=bool(habilidad),
        dash=bool(dash),
    )


_CLAVES_INPUT = ("dx", "dy", "disparando", "px", "py", "ax", "ay", "habilidad", "dash", "nh", "nd")


def _input_publico(datos):
    """Solo los campos del pedido (sin la posición ni el lugar del que lo mandó)."""
    return {clave: datos.get(clave) for clave in _CLAVES_INPUT}


class _Pulsos:
    """Convierte los contadores de pulsos de un jugador remoto (nh, nd:
    cuántas veces apretó habilidad / dash) en pulsos de un frame. Así un
    pulso no se pierde si dos pedidos llegan en el mismo frame, ni se
    repite si el mismo estado se lee dos veces."""

    def __init__(self):
        self._vistos = {}  # (jugador, clave) -> último contador entregado
        self._pendientes = {}  # (jugador, clave) -> pulso booleano sin contador

    def anotar(self, jugador, datos):
        """Pedidos sin contador: el pulso booleano queda pendiente hasta tomarlo."""
        for contador, pulso in (("nh", "habilidad"), ("nd", "dash")):
            if _entero(datos.get(contador)) is None and datos.get(pulso):
                self._pendientes[(jugador, pulso)] = True

    def tomar(self, jugador, datos, contador, pulso):
        valor = _entero(datos.get(contador))
        if valor is None:
            return self._pendientes.pop((jugador, pulso), False)
        visto = self._vistos.get((jugador, contador))
        self._vistos[(jugador, contador)] = valor
        # El primer dato (o un contador que volvió a 0: el otro reinició el juego) no es un pulso.
        return visto is not None and valor > visto

    def olvidar(self, jugador):
        for clave in [c for c in self._vistos if c[0] == jugador]:
            del self._vistos[clave]
        for clave in [c for c in self._pendientes if c[0] == jugador]:
            del self._pendientes[clave]


# =========================================================================
# Estado del juego por red
# =========================================================================

def _datos_jugador(jugador):
    return {
        "x": round(jugador.posicion.x, 1),
        "y": round(jugador.posicion.y, 1),
        "vida": jugador.vida,
        "vida_max": jugador.vida_maxima,
        "caminando": bool(getattr(jugador, "caminando_en_ciudad", False)),
    }


def _datos_extra(jugador):
    """Lo que el HUD y el dibujo del otro necesitan además de posición y vida."""
    mirada = jugador.direccion_mirada
    return {
        "carga": round(float(jugador.carga_habilidad), 3),
        "mx": round(mirada.x, 3),
        "my": round(mirada.y, 3),
        "inv": round(jugador.invulnerabilidad.tiempo_restante, 3),
    }


def _datos_enemigo(enemigo, indice):
    tipo = getattr(enemigo, "tipo", None)
    posicion = getattr(enemigo, "posicion", None)
    x, y = (posicion.x, posicion.y) if posicion is not None else enemigo.rect.center
    return {
        "id": getattr(enemigo, "_id_red", indice),
        "tp": tipo.value if isinstance(tipo, TipoEnemigo) else None,
        "x": round(x, 1),
        "y": round(y, 1),
        "vida": enemigo.vida,
        "vmax": getattr(enemigo, "vida_maxima", enemigo.vida),
        "vivo": bool(enemigo.vivo),
        "esc": bool(getattr(enemigo, "escudo_anonimato", False)),
    }


def serializar_estado(jugadores, escenario, colapso, escena_nombre="CIUDAD", zona=None, cuarto_idx=0):
    """Snapshot base del estado: escena, jugadores, colapso y enemigos.

    El colapso va exacto (sin redondear): Escena DERROTA se decide con
    round(valor, 1) >= 100 y un redondeo aquí podía mandar al invitado a
    la derrota antes que al host."""
    estado = {
        "t": time.time(),
        "escena": escena_nombre,
        "zona": zona,
        "cuarto_idx": cuarto_idx,
        "jugadores": [_datos_jugador(j) for j in jugadores],
        "colapso": float(colapso.valor) if colapso is not None else 0.0,
    }
    if escenario is not None and hasattr(escenario, "enemigos"):
        estado["enemigos"] = [_datos_enemigo(e, i) for i, e in enumerate(escenario.enemigos)]
    return estado


def aplicar_estado_remoto(estado, jugadores, escenario=None, colapso=None, id_local=1):
    """Aplica un snapshot recibido por red a los jugadores y mundo locales.

    Versión simple (sin espejo): los jugadores remotos toman la posición
    del host, el local solo se corrige si se alejó más de
    UMBRAL_RECONCILIACION_PX, la vida la manda el host para todos y los
    enemigos se emparejan por id. `vivo` es una propiedad (vida > 0): se
    cambia la vida, nunca `vivo`."""
    datos_jugadores = estado.get("jugadores") if isinstance(estado, dict) else None
    for i, datos in enumerate(datos_jugadores or []):
        if i >= len(jugadores) or not isinstance(datos, dict):
            continue
        j = jugadores[i]
        x, y = _numero(datos.get("x")), _numero(datos.get("y"))
        if x is not None and y is not None:
            lejos = math.hypot(j.posicion.x - x, j.posicion.y - y) > UMBRAL_RECONCILIACION_PX
            if i != id_local or lejos:
                _mover_a(j, x, y)
        if i != id_local:
            j.caminando_en_ciudad = bool(datos.get("caminando", False))
        vida = _numero(datos.get("vida"))
        if vida is not None:
            j.vida = vida

    valor = _numero(estado.get("colapso"), 0.0, COLAPSO_MAXIMO) if isinstance(estado, dict) else None
    if colapso is not None and valor is not None:
        colapso.valor = valor

    datos_enemigos = estado.get("enemigos") if isinstance(estado, dict) else None
    if escenario is None or not hasattr(escenario, "enemigos") or not isinstance(datos_enemigos, list):
        return
    enemigos = list(escenario.enemigos)
    por_id = {getattr(e, "_id_red", i): e for i, e in enumerate(enemigos)}
    for i, datos in enumerate(datos_enemigos):
        if not isinstance(datos, dict):
            continue
        clave = _entero(datos.get("id"))
        enemigo = por_id.get(clave if clave is not None else i)
        if enemigo is None:
            continue
        vida = _numero(datos.get("vida"))
        if vida is not None:
            enemigo.vida = vida
        if datos.get("vivo") is False and enemigo.vida > 0:
            enemigo.vida = 0
        x, y = _numero(datos.get("x")), _numero(datos.get("y"))
        if x is not None and y is not None:
            _mover_a(enemigo, x, y)


def _datos_proyectil(proyectil):
    color = tuple(proyectil.color[:3])
    return [
        round(proyectil.posicion.x, 1), round(proyectil.posicion.y, 1),
        round(proyectil.direccion.x, 3), round(proyectil.direccion.y, 3),
        round(float(proyectil.velocidad), 1), proyectil.danio, proyectil.rect.width,
        color[0], color[1], color[2], 1 if isinstance(proyectil, ProyectilConEstela) else 0,
    ]


def _proyectil_desde(datos):
    """Proyectil enemigo de adorno en el invitado (el daño real lo calcula el host)."""
    if not isinstance(datos, list) or len(datos) != 11:
        return None
    x, y, dx, dy, velocidad, danio = (_numero(v) for v in datos[:6])
    tamanio = _entero(datos[6])
    color = tuple(_entero(c) for c in datos[7:10])
    if None in (x, y, dx, dy, velocidad, danio, tamanio) or None in color or not 1 <= tamanio <= 200:
        return None
    color = tuple(max(0, min(255, c)) for c in color)
    centro = (round(x), round(y))
    if datos[10]:
        proyectil = ProyectilConEstela(centro, (dx, dy), velocidad, danio, color, tamanio,
                                       assets.ALFAS_ESTELA_JEFE, assets.ESPACIADO_ESTELA_JEFE)
    else:
        proyectil = Proyectil(centro, (dx, dy), velocidad, danio, color, tamanio)
    proyectil.posicion.update(x, y)
    return proyectil


def _datos_jefe(arena):
    jefe, mazmorra = arena.jefe, arena.mazmorra
    return {
        "x": round(jefe.x, 1),
        "y": round(jefe.y, 1),
        "vida": jefe.vida,
        "vmax": jefe.vida_maxima,
        "fase": jefe.fase,
        "esc": jefe.vida_escudo,
        "pausa": round(jefe.tiempo_pausa, 3),
        "dest": round(jefe.tiempo_destello, 3),
        "estado": mazmorra.estado,
        "trest": round(mazmorra.tiempo_restante, 3),
        "der": mazmorra.derrotas,
        "msg": round(mazmorra.tiempo_mensaje_derrota, 3),
        "sac": round(mazmorra.tiempo_sacudida, 3),
        "charcos": [[round(c.x, 1), round(c.y, 1), c.radio, round(c.tiempo, 3)] for c in mazmorra.charcos],
    }


def _datos_terminal(terminal):
    return {
        "nodo": terminal.nodo_actual.id,
        "idx": terminal.indice_seleccionado,
        "t": round(terminal.tiempo_restante, 3),
        "res": terminal.resultado,
    }


def _buscar_nodo(nodo, id_nodo):
    if nodo.id == id_nodo:
        return nodo
    for hijo in nodo.hijos:
        encontrado = _buscar_nodo(hijo, id_nodo)
        if encontrado is not None:
            return encontrado
    return None


def _espejar_terminal(terminal, datos):
    """La terminal del invitado muestra lo que el host navega y termina con su resultado."""
    nodo = _buscar_nodo(terminal.arbol.raiz, _entero(datos.get("nodo")))
    if nodo is not None:
        terminal.nodo_actual = nodo
    indice = _entero(datos.get("idx"))
    if indice is not None and terminal.nodo_actual.hijos:
        terminal.indice_seleccionado = indice % len(terminal.nodo_actual.hijos)
    restante = _numero(datos.get("t"), 0.0, terminal.duracion)
    if restante is not None:
        terminal.tiempo_restante = restante
    resultado = datos.get("res")
    if resultado in RESULTADOS_DECISION and terminal.resultado is None:
        terminal._terminar(resultado)


# =========================================================================
# Modo espejo: en el invitado nada hostil se simula, se copia del host
# =========================================================================

def _nada(*args, **kwargs):
    return None


def _ignorar_dano(*args, **kwargs):
    """Espejo: en el invitado los golpes no quitan vida (la vida la manda el host)."""
    return None


def _actualizar_espejo(enemigo, dt, *args, **kwargs):
    """Enemigo congelado del invitado: sin IA (ni disparos ni golpes), solo
    avanza su reloj para que el sprite siga animado."""
    enemigo.reloj += dt


def _congelar_enemigo(enemigo):
    if enemigo.__dict__.get("_espejo_red"):
        return
    enemigo.actualizar = functools.partial(_actualizar_espejo, enemigo)
    enemigo.recibir_dano = _ignorar_dano
    enemigo._espejo_red = True


def _descongelar(objeto, *nombres):
    """Quita los reemplazos del modo espejo: vuelve el método de la clase."""
    for nombre in nombres:
        objeto.__dict__.pop(nombre, None)


def _descongelar_enemigo(enemigo):
    _descongelar(enemigo, "actualizar", "recibir_dano", "_espejo_red")


def _congelar_cuarto(cuarto):
    for enemigo in cuarto.enemigos:
        _congelar_enemigo(enemigo)
    if cuarto.terminal is not None:
        _congelar_terminal(cuarto.terminal)


def _congelar_terminal(terminal):
    # Solo el host (J1) navega la decisión; el invitado la ve igual que él.
    terminal.navegar = _nada
    terminal.actualizar = _nada


def _congelar_arena(arena):
    arena.mazmorra.actualizar = _nada  # sin jefe, charcos ni reloj propios: llegan del host
    arena.jefe.recibir_dano = _ignorar_dano
    for subdito in arena.subditos:
        _congelar_enemigo(subdito)


def _etiquetar_cuarto(cuarto):
    """Numera los enemigos de un cuarto la primera vez que se ve: con la
    misma semilla ambas PCs crean los mismos enemigos en el mismo orden."""
    if cuarto.__dict__.get("_red_etiquetado"):
        return
    for indice, enemigo in enumerate(cuarto.enemigos):
        if getattr(enemigo, "_id_red", None) is None:
            enemigo._id_red = indice
    cuarto._red_etiquetado = True


# =========================================================================
# Lo mismo que hace Main.py (copiado aquí: importar Main desde Online lo
# cargaría por segunda vez cuando el juego se abre con `python Main.py`)
# =========================================================================

def _curar(jugadores):
    """Cada mazmorra (normal o final) se empieza con la vida llena (y sin dash a medias)."""
    for jugador in jugadores:
        jugador.vida = jugador.vida_maxima
        jugador.invulnerabilidad.reiniciar()
        jugador.dash.reiniciar()
        jugador.detener()


def _escenario_activo(escena, arena, mazmorra):
    return arena if escena in (Escena.JEFE, Escena.VICTORIA) else mazmorra


def _volver_a_la_ciudad(jugador, partida):
    jugador.colocar_en(partida.posicion_aparicion())
    return Escena.CIUDAD


def _crear_mazmorra(partida, zona, semilla):
    # Mismo árbol de decisión que arma el host (modo historia): la forma
    # del árbol no depende de la evidencia, así los ids coinciden.
    return MazmorraJugable(Mazmorra(partida.ciudad.reportes(zona), zona, semilla=semilla),
                           fabrica_arbol=partida.fabrica_arbol(zona),
                           duracion_terminal=DURACION_TERMINAL_HISTORIA)


def _nueva_semilla():
    return random.randrange(1, 2**31)


def _avisar_en_mazmorra(mazmorra, texto):
    if mazmorra is not None:
        mazmorra.mensaje = (texto, DURACION_AVISO_RED)


# =========================================================================
# Lectores de input (misma interfaz que src/core/entrada.py)
# =========================================================================

class _MandoFicticio:
    """Simula un mando siempre conectado para que el bucle de Main.py no falle nunca."""
    def attached(self):
        return True

    def get_axis(self, *args):
        return 0.0

    def get_button(self, *args):
        return False


def _detectar_mando():
    """Busca el primer control físico real (GameController de SDL) conectado."""
    try:
        from pygame._sdl2 import controller
        for indice in range(controller.get_count()):
            if controller.is_controller(indice):
                return controller.Controller(indice)
    except Exception:
        pass
    return None


class EntradaRed:
    """Host: input del jugador remoto que ocupa la ranura `id_jugador`
    (su índice en `jugadores`). Main.py la lee como a un control más."""

    def __init__(self, adaptador, id_jugador=1):
        self.adaptador = adaptador
        self.id_jugador = id_jugador
        self.mando = _MandoFicticio()

    def leer(self, *args, **kwargs):
        if self.adaptador is None:
            return InputJugador()
        try:
            return self.adaptador.tomar_input(self.id_jugador)
        except Exception:
            registro_errores.registrar("EntradaRed.leer")
            return InputJugador()


class EntradaTecladoRed(EntradaTeclado):
    """Host: el teclado+mouse del J1 o control de PS4 si está conectado.
    Guarda el último pedido y cuenta sus pulsos para mandárselo a los invitados."""

    def __init__(self, mando=None):
        super().__init__()
        real_mando = mando if (mando is not None and not isinstance(mando, _MandoFicticio)) else _detectar_mando()
        self.mando = real_mando if real_mando is not None else _MandoFicticio()
        self._mando_lector = EntradaMando(self.mando) if (real_mando is not None and hasattr(real_mando, "attached")) else None
        self.ultimo = None
        self.pulsos_habilidad = 0
        self.pulsos_dash = 0

    def leer(self, teclas=None, botones_mouse=None, punto_mouse=None):
        if teclas is None:
            teclas = pygame.key.get_pressed()
        if botones_mouse is None:
            botones_mouse = pygame.mouse.get_pressed()
        if punto_mouse is None and pygame.mouse.get_focused():
            punto_mouse = pygame.mouse.get_pos()

        pedido = super().leer(teclas, botones_mouse, punto_mouse)

        # Si hay control de PS4 conectado y activo, priorizarlo
        if self._mando_lector is not None and self.mando.attached():
            try:
                pedido_mando = self._mando_lector.leer()
                hay_mando = (
                    pedido_mando.movimiento != (0.0, 0.0)
                    or pedido_mando.direccion_apuntado is not None
                    or pedido_mando.disparando
                    or pedido_mando.habilidad
                    or pedido_mando.dash
                )
                if hay_mando:
                    pedido = pedido_mando
            except Exception:
                pass

        self.ultimo = pedido
        self.pulsos_habilidad += bool(pedido.habilidad)
        self.pulsos_dash += bool(pedido.dash)
        return pedido


class EntradaLocalCliente(EntradaTeclado):
    """Entrada del jugador local en la máquina invitada: lee teclado/mouse
    o control de PS4, y en cada frame manda el pedido (y su posición) al host."""

    def __init__(self, adaptador, id_jugador=1, mando=None):
        super().__init__()
        self.adaptador = adaptador
        self.id_jugador = id_jugador
        real_mando = mando if (mando is not None and not isinstance(mando, _MandoFicticio)) else _detectar_mando()
        self.mando = real_mando if real_mando is not None else _MandoFicticio()
        self._mando_lector = EntradaMando(self.mando) if (real_mando is not None and hasattr(real_mando, "attached")) else None
        self.pulsos_habilidad = 0
        self.pulsos_dash = 0

    def leer(self, teclas=None, botones_mouse=None, punto_mouse=None):
        try:
            if teclas is None:
                teclas = pygame.key.get_pressed()
            if botones_mouse is None:
                botones_mouse = pygame.mouse.get_pressed()
            if punto_mouse is None and pygame.mouse.get_focused():
                punto_mouse = pygame.mouse.get_pos()
            pedido = super().leer(teclas, botones_mouse, punto_mouse)

            if self._mando_lector is not None and self.mando.attached():
                pedido_mando = self._mando_lector.leer()
                hay_mando = (
                    pedido_mando.movimiento != (0.0, 0.0)
                    or pedido_mando.direccion_apuntado is not None
                    or pedido_mando.disparando
                    or pedido_mando.habilidad
                    or pedido_mando.dash
                )
                if hay_mando:
                    pedido = pedido_mando
        except Exception:
            registro_errores.registrar("EntradaLocalCliente.leer")
            pedido = InputJugador()

        self.pulsos_habilidad += bool(pedido.habilidad)
        self.pulsos_dash += bool(pedido.dash)
        if self.adaptador is not None:
            try:
                self.adaptador.enviar_input(pedido, (self.pulsos_habilidad, self.pulsos_dash))
            except Exception:
                registro_errores.registrar("EntradaLocalCliente.enviar")
        return pedido


class EntradaRemotaHost:
    """Invitado: ranura de un jugador remoto (el host u otro invitado).
    Devuelve el último pedido que ese jugador hizo (llega en el estado del
    host); su posición la corrige cada estado."""

    def __init__(self, adaptador, id_jugador=0):
        self.adaptador = adaptador
        self.id_jugador = id_jugador
        self.mando = _MandoFicticio()

    def leer(self, *args, **kwargs):
        if self.adaptador is None or not hasattr(self.adaptador, "input_remoto"):
            return InputJugador()
        try:
            return self.adaptador.input_remoto(self.id_jugador)
        except Exception:
            registro_errores.registrar("EntradaRemotaHost.leer")
            return InputJugador()


# =========================================================================
# Adaptadores
# =========================================================================

class _AdaptadorBase:
    """Lo común a host e invitado: referencias del frame, ids de red,
    limpieza del combate y registro de las decisiones de la partida."""

    def __init__(self, ids_red=None):
        self.ids_red = list(ids_red) if ids_red else None
        self._sesion = None
        self._jugadores = []
        self._partida = None

    def _indice_impostor(self):
        """Índice en `jugadores` del impostor de la partida, o None."""
        return next((i for i, j in enumerate(self._jugadores or ()) if getattr(j, "es_impostor", False)), None)

    def _es_impostor(self, indice):
        jugadores = self._jugadores or ()
        return 0 <= indice < len(jugadores) and bool(getattr(jugadores[indice], "es_impostor", False))

    def reunion_en_curso(self):
        """Reunión de emergencia o su resultado en pantalla: el mundo espera."""
        return self.estado_reunion().en_curso

    def expulsado(self, indice):
        """Lo expulsó una votación: ya no mueve la terminal, no vota ni convoca."""
        return indice in self.estado_reunion().expulsados

    def evento_red_en_curso(self):
        """Reunión, publicación del sabotaje o sus resultados: el mundo espera."""
        return self.reunion_en_curso() or self.estado_sabotaje().en_curso

    def post_sabotaje(self, indice_post):
        """La publicación `indice_post` del botón SABOTEAR (o None)."""
        posts = posts_sabotaje()
        return posts[indice_post] if 0 <= indice_post < len(posts) else None

    def _preparar_frame(self, sesion, partida, jugadores):
        self._sesion = sesion
        self._jugadores = jugadores
        if partida is not self._partida:
            self._partida = partida
            _envolver_partida(partida)

    def _limpiar_combate(self):
        """Lo mismo que `limpiar_combate()` de Main._jugar (proyectiles,
        números y partículas en vuelo); Main.py la deja en la sesión."""
        limpiar = getattr(self._sesion, "limpiar_combate", None)
        if callable(limpiar):
            limpiar()
            return
        proyectiles = getattr(self._sesion, "proyectiles_enemigos", None)
        if isinstance(proyectiles, list):
            proyectiles.clear()

    def _id_de_indice(self, indice):
        if self.ids_red and indice < len(self.ids_red):
            return self.ids_red[indice]
        return indice

    def _indice_de_id(self, id_red):
        if _entero(id_red) is None:
            return None
        if self.ids_red:
            return self.ids_red.index(id_red) if id_red in self.ids_red else None
        return id_red if id_red >= 0 else None


def _envolver_partida(partida):
    """Anota cada decisión aplicada (zona, resultado) en
    `partida._historial_red` y cuenta los reinicios (derrota global) en
    `partida._reinicios_red`. Solo agrega: siempre llama al original."""
    if partida.__dict__.get("_historial_red") is not None:
        return
    historial = []
    registrar_original = partida.registrar_decision
    reiniciar_original = partida.reiniciar

    def registrar_decision(zona, resultado):
        valor = registrar_original(zona, resultado)
        historial.append((zona, resultado))
        return valor

    def reiniciar():
        valor = reiniciar_original()
        historial.clear()
        partida._reinicios_red += 1
        return valor

    partida.registrar_decision = registrar_decision
    partida.reiniciar = reiniciar
    partida._historial_red = historial
    partida._reinicios_red = 0


class AdaptadorOnlineHost(_AdaptadorBase):
    """El host usa este adaptador para recibir los pedidos de los invitados,
    atender sus pedidos de entrar a un edificio y mandarles el estado."""

    def __init__(self, servidor, ids_red=None):
        super().__init__(ids_red)
        self.servidor = servidor
        self._ultimos_inputs = {}  # índice -> _InputRed (compatibilidad con recibir_input)
        self._datos_input = {}  # índice -> último dict INPUT recibido
        self._reporte_nuevo = set()  # índices con una posición aún sin aplicar
        self._pulsos = _Pulsos()
        self._solicitudes = []  # zonas que pidieron los invitados
        self._desconectados = set()  # índices cuyo invitado no está conectado
        self._contador_frames = 0
        self._intervalo_estado = 1  # se manda el estado en cada frame
        self._ultima_escena = None
        self._ultima_zona = None
        self._ultimo_cuarto = 0
        self._ultimo_lugar = None
        self._mazmorra_sembrada = None
        self._semilla = None
        self._cuarto_visto = None
        self._direccion_cruce = None
        self._arena_vista = None
        self._n_arena = 0
        self._siguiente_id_subdito = 0
        self._terminal = None  # (terminal, zona, semilla) de la última decisión
        self._fin = None  # {"zona", "sem", "res"}: la última decisión ya resuelta
        self._solicitudes_decision = []  # direcciones de navegación enviadas por invitados
        self.ultimo_actor = 0  # índice del último invitado que confirmó
        self.sabotaje = Sabotaje()  # bloqueo del impostor en la terminal de decisión: lo lleva el host
        self._leyendo = set()  # índices de invitados con una escena de la historia abierta
        self.reuniones = ControlReuniones()  # botón REPORTAR, votación y expulsados: los lleva el host
        self.sabotajes = ControlSabotajes(len(posts_sabotaje()))  # botón SABOTEAR del impostor
        self._escena = None  # la escena del último frame (dónde se puede convocar)
        self._versiones = {}  # índice -> VERSION_ESTADO que manda cada invitado en su INPUT

    # --- Mensajes ---------------------------------------------------------

    def _procesar_mensajes(self):
        """Único lugar que vacía la cola del servidor: cada mensaje va a su
        lugar (antes, varios lectores la vaciaban y se perdían mensajes)."""
        for msg in self.servidor.leer_mensajes():
            if not isinstance(msg, dict):
                continue
            tipo = msg.get("tipo")
            indice = self._indice_de_id(msg.get("id"))
            if tipo == INPUT and indice is not None and isinstance(msg.get("input"), dict):
                datos = msg["input"]
                self._datos_input[indice] = datos
                self._ultimos_inputs[indice] = deserializar_input(datos)
                self._pulsos.anotar(indice, datos)
                self._reporte_nuevo.add(indice)
                self._versiones[indice] = datos.get("v")
            elif tipo == DECISION_NAV and isinstance(msg.get("dir"), str):
                # Quien perdió la voz no decide; quien confirma carga con la decisión.
                campania = getattr(self._partida, "campania", None)
                if campania is not None and indice is not None and not campania.puede_decidir(indice):
                    continue
                if self.sabotajes.activo:
                    # La publicación del sabotaje se lleva las teclas de todos.
                    if indice is not None:
                        self.navegar_sabotaje(indice, msg["dir"])
                    continue
                # El impostor no mueve ni confirma hasta que termine su bloqueo.
                if indice is not None and not self.puede_navegar(indice):
                    continue
                if campania is not None and indice is not None and msg["dir"] == CONFIRMAR:
                    campania.registrar_actor(indice)
                    self.ultimo_actor = indice
                self._solicitudes_decision.append(msg["dir"])
            elif tipo == HISTORIA and indice is not None:
                self._aplicar_historia(indice, msg)
            elif tipo == REUNION and indice is not None:
                self._aplicar_reunion(indice, msg)
            elif tipo == SABOTAJE and indice is not None:
                self.sabotear(indice)
            elif tipo == ENTRAR_MAZMORRA and isinstance(msg.get("zona"), str):
                self._solicitudes.append(msg["zona"])
            elif tipo == DESCONEXION and indice is not None:
                self._olvidar_input(indice)

    def _aplicar_historia(self, indice, msg):
        """Decisión de la crisis de un invitado. La reputación la fija el
        host: una recompensa con clave no se cobra dos veces aunque el
        mensaje se repita, y la corrección se recalcula aquí con BFS."""
        evento = msg.get("evento")
        if evento == LECTURA:
            # Abrió o cerró una escena de la historia: en combate el mundo lo espera.
            if msg.get("ocupado"):
                self._leyendo.add(indice)
            else:
                self._leyendo.discard(indice)
            return
        campania = getattr(self._partida, "campania", None)
        if campania is None:
            return
        if evento == "aceptar":
            campania.aceptar_redencion(indice)
        elif evento == "rechazar":
            campania.rechazar_redencion(indice)
        elif evento == "fallar":
            campania.fallar_redencion(indice)
        elif evento == "reintentar":
            campania.volver_a_punto_control(indice)
        elif evento == "completar":
            for origen in msg.get("origenes") or []:
                if isinstance(origen, str) and origen in campania.red.grafo:
                    campania.red.corregir(origen, SALTOS_CORRECCION_REDENCION)
            campania.completar_redencion(indice)

    def tomar_solicitudes_decision(self):
        """Direcciones (izquierda/derecha/confirmar) que los invitados
        enviaron y aún no se aplicaron; las vacía. Main.py las aplica a la
        investigación del origen de la señal (modo historia): cualquier jugador
        de la sala puede mover el cursor o señalar, y el host, que es quien
        simula, decide qué pasa (servidor autoritativo)."""
        pendientes = [d for d in self._solicitudes_decision if d in (IZQUIERDA, DERECHA, CONFIRMAR)]
        self._solicitudes_decision.clear()
        return pendientes

    def puede_navegar(self, indice, terminal=None):
        """Terminal de decisión: el impostor no mueve ni confirma mientras dura
        su bloqueo (sorteado entre 10 y 15 s al abrirse); después elige
        normal, sin límite. Los demás navegan libres, y fuera de la terminal
        (p. ej. la investigación) nadie tiene límite. `terminal`: la que Main
        tiene abierta; con ella el bloqueo corre desde el primer frame en que
        se ve, aunque el adaptador todavía no la haya seguido."""
        if self.reuniones.en_curso or indice in self.reuniones.expulsados:
            return False  # en la reunión nadie decide; el expulsado ya no decide
        if terminal is not None:
            self.sabotaje.seguir_terminal(terminal)
        if not self.sabotaje.activo or indice != self._indice_impostor():
            return True
        return self.sabotaje.listo

    def restante_sabotaje(self):
        """Segundos que le faltan al bloqueo del impostor, o None sin terminal."""
        return self.sabotaje.restante if self.sabotaje.activo else None

    def espera_sabotaje(self):
        """Bloqueo total sorteado para la terminal abierta, o None sin terminal."""
        return self.sabotaje.espera if self.sabotaje.activo else None

    def esperando_lectura(self):
        """Índices de los invitados que siguen leyendo una escena de la historia."""
        return sorted(self._leyendo)

    # --- Reunión de emergencia (Online/reunion.py) -------------------------

    def convocar_reunion(self, indice):
        """REPORTAR de `indice`: empieza la reunión si hay impostor en juego,
        el botón está listo y el mundo está en marcha. True si empezó."""
        if self._indice_impostor() is None or self._escena not in ESCENAS_REUNION or self.sabotajes.en_curso:
            return False
        activos = [i for i in range(len(self._jugadores or ())) if i not in self._desconectados]
        return self.reuniones.convocar(indice, activos)

    # --- Botón SABOTEAR del impostor (Online/post_sabotaje.py) -------------

    def sabotear(self, indice):
        """Lanza la publicación viral si quien aprieta es el impostor (no
        expulsado), el botón está listo y el mundo está en marcha."""
        if (not self._es_impostor(indice) or indice in self.reuniones.expulsados or self._escena not in ESCENAS_SABOTAJE
                or self.reuniones.en_curso or len(self._jugadores or ()) < 2):
            return False
        return self.sabotajes.sabotear()

    def navegar_sabotaje(self, indice, direccion):
        """Tecla de `indice` en la publicación: el expulsado no elige y el
        impostor, solo después de su bloqueo. True si se aplicó."""
        if direccion not in (IZQUIERDA, DERECHA, CONFIRMAR) or indice in self.reuniones.expulsados:
            return False
        campania = getattr(self._partida, "campania", None)
        if campania is not None and not campania.puede_decidir(indice):
            return False  # quien perdió la voz en la historia tampoco decide aquí
        return self.sabotajes.navegar(direccion, self._es_impostor(indice))

    def estado_sabotaje(self):
        return vista_sabotaje_de_dict(self.sabotajes.a_dict())

    def terminal_sabotaje(self):
        return self.sabotajes.terminal

    def _aplicar_resultado_sabotaje(self, resultado, partida):
        """Una vez por publicación: si se volvió viral, sube la desinformación
        y la barra de colapso (como una incursión fallida); si la frenaron, baja."""
        campania = getattr(partida, "campania", None)
        if resultado.get("res") == PURIFICACION_EXITOSA:
            efectos = EFECTOS_POST_SABOTAJE_FRENADO
        else:
            efectos = EFECTOS_POST_SABOTAJE_VIRAL
            colapso = getattr(partida, "colapso", None)
            if colapso is not None:
                colapso.sumar_fallo()
        estado = getattr(campania, "estado", None)
        if estado is not None:
            estado.aplicar(efectos)

    def aviso_version(self):
        """Texto si algún invitado juega con otro código (o None)."""
        for indice, version in sorted(self._versiones.items()):
            if version != VERSION_ESTADO and indice not in self._desconectados:
                return TEXTO_VERSION_INVITADO.format(numero=indice + 1)
        return None

    def votar_reunion(self, indice, objetivo):
        return self.reuniones.votar(indice, objetivo)

    def escribir_reunion(self, indice, texto):
        return self.reuniones.escribir(indice, texto)

    def estado_reunion(self):
        return vista_de_dict(self.reuniones.a_dict())

    def _aplicar_reunion(self, indice, msg):
        """Pedido de un invitado; las reglas (quién vota, cuándo) las pone ControlReuniones."""
        evento = msg.get("evento")
        if evento == CONVOCAR:
            self.convocar_reunion(indice)
        elif evento == VOTAR:
            objetivo = msg.get("objetivo")
            if objetivo == SALTAR or (isinstance(objetivo, int) and not isinstance(objetivo, bool)):
                self.votar_reunion(indice, objetivo)
        elif evento == ESCRIBIR:
            self.escribir_reunion(indice, msg.get("texto"))

    def _lectores(self):
        """Quiénes leen, para el ESTADO: los invitados y el host (índice 0)."""
        host = [0] if getattr(self._sesion, "historia_ocupada", False) else []
        return sorted(set(host) | self._leyendo)

    def _seguir_sabotaje(self, escena, mazmorra, dt):
        """El bloqueo del impostor corre solo con la terminal de decisión abierta."""
        cuarto = getattr(mazmorra, "cuarto", None)
        terminal = getattr(cuarto, "terminal", None) if escena == Escena.DECISION else None
        self.sabotaje.seguir_terminal(terminal)
        self.sabotaje.actualizar(dt)

    def _olvidar_input(self, indice):
        self._datos_input.pop(indice, None)
        self._ultimos_inputs.pop(indice, None)
        self._reporte_nuevo.discard(indice)
        self._pulsos.olvidar(indice)
        self._leyendo.discard(indice)  # se fue: el mundo ya no lo espera
        self.reuniones.olvidar(indice)  # ni la votación espera su voto

    def recibir_input(self, id_jugador=1):
        """Retorna el último _InputRed de un jugador remoto (compatibilidad)."""
        self._procesar_mensajes()
        return self._ultimos_inputs.get(id_jugador)

    def tomar_input(self, indice):
        """InputJugador de este frame para el jugador remoto `indice`: el
        último pedido que mandó, con sus pulsos entregados una sola vez."""
        self._procesar_mensajes()
        datos = self._datos_input.get(indice)
        if datos is None or indice in self._desconectados:
            return InputJugador()
        return _input_jugador(
            datos,
            habilidad=self._pulsos.tomar(indice, datos, "nh", "habilidad"),
            dash=self._pulsos.tomar(indice, datos, "nd", "dash"),
        )

    # --- Frame ------------------------------------------------------------

    def actualizar(self, escena, arena, mazmorra, fundido, dt, sesion, partida, jugadores, jugador):
        """Ejecuta la sincronización autoritativa del Host en cada frame."""
        try:
            self._escena = escena
            self.reuniones.actualizar(dt, self._es_impostor, len(jugadores or ()))
            cerrado = self.sabotajes.actualizar(0.0 if self.reuniones.en_curso else dt)
            if cerrado is not None:
                self._aplicar_resultado_sabotaje(cerrado, partida)
            # En la reunión el bloqueo del impostor no corre (la terminal tampoco).
            self._seguir_sabotaje(escena, mazmorra, 0.0 if self.reuniones.en_curso else dt)
            return self._actualizar(escena, arena, mazmorra, fundido, sesion, partida, jugadores)
        except Exception:
            registro_errores.registrar("AdaptadorOnlineHost.actualizar")
            return escena, arena, mazmorra, fundido

    def _actualizar(self, escena, arena, mazmorra, fundido, sesion, partida, jugadores):
        self._preparar_frame(sesion, partida, jugadores)
        self._procesar_mensajes()
        self._actualizar_conexiones(partida, jugadores, mazmorra)

        # Main.py crea la mazmorra sin semilla (E en una puerta): se rehace
        # igual pero con una semilla conocida, así el invitado arma la misma.
        if mazmorra is not None and mazmorra is not self._mazmorra_sembrada:
            mazmorra = self._sembrar(mazmorra.mazmorra.nombre_zona, partida, jugadores)
        escena, arena, mazmorra, fundido = self._atender_solicitudes(
            escena, arena, mazmorra, fundido, partida, jugadores)

        if mazmorra is not None:
            self._seguir_cuartos(mazmorra)
            _etiquetar_cuarto(mazmorra.cuarto)
        if arena is not None:
            self._etiquetar_arena(arena)
        if escena == Escena.DECISION and mazmorra is not None and getattr(mazmorra, "cuarto", None) is not None and mazmorra.cuarto.terminal is not None:
            for d in self._solicitudes_decision:
                if d in (IZQUIERDA, DERECHA, CONFIRMAR):
                    mazmorra.cuarto.terminal.navegar(d)
            self._solicitudes_decision.clear()
        elif escena != Escena.RESULTADO:
            # Fuera de la terminal y de la investigación (modo historia,
            # escena RESULTADO) una navegación vieja no vale nada.
            self._solicitudes_decision.clear()
        if escena == Escena.MAZMORRA and mazmorra is not None and todos_caidos(jugadores):
            if self._fin is None:
                self._fin = {
                    "zona": mazmorra.mazmorra.nombre_zona,
                    "sem": self._semilla,
                    "res": DETONACION,
                    "opcion": "Derrota",
                    "antes": getattr(partida.colapso, "valor", 0.0),
                    "despues": min(1.0, getattr(partida.colapso, "valor", 0.0) + 0.2),
                }
        self._seguir_decision(escena, mazmorra)
        if escena not in ESCENAS_DE_COMBATE:
            entrada_host = (getattr(sesion, "entradas", None) or [None])[0]
            if isinstance(entrada_host, EntradaTecladoRed):
                entrada_host.ultimo = None  # sin combate no hay pedido que mostrar

        self._aplicar_posiciones(escena, arena, mazmorra, jugadores)
        self._enviar_estado(escena, arena, mazmorra, partida, jugadores)
        return escena, arena, mazmorra, fundido

    def notificar_resultado(self, resultado):
        """Anota el resultado para enviarlo de inmediato a los invitados."""
        if resultado is not None:
            zona_nombre = getattr(resultado, "zona", None)
            if not zona_nombre and self._mazmorra_sembrada is not None:
                zona_nombre = self._mazmorra_sembrada.mazmorra.nombre_zona
            self._fin = {
                "zona": zona_nombre,
                "sem": self._semilla,
                "res": getattr(resultado, "resultado", None),
                "opcion": getattr(resultado, "opcion", None),
                "antes": getattr(resultado, "colapso_antes", None),
                "despues": getattr(resultado, "colapso_despues", None),
                "txt": getattr(resultado, "explicacion", ""),
            }

    def actualizar_ciudad(self, dt, partida, jugadores, jugador):
        """En la ciudad cada invitado camina en su PC y avisa su posición:
        ya se aplicó en actualizar(). Se conserva por compatibilidad."""

    def _actualizar_conexiones(self, partida, jugadores, mazmorra):
        """Un invitado sin conexión queda caído (no se dibuja, los enemigos
        lo ignoran); al volver a conectarse revive con la vida llena."""
        conectados = self._ids_conectados()
        for indice in range(1, len(jugadores)):
            fuera = conectados is not None and self._id_de_indice(indice) not in conectados
            jugador = jugadores[indice]
            if fuera:
                if indice not in self._desconectados:
                    self._desconectados.add(indice)
                    self._olvidar_input(indice)
                    _avisar_en_mazmorra(mazmorra, f"J{indice + 1} se desconectó")
                jugador.vida = 0
            elif indice in self._desconectados:
                self._desconectados.discard(indice)
                jugador.vida = jugador.vida_maxima
                jugador.invulnerabilidad.reiniciar()
                _avisar_en_mazmorra(mazmorra, f"J{indice + 1} volvió")
        partida.jugadores_online = [j for i, j in enumerate(jugadores) if i not in self._desconectados]

    def _ids_conectados(self):
        ids_conectados = getattr(self.servidor, "ids_conectados", None)
        if not callable(ids_conectados):
            return None
        return {0, *ids_conectados()}

    def _sembrar(self, zona, partida, jugadores):
        semilla = _nueva_semilla()
        mazmorra = _crear_mazmorra(partida, zona, semilla)
        mazmorra.colocar_en_entrada(jugadores)
        self._mazmorra_sembrada = mazmorra
        self._semilla = semilla
        self._cuarto_visto = mazmorra.mazmorra.actual
        self._direccion_cruce = None
        self._fin = None
        return mazmorra

    def _atender_solicitudes(self, escena, arena, mazmorra, fundido, partida, jugadores):
        """Un invitado apretó E en una puerta: el host valida (en la ciudad,
        zona real, Alcaldía abierta) y entran todos, como con su propia E."""
        if getattr(self._sesion, "historia_ocupada", False):
            return escena, arena, mazmorra, fundido  # el host lee una escena: la entrada espera
        solicitudes, self._solicitudes = self._solicitudes, []
        if escena != Escena.CIUDAD:
            return escena, arena, mazmorra, fundido
        for zona in solicitudes:
            if zona not in EDIFICIOS or (zona == ZONA_FINAL and not partida.alcaldia_desbloqueada()):
                continue
            partida.entrar(zona)
            self._limpiar_combate()
            _curar(jugadores)
            if zona == ZONA_FINAL:
                return Escena.JEFE, ArenaJefe(partida.colapso, jugadores), None, assets.DURACION_FUNDIDO
            return Escena.MAZMORRA, None, self._sembrar(zona, partida, jugadores), assets.DURACION_FUNDIDO
        return escena, arena, mazmorra, fundido

    def _seguir_cuartos(self, mazmorra):
        """Anota por qué puerta se cruzó: el invitado cruza por la misma y
        aparece en el mismo lugar."""
        actual = mazmorra.mazmorra.actual
        if self._cuarto_visto is not None and actual != self._cuarto_visto:
            puertas = mazmorra.mazmorra.puertas(self._cuarto_visto)
            self._direccion_cruce = next((d for d, vecino in puertas.items() if vecino == actual), None)
        self._cuarto_visto = actual

    def _etiquetar_arena(self, arena):
        if arena is not self._arena_vista:
            self._arena_vista = arena
            self._n_arena += 1
        for subdito in arena.subditos:
            if getattr(subdito, "_id_red", None) is None:
                subdito._id_red = self._siguiente_id_subdito
                self._siguiente_id_subdito += 1

    def _seguir_decision(self, escena, mazmorra):
        """Recuerda la terminal mientras dura la decisión: Main.py borra la
        mazmorra al resolverla y el invitado necesita saber el resultado."""
        if escena == Escena.DECISION and mazmorra is not None and mazmorra.cuarto.terminal is not None:
            self._terminal = (mazmorra.cuarto.terminal, mazmorra.mazmorra.nombre_zona, self._semilla)
        if self._terminal is not None and self._fin is None:
            terminal, zona, semilla = self._terminal
            if terminal.resultado is not None:
                antes_val = getattr(self._partida.colapso, "valor", 0.0) if self._partida else 0.0
                self._fin = {
                    "zona": zona,
                    "sem": semilla,
                    "res": terminal.resultado,
                    "opcion": getattr(terminal, "opcion_elegida", None),
                    "antes": antes_val,
                    "despues": antes_val,
                }

    def _lugar(self, escena, arena, mazmorra):
        """Dónde está físicamente el equipo: la posición que manda un
        invitado solo se aplica si él está en el mismo lugar."""
        if escena in (Escena.MAZMORRA, Escena.DECISION) and mazmorra is not None:
            return ["MAZMORRA", self._semilla, mazmorra.mazmorra.actual]
        if escena in (Escena.JEFE, Escena.VICTORIA) and arena is not None:
            return ["JEFE", self._n_arena, None]
        return ["CIUDAD", None, None]

    def _aplicar_posiciones(self, escena, arena, mazmorra, jugadores):
        """Cada invitado manda su posición (la de su PC es la que vale): se
        aplica una vez por reporte, solo si está en el mismo lugar."""
        lugar = self._lugar(escena, arena, mazmorra)
        epoca = self._partida._reinicios_red
        escenario = _escenario_activo(escena, arena, mazmorra)
        for indice in sorted(self._reporte_nuevo):
            datos = self._datos_input.get(indice)
            if not datos or not 0 < indice < len(jugadores) or indice in self._desconectados:
                continue
            if datos.get("loc") != lugar or datos.get("ep") != epoca:
                continue
            x, y = _numero(datos.get("x")), _numero(datos.get("y"))
            if x is None or y is None:
                continue
            jugador = jugadores[indice]
            if lugar[0] == "CIUDAD":
                jugador.colocar_en((x, y))
                jugador.caminando_en_ciudad = bool(datos.get("cam"))
            elif escenario is not None:
                _mover_a(jugador, x, y, escenario.rect)
        self._reporte_nuevo.clear()

    # --- Estado -----------------------------------------------------------

    def _enviar_estado(self, escena, arena, mazmorra, partida, jugadores):
        self._contador_frames += 1
        lugar = self._lugar(escena, arena, mazmorra)
        zona, cuarto = self._zona_y_cuarto(arena, mazmorra)
        if lugar != self._ultimo_lugar or escena != self._ultima_escena:
            # Lo que el servidor le cuenta a quien se une con la partida en curso.
            self.servidor.actualizar_estado_partida(escena=escena.name, zona=zona, cuarto_idx=cuarto or 0)
            self._ultimo_lugar, self._ultima_escena, self._ultima_zona = lugar, escena, zona
            self._ultimo_cuarto = cuarto or 0
        if self._contador_frames % self._intervalo_estado:
            return
        datos = msg_estado(self.estado_completo(escena, arena, mazmorra, partida, jugadores))
        self.servidor.ultimo_snapshot_estado = datos
        self.servidor.enviar_a_todos(datos)

    @staticmethod
    def _zona_y_cuarto(arena, mazmorra):
        if mazmorra is not None:
            return mazmorra.mazmorra.nombre_zona, mazmorra.mazmorra.actual
        if arena is not None:
            return ZONA_FINAL, None
        return None, None

    def estado_completo(self, escena, arena, mazmorra, partida, jugadores):
        """Snapshot completo que se manda a los invitados (ver docstring del módulo)."""
        zona, cuarto = self._zona_y_cuarto(arena, mazmorra)
        en_mazmorra = mazmorra is not None and escena in (Escena.MAZMORRA, Escena.DECISION)
        estado = serializar_estado(jugadores, mazmorra if en_mazmorra else None, partida.colapso,
                                   escena.name, zona, cuarto or 0)
        m = mazmorra.mazmorra if mazmorra is not None else None
        estado.update({
            "v": VERSION_ESTADO,
            "ep": partida._reinicios_red,
            "loc": self._lugar(escena, arena, mazmorra),
            "ids": self.ids_red,
            "fuera": sorted(self._desconectados),
            "dec": [[z, r] for z, r in partida._historial_red],
            "ext": [_datos_extra(j) for j in jugadores],
            "sem": self._semilla if m is not None else None,
            "cu": cuarto,
            "dir": self._direccion_cruce if m is not None else None,
            "lim": sorted(m.limpiados) if m is not None else [],
            "tox": [[c, round(t, 3)] for c, t in m.toxicidad.items()] if m is not None else [],
            "arena": self._n_arena if arena is not None else None,
            "fin": self._fin,
            "res_info": self._fin,
            "cam": partida.campania.resumen_red(),  # reputación e indicadores: el host manda
            "leen": self._lectores(),
            "reu": self.reuniones.a_dict(),  # botón REPORTAR, votación en curso y expulsados
            "sbp": self.sabotajes.a_dict(),  # botón SABOTEAR y la publicación viral en curso
        })
        investigacion = getattr(self._sesion, "investigacion_activa", None)
        if escena == Escena.RESULTADO and investigacion is not None:
            estado["inv"] = investigacion.a_dict()
        if escena in ESCENAS_DE_COMBATE:
            estado["ins"] = self._pedidos(jugadores)
            proyectiles = getattr(self._sesion, "proyectiles_enemigos", None) or []
            estado["pro"] = [_datos_proyectil(p) for p in proyectiles[:MAX_PROYECTILES_RED] if p.vivo]
        if escena in ESCENAS_DE_COMBATE:
            # Vida de cada mueble del lugar, en el orden del plan (igual en todas las PCs).
            lugar = arena if arena is not None else (mazmorra if en_mazmorra else None)
            coberturas = getattr(lugar, "coberturas", None)
            if coberturas:
                estado["cob"] = [round(v, 2) for v in coberturas.vidas()]
        if arena is not None:
            estado["sub"] = [_datos_enemigo(s, i) for i, s in enumerate(arena.subditos)]
            estado["jefe"] = _datos_jefe(arena)
        if escena == Escena.DECISION and mazmorra is not None and mazmorra.cuarto.terminal is not None:
            estado["term"] = _datos_terminal(mazmorra.cuarto.terminal)
            estado["term"]["sab"] = round(self.sabotaje.restante, 2)
            estado["term"]["sabt"] = round(self.sabotaje.espera, 2)
        return estado

    def _pedidos(self, jugadores):
        """Último pedido de cada jugador (por índice) para que los demás lo
        vean moverse y disparar; None si no hay."""
        pedidos = []
        entradas = getattr(self._sesion, "entradas", None) or []
        for indice in range(len(jugadores)):
            if indice == 0:
                entrada = entradas[0] if entradas else None
                ultimo = getattr(entrada, "ultimo", None)
                if ultimo is None:
                    pedidos.append(None)
                    continue
                datos = serializar_input(ultimo)
                datos["nh"], datos["nd"] = entrada.pulsos_habilidad, entrada.pulsos_dash
                pedidos.append(datos)
            else:
                datos = self._datos_input.get(indice)
                pedidos.append(_input_publico(datos) if datos and indice not in self._desconectados else None)
        return pedidos

    def detener(self):
        self.servidor.detener()


class AdaptadorOnlineJoin(_AdaptadorBase):
    """El invitado usa este adaptador para mandar su pedido y su posición,
    recibir el estado del host y reflejarlo (modo espejo)."""

    def __init__(self, cliente, id_local=1, ids_red=None):
        super().__init__(ids_red)
        self.cliente = cliente
        self.id_local = id_local  # índice del jugador de esta PC en `jugadores`
        self._ultimo_estado = None
        self._estado_nuevo = False
        self._contador_frames = 0
        self._espejo = True  # False si se perdió el host: se sigue jugando solo
        self._semilla = None
        self._mazmorra_propia = None  # la que armó este adaptador con la semilla del host
        self._arena_propia = None
        self._arena_n = None
        self._ep_host = None
        self._pulsos = _Pulsos()
        self._contadores = (0, 0)  # pulsos propios de habilidad y dash
        self._lugar_actual = ["CIUDAD", None, None]
        self._ultimo_reporte = 0.0
        self._e_antes = False
        self._ultimo_pedido = (None, 0.0)
        self.resultado_remoto = None
        self.sabotaje_restante = None  # bloqueo del impostor según el host (con la terminal abierta)
        self.sabotaje_espera = None  # el bloqueo total que sorteó el host para esa terminal
        self.reunion = VistaReunion()  # reunión de emergencia según el host
        self.sabotaje_post = VistaSabotaje()  # publicación del botón SABOTEAR según el host
        self._terminal_post = None  # copia local (congelada) de esa publicación, para dibujarla
        self._version_host = None
        self.lectores = []  # índices que, según el host, leen una escena de la historia
        self._lectura_avisada = False  # lo último que este invitado le avisó al host

    def _conectado(self):
        return bool(getattr(self.cliente, "conectado", False))

    def puede_navegar(self, indice, terminal=None):
        """Solo para no mandar en vano: el impostor no navega mientras el host
        dice que sigue bloqueado, ni nadie en una reunión o ya expulsado.
        Quien decide de verdad es el host."""
        if self.reunion.en_curso or indice in self.reunion.expulsados:
            return False
        if indice != self._indice_impostor() or self.sabotaje_restante is None:
            return True
        return self.sabotaje_restante <= 0.0

    def restante_sabotaje(self):
        return self.sabotaje_restante

    def espera_sabotaje(self):
        return self.sabotaje_espera

    # --- Reunión de emergencia: se le pide al host (Online/reunion.py) ----

    def convocar_reunion(self, indice):
        if not self._conectado() or self.reunion.en_curso:
            return False
        self.cliente.enviar_reunion(CONVOCAR)
        return True

    def votar_reunion(self, indice, objetivo):
        if not self._conectado() or not self.reunion.activa or indice in self.reunion.votaron:
            return False
        self.cliente.enviar_reunion(VOTAR, objetivo=objetivo)
        return True

    def escribir_reunion(self, indice, texto):
        texto = limpiar_mensaje(texto)
        if not texto or not self._conectado() or not self.reunion.activa:
            return False
        self.cliente.enviar_reunion(ESCRIBIR, texto=texto)
        return True

    def estado_reunion(self):
        return self.reunion

    def sabotear(self, indice):
        if not self._conectado() or self.sabotaje_post.en_curso or self.reunion.en_curso:
            return False
        self.cliente.enviar_sabotaje()
        return True

    def navegar_sabotaje(self, indice, direccion):
        """Solo para no mandar en vano: el host decide. El impostor espera su bloqueo."""
        if not self._conectado() or not self.sabotaje_post.activo or indice in self.reunion.expulsados:
            return False
        if indice == self._indice_impostor() and self.sabotaje_post.bloqueo > 0.0:
            return False
        self.cliente.enviar_decision_nav(direccion)
        return True

    def estado_sabotaje(self):
        return self.sabotaje_post

    def terminal_sabotaje(self):
        return self._terminal_post

    def aviso_version(self):
        if self._version_host is not None and self._version_host != VERSION_ESTADO:
            return TEXTO_VERSION_HOST
        return None

    def _espejar_post(self):
        """La publicación del sabotaje se ve igual que en el host (árbol fijo,
        mismos ids): se copia cursor y reloj; nadie la navega aquí."""
        vista = self.sabotaje_post
        if not vista.activo:
            self._terminal_post = None
            return
        if self._terminal_post is None or self._terminal_post.numero_sabotaje != vista.numero:
            terminal = TerminalDecision(construir_arbol_publicacion(), vista.duracion, descender_resultados=True)
            terminal.iniciar()
            terminal.numero_sabotaje = vista.numero
            _congelar_terminal(terminal)
            self._terminal_post = terminal
        _espejar_terminal(self._terminal_post, {"nodo": vista.nodo, "idx": vista.seleccion, "t": vista.restante})

    def esperando_lectura(self):
        """Índices de los OTROS jugadores que siguen leyendo, según el host."""
        return [i for i in self.lectores if i != self.id_local]

    def _avisar_lectura(self):
        """Avisa al host cuando este jugador abre o cierra una escena de la
        historia: en combate el mundo lo espera (esperando_lectura del host)."""
        ocupado = bool(getattr(self._sesion, "historia_ocupada", False))
        if ocupado != self._lectura_avisada:
            self._lectura_avisada = ocupado
            self.enviar_historia(LECTURA, ocupado=ocupado)

    def enviar_historia(self, evento, **datos):
        """Avisa al host de una decisión de la crisis o la redención de este jugador."""
        try:
            if hasattr(self.cliente, "enviar_historia"):
                self.cliente.enviar_historia(evento, **datos)
        except Exception:
            registro_errores.registrar("AdaptadorOnlineJoin.enviar_historia")

    def enviar_decision_nav(self, direccion):
        """Notifica al host que este jugador navega o confirma en la terminal de decisión."""
        try:
            if hasattr(self.cliente, "enviar_decision_nav"):
                self.cliente.enviar_decision_nav(direccion)
        except Exception:
            registro_errores.registrar("AdaptadorOnlineJoin.enviar_decision_nav")

    # --- Envío ------------------------------------------------------------

    def enviar_input(self, pedido, contadores=None):
        """Serializa el input local (con su posición y lugar) y lo envía al host."""
        if contadores is not None:
            self._contadores = contadores
        datos = serializar_input(pedido)
        datos["nh"], datos["nd"] = self._contadores
        if 0 <= self.id_local < len(self._jugadores):
            jugador = self._jugadores[self.id_local]
            datos["x"] = round(jugador.posicion.x, 1)
            datos["y"] = round(jugador.posicion.y, 1)
            datos["cam"] = bool(getattr(jugador, "caminando_en_ciudad", False))
        datos["loc"] = self._lugar_actual
        datos["ep"] = self._ep_host
        datos["v"] = VERSION_ESTADO
        self.cliente.enviar_input(datos)

    def _pedir_zona(self, zona):
        ahora = time.monotonic()
        zona_previa, momento = self._ultimo_pedido
        if zona == zona_previa and ahora - momento < REPETIR_PEDIDO_ZONA_S:
            return
        self._ultimo_pedido = (zona, ahora)
        self.cliente.enviar_entrar_mazmorra(zona)

    # --- Recepción --------------------------------------------------------

    def _leer_mensajes(self):
        for msg in self.cliente.leer_mensajes():
            if isinstance(msg, dict) and msg.get("tipo") == ESTADO and isinstance(msg.get("estado"), dict):
                self._ultimo_estado = msg["estado"]
                self._estado_nuevo = True

    def recibir_estado(self):
        """Retorna el último estado recibido del host, o None."""
        self._leer_mensajes()
        return self._ultimo_estado

    def input_remoto(self, indice):
        """InputJugador del jugador remoto `indice` según el último estado."""
        estado = self._ultimo_estado
        if not self._espejo or not estado:
            return InputJugador()
        pedidos = estado.get("ins")
        if not isinstance(pedidos, list) or not 0 <= indice < len(pedidos) or not isinstance(pedidos[indice], dict):
            return InputJugador()
        datos = pedidos[indice]
        return _input_jugador(
            datos,
            habilidad=self._pulsos.tomar(indice, datos, "nh", "habilidad"),
            dash=self._pulsos.tomar(indice, datos, "nd", "dash"),
        )

    # --- Frame ------------------------------------------------------------

    def actualizar(self, escena, arena, mazmorra, fundido, dt, sesion, partida, jugadores, jugador):
        """Sincroniza la escena local con la del host y aplica su estado."""
        try:
            return self._actualizar(escena, arena, mazmorra, fundido, sesion, partida, jugadores, jugador)
        except Exception:
            registro_errores.registrar("AdaptadorOnlineJoin.actualizar")
            return escena, arena, mazmorra, fundido

    def _actualizar(self, escena, arena, mazmorra, fundido, sesion, partida, jugadores, jugador):
        self._preparar_frame(sesion, partida, jugadores)
        self._leer_mensajes()
        if self._espejo and not self._conectado():
            self._perder_host(arena, mazmorra, partida, jugadores)
        if not self._espejo:
            for indice, otro in enumerate(jugadores):
                if indice != self.id_local:
                    otro.vida = 0  # los remotos quedan fuera del juego
            self._lugar_actual = ["CIUDAD", None, None]
            return escena, arena, mazmorra, fundido

        self._avisar_lectura()
        escena, arena, mazmorra = self._deshacer_entrada_local(escena, arena, mazmorra)
        estado = self._ultimo_estado
        if estado is not None and self._estado_nuevo:
            self._estado_nuevo = False
            escena, arena, mazmorra, fundido = self._converger(
                estado, escena, arena, mazmorra, fundido, partida, jugadores, jugador)
            self._aplicar(estado, escena, arena, mazmorra, partida, jugadores)
        if mazmorra is not None and mazmorra is self._mazmorra_propia:
            _congelar_cuarto(mazmorra.cuarto)  # la terminal que el cuarto acaba de crear, por ejemplo
        if estado is not None:
            self._marcar_ausentes(estado, partida, jugadores)
        self._lugar_actual = self._lugar(escena, arena, mazmorra)
        return escena, arena, mazmorra, fundido

    def actualizar_ciudad(self, dt, partida, jugadores, jugador):
        """En la ciudad: avisa la posición propia al host y, con E junto a
        una puerta, le pide entrar (el host decide y lleva a todos)."""
        try:
            if not self._espejo:
                return
            ahora = time.monotonic()
            if ahora - self._ultimo_reporte >= INTERVALO_REPORTE_CIUDAD_S:
                self._ultimo_reporte = ahora
                self.enviar_input(InputJugador())
            e_apretada = bool(pygame.key.get_pressed()[pygame.K_e])
            if e_apretada and not self._e_antes:
                zona = ciudad_mapa.entrada_cercana((jugador.posicion.x, jugador.posicion.y))
                if zona is not None:
                    self._pedir_zona(zona)
            self._e_antes = e_apretada
        except Exception:
            registro_errores.registrar("AdaptadorOnlineJoin.actualizar_ciudad")

    def _lugar(self, escena, arena, mazmorra):
        if escena in (Escena.MAZMORRA, Escena.DECISION) and mazmorra is not None \
                and mazmorra is self._mazmorra_propia:
            return ["MAZMORRA", self._semilla, mazmorra.mazmorra.actual]
        if escena in (Escena.JEFE, Escena.VICTORIA) and arena is not None and arena is self._arena_propia:
            return ["JEFE", self._arena_n, None]
        return ["CIUDAD", None, None]

    def _deshacer_entrada_local(self, escena, arena, mazmorra):
        """Main.py entró solo a un edificio (E en el invitado): se vuelve a la
        ciudad y se le pide al host, que lleva a todos con la misma semilla."""
        if escena in (Escena.MAZMORRA, Escena.DECISION) and mazmorra is not None \
                and mazmorra is not self._mazmorra_propia:
            self._pedir_zona(mazmorra.mazmorra.nombre_zona)
            return Escena.CIUDAD, None, None
        if escena in (Escena.JEFE, Escena.VICTORIA) and arena is not None and arena is not self._arena_propia:
            self._pedir_zona(ZONA_FINAL)
            return Escena.CIUDAD, None, None
        return escena, arena, mazmorra

    # --- Seguir al host ---------------------------------------------------

    def _converger(self, estado, escena, arena, mazmorra, fundido, partida, jugadores, jugador):
        """Lleva al invitado a la escena, zona y cuarto donde está el host."""
        escena_host = _escena_de(estado.get("escena"))
        if escena_host is None:
            return escena, arena, mazmorra, fundido
        epoca = estado.get("ep")
        if self._ep_host is None:
            self._ep_host = epoca
        elif epoca != self._ep_host:
            # El host reinició la partida tras la derrota global: aquí también.
            self._ep_host = epoca
            escena, arena, mazmorra, fundido = self._reiniciar(partida, jugadores, jugador)

        zona, semilla = estado.get("zona"), _entero(estado.get("sem"))
        if escena_host in (Escena.MAZMORRA, Escena.DECISION) and semilla is not None and _zona_normal(zona):
            if mazmorra is None or mazmorra is not self._mazmorra_propia or self._semilla != semilla \
                    or escena not in (Escena.MAZMORRA, Escena.DECISION):
                escena, arena, mazmorra, fundido = self._entrar_mazmorra(zona, semilla, partida, jugadores)
            self._seguir_cuarto(mazmorra, estado, jugadores)
            if escena_host == Escena.DECISION:
                escena = self._seguir_decision(mazmorra, estado.get("term"))
        elif escena_host == Escena.RESULTADO:
            fin = estado.get("res_info") or estado.get("fin")
            if isinstance(fin, dict) and fin.get("res") in RESULTADOS_DECISION:
                res_val = fin.get("res")
                opcion_val = fin.get("opcion")
                antes_val = _numero(fin.get("antes"), 0.0, 1.0)
                despues_val = _numero(fin.get("despues"), 0.0, 1.0)
                if antes_val is None:
                    antes_val = getattr(partida.colapso, "valor", 0.0)
                if despues_val is None:
                    despues_val = getattr(partida.colapso, "valor", 0.0)
                zona_val = fin.get("zona") or (mazmorra.mazmorra.nombre_zona if mazmorra else partida.ubicacion)

                self.resultado_remoto = ResultadoMazmorra(
                    resultado=res_val,
                    opcion=opcion_val,
                    colapso_antes=antes_val,
                    colapso_despues=despues_val,
                    zona=zona_val,
                    texto=fin.get("txt") if isinstance(fin.get("txt"), str) else "",
                )
                self._limpiar_combate()
                self._mazmorra_propia = None
                self._semilla = None
                return Escena.RESULTADO, None, None, fundido
        elif escena_host in (Escena.JEFE, Escena.VICTORIA):
            numero = _entero(estado.get("arena"))
            if escena_host == Escena.JEFE and (arena is None or arena is not self._arena_propia
                                               or self._arena_n != numero
                                               or escena not in (Escena.JEFE, Escena.VICTORIA)):
                escena, arena, mazmorra, fundido = self._entrar_arena(numero, partida, jugadores)
        elif escena_host == Escena.CIUDAD and escena in (Escena.MAZMORRA, Escena.DECISION, Escena.JEFE, Escena.RESULTADO):
            self._limpiar_combate()
            self._mazmorra_propia = self._arena_propia = None
            self._semilla = None
            self.resultado_remoto = None
            return _volver_a_la_ciudad(jugador, partida), None, None, assets.DURACION_FUNDIDO
        return escena, arena, mazmorra, fundido

    def _reiniciar(self, partida, jugadores, jugador):
        partida.reiniciar()
        for otro in jugadores:
            _curar([otro])
            otro.carga_habilidad = 0.0
        self._limpiar_combate()
        self._mazmorra_propia = self._arena_propia = None
        self._semilla = None
        return _volver_a_la_ciudad(jugador, partida), None, None, assets.DURACION_FUNDIDO

    def _entrar_mazmorra(self, zona, semilla, partida, jugadores):
        self._limpiar_combate()
        partida.entrar(zona)
        _curar(jugadores)
        mazmorra = _crear_mazmorra(partida, zona, semilla)
        mazmorra.colocar_en_entrada(jugadores)
        # El invitado no cruza puertas por su cuenta: cruza cuando cruza el host.
        mazmorra._cruzar = _nada
        _etiquetar_cuarto(mazmorra.cuarto)
        _congelar_cuarto(mazmorra.cuarto)
        self._mazmorra_propia, self._semilla = mazmorra, semilla
        self._arena_propia = None
        return Escena.MAZMORRA, None, mazmorra, assets.DURACION_FUNDIDO

    def _entrar_arena(self, numero, partida, jugadores):
        self._limpiar_combate()
        partida.entrar(ZONA_FINAL)
        _curar(jugadores)
        arena = ArenaJefe(partida.colapso, jugadores)
        _congelar_arena(arena)
        self._arena_propia, self._arena_n = arena, numero
        self._mazmorra_propia, self._semilla = None, None
        return Escena.JEFE, arena, None, assets.DURACION_FUNDIDO

    def _seguir_cuarto(self, mazmorra, estado, jugadores):
        """Cuartos limpios, toxicidad y cuarto actual iguales a los del host."""
        m = mazmorra.mazmorra
        limpios = estado.get("lim")
        if isinstance(limpios, list):
            m.limpiados.update(c for c in limpios if _entero(c) is not None and c in m.celdas)
        toxicidad = estado.get("tox")
        if isinstance(toxicidad, list):
            for par in toxicidad:
                if isinstance(par, list) and len(par) == 2 and _entero(par[0]) in m.toxicidad:
                    valor = _numero(par[1], 0.0, 100.0)
                    if valor is not None:
                        m.toxicidad[par[0]] = valor
        cuarto = _entero(estado.get("cu"))
        if cuarto is not None and cuarto in m.celdas and cuarto != m.actual:
            self._ir_a_cuarto(mazmorra, cuarto, estado.get("dir"), jugadores)

    def _ir_a_cuarto(self, mazmorra, cuarto, direccion, jugadores):
        """Cruza por la misma puerta que el host (mismo punto de llegada); si
        el invitado estaba desfasado, salta directo a ese cuarto."""
        m = mazmorra.mazmorra
        if isinstance(direccion, str) and m.puertas(m.actual).get(direccion) == cuarto:
            MazmorraJugable._cruzar(mazmorra, direccion, jugadores)
        if m.actual != cuarto:
            m.entrar(cuarto)
            mazmorra._crear_cuarto_si_falta(cuarto)
            mazmorra._sincronizar_sellos()
            ubicar_en_fila(jugadores, mazmorra.cuarto.rect.center, (1, 0))
            mazmorra.gracia.iniciar()
        # Lo que Main.py hace con `cambio_de_cuarto` (aquí no lo vería: se
        # apaga en el próximo actualizar de la mazmorra).
        self._limpiar_combate()
        revivir_caidos(jugadores)
        for otro in jugadores:
            otro.detener()
        _etiquetar_cuarto(mazmorra.cuarto)
        _congelar_cuarto(mazmorra.cuarto)

    def _seguir_decision(self, mazmorra, datos_terminal):
        """El cuarto final queda en decisión con la terminal del host."""
        cuarto = mazmorra.cuarto
        if cuarto.terminal is None:
            # La misma que el cuarto habría abierto él solo: el árbol de la
            # historia (mismos ids y misma publicación que el host), aunque
            # el host llegue a la decisión antes de que aquí se limpie el cuarto.
            fabrica = getattr(cuarto, "fabrica_arbol", None) or construir_arbol_publicacion
            duracion = getattr(cuarto, "duracion_terminal", None)
            cuarto.terminal = (TerminalDecision(fabrica()) if duracion is None
                               else TerminalDecision(fabrica(), duracion, descender_resultados=True))
            cuarto.terminal.iniciar()
        cuarto.fase = FASE_DECISION
        _congelar_terminal(cuarto.terminal)
        if isinstance(datos_terminal, dict):
            _espejar_terminal(cuarto.terminal, datos_terminal)
        return Escena.DECISION

    # --- Aplicar el estado ------------------------------------------------

    def _aplicar(self, estado, escena, arena, mazmorra, partida, jugadores):
        lectores = estado.get("leen")
        self.lectores = [i for i in lectores if _entero(i) is not None] if isinstance(lectores, list) else []
        terminal = estado.get("term")
        self.sabotaje_restante = _numero(terminal.get("sab"), 0.0, 1e4) if isinstance(terminal, dict) else None
        self.sabotaje_espera = _numero(terminal.get("sabt"), 0.0, 1e4) if isinstance(terminal, dict) else None
        self.reunion = vista_de_dict(estado.get("reu"))
        self.sabotaje_post = vista_sabotaje_de_dict(estado.get("sbp"))
        self._espejar_post()
        self._version_host = estado.get("v")
        colapso = _numero(estado.get("colapso"), 0.0, COLAPSO_MAXIMO)
        if colapso is not None:
            partida.colapso.valor = colapso
        partida.campania.aplicar_resumen_red(estado.get("cam"))
        self.investigacion_espejo = estado.get("inv")
        self._reproducir_decisiones(estado, escena, partida, colapso)
        mismo_lugar = estado.get("loc") == self._lugar(escena, arena, mazmorra)
        self._aplicar_jugadores(estado, jugadores, mismo_lugar)
        if not mismo_lugar:
            return
        if mazmorra is not None and escena in (Escena.MAZMORRA, Escena.DECISION):
            self._espejar_cuarto(mazmorra.cuarto, estado.get("enemigos"))
        if arena is not None:
            self._espejar_arena(arena, estado)
        if escena in ESCENAS_DE_COMBATE:
            self._espejar_proyectiles(estado.get("pro"))
            # Los muebles se rompen donde diga el host (aquí las balas solo se frenan).
            lugar = arena if arena is not None else mazmorra
            coberturas = getattr(lugar, "coberturas", None)
            if coberturas is not None and isinstance(estado.get("cob"), list):
                coberturas.aplicar_vidas(estado["cob"])

    def _reproducir_decisiones(self, estado, escena, partida, colapso):
        """Decisiones del host que este invitado no vio (llegó tarde o no
        estaba en el cuarto final): se aplican igual aquí, para que el
        progreso, las calles y las barricadas sean los mismos."""
        decisiones = estado.get("dec")
        if not isinstance(decisiones, list) or escena in (Escena.MAZMORRA, Escena.DECISION):
            return
        if colapso is not None and round(colapso, 1) >= COLAPSO_MAXIMO:
            return  # el host está en la derrota global: se espera su reinicio
        historial = partida._historial_red
        for entrada in decisiones[len(historial):]:
            if isinstance(entrada, list) and len(entrada) == 2 and entrada[0] in EDIFICIOS \
                    and entrada[1] in RESULTADOS_DECISION:
                partida.registrar_decision(entrada[0], entrada[1])

    def _aplicar_jugadores(self, estado, jugadores, mismo_lugar):
        datos_jugadores = estado.get("jugadores")
        extras = estado.get("ext") if isinstance(estado.get("ext"), list) else []
        if not isinstance(datos_jugadores, list):
            return
        for indice, datos in enumerate(datos_jugadores[:len(jugadores)]):
            if not isinstance(datos, dict):
                continue
            jugador = jugadores[indice]
            vida = _numero(datos.get("vida"), -1000.0, 1000.0)
            if vida is not None:
                jugador.vida = vida  # la vida la manda el host para todos
            extra = extras[indice] if indice < len(extras) and isinstance(extras[indice], dict) else {}
            carga = _numero(extra.get("carga"), 0.0, 1000.0)
            if carga is not None:
                jugador.carga_habilidad = carga
            if indice == self.id_local or not mismo_lugar:
                continue  # la posición propia la manda esta PC
            invulnerable = _numero(extra.get("inv"), 0.0, 60.0)
            if invulnerable is not None:
                jugador.invulnerabilidad.tiempo_restante = invulnerable
            x, y = _numero(datos.get("x")), _numero(datos.get("y"))
            if x is not None and y is not None:
                _mover_a(jugador, x, y)
            jugador.caminando_en_ciudad = bool(datos.get("caminando"))
            mx, my = _numero(extra.get("mx"), -1.0, 1.0), _numero(extra.get("my"), -1.0, 1.0)
            if mx is not None and my is not None and (mx or my):
                jugador.direccion_mirada = pygame.Vector2(mx, my)

    def _marcar_ausentes(self, estado, partida, jugadores):
        """Los jugadores que el host ve desconectados no se dibujan ni pelean."""
        fuera = estado.get("fuera")
        ausentes = {i for i in fuera if _entero(i) is not None and i != self.id_local} \
            if isinstance(fuera, list) else set()
        for indice in ausentes:
            if 0 <= indice < len(jugadores):
                jugadores[indice].vida = 0
        partida.jugadores_online = [j for i, j in enumerate(jugadores) if i not in ausentes]

    def _espejar_enemigos(self, actuales, datos):
        """Lista de enemigos igual a la del host (emparejados por id).
        Retorna (nueva_lista, enemigos_que_ya_no_están)."""
        textos = getattr(self._sesion, "textos", None)
        por_id = {}
        for enemigo in actuales:
            por_id.setdefault(getattr(enemigo, "_id_red", None), enemigo)
        nueva, usados = [], set()
        for d in datos:
            if not isinstance(d, dict):
                continue
            clave, x, y = _entero(d.get("id")), _numero(d.get("x")), _numero(d.get("y"))
            vida = _numero(d.get("vida"), -1e4, 1e4)
            if clave is None or x is None or y is None or vida is None or clave in usados:
                continue
            try:
                tipo = TipoEnemigo(d.get("tp")) if d.get("tp") is not None else None
            except ValueError:
                tipo = None
            enemigo = por_id.get(clave)
            if enemigo is not None and tipo is not None and getattr(enemigo, "tipo", None) != tipo:
                enemigo = None  # otro tipo con el mismo id: se reemplaza
            if enemigo is None:
                if tipo is None:
                    continue
                enemigo = crear_enemigo(tipo, round(x), round(y))
                enemigo._id_red = clave
            elif textos is not None and vida < enemigo.vida - 1e-6:
                textos.agregar(f"-{enemigo.vida - vida:g}", (enemigo.rect.centerx, enemigo.rect.top - 12))
            _congelar_enemigo(enemigo)
            enemigo.vida = vida
            vida_maxima = _numero(d.get("vmax"), 0.0, 1e4)
            if vida_maxima:
                enemigo.vida_maxima = vida_maxima
            enemigo.escudo_anonimato = bool(d.get("esc"))
            _mover_a(enemigo, x, y)
            usados.add(clave)
            nueva.append(enemigo)
        sobrantes = [e for e in actuales if e not in nueva]
        return nueva, sobrantes

    def _espejar_cuarto(self, cuarto, datos):
        if not isinstance(datos, list):
            return
        nueva, sobrantes = self._espejar_enemigos(cuarto.enemigos, datos)
        for enemigo in sobrantes:
            enemigo.vida = min(enemigo.vida, 0)  # murió en el host
        # Los muertos se quedan en la lista: el cuarto los quita en su
        # actualizar y así abre las puertas como siempre.
        cuarto.enemigos[:] = nueva + sobrantes

    def _espejar_arena(self, arena, estado):
        m = arena.mazmorra
        datos = estado.get("jefe")
        if isinstance(datos, dict):
            derrotas = _entero(datos.get("der"))
            if derrotas is not None and derrotas > m.derrotas:
                # El host perdió contra el jefe y la pelea se reinició.
                m.derrotas = derrotas
                m._preparar_pelea()
                arena._vincular_cuerpo_jefe()
                m.reinicio_pendiente = True  # ArenaJefe cura, recoloca y da la gracia
            jefe = arena.jefe
            jefe.recibir_dano = _ignorar_dano
            x, y = _numero(datos.get("x")), _numero(datos.get("y"))
            if x is not None and y is not None:
                jefe.x, jefe.y = x, y
                if jefe.rect is not None:
                    jefe.rect.center = (round(x), round(y))
            vida = _numero(datos.get("vida"), -1e5, 1e5)
            if vida is not None:
                textos = getattr(self._sesion, "textos", None)
                if textos is not None and vida < jefe.vida - 1e-6 and jefe.rect is not None:
                    textos.agregar(f"-{jefe.vida - vida:g}", (jefe.rect.centerx, jefe.rect.top - 12))
                jefe.vida = vida
            fase = _entero(datos.get("fase"))
            if fase is not None:
                jefe.fase = fase
            escudo = _entero(datos.get("esc"))
            if escudo is not None:
                jefe._vida_escudo = max(0, escudo)
            for clave, atributo in (("pausa", "tiempo_pausa"), ("dest", "tiempo_destello")):
                valor = _numero(datos.get(clave), 0.0, 60.0)
                if valor is not None:
                    setattr(jefe, atributo, valor)
            jefe.eventos.clear()
            if datos.get("estado") in (EN_COMBATE, VICTORIA):
                m.estado = datos["estado"]
            for clave, atributo in (("trest", "tiempo_restante"), ("msg", "tiempo_mensaje_derrota"),
                                    ("sac", "tiempo_sacudida")):
                valor = _numero(datos.get(clave), 0.0, 1e4)
                if valor is not None:
                    setattr(m, atributo, valor)
            charcos = datos.get("charcos")
            if isinstance(charcos, list):
                m.charcos = [c for c in (_charco_desde(d) for d in charcos) if c is not None]
        subditos = estado.get("sub")
        if isinstance(subditos, list):
            arena.subditos = self._espejar_enemigos(arena.subditos, subditos)[0]

    def _espejar_proyectiles(self, datos):
        proyectiles = getattr(self._sesion, "proyectiles_enemigos", None)
        if not isinstance(proyectiles, list) or not isinstance(datos, list):
            return
        proyectiles[:] = [p for p in (_proyectil_desde(d) for d in datos[:MAX_PROYECTILES_RED]) if p is not None]

    def _perder_host(self, arena, mazmorra, partida, jugadores):
        """Se cayó la conexión: todo vuelve a simularse en esta PC y se sigue solo."""
        self._espejo = False
        if arena is not None:
            arena.coberturas.espejo = False
        if mazmorra is not None:
            _descongelar(mazmorra, "_cruzar")
            for cuarto in mazmorra.cuartos.values():
                cuarto.coberturas.espejo = False  # vuelven a dañarse en esta PC
                for enemigo in cuarto.enemigos:
                    _descongelar_enemigo(enemigo)
                if cuarto.terminal is not None:
                    _descongelar(cuarto.terminal, "navegar", "actualizar")
            _avisar_en_mazmorra(mazmorra, TEXTO_HOST_PERDIDO)
        if arena is not None:
            _descongelar(arena.mazmorra, "actualizar")
            _descongelar(arena.jefe, "recibir_dano")
            for subdito in arena.subditos:
                _descongelar_enemigo(subdito)
        if 0 <= self.id_local < len(jugadores):
            partida.jugadores_online = [jugadores[self.id_local]]
        print(f"[Online] {TEXTO_HOST_PERDIDO}: la partida sigue en esta PC.")

    def detener(self):
        self.cliente.desconectar()


def _charco_desde(datos):
    if not isinstance(datos, list) or len(datos) != 4:
        return None
    x, y, radio, tiempo = _numero(datos[0]), _numero(datos[1]), _entero(datos[2]), _numero(datos[3], 0.0, 1e4)
    if None in (x, y, radio, tiempo):
        return None
    charco = Charco(x, y, radio)
    charco.tiempo = tiempo
    return charco


# =========================================================================
# Configuración de la sesión (la usa Main._menu_inicio)
# =========================================================================

class ConfigSesionHost:
    """Configura la sesión para el Host."""

    def __init__(self, conexion, clases, ids_red=None, mando=None):
        self.conexion = conexion
        self.clases = clases
        self.ids_red = ids_red
        real_mando = mando if (mando is not None and not isinstance(mando, _MandoFicticio)) else _detectar_mando()
        self.mando = real_mando if real_mando is not None else _MandoFicticio()

    def configurar_sesion(self, sesion):
        adaptador = AdaptadorOnlineHost(self.conexion, ids_red=self.ids_red)
        sesion.adaptador_red = adaptador
        sesion.id_local = 0
        sesion.mando = self.mando
        entradas = [EntradaTecladoRed(mando=self.mando)]
        for jid in range(1, len(self.clases)):
            entradas.append(EntradaRed(adaptador, id_jugador=jid))
        sesion.entradas = entradas
        _vestir_jugadores(sesion, self.conexion, self.ids_red)
        _asignar_impostor(sesion, self.conexion, self.ids_red)
        return sesion


class ConfigSesionJoin:
    """Configura la sesión para el Invitado."""

    def __init__(self, conexion, clases, id_local=1, ids_red=None, mando=None):
        self.conexion = conexion
        self.clases = clases
        self.id_local = id_local
        self.ids_red = ids_red
        real_mando = mando if (mando is not None and not isinstance(mando, _MandoFicticio)) else _detectar_mando()
        self.mando = real_mando if real_mando is not None else _MandoFicticio()

    def configurar_sesion(self, sesion):
        adaptador = AdaptadorOnlineJoin(self.conexion, id_local=self.id_local, ids_red=self.ids_red)
        sesion.adaptador_red = adaptador
        sesion.id_local = self.id_local
        sesion.mando = self.mando
        entradas = []
        for jid in range(len(self.clases)):
            if jid == self.id_local:
                entradas.append(EntradaLocalCliente(adaptador, id_jugador=jid, mando=self.mando))
            else:
                entradas.append(EntradaRemotaHost(adaptador, id_jugador=jid))
        sesion.entradas = entradas
        _vestir_jugadores(sesion, self.conexion, self.ids_red)
        _asignar_impostor(sesion, self.conexion, self.ids_red)
        return sesion


def _ids_de_partida(conexion, cantidad):
    """Id de red de cada jugador, en el orden de `clases`: el que fijó el
    lobby al iniciar; si no, los de la sala; si no cuadran, 0..n-1."""
    for ids in (getattr(conexion, "ids_partida", None), _ids_de_sala(conexion)):
        if isinstance(ids, list) and len(ids) == cantidad and all(_entero(i) is not None for i in ids) \
                and len(set(ids)) == cantidad:
            return list(ids)
    return list(range(cantidad))


def _ids_de_sala(conexion):
    sala = getattr(conexion, "sala", None)
    try:
        return sala.jugadores() if sala is not None else None
    except Exception:
        return None


def _vestir_jugadores(sesion, conexion, ids_red):
    """Cada jugador de `sesion.jugadores` toma la apariencia que eligió en
    los vestidores del lobby: la de su nodo en el grafo de sala, por el
    orden de `ids_red` (None = el de _ids_de_partida). Como todas las PCs
    usan el mismo orden, todas ven igual a cada jugador. Nunca rompe la
    sesión: sin sala, sin jugadores o con un error se anota y cada uno
    queda con la hoja de su rol."""
    try:
        jugadores = getattr(sesion, "jugadores", None)
        sala = getattr(conexion, "sala", None)
        if not jugadores or sala is None:
            faltante = "jugadores en la sesión" if not jugadores else "grafo de sala"
            registro_errores.registrar(
                "_vestir_jugadores",
                RuntimeError(f"sin {faltante}: cada jugador queda con la hoja de su rol"),
            )
            return
        ids = ids_red if ids_red is not None else _ids_de_partida(conexion, len(jugadores))
        apariencias = []
        for id_red in ids:
            apariencia = sala.apariencia_de(id_red)
            # Se valida igual que lo que llega por red (Apariencia.de_dict): así
            # esta PC ve a cada uno como las demás y el dibujo de cada frame
            # nunca recibe un tono o un rol inválido.
            datos = apariencia.a_dict() if isinstance(apariencia, Apariencia) else apariencia
            apariencias.append(Apariencia.de_dict(datos))
        # Se asignan al final: si la sala falla a medias, nadie queda vestido.
        for jugador, apariencia in zip(jugadores, apariencias):
            jugador.apariencia = apariencia
    except Exception:
        registro_errores.registrar("_vestir_jugadores")


def _asignar_impostor(sesion, conexion, ids_red):
    """Deja en la sesión el id de red del impostor (lo sorteó el host) y marca
    a su jugador, por el mismo orden de `ids_red` que la ropa. Por ahora es
    solo el dato: ninguna mecánica de la partida lo usa todavía."""
    try:
        id_impostor = getattr(conexion, "id_impostor", None)
        sesion.id_impostor = id_impostor
        jugadores = getattr(sesion, "jugadores", None) or []
        ids = ids_red if ids_red is not None else _ids_de_partida(conexion, len(jugadores))
        for jugador, id_red in zip(jugadores, ids):
            jugador.es_impostor = id_red == id_impostor
    except Exception:
        registro_errores.registrar("_asignar_impostor")


def preparar_sesion_online(clases, mando, conexion, es_host):
    """Inicializa la configuración de red y prepara las entradas para Host o Join."""
    ids = _ids_de_partida(conexion, len(clases))
    if es_host:
        config = ConfigSesionHost(conexion, clases, ids_red=ids, mando=mando)
        return clases, mando, config
    id_red = conexion.id_jugador if getattr(conexion, "id_jugador", None) is not None else 1
    if id_red in ids:
        id_local = ids.index(id_red)
    else:
        id_local = max(0, min(id_red, len(clases) - 1))
    config = ConfigSesionJoin(conexion, clases, id_local=id_local, ids_red=ids, mando=mando)
    return clases, mando, config


# =========================================================================
# Protección del loop de Main.py y cierre de la red
# =========================================================================

def proteger_partida_online(jugar):
    """Decorador para Main._jugar: si algo falla durante una partida ONLINE,
    se anota el error y se vuelve al menú principal (la partida queda para
    CONTINUAR) en vez de cerrar el juego. En una partida local el error
    sale como siempre."""

    @functools.wraps(jugar)
    def jugar_protegido(pantalla, reloj, sesion, preferencias, presentar):
        try:
            return jugar(pantalla, reloj, sesion, preferencias, presentar)
        except Exception:
            if getattr(sesion, "adaptador_red", None) is None:
                raise
            registro_errores.registrar("Main._jugar (partida online)")
            pygame.mouse.set_visible(True)
            return MENU

    return jugar_protegido


def cerrar_red_de_sesion(sesion):
    """Cierra el servidor o la conexión de una sesión online que se deja
    (al empezar otra partida), para no dejar el puerto 7777 ocupado ni a
    los invitados esperando a un host que ya no juega."""
    adaptador = getattr(sesion, "adaptador_red", None)
    if adaptador is None:
        return
    try:
        adaptador.detener()
    except Exception:
        registro_errores.registrar("cerrar_red_de_sesion")


def compartir_combate_con_sesion(sesion, limpiar_combate, proyectiles_enemigos, textos):
    """Main._jugar deja en la sesión lo que los adaptadores necesitan del
    frame: limpiar el combate al cambiar de lugar, los proyectiles
    enemigos (el host los manda y el invitado los dibuja) y los números
    de daño. Sin esto el invitado no veía las balas enemigas."""
    try:
        sesion.limpiar_combate = limpiar_combate
        sesion.proyectiles_enemigos = proyectiles_enemigos
        sesion.textos = textos
    except Exception:
        registro_errores.registrar("compartir_combate_con_sesion")


def normalizar_escena(escena, arena, mazmorra, resultado, jugador, partida):
    """Escena que Main._jugar puede usar sin romperse.

    El adaptador cambia escena/arena/mazmorra en mitad del frame (el
    invitado es llevado a la mazmorra en la que entró el host). Si alguna
    vez llega una escena de combate sin su lugar (MAZMORRA sin mazmorra,
    JEFE sin arena, DECISION sin terminal, RESULTADO sin resultado), Main
    hacía `escenario.gracia` sobre None y el juego se cerraba
    (AttributeError: 'NoneType' object has no attribute 'gracia'). Aquí se
    corrige a la escena válida más cercana y se anota en el registro."""
    try:
        corregida = escena
        if escena in (Escena.MAZMORRA, Escena.DECISION) and mazmorra is None:
            corregida = Escena.CIUDAD
        elif escena == Escena.DECISION and getattr(mazmorra.cuarto, "terminal", None) is None:
            corregida = Escena.MAZMORRA
        elif escena in (Escena.JEFE, Escena.VICTORIA) and arena is None:
            corregida = Escena.CIUDAD
        elif escena == Escena.RESULTADO and resultado is None:
            corregida = Escena.CIUDAD
        if corregida is escena:
            return escena
        registro_errores.registrar(
            "normalizar_escena",
            RuntimeError(f"{escena.name} sin su lugar (arena={arena is not None}, "
                         f"mazmorra={mazmorra is not None}): se pasa a {corregida.name}"),
        )
        if corregida == Escena.CIUDAD and jugador is not None and partida is not None:
            _volver_a_la_ciudad(jugador, partida)
        return corregida
    except Exception:
        registro_errores.registrar("normalizar_escena")
        return escena
