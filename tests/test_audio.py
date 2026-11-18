"""Audio sin dispositivo ni pygame: catálogo de IDs, rutas, fallback,
mezcla, anti-spam, cola de eventos y que todo lo que el juego pide exista."""

import glob
import json
import os
import re
import sys
import wave

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, RAIZ)
os.chdir(RAIZ)

import pytest  # noqa: E402

from src.audio import eventos_sonido  # noqa: E402
from src.core import assets  # noqa: E402
from src.core.balance import (  # noqa: E402
    DURACION_MAXIMA_LARGO,
    DURACION_MAXIMA_SFX,
    GANANCIA_MUSICA,
    GANANCIA_SONIDO,
    LARGOS_PERMITIDOS,
    STATS_POR_ROL,
    VOLUMEN_CATEGORIA,
)
from src.audio.ajustes_audio import AjustesAudio  # noqa: E402
from src.audio.mezcla import LimitadorSonidos, categoria, resolver_ruta, volumen_final  # noqa: E402
from src.entities.tipos_enemigo import TipoEnemigo  # noqa: E402


# ----------------------------------------------------------------------
# Catálogo: cada ID apunta a un archivo que existe
# ----------------------------------------------------------------------

def test_todas_las_rutas_de_sonido_existen():
    faltan = [(i, ruta) for i, (ruta, _) in assets.SONIDOS.items() if not os.path.exists(ruta)]
    assert not faltan


def test_todas_las_pistas_de_musica_existen():
    faltan = [(i, ruta) for i, ruta in assets.MUSICA.items() if not os.path.exists(ruta)]
    assert not faltan


def test_rutas_dentro_de_assets_audio_en_minusculas_sin_espacios_ni_tildes():
    rutas = [ruta for ruta, _ in assets.SONIDOS.values()] + list(assets.MUSICA.values())
    for ruta in rutas:
        partes = os.path.normpath(ruta).split(os.sep)
        assert partes[:2] == ["assets", "audio"], ruta
        assert re.fullmatch(r"[a-z0-9_./\\]+", ruta), ruta


def test_cada_sonido_tiene_categoria_y_ganancia():
    for id_sonido, (_, grupo) in assets.SONIDOS.items():
        assert grupo in (assets.CATEGORIA_SFX, assets.CATEGORIA_UI)
        assert 0 < GANANCIA_SONIDO[id_sonido] <= 1.0
    assert set(GANANCIA_SONIDO) == set(assets.SONIDOS)
    assert set(GANANCIA_MUSICA) == set(assets.MUSICA)
    assert all(0 < g <= 1.0 for g in GANANCIA_MUSICA.values())
    assert set(VOLUMEN_CATEGORIA) == {assets.CATEGORIA_MUSICA, assets.CATEGORIA_SFX, assets.CATEGORIA_UI,
                                      assets.CATEGORIA_CINEMATICA}


def _duracion_wav(ruta):
    with wave.open(ruta) as archivo:
        return archivo.getnframes() / archivo.getframerate()


def test_duracion_de_los_efectos():
    """Efectos cortos; solo habilidades, jefe, jingles y transiciones de la
    historia pueden pasar de DURACION_MAXIMA_SFX."""
    for id_sonido, (ruta, _) in assets.SONIDOS.items():
        duracion = _duracion_wav(ruta)
        limite = DURACION_MAXIMA_LARGO if id_sonido in LARGOS_PERMITIDOS else DURACION_MAXIMA_SFX
        assert duracion <= limite, (id_sonido, duracion)


def test_ningun_archivo_de_audio_pesa_mas_de_5_mb_y_el_total_menos_de_40():
    archivos = [f for f in glob.glob(os.path.join("assets", "audio", "**", "*"), recursive=True) if os.path.isfile(f)]
    assert all(os.path.getsize(f) <= 5 * 1024 * 1024 for f in archivos)
    assert sum(os.path.getsize(f) for f in archivos) < 40 * 1024 * 1024


# ----------------------------------------------------------------------
# Todo lo que el juego pide existe en el catálogo
# ----------------------------------------------------------------------

