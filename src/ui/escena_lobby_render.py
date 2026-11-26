"""Escena del lobby: la recepción del hotel Backrooms (solo dibujo).

    crear(grade) -> EscenaLobby, o None si falta el arte o la composición
                    (el lobby vuelve entonces al diseño neón anterior)

Para ir a 60 FPS la escena se pre-renderiza una vez a ESCALA_BACKROOMS en
dos capas: "fondo" (tiles + props quietos detrás de los personajes) y
"frente" (props quietos delante). Cada frame solo se dibujan encima las
luces que parpadean, las animaciones, el reloj, los halos, los cuatro
roles posando en sus puestos y el polvo. Lógica pura en escena_lobby.py.
"""

import math
import time

import pygame

from src.core import assets
from src.ui import cargador_backrooms, escena_lobby, sprites
from src.ui.rutas_backrooms import cuadro_por_tiempo


def crear(grade=assets.GRADE_LOBBY):
    if not cargador_backrooms.disponible(grade):
        return None
    plantilla = escena_lobby.cargar_plantilla()
    if plantilla is None:
        return None
    try:
        return EscenaLobby(plantilla, grade)
    except (pygame.error, KeyError, ValueError, TypeError) as error:  # composición rota: lobby clásico
        print(f"[lobby] escena del hotel desactivada: {error}")
        return None


def _oscurecida(superficie, factor):
    copia = superficie.copy()
    tinte = round(255 * factor)
    copia.fill((tinte, tinte, tinte, 255), special_flags=pygame.BLEND_RGBA_MULT)
    return copia


