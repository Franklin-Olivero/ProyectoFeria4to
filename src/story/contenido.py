"""Carga y validación del contenido narrativo (lógica pura, sin Pygame).

El contenido vive en content/campaign.json: prólogo, capítulos por
zona, escenarios de decisión (publicación, evidencias y opciones del
árbol), pistas de NOVA_404, grafo social, sospechosos y finales. Aquí
solo se lee y se valida: ids únicos, referencias que existen, resultados
y efectos con nombres conocidos. Un JSON roto lanza ContenidoInvalido
al cargar, con un mensaje que dice qué falta, en vez de fallar a mitad
de la partida.
"""

import json
import os

RUTA_CONTENIDO = os.path.join("content", "campaign.json")

INDICADORES = (
    "informacion_verificada",
    "confianza",
    "convivencia",
    "bienestar_digital",
    "participacion_responsable",
    "desinformacion",
    "conflictos",
)
INDICADORES_BUENOS = INDICADORES[:5]
INDICADORES_MALOS = INDICADORES[5:]

RESULTADO_PURIFICACION = "purificacion"
RESULTADO_DETONACION = "detonacion"
RESULTADOS = (RESULTADO_PURIFICACION, RESULTADO_DETONACION)

VEREDICTOS = ("cierto", "falso", "fuera_de_contexto", "sin_verificar")
ESTADOS_EVIDENCIA_OVERRIDE = ("sin_pruebas", "parcial")

CLAVES_RAIZ = ("prologo", "capitulos", "escenarios", "pistas", "red_social", "sospechosos", "finales", "candidatos")
CLAVES_POST = ("usuario", "hace", "texto", "etiqueta")
CLAVES_EVIDENCIA = ("id", "titulo", "fuente", "fragmento")
CLAVES_FINALES = ("renace", "dividida", "arquitecto")


class ContenidoInvalido(ValueError):
    """El JSON de la campaña no cumple el formato esperado."""


_cache = {}


def cargar(ruta=RUTA_CONTENIDO):
    """Diccionario del contenido ya validado (se lee del disco una sola
    vez por ruta)."""
    if ruta not in _cache:
        with open(ruta, encoding="utf-8") as archivo:
            datos = json.load(archivo)
        validar(datos)
        _cache[ruta] = datos
    return _cache[ruta]


def validar(datos):
    """Lanza ContenidoInvalido si falta algo o una referencia no existe."""
    for clave in CLAVES_RAIZ:
        if clave not in datos:
            raise ContenidoInvalido(f"Falta la clave raíz {clave!r}.")
    _validar_dialogo(datos["prologo"], "prologo")
    for zona, capitulo in datos["capitulos"].items():
        if "intro" not in capitulo or "titulo" not in capitulo:
            raise ContenidoInvalido(f"El capítulo de {zona!r} necesita 'titulo' e 'intro'.")
        _validar_dialogo(capitulo["intro"], f"capitulos[{zona}]")
    ids_evidencia = set()
    for zona, escenario in datos["escenarios"].items():
        _validar_escenario(zona, escenario, ids_evidencia)
    for id_pista in datos["pistas"]:
        if id_pista not in ids_evidencia:
            raise ContenidoInvalido(f"La pista {id_pista!r} no corresponde a ninguna evidencia.")
    _validar_red_social(datos["red_social"])
    ids_ciudadanos = {c["id"] for c in datos["red_social"]["ciudadanos"]}
    for zona, escenario in datos["escenarios"].items():
        origen = escenario.get("propagacion", {}).get("origen")
        if origen is not None and origen not in ids_ciudadanos:
            raise ContenidoInvalido(f"escenarios[{zona}].propagacion: el origen {origen!r} no es un ciudadano.")
    _validar_eventos(datos.get("eventos", []))
    _validar_sospechosos(datos["sospechosos"])
    for clave in CLAVES_FINALES:
        final = datos["finales"].get(clave)
        if not isinstance(final, dict) or "titulo" not in final or "texto" not in final:
            raise ContenidoInvalido(f"El final {clave!r} necesita 'titulo' y 'texto'.")
    _validar_candidatos(datos["candidatos"])
    _validar_cinematica(datos.get("cinematica_intro", []))
    if not isinstance(datos.get("objetivos_intro", []), list):
        raise ContenidoInvalido("objetivos_intro debe ser una lista de textos.")


def _validar_cinematica(tomas):
    """Cada toma necesita id único y duración numérica (0 = espera Enter)."""
    ids = set()
    for numero, toma in enumerate(tomas):
        if "id" not in toma:
            raise ContenidoInvalido(f"cinematica_intro[{numero}]: falta 'id'.")
        if toma["id"] in ids:
            raise ContenidoInvalido(f"cinematica_intro: id repetido {toma['id']!r}.")
        ids.add(toma["id"])
        if not isinstance(toma.get("duracion", 5.0), (int, float)):
            raise ContenidoInvalido(f"cinematica_intro[{toma['id']}]: 'duracion' debe ser un número.")


def _validar_dialogo(lineas, donde):
    if not isinstance(lineas, list) or not lineas:
        raise ContenidoInvalido(f"{donde}: el diálogo debe ser una lista con al menos una línea.")
    for numero, linea in enumerate(lineas):
        if "hablante" not in linea or "texto" not in linea:
            raise ContenidoInvalido(f"{donde}[{numero}]: cada línea necesita 'hablante' y 'texto'.")


