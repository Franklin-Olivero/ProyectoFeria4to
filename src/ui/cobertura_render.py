"""Dibujo de las coberturas rompibles de un cuarto (solo presentación).

La lógica (vida, hitbox, etapas) vive en src/dungeon/coberturas.py. Aquí
cada mueble se dibuja según su etapa de daño:

    intacto -> agrietado -> muy dañado (más grietas, le faltan pedazos y
    se oscurece) -> roto (quedan escombros en el piso, ya sin hitbox).

Las grietas, muescas y escombros se generan una vez por (tema, objeto,
etapa) a partir de la imagen del mueble, con una semilla fija por nombre:
no hace falta arte nuevo y siempre se rompe igual.

    dibujar_con(pantalla, tema, coberturas, entidades)
        coberturas y entidades (enemigos) ordenadas por su base: lo de
        más abajo tapa a lo de más arriba (vista 3/4).
    dibujar_delante(pantalla, tema, coberturas, cuerpos)
        vuelve a dibujar, recortado, el mueble que queda DELANTE de cada
        cuerpo (los jugadores se dibujan después de todo el cuarto).
"""

import random

import pygame

from src.core import assets
from src.dungeon.coberturas import ETAPA_ROTA
from src.ui import decor_mazmorra

_cache = {}  # (tema, nombre, etapa | "rota" | "golpe") -> Surface


def imagen(tema, nombre, etapa):
    """Imagen del mueble en esa etapa de daño (ETAPA_ROTA = escombros), o None."""
    clave = (tema, nombre, etapa)
    if clave not in _cache:
        base = decor_mazmorra.imagen(tema, nombre)
        if base is None:
            _cache[clave] = None
        elif etapa >= ETAPA_ROTA:
            _cache[clave] = _escombros(base, nombre)
        elif etapa == 0:
            _cache[clave] = base
        else:
            _cache[clave] = _daniada(base, nombre, etapa)
    return _cache[clave]


def _rng(nombre, etapa):
    return random.Random(f"cobertura-{nombre}-{etapa}")


