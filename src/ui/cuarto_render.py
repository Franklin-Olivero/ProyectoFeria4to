"""Dibujo del escenario de combate: piso, muros, grafitis, puertas y la
terminal física del cuarto final (solo presentación).

Lo usan Cuarto (src/dungeon/cuarto.py) y ArenaJefe
(src/dungeon/arena_jefe.py). El piso con sus grafitis se genera una
vez por cuarto y se cachea en una Surface, así cada frame es un blit.
"""

import random

import pygame

from src.core import assets
from src.ui import dibujo, sprites
from src.ui.fuentes import fuente

_fondos = {}


def fondo_cuarto(rect, semilla, cantidad_grafitis):
    """Surface con baldosas, muros de ladrillo y grafitis para `rect`
    (el área jugable). Mide rect más el grosor de los muros a cada lado;
    se dibuja con `blit(fondo, origen_fondo(rect))`."""
    clave = (rect.size, semilla, cantidad_grafitis)
    if clave in _fondos:
        return _fondos[clave]

    g = assets.GROSOR_MURO
    superficie = pygame.Surface((rect.width + 2 * g, rect.height + 2 * g), pygame.SRCALPHA)
    interior = pygame.Rect(g, g, rect.width, rect.height)

    # Orden: muro (todo el fondo), luego el piso encima y los grafitis
    # sobre el piso; al final solo las juntas y bordes del muro.
    _dibujar_muros(superficie, interior)
    _dibujar_baldosas(superficie, interior, random.Random(semilla))
    _dibujar_grafitis(superficie, interior, random.Random(semilla), cantidad_grafitis)
    _dibujar_bordes_muro(superficie, interior)

    _fondos[clave] = superficie
    return superficie


def origen_fondo(rect):
    return (rect.left - assets.GROSOR_MURO, rect.top - assets.GROSOR_MURO)


def _dibujar_baldosas(superficie, interior, rng=None):
    baldosas = [sprites.cuadro_cuarto(nombre) for nombre in assets.CUADROS_PISO]
    if all(b is not None for b in baldosas):
        _dibujar_baldosas_hoja(superficie, interior, baldosas, rng or random.Random(0))
        return
    lado = assets.TAMANIO_BALDOSA
    pygame.draw.rect(superficie, assets.COLOR_BALDOSA_A, interior)
    for fila, y in enumerate(range(interior.top, interior.bottom, lado)):
        for columna, x in enumerate(range(interior.left, interior.right, lado)):
            if (fila + columna) % 2 == 0:
                continue
            baldosa = pygame.Rect(x, y, lado, lado).clip(interior)
            pygame.draw.rect(superficie, assets.COLOR_BALDOSA_B, baldosa)


def _dibujar_baldosas_hoja(superficie, interior, baldosas, rng):
    """Piso con la hoja de sprites: tablero de dos baldosas y, de vez en
    cuando, una con detalle (grieta, rejilla). Se recorta al interior."""
    lado = assets.TAMANIO_BALDOSA_HOJA
    detalles = [sprites.cuadro_cuarto(nombre) for nombre in assets.CUADROS_PISO_DETALLE]
    detalles = [d for d in detalles if d is not None]
    recorte = superficie.get_clip()
    superficie.set_clip(interior)
    for fila, y in enumerate(range(interior.top, interior.bottom, lado)):
        for columna, x in enumerate(range(interior.left, interior.right, lado)):
            imagen = baldosas[(fila + columna) % 2]
            if detalles and rng.random() < assets.PROBABILIDAD_PISO_DETALLE:
                imagen = rng.choice(detalles)
            superficie.blit(imagen, (x, y))
    superficie.set_clip(recorte)


