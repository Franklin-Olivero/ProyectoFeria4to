"""Monta el prólogo «La ciudad que perdió» a partir de los clips de Higgsfield.

Solo se usa al producir el contenido, no al jugar (el juego no necesita ffmpeg):

    pip install imageio-ffmpeg          # en un entorno aparte
    python tools/montar_prologo.py

Historia (≈65 s): Teo, el defensor de la ficticia Ciudad Umbral, comparte sin
verificar («No tengo tiempo para eso»), descarta la misión de investigar el
Colegio, el Hospital y la Empresa de Medios («Seguro alguien más se encarga»),
las misiones quedan sin completar mientras el colapso sube, una ciudadana le
reclama que tuvo las pruebas y la ciudad cae. Él lo reconoce («Pude haber hecho
algo... y no lo hice»). Corte a Ciudad Nova: «Ellos tuvieron su oportunidad.
Esta es la tuya».

Entradas (fuera de git, en _packs/prologo_umbral/, ver docs/ASSET_MANIFEST.md):
    clips/*.mp4                 tomas de Kling 3.0 (24 fps)
    audio2/*.mp3                voces en español (ElevenLabs v4 vía Higgsfield)
    audio/m1_tension.mp3, m2_heroica.mp3   música (ElevenLabs Music vía Higgsfield)
y del repo: cuadros de assets/story/video/{intro_ciudad,nova_aparicion}, las
ilustraciones de capítulo de assets/story/ y los efectos de assets/audio/sfx.

Salidas:
    assets/story/video/prologo_umbral/*.jpg + clip.json   cuadros (lineal, 15 fps)
    assets/audio/musica/prologo_umbral.ogg                banda sonora masterizada
    content/campaign.json → cinematica_intro[0]           duración y rótulos (subtítulos
                                                          sacados de la misma lista de voces)
    _packs/prologo_umbral/prologo_umbral.mp4              máster con audio (sin rótulos)

Audio: cada voz se normaliza por separado (-16 LUFS; los susurros -18), la
música baja sola mientras alguien habla (sidechain) y la mezcla final se
masteriza en dos pasadas a -16 LUFS integrados con pico verdadero ≤ -1 dBTP.
"""

import json
import os
import re
import shutil
import subprocess

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
FUENTES = os.path.join(RAIZ, "_packs", "prologo_umbral")
CLIPS = os.path.join(FUENTES, "clips")
AUDIO = os.path.join(FUENTES, "audio")
VOZ = os.path.join(FUENTES, "audio2")
SFX = os.path.join(RAIZ, "assets", "audio", "sfx")
VIDEOS = os.path.join(RAIZ, "assets", "story", "video")
HISTORIA = os.path.join(RAIZ, "assets", "story")
CAMPANIA = os.path.join(RAIZ, "content", "campaign.json")
ID_CLIP = "prologo_umbral"

FPS = 15  # cuadros por segundo del resultado (pixel art fluido sin pesar demasiado)
ANCHO_CUADRO, ALTO_CUADRO = 960, 540  # el juego los escala a 1280×720 en el hilo lector
CALIDAD_JPG = 4  # 2 = mejor, 31 = peor
LUFS_OBJETIVO, PICO_MAXIMO = -16.0, -1.0  # máster: loudness integrado y pico verdadero (dBTP)
LUFS_VOZ, LUFS_SUSURRO = -16.0, -18.0

