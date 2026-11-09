"""El jugador controla el ritmo de lectura: las escenas esperan, el modo
automático respeta el tiempo de lectura, nada se recorta y todo se puede
saltar. Las comprobaciones de layout usan la fuente real (sin ventana)."""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame  # noqa: E402
import pytest  # noqa: E402

from src.core import assets  # noqa: E402
from src.core.balance import ZONA_COLEGIO, ZONA_HOSPITAL  # noqa: E402
from src.core.preferencias import Preferencias, desde_dict  # noqa: E402
from src.dungeon.partida import Partida  # noqa: E402
from src.story import cinematica as cine  # noqa: E402
from src.story.dialogo import DialogoSecuencia, paginar_texto  # noqa: E402
from src.ui import dibujo  # noqa: E402
from src.ui.ajustes import ModalAjustes, PESTANA_ACCESIBILIDAD  # noqa: E402

TEXTO = "Una escena con diálogo que se debe poder leer sin ninguna prisa."


def _toma(**datos):
    return cine.Toma("a", 5.0, texto=TEXTO, **datos)


def test_formula_de_tiempo_de_lectura():
    assert cine.tiempo_lectura("") == 0.0
    assert cine.tiempo_lectura("Breve.") == 7.0  # nunca menos de 7 s con diálogo
    largo = " ".join(["palabra"] * 50)  # 50 palabras a 150 ppm = 20 s + 2 s
    assert cine.tiempo_lectura(largo) == pytest.approx(22.0)


def test_modo_manual_nunca_avanza_solo():
    c = cine.Cinematica([_toma(), cine.Toma("b", 2.0, texto=TEXTO)])
    assert c.modo == cine.MODO_MANUAL
    for _ in range(60 * 300):  # cinco minutos
        c.actualizar(1 / 60)
    assert c.actual.id == "a" and not c.terminada and c.esperando_enter


def test_primer_enter_revela_y_el_segundo_avanza():
    c = cine.Cinematica([_toma(), cine.Toma("b", 2.0, texto=TEXTO)])
    assert c.caracteres_visibles == 0 and not c.texto_completo
    c.avanzar()
    assert c.actual.id == "a" and c.texto_completo and c.caracteres_visibles == len(TEXTO)
    c.avanzar()
    assert c.actual.id == "b" and not c.texto_completo


def test_el_texto_aparece_de_forma_progresiva():
    c = cine.Cinematica([_toma()])
    c.actualizar(cine.RETARDO_TEXTO + 1.0)
    assert 0 < c.caracteres_visibles < len(TEXTO)
    visibles = c.caracteres_visibles
    c.actualizar(0.5)
    assert c.caracteres_visibles > visibles


def test_modo_automatico_respeta_tiempo_de_lectura_y_escritura():
    c = cine.Cinematica([_toma(), cine.Toma("b", 2.0)], modo=cine.MODO_AUTOMATICO, velocidad=2.0)
    # Con 2 caracteres por segundo el texto tarda más que el mínimo: no se va antes.
    for _ in range(60 * 12):
        c.actualizar(1 / 60)
    assert c.actual.id == "a" and not c.texto_completo
    while c.actual.id == "a":
        c.actualizar(1 / 60)
    assert c.actual.id == "b" and c.tiempo < 0.1
    rapida = cine.Cinematica([_toma(), cine.Toma("b", 2.0)], modo=cine.MODO_AUTOMATICO, velocidad=500.0)
    rapida.actualizar(6.9)
    assert rapida.actual.id == "a"  # mínimo de 7 s
    rapida.actualizar(0.2)
    assert rapida.actual.id == "b"


def test_toma_sin_texto_usa_su_duracion_en_cualquier_modo():
    for modo in (cine.MODO_MANUAL, cine.MODO_AUTOMATICO):
        c = cine.Cinematica([cine.Toma("a", 1.0), cine.Toma("b", 1.0)], modo=modo)
        c.actualizar(1.1)
        assert c.actual.id == "b"


