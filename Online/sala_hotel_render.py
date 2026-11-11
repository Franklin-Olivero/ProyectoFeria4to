"""Dibujo de la sala de espera Online como un salón del hotel Backrooms.

Reutiliza la escena del lobby del hotel (src/ui/escena_lobby_render.EscenaLobby:
tiles y props pre-renderizados, luces que fallan, el reloj con la hora real y
el polvo) con la composición de Online/datos/sala_hotel.json, corrida a la
esquina de la sala. Encima va lo interactivo, con el morado de Civitas:

    - la recepción (elegir rol), con su cartel;
    - los cuatro vestidores (carritos de equipaje), cada uno con un cartel
      numerado y la vitrina de la cabeza y el traje de un rol;
    - el halo y la invitación "[E] o clic" del que está al alcance.

Si falta el arte Backrooms, `dibujar_sala` devuelve False y Online/lobby.py
dibuja la sala neón de antes. La disposición está en Online/sala_hotel.py.
"""

import math

import pygame

from src.core import assets
from src.ui import cargador_backrooms, dibujo, sprites
from src.ui.escena_lobby_render import EscenaLobby

from Online import sala_hotel

COLOR_ACENTO = assets.COLOR_CIVITAS
COLOR_FONDO_CARTEL = (30, 18, 56)
COLOR_MARCO_SALA = (92, 60, 160)
ALTO_CARTEL = 22
ESCALA_VITRINA = 2

_escena = {}  # grade -> EscenaLobby (o None si no se pudo armar)


def escena(grade=assets.GRADE_LOBBY):
    """La escena pre-renderizada del salón (se arma una sola vez), o None."""
    if grade not in _escena:
        _escena[grade] = None
        if cargador_backrooms.disponible(grade):
            plantilla = sala_hotel.plantilla()
            if plantilla is not None:
                try:
                    salon = EscenaLobby(plantilla, grade)
                    salon.desplazamiento = sala_hotel.ORIGEN
                    _escena[grade] = salon
                except (pygame.error, KeyError, ValueError, TypeError) as error:
                    print(f"[lobby online] salón del hotel desactivado: {error}")
    return _escena[grade]


def _cartel(pantalla, texto, centro, activo):
    color = COLOR_ACENTO if activo else assets.COLOR_TEXTO_SECUNDARIO
    return dibujo.chip(pantalla, texto, centro, assets.COLOR_TEXTO_HUD if activo else color, COLOR_FONDO_CARTEL,
                       color, assets.TAMANIO_FUENTE_MINI, ancla="center", alto=ALTO_CARTEL, margen=8)


def _halo(pantalla, rect, tiempo):
    pulso = int(40 + 25 * math.sin(tiempo * 7))
    dibujo.panel_alfa(pantalla, pygame.Rect(rect).inflate(26, 26), (*COLOR_ACENTO, pulso), radio=14)


def _invitacion(pantalla, texto, centro, tiempo):
    y = centro[1] + math.sin(tiempo * 6) * 3
    dibujo.chip(pantalla, texto, (centro[0], y), assets.COLOR_TEXTO_HUD, COLOR_FONDO_CARTEL, COLOR_ACENTO,
                assets.TAMANIO_FUENTE_PEQUENA, ancla="center", alto=26)


def dibujar_sala(pantalla, tiempo, cerca_recepcion, vestidor_cercano, composicion, reducir_movimiento=False):
    """El salón con sus carteles. False si no hay arte (la sala neón lo reemplaza)."""
    salon = escena()
    if salon is None or composicion is None:
        return False
    salon.dibujar(pantalla, [], tiempo, reducir_movimiento)
    sala = pygame.Rect(sala_hotel.disposicion(composicion).sala)
    pygame.draw.rect(pantalla, COLOR_MARCO_SALA, sala, 3, border_radius=6)
    objetos = composicion.get("objetos", [])
    recepcion = next((o for o in objetos if o.get("rol") == "recepcion"), None)
    vestidores = [o for o in objetos if o.get("rol") == "vestidor"]
    if recepcion is not None:
        dibujo_rect = pygame.Rect(sala_hotel.rect_objeto(recepcion))
        if cerca_recepcion:
            _halo(pantalla, dibujo_rect, tiempo)
            _invitacion(pantalla, "Presiona [E] o clic: elegir rol", (dibujo_rect.centerx, dibujo_rect.top - 18), tiempo)
        else:
            _cartel(pantalla, "RECEPCIÓN · ROLES", (dibujo_rect.centerx, dibujo_rect.top - 14), False)
    for numero, vestidor in enumerate(vestidores):
        dibujo_rect = pygame.Rect(sala_hotel.rect_objeto(vestidor))
        cerca = numero == vestidor_cercano
        if cerca:
            _halo(pantalla, dibujo_rect, tiempo)
        vitrina = _vitrina(pantalla, numero, (dibujo_rect.centerx, dibujo_rect.top - 6), cerca)
        _cartel(pantalla, f"VESTIDOR {numero + 1}", (dibujo_rect.centerx, dibujo_rect.bottom + 12), cerca)
        if cerca:
            arriba = vitrina.top if vitrina is not None else dibujo_rect.top
            _invitacion(pantalla, "Presiona [E] o clic: vestidor", (dibujo_rect.centerx, arriba - 18), tiempo)
    return True


def _vitrina(pantalla, numero, abajo_centro, activa):
    """Cartelito sobre el carrito con la cabeza y el traje de un rol (lo que se puede probar)."""
    rol = assets.ROLES_APARIENCIA[numero % len(assets.ROLES_APARIENCIA)]
    partes = [sprites.sprite_parte_jugador(simbolos, rol, None, ESCALA_VITRINA)
              for simbolos in (assets.SIMBOLOS_CABEZA, assets.SIMBOLOS_TRAJE)]
    partes = [p for p in partes if p is not None]
    if not partes:
        return None
    ancho = sum(p.get_width() for p in partes) + 18
    alto = max(p.get_height() for p in partes) + 10
    caja = pygame.Rect(0, 0, ancho, alto)
    caja.midbottom = abajo_centro
    dibujo.panel(pantalla, caja, COLOR_FONDO_CARTEL, COLOR_ACENTO if activa else assets.COLOR_BORDE_VIDRIO, 1, radio=6)
    x = caja.left + 6
    for parte in partes:
        pantalla.blit(parte, parte.get_rect(midbottom=(x + parte.get_width() // 2, caja.bottom - 5)))
        x += parte.get_width() + 6
    return caja
