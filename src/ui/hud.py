"""HUD superior y barra de controles inferior (solo presentación).

HUD superior: etiqueta del jugador, corazones de vida, carga de la
habilidad (F), contador de enemigos, título/subtítulo del lugar y la
barra de colapso electoral. En cooperativo, los datos de cada jugador
pasan a un panel lateral (J1 a la izquierda, J2 a la derecha) con vida,
habilidad, el indicador animado del dash y sus controles clave; arriba
quedan solo el lugar, los enemigos y el colapso. Barra inferior: chips
con las teclas de la escena actual. No modifican ningún estado del juego.
"""

import math

import pygame

from src.core import assets
from src.ui import dibujo, sprites

CONTROLES_COMBATE = [
    ("WASD", "mover"),
    ("Ratón", "apuntar"),
    ("Clic", "disparar"),
    ("F", "habilidad"),
    ("Shift", "dash"),
    ("M", "minimapa"),
    ("Tab", "ver árbol"),
]
CONTROLES_JEFE = [
    ("WASD", "mover"),
    ("Ratón", "apuntar"),
    ("Clic", "disparar"),
    ("F", "habilidad"),
    ("Shift", "dash"),
    ("Tab", "ver árbol"),
]
CONTROLES_TERMINAL = [("← →", "elegir opción"), ("Enter", "confirmar")]
CONTROLES_CIUDAD = [
    ("WASD", "caminar"),
    ("E", "entrar"),
    ("G", "ruta sugerida"),
    ("Tab", "cambiar destino"),
    ("M", "mapa del mundo"),
    ("I", "estado de la ciudad"),
    ("H", "ayuda"),
    ("Esc", "menú principal"),
]
CONTROLES_DIALOGO = [("Enter", "continuar"), ("Esc", "saltar")]
CONTROLES_MAPA_MUNDO = [("Tab", "cambiar destino"), ("M", "volver a la ciudad")]
CONTROLES_FINAL = [("Enter", "continuar"), ("Esc", "salir")]
CONTROLES_MODO = [("← →", "elegir"), ("1-2", "directo"), ("Enter", "confirmar"), ("Esc", "volver")]
CONTROLES_MENU_PRINCIPAL = [
    ("↑ ↓", "elegir"),
    ("Enter / ✕", "confirmar"),
    ("Ratón", "señalar y clic"),
]
CONTROLES_VISTA_MENU = [("Enter / Esc / ○", "volver")]
CONTROLES_AJUSTES = [
    ("↑ ↓", "moverse"),
    ("← →", "cambiar"),
    ("Q E / L1 R1", "pestaña"),
    ("Enter / ✕", "activar"),
    ("Esc / ○", "cerrar"),
]
CONTROLES_SELECCION = [("← →", "elegir"), ("Enter", "confirmar"), ("1-4", "directo"), ("Esc", "volver")]
CONTROLES_SELECCION_DOS = [
    ("A D", "J1 elige"),
    ("Enter", "J1 confirma"),
    ("Cruceta", "J2 elige"),
    ("✕", "J2 confirma"),
    ("Retroceso / ○", "cambiar"),
    ("Esc", "volver"),
]
# Paneles laterales del cooperativo, por número de jugador (0 = J1):
# tecla de habilidad (rotula su barra) y controles clave.
TECLA_HABILIDAD_PANEL = ("F", "L1")
CONTROLES_PANEL = (
    [("SPACE", "Disparar"), ("Mouse", "Apuntar"), ("SHIFT", "Dash")],
    [("R2", "Disparar"), ("Stick R", "Apuntar"), ("✕", "Dash")],
)


