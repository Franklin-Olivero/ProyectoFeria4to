"""Dibujo de la pantalla de selección de rol (solo presentación).

Una tarjeta por rol: número (atajo 1-4 del J1), sprite, nombre,
habilidad y una barra horizontal por estadística (Velocidad, Cadencia,
Daño, Vida). El largo de cada barra es la fracción de esa estadística
respecto al rol que la tiene más alta (balance.stats_normalizadas), así
de un vistazo se ve quién es rápido, quién es lento y quién aguanta.

Cada jugador tiene un cursor (src/ui/seleccion.py): la tarjeta bajo su
cursor se resalta con un chip "J1"/"J2", y al confirmar se tiñe del
color del rol y el chip muestra ✓.
"""

from src.core import assets
from src.core.balance import ESTADISTICAS_VISIBLES, stats_normalizadas
from src.ui import dibujo, sprites

TITULO = "Elige tu personaje"
TITULO_DOS = "Elijan sus personajes"
SUBTITULO = "Civitas · 4 roles, una ciudad al borde del colapso"
SUBTITULO_DOS = "J1 con teclado · J2 con el control · pueden repetir rol"


def dibujar_seleccion(pantalla, clases_rol, seleccion):
    """`clases_rol` es la lista ordenada de clases de rol (tecla 1 = la
    primera); `seleccion` es la SeleccionRoles con un cursor por jugador."""
    pantalla.fill(assets.COLOR_FONDO)
    dos = len(seleccion.cursores) > 1
    cx, cy = assets.POSICION_TITULO_SELECCION
    dibujo.texto(pantalla, TITULO_DOS if dos else TITULO, (cx, cy), assets.COLOR_TEXTO_HUD,
                 assets.TAMANIO_FUENTE_GRANDE, negrita=True, ancla="center")
    dibujo.texto(pantalla, SUBTITULO_DOS if dos else SUBTITULO, (cx, cy + 34), assets.COLOR_TEXTO_SECUNDARIO,
                 assets.TAMANIO_FUENTE_NORMAL, ancla="center")

    normalizadas = stats_normalizadas()
    origen_x, origen_y = assets.ORIGEN_COLUMNAS_SELECCION
    fila = assets.SEPARACION_FILAS_SELECCION

    for indice, clase in enumerate(clases_rol):
        # Jugadores cuyo cursor está sobre esta tarjeta: (número, confirmado).
        encima = [(n, cursor.confirmado) for n, cursor in enumerate(seleccion.cursores) if cursor.indice == indice]
        resaltada = bool(encima)
        tarjeta = dibujo.panel(
            pantalla,
            (origen_x + indice * assets.ANCHO_COLUMNA_SELECCION, origen_y,
             assets.ANCHO_TARJETA_SELECCION, assets.ALTO_TARJETA_SELECCION),
            assets.COLOR_FONDO_PANEL, clase.COLOR,
            assets.GROSOR_TARJETA_RESALTADA if resaltada else 1, radio=10,
        )
        if any(confirmado for _, confirmado in encima):
            dibujo.panel_alfa(pantalla, tarjeta, (*clase.COLOR, assets.ALFA_TARJETA_CONFIRMADA), radio=10)
        x = tarjeta.left + 20
        y = tarjeta.top + 18
        dibujo.chip(pantalla, str(indice + 1), (x, y), clase.COLOR, assets.COLOR_FONDO, clase.COLOR,
                    assets.TAMANIO_FUENTE_MEDIA, alto=30, margen=11)
        _dibujar_chips_cursor(pantalla, encima, (tarjeta.right - 14, y), clase.COLOR)

        # Retrato ilustrado del rol si existe; si no, el sprite grande.
        imagen = sprites.retrato_rol(clase.rol, assets.ALTO_RETRATO_SELECCION)
        if imagen is None:
            imagen = sprites.sprite_jugador(clase.COLOR, escala=5, rol=clase.rol)
        pantalla.blit(imagen, imagen.get_rect(midbottom=(tarjeta.centerx, y + 124)))
        y += 140
        dibujo.texto(pantalla, clase.NOMBRE, (tarjeta.centerx, y), clase.COLOR, assets.TAMANIO_FUENTE_TITULO,
                     negrita=True, ancla="center")
        y += 26
        dibujo.texto(pantalla, clase.NOMBRE_HABILIDAD, (tarjeta.centerx, y), assets.COLOR_TEXTO_SECUNDARIO,
                     assets.TAMANIO_FUENTE_PEQUENA, ancla="center")
        y += 40

        for etiqueta, atributo in ESTADISTICAS_VISIBLES:
            dibujo.texto(pantalla, etiqueta, (x, y), assets.COLOR_TEXTO_HUD, assets.TAMANIO_FUENTE_PEQUENA)
            dibujo.barra(
                pantalla, (x + assets.DESPLAZAMIENTO_BARRA_X, y + 3, assets.ANCHO_MAXIMO_BARRA, assets.ALTO_BARRA),
                normalizadas[clase.rol][atributo], clase.COLOR, borde=None, radio=3,
            )
            y += fila

    if dos:
        partes = []
        for n, cursor in enumerate(seleccion.cursores):
            nombre = clases_rol[cursor.indice].NOMBRE
            partes.append(f"J{n + 1}: {nombre} ✓" if cursor.confirmado else f"J{n + 1}: eligiendo…")
        dibujo.texto(pantalla, "   ·   ".join(partes), assets.POSICION_ESTADO_SELECCION,
                     assets.COLOR_TEXTO_HUD, assets.TAMANIO_FUENTE_MEDIA, ancla="center")


def _dibujar_chips_cursor(pantalla, encima, esquina_derecha, color):
    """Chips "J1"/"J2" del color del rol de la tarjeta (con ✓ si
    confirmó), alineados a la derecha."""
    x, y = esquina_derecha
    for numero, confirmado in reversed(encima):
        etiqueta = f"J{numero + 1} ✓" if confirmado else f"J{numero + 1}"
        rect = dibujo.chip(pantalla, etiqueta, (x, y), assets.COLOR_FONDO, color, color,
                           assets.TAMANIO_FUENTE_NORMAL, alto=30, margen=9, ancla="topright")
        x = rect.left - 6