class EscenaLobby:
    def __init__(self, plantilla, grade):
        self.plantilla = plantilla
        self.grade = grade
        self.escala = assets.ESCALA_BACKROOMS
        self.desplazamiento = assets.DESPLAZAMIENTO_ESCENA_LOBBY
        self.linea = escena_lobby.linea_puestos(plantilla)
        tam = (plantilla["ancho"] * plantilla["tile"] * self.escala, plantilla["alto"] * plantilla["tile"] * self.escala)
        detras, delante = escena_lobby.separar_por_profundidad(plantilla["objetos"], self.linea)
        self.fondo = pygame.Surface(tam).convert() if pygame.display.get_surface() else pygame.Surface(tam)
        self.fondo.fill((0, 0, 0))
        self._dibujar_tiles(self.fondo)
        self._sombra_techo(self.fondo)
        self.dinamicos_detras = self._pintar_quietos(self.fondo, detras)
        self.frente = pygame.Surface(tam, pygame.SRCALPHA)
        self.dinamicos_delante = self._pintar_quietos(self.frente, delante)
        self._oscuras = {}
        # Una luz con "objeto" parpadea al compás del objeto con ese "id".
        self.por_id = {o["id"]: (i, o) for i, o in enumerate(plantilla["objetos"]) if "id" in o}

    # --- pre-render ----------------------------------------------------
    def _a_pantalla(self, x, y):
        """px nativos -> px de la capa pre-renderizada."""
        return (round(x * self.escala), round(y * self.escala))

    def _en_pantalla(self, x, y):
        """px nativos -> px de pantalla (con el corrimiento de la escena)."""
        px, py = self._a_pantalla(x, y)
        return (px + self.desplazamiento[0], py + self.desplazamiento[1])

    def _dibujar_tiles(self, destino):
        lado = self.plantilla["tile"] * self.escala
        for capa in self.plantilla["capas"]:
            for fila, ids in enumerate(capa["tiles"]):
                for columna, id_tile in enumerate(ids):
                    if id_tile >= 0:
                        destino.blit(cargador_backrooms.tile(self.grade, id_tile, self.escala),
                                     (columna * lado, fila * lado))

    def _sombra_techo(self, destino):
        """Penumbra que baja desde el techo: la tapa del muro no compite con el título."""
        alto = assets.ALTO_SOMBRA_TECHO_LOBBY
        sombra = pygame.Surface((destino.get_width(), alto), pygame.SRCALPHA)
        for y in range(alto):
            alfa = round(assets.ALFA_SOMBRA_TECHO_LOBBY * (1 - y / alto) ** 1.6)
            sombra.fill((0, 0, 0, alfa), (0, y, destino.get_width(), 1))
        destino.blit(sombra, (0, 0))

    def _imagen(self, obj, apagada=False):
        """Imagen quieta del objeto (su versión apagada si la tiene y se pide)."""
        if apagada and obj.get("apagado"):
            nombre = obj["apagado"]
        elif obj["tipo"] == "animacion":
            nombre = obj.get("estatico") or obj["nombre"]
        else:
            nombre = obj["nombre"]
        tamanio = (obj.get("ancho", 16), obj.get("alto", 16))
        return cargador_backrooms.prop(self.grade, "", nombre, self.escala, tamanio)

    def _pintar_quietos(self, destino, objetos):
        """Pinta los objetos quietos en `destino`; devuelve los dinámicos."""
        dinamicos = []
        for indice, obj in objetos:
            if escena_lobby.es_dinamico(obj):
                dinamicos.append((indice, obj))
                continue
            imagen = self._imagen(obj)
            destino.blit(imagen, imagen.get_rect(bottomleft=self._a_pantalla(obj["x"], obj["y"])))
        return dinamicos

    # --- cada frame ----------------------------------------------------
    def _brillo(self, indice, obj, t):
        return escena_lobby.brillo(obj.get("parpadeo"), t, semilla=indice)

    def _dibujar_dinamico(self, superficie, indice, obj, t):
        pie = self._en_pantalla(obj["x"], obj["y"])
        cuadros = None
        if obj["tipo"] == "animacion" and cargador_backrooms.tiene_animacion(self.grade, obj["nombre"]):
            cuadros = cargador_backrooms.animacion(self.grade, obj["nombre"], self.escala)
        if cuadros:
            imagen = cuadros[cuadro_por_tiempo([ms for _, ms in cuadros], t + indice * 0.37)][0]
        else:
            luz = self._brillo(indice, obj, t)
            if luz >= 0.999:
                imagen = self._imagen(obj)
            elif obj.get("apagado") and luz < 0.5:
                imagen = self._imagen(obj, apagada=True)
            else:
                clave = (indice, round(luz, 1))
                if clave not in self._oscuras:
                    factor = assets.FACTOR_APAGADO_LOBBY + (1 - assets.FACTOR_APAGADO_LOBBY) * luz
                    self._oscuras[clave] = _oscurecida(self._imagen(obj), factor)
                imagen = self._oscuras[clave]
        rect = imagen.get_rect(bottomleft=pie)
        superficie.blit(imagen, rect)
        if obj.get("reloj"):
            self._manecillas(superficie, rect)

    def _manecillas(self, superficie, rect):
        local = time.localtime()
        centro = (rect.centerx, rect.centery)
        radio = min(rect.width, rect.height) / 2
        h, m, s = escena_lobby.angulos_reloj(local.tm_hour, local.tm_min, local.tm_sec)
        for grados, largo, grosor in ((h, 0.45, 3), (m, 0.68, 2), (s, 0.72, 1)):
            punta = escena_lobby.punta_manecilla(centro, grados, radio * largo)
            pygame.draw.line(superficie, assets.COLOR_MANECILLA_RELOJ, centro, punta, grosor)

    def _luces(self, superficie, t):
        for luz in self.plantilla.get("luces", []):
            imagen = cargador_backrooms.light_pool(self.grade, luz["nombre"], self.escala)
            ligado = self.por_id.get(luz.get("objeto"))
            nivel = self._brillo(*ligado, t) if ligado is not None else 1.0
            if nivel <= 0.02:
                continue
            copia = imagen.copy() if nivel < 0.999 else imagen
            if nivel < 0.999:
                copia.set_alpha(round(255 * nivel))
            superficie.blit(copia, copia.get_rect(center=self._en_pantalla(luz["x"], luz["y"])))

    def dibujar(self, pantalla, roles, t, reducir_movimiento=False):
        """`roles`: por puesto, (clase de rol, resaltada, confirmada[, apariencia del vestidor])."""
        t_luz = 0.0 if reducir_movimiento else t
        pantalla.blit(self.fondo, self.desplazamiento)
        for indice, obj in self.dinamicos_detras:
            self._dibujar_dinamico(pantalla, indice, obj, t_luz)
        self._luces(pantalla, t_luz)
        self._puestos(pantalla, roles, t_luz)
        pantalla.blit(self.frente, self.desplazamiento)
        for indice, obj in self.dinamicos_delante:
            self._dibujar_dinamico(pantalla, indice, obj, t_luz)
        if not reducir_movimiento:
            self._polvo(pantalla, t)

    def _puestos(self, superficie, roles, t):
        pool = cargador_backrooms.light_pool(self.grade, self.plantilla["luz_puesto"], self.escala) \
            if self.plantilla.get("luz_puesto") else None
        for (x, y), (clase, resaltada, confirmada, *resto) in zip(self.plantilla["puestos"], roles):
            apariencia = resto[0] if resto else None
            pie = self._en_pantalla(x, y)
            if pool is not None:
                copia = pool.copy()
                copia.set_alpha(255 if resaltada else 150)
                superficie.blit(copia, copia.get_rect(center=(pie[0], pie[1] - 6)))
            halo = pygame.Surface((96, 26), pygame.SRCALPHA)
            alfa = assets.COLOR_HALO_PUESTO_ALFA * (2 if resaltada else 1)
            pygame.draw.ellipse(halo, (*clase.COLOR, min(255, alfa)), halo.get_rect())
            superficie.blit(halo, halo.get_rect(center=pie))
            respiro = round(2 * math.sin(t * 2.4 + x))
            # El personaje de Higgsfield (decidido cuando lo señalan, teñido
            # si quien lo señala se personalizó); sin retrato, el sprite del rol.
            if apariencia is not None and not apariencia.es_predeterminada():
                imagen = sprites.retrato_rol(clase.rol, assets.ALTO_RETRATO_PUESTO, apariencia)
            else:
                imagen = sprites.retrato_rol(f"{clase.rol}_decidido" if resaltada else clase.rol,
                                             assets.ALTO_RETRATO_PUESTO)
            if imagen is None:
                imagen = sprites.sprite_jugador(clase.COLOR, escala=assets.ESCALA_SPRITE_PUESTO, rol=clase.rol,
                                                tiempo=t, caminando=resaltada and not confirmada,
                                                apariencia=apariencia)
            superficie.blit(imagen, imagen.get_rect(midbottom=(pie[0], pie[1] + 4 + respiro)))

    def _polvo(self, superficie, t):
        polvo = self.plantilla.get("polvo")
        if not polvo:
            return
        for x, y, alfa in escena_lobby.motas_polvo(polvo["cantidad"], polvo["rect"], t):
            superficie.blit(self._mota(alfa // 2), self._en_pantalla(x, y))

    def _mota(self, alfa):
        clave = ("mota", alfa // 8)
        if clave not in self._oscuras:
            mota = pygame.Surface((2, 2), pygame.SRCALPHA)
            mota.fill((*assets.COLOR_POLVO_LOBBY, (alfa // 8) * 8))
            self._oscuras[clave] = mota
        return self._oscuras[clave]
