"""Dónde va el celular del modo Online en cada lugar (lógica pura, sin pygame).

El botón CELULAR va a la DERECHA, como espejo de REPORTAR y SABOTEAR, que van
a la izquierda (Online/disposicion_hud.py):

    Sala de espera   píldora arriba a la derecha, sobre ROOM SETTINGS (ese
                     panel empieza en y = 50: la franja de arriba está libre).
    Ciudad           abajo a la derecha, sobre el aviso "Civitas · Te
                     mencionan" (assets.RECT_FEED_CIVITAS).
    Mazmorra o jefe  con 2 o 3 jugadores, en el margen derecho bajo el panel
                     de J2 (espejo de REPORTAR en (10, 452)); con 4 el margen
                     derecho es del panel de J4, así que va al rincón inferior
                     derecho del cuarto. El "HUD detallado" no cambia nada a la
                     derecha (su panel de misión va abajo a la izquierda).
    Terminal y las demás pantallas: no hay celular (rect_boton -> None).

El celular abierto ocupa la derecha de la pantalla y termina antes de la barra
de controles (y = 652 < 660). El globo del mensaje entrante (con el celular
cerrado) sale a la izquierda del botón. Los rectángulos son tuplas (x, y,
ancho, alto) en px de la pantalla lógica de 1280x720.
"""

from src.core.escenas import Escena

ANCHO_PANTALLA, ALTO_PANTALLA = 1280, 720

SALA = "sala"  # el lobby del hotel usa este "lugar" en vez de una Escena
ESCENAS_CELULAR = (Escena.CIUDAD, Escena.MAZMORRA, Escena.JEFE)

RECT_CELULAR_ABIERTO = (884, 22, 360, 630)  # cuerpo del celular abierto (a la derecha; abajo termina en 652 < 660)
RECT_BOTON_SALA = (960, 8, 260, 36)  # sala de espera: píldora arriba a la derecha (encima de ROOM SETTINGS)
RECT_BOTON_CIUDAD = (1160, 456, 100, 92)  # abajo a la derecha, sobre assets.RECT_FEED_CIVITAS = (900, 560, 360, 80)
RECT_BOTON_MARGEN = (1166, 452, 104, 92)  # combate con 2-3 jugadores: margen derecho bajo el panel de J2
RECT_BOTON_CUARTO = (1032, 548, 100, 92)  # combate con 4: rincón inferior derecho del cuarto
MAX_JUGADORES_MARGEN = 3  # con más, el margen derecho de abajo es del panel de J4

# Globo del mensaje entrante (celular cerrado): a la izquierda del botón.
ANCHO_AVISO, ALTO_AVISO = 300, 64
ANCHO_AVISO_SALA, ALTO_AVISO_SALA = 380, 36  # en la sala, una sola fila a la altura de la píldora
SEPARACION_AVISO = 12  # px entre el globo y el botón (ahí va la colita del globo)
MARGEN_AVISO = 6  # px mínimos al borde de la pantalla
LIMITE_FRANJA_SALA = 50  # en la sala, ROOM SETTINGS y la sala empiezan en y = 50


def disponible_en(lugar):
    """¿Hay celular en este lugar? En la sala y en la ciudad, mazmorra y jefe."""
    return lugar == SALA or lugar in ESCENAS_CELULAR


def rect_boton(lugar, cantidad_jugadores=2, hud_detallado=False):
    """Rect del botón CELULAR en `lugar` (SALA o una Escena), o None si ahí no
    hay celular (terminal, resultado, victoria...). `hud_detallado` se acepta
    por simetría con disposicion_hud.rects_botones: a la derecha no cambia nada."""
    if lugar == SALA:
        return RECT_BOTON_SALA
    if lugar == Escena.CIUDAD:
        return RECT_BOTON_CIUDAD
    if lugar in (Escena.MAZMORRA, Escena.JEFE):
        return RECT_BOTON_MARGEN if cantidad_jugadores <= MAX_JUGADORES_MARGEN else RECT_BOTON_CUARTO
    return None


def rect_aviso(lugar, rect_boton):
    """Globo del mensaje entrante a la izquierda del botón, centrado a su
    altura. En la sala es una fila baja a la altura de la píldora (queda en la
    franja libre, por encima de y = 50). Siempre dentro de la pantalla."""
    x, y, ancho_boton, alto_boton = rect_boton
    if lugar == SALA:
        ancho, alto = ANCHO_AVISO_SALA, ALTO_AVISO_SALA
        tope_abajo = LIMITE_FRANJA_SALA - MARGEN_AVISO
    else:
        ancho, alto = ANCHO_AVISO, ALTO_AVISO
        tope_abajo = ALTO_PANTALLA - MARGEN_AVISO
    izquierda = max(MARGEN_AVISO, x - SEPARACION_AVISO - ancho)
    arriba = y + alto_boton // 2 - alto // 2
    arriba = max(MARGEN_AVISO, min(arriba, tope_abajo - alto))
    return (izquierda, arriba, ancho, alto)


def rect_celular(apertura=1.0):
    """RECT_CELULAR_ABIERTO desplazado hacia abajo según la animación de abrir
    (0 = escondido bajo la pantalla, 1 = en su lugar). Llega frenando
    (ease-out cúbico), como los paneles del juego (src/ui/layout.py)."""
    try:
        apertura = min(1.0, max(0.0, float(apertura)))
    except (TypeError, ValueError):
        apertura = 1.0
    suave = 1 - (1 - apertura) ** 3
    x, y, ancho, alto = RECT_CELULAR_ABIERTO
    return (x, y + round((1 - suave) * (ALTO_PANTALLA - y)), ancho, alto)