# ----------------------------------------------------------------------
# Montaje (EDL): (id, fuente, desde_s, duracion_s, opciones)
#   fuente: archivo de clips/, "cuadros:<id>" (JPG a 12 fps del repo),
#           "imagen:<id>" (ilustración de assets/story/, con acercamiento lento),
#           "negro" o "blanco"
#   opciones: glitch (interferencia), lento (factor de duración), congelar (s extra)
# ----------------------------------------------------------------------
TOMAS = [
    # A — La primera decisión
    ("error", "v01_error.mp4", 0.3, 4.4, {}),
    ("compartir", "v02_pulgar.mp4", 0.6, 2.0, {}),
    ("red", "v03_red.mp4", 0.6, 1.6, {}),
    # B — La oportunidad que ignoró
    ("mirador", "n1_mirador.mp4", 0.0, 3.4, {}),
    ("mision", "n2_mision.mp4", 0.0, 2.8, {}),
    # C — Las consecuencias se acumulan
    ("transicion", "v04_transicion.mp4", 1.6, 2.2, {}),
    ("entradas", "n3_entradas.mp4", 0.4, 2.6, {}),
    ("discusion", "v05_discusion.mp4", 0.4, 1.4, {}),
    ("camina", "v06_camina.mp4", 0.6, 1.4, {}),
    # D — La confrontación
    ("acusacion", "v07_acusacion.mp4", 0.3, 3.0, {}),
    ("replica", "n4_replica.mp4", 0.0, 4.8, {}),
    # E — El arrepentimiento
    ("rostro", "v08_rostro.mp4", 0.2, 4.2, {}),
    ("telefono", "v09_telefono.mp4", 0.4, 3.0, {}),
    ("solo", "v10_solo.mp4", 0.0, 3.6, {}),
    # Hubo señales, hubo pruebas, hubo oportunidades
    ("eco_red", "v03_red.mp4", 3.0, 1.2, {}),
    ("eco_mision", "n2_mision.mp4", 0.8, 1.2, {}),
    ("eco_entradas", "n3_entradas.mp4", 2.8, 1.4, {}),
    ("eco_solo", "v10_solo.mp4", 2.0, 2.0, {}),
    ("interferencia", "v10_solo.mp4", 4.0, 0.4, {"glitch": True}),
    ("destello", "blanco", 0.0, 2 / FPS, {}),
    # Ciudad Nova
    ("nova", "cuadros:intro_ciudad", 0.0, 3.4, {}),
    ("nova_amenaza", "cuadros:nova_aparicion", 0.6, 1.4, {}),
    ("lugar_colegio", "imagen:capitulo_colegio", 0.0, 2.0, {}),
    ("lugar_hospital", "imagen:capitulo_hospital", 0.0, 1.95, {}),
    ("lugar_medios", "imagen:capitulo_medios", 0.0, 2.45, {}),
    ("heroe", "v11_heroe.mp4", 0.0, 5.0, {"congelar": 3.9}),
]

# ----------------------------------------------------------------------
# Voces: (archivo de audio2/, toma, desfase_s, hablante, subtítulo, susurro)
# Su posición define también el subtítulo (mismo inicio, fin = fin de la voz).
# ----------------------------------------------------------------------
LIA, TEO, CIUDADANA, NARRADOR = "LÍA", "TEO", "CIUDADANA", "NARRADOR"
VOCES = [
    ("a1_lia.mp3", "error", 0.25, LIA, "Espera. ¿Ya comprobaste si eso es verdad?", False),
    ("a2_teo_tiempo.mp3", "error", 3.45, TEO, "No tengo tiempo para eso.", False),
    ("a3_teo_alguien.mp3", "mision", 0.0, TEO, "Seguro alguien más se encarga.", False),
    ("a4_ciudadana1.mp3", "acusacion", 0.25, CIUDADANA, "¡Podías haberlo detenido!", False),
    ("a5_teo_nosabia.mp3", "acusacion", 2.45, TEO, "Yo no sabía que iba a terminar así...", False),
    ("a6_ciudadana2.mp3", "replica", 2.3, CIUDADANA, "¡Tuviste las pruebas! ¡Tuviste la oportunidad!", False),
    ("a7_teo_pude.mp3", "telefono", 0.6, TEO, "Pude haber hecho algo...", True),
    ("a8_teo_nolohice.mp3", "solo", 0.25, TEO, "Y no lo hice.", True),
    ("n1_senales.mp3", "solo", 1.5, NARRADOR, "En Umbral hubo señales.", False),
    ("n2_pruebas.mp3", "eco_red", 0.15, NARRADOR, "Hubo pruebas. Hubo oportunidades de detenerlo.", False),
    ("n3_nadie.mp3", "eco_solo", 0.0, NARRADOR, "Pero nadie actuó a tiempo.", False),
    ("n4_amenaza.mp3", "nova", 0.25, NARRADOR, "Ahora la misma amenaza está llegando a tu ciudad.", False),
    ("n5_investigar.mp3", "lugar_colegio", 0.05, NARRADOR, "Tú puedes investigar.", False),
    ("n6_verdad.mp3", "lugar_hospital", 0.05, NARRADOR, "Puedes descubrir la verdad.", False),
    ("n7_decisiones.mp3", "lugar_medios", 0.05, NARRADOR, "Puedes tomar decisiones diferentes.", False),
    ("n8_ellos.mp3", "heroe", 0.35, NARRADOR, "Ellos tuvieron su oportunidad.", False),
    ("n9_tuya.mp3", "heroe", 2.85, NARRADOR, "Esta es la tuya.", False),
]

