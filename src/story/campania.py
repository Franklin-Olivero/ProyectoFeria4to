"""Estado de la campaña "Código Nova" dentro de una partida (sin Pygame).

Vive en Partida.campania y sobrevive entre mazmorras:
    - qué diálogos ya se vieron (prólogo una vez, intro de cada zona una vez);
    - qué evidencias se revelaron en cada zona (una por cuarto limpio) y
      las pistas de NOVA_404 que salieron de ellas (lista sin repetidos);
    - el escenario activo (árbol armado para el estado de evidencia del
      momento) y la consecuencia de cada zona;
    - los indicadores de Ciudad Nova (EstadoCiudad), la reputación y los
      puntos del jugador;
    - la red social (src/story/red_social.py): la publicación de cada
      zona con "propagacion" viaja por BFS al resolverse la terminal y su
      alcance real suma efectos; una Purificación publica además la
      corrección, que frena los rebotes futuros sin borrar lo ya visto;
    - los eventos aleatorios al volver a la ciudad (src/story/eventos.py)
      con un random.Random(semilla) propio, reproducible en los tests;
    - el matiz narrativo del rol (balance.py) y, más adelante, la
      investigación del infiltrado y la caída del jefe.

Reglas contra dobles recompensas: los efectos sobre los indicadores se
aplican cada vez que se resuelve una terminal (la ciudad reacciona a
cada publicación), pero los puntos y la reputación positiva de una
zona se cobran una sola vez (la primera Purificación Exitosa); las
penalizaciones sí se repiten. Partida.cerrar_mazmorra es quien llama a
aplicar_consecuencia, y solo cuando la mazmorra acepta completarse.
Todo cambio de indicadores pasa por `_aplicar_efectos`.
"""

import random

from src.core.balance import (
    BIENESTAR_POR_ALCANZADO,
    CONFIANZA_EXTRA_CIUDADANO,
    DESINFORMACION_POR_ALCANZADO,
    EFECTOS_JEFE_DERROTADO,
    EVENTOS_RECIENTES_CINTILLO,
    EVIDENCIA_INICIAL_PERIODISTA,
    INDICADOR_MAXIMO,
    INDICADOR_MINIMO,
    MULTIPLICADOR_PENALIZACION_CANDIDATO,
    PUNTOS_JEFE_DERROTADO,
    REBOTE_EXTRA_INFLUENCER,
    REPUTACION_INICIAL,
    VERIFICADA_POR_CORREGIDO,
    ZONA_EMPRESA_MEDIOS,
)
from src.core.assets import FONDO_POR_ZONA, FONDO_PROLOGO
from src.story import contenido as contenido_mod
from src.story.cinematica import guion_entrada_jefe, guion_intro, tarjeta_capitulo
from src.story.dialogo import DialogoSecuencia
from src.story.escenarios import EscenarioDecision, estado_evidencia
from src.story.estado_ciudad import EstadoCiudad
from src.story.eventos import sortear_evento
from src.story.investigacion import Investigacion
from src.story.red_social import CORRECCION, RUMOR, RedSocial

ZONA_INVESTIGACION = ZONA_EMPRESA_MEDIOS  # capítulo 3: el infiltrado

ROL_INFLUENCER = "influencer"
ROL_CIUDADANO = "ciudadano"
ROL_PERIODISTA = "periodista"
ROL_CANDIDATO = "candidato"


