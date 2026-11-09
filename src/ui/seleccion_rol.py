"""Lobby: selección de rol con la paleta neón de Civitas (solo presentación).

Una tarjeta por rol: número (atajo 1-4 del J1), sprite animado (idle;
camina cuando un cursor la elige), nombre, habilidad con una descripción
corta y, por estadística (Velocidad, Cadencia, Daño, Vida, Carga), una
barra de 10 segmentos con su puntaje "7/10" (src/core/puntajes_roles.py,
entre el mínimo y el máximo de los 4 roles): de un vistazo se ve quién
es rápido, quién aguanta y a quién le cuesta menos llenar la habilidad,
sin multiplicadores. Los valores reales de balance no cambian.

Abajo, un panel con el resumen de la partida, la sinergia del equipo
elegido (src/ui/lobby.py), el volumen y los controles. El fondo es la
portada con siluetas de árboles neón que se mecen, una rejilla neón y
partículas que se mueven despacio (se
quedan quietas con "reducir movimiento").

Con la escena del hotel (src/ui/escena_lobby_render.py, arte Backrooms)
el fondo es la recepción viva: cada rol posa en su puesto sobre su
tarjeta (las tarjetas son más bajas y ya no traen el sprite) y una
cartelera en la pared muestra el tablero de mazmorras
(src/dungeon/registro_mazmorras.py). Sin ese arte, el lobby es el de
siempre.

VistaSeleccion guarda solo estado de dibujo (cuánto está levantada cada
tarjeta, el fundido de entrada y salida); quién eligió qué vive en
SeleccionRoles (src/ui/seleccion.py).
"""

import math

import pygame

from src.core import assets
from src.core.balance import ESTADISTICAS_VISIBLES, PUNTAJE_MAXIMO
from src.core.puntajes_roles import puntajes
from src.dungeon import registro_mazmorras
from src.ui import cargador_assets, dibujo, kit, layout, lobby, sprites

TITULO = "Elige tu personaje"
TITULO_DOS = "Elijan sus personajes"
SUBTITULO = "Civitas · 4 roles, una ciudad al borde del colapso"
SUBTITULO_DOS = "J1 con teclado y ratón · J2 con el control · pueden repetir rol"


def rect_tarjeta(indice, hotel=False):
    """Rect de la tarjeta `indice` en reposo (también para el ratón)."""
    if hotel:
        x, y = assets.ORIGEN_COLUMNAS_HOTEL
        alto = assets.ALTO_TARJETA_HOTEL
    else:
        x, y = assets.ORIGEN_COLUMNAS_SELECCION
        alto = assets.ALTO_TARJETA_SELECCION
    return pygame.Rect(x + indice * assets.ANCHO_COLUMNA_SELECCION, y, assets.ANCHO_TARJETA_SELECCION, alto)


def tarjeta_en(posicion, cantidad, hotel=False):
    """Índice de la tarjeta bajo `posicion` (px de pantalla), o None."""
    for indice in range(cantidad):
        if rect_tarjeta(indice, hotel).collidepoint(posicion):
            return indice
    return None