# ----------------------------------------------------------------------
# Rótulos que no son voces: (toma, desde_s, hasta_s o None = fin de la toma
# + extra, estilo, texto, campos extra). Los dibuja src/ui/cinematica_render.py.
# ----------------------------------------------------------------------
ROTULOS = [
    ("mirador", 0.6, ("mision", 1.3), "mision", "INVESTIGAR EL ORIGEN DEL RUMOR|Colegio · Hospital · Empresa de Medios|3 pruebas por recuperar|2 publicaciones por verificar", {"x": 0.6, "y": 0.5}),
    ("mision", 1.4, ("mision", 2.8), "descartada", "MISIÓN DESCARTADA", {"x": 0.6, "y": 0.42}),
    ("transicion", 0.2, ("transicion", 2.2), "dia", "DÍA 2 · Misión sin completar", {}),
    ("transicion", 0.4, ("discusion", 1.0), "post", "@UmbralAlerta|URGENTE: cierran el hospital hoy. ¡Compartan!", {"x": 0.06, "y": 0.24}),
    ("entradas", 0.1, ("entradas", 2.6), "dia", "DÍA 4 · 3 misiones sin completar", {}),
    ("entradas", 0.5, ("camina", 1.0), "post", "@VozDeUmbral|El colegio oculta la verdad. ¡Difunde!", {"x": 0.64, "y": 0.62}),
    ("discusion", 0.0, ("camina", 1.4), "dia", "DÍA 6 · Nadie verificó", {}),
    ("transicion", 0.0, ("camina", 1.4), "colapso", "COLAPSO DE UMBRAL", {"valor_desde": 18, "valor_hasta": 94}),
    ("telefono", 0.2, ("telefono", 3.0), "mision", "MISIONES SIN COMPLETAR|Colegio · Hospital · Empresa de Medios|0 de 3 pruebas recuperadas", {"x": 0.6, "y": 0.52}),
    ("telefono", 0.3, ("solo", 1.6), "alerta", "CIUDAD UMBRAL — COLAPSO TOTAL", {}),
    ("lugar_colegio", 0.15, ("lugar_colegio", 2.0), "lugar", "COLEGIO", {"x": 0.5, "y": 0.2}),
    ("lugar_hospital", 0.15, ("lugar_hospital", 1.95), "lugar", "HOSPITAL", {"x": 0.5, "y": 0.2}),
    ("lugar_medios", 0.15, ("lugar_medios", 2.45), "lugar", "EMPRESA DE MEDIOS", {"x": 0.5, "y": 0.2}),
    ("heroe", 4.85, ("heroe", 7.05), "lema", "ERES LA ÚLTIMA ESPERANZA DE CIUDAD NOVA.", {"fila": 0}),
    ("heroe", 5.45, ("heroe", 7.05), "lema", "MAKE IT COUNT.", {"fila": 1}),
    ("heroe", 6.9, ("heroe", 8.9), "titulo", "CIVITAS: CÓDIGO NOVA|¿Vas a cometer los mismos errores o vas a salvar Ciudad Nova?", {}),
]