def _literales(patron):
    encontrados = set()
    for ruta in glob.glob("src/**/*.py", recursive=True) + ["Main.py"]:
        with open(ruta, encoding="utf-8") as archivo:
            encontrados |= set(re.findall(patron, archivo.read()))
    return encontrados


def test_cada_evento_emitido_existe():
    for id_sonido in _literales(r'emitir\("([a-z_]+)"\)') | _literales(r'sonar\("([a-z_]+)"\)'):
        assert id_sonido in assets.SONIDOS, id_sonido
    for rol in STATS_POR_ROL:
        assert f"disparo_{rol}" in assets.SONIDOS and f"habilidad_{rol}" in assets.SONIDOS
    for tipo in TipoEnemigo:
        assert f"muerte_{tipo.value}" in assets.SONIDOS


def test_sonidos_de_la_historia_existen():
    with open(os.path.join("content", "campaign.json"), encoding="utf-8") as archivo:
        contenido = archivo.read()
    usados = set(re.findall(r'"sonido":\s*"([a-z_]+)"', contenido)) | _literales(r'sonido="([a-z_]+)"')
    assert usados and all(id_sonido in assets.SONIDOS for id_sonido in usados), usados - set(assets.SONIDOS)
    json.loads(contenido)  # sigue siendo JSON válido


def test_cada_pista_pedida_existe():
    pedidas = _literales(r'musica\("([a-z_]+)"\)') | _literales(r'return "([a-z_]+)"\n') & set(assets.MUSICA)
    pedidas |= {"ciudad", "combate", "decision", "misterio", "jefe", "victoria", "derrota", "crisis", "redencion"}
    assert pedidas <= set(assets.MUSICA), pedidas - set(assets.MUSICA)


# ----------------------------------------------------------------------
# Resolución de rutas y fallback silencioso
# ----------------------------------------------------------------------

def test_resolver_ruta_con_archivo_presente():
    ruta = assets.SONIDOS["dash"][0]
    assert resolver_ruta("dash", existe=lambda r: True) == ruta
    assert resolver_ruta("menu", assets.MUSICA, existe=lambda r: True) == assets.MUSICA["menu"]


def test_resolver_ruta_sin_archivo_o_id_desconocido_es_none():
    assert resolver_ruta("dash", existe=lambda r: False) is None
    assert resolver_ruta("no_existe") is None
    assert resolver_ruta(None) is None
    assert resolver_ruta("menu", assets.MUSICA, existe=lambda r: False) is None


def test_categoria():
    assert categoria("navegar") == assets.CATEGORIA_UI
    assert categoria("muerte_tirador") == assets.CATEGORIA_SFX
    assert categoria("desconocido") == assets.CATEGORIA_SFX


# ----------------------------------------------------------------------
# Mezcla
# ----------------------------------------------------------------------

def test_volumen_final_es_general_por_categoria_por_ganancia():
    ajustes = AjustesAudio(volumen_general=50, volumen_musica=80, volumen_efectos=60)
    esperado = 0.5 * 0.6 * VOLUMEN_CATEGORIA["sfx"] * GANANCIA_SONIDO["muerte_tirador"]
    assert volumen_final("muerte_tirador", ajustes) == pytest.approx(esperado)
    esperado = 0.5 * 0.8 * VOLUMEN_CATEGORIA["musica"] * GANANCIA_MUSICA["jefe"]
    assert volumen_final("jefe", ajustes, es_musica=True) == pytest.approx(esperado)
    # Los de interfaz usan el volumen de efectos con la mezcla de su categoría.
    esperado = 0.5 * 0.6 * VOLUMEN_CATEGORIA["ui"] * GANANCIA_SONIDO["navegar"]
    assert volumen_final("navegar", ajustes) == pytest.approx(esperado)
    # La pausa atenúa la música.
    assert volumen_final("jefe", ajustes, es_musica=True, atenuacion=0.5) == pytest.approx(
        0.5 * volumen_final("jefe", ajustes, es_musica=True))