class VistaSeleccion:
    def __init__(self, cantidad_roles, escena=None, tablero=()):
        """`escena`: EscenaLobby del hotel o None (lobby clásico);
        `tablero`: filas de registro_mazmorras.filas_tablero."""
        self.elevacion = [0.0] * cantidad_roles
        self.tiempo = 0.0
        self.salida = None  # s desde que todos confirmaron (fundido de salida)
        self.escena = escena
        self.tablero = list(tablero)

    @property
    def hotel(self):
        return self.escena is not None

    def tarjeta_en(self, posicion, cantidad):
        return tarjeta_en(posicion, cantidad, self.hotel)

    def actualizar(self, dt, seleccion):
        self.tiempo += dt
        encima = set(seleccion.indices())
        mezcla = 1 - math.exp(-assets.SUAVIZADO_TARJETA_LOBBY * dt)
        for i, actual in enumerate(self.elevacion):
            objetivo = assets.ELEVACION_TARJETA_LOBBY if i in encima else 0.0
            self.elevacion[i] = actual + (objetivo - actual) * mezcla
        if self.salida is not None:
            self.salida += dt

    def empezar_salida(self):
        if self.salida is None:
            self.salida = 0.0

    @property
    def salida_terminada(self):
        return self.salida is not None and self.salida >= assets.DURACION_SALIDA_LOBBY

    def dibujar(self, pantalla, clases_rol, seleccion, volumen, silenciado, reducir_movimiento=False):
        """`volumen`: porcentaje general a mostrar; `silenciado`: tecla N."""
        t = 0.0 if reducir_movimiento else self.tiempo
        if self.hotel:
            self._dibujar_hotel(pantalla, clases_rol, seleccion, volumen, silenciado, reducir_movimiento)
            return
        dibujar_fondo_neon(pantalla, t)
        dos = len(seleccion.cursores) > 1
        cx, cy = assets.POSICION_TITULO_SELECCION
        _texto_neon(pantalla, TITULO_DOS if dos else TITULO, (cx, cy), assets.TAMANIO_FUENTE_GRANDE)
        dibujo.texto(pantalla, SUBTITULO_DOS if dos else SUBTITULO, (cx, cy + 34), assets.COLOR_TEXTO_SECUNDARIO,
                     assets.TAMANIO_FUENTE_NORMAL, ancla="center")

        for indice, clase in enumerate(clases_rol):
            encima = [(n, cursor.confirmado) for n, cursor in enumerate(seleccion.cursores) if cursor.indice == indice]
            _dibujar_tarjeta(pantalla, indice, clase, encima, puntajes(clase.rol), self.elevacion[indice], t)

        roles = [clases_rol[cursor.indice].rol for cursor in seleccion.cursores]
        _dibujar_resumen(pantalla, seleccion, clases_rol, roles, volumen, silenciado)
        self._dibujar_fundido(pantalla)

    def _dibujar_hotel(self, pantalla, clases_rol, seleccion, volumen, silenciado, reducir_movimiento):
        t = 0.0 if reducir_movimiento else self.tiempo
        posan = []
        for indice, clase in enumerate(clases_rol):
            encima = [c for c in seleccion.cursores if c.indice == indice]
            posan.append((clase, bool(encima), any(c.confirmado for c in encima)))
        self.escena.dibujar(pantalla, posan, self.tiempo, reducir_movimiento)

        dos = len(seleccion.cursores) > 1
        cx, cy = assets.POSICION_TITULO_HOTEL
        franja = pygame.Rect(0, 0, assets.ANCHO_VELO_TITULO_HOTEL, 78)
        franja.center = (cx, cy + 14)
        dibujo.panel_alfa(pantalla, franja, (0, 0, 0, assets.ALFA_VELO_TITULO_HOTEL), radio=14)
        _texto_neon(pantalla, TITULO_DOS if dos else TITULO, (cx, cy), assets.TAMANIO_FUENTE_GRANDE)
        dibujo.texto(pantalla, SUBTITULO_DOS if dos else SUBTITULO, (cx, cy + 32), assets.COLOR_TEXTO_HUD,
                     assets.TAMANIO_FUENTE_PEQUENA, ancla="center")
        _dibujar_tablero(pantalla, self.tablero)

        for indice, clase in enumerate(clases_rol):
            encima = [(n, cursor.confirmado) for n, cursor in enumerate(seleccion.cursores) if cursor.indice == indice]
            _dibujar_tarjeta_hotel(pantalla, indice, clase, encima, puntajes(clase.rol), self.elevacion[indice], t)
        roles = [clases_rol[cursor.indice].rol for cursor in seleccion.cursores]
        _dibujar_resumen(pantalla, seleccion, clases_rol, roles, volumen, silenciado, assets.RECT_PANEL_RESUMEN_HOTEL)
        self._dibujar_fundido(pantalla)

    def _dibujar_fundido(self, pantalla):
        if self.salida is not None:
            fraccion = min(1.0, self.salida / assets.DURACION_SALIDA_LOBBY)
        else:
            fraccion = max(0.0, 1 - self.tiempo / assets.DURACION_ENTRADA_LOBBY)
        if fraccion > 0:
            kit.velo(pantalla, round(255 * fraccion), (0, 0, 0))


def _texto_neon(pantalla, cadena, centro, tamanio):
    """Título con resplandor: copias desplazadas en violeta debajo del texto."""
    for dx, dy in ((-2, 0), (2, 0), (0, -2), (0, 2)):
        dibujo.texto(pantalla, cadena, (centro[0] + dx, centro[1] + dy), assets.COLOR_MORADO_OSCURO, tamanio,
                     negrita=True, ancla="center")
    dibujo.texto(pantalla, cadena, centro, assets.COLOR_TEXTO_HUD, tamanio, negrita=True, ancla="center")