EFECTOS = [
    (os.path.join(SFX, "ui", "notificacion.wav"), "compartir", 0.9, 0.9),
    (os.path.join(SFX, "jefe", "viral.wav"), "compartir", 1.3, 0.8),
] + [
    # Cascada de notificaciones: cada vez más seguidas (el rumor se multiplica).
    (os.path.join(SFX, "ui", "notificacion.wav"), "red", 0.1 + 1.4 * (1 - (1 - i / 9) ** 1.6), 0.35)
    for i in range(10)
] + [
    (os.path.join(SFX, "ui", "notificacion.wav"), "mirador", 0.5, 0.8),  # llega la misión
    (os.path.join(SFX, "ui", "bitcade_ui_error.wav"), "mision", 1.4, 0.8),  # la descarta
    (os.path.join(SFX, "ui", "reputacion_baja.wav"), "entradas", 0.3, 0.6),
    (os.path.join(SFX, "ui", "notificacion.wav"), "transicion", 0.5, 0.5),
    (os.path.join(SFX, "ui", "notificacion.wav"), "entradas", 0.6, 0.5),
    (os.path.join(SFX, "enemigos", "glitch.wav"), "telefono", 0.3, 0.6),
    (os.path.join(SFX, "enemigos", "glitch.wav"), "interferencia", 0.0, 1.0),
    (os.path.join(SFX, "ciudad", "transicion.wav"), "destello", 0.0, 0.9),
    (os.path.join(SFX, "enemigos", "glitch.wav"), "nova_amenaza", 0.0, 0.7),
]
# Ambiente que Kling generó (lluvia, murmullo, sirenas): (toma de donde sale, toma donde suena, desde, dur, vol)
AMBIENTE = [
    ("transicion", "transicion", None, None, 0.6),
    ("entradas", "entradas", None, None, 0.65),
    ("discusion", "discusion", None, None, 0.7),
    ("camina", "camina", None, None, 0.6),
    ("entradas", "acusacion", 0.0, 4.6, 0.3),  # murmullo bajo la confrontación
    ("entradas", "replica", 0.0, 4.8, 0.3),
]
MUSICA = [
    # (archivo, toma, desfase, volumen, desde, duracion, fundido_salida)
    # duracion: segundos, "hasta:<toma>:<extra_s>" o None (hasta el final)
    ("m1_tension.mp3", "error", 0.0, 0.75, 0.0, "hasta:rostro:0.6", 1.0),  # se corta en el primer plano de Teo
    ("m1_tension.mp3", "rostro", 1.0, 0.5, 0.4, "hasta:eco_red:0.0", 1.2),  # casi silencio: un pulso lejano
    ("m1_tension.mp3", "eco_red", 0.0, 0.6, 3.0, "hasta:destello:0.0", 0.4),
    ("m1_tension.mp3", "nova", 0.0, 0.6, 6.0, "hasta:lugar_colegio:0.4", 1.4),  # Nova: la amenaza crece
    ("m2_heroica.mp3", "lugar_colegio", -2.6, 0.85, 0.0, None, 1.6),  # esperanza: sube con los lugares
]


def ffmpeg():
    import imageio_ffmpeg

    return imageio_ffmpeg.get_ffmpeg_exe()


def _cuadros(segundos):
    return round(segundos * FPS)


def _cuadros_de_toma(duracion, op):
    """(cuadros del clip, cuadros congelados): enteros, así el video y el audio
    usan exactamente los mismos instantes de corte (sin deriva por redondeo)."""
    return _cuadros(duracion * op.get("lento", 1.0)), _cuadros(op.get("congelar", 0.0))


def _inicio_de_tomas():
    inicios, cuadro = {}, 0
    for id_toma, _f, _d, duracion, op in TOMAS:
        inicios[id_toma] = cuadro / FPS
        cuadro += sum(_cuadros_de_toma(duracion, op))
    return inicios, cuadro / FPS


def _fin_de_toma(inicios, id_toma):
    _id, _f, _d, duracion, op = next(t for t in TOMAS if t[0] == id_toma)
    return inicios[id_toma] + sum(_cuadros_de_toma(duracion, op)) / FPS


def _duracion_audio(ruta):
    salida = subprocess.run([ffmpeg(), "-i", ruta], capture_output=True, text=True).stderr
    h, m, s = re.search(r"Duration: (\d+):(\d+):([\d.]+)", salida).groups()
    return int(h) * 3600 + int(m) * 60 + float(s)


# ----------------------------------------------------------------------
# Video
# ----------------------------------------------------------------------