def dibujar_hud_superior(pantalla, jugador, cantidad_enemigos, titulo, subtitulo, colapso,
                         etiqueta_jugador="J1"):
    """Franja superior completa: jugador, vida, habilidad, enemigos,
    título y barra de colapso. `jugador` puede ser None (mapa) y
    `etiqueta_jugador` None (cooperativo: cada uno tiene su panel)."""
    franja = pygame.Rect(0, 0, pantalla.get_width(), assets.ALTO_HUD)
    pygame.draw.rect(pantalla, assets.COLOR_FONDO, franja)
    pygame.draw.line(pantalla, assets.COLOR_LINEA_HUD, (0, franja.bottom), (franja.right, franja.bottom), 2)

    if etiqueta_jugador:
        dibujo.texto(pantalla, etiqueta_jugador, assets.POSICION_JUGADOR_HUD, assets.COLOR_TEAL,
                     assets.TAMANIO_FUENTE_TITULO, negrita=True, ancla="center")
    if jugador is not None:
        dibujar_corazones(pantalla, jugador.vida, jugador.vida_maxima)
        dibujar_habilidad(pantalla, jugador)

    if cantidad_enemigos is not None:
        x, y = assets.POSICION_ENEMIGOS_HUD
        dibujo.texto(pantalla, "Enemigos", (x, y), assets.COLOR_TEXTO_SECUNDARIO,
                     assets.TAMANIO_FUENTE_PEQUENA)
        dibujo.texto(pantalla, str(cantidad_enemigos), (x, y + 16), assets.COLOR_MAGENTA,
                     assets.TAMANIO_FUENTE_TITULO, negrita=True)

    if titulo:
        dibujo.texto(pantalla, titulo, assets.POSICION_TITULO_HUD, assets.COLOR_TEXTO_HUD,
                     assets.TAMANIO_FUENTE_MEDIA, negrita=True, ancla="center")
    if subtitulo:
        dibujo.texto(pantalla, subtitulo, assets.POSICION_SUBTITULO_HUD, assets.COLOR_TEXTO_SECUNDARIO,
                     assets.TAMANIO_FUENTE_PEQUENA, ancla="center")

    dibujar_barra_colapso(pantalla, colapso)


