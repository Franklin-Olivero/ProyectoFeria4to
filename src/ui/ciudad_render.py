"""Dibujo de Ciudad Nova (escena CIUDAD, solo presentación).

El suelo estático (casillas, casas y fachadas) se pinta una sola vez en
una Surface del tamaño del mundo y cada frame se copia solo la parte
que ve la cámara. Encima van las capas que cambian: halos de las
farolas, auras de toxicidad, rótulos neón, barricadas activas, la ruta
sugerida y el jugador. También dibuja el cintillo de noticias y los
avisos. No modifica el estado del juego.
"""

import math

import pygame

from src.core import assets
from src.core.balance import ADELANTO_CAMARA_CIUDAD, TAM_CASILLA
from src.dungeon import ciudad_mapa
from src.ui import cargador_assets, casillas_ciudad, decoracion_ciudad, dibujo, edificios_ciudad, sprites
from src.ui.fuentes import fuente
from src.ui.mapa_render import color_toxicidad

_cache = {}


def vista():
    """Rect de pantalla donde se ve el mundo."""
    return pygame.Rect(assets.RECT_VISTA_CIUDAD)


def camara_para(posicion):
    """Cámara centrada ADELANTO_CAMARA_CIUDAD px por encima del jugador
    (limitada a los bordes del mundo)."""
    objetivo = (posicion[0], posicion[1] - ADELANTO_CAMARA_CIUDAD)
    return ciudad_mapa.calcular_camara(objetivo, ciudad_mapa.TAM_MUNDO, vista().size)


# ----------------------------------------------------------------------
# Suelo estático (cacheado)
# ----------------------------------------------------------------------

def _imagen_casilla(col, fila, letra):
    if letra == ciudad_mapa.PASTO:
        return casillas_ciudad.casilla_pasto()
    if letra in ciudad_mapa.CALLES:
        marca = {ciudad_mapa.CALLE_HORIZONTAL: "horizontal", ciudad_mapa.CALLE_VERTICAL: "vertical"}.get(letra)
        return casillas_ciudad.casilla_calle(marca)
    if letra == ciudad_mapa.ARBOL:
        return casillas_ciudad.casilla_arbol()
    if letra == ciudad_mapa.CASA:
        con_techo = ciudad_mapa.casilla(col, fila - 1) != ciudad_mapa.CASA
        return casillas_ciudad.casilla_casa(con_techo, col * 31 + fila * 17)
    plaza_col, plaza_fila, plaza_ancho, plaza_alto = ciudad_mapa.PLAZA
    if plaza_col <= col < plaza_col + plaza_ancho and plaza_fila <= fila < plaza_fila + plaza_alto:
        return casillas_ciudad.casilla_plaza()
    # Acera, barricada de la Alcaldía y el suelo bajo los edificios.
    return casillas_ciudad.casilla_acera()


def mundo_base():
    """Surface con todo lo que no cambia: casillas y fachadas."""
    if "mundo" not in _cache:
        # Sin canal alfa (profundidad 24), como el lienzo de Main.py.
        superficie = pygame.Surface(ciudad_mapa.TAM_MUNDO, 0, 24)
        for fila, linea in enumerate(ciudad_mapa.MAPA):
            for col, letra in enumerate(linea):
                superficie.blit(_imagen_casilla(col, fila, letra), (col * TAM_CASILLA, fila * TAM_CASILLA))
        mosaico = casillas_ciudad.mosaico_plaza()
        superficie.blit(mosaico, mosaico.get_rect(
            center=ciudad_mapa.centro_casilla(*ciudad_mapa.NODOS_CALLE[ciudad_mapa.ZONA_PLAZA])))
        # Cada edificio con su escala entera, del tamaño de su huella (edificios_ciudad).
        edificios_ciudad.dibujar_todos(superficie)
        _cache["mundo"] = superficie
    return _cache["mundo"]


def _farolas():
    if "farolas" not in _cache:
        _cache["farolas"] = decoracion_ciudad.farolas()
    return _cache["farolas"]


def _halo():
    """Círculo de luz que se suma (BLEND_ADD) al suelo: más brillante al centro."""
    if "halo" not in _cache:
        radio = assets.RADIO_HALO_FAROLA
        superficie = pygame.Surface((radio * 2, radio * 2))
        r, g, b, intensidad = assets.COLOR_HALO_FAROLA
        for paso in range(radio, 0, -4):
            t = (1 - paso / radio) * intensidad / 255
            pygame.draw.circle(superficie, (round(r * t), round(g * t), round(b * t)), (radio, radio), paso)
        _cache["halo"] = superficie
    return _cache["halo"]


# ----------------------------------------------------------------------
# Escena completa
# ----------------------------------------------------------------------