def _fuente_video(fuente):
    if fuente.startswith("cuadros:"):
        return ["-framerate", "12", "-i", os.path.join(VIDEOS, fuente.split(":", 1)[1], "%04d.jpg")]
    if fuente.startswith("imagen:"):
        return ["-loop", "1", "-framerate", str(FPS), "-i", os.path.join(HISTORIA, fuente.split(":", 1)[1] + ".png")]
    return ["-i", os.path.join(CLIPS, fuente)]


def montar_video(salida):
    entradas, filtros, etiquetas, indice = [], [], [], {}
    for _id, fuente, _d, _dur, _op in TOMAS:
        if fuente not in ("negro", "blanco") and fuente not in indice:
            indice[fuente] = len(indice)
            entradas += _fuente_video(fuente)
    for n, (id_toma, fuente, desde, duracion, op) in enumerate(TOMAS):
        cuadros, congelados = _cuadros_de_toma(duracion, op)
        if fuente in ("negro", "blanco"):
            color = "black" if fuente == "negro" else "white"
            filtros.append(f"color=c={color}:s=1280x720:r={FPS},trim=end_frame={cuadros},setsar=1,format=yuv420p[t{n}]")
        elif fuente.startswith("imagen:"):
            # Ilustración fija con acercamiento lento hacia el centro (Ken Burns).
            filtros.append(
                f"[{indice[fuente]}:v]scale=1280:720:flags=lanczos,trim=end_frame={cuadros},setpts=PTS-STARTPTS,"
                f"scale=2560:1440,zoompan=z='1+0.07*on/{cuadros}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
                f":d=1:s=1280x720:fps={FPS},setsar=1,format=yuv420p[t{n}]")
        else:
            # Se recorta con margen, se pasa a FPS y se cortan los cuadros exactos.
            cadena = (f"[{indice[fuente]}:v]trim=start={desde}:duration={duracion + 0.5},setpts=PTS-STARTPTS,"
                      f"scale=1280:720:flags=lanczos,setsar=1")
            if op.get("lento"):
                cadena += f",setpts={op['lento']}*PTS"
            cadena += f",fps={FPS},trim=end_frame={cuadros},setpts=PTS-STARTPTS"
            if op.get("glitch"):
                cadena += ",rgbashift=rh=-10:bh=10:gv=4,noise=alls=45:allf=t,eq=contrast=1.25:saturation=0.6"
            if congelados:
                cadena += f",tpad=stop_mode=clone:stop={congelados}"
            filtros.append(cadena + f",format=yuv420p[t{n}]")
        etiquetas.append(f"[t{n}]")
    filtros.append("".join(etiquetas) + f"concat=n={len(TOMAS)}:v=1:a=0[v]")
    subprocess.run([ffmpeg(), "-y", "-v", "error", *entradas, "-filter_complex", ";".join(filtros),
                    "-map", "[v]", "-c:v", "libx264", "-crf", "16", "-preset", "medium", "-r", str(FPS), salida],
                   check=True)


# ----------------------------------------------------------------------
# Audio
# ----------------------------------------------------------------------


def _medir_loudness(ruta, filtro_previo=""):
    """Primera pasada de loudnorm: lo que mide del archivo (dict de strings)."""
    filtro = (filtro_previo + "," if filtro_previo else "") + \
        f"loudnorm=I={LUFS_OBJETIVO}:TP={PICO_MAXIMO}:LRA=11:print_format=json"
    salida = subprocess.run([ffmpeg(), "-hide_banner", "-nostats", "-i", ruta, "-af", filtro, "-f", "null", "-"],
                            capture_output=True, text=True).stderr
    return json.loads(salida[salida.rindex("{"):salida.rindex("}") + 1])


