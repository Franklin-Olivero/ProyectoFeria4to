"""Recorre la campaña completa con el juego REAL (Main.main y su loop) y guarda capturas.

No simula la lógica aparte: engancha pygame.display.flip y, frame a frame, un
guion envía las mismas teclas que un jugador. Para ir rápido, quita enemigos y
coloca al jugador frente a cada puerta, pero las decisiones, la crisis, la
redención, las elecciones y los finales pasan por el código de la partida.

    python tools/recorrido_campania.py --capturas docs/capturas/premium
    python tools/recorrido_campania.py --ventana       # ventana real (sin dummy)

También lo usa tests/test_campania_completa.py. El reloj va a 60 FPS simulados
(sin esperar), salvo con --tiempo-real.
"""

import argparse
import os
import sys

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)
os.chdir(RAIZ)


class FinDelGuion(Exception):
    pass


class RelojSimulado:
    def __init__(self, fps=60):
        self.ms = round(1000 / fps)
        self.acumulado = 0

    def tick_busy_loop(self, _=0):
        self.acumulado += self.ms
        return self.ms

    tick = tick_busy_loop

    def get_fps(self):
        return 1000 / self.ms


class Conductor:
    """Da acceso a las variables locales del loop de la partida y envía teclas."""

    def __init__(self, pygame, carpeta=None, verboso=False):
        self.pygame = pygame
        self.carpeta = carpeta
        self.verboso = verboso
        self.capturas = []
        self.pasos = []
        self.frames = 0

    # --- estado del juego ---------------------------------------------
    def locales(self):
        frame = sys._getframe(1)
        while frame is not None:
            if frame.f_code.co_name == "_jugar" and "partida" in frame.f_locals:
                return frame.f_locals
            frame = frame.f_back
        return None

    def tecla(self, *teclas):
        for tecla in teclas:
            self.pygame.event.post(self.pygame.event.Event(self.pygame.KEYDOWN, key=tecla, mod=0, unicode=""))
            self.pygame.event.post(self.pygame.event.Event(self.pygame.KEYUP, key=tecla, mod=0))

    def captura(self, nombre):
        if self.carpeta is None:
            return
        os.makedirs(self.carpeta, exist_ok=True)
        ruta = os.path.join(self.carpeta, f"{nombre}.png")
        self.pygame.image.save(self.pygame.display.get_surface(), ruta)
        self.capturas.append(ruta)

    def log(self, texto):
        if self.verboso:
            print(f"[{self.frames:6d}] {texto}", flush=True)


