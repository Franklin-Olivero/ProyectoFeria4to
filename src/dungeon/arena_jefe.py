"""Arena del jefe final: la parte física y visual de la mazmorra final.

Envuelve a MazmorraFinal (lógica pura) y le pone cuerpo con Pygame:
    - el cuarto grande (rect) y el rect de colisión del jefe,
    - convierte cada DisparoJefe en un ProyectilConEstela real,
    - crea los súbditos invocados (Enemigo normales, con la velocidad
      del tramo de toxicidad máximo y como mucho
      dificultad["cantidad_enemigos"] vivos a la vez),
    - dibuja jefe, charcos, barra de vida, fase, tiempo y mensajes.

Expone la misma interfaz que Cuarto (rect, enemigos, actualizar,
dibujar, manejar_evento), así Main.py usa el mismo loop de combate,
colisiones y carga de habilidad. Nunca hay minijuego de decisión aquí.
"""

import pygame

from src.core import assets
from src.core.balance import DANIO_PROYECTIL_JEFE, UMBRAL_FASE_2, UMBRAL_FASE_3
from src.dungeon.mazmorra_final import EN_COMBATE, VICTORIA, MazmorraFinal
from src.entities.enemy import Enemigo
from src.entities.projectile import ProyectilConEstela
from src.ui import cuarto_render, dibujo, sprites

DISTANCIA_INICIO_JUGADOR = 50  # px desde el borde inferior de la arena
SEMILLA_FONDO_ARENA = 777
GRAFITIS_ARENA = 4
NOMBRE_JEFE = "Servidor Central"