def montar_audio(salida, duracion_total):
    inicios, _ = _inicio_de_tomas()
    entradas, filtros = [], []
    grupos = {"voz": [], "musica": [], "sfx": []}

    def entrada(ruta):
        entradas.extend(["-i", ruta])
        return len(entradas) // 2 - 1

    def colocar(i, instante, volumen, grupo, extra=""):
        ms = max(0, round(instante * 1000))
        etiqueta = f"a{len(filtros)}"
        filtros.append(f"[{i}:a]aformat=sample_rates=48000:channel_layouts=stereo{extra},"
                       f"volume={volumen},adelay={ms}|{ms}[{etiqueta}]")
        grupos[grupo].append(f"[{etiqueta}]")

    for archivo, toma, desfase, _h, _t, susurro in VOCES:
        # Cada línea a su loudness (los susurros algo más bajos), sin ruido de fondo
        # y con compresión suave: así ninguna voz queda tapada.
        lufs = LUFS_SUSURRO if susurro else LUFS_VOZ
        extra = (",highpass=f=80,acompressor=threshold=0.125:ratio=3:attack=5:release=120:makeup=1,"
                 f"loudnorm=I={lufs}:TP=-2:LRA=7,aresample=48000,asetpts=N/SR/TB")
        colocar(entrada(os.path.join(VOZ, archivo)), inicios[toma] + desfase, 1.0, "voz", extra)
    for ruta, toma, desfase, volumen in EFECTOS:
        colocar(entrada(ruta), inicios[toma] + desfase, volumen, "sfx")
    for origen, destino, desde, duracion, volumen in AMBIENTE:
        _id, fuente, desde_toma, dur_toma, _op = next(t for t in TOMAS if t[0] == origen)
        desde = desde_toma if desde is None else desde
        duracion = dur_toma if duracion is None else duracion
        extra = (f",atrim=start={desde}:duration={duracion},asetpts=PTS-STARTPTS,"
                 f"afade=t=in:d=0.2,afade=t=out:st={duracion - 0.4}:d=0.4")
        colocar(entrada(os.path.join(CLIPS, fuente)), inicios[destino], volumen, "sfx", extra)
    for archivo, toma, desfase, volumen, desde, duracion, fundido in MUSICA:
        inicio = inicios[toma] + desfase
        if duracion is None:
            duracion = duracion_total - inicio
        elif isinstance(duracion, str):
            _, hasta, extra_s = duracion.split(":")
            duracion = inicios[hasta] + float(extra_s) - inicio
        extra = (f",atrim=start={desde}:duration={duracion:.3f},asetpts=PTS-STARTPTS,"
                 f"afade=t=out:st={max(0.0, duracion - fundido):.3f}:d={fundido}")
        colocar(entrada(os.path.join(AUDIO, archivo)), inicio, volumen, "musica", extra)

    def mezclar(grupo, etiqueta):
        filtros.append("".join(grupos[grupo]) + f"amix=inputs={len(grupos[grupo])}:normalize=0:dropout_transition=0,"
                       f"asetpts=N/SR/TB,apad=whole_dur={duracion_total}[{etiqueta}]")

    mezclar("voz", "voz")
    mezclar("musica", "mus")
    mezclar("sfx", "fx")
    filtros.append("[voz]asplit=3[voz1][voz2][voz3]")
    # Mientras alguien habla, música y efectos bajan solos (ducking ~10 dB).
    filtros.append("[mus][voz2]sidechaincompress=threshold=0.015:ratio=10:attack=20:release=400[musb]")
    filtros.append("[fx][voz3]sidechaincompress=threshold=0.015:ratio=4:attack=20:release=300[fxb]")
    # (sin atrim: con las marcas de tiempo que deja loudnorm cortaba la voz; se corta con -t)
    filtros.append(f"[voz1][musb][fxb]amix=inputs=3:normalize=0,"
                   f"afade=t=out:st={duracion_total - 0.8}:d=0.8[mezcla]")
    crudo = os.path.join(FUENTES, "mezcla_cruda.wav")
    subprocess.run([ffmpeg(), "-y", "-v", "error", *entradas, "-filter_complex", ";".join(filtros),
                    "-map", "[mezcla]", "-t", f"{duracion_total:.3f}", "-ar", "48000", "-ac", "2", "-c:a", "pcm_f32le",
                    crudo], check=True)
    # Máster en dos pasadas: medir y luego normalizar en modo lineal (sin bombeo).
    m = _medir_loudness(crudo)
    norma = (f"loudnorm=I={LUFS_OBJETIVO}:TP={PICO_MAXIMO}:LRA=11:measured_I={m['input_i']}:"
             f"measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:"
             f"offset={m['target_offset']}:linear=true,alimiter=limit=0.84:level=false,aresample=44100")
    subprocess.run([ffmpeg(), "-y", "-v", "error", "-i", crudo, "-af", norma, "-ar", "44100", "-ac", "2",
                    "-c:a", "libvorbis", "-q:a", "6", salida], check=True)
    os.remove(crudo)