def test_la_banda_sonora_de_la_cinematica_no_depende_del_deslizador_de_musica():
    # Regresión: con la música al 22 % (rescatada de un preferencias.json viejo)
    # las voces del prólogo sonaban a 0.19 y no se entendían.
    baja = AjustesAudio(volumen_general=100, volumen_musica=22, volumen_efectos=36)
    assert volumen_final("prologo_umbral", baja, es_musica=True) == pytest.approx(1.0)
    assert volumen_final("prologo_umbral", AjustesAudio(volumen_general=60), es_musica=True) == pytest.approx(0.6)
    assert volumen_final("prologo_umbral", AjustesAudio(silencio=True), es_musica=True) == 0.0
    assert volumen_final("jefe", baja, es_musica=True) < 0.25  # la música normal sí lo respeta


def test_volumen_final_silencio_cero_y_nunca_mas_de_uno():
    assert volumen_final("dash", AjustesAudio(silencio=True)) == 0.0
    assert volumen_final("menu", AjustesAudio(silencio=True), es_musica=True) == 0.0
    assert volumen_final("dash", AjustesAudio(volumen_general=0)) == 0.0
    maximo = AjustesAudio(volumen_general=100, volumen_musica=100, volumen_efectos=100)
    for id_sonido in assets.SONIDOS:
        assert 0.0 <= volumen_final(id_sonido, maximo) <= 1.0
    for id_pista in assets.MUSICA:
        assert 0.0 <= volumen_final(id_pista, maximo, es_musica=True, atenuacion=3.0) <= 1.0


# ----------------------------------------------------------------------
# Anti-spam
# ----------------------------------------------------------------------

def test_limitador_respeta_el_intervalo_minimo():
    limitador = LimitadorSonidos(maximo=3, intervalo=0.05)
    assert limitador.permitir("disparo", 0.0)
    assert not limitador.permitir("disparo", 0.02)  # demasiado pronto
    assert limitador.permitir("otro", 0.02)  # cada ID lleva su propia cuenta
    assert limitador.permitir("disparo", 0.06)


def test_limitador_respeta_el_maximo_de_copias_simultaneas():
    limitador = LimitadorSonidos(maximo=3, intervalo=0.0)
    assert limitador.permitir("impacto", 1.0, sonando=2)
    assert not limitador.permitir("impacto", 2.0, sonando=3)
    assert limitador.permitir("impacto", 3.0, sonando=0)


def test_muchos_pedidos_en_el_mismo_instante_suenan_una_vez():
    limitador = LimitadorSonidos()
    permitidos = [limitador.permitir("muerte_perseguidor", 5.0) for _ in range(10)]
    assert permitidos.count(True) == 1


# ----------------------------------------------------------------------
# Cola de eventos
# ----------------------------------------------------------------------

def test_eventos_se_drenan_en_orden_y_la_cola_queda_vacia():
    eventos_sonido.drenar()
    eventos_sonido.emitir("dash")
    eventos_sonido.emitir(None)  # se ignora
    eventos_sonido.emitir("jugador_herido")
    assert eventos_sonido.drenar() == ["dash", "jugador_herido"]
    assert eventos_sonido.drenar() == []


def test_cola_de_eventos_tiene_tope():
    eventos_sonido.drenar()
    for i in range(eventos_sonido.MAXIMO_PENDIENTES + 20):
        eventos_sonido.emitir(f"e{i}")
    pendientes = eventos_sonido.drenar()
    assert len(pendientes) == eventos_sonido.MAXIMO_PENDIENTES
    assert pendientes[-1] == f"e{eventos_sonido.MAXIMO_PENDIENTES + 19}"


def test_logica_de_audio_no_importa_pygame():
    for modulo in ("src/audio/mezcla.py", "src/audio/eventos_sonido.py", "src/audio/ajustes_audio.py",
                   "src/ui/lobby.py", "src/ui/pausa.py", "src/core/datos_usuario.py"):
        with open(modulo, encoding="utf-8") as archivo:
            assert "import pygame" not in archivo.read(), modulo
