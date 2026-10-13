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

DISTANCIA_INICIO_JUGADOR = 50  # px desde el borde inferior de la arena


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

        self.mazmorra.actualizar(dt, jugador)
        self._vincular_cuerpo_jefe()

        if self.mazmorra.reinicio_pendiente:
            self.mazmorra.reinicio_pendiente = False
            self.subditos.clear()
            proyectiles_enemigos.clear()
            jugador.vida = jugador.vida_maxima
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
            subdito = Enemigo(self.jefe.x + lado * assets.SEPARACION_INVOCACION, self.jefe.y, velocidad)
            subdito.mantener_dentro(self.rect)
            self.subditos.append(subdito)

    # ------------------------------------------------------------------
    # Dibujo
    # ------------------------------------------------------------------

    def dibujar(self, pantalla):
        pygame.draw.rect(pantalla, assets.COLOR_MURO_ARENA, self.rect, assets.GROSOR_MURO_ARENA)
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
        color = assets.COLOR_DESTELLO_JEFE if jefe.tiempo_destello > 0 else assets.COLOR_JEFE
        pygame.draw.rect(pantalla, color, jefe.rect)
        if jefe.escudo_anonimato:
            escudo = jefe.rect.inflate(assets.MARGEN_ESCUDO_JEFE * 2, assets.MARGEN_ESCUDO_JEFE * 2)
            pygame.draw.rect(pantalla, assets.COLOR_ESCUDO_JEFE, escudo, assets.GROSOR_ESCUDO_JEFE)

    def dibujar_hud(self, pantalla, fuente):
        """Barra de vida con marcas de fase, "Fase N", tiempo y mensajes.
        Se dibuja fuera de la sacudida para que siempre se lea."""
        jefe = self.jefe
        fondo = pygame.Rect(assets.RECT_BARRA_JEFE)
        pygame.draw.rect(pantalla, assets.COLOR_FONDO_BARRA_JEFE, fondo)
        relleno = fondo.copy()
        relleno.width = round(fondo.width * jefe.fraccion_vida)
        pygame.draw.rect(pantalla, assets.COLOR_BARRA_JEFE, relleno)
        for umbral in (UMBRAL_FASE_2, UMBRAL_FASE_3):
            x = fondo.left + round(fondo.width * umbral)
            marca = pygame.Rect(0, 0, assets.ANCHO_MARCA_FASE, fondo.height)
            marca.midtop = (x, fondo.top)
            pygame.draw.rect(pantalla, assets.COLOR_MARCA_FASE, marca)

        texto_fase = f"Fase {jefe.fase}"
        if jefe.escudo_anonimato:
            texto_fase += f"  Escudo: {jefe.vida_escudo}"
        pantalla.blit(
            fuente.render(texto_fase, True, assets.COLOR_TEXTO_HUD), assets.POSICION_TEXTO_FASE
        )

        segundos = int(self.mazmorra.tiempo_restante + 0.999)  # redondeo hacia arriba
        texto_tiempo = f"Tiempo: {segundos // 60}:{segundos % 60:02d}"
        pantalla.blit(
            fuente.render(texto_tiempo, True, assets.COLOR_TEXTO_HUD),
            assets.POSICION_TEXTO_TIEMPO_JEFE,
        )

        mensaje = self.mazmorra.texto_mensaje()
        if mensaje is not None:
            color = (
                assets.COLOR_MENSAJE_VICTORIA
                if self.mazmorra.estado == VICTORIA
                else assets.COLOR_MENSAJE_DERROTA
            )
            superficie = fuente.render(mensaje, True, color)
            pantalla.blit(superficie, superficie.get_rect(center=assets.POSICION_MENSAJE_CENTRAL))