def guion_completo(c, opciones):
    """Generador: cada `yield` espera un frame; `yield n` espera n frames."""
    pg = c.pygame
    ENTER, ESC, IZQ, DER, E = pg.K_RETURN, pg.K_ESCAPE, pg.K_LEFT, pg.K_RIGHT, pg.K_e

    def L():
        return c.locales()

    def esperar_jugar():
        while L() is None:
            yield 1

    def cerrar_overlays(capturar=None, limite=6000):
        """Avanza diálogos, cinemáticas e indicadores con Enter, con calma."""
        n = 0
        tomas_vistas = set()
        for _ in range(limite):
            loc = L()
            if loc is None:
                return
            indicador = loc["indicador_rep"]
            dialogo = loc["dialogo"]
            if indicador is None and dialogo is None:
                return
            yield 12
            if capturar and dialogo is not None:
                actual = getattr(dialogo, "actual", None)
                clave = (id(dialogo), getattr(dialogo, "indice", 0))
                if actual is not None and clave not in tomas_vistas:
                    tomas_vistas.add(clave)
                    yield 110  # lectura: el texto se escribe y el fundido termina
                    dialogo_actual = L()["dialogo"]
                    if dialogo_actual is not None and not dialogo_actual.texto_completo:
                        c.tecla(ENTER)  # revela si aún se escribe
                        yield 6
                    n += 1
                    c.captura(f"{capturar}_{n:02d}")
                    c.tecla(ENTER)
                    continue
            if capturar and indicador is not None and indicador.tiempo > 2.5:
                n += 1
                c.captura(f"{capturar}_rep_{n:02d}")
            c.tecla(ENTER)

    # ------------------------------------------------------ menú y roles
    yield 30
    c.captura("01_menu")
    c.tecla(ENTER)  # JUGAR
    yield 30
    c.captura("02_modo")
    c.tecla(pg.K_1)
    yield 30
    c.captura("03_roles")
    c.tecla(*([DER] * opciones.get("rol", 2)))  # Periodista por defecto
    yield 5
    c.tecla(ENTER)
    yield from esperar_jugar()
    c.log("partida iniciada")
    yield 20

    # ------------------------------------------------------ intro: espera a Enter
    loc = L()
    intro = loc["dialogo"]
    assert intro is not None and intro.modo == "manual"
    toma_inicial = intro.actual.id
    yield 60 * 40  # 40 s simulados sin tocar nada: nada debe avanzar solo
    assert L()["dialogo"].actual.id == toma_inicial, "una escena con texto avanzó sola"
    c.log("la intro esperó 40 s en la primera toma")
    yield from cerrar_overlays("04_intro")
    assert L()["dialogo"] is None
    yield 30
    c.captura("05_ciudad")
    campania = L()["partida"].campania
    assert L()["escena"].name == "CIUDAD"

    # ------------------------------------------------------ utilidades de zona
    def ir_a_puerta(zona):
        from src.dungeon import ciudad_mapa
        col, fila = ciudad_mapa.ENTRADAS[zona]
        x, y = ciudad_mapa.centro_casilla(col, fila)
        L()["jugador"].colocar_en((x, y + 8))

    def entrar(zona, capturar=None):
        ir_a_puerta(zona)
        yield 3
        c.tecla(E)
        yield 6
        yield from cerrar_overlays(capturar)
        assert L()["escena"].name in ("MAZMORRA", "JEFE"), L()["escena"]

    def limpiar_cuartos(recoger=3, capturar=None):
        """Limpia todos los cuartos intermedios tocando puertas de verdad y
        recoge `recoger` pruebas del suelo; deja al jugador en el cuarto final."""
        recogidas = 0
        mazmorra = L()["mazmorra"]
        m = mazmorra.mazmorra
        for _ in range(400):
            loc = L()
            mazmorra = loc["mazmorra"]
            if mazmorra is None:
                return
            jugador = loc["jugador"]
            m = mazmorra.mazmorra
            mazmorra.gracia.restante = 0.0
            while mazmorra.cuarto.enemigos:
                mazmorra.cuarto.eliminar_un_enemigo()
            yield 3
            zona = m.nombre_zona
            if campania.hay_evidencia_suelta(zona, m.actual):
                if capturar and recogidas == 0:
                    yield 12
                    c.captura(f"{capturar}_prueba_suelta")
                if recogidas < recoger:
                    punto = (mazmorra.cuarto.rect.centerx, mazmorra.cuarto.rect.centery - 40)
                    jugador.colocar_en(punto)
                    yield 2
                    recogidas += 1
                    if capturar and recogidas == 1:
                        yield 10
                        c.captura(f"{capturar}_prueba_recogida")
                    yield 2
            if m.final_desbloqueado() and m.actual == m.cuarto_final:
                return
            # Siguiente cuarto: BFS real por el grafo evitando el final si está sellado.
            grafo = m.grafo
            pendientes = [n for n in grafo.nodos() if n not in m.limpiados and n != m.cuarto_final]
            destino = pendientes[0] if pendientes else m.cuarto_final
            if destino != m.cuarto_final:
                grafo = grafo.copia()
                grafo.eliminar_nodo(m.cuarto_final)
            ruta = grafo.camino(grafo.bfs(m.actual)[2], m.actual, destino)
            if len(ruta) < 2:
                return
            direccion = next(d for d, v in m.puertas(m.actual).items() if v == ruta[1])
            puerta = mazmorra.cuarto.puertas[direccion]
            jugador.rect.center = puerta.rect.center
            jugador.posicion.update(jugador.rect.center)
            jugador.detener()
            yield 3
        raise AssertionError("no se pudo limpiar la mazmorra")

    def decidir(*teclas, capturar=None):
        """Abre la terminal (limpia el cuarto final) y navega."""
        for _ in range(240):
            loc = L()
            if loc["escena"].name == "DECISION":
                break
            mazmorra = loc["mazmorra"]
            mazmorra.gracia.restante = 0.0
            while mazmorra.cuarto.enemigos:
                mazmorra.cuarto.eliminar_un_enemigo()
            yield 2
        assert L()["escena"].name == "DECISION", L()["escena"]
        yield 45
        if capturar:
            c.captura(f"{capturar}_terminal")
        for i, tecla in enumerate(teclas):
            c.tecla(tecla)
            yield 8
            if capturar and tecla == ENTER and i == 0:
                c.captura(f"{capturar}_terminal_nivel2")
        yield 6

    def salir_de_resultado(capturar=None):
        """Del resultado a la ciudad: indicador, propagación, investigación."""
        n = 0
        for _ in range(60):
            loc = L()
            if loc["escena"].name == "CIUDAD":
                return
            yield from cerrar_overlays(f"{capturar}_cierre" if capturar else None)
            loc = L()
            if loc["investigacion"] is not None and not loc["investigacion"].terminada:
                return
            yield 90 if capturar else 10
            if capturar:
                n += 1
                c.captura(f"{capturar}_resultado_{n}")
            c.tecla(ENTER)
            yield 6
        raise AssertionError("no se volvió a la ciudad")

    def atender_crisis(capturar=None):
        yield 20
        yield from cerrar_overlays(capturar)

    # ------------------------------------------------------ cap. 1: sin pruebas, comparte
    insistir = (ENTER, DER, ENTER)
    yield from entrar("Colegio", "10_capitulo1")
    yield 40
    c.captura("11_colegio_combate")
    yield from limpiar_cuartos(recoger=3, capturar="12_colegio")
    yield 30
    c.captura("13_colegio_cuarto_final")
    yield from decidir(*insistir, capturar="14_colegio")
    assert L()["escena"].name == "RESULTADO"
    yield 10
    c.captura("15_indicador_reputacion_animando")
    yield from salir_de_resultado("16_colegio")
    assert L()["escena"].name == "CIUDAD"
    valor = campania.reputacion
    c.log(f"Colegio: reputación {valor}")
    assert valor < -20
    yield 40
    c.captura("17_ciudad_reputacion_baja")
    yield 60 * 3
    c.captura("18_ciudad_reaccion")

    # ------------------------------------------------------ cap. 3: insiste otra vez => crisis
    yield from entrar("Empresa de Medios", "20_capitulo3")
    yield 30
    c.captura("21_medios_combate")
    yield from limpiar_cuartos(recoger=3)
    yield 30
    c.captura("22_medios_cuarto_final")
    yield from decidir(*insistir, capturar="23_medios")
    # Investigación: DFS hasta el origen.
    yield from salir_de_resultado()
    loc = L()
    assert loc["investigacion"] is not None, "no apareció la investigación"
    yield 30
    c.captura("24_investigacion_inicio")
    inv = loc["investigacion"]
    # Baja por el hilo real hasta nova_root y señala.
    for cuenta in ("nova_despierta", "repetidor", "nova_root"):
        while inv.opcion_seleccionada.cuenta != cuenta:
            c.tecla(DER)
            yield 3
        c.tecla(ENTER)
        yield 12
        c.captura(f"25_investigacion_{cuenta}")
    while inv.opcion_seleccionada.tipo != "senalar":
        c.tecla(DER)
        yield 3
    c.tecla(ENTER)
    yield 12
    assert inv.terminada and inv.resultado.correcto
    c.captura("26_investigacion_veredicto")
    yield from salir_de_resultado()
    assert L()["escena"].name == "CIUDAD"

    # ------------------------------------------------------ crisis y rechazo => final de derrota
    assert campania.rep(0).valor <= -60, campania.rep(0).valor
    yield from atender_crisis("30_crisis")
    for _ in range(10):
        if L()["eleccion_crisis"] is not None:
            break
        yield 12
    assert L()["eleccion_crisis"] is not None, "no apareció la elección de la crisis"
    assert L()["eleccion_crisis"].seleccion == "aceptar" and L()["eleccion_crisis"].resultado is None
    yield 50  # pasa la pausa que protege de un Enter accidental
    c.captura("31_crisis_eleccion")
    c.tecla(DER)
    yield 8
    c.captura("32_crisis_rechazar")
    c.tecla(ENTER)
    yield 6
    assert campania.rep(0).sin_voz
    yield from cerrar_overlays("33_rechazo")
    yield 20
    assert L()["final_derrota"] is not None, "no apareció el final de derrota"
    yield 30
    c.captura("34_final_confianza_perdida")
    # Punto de control: vuelve a elegir, y esta vez acepta.
    assert L()["final_derrota"].opciones[0] == "reintentar"
    yield 40
    c.tecla(ENTER)
    yield 8
    assert L()["eleccion_crisis"] is not None
    assert not campania.rep(0).sin_voz
    yield 45
    c.tecla(ENTER)  # ACEPTAR
    yield 50
    mision = campania.mision_de(0)
    assert mision is not None and L()["etapa_abierta"] == 0

    # ------------------------------------------------------ misión: etapas 1, 2 y 3
    def elegir_en_arbol(arbol, correcta):
        for i, nodo in enumerate(arbol.opciones):
            if arbol.respuestas[nodo.id].correcta == correcta:
                while arbol.indice != i:
                    c.tecla(DER)
                    yield 3
                c.tecla(ENTER)
                yield 8
                return
        raise AssertionError

    yield 20
    c.captura("40_etapa1_publicacion")
    yield from elegir_en_arbol(mision.arbol_reconocer, False)
    c.captura("41_etapa1_error_explicado")
    yield from elegir_en_arbol(mision.arbol_reconocer, True)
    yield 10
    c.captura("42_etapa1_responsabilidad")
    yield from elegir_en_arbol(mision.arbol_reconocer, True)
    assert mision.etapa == "corregir" and L()["etapa_abierta"] is None
    yield 40
    c.captura("43_baliza_kiosco")
    from src.dungeon import ciudad_mapa
    from src.dungeon.grafo_ciudad import ZONA_INICIO
    L()["jugador"].colocar_en(ciudad_mapa.posicion_aparicion(ZONA_INICIO))
    yield 10
    c.captura("44_baliza_cerca")
    c.tecla(E)
    yield 12
    assert L()["etapa_abierta"] == 0
    c.captura("45_etapa2_grafo")
    while mision.ciudadano_elegido != "julio":
        c.tecla(DER)
        yield 3
    c.tecla(ENTER)
    yield 12
    c.captura("46_etapa2_publicada")
    if mision.etapa == "corregir":
        while mision.ciudadano_elegido != "ana":
            c.tecla(DER)
            yield 3
        c.tecla(ENTER)
        yield 12
        c.captura("47_etapa2_segunda")
    assert mision.etapa == "confianza", mision.etapa
    assert L()["etapa_abierta"] is None
    L()["jugador"].colocar_en(ciudad_mapa.posicion_aparicion(mision.zona))
    yield 8
    c.tecla(E)
    yield 12
    assert L()["etapa_abierta"] == 0
    c.captura("48_etapa3_ayuda")
    yield from elegir_en_arbol(mision.arbol_confianza, True)
    assert campania.rep(0).estado_crisis == "redimido"
    yield from cerrar_overlays("49_redencion")
    assert campania.rep(0).valor < 0
    c.log(f"Redimido: reputación {campania.rep(0).valor}")
    yield 20
    c.captura("50_ciudad_redimido")

    # ------------------------------------------------------ cap. 2: verifica y comparte la verdad
    yield from entrar("Hospital", "51_capitulo2")
    yield 30
    c.captura("52_hospital_combate")
    yield from limpiar_cuartos(recoger=2)
    yield from decidir(capturar="53_hospital")
    # Verificar => muestra el resultado de la verificación según las pruebas.
    c.tecla(ENTER)
    yield 10
    c.captura("54_hospital_verificar")
    c.tecla(ENTER)
    yield 8
    assert L()["escena"].name == "RESULTADO"
    yield from salir_de_resultado("55_hospital")
    assert campania.resultados["Hospital"].exito

    # ------------------------------------------------------ jefe y epílogo
    assert L()["partida"].alcaldia_desbloqueada()
    yield from entrar("Alcaldía", "60_jefe_entrada")
    assert L()["escena"].name == "JEFE"
    yield 120
    c.captura("61_jefe_combate")
    arena = L()["arena"]
    arena.mazmorra.jefe.vida = 0
    arena.mazmorra.jefe.recibir_dano(1) if hasattr(arena.mazmorra.jefe, "recibir_dano") else None
    for _ in range(600):
        if L()["escena"].name == "VICTORIA":
            break
        L()["arena"].mazmorra.estado = "victoria" if False else L()["arena"].mazmorra.estado
        yield 2
    assert L()["escena"].name == "VICTORIA", L()["escena"]
    yield from cerrar_overlays("62_caida")
    yield 30
    c.captura("63_victoria")
    c.tecla(ENTER)
    yield 60 * 4
    c.captura("64_elecciones")
    c.tecla(ENTER)
    yield 6
    yield from cerrar_overlays("65_final")
    yield 60
    c.captura("66_elecciones_final")
    c.tecla(ENTER)
    yield 30
    assert L()["escena"].name == "CIUDAD"
    c.captura("67_ciudad_tras_final")
    c.log("campaña completa")
    raise FinDelGuion