def dibujar_ciudad(pantalla, partida, jugador, tiempo, ruta=None):
    """Mundo visible + capas dinámicas. `ruta` = puntos (px del mundo)
    de la ruta sugerida a dibujar, o None."""
    rect_vista = vista()
    posicion = (jugador.posicion.x, jugador.posicion.y)
    camara = camara_para(posicion)
    # Desplazamiento mundo -> pantalla.
    dx, dy = rect_vista.x - camara[0], rect_vista.y - camara[1]

    pantalla.set_clip(rect_vista)
    pantalla.fill(assets.COLOR_FONDO, rect_vista)
    pantalla.blit(mundo_base(), rect_vista.topleft, pygame.Rect(camara, rect_vista.size))
    _dibujar_halos(pantalla, rect_vista, dx, dy)
    _dibujar_auras(pantalla, partida, rect_vista, dx, dy, tiempo)
    _dibujar_rotulos(pantalla, rect_vista, dx, dy)
    _dibujar_barricadas(pantalla, partida, rect_vista, dx, dy)
    if ruta:
        _dibujar_ruta(pantalla, ruta, dx, dy, tiempo)

    def dibujar_jugador():
        if jugador.invulnerabilidad.visible:
            imagen = sprites.sprite_jugador(jugador.COLOR, rol=jugador.rol, tiempo=tiempo,
                                            caminando=jugador.caminando_en_ciudad,
                                            apariencia=getattr(jugador, "apariencia", None))
            sprites.dibujar_centrado(pantalla, imagen, (round(posicion[0] + dx), round(posicion[1] + dy - 6)))

    # Farolas, árboles, bancas y el jugador, ordenados por su base (Y).
    vista_mundo = pygame.Rect(camara, rect_vista.size)
    decoracion_ciudad.dibujar_con_jugador(pantalla, vista_mundo, dx, dy, dibujar_jugador, jugador.rect.bottom)
    pantalla.set_clip(None)


def _dibujar_halos(pantalla, rect_vista, dx, dy):
    halo = _halo()
    ox, oy = assets.DESPLAZAMIENTO_HALO_FAROLA
    for x, y in _farolas():
        rect = halo.get_rect(center=(x + dx + ox, y + dy + oy))
        if rect.colliderect(rect_vista):
            pantalla.blit(halo, rect, special_flags=pygame.BLEND_RGB_ADD)


def rect_edificio(zona, dx=0, dy=0):
    col, fila, ancho, alto = ciudad_mapa.EDIFICIOS[zona]
    return pygame.Rect(col * TAM_CASILLA + dx, fila * TAM_CASILLA + dy, ancho * TAM_CASILLA, alto * TAM_CASILLA)


def _dibujar_auras(pantalla, partida, rect_vista, dx, dy, tiempo):
    """Borde neón pulsante alrededor de cada edificio, del color de su
    toxicidad (verde 0 -> rojo 100)."""
    pulso = 0.5 + 0.5 * math.sin(2 * math.pi * tiempo / assets.PERIODO_AURA)
    alfa = assets.ALFA_AURA_MIN + (assets.ALFA_AURA_MAX - assets.ALFA_AURA_MIN) * pulso
    margen, grosor = assets.MARGEN_AURA, assets.GROSOR_AURA
    for zona in ciudad_mapa.EDIFICIOS:
        rect = rect_edificio(zona, dx, dy)
        exterior = rect.inflate((margen + grosor * assets.CAPAS_AURA) * 2, (margen + grosor * assets.CAPAS_AURA) * 2)
        if not exterior.colliderect(rect_vista):
            continue
        color = color_toxicidad(partida.toxicidad(zona))
        capa = pygame.Surface(exterior.size, pygame.SRCALPHA)
        for i in range(assets.CAPAS_AURA):
            borde = rect.inflate((margen + grosor * i) * 2, (margen + grosor * i) * 2).move(-exterior.x, -exterior.y)
            pygame.draw.rect(capa, (*color, round(alfa / (i + 1))), borde, grosor,
                             border_radius=assets.RADIO_PANEL * 2)
        pantalla.blit(capa, exterior.topleft)


def _dibujar_rotulos(pantalla, rect_vista, dx, dy):
    """Nombre de la zona en neón sobre la placa de su fachada (la placa se
    redibuja aquí para que todos los edificios la tengan igual)."""
    for zona in ciudad_mapa.EDIFICIOS:
        placa = edificios_ciudad.rect_placa(zona).move(dx, dy)
        if not placa.colliderect(rect_vista):
            continue
        neon = assets.COLORES_NEON_ZONA[zona]
        pygame.draw.rect(pantalla, assets.COLOR_MARCO_VENTANA, placa)
        pygame.draw.rect(pantalla, neon, placa, assets.ESCALA_PIXEL)
        texto = fuente(assets.TAMANIO_FUENTE_ROTULO, True).render(zona.upper(), True, neon)
        brillo = texto.copy()
        brillo.set_alpha(assets.ALFA_BRILLO_ROTULO)
        centro = texto.get_rect(center=placa.center)
        for ox, oy in ((-2, 0), (2, 0), (0, -2), (0, 2)):
            pantalla.blit(brillo, centro.move(ox, oy))
        pantalla.blit(texto, centro)