def dibujar_fondo_neon(pantalla, t):
    """Fondo del lobby (portada, árboles, rejilla y partículas): también lo usa
    la pantalla de instrucciones de mazmorra."""
    fondo = sprites.fondo_historia(assets.FONDO_PROLOGO, pantalla.get_size())
    if fondo is not None:
        pantalla.blit(fondo, (0, 0))
        kit.velo(pantalla, 215)
    else:
        pantalla.fill(assets.COLOR_FONDO)
    ancho, alto = pantalla.get_size()
    _dibujar_arboles(pantalla, t)
    capa = pygame.Surface((ancho, alto), pygame.SRCALPHA)
    # Rejilla neón en perspectiva bajo el horizonte: las líneas bajan despacio.
    horizonte = alto * 0.55
    fase = (t * 0.25) % 1.0
    for i in range(12):
        avance = ((i + fase) / 12) ** 2
        y = round(horizonte + avance * (alto - horizonte))
        pygame.draw.line(capa, (*assets.COLOR_REJILLA_LOBBY, round(20 + 50 * avance)), (0, y), (ancho, y))
    fuga = (ancho / 2, horizonte)
    for i in range(-10, 11):
        pygame.draw.line(capa, (*assets.COLOR_REJILLA_LOBBY, 30), fuga, (ancho / 2 + i * 150, alto))
    # Partículas que suben con un vaivén suave.
    for i in range(assets.CANTIDAD_PARTICULAS_LOBBY):
        velocidad = 14 + (i * 37) % 23
        x = (i * 211) % ancho + 12 * math.sin(t * 0.8 + i)
        y = alto - ((t * velocidad + i * 53) % (alto + 40))
        color = assets.COLOR_NEON_LOBBY if i % 2 else assets.COLOR_NEON_LOBBY_2
        pygame.draw.circle(capa, (*color, 70 + (i * 13) % 80), (round(x), round(y)), 1 + i % 3)
    pantalla.blit(capa, (0, 0))


_siluetas = {}


def _silueta(numero, escala):
    """Árbol del pack como silueta neón: relleno violeta translúcido y borde
    más claro (cacheada). None si falta el PNG: el fondo sigue sin árboles."""
    clave = (numero, escala)
    if clave not in _siluetas:
        arbol = cargador_assets.arbol(numero, escala)
        silueta = None
        if arbol is not None:
            mascara = pygame.mask.from_surface(arbol)
            silueta = mascara.to_surface(setcolor=(*assets.COLOR_SILUETA_LOBBY, assets.ALFA_SILUETA_LOBBY),
                                         unsetcolor=(0, 0, 0, 0))
            for punto in mascara.outline(escala):
                pygame.draw.rect(silueta, (*assets.COLOR_BORDE_SILUETA_LOBBY, 170), (*punto, escala, escala))
        _siluetas[clave] = silueta
    return _siluetas[clave]


def _dibujar_arboles(pantalla, t):
    """Siluetas de árboles al fondo, apoyadas abajo y meciéndose apenas
    (cada una con su fase); detrás de las tarjetas, nunca encima."""
    ancho, alto = pantalla.get_size()
    for i, (numero, escala, x_relativa) in enumerate(assets.ARBOLES_LOBBY):
        silueta = _silueta(numero, escala)
        if silueta is None:
            continue
        angulo = assets.AMPLITUD_BALANCEO_LOBBY * math.sin(t * 0.7 + i * 1.3)
        figura = pygame.transform.rotate(silueta, angulo) if angulo else silueta
        deriva = 6 * math.sin(t * 0.15 + i)  # parallax muy suave
        pantalla.blit(figura, figura.get_rect(midbottom=(round(ancho * x_relativa + deriva), alto)))


