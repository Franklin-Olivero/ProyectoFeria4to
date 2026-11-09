"""Elecciones simuladas y finales de la campaña (lógica pura, sin Pygame).

Simulación FICTICIA con fines educativos: no modela elecciones reales.
Cada candidato (content/campaign.json) tiene una base de apoyo y un
indicador afín; su apoyo crece con ese indicador y con la reputación
del jugador, y el total se normaliza a 100 %. El cálculo es
determinista: los mismos indicadores dan el mismo resultado. Ningún
candidato tiene la victoria escrita.

Finales (umbrales en balance.py):
    - "confianza_perdida" (derrota): nadie del equipo tiene ya voz porque
      todos rechazaron o fallaron la redención;
    - "arquitecto" (secreto): las 3 pistas, el origen de la señal rastreado
      en el capítulo 3 y el jefe derrotado, sin reputación cuestionada;
    - "renace": información verificada y confianza altas, desinformación
      baja y sin reputación cuestionada;
    - "dividida": en cualquier otro caso.
"""

from src.core.balance import (
    FINAL_RENACE_CONFIANZA_MIN,
    FINAL_RENACE_DESINFORMACION_MAX,
    FINAL_RENACE_VERIFICADA_MIN,
    PESO_INDICADOR_AFIN_ELECCION,
    PESO_REPUTACION_ELECCION,
    PISTAS_PARA_FINAL_SECRETO,
    REPUTACION_MIN_FINAL_POSITIVO,
)

FINAL_RENACE = "renace"
FINAL_DIVIDIDA = "dividida"
FINAL_ARQUITECTO = "arquitecto"
FINAL_CONFIANZA_PERDIDA = "confianza_perdida"


def calcular_apoyos(candidatos, estado, reputacion):
    """[(candidato, porcentaje)] de mayor a menor apoyo; los porcentajes
    (redondeados a 1 decimal) suman ~100. Apoyo bruto = base +
    PESO_INDICADOR_AFIN * indicador afín + PESO_REPUTACION * reputación
    (solo para candidatos cuyo indicador afín es "bueno": la reputación
    del jugador no ayuda a quien se alimenta de la desinformación)."""
    brutos = []
    for candidato in candidatos:
        afin = candidato["afin"]
        bruto = candidato["base"] + PESO_INDICADOR_AFIN_ELECCION * estado.valor(afin)
        if afin not in ("desinformacion", "conflictos"):
            bruto += PESO_REPUTACION_ELECCION * reputacion
        brutos.append((candidato, max(0.0, bruto)))
    total = sum(b for _, b in brutos) or 1.0
    apoyos = [(c, round(100.0 * b / total, 1)) for c, b in brutos]
    return sorted(apoyos, key=lambda par: -par[1])


def determinar_final(campania):
    """Clave del final según el estado de la campaña (ver módulo)."""
    estado = campania.estado
    if campania.todos_sin_voz():
        return FINAL_CONFIANZA_PERDIDA
    respetado = campania.reputacion_colectiva() >= REPUTACION_MIN_FINAL_POSITIVO
    if (respetado and len(campania.pistas) >= PISTAS_PARA_FINAL_SECRETO and campania.origen_rastreado
            and campania.jefe_derrotado):
        return FINAL_ARQUITECTO
    if (respetado and estado.valor("informacion_verificada") >= FINAL_RENACE_VERIFICADA_MIN
            and estado.valor("confianza") >= FINAL_RENACE_CONFIANZA_MIN
            and estado.valor("desinformacion") <= FINAL_RENACE_DESINFORMACION_MAX):
        return FINAL_RENACE
    return FINAL_DIVIDIDA


def resumen_final(campania):
    """Todo lo que muestra la pantalla de elecciones."""
    clave = determinar_final(campania)
    final = campania.contenido["finales"][clave]
    return {
        "clave": clave,
        "titulo": final["titulo"],
        "texto": final["texto"],
        "epilogo": final.get("epilogo_redimido", "") if campania.hubo_redencion() else "",
        "apoyos": calcular_apoyos(campania.contenido["candidatos"], campania.estado, campania.reputacion_colectiva()),
        "resumen": campania.resumen(),
        "pistas_completas": len(campania.pistas) >= PISTAS_PARA_FINAL_SECRETO,
        "nota": campania.contenido.get("nota", ""),
        "campania": campania,
    }