class Campania:
    def __init__(self, contenido=None, semilla=None):
        self.contenido = contenido if contenido is not None else contenido_mod.cargar()
        self.semilla = semilla
        self.rol = None
        self.reiniciar()

    def reiniciar(self):
        self.rng = random.Random(self.semilla)
        self.prologo_visto = False
        self.intros_vistas = set()
        self.evidencias_reveladas = {}  # zona -> cantidad revelada
        self.pistas = []  # ids de evidencia con pista, en orden de hallazgo
        self.escenario_activo = None
        self.zona_activa = None
        self.resultados = {}  # zona -> última Consecuencia
        self.recompensadas = set()  # zonas cuya recompensa positiva ya se cobró
        self.ultima_consecuencia = None
        self.ultimos_deltas = {}
        self.estado = EstadoCiudad()
        self.reputacion = REPUTACION_INICIAL
        self.puntos = 0
        self.red = RedSocial(self.contenido["red_social"], self.rng)
        self.ultima_propagacion = None  # (rumor, corrección o None) de la última zona
        self.eventos_ocurridos = []  # EventoOcurrido en orden
        self.infiltrado_elegido = None  # ResultadoInvestigacion del capítulo 3
        self.jefe_derrotado = False

    def establecer_rol(self, rol):
        """Clave del rol del J1 ("periodista"...), para los matices narrativos."""
        self.rol = rol

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

    def presentacion_zona(self, zona, rol=None, nombre_rol="Tú"):
        """(cinemática, diálogo) al entrar a `zona` la primera vez: la
        tarjeta del capítulo y luego su diálogo; en la Alcaldía, la
        cinemática de entrada al jefe sin diálogo. (None, None) si ya se vio."""
        capitulo = self.contenido["capitulos"].get(zona)
        if capitulo is None or zona in self.intros_vistas:
            return None, None
        numero = capitulo.get("numero", 0)
        if numero >= 4:
            self.intros_vistas.add(zona)
            return guion_entrada_jefe(len(self.pistas), self.total_pistas()), None
        tarjeta = tarjeta_capitulo(numero, capitulo["titulo"], zona)
        return tarjeta, self.dialogo_capitulo(zona, rol, nombre_rol)

    def dialogo_capitulo(self, zona, rol=None, nombre_rol="Tú"):
        """La intro del capítulo de `zona` la primera vez que se entra;
        None si ya se vio o la zona no tiene capítulo."""
        capitulo = self.contenido["capitulos"].get(zona)
        if capitulo is None or zona in self.intros_vistas:
            return None
        self.intros_vistas.add(zona)
        numero = capitulo.get("numero", 0)
        titulo = f"Capítulo {numero}: {capitulo['titulo']}" if numero < 4 else f"Final: {capitulo['titulo']}"
        return DialogoSecuencia(capitulo["intro"], rol, nombre_rol, len(self.pistas), titulo=titulo,
                                fondo=FONDO_POR_ZONA.get(zona))

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
        """Revela la siguiente evidencia de `zona` (una por cuarto
        limpio). Retorna el diccionario de la evidencia, o None si no
        quedan. Si trae pista, la suma una sola vez."""
        evidencias = self.evidencias_de(zona)
        indice = self.evidencias_reveladas.get(zona, 0)
        if indice >= len(evidencias):
            return None
        evidencia = evidencias[indice]
        self.evidencias_reveladas[zona] = indice + 1
        if evidencia.get("pista") and evidencia["id"] not in self.pistas:
            self.pistas.append(evidencia["id"])
        return evidencia

    def al_entrar_zona(self, zona):
        """Matiz del Periodista: identifica una fuente extra al entrar
        (la primera evidencia, si la zona aún no tiene ninguna). Retorna
        la evidencia revelada o None."""
        if self.rol != ROL_PERIODISTA or self.evidencias_reveladas.get(zona, 0) >= EVIDENCIA_INICIAL_PERIODISTA:
            return None
        return self.revelar_evidencia(zona)

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

    def preparar_escenario(self, zona):
        """Arma el árbol de `zona` con el estado de evidencia de AHORA
        (se llama cuando el cuarto final abre la terminal) y lo deja
        como escenario activo. None si la zona no tiene escenario."""
        if not self.tiene_escenario(zona):
            self.escenario_activo = None
            self.zona_activa = None
            return None
        self.escenario_activo = EscenarioDecision(self.contenido["escenarios"][zona], self.estado_evidencia(zona))
        self.zona_activa = zona
        return self.escenario_activo

    def consecuencia_de_terminal(self, zona, terminal):
        """Consecuencia del resultado de `terminal` en `zona`, o None si
        no hay escenario activo para esa zona."""
        if self.escenario_activo is None or self.zona_activa != zona:
            return None
        return self.escenario_activo.consecuencia_para(terminal)

    def aplicar_consecuencia(self, zona, consecuencia):
        """Aplica efectos (más los de la propagación por la red social y
        el matiz del rol), reputación y puntos. Retorna los deltas reales
        sobre los indicadores. (La llama Partida.cerrar_mazmorra.)"""
        efectos = dict(consecuencia.efectos)
        if consecuencia.exito and self.rol == ROL_CIUDADANO:
            efectos["confianza"] = efectos.get("confianza", 0) + CONFIANZA_EXTRA_CIUDADANO
        self.ultima_propagacion = self._propagar_publicacion(zona, consecuencia, efectos)
        self.ultimos_deltas = self._aplicar_efectos(efectos)

        premiar = not (consecuencia.exito and zona in self.recompensadas)
        reputacion = consecuencia.reputacion
        if reputacion < 0 and self.rol == ROL_CANDIDATO:
            reputacion *= MULTIPLICADOR_PENALIZACION_CANDIDATO
        if reputacion < 0 or premiar:
            self.reputacion = max(INDICADOR_MINIMO, min(INDICADOR_MAXIMO, self.reputacion + reputacion))
        if premiar:
            self.puntos += consecuencia.puntos
        if consecuencia.exito:
            self.recompensadas.add(zona)
        self.resultados[zona] = consecuencia
        self.ultima_consecuencia = consecuencia
        self.escenario_activo = None
        self.zona_activa = None
        return self.ultimos_deltas

    def _aplicar_efectos(self, efectos):
        """Único punto por el que cambian los indicadores."""
        return self.estado.aplicar(efectos)

    def _propagar_publicacion(self, zona, consecuencia, efectos):
        """Si el escenario de `zona` tiene "propagacion", el rumor viaja
        por BFS desde su origen (la publicación ya era viral: la memoria
        queda); con Purificación Exitosa se publica además la corrección,
        que alcanza a los contactos cercanos y los marca como corregidos.
        Suma a `efectos` según el alcance real y retorna la Propagacion
        principal (la del rumor), o None si la zona no propaga."""
        configuracion = self.contenido["escenarios"].get(zona, {}).get("propagacion")
        if configuracion is None:
            return None
        origen = configuracion["origen"]
        extra = REBOTE_EXTRA_INFLUENCER if (self.rol == ROL_INFLUENCER and not consecuencia.exito) else 0.0
        rumor = self.red.propagar(origen, probabilidad_extra=extra, tipo=RUMOR)
        if consecuencia.exito:
            correccion = self.red.corregir(origen)
            sin_corregir = [n for n in rumor.alcanzados if n not in correccion.alcanzados]
            efectos["desinformacion"] = efectos.get("desinformacion", 0) + int(
                len(sin_corregir) * DESINFORMACION_POR_ALCANZADO)
            efectos["informacion_verificada"] = efectos.get("informacion_verificada", 0) + int(
                correccion.total * VERIFICADA_POR_CORREGIDO)
        else:
            efectos["desinformacion"] = efectos.get("desinformacion", 0) + int(
                rumor.total * DESINFORMACION_POR_ALCANZADO)
            efectos["bienestar_digital"] = efectos.get("bienestar_digital", 0) + int(
                rumor.total * BIENESTAR_POR_ALCANZADO)
        return rumor

    def correccion_reciente(self):
        """La Propagacion de la última corrección publicada, si la hubo."""
        return self.red.ultima(CORRECCION)

    # ------------------------------------------------------------------
    # Eventos aleatorios
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
        """Titulares de los últimos eventos, del más reciente al más viejo."""
        recientes = self.eventos_ocurridos[-EVENTOS_RECIENTES_CINTILLO:]
        return [f"Civitas: {evento.titular}" for evento in reversed(recientes)]

    # ------------------------------------------------------------------
    # Capítulo 3: infiltrado, y final: jefe
    # ------------------------------------------------------------------

    def investigacion_pendiente(self, zona):
        """True si al salir de `zona` toca la investigación (zona del
        capítulo 3 recién purificada o detonada, aún sin acusar)."""
        return zona == ZONA_INVESTIGACION and self.infiltrado_elegido is None and zona in self.resultados

    def nueva_investigacion(self):
        return Investigacion(self.contenido["sospechosos"])

    def registrar_investigacion(self, resultado):
        """Aplica la acusación una sola vez (la primera cuenta)."""
        if self.infiltrado_elegido is not None:
            return False
        self.infiltrado_elegido = resultado
        self.ultimos_deltas = self._aplicar_efectos(resultado.efectos)
        self.reputacion = max(INDICADOR_MINIMO, min(INDICADOR_MAXIMO, self.reputacion + resultado.reputacion))
        self.puntos += resultado.puntos
        return True

    @property
    def infiltrado_correcto(self):
        return self.infiltrado_elegido is not None and self.infiltrado_elegido.correcto

    def registrar_jefe_derrotado(self):
        """Victoria en la Alcaldía: efectos y puntos una sola vez."""
        if self.jefe_derrotado:
            return False
        self.jefe_derrotado = True
        self.ultimos_deltas = self._aplicar_efectos(dict(EFECTOS_JEFE_DERROTADO))
        self.puntos += PUNTOS_JEFE_DERROTADO
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
            "puntos": self.puntos,
            "pistas": len(self.pistas),
            "total_pistas": self.total_pistas(),
            "purificadas": self.zonas_purificadas(),
            "expuestos": len(self.red.expuestos),
            "corregidos": len(self.red.corregidos),
        }
