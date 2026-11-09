"""Qué bloques del HUD se ven en cada escena (lógica pura, sin Pygame).

Inventario y clasificación de lo que se dibuja durante la partida:

    ESENCIAL   (siempre que tenga sentido en la escena)
        vida, habilidad, colapso, contador (enemigos y cuartos), minimapa
        (tecla M), jefe (barra, fase y tiempo), temporizador (terminal),
        aviso (puerta cercana, "Limpia todos los cuartos primero"),
        mision_linea (la misión en una sola línea, solo en la ciudad),
        cintillo (franja fina de noticias, solo en la ciudad)
    SECUNDARIO (solo con "HUD detallado" en los ajustes de la pausa)
        titulo (lugar y su subtítulo), destino (destino y calles
        bloqueadas), mision (panel completo), reputacion, controles
    RUIDO      (quitado): la franja opaca superior a todo lo ancho, el
        cintillo grueso bajo el HUD, la barra de controles fija, el panel
        de misión abierto tapando el mapa, el título repetido.

La misión completa también se abre un momento al pasar el mouse por su
línea o al cambiar de destino con Tab (`mision_abierta`). Los controles
se ven unos segundos al entrar a una escena o con H (`mostrar_controles`)
y en la terminal, donde hacen falta para jugar. En el mapa del mundo se
ven los suyos (cómo cerrarlo).

`bloques_visibles` es la única regla: el coordinador (src/ui/hud_partida.py)
dibuja exactamente lo que devuelve.
"""

from src.core.escenas import Escena

VIDA = "vida"
HABILIDAD = "habilidad"
COLAPSO = "colapso"
CONTADOR = "contador"
MINIMAPA = "minimapa"
JEFE = "jefe"
TEMPORIZADOR = "temporizador"
AVISO = "aviso"
MISION_LINEA = "mision_linea"
CINTILLO = "cintillo"
TITULO = "titulo"
DESTINO = "destino"
MISION = "mision"
REPUTACION = "reputacion"
CONTROLES = "controles"

ESENCIALES = frozenset({VIDA, HABILIDAD, COLAPSO, CONTADOR, MINIMAPA, JEFE, TEMPORIZADOR, AVISO, MISION_LINEA,
                        CINTILLO})
SECUNDARIOS = frozenset({TITULO, DESTINO, MISION, REPUTACION, CONTROLES})


def bloques_visibles(escena, hud_detallado=False, mostrar_controles=False, minimapa=True, multijugador=False,
                     mapa_mundo=False, mision_abierta=False):
    """frozenset de los bloques que se dibujan.

    escena: Escena; hud_detallado: la opción de la pausa; mostrar_controles:
    los segundos de ayuda al entrar o con H; minimapa: la tecla M;
    multijugador: cada jugador tiene su panel lateral (vida y habilidad no
    van arriba); mapa_mundo: el mapa de la ciudad (M) está abierto;
    mision_abierta: mouse sobre la línea de misión o Tab reciente."""
    bloques = set()
    if escena == Escena.CIUDAD:
        bloques |= {VIDA, HABILIDAD, COLAPSO}
        if mapa_mundo:
            bloques |= {TITULO, CONTROLES}  # el mapa es otra pantalla: su nombre y cómo cerrarlo
        else:
            bloques |= {AVISO, MISION_LINEA, CINTILLO}
            if mision_abierta:
                bloques.add(MISION)
        if hud_detallado:
            bloques |= {TITULO, DESTINO, REPUTACION} | ({MISION} if not mapa_mundo else set())
    elif escena == Escena.MAZMORRA:
        bloques |= {VIDA, HABILIDAD, COLAPSO, CONTADOR, AVISO}
        if minimapa:
            bloques.add(MINIMAPA)
        if hud_detallado:
            bloques |= {TITULO, MISION}
    elif escena == Escena.JEFE:
        bloques |= {VIDA, HABILIDAD, COLAPSO, JEFE}
        if hud_detallado:
            bloques |= {TITULO}
    elif escena == Escena.DECISION:
        bloques |= {TEMPORIZADOR, CONTROLES}  # sin estos no se puede jugar la terminal
    else:
        return frozenset()
    if mostrar_controles or hud_detallado:
        bloques.add(CONTROLES)
    if multijugador:
        bloques -= {VIDA, HABILIDAD}  # cada jugador en su panel lateral
    return frozenset(bloques)


def es_esencial(bloque):
    return bloque in ESENCIALES