def _validar_escenario(zona, escenario, ids_evidencia):
    donde = f"escenarios[{zona}]"
    for clave in ("id", "post", "evidencias", "opciones", "tiempo_agotado", "veredicto"):
        if clave not in escenario:
            raise ContenidoInvalido(f"{donde}: falta {clave!r}.")
    if escenario["veredicto"] not in VEREDICTOS:
        raise ContenidoInvalido(f"{donde}: veredicto {escenario['veredicto']!r} desconocido.")
    for clave in CLAVES_POST:
        if clave not in escenario["post"]:
            raise ContenidoInvalido(f"{donde}.post: falta {clave!r}.")
    if not escenario["evidencias"]:
        raise ContenidoInvalido(f"{donde}: necesita al menos una evidencia.")
    for evidencia in escenario["evidencias"]:
        for clave in CLAVES_EVIDENCIA:
            if clave not in evidencia:
                raise ContenidoInvalido(f"{donde}.evidencias: falta {clave!r}.")
        if evidencia["id"] in ids_evidencia:
            raise ContenidoInvalido(f"Evidencia repetida: {evidencia['id']!r}.")
        ids_evidencia.add(evidencia["id"])
    if not escenario["opciones"]:
        raise ContenidoInvalido(f"{donde}: necesita opciones.")
    etiquetas = set()
    for opcion in escenario["opciones"]:
        if opcion.get("etiqueta") in etiquetas:
            raise ContenidoInvalido(f"{donde}: opción repetida {opcion.get('etiqueta')!r}.")
        etiquetas.add(opcion.get("etiqueta"))
        _validar_opcion(opcion, f"{donde}.opciones")
    _validar_consecuencia(escenario["tiempo_agotado"], f"{donde}.tiempo_agotado")


def _validar_opcion(opcion, donde):
    if "etiqueta" not in opcion:
        raise ContenidoInvalido(f"{donde}: toda opción necesita 'etiqueta'.")
    if "hijos" in opcion:
        if not opcion["hijos"]:
            raise ContenidoInvalido(f"{donde}[{opcion['etiqueta']}]: 'hijos' no puede estar vacío.")
        for hijo in opcion["hijos"]:
            _validar_opcion(hijo, f"{donde}[{opcion['etiqueta']}]")
        return
    _validar_consecuencia(opcion, f"{donde}[{opcion['etiqueta']}]")
    for estado, alternativa in opcion.get("por_evidencia", {}).items():
        if estado not in ESTADOS_EVIDENCIA_OVERRIDE:
            raise ContenidoInvalido(f"{donde}[{opcion['etiqueta']}]: estado de evidencia {estado!r} desconocido.")
        _validar_consecuencia(alternativa, f"{donde}[{opcion['etiqueta']}].por_evidencia[{estado}]")


def _validar_consecuencia(datos, donde):
    if datos.get("resultado") not in RESULTADOS:
        raise ContenidoInvalido(f"{donde}: resultado {datos.get('resultado')!r} debe ser uno de {RESULTADOS}.")
    if "texto" not in datos:
        raise ContenidoInvalido(f"{donde}: falta 'texto'.")
    for indicador, delta in datos.get("efectos", {}).items():
        if indicador not in INDICADORES:
            raise ContenidoInvalido(f"{donde}: indicador {indicador!r} desconocido.")
        if not isinstance(delta, int):
            raise ContenidoInvalido(f"{donde}: el efecto sobre {indicador!r} debe ser entero.")


def _validar_red_social(red):
    ids = [c.get("id") for c in red.get("ciudadanos", [])]
    if len(ids) < 2 or len(set(ids)) != len(ids):
        raise ContenidoInvalido("red_social: los ciudadanos necesitan ids únicos (mínimo 2).")
    for a, b in red.get("conexiones", []):
        if a not in ids or b not in ids or a == b:
            raise ContenidoInvalido(f"red_social: conexión inválida {(a, b)!r}.")


def _validar_eventos(eventos):
    ids = set()
    for evento in eventos:
        if "id" not in evento or "titulo" not in evento:
            raise ContenidoInvalido("eventos: cada evento necesita 'id' y 'titulo'.")
        if evento["id"] in ids:
            raise ContenidoInvalido(f"eventos: id repetido {evento['id']!r}.")
        ids.add(evento["id"])
        if evento.get("propaga") not in (None, "rumor", "correccion"):
            raise ContenidoInvalido(f"eventos[{evento['id']}]: 'propaga' debe ser 'rumor' o 'correccion'.")
        for indicador in evento.get("efectos", {}):
            if indicador not in INDICADORES:
                raise ContenidoInvalido(f"eventos[{evento['id']}]: indicador {indicador!r} desconocido.")


def _validar_sospechosos(sospechosos):
    cuentas = sospechosos.get("cuentas", [])
    ids = [c.get("id") for c in cuentas]
    if len(set(ids)) != len(ids) or not ids:
        raise ContenidoInvalido("sospechosos: las cuentas necesitan ids únicos.")
    if sospechosos.get("culpable") not in ids:
        raise ContenidoInvalido("sospechosos: 'culpable' debe ser el id de una cuenta.")
    for cuenta in cuentas:
        for clave in ("nombre", "descripcion", "pistas", "veredicto", "texto"):
            if clave not in cuenta:
                raise ContenidoInvalido(f"sospechosos[{cuenta.get('id')}]: falta {clave!r}.")


def _validar_candidatos(candidatos):
    if len(candidatos) != 4:
        raise ContenidoInvalido("candidatos: deben ser exactamente 4.")
    for candidato in candidatos:
        for clave in ("id", "nombre", "lema", "base", "afin"):
            if clave not in candidato:
                raise ContenidoInvalido(f"candidatos[{candidato.get('id')}]: falta {clave!r}.")
        if candidato["afin"] not in INDICADORES:
            raise ContenidoInvalido(f"candidatos[{candidato['id']}]: indicador afín desconocido.")