def _daniada(base, nombre, etapa):
    """Copia de `base` con las grietas y muescas de la etapa."""
    figura = base.copy()
    ancho, alto = figura.get_size()
    mascara = pygame.mask.from_surface(base)
    grietas = pygame.Surface((ancho, alto), pygame.SRCALPHA)
    # Las grietas de una etapa incluyen las de la anterior (misma semilla):
    # el mueble se va rompiendo por donde ya estaba rajado.
    rng = _rng(nombre, "grietas")
    for _ in range(assets.GRIETAS_POR_ETAPA[etapa]):
        x, y = rng.randint(4, max(4, ancho - 5)), rng.randint(0, max(0, alto // 2))
        puntos = [(x, y)]
        for _ in range(rng.randint(3, 6)):
            x += rng.randint(-8, 8)
            y += rng.randint(6, 14)
            puntos.append((x, y))
        pygame.draw.lines(grietas, assets.COLOR_GRIETA_COBERTURA, False, puntos, assets.GROSOR_GRIETA_COBERTURA)
        if rng.random() < 0.6:  # una rama corta
            i = rng.randrange(1, len(puntos))
            px, py = puntos[i]
            pygame.draw.line(grietas, assets.COLOR_GRIETA_COBERTURA, (px, py),
                             (px + rng.choice((-10, 10)), py + rng.randint(2, 8)), assets.GROSOR_GRIETA_COBERTURA)
    # Solo sobre el cuerpo del mueble, no sobre su fondo transparente.
    grietas.blit(mascara.to_surface(setcolor=(255, 255, 255, 255), unsetcolor=(0, 0, 0, 0)), (0, 0),
                 special_flags=pygame.BLEND_RGBA_MULT)
    figura.blit(grietas, (0, 0))
    rng = _rng(nombre, "muescas")
    for _ in range(assets.MUESCAS_POR_ETAPA[etapa]):
        lado = rng.choice((8, 10, 14))
        # Mordiscos en el borde de arriba y los costados: la base sigue entera.
        if rng.random() < 0.5:
            x, y = rng.randint(0, max(0, ancho - lado)), _tope(mascara, rng.randint(0, ancho - 1), alto)
        else:
            y = rng.randint(0, max(0, alto // 2))
            x = rng.choice((_borde_izq(mascara, y, ancho), _borde_der(mascara, y, ancho) - lado))
        figura.fill((0, 0, 0, 0), (x - x % 2, y - y % 2, lado, lado))
    factor = round(255 * assets.FACTOR_ETAPA_COBERTURA[etapa])
    figura.fill((factor, factor, factor, 255), special_flags=pygame.BLEND_RGBA_MULT)
    return figura


def _tope(mascara, x, alto):
    for y in range(alto):
        if mascara.get_at((x, y)):
            return y
    return 0


def _borde_izq(mascara, y, ancho):
    for x in range(ancho):
        if mascara.get_at((x, y)):
            return x
    return 0


def _borde_der(mascara, y, ancho):
    for x in range(ancho - 1, -1, -1):
        if mascara.get_at((x, y)):
            return x + 1
    return ancho


def _escombros(base, nombre):
    """Pedazos del mueble amontonados en el piso, apoyados en su base: se
    recortan trozos de la imagen original (así el montón tiene sus colores)
    sobre una mancha de polvo."""
    ancho, alto = base.get_size()
    alto_pila = max(20, min(alto // 2, 44))
    figura = pygame.Surface((ancho, alto), pygame.SRCALPHA)
    mancha = pygame.Rect(0, 0, round(ancho * 0.92), max(12, alto_pila // 2))
    mancha.midbottom = (ancho // 2, alto)
    pygame.draw.ellipse(figura, assets.COLOR_SOMBRA_PROP, mancha)
    mascara = pygame.mask.from_surface(base)
    rng = _rng(nombre, "escombros")
    trozos = []
    for _ in range(assets.ESCOMBROS_COBERTURA * 8):
        if len(trozos) >= assets.ESCOMBROS_COBERTURA:
            break
        w, h = rng.choice((12, 16, 20)), rng.choice((8, 10, 14))
        w, h = min(w, ancho), min(h, alto)
        ox, oy = rng.randint(0, ancho - w), rng.randint(0, alto - h)
        if not mascara.get_at((ox + w // 2, oy + h // 2)):
            continue  # ese trozo sería aire
        # Más pedazos y más altos al medio que en las orillas: forma de montón.
        x = round(rng.triangular(0, ancho - w))
        centrado = 1 - abs((x + w / 2) / ancho - 0.5) * 2
        y = alto - h - rng.randint(0, max(1, round(alto_pila * centrado)))
        trozos.append((y + h, (x - x % 2, y - y % 2), (ox, oy, w, h)))
    for _, destino, origen in sorted(trozos):  # los de más abajo, encima
        trozo = base.subsurface(origen)
        contorno = pygame.mask.from_surface(trozo).to_surface(setcolor=assets.COLOR_GRIETA_COBERTURA,
                                                               unsetcolor=(0, 0, 0, 0))
        figura.blit(contorno, (destino[0], destino[1] + 2))  # canto oscuro: se lee como pieza suelta
        figura.blit(trozo, destino)
    factor = round(255 * assets.FACTOR_ESCOMBROS)
    figura.fill((factor, factor, factor, 255), special_flags=pygame.BLEND_RGBA_MULT)
    return figura


def _golpeada(tema, nombre, etapa, figura):
    """La misma imagen, más clara: el destello de un impacto."""
    clave = (tema, nombre, etapa, "golpe")
    if clave not in _cache:
        clara = figura.copy()
        d = assets.DESTELLO_GOLPE_COBERTURA
        clara.fill((d, d, d, 0), special_flags=pygame.BLEND_RGB_ADD)
        _cache[clave] = clara
    return _cache[clave]


def dibujar(pantalla, tema, cobertura, tiempo=0.0, con_sombra=True):
    """Una cobertura: sombra, imagen de su etapa, temblor y destello si
    acaba de recibir un impacto, y su halo si es una pantalla encendida."""
    etapa = cobertura.etapa
    figura = imagen(tema, cobertura.nombre, etapa)
    if figura is None:
        return
    rect = pygame.Rect(cobertura.rect)
    if cobertura.rota:
        pantalla.blit(figura, rect)
        return
    if con_sombra:
        pantalla.blit(*decor_mazmorra.sombra(rect))
    if cobertura.tiempo_golpe > 0:
        figura = _golpeada(tema, cobertura.nombre, etapa, figura)
        t = assets.TEMBLOR_GOLPE_COBERTURA
        rect = rect.move(t if int(cobertura.tiempo_golpe * 40) % 2 else -t, 0)
    pantalla.blit(figura, rect)
    foco = decor_mazmorra.foco_de(cobertura.nombre)
    if foco is not None and etapa < 2:  # muy dañada, la pantalla ya no enciende
        decor_mazmorra.dibujar_focos(pantalla, [(rect, foco)], tiempo, 0)


def base_y(cobertura):
    """Y del borde inferior de la base: con qué se ordena al dibujar."""
    return cobertura.hitbox[1] + cobertura.hitbox[3]


def dibujar_con(pantalla, tema, coberturas, entidades=(), tiempo=0.0):
    """Coberturas y `entidades` [(y de su base, función que la dibuja)]
    en orden de base. Los escombros van primero: se pisan."""
    capas = []
    for cobertura in coberturas:
        if cobertura.rota:
            dibujar(pantalla, tema, cobertura, tiempo)
        else:
            capas.append((base_y(cobertura), 0, cobertura))
    capas.extend((y, 1, pintar) for y, pintar in entidades)
    for _, es_entidad, cosa in sorted(capas, key=lambda c: (c[0], c[1])):
        if es_entidad:
            cosa()
        else:
            dibujar(pantalla, tema, cosa, tiempo)


def dibujar_delante(pantalla, tema, coberturas, cuerpos, tiempo=0.0):
    """Para cada cuerpo (pygame.Rect de un personaje ya dibujado), repinta
    recortado al cuerpo cada mueble en pie cuya base queda más abajo: el
    personaje está detrás de él. O(coberturas * cuerpos)."""
    recorte = pantalla.get_clip()
    for cuerpo in cuerpos:
        # Lo que ocupa su sprite: más alto que su hitbox.
        zona = pygame.Rect(cuerpo.left - 12, cuerpo.top - 34, cuerpo.width + 24, cuerpo.height + 46)
        for cobertura in coberturas:
            if cobertura.rota or base_y(cobertura) <= cuerpo.bottom:
                continue
            if zona.colliderect(cobertura.rect):
                pantalla.set_clip(zona.clip(recorte) if recorte else zona)
                dibujar(pantalla, tema, cobertura, tiempo, con_sombra=False)
    pantalla.set_clip(recorte)