def _dibujar_grafitis(superficie, interior, rng, cantidad):
    """Texto girado y manchas poligonales, translúcidos, sobre el piso."""
    f = fuente(assets.TAMANIO_FUENTE_GRAFITI, negrita=True)
    textos = list(assets.TEXTOS_GRAFITI)
    rng.shuffle(textos)
    # Cada grafiti va en su propia columna del cuarto, para que no se
    # amontonen; la altura sí es aleatoria.
    ancho_columna = (interior.width - 160) / max(1, cantidad)
    for i in range(cantidad):
        # Mancha: polígono irregular alrededor de un centro.
        cx = round(interior.left + 80 + ancho_columna * (i + rng.uniform(0.25, 0.75)))
        cy = rng.randint(interior.top + 70, interior.bottom - 70)
        puntos = []
        for k in range(7):
            angulo = k * 360 / 7 + rng.uniform(-20, 20)
            radio = rng.uniform(50, 120)
            puntos.append(pygame.Vector2(radio, 0).rotate(angulo) + (cx, cy))
        pygame.draw.polygon(superficie, assets.COLOR_MANCHA, puntos)
        for _ in range(4):  # salpicaduras
            px = cx + rng.randint(-150, 150)
            py = cy + rng.randint(-90, 90)
            pygame.draw.rect(superficie, assets.COLOR_GRAFITI, (px, py, rng.randint(6, 16), rng.randint(4, 8)))

        texto = textos[i % len(textos)]
        imagen = f.render(texto, True, assets.COLOR_GRAFITI[:3])
        imagen.set_alpha(assets.COLOR_GRAFITI[3])
        imagen = pygame.transform.rotate(imagen, rng.choice((-14, -8, 6, 12)))
        superficie.blit(imagen, imagen.get_rect(center=(cx, cy)).clamp(interior))


def _dibujar_muros(superficie, interior):
    g = assets.GROSOR_MURO
    exterior = interior.inflate(2 * g, 2 * g)
    ladrillo = sprites.cuadro_cuarto(assets.CUADRO_MURO)
    if ladrillo is None:
        pygame.draw.rect(superficie, assets.COLOR_MURO, exterior)
        return
    # Ladrillos de la hoja repetidos por toda la franja (el piso tapa el
    # centro después).
    recorte = superficie.get_clip()
    superficie.set_clip(exterior)
    for y in range(exterior.top, exterior.bottom, ladrillo.get_height()):
        for x in range(exterior.left, exterior.right, ladrillo.get_width()):
            superficie.blit(ladrillo, (x, y))
    superficie.set_clip(recorte)