class ArenaJefe:
    def __init__(self, colapso, jugador):
        self.rect = pygame.Rect(0, 0, assets.ANCHO_ARENA, assets.ALTO_ARENA)
        self.rect.center = assets.CENTRO_ARENA
        limites = (self.rect.left, self.rect.top, self.rect.right, self.rect.bottom)
        self.mazmorra = MazmorraFinal(colapso, limites)
        self.subditos = []
        self._tiempo = 0.0  # reloj visual para el parpadeo
        self._vincular_cuerpo_jefe()
        self.colocar_jugador(jugador)

    @property
    def jefe(self):
        return self.mazmorra.jefe

    @property
    def enemigos(self):
        """Súbditos + jefe (si sigue vivo): lo que pueden golpear los ataques."""
        if self.jefe.vivo and self.mazmorra.estado == EN_COMBATE:
            return self.subditos + [self.jefe]
        return list(self.subditos)

    def colocar_jugador(self, jugador):
        jugador.rect.center = (self.rect.centerx, self.rect.bottom - DISTANCIA_INICIO_JUGADOR)
        jugador.posicion.update(jugador.rect.center)

    def _vincular_cuerpo_jefe(self):
        # Al reiniciar la pelea la mazmorra crea un Jefe nuevo sin rect.
        if self.jefe.rect is None:
            self.jefe.rect = pygame.Rect(0, 0, assets.TAMANIO_JEFE, assets.TAMANIO_JEFE)
            self.jefe.rect.center = (round(self.jefe.x), round(self.jefe.y))

    def manejar_evento(self, evento):
        """La arena no tiene teclas propias (sin debug ni decisión)."""

    def actualizar(self, dt, jugador, proyectiles_enemigos):
        self._tiempo += dt
        if self.mazmorra.estado == EN_COMBATE:
            for subdito in self.subditos:
                subdito.actualizar(dt, jugador, proyectiles_enemigos)
                subdito.mantener_dentro(self.rect)
            self.subditos = [subdito for subdito in self.subditos if subdito.vivo]

        # El jefe respeta MAX_PROYECTILES_JEFE: se le pasa cuántas balas
        # suyas siguen vivas (las de los súbditos no cuentan).
        balas_jefe = sum(isinstance(p, ProyectilConEstela) for p in proyectiles_enemigos)
        self.mazmorra.actualizar(dt, jugador, balas_jefe)
        self._vincular_cuerpo_jefe()

        if self.mazmorra.reinicio_pendiente:
            self.mazmorra.reinicio_pendiente = False
            self.subditos.clear()
            proyectiles_enemigos.clear()
            jugador.vida = jugador.vida_maxima
            jugador.invulnerabilidad.reiniciar()
            self.colocar_jugador(jugador)
            return

        if self.mazmorra.estado == VICTORIA:
            # Servidor purificado: desaparece todo lo hostil.
            self.subditos.clear()
            proyectiles_enemigos.clear()
            return

        salida = self.mazmorra.salida
        for disparo in salida.disparos:
            proyectiles_enemigos.append(
                ProyectilConEstela(
                    posicion=(disparo.x, disparo.y),
                    direccion=(disparo.dx, disparo.dy),
                    velocidad=disparo.velocidad,
                    danio=DANIO_PROYECTIL_JEFE,
                    color=assets.COLOR_PROYECTIL_JEFE,
                    tamanio=assets.TAMANIO_PROYECTIL_JEFE,
                    alfas=assets.ALFAS_ESTELA_JEFE,
                    espaciado=assets.ESPACIADO_ESTELA_JEFE,
                )
            )
        self._invocar(salida.invocaciones)

    def _invocar(self, cantidad):
        """Crea súbditos a los lados del jefe, sin pasar el tope del tramo."""
        tope = self.mazmorra.dificultad["cantidad_enemigos"]
        velocidad = assets.VELOCIDAD_ENEMIGO * self.mazmorra.dificultad["multiplicador_velocidad"]
        for i in range(cantidad):
            if len(self.subditos) >= tope:
                break
            lado = -1 if i % 2 == 0 else 1
            # Agresividad absoluta: persiguen y disparan desde cualquier distancia.
            subdito = Enemigo(
                self.jefe.x + lado * assets.SEPARACION_INVOCACION, self.jefe.y, velocidad,
                agro_permanente=True,
            )
            subdito.mantener_dentro(self.rect)
            self.subditos.append(subdito)

    # ------------------------------------------------------------------
    # Dibujo
    # ------------------------------------------------------------------

    def dibujar(self, pantalla):
        fondo = cuarto_render.fondo_cuarto(self.rect, SEMILLA_FONDO_ARENA, GRAFITIS_ARENA)
        pantalla.blit(fondo, cuarto_render.origen_fondo(self.rect))
        for charco in self.mazmorra.charcos:
            self._dibujar_charco(pantalla, charco)
        for subdito in self.subditos:
            subdito.dibujar(pantalla)
        if self.jefe.vivo:
            self._dibujar_jefe(pantalla)

    def _dibujar_charco(self, pantalla, charco):
        centro = (round(charco.x), round(charco.y))
        if charco.activo:
            superficie = pygame.Surface((charco.radio * 2, charco.radio * 2), pygame.SRCALPHA)
            pygame.draw.circle(
                superficie,
                (*assets.COLOR_CHARCO, assets.ALFA_CHARCO_ACTIVO),
                (charco.radio, charco.radio),
                charco.radio,
            )
            pantalla.blit(superficie, superficie.get_rect(center=centro))
        # Contorno siempre: durante el aviso es lo único que se ve.
        pygame.draw.circle(
            pantalla, assets.COLOR_CHARCO, centro, charco.radio, assets.GROSOR_CONTORNO_CHARCO
        )

    def _dibujar_jefe(self, pantalla):
        jefe = self.jefe
        if jefe.tiempo_pausa > 0:
            # Parpadeo al cambiar de fase: visible e invisible alternados.
            if int(self._tiempo / assets.PERIODO_PARPADEO_JEFE) % 2 == 0:
                return
        imagen = sprites.sprite(sprites.JEFE, sprites.PALETA_JEFE, escala=4)
        if jefe.tiempo_destello > 0:
            # Destello blanco al recibir daño: silueta del sprite en blanco.
            imagen = imagen.copy()
            imagen.fill(assets.COLOR_DESTELLO_JEFE, special_flags=pygame.BLEND_RGB_MAX)
        pantalla.blit(imagen, imagen.get_rect(center=jefe.rect.center))
        if jefe.escudo_anonimato:
            escudo = jefe.rect.inflate(assets.MARGEN_ESCUDO_JEFE * 2, assets.MARGEN_ESCUDO_JEFE * 2)
            pygame.draw.rect(pantalla, assets.COLOR_ESCUDO_JEFE, escudo, assets.GROSOR_ESCUDO_JEFE,
                             border_radius=8)

    def dibujar_hud(self, pantalla):
        """Nombre del jefe, barra de vida con marcas de fase, fase, escudo
        y tiempo, en el centro del HUD superior. Se dibuja fuera de la
        sacudida para que siempre se lea."""
        jefe = self.jefe
        fondo = pygame.Rect(assets.RECT_BARRA_JEFE)
        dibujo.texto(pantalla, NOMBRE_JEFE, (fondo.centerx, 20), assets.COLOR_MORADO,
                     assets.TAMANIO_FUENTE_MEDIA, negrita=True, ancla="center")
        dibujo.barra(pantalla, fondo, jefe.fraccion_vida, assets.COLOR_BARRA_JEFE)
        for umbral in (UMBRAL_FASE_2, UMBRAL_FASE_3):
            x = fondo.left + round(fondo.width * umbral)
            pygame.draw.line(pantalla, assets.COLOR_MARCA_FASE, (x, fondo.top), (x, fondo.bottom),
                             assets.ANCHO_MARCA_FASE)

        texto_fase = f"Fase {jefe.fase}"
        if jefe.escudo_anonimato:
            texto_fase += f" · Escudo {jefe.vida_escudo}"
        dibujo.texto(pantalla, texto_fase, (fondo.left, fondo.bottom + 3), assets.COLOR_TEXTO_SECUNDARIO,
                     assets.TAMANIO_FUENTE_PEQUENA)
        segundos = int(self.mazmorra.tiempo_restante + 0.999)  # redondeo hacia arriba
        dibujo.texto(pantalla, f"{segundos // 60}:{segundos % 60:02d}", (fondo.right, fondo.bottom + 3),
                     assets.COLOR_AMARILLO, assets.TAMANIO_FUENTE_PEQUENA, negrita=True, ancla="topright")

        # La victoria tiene su propia pantalla (src/ui/pantalla_victoria.py);
        # aquí solo se avisa la derrota.
        mensaje = self.mazmorra.texto_mensaje()
        if mensaje is not None and self.mazmorra.estado != VICTORIA:
            dibujo.chip(pantalla, mensaje, assets.POSICION_MENSAJE_CENTRAL, assets.COLOR_MAGENTA,
                        assets.COLOR_FONDO_PANEL, assets.COLOR_MAGENTA, assets.TAMANIO_FUENTE_MEDIA,
                        ancla="center", alto=36, margen=16)