# ----------------------------------------------------------------------
# Rótulos → content/campaign.json
# ----------------------------------------------------------------------


def rotulos(duracion_total):
    inicios, _ = _inicio_de_tomas()
    lista = []
    for archivo, toma, desfase, hablante, texto, _s in VOCES:
        inicio = inicios[toma] + desfase
        fin = inicio + _duracion_audio(os.path.join(VOZ, archivo)) + 0.25
        lista.append({"inicio": round(inicio, 2), "fin": round(fin, 2), "texto": texto,
                      "hablante": hablante, "estilo": "subtitulo"})
    for toma, desde, (hasta_toma, hasta_s), estilo, texto, extra in ROTULOS:
        fin = min(duracion_total, inicios[hasta_toma] + hasta_s)
        lista.append({"inicio": round(inicios[toma] + desde, 2), "fin": round(fin, 2), "texto": texto,
                      "estilo": estilo, **extra})
    # Ningún subtítulo se queda pegado al siguiente.
    subs = sorted((r for r in lista if r["estilo"] == "subtitulo"), key=lambda r: r["inicio"])
    for actual, siguiente in zip(subs, subs[1:]):
        actual["fin"] = min(actual["fin"], round(siguiente["inicio"] - 0.05, 2))
    return sorted(lista, key=lambda r: r["inicio"])


def escribir_campania(duracion_total):
    with open(CAMPANIA, encoding="utf-8") as archivo:
        texto = archivo.read()
    datos = json.loads(texto)
    toma = datos["cinematica_intro"][0]
    toma["duracion"] = round(duracion_total, 2)
    toma["rotulos"] = rotulos(duracion_total)
    inicio = texto.index('  "cinematica_intro": [')
    fin = texto.index('  "objetivos_intro": [')
    bloque = '  "cinematica_intro": ' + json.dumps(datos["cinematica_intro"], ensure_ascii=False, indent=2).replace("\n", "\n  ") + ",\n"
    with open(CAMPANIA, "w", encoding="utf-8") as archivo:
        archivo.write(texto[:inicio] + bloque + texto[fin:])


def extraer_cuadros(video, carpeta):
    if os.path.isdir(carpeta):
        shutil.rmtree(carpeta)
    os.makedirs(carpeta)
    subprocess.run([ffmpeg(), "-y", "-v", "error", "-i", video, "-vf", f"scale={ANCHO_CUADRO}:{ALTO_CUADRO}:flags=lanczos",
                    "-q:v", str(CALIDAD_JPG), os.path.join(carpeta, "%04d.jpg")], check=True)
    total = len([n for n in os.listdir(carpeta) if n.endswith(".jpg")])
    with open(os.path.join(carpeta, "clip.json"), "w", encoding="utf-8") as archivo:
        json.dump({"fps": FPS, "lineal": True, "cuadros": total,
                   "origen": "Higgsfield: Kling 3.0 + ElevenLabs (ver docs/ASSET_MANIFEST.md)"}, archivo)
    return total


def main():
    inicios, total = _inicio_de_tomas()
    print(f"Duración total: {total:.2f} s")
    for id_toma, inicio in inicios.items():
        print(f"  {inicio:6.2f}  {id_toma}")
    video = os.path.join(FUENTES, "prologo_video.mp4")
    ogg = os.path.join(RAIZ, "assets", "audio", "musica", f"{ID_CLIP}.ogg")
    montar_video(video)
    montar_audio(ogg, total)
    escribir_campania(total)
    master = os.path.join(FUENTES, f"{ID_CLIP}.mp4")
    subprocess.run([ffmpeg(), "-y", "-v", "error", "-i", video, "-i", ogg, "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                    "-shortest", master], check=True)
    cuadros = extraer_cuadros(video, os.path.join(VIDEOS, ID_CLIP))
    m = _medir_loudness(ogg)
    print(f"{cuadros} cuadros a {FPS} fps; audio {m['input_i']} LUFS, pico {m['input_tp']} dBTP")


if __name__ == "__main__":
    main()