def _dibujar_bordes_muro(superficie, interior):
    g = assets.GROSOR_MURO
    exterior = interior.inflate(2 * g, 2 * g)
    if sprites.cuadro_cuarto(assets.CUADRO_MURO) is not None:
        # Con la hoja de ladrillos solo hacen falta los dos bordes.
        pygame.draw.rect(superficie, assets.COLOR_MURO_BORDE, exterior, 2)
        pygame.draw.rect(superficie, assets.COLOR_MURO_BORDE, interior, 2)
        return
    # Ladrillos: juntas horizontales y verticales alternadas, recortadas al muro.
    capa = pygame.Surface(exterior.size, pygame.SRCALPHA)
    for fila, y in enumerate(range(0, exterior.height, assets.ALTO_LADRILLO)):
        pygame.draw.line(capa, assets.COLOR_MURO_LINEA, (0, y), (exterior.width, y), 1)
        desfase = (assets.ANCHO_LADRILLO // 2) if fila % 2 else 0
        for x in range(desfase, exterior.width, assets.ANCHO_LADRILLO):
            pygame.draw.line(capa, assets.COLOR_MURO_LINEA, (x, y), (x, y + assets.ALTO_LADRILLO), 1)
    # Solo se conserva la franja del muro (se borra el interior de la capa).
    pygame.draw.rect(capa, (0, 0, 0, 0), interior)
    superficie.blit(capa, exterior.topleft)
    pygame.draw.rect(superficie, assets.COLOR_MURO_BORDE, exterior, 2)
    pygame.draw.rect(superficie, assets.COLOR_MURO_BORDE, interior, 2)


def _rect_visual_puerta(puerta, rect_cuarto):
    """Rect de la puerta dentro de la franja del muro (no el de colisión)."""
    g = assets.GROSOR_MURO
    r = rect_cuarto
    if puerta.direccion in ("N", "S"):
        visual = pygame.Rect(0, 0, assets.ANCHO_PUERTA, g)
        if puerta.direccion == "N":
            visual.midbottom = (r.centerx, r.top)
        else:
            visual.midtop = (r.centerx, r.bottom)
    else:
        visual = pygame.Rect(0, 0, g, assets.ANCHO_PUERTA)
        if puerta.direccion == "E":
            visual.midleft = (r.right, r.centery)
        else:
            visual.midright = (r.left, r.centery)
    return visual


def dibujar_puerta(pantalla, puerta, rect_cuarto):
    visual = _rect_visual_puerta(puerta, rect_cuarto)
    color = puerta.color()
    estado = "bloqueada" if puerta.bloqueada else "sellada" if puerta.sellada else "abierta"
    imagen = sprites.cuadro_puerta(estado)
    if imagen is not None:
        if puerta.direccion in ("E", "W"):
            imagen = pygame.transform.rotate(imagen, 90)
        pantalla.blit(imagen, imagen.get_rect(center=visual.center))
        return
    pygame.draw.rect(pantalla, assets.COLOR_FONDO, visual)
    pygame.draw.rect(pantalla, color, visual, 2)
    if puerta.bloqueada:
        # Barrotes: la puerta está cerrada por los enemigos del cuarto.
        if puerta.direccion in ("N", "S"):
            for x in range(visual.left + 8, visual.right - 4, 10):
                pygame.draw.line(pantalla, color, (x, visual.top + 3), (x, visual.bottom - 3), 2)
        else:
            for y in range(visual.top + 8, visual.bottom - 4, 10):
                pygame.draw.line(pantalla, color, (visual.left + 3, y), (visual.right - 3, y), 2)
    elif puerta.sellada:
        # Una X: cerrada por cuartos pendientes, no por enemigos.
        pygame.draw.rect(pantalla, color, visual)
        for inicio, fin in ((visual.topleft, visual.bottomright), (visual.bottomleft, visual.topright)):
            pygame.draw.line(pantalla, assets.COLOR_X_PUERTA_SELLADA, inicio, fin, assets.GROSOR_X_PUERTA_SELLADA)
    else:
        # Abierta: hueco iluminado del color de la puerta.
        pygame.draw.rect(pantalla, color, visual.inflate(-6, -6))


def dibujar_terminal_cuarto(pantalla, rect_cuarto, bloqueada, cantidad_enemigos):
    """Terminal física pegada al muro derecho del cuarto final, con su
    aviso de bloqueo a la izquierda."""
    paleta = sprites.PALETA_TERMINAL_BLOQUEADA if bloqueada else sprites.PALETA_TERMINAL_LISTA
    imagen = sprites.sprite(sprites.TERMINAL, paleta, escala=4)
    marco = imagen.get_rect()
    marco.inflate_ip(16, 16)
    marco.midright = (rect_cuarto.right - assets.MARGEN_TERMINAL_CUARTO, rect_cuarto.centery)
    borde = assets.COLOR_TEAL if not bloqueada else assets.COLOR_TEAL
    dibujo.panel(pantalla, marco, assets.COLOR_FONDO_TERMINAL_CUARTO, borde, 2, radio=4)
    pantalla.blit(imagen, imagen.get_rect(center=marco.center))

    if bloqueada:
        titulo, detalle = assets.TEXTO_TERMINAL_BLOQUEADA, f"Elimina a los {cantidad_enemigos} enemigos"
    else:
        titulo, detalle = assets.TEXTO_TERMINAL_LISTA, "Acércate para decidir"
    x = marco.left - 14
    dibujo.texto(pantalla, titulo, (x, marco.centery - 4), assets.COLOR_TEXTO_HUD,
                 assets.TAMANIO_FUENTE_NORMAL, negrita=True, ancla="bottomright")
    dibujo.texto(pantalla, detalle, (x, marco.centery + 2), assets.COLOR_TEXTO_SECUNDARIO,
                 assets.TAMANIO_FUENTE_PEQUENA, ancla="topright")
