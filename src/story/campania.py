"""Estado de la campaña "Código Nova" dentro de una partida (sin Pygame).

Vive en Partida.campania y sobrevive entre mazmorras:
    - qué diálogos ya se vieron (prólogo una vez, intro de cada zona una vez);
    - qué evidencias se revelaron en cada zona y las pistas de NOVA_404 que
      salieron de ellas (lista sin repetidos). Al limpiar un cuarto la prueba
      queda en el suelo (`evidencias_sueltas`): hay que ir a recogerla, así
      que decidir sin todas las pruebas es una posibilidad real;
    - el escenario activo (árbol armado para el estado de evidencia del
      momento) y la consecuencia de cada zona;
    - los indicadores de Ciudad Nova (EstadoCiudad), los puntos y la
      REPUTACIÓN DE CADA JUGADOR (ReputacionJugador, una por índice);
    - la red social (src/story/red_social.py): la publicación de cada zona
      viaja por BFS al resolverse la terminal y su alcance real ajusta
      indicadores y reputación;
    - los eventos aleatorios al volver a la ciudad (src/story/eventos.py)
      con un random.Random(semilla) propio, reproducible en los tests;
    - el matiz narrativo del rol (balance.py), el rastreo del origen de la
      señal y la caída del jefe;
    - la crisis de reputación y la misión de redención.

Reglas contra dobles recompensas: los efectos sobre los indicadores se
aplican cada vez que se resuelve una terminal (la ciudad reacciona a
cada publicación), pero los puntos y la reputación positiva de una
zona se cobran una sola vez; las penalizaciones sí se repiten.
Partida.cerrar_mazmorra es quien llama a aplicar_consecuencia, y solo
cuando la mazmorra acepta completarse. Todo cambio de indicadores pasa
por `_aplicar_efectos`.

Multijugador: el host es la autoridad (`espejo` = False). Un invitado tiene
`espejo` = True: no aplica consecuencias y copia el estado con
`aplicar_resumen_red`. Cada jugador se identifica por su índice en la lista
de jugadores de la partida.
"""

import random

from src.core.assets import FONDO_POR_ZONA, FONDO_PROLOGO
from src.core.balance import (
    BIENESTAR_POR_ALCANZADO,
    CONFIANZA_EXTRA_CIUDADANO,
    DESINFORMACION_POR_ALCANZADO,
    EFECTOS_JEFE_DERROTADO,
    EFECTOS_RECHAZO_REDENCION,
    EFECTOS_REDENCION,
    EVENTOS_RECIENTES_CINTILLO,
    EVIDENCIA_INICIAL_PERIODISTA,
    MULTIPLICADOR_PENALIZACION_CANDIDATO,
    PUNTOS_JEFE_DERROTADO,
    REBOTE_EXTRA_INFLUENCER,
    RECUPERACION_REDENCION,
    SALTOS_CORRECCION_CRISIS,
    SALTOS_CORRECCION_CUESTIONADA,
    SALTOS_CORRECCION_REFERENTE,
    SALTOS_MAXIMOS_PROPAGACION,
    TIEMPO_EXTRA_TERMINAL_REFERENTE,
    TOPE_REPUTACION_TRAS_REDENCION,
    UMBRAL_CONFIANZA,
    UMBRAL_CRISIS_REPUTACION,
    UMBRAL_DESCONFIANZA,
    UMBRAL_REFERENTE,
    VERIFICADA_POR_CORREGIDO,
    ZONA_EMPRESA_MEDIOS,
)
from src.story import contenido as contenido_mod
from src.story import reputacion as rep_mod
from src.story.cinematica import (
    guion_crisis,
    guion_entrada_jefe,
    guion_intro,
    guion_rechazo,
    guion_redencion,
    tarjeta_capitulo,
)
from src.story.dialogo import DialogoSecuencia
from src.story.escenarios import PARCIAL, SIN_PRUEBAS, EscenarioDecision, estado_evidencia
from src.story.estado_ciudad import EstadoCiudad
from src.story.eventos import sortear_evento
from src.story.investigacion import Investigacion
from src.story.red_social import CORRECCION, RUMOR, RedSocial
from src.story.redencion import MisionRedencion
from src.story.reputacion import ReputacionJugador

ZONA_INVESTIGACION = ZONA_EMPRESA_MEDIOS  # capítulo 3: el origen de la señal

ROL_INFLUENCER = "influencer"
ROL_CIUDADANO = "ciudadano"
ROL_PERIODISTA = "periodista"
ROL_CANDIDATO = "candidato"