def test_escenas_se_pueden_saltar_y_los_objetivos_esperan():
    c = cine.Cinematica([_toma(), _toma(), cine.Toma("fin", cine.ESPERA_ENTER)])
    c.saltar()
    assert c.actual.id == "fin"
    c.saltar()
    assert c.terminada
    forzada = cine.Cinematica([_toma()], saltable=False)
    forzada.saltar()
    assert not forzada.terminada


def test_tarjeta_de_capitulo_es_legible_con_los_datos_pedidos():
    tarjeta, _ = Partida().campania.presentacion_zona(ZONA_COLEGIO, "ciudadano", "Ciudadano")
    toma = tarjeta.actual
    assert toma.superior == "CAPÍTULO 1" and toma.titulo == "EL RUMOR"
    assert "Colegio" in toma.subtitulo and len(toma.lineas) == 2  # ubicación, contexto y objetivo
    assert toma.duracion >= 7
    tarjeta.avanzar()
    assert tarjeta.terminada  # Enter la pasa de inmediato


def test_dialogo_con_velocidad_tambien_revela_antes_de_avanzar():
    d = DialogoSecuencia([{"hablante": "A", "texto": TEXTO}, {"hablante": "B", "texto": TEXTO}])
    assert d.texto_completo  # sin velocidad: sin efecto de escritura
    d.configurar_lectura(30.0)
    assert not d.texto_completo
    d.actualizar(0.5)
    assert 0 < d.caracteres_visibles < len(TEXTO)
    d.avanzar()
    assert d.indice == 0 and d.texto_completo
    d.avanzar()
    assert d.indice == 1
    d.saltar()
    assert d.terminado


def test_texto_largo_se_pagina_sin_perder_palabras():
    texto = ("Primera oración bastante larga para llenar buena parte de la página. " * 8).strip()
    paginas = paginar_texto(texto, 120)
    assert len(paginas) > 1 and all(len(p) <= 120 for p in paginas)
    assert " ".join(paginas).split() == texto.split()
    assert paginar_texto("corto") == ["corto"]


def test_cinematica_larga_se_pagina_sin_recortar():
    texto = "Una oración de relleno que ocupa espacio en la pantalla. " * 12
    c = cine.Cinematica([cine.Toma("largo", 5.0, texto=texto.strip())])
    assert len(c.tomas) > 1
    assert " ".join(t.texto for t in c.tomas).split() == texto.split()
    assert all(len(t.texto) <= cine.MAX_CARACTERES_SUBTITULO for t in c.tomas)


# --------------------------------------------------------------- layout real


def _lineas_que_ocupa(texto, tamanio, ancho):
    return len(dibujo.ajustar_texto(texto, tamanio, ancho))


def test_todo_el_guion_cabe_en_la_caja_de_subtitulos_sin_puntos_suspensivos():
    pygame.init()
    partida = Partida()
    contenido = partida.campania.contenido
    caja = pygame.Rect(assets.RECT_SUBTITULO_CINEMATICA)
    ancho = caja.width - 40
    from src.ui.fuentes import fuente
    alto_linea = fuente(assets.TAMANIO_FUENTE_SUBTITULO).get_height() + 4
    caben = (caja.height - 44) // alto_linea
    for rol in ("ciudadano", "influencer", "periodista", "candidato"):
        guiones = [cine.guion_intro(contenido, rol, rol),
                   cine.guion_crisis(contenido["redencion"], rol, rol),
                   cine.guion_redencion(contenido["redencion"], rol, rol),
                   cine.guion_rechazo(contenido["redencion"], contenido["finales"]["confianza_perdida"])]
        for guion in guiones:
            for toma in guion.tomas:
                if toma.texto:
                    assert _lineas_que_ocupa(toma.texto, assets.TAMANIO_FUENTE_SUBTITULO, ancho) <= caben, toma.id