def _dibujar_barricadas(pantalla, partida, rect_vista, dx, dy):
    imagen = cargador_assets.prop_urbano("barricada") or casillas_ciudad.casilla_barricada()
    for col, fila in partida.barricadas_activas():
        casilla = pygame.Rect(col * TAM_CASILLA + dx, fila * TAM_CASILLA + dy, TAM_CASILLA, TAM_CASILLA)
        if rect_vista.colliderect(casilla):
            pantalla.blit(imagen, imagen.get_rect(midbottom=(casilla.centerx, casilla.bottom - 2)))


def _dibujar_ruta(pantalla, ruta, dx, dy, tiempo):
    puntos = [(x + dx, y + dy) for x, y in ruta]
    for inicio, fin in zip(puntos, puntos[1:]):
        dibujo.linea_punteada(pantalla, assets.COLOR_RUTA_CIUDAD, inicio, fin,
                              assets.LARGO_TRAZO_RUTA, assets.HUECO_TRAZO_RUTA, assets.GROSOR_RUTA_CIUDAD)
    # Destino: anillo que late sobre la puerta.
    radio = assets.RADIO_DESTINO_RUTA * (1 + 0.25 * math.sin(tiempo * 6))
    pygame.draw.circle(pantalla, assets.COLOR_RUTA_CIUDAD, puntos[-1], round(radio), 3)


# ----------------------------------------------------------------------
# Cintillo y avisos (coordenadas de pantalla)
# ----------------------------------------------------------------------

def dibujar_cintillo(pantalla, titulares, tiempo):
    """Franja fina "Breaking News Civitas" al pie, semitransparente, con los
    titulares desplazándose despacio."""
    rect = pygame.Rect(assets.RECT_CINTILLO)
    dibujo.panel_alfa(pantalla, rect, (*assets.COLOR_PANEL_HUD, assets.ALFA_CINTILLO), radio=0)
    pygame.draw.line(pantalla, assets.COLOR_LINEA_HUD, rect.topleft, rect.topright, 1)
    etiqueta = dibujo.chip(pantalla, assets.ETIQUETA_CINTILLO, (rect.left + 8, rect.centery),
                           assets.COLOR_FONDO, assets.COLOR_ETIQUETA_CINTILLO, assets.COLOR_ETIQUETA_CINTILLO,
                           assets.TAMANIO_FUENTE_MINI, ancla="midleft", alto=rect.height - 6, margen=6)
    franja = pygame.Rect(etiqueta.right + 12, rect.top, rect.right - etiqueta.right - 12, rect.height)
    cadena = assets.SEPARADOR_CINTILLO.join(titulares) + assets.SEPARADOR_CINTILLO
    # Los titulares cambian poco: se re-renderiza solo si cambió el texto.
    if _cache.get("cintillo_texto") != cadena:
        _cache["cintillo_texto"] = cadena
        _cache["cintillo"] = fuente(assets.TAMANIO_FUENTE_PEQUENA).render(cadena, True, assets.COLOR_TEXTO_CINTILLO)
    texto = _cache["cintillo"]
    desplazamiento = (tiempo * assets.VELOCIDAD_CINTILLO) % texto.get_width()
    pantalla.set_clip(franja)
    x = franja.left - desplazamiento
    while x < franja.right:
        pantalla.blit(texto, texto.get_rect(midleft=(x, franja.centery)))
        x += texto.get_width()
    pantalla.set_clip(None)


def dibujar_aviso(pantalla, cadena, color, centro=assets.POSICION_AVISO_ENTRADA):
    dibujo.chip(pantalla, cadena, centro, color, assets.COLOR_FONDO_PANEL, color,
                assets.TAMANIO_FUENTE_MEDIA, ancla="center", alto=36, margen=16)


def dibujar_fundido(pantalla, restante):
    """Velo del color de fondo que se desvanece en DURACION_FUNDIDO."""
    if restante <= 0:
        return
    velo = pygame.Surface(pantalla.get_size())
    velo.fill(assets.COLOR_FUNDIDO)
    velo.set_alpha(round(255 * min(1.0, restante / assets.DURACION_FUNDIDO)))
    pantalla.blit(velo, (0, 0))
