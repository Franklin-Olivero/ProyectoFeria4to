"""Prólogo «La ciudad que perdió»: película con banda sonora y rótulos (sin ventana)."""

import json
import os
import sys

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, RAIZ)

from src.core import assets  # noqa: E402
from src.dungeon.partida import Partida  # noqa: E402
from src.story import cinematica as cine  # noqa: E402
from src.story.contenido import ContenidoInvalido, _validar_cinematica  # noqa: E402


def _prologo():
    return Partida().campania.cinematica_intro("ciudadano", "Ciudadano")


def test_enter_no_corta_la_pelicula_pero_esc_salta_a_la_mision():
    c = _prologo()
    c.avanzar()  # el Enter que venía de elegir rol
    assert c.actual.id == "prologo_umbral"
    c.actualizar(10.0)
    c.avanzar()
    assert c.actual.id == "prologo_umbral" and abs(c.tiempo - 10.0) < 1e-9
    c.saltar()
    assert c.actual.id == "objetivos" and not c.terminada


def test_la_pelicula_avanza_sola_al_terminar():
    c = _prologo()
    c.actualizar(c.actual.duracion + 0.01)
    assert c.actual.id == "objetivos"


def test_la_pista_se_pide_una_vez_y_el_reloj_arranca_con_ella():
    c = _prologo()
    c.actualizar(0.4)  # cargar la pista tardó un frame
    assert c.tomar_pista() == assets.PISTA_PROLOGO
    assert c.tomar_pista() is None
    c.reiniciar_reloj()
    assert c.tiempo == 0.0
    c.saltar()
    assert c.tomar_pista() is None  # los objetivos vuelven a la música normal


def test_rotulos_del_guion_estan_en_orden_y_dentro_de_la_pelicula():
    toma = _prologo().actual
    estilos = [r.estilo for r in toma.rotulos]
    assert cine.ROTULO_ALERTA in estilos and cine.ROTULO_TITULO in estilos and cine.ROTULO_LEMA in estilos
    textos = " ".join(r.texto for r in toma.rotulos)
    # Teo tuvo oportunidades y las rechazó; el colapso se acumula; se arrepiente.
    for frase in ("¿Ya comprobaste si eso es verdad?", "No tengo tiempo para eso", "INVESTIGAR EL ORIGEN DEL RUMOR",
                  "Colegio · Hospital · Empresa de Medios", "Seguro alguien más se encarga", "MISIÓN DESCARTADA",
                  "DÍA 4", "COLAPSO DE UMBRAL", "¡Podías haberlo detenido!", "¡Tuviste las pruebas!",
                  "MISIONES SIN COMPLETAR", "COLAPSO TOTAL", "Pude haber hecho algo", "Y no lo hice",
                  "Hubo pruebas", "Ellos tuvieron su oportunidad", "Esta es la tuya",
                  "ERES LA ÚLTIMA ESPERANZA DE CIUDAD NOVA", "MAKE IT COUNT", "CÓDIGO NOVA",
                  "¿Vas a cometer los mismos errores o vas a salvar Ciudad Nova?"):
        assert frase in textos, frase
    colapso = next(r for r in toma.rotulos if r.estilo == cine.ROTULO_COLAPSO)
    assert colapso.valor_en(colapso.inicio) < 30 and colapso.valor_en(colapso.fin) > 90
    assert all(0 <= r.inicio < r.fin <= toma.duracion for r in toma.rotulos)
    assert [r.inicio for r in toma.rotulos] == sorted(r.inicio for r in toma.rotulos)
    # Subtítulos que no se pisan entre sí (cada voz tiene su turno).
    subs = [r for r in toma.rotulos if r.estilo == cine.ROTULO_SUBTITULO]
    assert all(a.fin <= b.inicio + 0.15 for a, b in zip(subs, subs[1:]))
    assert toma.rotulos_en(1.0)[0].hablante == "LÍA"
    titulo = next(r for r in toma.rotulos if r.estilo == cine.ROTULO_TITULO)
    assert titulo.fraccion(titulo.inicio) == 0.0 and titulo.fraccion(titulo.inicio + 1.0) == 1.0


def test_video_y_audio_existen_y_duran_lo_mismo_que_la_toma():
    from src.ui import video_cuadros

    toma = _prologo().actual
    carpeta = os.path.join(RAIZ, assets.RUTA_VIDEOS_HISTORIA, toma.video)
    with open(os.path.join(carpeta, "clip.json"), encoding="utf-8") as archivo:
        assert json.load(archivo)["lineal"] is True
    assert abs(video_cuadros.duracion(toma.video) - toma.duracion) < 0.25
    assert os.path.isfile(os.path.join(RAIZ, assets.MUSICA[toma.pista]))
    assert os.path.isfile(os.path.join(RAIZ, "assets", "story", f"{toma.fondo}.png"))  # respaldo sin video


def test_clip_lineal_no_va_y_vuelve():
    from src.ui.video_cuadros import _Clip

    clip = _Clip.__new__(_Clip)
    clip.nombres = [f"{i}.jpg" for i in range(5)]
    clip.fps = 2.0
    clip.lineal = True
    assert [clip.indice_en(t / 2) for t in range(8)] == [0, 1, 2, 3, 4, 4, 4, 4]


def test_sin_video_ni_audio_la_pelicula_se_dibuja_con_su_respaldo():
    import pygame

    from src.ui import cinematica_render

    pygame.init()
    pantalla = pygame.Surface((1280, 720))
    toma = cine.Toma("p", 10.0, fondo="no_existe", video="no_existe", efecto=cine.EFECTO_PELICULA, pelicula=True,
                     pista="no_existe", rotulos=[cine.Rotulo(0.0, 5.0, "Hola", hablante="LÍA"),
                                                 cine.Rotulo(1.0, 4.0, "ALERTA", cine.ROTULO_ALERTA),
                                                 cine.Rotulo(2.0, 4.0, "LEMA", cine.ROTULO_LEMA, fila=1),
                                                 cine.Rotulo(3.0, 9.0, "TÍTULO", cine.ROTULO_TITULO)])
    c = cine.Cinematica([toma])
    for tiempo in (0.0, 1.5, 3.5, 8.0):
        c.tiempo = tiempo
        cinematica_render.dibujar_cinematica(pantalla, c)


def test_contenido_rechaza_rotulos_fuera_de_tiempo():
    import pytest

    with pytest.raises(ContenidoInvalido):
        _validar_cinematica([{"id": "p", "duracion": 5.0, "rotulos": [{"inicio": 4.0, "fin": 6.0, "texto": "x"}]}])
    with pytest.raises(ContenidoInvalido):
        _validar_cinematica([{"id": "p", "duracion": 5.0, "rotulos": [{"inicio": 1.0, "fin": 2.0}]}])


def test_la_banda_sonora_esta_masterizada_y_sin_saturar():
    """-16 LUFS integrados (±1) y ninguna muestra al tope, medido con Pygame."""
    import array
    import math

    import pygame

    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    pygame.mixer.init(44100, -16, 2)
    try:
        sonido = pygame.mixer.Sound(os.path.join(RAIZ, assets.MUSICA[assets.PISTA_PROLOGO]))
        muestras = array.array("h", sonido.get_raw())
    finally:
        pygame.mixer.quit()
    pico = max(abs(m) for m in muestras[::3])
    rms = math.sqrt(sum(m * m for m in muestras[::11]) / len(muestras[::11]))
    assert pico < 32767  # sin clipping
    assert -21 < 20 * math.log10(rms / 32768) < -15  # fuerte, no un susurro (antes llegaba a 0.19 de volumen)