def test_todos_los_dialogos_caben_en_su_panel_sin_recortar():
    pygame.init()
    from src.ui.fuentes import fuente
    panel = pygame.Rect(assets.RECT_PANEL_DIALOGO)
    alto_caja = panel.height - 50 - 44
    # Con retrato: el peor caso de ancho.
    ancho = panel.width - 20 - assets.ALTO_RETRATO_DIALOGO - 24 - 24
    alto_linea = fuente(assets.TAMANIO_FUENTE_MEDIA).get_height() + 6
    caben = (alto_caja + 6) // alto_linea
    partida = Partida()
    contenido = partida.campania.contenido
    for rol in ("ciudadano", "influencer", "periodista", "candidato"):
        for zona, capitulo in contenido["capitulos"].items():
            for reputacion in (-40, 0, 40):
                d = DialogoSecuencia(capitulo["intro"], rol, rol, 3, reputacion=reputacion)
                for linea in d.lineas:
                    assert _lineas_que_ocupa(linea.texto, assets.TAMANIO_FUENTE_MEDIA, ancho) <= caben, linea.texto


# --------------------------------------------------------------- ajustes


def test_preferencias_de_avance_validadas_y_con_manual_por_defecto():
    p = Preferencias()
    assert p.avance_cinematicas == "manual" and p.velocidad_texto == "normal"
    assert desde_dict({"avance_cinematicas": "automatico"}).avance_cinematicas == "automatico"
    assert desde_dict({"avance_cinematicas": "rapidisimo"}).avance_cinematicas == "manual"
    assert desde_dict({"velocidad_texto": 3}).velocidad_texto == "normal"


def test_opciones_de_lectura_en_ajustes():
    p = Preferencias()
    modal = ModalAjustes(p)
    modal.elegir_pestana(PESTANA_ACCESIBILIDAD)
    assert {"avance_cinematicas", "velocidad_texto"} <= set(modal.controles())
    modal.enfocar("avance_cinematicas")
    from src.ui.navegacion import DERECHA
    modal.accion(DERECHA)
    assert p.avance_cinematicas == "automatico"
    modal.enfocar("velocidad_texto")
    modal.accion(DERECHA)
    assert p.velocidad_texto != "normal"


def test_presentacion_con_zona_final_y_carta_de_hospital():
    partida = Partida()
    tarjeta, dialogo = partida.campania.presentacion_zona(ZONA_HOSPITAL, "ciudadano", "Ciudadano")
    assert tarjeta.actual.titulo == "CONTAGIO DIGITAL" and dialogo.lineas
    jefe, nada = partida.campania.presentacion_zona("Alcaldía")
    assert nada is None and jefe.tomas[-1].lineas


# --------------------------------------------------------------- fallbacks


def test_sin_video_ni_ilustracion_la_cinematica_igual_se_dibuja():
    from src.ui import cinematica_render, sprites, video_cuadros
    pygame.init()
    pantalla = pygame.Surface((1280, 720))
    assert video_cuadros.cuadro("no_existe", 1.0, (1280, 720)) is None
    assert not video_cuadros.disponible("no_existe")
    c = cine.Cinematica([cine.Toma("a", 5.0, fondo="tampoco_existe", video="no_existe", texto=TEXTO, hablante="X")])
    for tiempo in (0.0, 1.0, 40.0):
        c.tiempo = c.tiempo_texto = tiempo
        cinematica_render.dibujar_cinematica(pantalla, c)
    # Un retrato de emoción que falta cae al retrato base del rol.
    assert sprites.retrato_rol("no_hay_rol", 100) is None


def test_video_va_y_vuelve_sin_congelarse():
    from src.ui.video_cuadros import _Clip
    pygame.init()
    clip = _Clip.__new__(_Clip)
    clip.nombres = [f"{i}.jpg" for i in range(5)]
    clip.fps = 2.0
    import threading
    clip._candado = threading.Lock()
    clip._evento = threading.Event()
    clip.listos = {i: i for i in range(5)}
    assert [clip.en(t / 2) for t in range(10)] == [0, 1, 2, 3, 4, 3, 2, 1, 0, 1]


def test_dialogos_muestran_retrato_segun_reputacion():
    lineas = [{"hablante": "JUGADOR", "retrato": "jugador", "texto": "Hola."}]
    assert DialogoSecuencia(lineas, "periodista", "P", 0, reputacion=0).lineas[0].retrato == "periodista"
    assert DialogoSecuencia(lineas, "periodista", "P", 0, reputacion=-30).lineas[0].retrato == "periodista_preocupado"
    assert DialogoSecuencia(lineas, "periodista", "P", 0, reputacion=30).lineas[0].retrato == "periodista_decidido"