def _dibujar_tarjeta(pantalla, indice, clase, encima, puntajes_rol, elevacion, t):
    resaltada = bool(encima)
    confirmada = any(confirmado for _, confirmado in encima)
    tarjeta = rect_tarjeta(indice).move(0, -round(elevacion))
    if resaltada:
        latido = 0.5 + 0.5 * math.sin(t * 4)
        pygame.draw.rect(pantalla, clase.COLOR, tarjeta.inflate(round(6 + 4 * latido), round(6 + 4 * latido)), 2,
                         border_radius=12)
    kit.panel(pantalla, tarjeta, clase.COLOR if resaltada else assets.COLOR_BORDE_VIDRIO, alfa=240,
              filo="todo" if resaltada else "arriba")
    if confirmada:
        dibujo.panel_alfa(pantalla, tarjeta, (*clase.COLOR, assets.ALFA_TARJETA_CONFIRMADA), radio=10)
    x = tarjeta.left + 16
    y = tarjeta.top + 14
    dibujo.chip(pantalla, str(indice + 1), (x, y), clase.COLOR, assets.COLOR_FONDO, clase.COLOR,
                assets.TAMANIO_FUENTE_MEDIA, alto=30, margen=11)
    _dibujar_chips_cursor(pantalla, encima, (tarjeta.right - 12, y), clase.COLOR)

    # Sprite animado sobre un halo del color del rol.
    base = (tarjeta.centerx, tarjeta.top + 150)
    halo = pygame.Surface((180, 60), pygame.SRCALPHA)
    pygame.draw.ellipse(halo, (*clase.COLOR, 70 if resaltada else 35), halo.get_rect())
    pantalla.blit(halo, halo.get_rect(center=(base[0], base[1] - 4)))
    respiro = round(2 * math.sin(t * 2.4 + indice))
    imagen = sprites.sprite_jugador(clase.COLOR, escala=assets.ESCALA_SPRITE_LOBBY, rol=clase.rol,
                                    tiempo=t, caminando=resaltada)
    pantalla.blit(imagen, imagen.get_rect(midbottom=(base[0], base[1] + respiro)))

    y = tarjeta.top + 172
    dibujo.texto(pantalla, clase.NOMBRE, (tarjeta.centerx, y), clase.COLOR, assets.TAMANIO_FUENTE_TITULO,
                 negrita=True, ancla="center")
    y += 24
    dibujo.texto(pantalla, f"{clase.NOMBRE_HABILIDAD} · {lobby.PAPEL[clase.rol]}", (tarjeta.centerx, y),
                 assets.COLOR_TEXTO_HUD, assets.TAMANIO_FUENTE_PEQUENA, negrita=True, ancla="center")
    y += 14
    dibujo.parrafo(pantalla, lobby.DESCRIPCION_HABILIDAD[clase.rol], (tarjeta.centerx, y), tarjeta.width - 28,
                   assets.COLOR_TEXTO_SECUNDARIO, assets.TAMANIO_FUENTE_PEQUENA, interlineado=2, centrado=True)

    y = tarjeta.top + 268
    for etiqueta, atributo in ESTADISTICAS_VISIBLES:
        dibujo.texto(pantalla, etiqueta, (x, y), assets.COLOR_TEXTO_HUD, assets.TAMANIO_FUENTE_PEQUENA)
        _barra_segmentada(pantalla, (x + assets.DESPLAZAMIENTO_BARRA_X, y + 3), puntajes_rol[atributo], clase.COLOR)
        dibujo.texto(pantalla, lobby.valor_estadistica(clase.rol, atributo), (tarjeta.right - 14, y),
                     assets.COLOR_TEXTO_HUD, assets.TAMANIO_FUENTE_PEQUENA, negrita=True, ancla="topright")
        y += assets.SEPARACION_FILAS_SELECCION


