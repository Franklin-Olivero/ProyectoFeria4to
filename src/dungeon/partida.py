"""Estado global de una partida (lógica pura, sin Pygame).

Agrupa lo que sobrevive entre mazmorras: el Colapso Electoral, el
progreso (mazmorras completadas), la red de calles de Ciudad Nova con
sus pesos dinámicos y barricadas, y la última zona donde estuvo el
jugador (donde reaparece al volver a la ciudad). Main.py solo traduce
teclas a estas llamadas; así entrar a un edificio, la decisión y la
derrota global se pueden probar sin abrir ventana.
"""

from src.core.balance import NIVEL_TOXICIDAD_FINAL
from src.core.colapso import ColapsoElectoral
from src.dungeon import ciudad_mapa
from src.dungeon.clasificador_toxicidad import calcular_nivel_toxicidad, construir_arbol_reportes
from src.dungeon.grafo_ciudad import EDIFICIOS, ZONA_FINAL, ZONA_INICIO, GrafoCiudad
from src.dungeon.mazmorra_final import esta_desbloqueada
from src.dungeon.noticias import EstadoNoticias, generar_titulares
from src.dungeon.progreso import ProgresoPartida
from src.story.campania import Campania
from src.ui.terminal_decision import PURIFICACION_EXITOSA, construir_arbol_publicacion


class Partida:
    def __init__(self):
        self.campania = Campania()
        self.reiniciar()

    def reiniciar(self):
        """Estado inicial: colapso 0, progreso 0, en la Plaza, las calles
        con sus pesos originales y sin barricadas, y la campaña desde el
        prólogo (indicadores, pistas y evidencias en cero)."""
        self.colapso = ColapsoElectoral()
        self.progreso = ProgresoPartida()
        self.ciudad = GrafoCiudad()
        self.ubicacion = ZONA_INICIO
        self.campania.reiniciar()

    def alcaldia_desbloqueada(self):
        return esta_desbloqueada(self.colapso, self.progreso.mazmorras_completadas)

    # ------------------------------------------------------------------
    # Ciudad Nova
    # ------------------------------------------------------------------

    def entrar(self, zona):
        """El jugador cruza la puerta de `zona` (caminar es gratis): queda
        como ubicación, para reaparecer frente a esa puerta al volver."""
        self.ubicacion = zona

    def posicion_aparicion(self):
        """Px del mundo donde aparece el jugador en la ciudad."""
        return ciudad_mapa.posicion_aparicion(self.ubicacion)

    def barricadas_activas(self):
        """Barricadas de calle + las de la Alcaldía mientras está sellada."""
        casillas = self.ciudad.barricadas_activas()
        if not self.alcaldia_desbloqueada():
            casillas = casillas | ciudad_mapa.BARRICADAS_ALCALDIA
        return casillas

    def es_solida(self, col, fila):
        return ciudad_mapa.es_solida(col, fila, self.barricadas_activas())

    def ruta_sugerida(self, posicion, destino):
        """(nodos, costo) desde el nodo más cercano a `posicion`, o None."""
        return self.ciudad.ruta_sugerida(posicion, destino)

    def toxicidad(self, zona):
        """Nivel 0-100 de la zona: el de sus reportes (árbol N-ario) o el
        máximo para la Alcaldía."""
        if zona == ZONA_FINAL:
            return NIVEL_TOXICIDAD_FINAL
        return calcular_nivel_toxicidad(construir_arbol_reportes(self.ciudad.reportes(zona), zona))

    def titulares(self):
        """Titulares del cintillo según el estado actual: primero los
        eventos recientes de la campaña, luego los de la ciudad."""
        return self.campania.titulares() + generar_titulares(EstadoNoticias(
            toxicidad={zona: self.toxicidad(zona) for zona in EDIFICIOS if zona != ZONA_FINAL},
            calles_bloqueadas=self.ciudad.calles_bloqueadas(),
            colapso=self.colapso.valor,
            alcaldia_abierta=self.alcaldia_desbloqueada(),
        ))

    # ------------------------------------------------------------------
    # Mazmorras
    # ------------------------------------------------------------------

    def fabrica_arbol(self, zona):
        """Función sin argumentos que arma el árbol de la terminal de
        `zona` en el momento en que el cuarto final la abre: el escenario
        de la campaña con el estado de evidencia de ese instante, o el
        árbol fijo original si la zona no tiene escenario."""
        def fabrica():
            escenario = self.campania.preparar_escenario(zona)
            return escenario.arbol if escenario is not None else construir_arbol_publicacion()
        return fabrica

    def cerrar_mazmorra(self, mazmorra, resultado, terminal=None):
        """Único camino del juego para aplicar la decisión de una mazmorra
        normal: solo si `mazmorra.completar()` acepta (cuarto final con
        el sello cumplido y aún no completada). Así registrar_decision
        se aplica una sola vez por mazmorra. Con `terminal` (la
        TerminalDecision resuelta) aplica además, una sola vez, la
        consecuencia narrativa de la campaña (indicadores, reputación,
        puntos). Retorna True si se aplicó."""
        if not mazmorra.completar():
            return False
        self.registrar_decision(mazmorra.nombre_zona, resultado)
        self.campania.ultima_consecuencia = None
        self.campania.ultimos_deltas = {}
        if terminal is not None:
            consecuencia = self.campania.consecuencia_de_terminal(mazmorra.nombre_zona, terminal)
            if consecuencia is not None:
                self.campania.aplicar_consecuencia(mazmorra.nombre_zona, consecuencia)
        return True

    def registrar_decision(self, zona, resultado):
        """Resultado del minijuego de la mazmorra de `zona`: aplica
        colapso y progreso, y ajusta los pesos (y barricadas) de las
        calles de la entrada de la zona."""
        self.progreso.registrar_decision(resultado, self.colapso)
        self.ciudad.actualizar_tras_mazmorra(zona, resultado == PURIFICACION_EXITOSA)

    def hay_derrota_global(self):
        return self.colapso.esta_colapsado()