def dibujar_corazones(pantalla, vida, vida_maxima, origen=assets.POSICION_CORAZONES, por_fila=None):
    """Un corazón por punto de vida máxima; lleno, medio o vacío. Con
    `por_fila`, salta de fila cada esa cantidad de corazones."""
    x0, y0 = origen
    lleno = sprites.sprite(sprites.CORAZON, sprites.PALETA_CORAZON_LLENO)
    vacio = sprites.sprite(sprites.CORAZON, sprites.PALETA_CORAZON_VACIO)
    for i in range(math.ceil(vida_maxima)):
        fila, columna = divmod(i, por_fila) if por_fila else (0, i)
        posicion = (x0 + columna * assets.SEPARACION_CORAZONES, y0 + fila * assets.SEPARACION_CORAZONES)
        pantalla.blit(vacio, posicion)
        restante = vida - i
        if restante >= 1:
            pantalla.blit(lleno, posicion)
        elif restante > 0:
            # Medio corazón: solo la mitad izquierda del sprite lleno.
            mitad = pygame.Rect(0, 0, lleno.get_width() // 2, lleno.get_height())
            pantalla.blit(lleno, posicion, mitad)


def dibujar_habilidad(pantalla, jugador, origen=assets.POSICION_HABILIDAD_HUD,
                      ancho=assets.ANCHO_BARRA_HABILIDAD, tecla="F", etiqueta_abajo=False):
    x, y = origen
    fraccion = jugador.carga_habilidad / jugador.carga_maxima if jugador.carga_maxima else 0
    lista = jugador.habilidad_cargada()
    color = assets.COLOR_TEAL if lista else assets.COLOR_MORADO
    dibujo.texto(pantalla, tecla, (x, y - 3), color, assets.TAMANIO_FUENTE_PEQUENA, negrita=True)
    inicio_barra = x + 8 + 8 * len(tecla)
    dibujo.barra(pantalla, (inicio_barra, y, ancho, assets.ALTO_BARRA_HABILIDAD),
                 fraccion, color, borde=None, radio=2)
    etiqueta = "LISTA" if lista else f"{jugador.carga_habilidad:g}/{jugador.carga_maxima}"
    posicion = (inicio_barra, y + 10) if etiqueta_abajo else (inicio_barra + ancho + 8, y - 4)
    dibujo.texto(pantalla, etiqueta, posicion, assets.COLOR_TEXTO_SECUNDARIO, assets.TAMANIO_FUENTE_PEQUENA)


def dibujar_panel_jugador(pantalla, jugador, numero):
    """Panel lateral de un jugador en cooperativo (numero 0 = J1 a la
    izquierda, 1 = J2 a la derecha): etiqueta y rol, corazones, carga de
    la habilidad, indicador del dash y controles clave."""
    rect = dibujo.panel(pantalla, assets.RECTS_PANEL_JUGADOR[numero], assets.COLOR_FONDO_PANEL,
                        jugador.COLOR, 2, radio=8)
    x = rect.left + 9
    dibujo.texto(pantalla, f"J{numero + 1}", (x, rect.top + 6), jugador.COLOR, assets.TAMANIO_FUENTE_TITULO,
                 negrita=True)
    estado = jugador.NOMBRE if jugador.vivo else "CAÍDO"
    color_estado = assets.COLOR_TEXTO_SECUNDARIO if jugador.vivo else assets.COLOR_MAGENTA
    dibujo.texto(pantalla, estado, (x, rect.top + 34), color_estado, assets.TAMANIO_FUENTE_PEQUENA)
    dibujar_corazones(pantalla, jugador.vida, jugador.vida_maxima, (x, rect.top + 56),
                      assets.CORAZONES_POR_FILA_PANEL)
    dibujar_habilidad(pantalla, jugador, (x, rect.top + 114), assets.ANCHO_BARRA_HABILIDAD_PANEL,
                      tecla=TECLA_HABILIDAD_PANEL[numero], etiqueta_abajo=True)

    # Indicador del dash, con su estado a la derecha.
    radio = assets.RADIO_INDICADOR_DASH
    centro = (x + radio + 2, rect.top + 182)
    dibujar_indicador_dash(pantalla, jugador, centro)
    dash = jugador.dash
    texto_x = centro[0] + radio + 10
    dibujo.texto(pantalla, "Dash", (texto_x, centro[1] - 16), assets.COLOR_TEXTO_SECUNDARIO,
                 assets.TAMANIO_FUENTE_PEQUENA)
    if dash.fraccion_cooldown == 0:
        estado_dash, color_dash = "LISTO", assets.COLOR_TEAL
    else:
        estado_dash, color_dash = f"{dash.cooldown_restante:.1f}s", assets.COLOR_MORADO
    dibujo.texto(pantalla, estado_dash, (texto_x, centro[1] + 1), color_dash, assets.TAMANIO_FUENTE_PEQUENA,
                 negrita=True)

    # Controles clave: tecla en el color del rol, acción en gris.
    y = rect.top + 230
    pygame.draw.line(pantalla, assets.COLOR_LINEA_HUD, (x, y - 8), (rect.right - 9, y - 8), 1)
    for tecla, accion in CONTROLES_PANEL[numero]:
        marco = dibujo.texto(pantalla, tecla, (x, y), jugador.COLOR, assets.TAMANIO_FUENTE_MINI, negrita=True)
        dibujo.texto(pantalla, accion, (marco.right + 4, y), assets.COLOR_TEXTO_SECUNDARIO,
                     assets.TAMANIO_FUENTE_MINI)
        y += 20


def dibujar_indicador_dash(pantalla, jugador, centro):
    """Círculo con un muñeco corriendo que muestra el cooldown del dash.

    - Listo: a todo color, con un aura neón suave del color del rol.
    - Recargando: el icono a la mitad de brillo y el círculo llenándose
      desde abajo con una ola (seno que se desplaza con el tiempo).
    - Al quedar disponible: destello blanco de DURACION_FLASH_DASH s.
    Lee el estado de jugador.dash; no guarda nada propio.
    """
    dash = jugador.dash
    radio = assets.RADIO_INDICADOR_DASH
    listo = dash.fraccion_cooldown == 0
    color = jugador.COLOR
    color_icono = color if listo else _oscurecer(color, assets.OSCURECER_INDICADOR_DASH)

    if listo:
        _dibujar_aura(pantalla, centro, radio, color)
    pygame.draw.circle(pantalla, assets.COLOR_FONDO_INDICADOR_DASH, centro, radio)
    if not listo:
        _dibujar_ola(pantalla, centro, radio, color, 1 - dash.fraccion_cooldown)

    icono = sprites.sprite(sprites.CORRIENDO, {"c": color_icono}, assets.ESCALA_ICONO_DASH)
    pantalla.blit(icono, icono.get_rect(center=centro))
    pygame.draw.circle(pantalla, color_icono, centro, radio, 2)

    if dash.tiempo_listo < assets.DURACION_FLASH_DASH:
        # El destello se apaga a lo largo de su duración.
        alfa = round(255 * (1 - dash.tiempo_listo / assets.DURACION_FLASH_DASH))
        lado = (radio + 8) * 2
        capa = pygame.Surface((lado, lado), pygame.SRCALPHA)
        pygame.draw.circle(capa, (*assets.COLOR_FLASH_DASH, alfa), (lado // 2, lado // 2), radio + 6, 4)
        pantalla.blit(capa, capa.get_rect(center=centro))


def _dibujar_aura(pantalla, centro, radio, color):
    """Anillos concéntricos cada vez más transparentes hacia afuera."""
    capas = assets.CAPAS_AURA_DASH
    lado = (radio + capas * 2 + 2) * 2
    capa = pygame.Surface((lado, lado), pygame.SRCALPHA)
    for i in range(capas, 0, -1):
        alfa = round(assets.ALFA_AURA_DASH * (capas - i + 1) / capas)
        pygame.draw.circle(capa, (*color[:3], alfa), (lado // 2, lado // 2), radio + i * 2, 2)
    pantalla.blit(capa, capa.get_rect(center=centro))


def _dibujar_ola(pantalla, centro, radio, color, llenado):
    """Llena el círculo desde abajo hasta `llenado` (0-1) con una ola
    en la superficie, recortada a la forma del círculo."""
    lado = radio * 2
    nivel = lado * (1 - llenado)  # y de la superficie del agua (0 = arriba)
    t = pygame.time.get_ticks() / 1000
    puntos = [
        (x, nivel + assets.AMPLITUD_OLA_DASH
         * math.sin(2 * math.pi * x / assets.LARGO_OLA_DASH + t * assets.VELOCIDAD_OLA_DASH))
        for x in range(0, lado + 1, 2)
    ]
    agua = pygame.Surface((lado, lado), pygame.SRCALPHA)
    pygame.draw.polygon(agua, (*color[:3], assets.ALFA_AGUA_INDICADOR_DASH), puntos + [(lado, lado), (0, lado)])
    # Recorte circular: fuera del círculo la máscara es transparente y
    # BLEND_RGBA_MIN deja el agua en alfa 0.
    mascara = pygame.Surface((lado, lado), pygame.SRCALPHA)
    pygame.draw.circle(mascara, (255, 255, 255, 255), (radio, radio), radio)
    agua.blit(mascara, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    pantalla.blit(agua, (centro[0] - radio, centro[1] - radio))


def _oscurecer(color, factor):
    return tuple(round(c * factor) for c in color[:3])


def dibujar_barra_colapso(pantalla, colapso, rect=assets.RECT_BARRA_COLAPSO,
                          posicion_etiqueta=assets.POSICION_ETIQUETA_COLAPSO,
                          posicion_valor=assets.POSICION_VALOR_COLAPSO):
    dibujo.texto(pantalla, "Barra de colapso electoral", posicion_etiqueta,
                 assets.COLOR_TEXTO_SECUNDARIO, assets.TAMANIO_FUENTE_PEQUENA)
    dibujo.barra(pantalla, rect, colapso.valor / 100.0)
    dibujo.texto(pantalla, f"{colapso.valor:.1f}%", posicion_valor, assets.COLOR_AMARILLO,
                 assets.TAMANIO_FUENTE_NORMAL, negrita=True, ancla="midleft")


def dibujar_barra_controles(pantalla, controles):
    """Franja inferior con un chip de tecla + descripción por control."""
    alto = assets.ALTO_BARRA_CONTROLES
    franja = pygame.Rect(0, pantalla.get_height() - alto, pantalla.get_width(), alto)
    pygame.draw.rect(pantalla, assets.COLOR_FONDO, franja)
    pygame.draw.line(pantalla, assets.COLOR_LINEA_HUD, (0, franja.top), (franja.right, franja.top), 2)

    # Se mide todo primero para centrar la fila completa.
    from src.ui.fuentes import fuente  # import local: evita ciclo en tests sin fuentes

    f_chip = fuente(assets.TAMANIO_FUENTE_PEQUENA, True)
    f_desc = fuente(assets.TAMANIO_FUENTE_NORMAL)
    anchos = []
    for tecla, descripcion in controles:
        anchos.append(f_chip.size(tecla)[0] + assets.MARGEN_CHIP * 2 + 8 + f_desc.size(descripcion)[0])
    total = sum(anchos) + assets.SEPARACION_CONTROLES * (len(controles) - 1)
    x = (pantalla.get_width() - total) // 2
    y = franja.centery
    for (tecla, descripcion), ancho in zip(controles, anchos):
        rect = dibujo.chip(pantalla, tecla, (x, y), ancla="midleft")
        dibujo.texto(pantalla, descripcion, (rect.right + 8, y), assets.COLOR_TEXTO_SECUNDARIO,
                     assets.TAMANIO_FUENTE_NORMAL, ancla="midleft")
        x += ancho + assets.SEPARACION_CONTROLES