class Campania:
    def __init__(self, contenido=None, semilla=None):
        self.contenido = contenido if contenido is not None else contenido_mod.cargar()
        self.semilla = semilla
        self.rol = None
        self.roles = {}  # índice de jugador -> clave del rol
        self.espejo = False  # True en un invitado: el estado llega del host
        self.reiniciar()

    def reiniciar(self):
        self.rng = random.Random(self.semilla)
        self.prologo_visto = False
        self.intros_vistas = set()
        self.evidencias_reveladas = {}  # zona -> cantidad revelada
        self.evidencias_sueltas = {}  # zona -> {cuarto: True}: pruebas en el suelo sin recoger
        self.evidencias_nuevas = []  # recién reveladas, para la tarjeta en pantalla
        self.pistas = []  # ids de evidencia con pista, en orden de hallazgo
        self.escenario_activo = None
        self.zona_activa = None
        self.exige_mas_pruebas = False  # reputación cuestionada: lo parcial no basta
        self.resultados = {}  # zona -> última Consecuencia
        self.recompensadas = set()  # zonas cuya recompensa positiva ya se cobró
        self.ultima_consecuencia = None
        self.ultimos_deltas = {}
        self.ultimo_cambio_reputacion = None
        self.estado = EstadoCiudad()
        self.reputaciones = {}  # índice de jugador -> ReputacionJugador
        self.actor_decision = 0  # quien confirmó la última opción en la terminal
        self.puntos = 0
        self.red = RedSocial(self.contenido["red_social"], self.rng)
        self.ultima_propagacion = None  # (rumor, corrección o None) de la última zona
        self.eventos_ocurridos = []  # EventoOcurrido en orden
        self.origen_elegido = None  # ResultadoInvestigacion del capítulo 3
        self.jefe_derrotado = False
        self.misiones_redencion = {}  # índice -> MisionRedencion activa
        self.esperando_host = set()  # invitado: índices cuya decisión el host aún no refleja
        self.puntos_control = {}  # índice -> instantánea al abrirse la crisis
        self.zonas_visitadas_ayuda = set()  # zonas donde un ciudadano ya aportó una prueba
        self.version = 0  # cambia con cada novedad que deben ver los invitados

    def establecer_rol(self, rol, indice=0):
        """Clave del rol ("periodista"...), para los matices narrativos."""
        self.roles[indice] = rol
        if indice == 0 or self.rol is None:
            self.rol = rol

    # ------------------------------------------------------------------
    # Reputación de cada jugador
    # ------------------------------------------------------------------

    def rep(self, indice=0):
        """ReputacionJugador del jugador `indice` (se crea la primera vez)."""
        if indice not in self.reputaciones:
            self.reputaciones[indice] = ReputacionJugador()
        return self.reputaciones[indice]

    @property
    def reputacion(self):
        """Reputación del J1 (en solitario, la única)."""
        return self.rep(0).valor

    def reputacion_colectiva(self):
        """Promedio de los jugadores: lo que pesa en las elecciones y finales."""
        if not self.reputaciones:
            return self.rep(0).valor
        valores = [r.valor for r in self.reputaciones.values()]
        return sum(valores) / len(valores)

    def puede_decidir(self, indice):
        """Quien rechazó o falló la redención ya no decide por la ciudad."""
        return not self.rep(indice).sin_voz

    def todos_sin_voz(self):
        return bool(self.reputaciones) and all(r.sin_voz for r in self.reputaciones.values())

    def hubo_redencion(self):
        return any(r.redenciones > 0 for r in self.reputaciones.values())

    def saltos_correccion(self, indice=0):
        """Hasta dónde llega una corrección publicada por este jugador: la
        credibilidad se traduce en alcance real dentro del BFS."""
        valor = self.rep(indice).valor
        if valor >= UMBRAL_REFERENTE:
            return SALTOS_CORRECCION_REFERENTE
        if valor <= UMBRAL_CRISIS_REPUTACION:
            return SALTOS_CORRECCION_CRISIS
        if valor <= UMBRAL_DESCONFIANZA:
            return SALTOS_CORRECCION_CUESTIONADA
        return SALTOS_MAXIMOS_PROPAGACION

    def _mensaje_reputacion(self, accion, veredicto, estado):
        tabla = self.contenido["mensajes_reputacion"].get(accion, {})
        textos = tabla.get(rep_mod.clase_veracidad(veredicto), {})
        conocimiento = rep_mod.conocimiento_de(estado)
        return textos.get(conocimiento) or textos.get(rep_mod.SABIA) or textos.get(rep_mod.SIN_SABER, "")

    # ------------------------------------------------------------------
    # Diálogos
    # ------------------------------------------------------------------

    def dialogo_prologo(self, rol=None, nombre_rol="Tú"):
        """La secuencia del prólogo la primera vez; después None."""
        if self.prologo_visto:
            return None
        self.prologo_visto = True
        return DialogoSecuencia(self.contenido["prologo"], rol, nombre_rol, len(self.pistas),
                                titulo=self.contenido["titulo"], fondo=FONDO_PROLOGO)

    def cinematica_intro(self, rol=None, nombre_rol="Tú"):
        """La cinemática inicial la primera vez (reemplaza al prólogo en
        texto: ambos cuentan como "prólogo visto"); después None."""
        if self.prologo_visto:
            return None
        self.prologo_visto = True
        return guion_intro(self.contenido, rol, nombre_rol)

    def cinematica_intro_repetida(self, rol=None, nombre_rol="Tú"):
        """Para volver a ver la introducción (EXTRAS): no cambia el estado."""
        return guion_intro(self.contenido, rol, nombre_rol)

    def texto_intro_rol(self, rol):
        return self.contenido.get("intro_rol", {}).get(rol)

    def presentacion_zona(self, zona, rol=None, nombre_rol="Tú", indice=0):
        """(cinemática, diálogo) al entrar a `zona` la primera vez: la
        tarjeta del capítulo y luego su diálogo; en la Alcaldía, la
        cinemática de entrada al jefe sin diálogo. (None, None) si ya se vio."""
        capitulo = self.contenido["capitulos"].get(zona)
        if capitulo is None or zona in self.intros_vistas:
            return None, None
        numero = capitulo.get("numero", 0)
        if numero >= 4:
            self.intros_vistas.add(zona)
            return guion_entrada_jefe(len(self.pistas), self.total_pistas(), capitulo), None
        tarjeta = tarjeta_capitulo(numero, capitulo["titulo"], zona, ubicacion=capitulo.get("ubicacion", ""),
                                   contexto=capitulo.get("contexto", ""), objetivo=capitulo.get("objetivo", ""))
        return tarjeta, self.dialogo_capitulo(zona, rol, nombre_rol, indice)

    def dialogo_capitulo(self, zona, rol=None, nombre_rol="Tú", indice=0):
        """La intro del capítulo de `zona` la primera vez que se entra;
        None si ya se vio o la zona no tiene capítulo."""
        capitulo = self.contenido["capitulos"].get(zona)
        if capitulo is None or zona in self.intros_vistas:
            return None
        self.intros_vistas.add(zona)
        numero = capitulo.get("numero", 0)
        titulo = f"Capítulo {numero}: {capitulo['titulo']}" if numero < 4 else f"Final: {capitulo['titulo']}"
        return DialogoSecuencia(capitulo["intro"], rol, nombre_rol, len(self.pistas), titulo=titulo,
                                fondo=FONDO_POR_ZONA.get(zona), reputacion=self.rep(indice).valor)

    def titulo_capitulo(self, zona):
        capitulo = self.contenido["capitulos"].get(zona)
        return capitulo["titulo"] if capitulo else zona

    # ------------------------------------------------------------------
    # Evidencias y pistas
    # ------------------------------------------------------------------

    def tiene_escenario(self, zona):
        return zona in self.contenido["escenarios"]

    def evidencias_de(self, zona):
        return self.contenido["escenarios"][zona]["evidencias"] if self.tiene_escenario(zona) else []

    def evidencias_reveladas_de(self, zona):
        total = self.evidencias_de(zona)
        return total[: self.evidencias_reveladas.get(zona, 0)]

    def revelar_evidencia(self, zona):
        """Revela la siguiente evidencia de `zona`. Retorna el diccionario
        de la evidencia, o None si no quedan. Si trae pista, la suma una
        sola vez."""
        evidencias = self.evidencias_de(zona)
        indice = self.evidencias_reveladas.get(zona, 0)
        if indice >= len(evidencias):
            return None
        evidencia = evidencias[indice]
        self.evidencias_reveladas[zona] = indice + 1
        if evidencia.get("pista") and evidencia["id"] not in self.pistas:
            self.pistas.append(evidencia["id"])
        self.evidencias_nuevas.append(evidencia)
        self.version += 1
        return evidencia

    def tomar_evidencia_nueva(self):
        return self.evidencias_nuevas.pop(0) if self.evidencias_nuevas else None

    def soltar_evidencia(self, zona, cuarto):
        """Un cuarto recién limpio deja una prueba en el suelo, si a la zona
        aún le quedan por encontrar. Retorna True si se soltó."""
        sueltas = self.evidencias_sueltas.setdefault(zona, {})
        restantes = len(self.evidencias_de(zona)) - self.evidencias_reveladas.get(zona, 0) - len(sueltas)
        if restantes <= 0 or cuarto in sueltas:
            return False
        sueltas[cuarto] = True
        self.version += 1
        return True

    def hay_evidencia_suelta(self, zona, cuarto):
        return cuarto in self.evidencias_sueltas.get(zona, {})

    def recoger_evidencia(self, zona, cuarto):
        """Un jugador tocó la prueba del `cuarto`: se revela una sola vez."""
        sueltas = self.evidencias_sueltas.get(zona, {})
        if cuarto not in sueltas:
            return None
        del sueltas[cuarto]
        self.version += 1
        return self.revelar_evidencia(zona)

    def al_entrar_zona(self, zona, indice=0):
        """Matiz del Periodista: identifica una fuente extra al entrar
        (la primera evidencia, si la zona aún no tiene ninguna). Retorna
        la evidencia revelada o None."""
        rol = self.roles.get(indice, self.rol)
        if rol != ROL_PERIODISTA or self.evidencias_reveladas.get(zona, 0) >= EVIDENCIA_INICIAL_PERIODISTA:
            return None
        return self.revelar_evidencia(zona)

    def aporte_ciudadano(self, zona, indice=0):
        """Oportunidad de la buena reputación: un ciudadano que confía en el
        jugador le envía una prueba al entrar a la zona (una vez por zona).
        Retorna (nombre del ciudadano, evidencia) o None."""
        if self.rep(indice).valor < UMBRAL_CONFIANZA or zona in self.zonas_visitadas_ayuda:
            return None
        self.zonas_visitadas_ayuda.add(zona)
        evidencia = self.revelar_evidencia(zona)
        if evidencia is None:
            return None
        nodo = self.rng.choice(sorted(self.red.corregidos) or self.red.ciudadanos())
        return self.red.nombre(nodo), evidencia

    def estado_evidencia(self, zona):
        if not self.tiene_escenario(zona):
            return estado_evidencia(0, 0, "sin_verificar")
        datos = self.contenido["escenarios"][zona]
        return estado_evidencia(self.evidencias_reveladas.get(zona, 0), len(datos["evidencias"]), datos["veredicto"])

    def textos_pistas(self):
        return [self.contenido["pistas"][id_pista] for id_pista in self.pistas]

    def total_pistas(self):
        return len(self.contenido["pistas"])

    # ------------------------------------------------------------------
    # Escenario de decisión
    # ------------------------------------------------------------------

    def preparar_escenario(self, zona, indice=0):
        """Arma el árbol de `zona` con el estado de evidencia de AHORA
        (se llama cuando el cuarto final abre la terminal) y lo deja
        como escenario activo. Con reputación cuestionada las pruebas
        parciales ya no bastan: la ciudad exige todas. None si no hay escenario."""
        if not self.tiene_escenario(zona):
            self.escenario_activo = None
            self.zona_activa = None
            return None
        estado = self.estado_evidencia(zona)
        self.exige_mas_pruebas = estado == PARCIAL and self.rep(indice).valor <= UMBRAL_DESCONFIANZA
        if self.exige_mas_pruebas:
            estado = SIN_PRUEBAS
        self.escenario_activo = EscenarioDecision(self.contenido["escenarios"][zona], estado)
        self.zona_activa = zona
        self.actor_decision = indice
        return self.escenario_activo

    def duracion_extra_terminal(self, indice=0):
        return TIEMPO_EXTRA_TERMINAL_REFERENTE if self.rep(indice).valor >= UMBRAL_REFERENTE else 0.0

    def registrar_actor(self, indice):
        """Quien confirma en la terminal carga con la decisión."""
        if self.puede_decidir(indice):
            self.actor_decision = indice

    def consecuencia_de_terminal(self, zona, terminal):
        """Consecuencia del resultado de `terminal` en `zona`, o None si
        no hay escenario activo para esa zona."""
        if self.escenario_activo is None or self.zona_activa != zona:
            return None
        return self.escenario_activo.consecuencia_para(terminal)

    def aplicar_consecuencia(self, zona, consecuencia, actor=None):
        """Aplica efectos (más los de la propagación por la red social y
        el matiz del rol), puntos y la reputación de quien decidió. Retorna
        los deltas reales sobre los indicadores. (La llama
        Partida.cerrar_mazmorra.)"""
        actor = actor if actor is not None else self.actor_decision
        rol_actor = self.roles.get(actor, self.rol)
        efectos = dict(consecuencia.efectos)
        if consecuencia.exito and rol_actor == ROL_CIUDADANO:
            efectos["confianza"] = efectos.get("confianza", 0) + CONFIANZA_EXTRA_CIUDADANO
        self.ultima_propagacion, afectados = self._propagar_publicacion(zona, consecuencia, efectos, actor, rol_actor)
        self.ultimos_deltas = self._aplicar_efectos(efectos)

        premiar = not (consecuencia.exito and zona in self.recompensadas)
        if premiar:
            self.puntos += consecuencia.puntos
        self.ultimo_cambio_reputacion = self._valorar_decision(zona, consecuencia, afectados, actor, rol_actor)
        consecuencia.reputacion = self.ultimo_cambio_reputacion.delta if self.ultimo_cambio_reputacion else 0
        if consecuencia.exito:
            self.recompensadas.add(zona)
        self.resultados[zona] = consecuencia
        self.ultima_consecuencia = consecuencia
        self.escenario_activo = None
        self.zona_activa = None
        self.version += 1
        return self.ultimos_deltas

    def _valorar_decision(self, zona, consecuencia, afectados, actor, rol_actor):
        """El cambio real de reputación: tabla de acciones + gravedad +
        alcance (BFS) + matiz del Candidato. Lo positivo se cobra una vez
        por zona; lo negativo se repite cada vez que se decide mal."""
        datos = self.contenido["escenarios"].get(zona, {})
        veredicto = datos.get("veredicto", "sin_verificar")
        delta = rep_mod.valorar_accion(consecuencia.accion, veredicto, consecuencia.estado_evidencia,
                                       datos.get("gravedad", "media"))
        delta = rep_mod.ajuste_por_alcance(delta, afectados)
        if delta < 0 and rol_actor == ROL_CANDIDATO:
            delta = round(delta * MULTIPLICADOR_PENALIZACION_CANDIDATO)
        mensaje = self._mensaje_reputacion(consecuencia.accion, veredicto, consecuencia.estado_evidencia)
        clave = f"decision:{zona}" if delta > 0 else None
        return self.rep(actor).aplicar(delta, mensaje, zona, clave)

    def _aplicar_efectos(self, efectos):
        """Único punto por el que cambian los indicadores."""
        return self.estado.aplicar(efectos)

    def _propagar_publicacion(self, zona, consecuencia, efectos, actor=0, rol_actor=None):
        """La publicación de `zona` viaja por el grafo social y su alcance
        real suma a `efectos`. Retorna (Propagacion principal, afectados):

            engañosa + éxito: el rumor ya era viral (memoria) y sale una corrección;
            engañosa + fallo: solo viaja el rumor;
            veraz + éxito: viaja la información verdadera;
            veraz + fallo: viaja la versión de que era mentira (un rumor).

        La corrección llega tan lejos como la reputación de quien la publica."""
        datos = self.contenido["escenarios"].get(zona, {})
        configuracion = datos.get("propagacion")
        if configuracion is None:
            return None, 0
        origen = configuracion["origen"]
        veraz = rep_mod.clase_veracidad(datos.get("veredicto")) == rep_mod.VERAZ
        extra = REBOTE_EXTRA_INFLUENCER if (rol_actor == ROL_INFLUENCER and not consecuencia.exito) else 0.0
        if veraz and consecuencia.exito:
            verdad = self.red.propagar(origen, tipo=CORRECCION)
            efectos["informacion_verificada"] = efectos.get("informacion_verificada", 0) + int(
                verdad.total * VERIFICADA_POR_CORREGIDO)
            return verdad, verdad.total
        rumor = self.red.propagar(origen, probabilidad_extra=extra, tipo=RUMOR)
        if consecuencia.exito:
            correccion = self.red.corregir(origen, self.saltos_correccion(actor))
            sin_corregir = [n for n in rumor.alcanzados if n not in correccion.alcanzados]
            efectos["desinformacion"] = efectos.get("desinformacion", 0) + int(
                len(sin_corregir) * DESINFORMACION_POR_ALCANZADO)
            efectos["informacion_verificada"] = efectos.get("informacion_verificada", 0) + int(
                correccion.total * VERIFICADA_POR_CORREGIDO)
            return rumor, correccion.total
        efectos["desinformacion"] = efectos.get("desinformacion", 0) + int(
            rumor.total * DESINFORMACION_POR_ALCANZADO)
        efectos["bienestar_digital"] = efectos.get("bienestar_digital", 0) + int(
            rumor.total * BIENESTAR_POR_ALCANZADO)
        return rumor, rumor.total

    def correccion_reciente(self):
        """La Propagacion de la última corrección publicada, si la hubo."""
        return self.red.ultima(CORRECCION)

    # ------------------------------------------------------------------
    # Eventos aleatorios y reacciones de la ciudad
    # ------------------------------------------------------------------

    def hubo_detonacion(self):
        return any(not c.exito for c in self.resultados.values())

    def sortear_evento(self):
        """Al volver a la ciudad: un evento al azar del contenido, con
        sus efectos aplicados una sola vez. Retorna el EventoOcurrido o
        None si el contenido no define eventos."""
        evento = sortear_evento(self.contenido.get("eventos", []), self.rng, self.red, self.hubo_detonacion())
        if evento is None:
            return None
        evento.efectos = self._aplicar_efectos(evento.efectos)
        self.eventos_ocurridos.append(evento)
        return evento

    def titulares(self):
        """Titulares de los últimos eventos, del más reciente al más viejo;
        la reputación de los jugadores también es noticia."""
        recientes = self.eventos_ocurridos[-EVENTOS_RECIENTES_CINTILLO:]
        titulares = [f"Civitas: {evento.titular}" for evento in reversed(recientes)]
        for indice, reputacion in sorted(self.reputaciones.items()):
            if reputacion.sin_voz:
                titulares.insert(0, f"Civitas: J{indice + 1} ya no tiene credibilidad en la ciudad")
            elif reputacion.nivel == "crisis":
                titulares.insert(0, f"Civitas: crecen las críticas contra J{indice + 1} por sus publicaciones")
            elif reputacion.nivel == "referente":
                titulares.insert(0, f"Civitas: vecinos destacan las aclaraciones de J{indice + 1}")
        return titulares

    def reaccion_ciudadana(self, indice=0):
        """Comentario de un ciudadano según el nivel de reputación. Se elige
        con datos reales: quien recibió tu rumor si te va mal y quien recibió
        tu corrección si te va bien. Retorna (texto, nivel)."""
        reputacion = self.rep(indice)
        nivel = reputacion.nivel
        textos = self.contenido["reacciones"][nivel]
        if nivel in ("cuestionada", "crisis"):
            candidatos = sorted(self.red.expuestos - self.red.corregidos) or sorted(self.red.expuestos)
        elif nivel in ("referente", "confiable"):
            candidatos = sorted(self.red.corregidos)
        else:
            candidatos = []
        nodo = self.rng.choice(candidatos or self.red.ciudadanos())
        return self.rng.choice(textos).format(nombre=self.red.nombre(nodo)), nivel

    # ------------------------------------------------------------------
    # Crisis de reputación y redención
    # ------------------------------------------------------------------

    def esperar_host(self, indice):
        """Invitado: acaba de decidir. Hasta que el host lo confirme, su
        snapshot no debe devolverlo a la crisis ni pisar su misión local."""
        self.esperando_host.add(indice)

    def jugador_en_crisis(self, indices=None):
        """Índice del primer jugador con crisis pendiente (entre `indices`,
        los jugadores de esta pantalla), o None."""
        for indice in sorted(self.reputaciones):
            if (indices is None or indice in indices) and self.reputaciones[indice].crisis_pendiente:
                return indice
        return None

    def guion_de_crisis(self, indice, nombre, rol=None):
        return guion_crisis(self.contenido["redencion"], nombre, rol)

    def _zona_danada(self, indice=0):
        """Zona de la peor decisión de este jugador."""
        peor = self.rep(indice).peor_cambio()
        if peor is not None and peor.motivo in self.contenido["escenarios"]:
            return peor.motivo
        for zona, consecuencia in self.resultados.items():
            if not consecuencia.exito:
                return zona
        return next(iter(self.contenido["escenarios"]))

    def guardar_punto_control(self, indice):
        """Instantánea para reintentar desde la crisis tras un final de derrota."""
        reputacion = self.rep(indice)
        self.puntos_control[indice] = {
            "valor": reputacion.valor,
            "indicadores": self.estado.como_dict(),
            "expuestos": set(self.red.expuestos),
            "corregidos": set(self.red.corregidos),
            "historial": len(self.red.historial),
            "puntos": self.puntos,
        }

    def volver_a_punto_control(self, indice):
        """Reintento: la crisis vuelve a estar pendiente, como al abrirse."""
        punto = self.puntos_control.get(indice)
        if punto is None:
            return False
        reputacion = self.rep(indice)
        reputacion.valor = punto["valor"]
        reputacion.estado_crisis = rep_mod.CRISIS_PENDIENTE
        self.estado = EstadoCiudad(dict(punto["indicadores"]))
        self.red.expuestos = set(punto["expuestos"])
        self.red.corregidos = set(punto["corregidos"])
        del self.red.historial[punto["historial"]:]
        self.puntos = punto["puntos"]
        self.misiones_redencion.pop(indice, None)
        self.version += 1
        return True

    def aceptar_redencion(self, indice=0):
        """El jugador acepta: empieza la misión. Retorna la MisionRedencion."""
        reputacion = self.rep(indice)
        if reputacion.estado_crisis != rep_mod.CRISIS_PENDIENTE:
            return self.misiones_redencion.get(indice)
        self.guardar_punto_control(indice)
        reputacion.estado_crisis = rep_mod.EN_REDENCION
        self.version += 1
        return self.crear_mision_redencion(indice)

    def crear_mision_redencion(self, indice=0):
        zona = self._zona_danada(indice)
        datos = self.contenido["redencion"]
        escenario = self.contenido["escenarios"][zona]
        mision = MisionRedencion(datos, escenario["post"], escenario["evidencias"], self.red, datos["ayuda"][zona])
        mision.zona = zona
        self.misiones_redencion[indice] = mision
        return mision

    def mision_de(self, indice=0):
        return self.misiones_redencion.get(indice)

    def completar_redencion(self, indice=0, mision=None):
        """Misión cumplida: devuelve parte de la reputación (menos cada vez
        que recae) sin borrar el pasado: el historial queda y baja el tope.
        Se cobra una sola vez por misión."""
        reputacion = self.rep(indice)
        if reputacion.estado_crisis != rep_mod.EN_REDENCION:
            return None
        recuperacion = RECUPERACION_REDENCION // (1 + reputacion.redenciones)
        reputacion.tope = TOPE_REPUTACION_TRAS_REDENCION
        reputacion.estado_crisis = rep_mod.REDIMIDO
        cambio = reputacion.aplicar(recuperacion, self.contenido["redencion"]["mensaje_recuperacion"],
                                    "Segunda oportunidad", f"redencion:{reputacion.redenciones}")
        reputacion.redenciones += 1
        self.ultimos_deltas = self._aplicar_efectos(dict(EFECTOS_REDENCION))
        self.misiones_redencion.pop(indice, None)
        self.ultimo_cambio_reputacion = cambio
        self.version += 1
        return cambio

    def rechazar_redencion(self, indice=0, estado_final=rep_mod.RECHAZADA):
        """El jugador se niega (o falla la misión): pierde la voz en la
        ciudad y NOVA_404 usa sus publicaciones de ejemplo (el rumor vuelve a
        viajar por el BFS). Los demás jugadores siguen jugando."""
        reputacion = self.rep(indice)
        if reputacion.sin_voz:
            return False
        if indice not in self.puntos_control:
            self.guardar_punto_control(indice)
        reputacion.estado_crisis = estado_final
        self.misiones_redencion.pop(indice, None)
        origen = self.contenido["escenarios"][self._zona_danada(indice)].get("propagacion", {}).get("origen")
        if origen is not None:
            self.ultima_propagacion = self.red.propagar(origen, tipo=RUMOR)
        self.ultimos_deltas = self._aplicar_efectos(dict(EFECTOS_RECHAZO_REDENCION))
        self.version += 1
        return True

    def fallar_redencion(self, indice=0):
        return self.rechazar_redencion(indice, rep_mod.FALLIDA)

    def guion_recuperacion(self, rol=None, nombre="Tú"):
        return guion_redencion(self.contenido["redencion"], rol, nombre)

    def guion_de_rechazo(self):
        return guion_rechazo(self.contenido["redencion"], self.contenido["finales"]["confianza_perdida"])

    def balance_final_individual(self, indice=0):
        """Datos de la pantalla «La confianza perdida»."""
        final = self.contenido["finales"]["confianza_perdida"]
        reputacion = self.rep(indice)
        danos = [c for c in reputacion.historial if c.delta < 0 and c.mensaje]
        danos.sort(key=lambda c: c.delta)
        mensajes = list(dict.fromkeys(c.mensaje for c in danos))  # sin repetir
        return {
            "titulo": final["titulo"],
            "texto": final["texto"],
            "mensaje": final["mensaje"],
            "reputacion": reputacion.valor,
            "nivel": reputacion.nombre_nivel,
            "expuestos": len(self.red.expuestos),
            "sin_corregir": len(self.red.expuestos - self.red.corregidos),
            "ciudadanos": len(self.red.ciudadanos()),
            "consecuencias": mensajes[:3],
            "salud": self.estado.salud(),
            "indicadores": self.estado,
            "punto_control": indice in self.puntos_control,
        }

    # ------------------------------------------------------------------
    # Capítulo 3: origen de la señal, y final: jefe
    # ------------------------------------------------------------------

    def investigacion_pendiente(self, zona):
        """True si al salir de `zona` toca el rastreo (zona del capítulo 3
        ya resuelta y aún sin señalar un origen)."""
        return zona == ZONA_INVESTIGACION and self.origen_elegido is None and zona in self.resultados

    def nueva_investigacion(self):
        return Investigacion(self.contenido["red_cuentas"])

    def registrar_investigacion(self, resultado, actor=None):
        """Aplica el señalamiento una sola vez (el primero cuenta)."""
        if self.origen_elegido is not None:
            return False
        self.origen_elegido = resultado
        self.ultimos_deltas = self._aplicar_efectos(resultado.efectos)
        actor = actor if actor is not None else self.actor_decision
        self.ultimo_cambio_reputacion = self.rep(actor).aplicar(
            resultado.reputacion, resultado.texto, "El origen de la señal", "investigacion")
        self.puntos += resultado.puntos
        self.version += 1
        return True

    @property
    def origen_rastreado(self):
        return self.origen_elegido is not None and self.origen_elegido.correcto

    def registrar_jefe_derrotado(self):
        """Victoria en la Alcaldía: efectos y puntos una sola vez."""
        if self.jefe_derrotado:
            return False
        self.jefe_derrotado = True
        self.ultimos_deltas = self._aplicar_efectos(dict(EFECTOS_JEFE_DERROTADO))
        self.puntos += PUNTOS_JEFE_DERROTADO
        self.version += 1
        return True

    # ------------------------------------------------------------------
    # Resumen
    # ------------------------------------------------------------------

    def zonas_purificadas(self):
        return [zona for zona, c in self.resultados.items() if c.exito]

    def resumen(self):
        """Datos para el panel de estado (tecla I) y la pantalla final."""
        return {
            "salud": self.estado.salud(),
            "reputacion": self.reputacion,
            "nivel_reputacion": self.rep(0).nombre_nivel,
            "puntos": self.puntos,
            "pistas": len(self.pistas),
            "total_pistas": self.total_pistas(),
            "purificadas": self.zonas_purificadas(),
            "expuestos": len(self.red.expuestos),
            "corregidos": len(self.red.corregidos),
        }

    # ------------------------------------------------------------------
    # Sincronización con los invitados (el host es la autoridad)
    # ------------------------------------------------------------------

    def resumen_red(self):
        """Estado que el host manda a los invitados. Solo tipos JSON."""
        return {
            "ver": self.version,
            "rep": {str(i): self._rep_a_dict(r) for i, r in self.reputaciones.items()},
            "ind": self.estado.como_dict(),
            "evi": dict(self.evidencias_reveladas),
            "sue": {z: sorted(c) for z, c in self.evidencias_sueltas.items()},
            "pts": self.puntos,
            "exp": sorted(self.red.expuestos),
            "cor": sorted(self.red.corregidos),
            "res": {z: bool(c.exito) for z, c in self.resultados.items()},
            "org": None if self.origen_elegido is None else bool(self.origen_elegido.correcto),
            "jef": self.jefe_derrotado,
        }

    @staticmethod
    def _rep_a_dict(reputacion):
        ultimo = reputacion.historial[-1] if reputacion.historial else None
        return {
            "v": reputacion.valor,
            "k": reputacion.contador,
            "e": reputacion.estado_crisis,
            "t": reputacion.tope,
            "d": reputacion.redenciones,
            "u": None if ultimo is None else [ultimo.antes, ultimo.despues, ultimo.mensaje, ultimo.motivo],
        }

    def aplicar_resumen_red(self, datos):
        """Invitado: copia lo que dice el host, sin confiar en tipos ni
        rangos. Detecta cambios de reputación y pruebas para presentarlos."""
        if not isinstance(datos, dict):
            return
        reputaciones = datos.get("rep")
        if isinstance(reputaciones, dict):
            for clave, valores in reputaciones.items():
                if str(clave).isdigit() and isinstance(valores, dict):
                    self._copiar_rep(int(clave), valores)
        indicadores = datos.get("ind")
        if isinstance(indicadores, dict):
            self.estado = EstadoCiudad({k: v for k, v in indicadores.items() if isinstance(v, int)})
        evidencias = datos.get("evi")
        if isinstance(evidencias, dict):
            for zona, cantidad in evidencias.items():
                while isinstance(cantidad, int) and self.tiene_escenario(zona) \
                        and self.evidencias_reveladas.get(zona, 0) < cantidad:
                    if self.revelar_evidencia(zona) is None:
                        break
        sueltas = datos.get("sue")
        if isinstance(sueltas, dict):
            self.evidencias_sueltas = {z: {c: True for c in cuartos} for z, cuartos in sueltas.items()
                                       if isinstance(cuartos, list)}
        if isinstance(datos.get("pts"), int):
            self.puntos = datos["pts"]
        for nombre, atributo in (("exp", "expuestos"), ("cor", "corregidos")):
            if isinstance(datos.get(nombre), list):
                setattr(self.red, atributo, {n for n in datos[nombre] if n in self.red.grafo})
        if isinstance(datos.get("jef"), bool):
            self.jefe_derrotado = datos["jef"]
        self.version = datos.get("ver", self.version)

    def _copiar_rep(self, indice, valores):
        reputacion = self.rep(indice)
        valor, contador = valores.get("v"), valores.get("k")
        if isinstance(valor, int):
            reputacion.valor = valor
        if isinstance(valores.get("e"), str):
            # Con la decisión de crisis en camino al host, manda la copia local.
            if indice in self.esperando_host and valores["e"] == rep_mod.CRISIS_PENDIENTE:
                pass
            else:
                self.esperando_host.discard(indice)
                reputacion.estado_crisis = valores["e"]
        if isinstance(valores.get("t"), int):
            reputacion.tope = valores["t"]
        if isinstance(valores.get("d"), int):
            reputacion.redenciones = valores["d"]
        ultimo = valores.get("u")
        if isinstance(contador, int) and contador > reputacion.contador:
            reputacion.contador = contador
            if isinstance(ultimo, list) and len(ultimo) == 4:
                cambio = rep_mod.CambioReputacion(int(ultimo[0]), int(ultimo[1]), str(ultimo[2]), str(ultimo[3]))
                reputacion.historial.append(cambio)
                reputacion.pendientes.append(cambio)
                self.ultimo_cambio_reputacion = cambio