def _dibujar_tarjeta_hotel(pantalla, indice, clase, encima, puntajes_rol, elevacion, t):
    """Tarjeta compacta del lobby del hotel: el sprite posa en la escena,
    sobre la tarjeta."""
    resaltada = bool(encima)
    confirmada = any(confirmado for _, confirmado in encima)
    tarjeta = rect_tarjeta(indice, hotel=True).move(0, -round(elevacion))
    if resaltada:
        latido = 0.5 + 0.5 * math.sin(t * 4)
        pygame.draw.rect(pantalla, clase.COLOR, tarjeta.inflate(round(6 + 4 * latido), round(6 + 4 * latido)), 2,
                         border_radius=12)
    kit.panel(pantalla, tarjeta, clase.COLOR if resaltada else assets.COLOR_BORDE_VIDRIO,
              alfa=assets.ALFA_TARJETA_HOTEL, filo="todo" if resaltada else "arriba")
    if confirmada:
        dibujo.panel_alfa(pantalla, tarjeta, (*clase.COLOR, assets.ALFA_TARJETA_CONFIRMADA), radio=10)
    x = tarjeta.left + 16
    dibujo.chip(pantalla, str(indice + 1), (x, tarjeta.top + 12), clase.COLOR, assets.COLOR_FONDO, clase.COLOR,
                assets.TAMANIO_FUENTE_MEDIA, alto=30, margen=11)
    _dibujar_chips_cursor(pantalla, encima, (tarjeta.right - 12, tarjeta.top + 12), clase.COLOR)

    y = tarjeta.top + 58
    dibujo.texto(pantalla, clase.NOMBRE, (tarjeta.centerx, y), clase.COLOR, assets.TAMANIO_FUENTE_TITULO,
                 negrita=True, ancla="center")
    y += 22
    layout.texto_en_ancho(pantalla, f"{clase.NOMBRE_HABILIDAD} · {lobby.PAPEL[clase.rol]}", (tarjeta.centerx, y),
                          tarjeta.width - 24, assets.COLOR_TEXTO_HUD, assets.TAMANIO_FUENTE_PEQUENA, negrita=True,
                          ancla="midtop")
    y += 18
    dibujo.parrafo(pantalla, lobby.DESCRIPCION_HABILIDAD[clase.rol], (tarjeta.centerx, y), tarjeta.width - 28,
                   assets.COLOR_TEXTO_SECUNDARIO, assets.TAMANIO_FUENTE_PEQUENA, interlineado=2, centrado=True)
    y = tarjeta.top + 138
    for etiqueta, atributo in ESTADISTICAS_VISIBLES:
        dibujo.texto(pantalla, etiqueta, (x, y), assets.COLOR_TEXTO_HUD, assets.TAMANIO_FUENTE_PEQUENA)
        _barra_segmentada(pantalla, (x + assets.DESPLAZAMIENTO_BARRA_X, y + 3), puntajes_rol[atributo], clase.COLOR)
        dibujo.texto(pantalla, lobby.valor_estadistica(clase.rol, atributo), (tarjeta.right - 14, y),
                     assets.COLOR_TEXTO_HUD, assets.TAMANIO_FUENTE_PEQUENA, negrita=True, ancla="topright")
        y += assets.SEPARACION_FILAS_HOTEL


def _dibujar_tablero(pantalla, filas):
    """Cartelera de la recepción: cada mazmorra del registro con su
    toxicidad y su estado."""
    if not filas:
        return
    rect = pygame.Rect(assets.RECT_TABLERO_MAZMORRAS)
    pygame.draw.rect(pantalla, assets.COLOR_MARCO_TABLERO, rect, border_radius=6)
    interior = rect.inflate(-8, -8)
    pygame.draw.rect(pantalla, assets.COLOR_TABLERO, interior, border_radius=4)
    hechas, total = registro_mazmorras.resumen(filas)
    x, y = interior.left + 10, interior.top + 7
    dibujo.texto(pantalla, "MAZMORRAS", (x, y), assets.COLOR_TEXTO_TABLERO, assets.TAMANIO_FUENTE_PEQUENA, negrita=True)
    dibujo.texto(pantalla, f"{hechas}/{total} purificadas", (interior.right - 10, y), assets.COLOR_TEXTO_TABLERO,
                 assets.TAMANIO_FUENTE_PEQUENA, ancla="topright")
    y += 21
    pygame.draw.line(pantalla, assets.COLOR_MARCO_TABLERO, (x, y), (interior.right - 10, y))
    paso = (interior.bottom - 4 - (y + 6)) / max(1, len(filas))
    for i, fila in enumerate(filas):
        fy = round(y + 6 + i * paso)
        completada = fila.estado == registro_mazmorras.ESTADO_COMPLETADA
        color_estado = assets.COLOR_COMPLETADA_TABLERO if completada else assets.COLOR_PENDIENTE_TABLERO
        nombre = fila.nombre + (" · jefe" if fila.tipo == registro_mazmorras.TIPO_FINAL else "")
        layout.texto_en_ancho(pantalla, nombre, (x, fy), assets.ANCHO_NOMBRE_TABLERO, assets.COLOR_TEXTO_TABLERO,
                              assets.TAMANIO_FUENTE_PEQUENA, minimo=assets.TAMANIO_FUENTE_MINI)
        dibujo.texto(pantalla, f"Tox {fila.toxicidad}", (x + assets.ANCHO_NOMBRE_TABLERO + 6, fy),
                     _color_toxicidad(fila.toxicidad), assets.TAMANIO_FUENTE_PEQUENA, negrita=True)
        dibujo.texto(pantalla, fila.estado, (interior.right - 10, fy), color_estado, assets.TAMANIO_FUENTE_PEQUENA,
                     ancla="topright")


def _color_toxicidad(nivel):
    if nivel >= assets.TOXICIDAD_ALTA_TABLERO:
        return assets.COLOR_TOXICIDAD_ALTA_TABLERO
    if nivel >= assets.TOXICIDAD_MEDIA_TABLERO:
        return assets.COLOR_PENDIENTE_TABLERO
    return assets.COLOR_COMPLETADA_TABLERO