def ejecutar(guion=guion_completo, carpeta=None, ventana=False, tiempo_real=False, opciones=None, verboso=False,
             maximo_frames=400000):
    if not ventana:
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        os.environ.setdefault("SDL_AUDIODRIVER", "dummy")  # otro valor = probar sin dispositivo de audio
    # Los ajustes que el recorrido cambie van a una carpeta temporal, nunca a
    # la carpeta de datos del jugador (src/core/datos_usuario.py).
    if not os.environ.get("CIVITAS_DATOS"):
        import tempfile
        os.environ["CIVITAS_DATOS"] = tempfile.mkdtemp(prefix="civitas_recorrido_")
    import pygame
    import Main
    from src.core import preferencias as prefs

    conductor = Conductor(pygame, carpeta, verboso)
    original_flip = pygame.display.flip
    generador = {"g": None, "espera": 0}

    def flip():
        original_flip()
        conductor.frames += 1
        if conductor.frames > maximo_frames:
            raise AssertionError("demasiados frames: el guion quedó atascado")
        if generador["espera"] > 0:
            generador["espera"] -= 1
            return
        try:
            espera = next(generador["g"])
        except StopIteration:
            raise FinDelGuion
        generador["espera"] = (espera or 1) - 1

    pygame.display.flip = flip
    generador["g"] = guion(conductor, opciones or {})
    Main.guardar_preferencias = lambda *_: None
    Main.cargar_preferencias = lambda *_: prefs.Preferencias(**(opciones or {}).get("preferencias", {}))
    if not tiempo_real:
        Main.crear_reloj = lambda: RelojSimulado()
    try:
        Main.main()
    except FinDelGuion:
        pass
    finally:
        pygame.display.flip = original_flip
        pygame.quit()
    return conductor


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--capturas", default=None)
    parser.add_argument("--ventana", action="store_true")
    parser.add_argument("--tiempo-real", action="store_true")
    parser.add_argument("--rol", type=int, default=2)
    args = parser.parse_args()
    resultado = ejecutar(carpeta=args.capturas, ventana=args.ventana, tiempo_real=args.tiempo_real,
                         opciones={"rol": args.rol}, verboso=True)
    print(f"OK: {resultado.frames} frames, {len(resultado.capturas)} capturas")