def _barra_segmentada(pantalla, origen, puntaje, color):
    """PUNTAJE_MAXIMO casillas; las primeras `puntaje` encendidas."""
    hueco = assets.SEPARACION_SEGMENTOS_BARRA
    lado = (assets.ANCHO_MAXIMO_BARRA - hueco * (PUNTAJE_MAXIMO - 1)) // PUNTAJE_MAXIMO
    x, y = origen
    for i in range(PUNTAJE_MAXIMO):
        relleno = color if i < puntaje else assets.COLOR_SEGMENTO_VACIO
        pygame.draw.rect(pantalla, relleno, (x + i * (lado + hueco), y, lado, assets.ALTO_BARRA), border_radius=2)


def _dibujar_resumen(pantalla, seleccion, clases_rol, roles, volumen, silenciado,
                     rect=assets.RECT_PANEL_RESUMEN_LOBBY):
    panel = kit.panel(pantalla, rect, assets.COLOR_NEON_LOBBY, alfa=220)
    x, y = panel.left + 18, panel.top + 10
    estrellas, texto = lobby.sinergia(roles)
    dibujo.texto(pantalla, "SINERGIA", (x, y), assets.COLOR_NEON_LOBBY_2, assets.TAMANIO_FUENTE_PEQUENA, negrita=True)
    if estrellas:
        for i in range(lobby.MAXIMO_ESTRELLAS):
            _estrella(pantalla, (x + 100 + i * 18, y + 8), 7, i < estrellas)
    dibujo.texto(pantalla, texto, (x + 160, y), assets.COLOR_TEXTO_HUD, assets.TAMANIO_FUENTE_PEQUENA)
    estado = "Silencio (N)" if silenciado else f"Volumen {volumen} %"
    dibujo.chip(pantalla, estado, (panel.right - 16, y - 3), assets.COLOR_MAGENTA if silenciado else assets.COLOR_TEAL,
                assets.COLOR_FONDO, assets.COLOR_MAGENTA if silenciado else assets.COLOR_TEAL, alto=24, ancla="topright")
    y += 28
    if len(seleccion.cursores) > 1:
        partes = []
        for n, cursor in enumerate(seleccion.cursores):
            nombre = clases_rol[cursor.indice].NOMBRE
            partes.append(f"J{n + 1}: {nombre} ✓" if cursor.confirmado else f"J{n + 1}: eligiendo…")
        dibujo.texto(pantalla, "   ·   ".join(partes) + "     " + lobby.RESUMEN_PARTIDA, (x, y), assets.COLOR_TEXTO_HUD,
                     assets.TAMANIO_FUENTE_PEQUENA)
    else:
        dibujo.texto(pantalla, lobby.RESUMEN_PARTIDA, (x, y), assets.COLOR_TEXTO_HUD, assets.TAMANIO_FUENTE_PEQUENA)
    y += 26
    dibujo.texto(pantalla, lobby.LINEA_CONTROLES, (x, y), assets.COLOR_TEXTO_SECUNDARIO, assets.TAMANIO_FUENTE_PEQUENA)


def _estrella(pantalla, centro, radio, llena):
    """Estrella de 5 puntas (la fuente no trae el glifo ★)."""
    puntos = []
    for i in range(10):
        r = radio if i % 2 == 0 else radio * 0.45
        angulo = math.pi / 2 + i * math.pi / 5
        puntos.append((centro[0] + r * math.cos(angulo), centro[1] - r * math.sin(angulo)))
    if llena:
        pygame.draw.polygon(pantalla, assets.COLOR_AMARILLO, puntos)
    else:
        pygame.draw.polygon(pantalla, assets.COLOR_TEXTO_APAGADO, puntos, 1)


def _dibujar_chips_cursor(pantalla, encima, esquina_derecha, color):
    """Chips "J1"/"J2" del color del rol de la tarjeta (con ✓ si
    confirmó), alineados a la derecha."""
    x, y = esquina_derecha
    for numero, confirmado in reversed(encima):
        etiqueta = f"J{numero + 1} ✓" if confirmado else f"J{numero + 1}"
        rect = dibujo.chip(pantalla, etiqueta, (x, y), assets.COLOR_FONDO, color, color,
                           assets.TAMANIO_FUENTE_NORMAL, alto=30, margen=9, ancla="topright")
        x = rect.left - 6
