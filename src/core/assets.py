"""Constantes visuales centralizadas: paleta, fuentes, tamaños y layout.

Todo elemento visual del juego referencia sus colores, tamaños,
posiciones y rutas de archivo desde aquí en lugar de usar valores
hardcodeados dispersos en la lógica. Los sprites en pixel art viven en
src/ui/sprites.py (dibujados en código, sin archivos de imagen); cuando
se agregue arte real, el cambio se limita a reemplazar esos sprites y
los valores de este archivo, sin tocar la lógica de juego.

La pantalla es de 1280x720 (src/core/config.py): HUD arriba (0-62),
barra de controles abajo (660-720) y el cuarto (o la vista de Ciudad
Nova, bajo el cintillo de noticias) en medio.
"""

import os

# ----------------------------------------------------------------------
# Paleta general (estilo "neón sobre noche": 4 acentos sobre azul oscuro)
# ----------------------------------------------------------------------
COLOR_FONDO = (11, 14, 38)
COLOR_FONDO_PANEL = (18, 22, 52)
COLOR_FONDO_PANEL_CLARO = (26, 32, 68)
COLOR_BORDE_PANEL = (54, 60, 108)
COLOR_LINEA_HUD = (40, 46, 88)

COLOR_TEAL = (62, 230, 196)
COLOR_TEAL_OSCURO = (18, 92, 82)
COLOR_MAGENTA = (255, 56, 120)
COLOR_MAGENTA_OSCURO = (110, 26, 60)
COLOR_AMARILLO = (255, 190, 60)
COLOR_MORADO = (164, 110, 255)
COLOR_MORADO_OSCURO = (70, 48, 120)

# Tokens semánticos de la identidad (docs/ART_DIRECTION.md): cada color
# significa una sola cosa en todo el juego.
COLOR_NOCHE = (7, 9, 26)  # azul oscuro: la ciudad y la tecnología
COLOR_CIVITAS = COLOR_MORADO  # violeta: Civitas y el foco de la interfaz
COLOR_VERIFICADO = (56, 222, 232)  # cian: información verificada
COLOR_NOVA = COLOR_MAGENTA  # magenta: la manipulación de NOVA_404
COLOR_ALERTA = COLOR_AMARILLO  # ámbar: advertencias
COLOR_GRAVE = (236, 72, 80)  # rojo: consecuencias graves
COLOR_VIDRIO_ARRIBA = (24, 28, 66)  # paneles de la interfaz (src/ui/kit.py)
COLOR_VIDRIO_ABAJO = (13, 15, 40)
COLOR_BORDE_VIDRIO = (58, 64, 116)
COLOR_FOCO_FONDO = (44, 34, 96)
COLOR_OPCION_FONDO = (18, 21, 52)
COLOR_ARISTA_RED = (64, 70, 122)
COLOR_NODO_NEUTRO = (92, 96, 142)
MARCAS_REPUTACION = (-60, -20, 20, 60)  # separaciones de los niveles en la barra


def color_reputacion(valor):
    """Color de un valor de reputación: rojo, magenta, gris, cian."""
    if valor <= -60:
        return COLOR_GRAVE
    if valor <= -20:
        return COLOR_NOVA
    if valor >= 20:
        return COLOR_VERIFICADO
    return COLOR_TEXTO_SECUNDARIO


COLOR_TEXTO_HUD = (236, 236, 246)
COLOR_TEXTO_SECUNDARIO = (150, 150, 182)
COLOR_TEXTO_APAGADO = (96, 94, 130)

# ----------------------------------------------------------------------
# Fuentes (JetBrains Mono, licencia OFL, en assets/fonts). Si el archivo
# falta, src/ui/fuentes.py cae a la fuente por defecto de pygame.
# ----------------------------------------------------------------------
RUTA_FUENTE_REGULAR = os.path.join("assets", "fuentes", "jetbrains_mono_regular.ttf")
RUTA_FUENTE_NEGRITA = os.path.join("assets", "fuentes", "jetbrains_mono_bold.ttf")
TAMANIO_FUENTE_PEQUENA = 13
TAMANIO_FUENTE_NORMAL = 15
TAMANIO_FUENTE_MEDIA = 18
TAMANIO_FUENTE_TITULO = 22
TAMANIO_FUENTE_GRANDE = 34
TAMANIO_FUENTE_ENORME = 48

# ----------------------------------------------------------------------
# Layout general
# ----------------------------------------------------------------------
ALTO_HUD = 62
ALTO_BARRA_CONTROLES = 60
RADIO_PANEL = 6  # esquinas redondeadas de paneles y chips
ESCALA_PIXEL = 3  # 1 píxel de sprite = 3 píxeles de pantalla

# HUD superior
POSICION_JUGADOR_HUD = (26, 31)  # centro de "J1"
POSICION_CORAZONES = (72, 20)  # esquina superior izq. del primer corazón
SEPARACION_CORAZONES = 25
POSICION_HABILIDAD_HUD = (72, 46)  # barra de carga de la habilidad (F)
ANCHO_BARRA_HABILIDAD = 120
ALTO_BARRA_HABILIDAD = 6
POSICION_ENEMIGOS_HUD = (300, 16)
POSICION_TITULO_HUD = (640, 24)  # centro del título del lugar
POSICION_SUBTITULO_HUD = (640, 46)
RECT_BARRA_COLAPSO = (880, 34, 260, 16)  # x, y, ancho, alto
POSICION_ETIQUETA_COLAPSO = (880, 16)
POSICION_VALOR_COLAPSO = (1156, 42)  # midleft del porcentaje
COLOR_BARRA_COLAPSO = COLOR_AMARILLO
COLOR_FONDO_BARRA = (38, 36, 74)
COLOR_BORDE_BARRA = (74, 70, 120)
# Paneles laterales (cooperativo): J1 en el margen izquierdo y J2 en el
# derecho, entre el muro del cuarto (x 122-1158) y el borde de la pantalla.
RECTS_PANEL_JUGADOR = (
    (4, 75, 114, 270),     # J1 (arriba izq)
    (1162, 75, 114, 270),   # J2 (arriba der)
    (4, 360, 114, 270),    # J3 (abajo izq)
    (1162, 360, 114, 270),  # J4 (abajo der)
)  # x, y, ancho, alto para hasta 4 jugadores
CORAZONES_POR_FILA_PANEL = 4
ANCHO_BARRA_HABILIDAD_PANEL = 70
TAMANIO_FUENTE_MINI = 10  # controles clave del panel ("Stick R Apuntar" debe caber en 96 px)

# Indicador del cooldown del dash (círculo con un muñeco corriendo)
RADIO_INDICADOR_DASH = 22
OSCURECER_INDICADOR_DASH = 0.5  # recargando: el icono a la mitad de brillo
COLOR_FONDO_INDICADOR_DASH = (14, 12, 32)
ALFA_AGUA_INDICADOR_DASH = 150  # el "agua" que sube mientras recarga
AMPLITUD_OLA_DASH = 2.5  # px
LARGO_OLA_DASH = 18  # px entre crestas
VELOCIDAD_OLA_DASH = 6.0  # rad/s: qué tan rápido se mueve la ola
CAPAS_AURA_DASH = 4  # anillos del aura neón cuando está listo
ALFA_AURA_DASH = 70  # alfa del anillo más interno (los de afuera se desvanecen)
DURACION_FLASH_DASH = 0.15  # s del destello al quedar disponible
COLOR_FLASH_DASH = (255, 255, 255)
ESCALA_ICONO_DASH = 2

# Chips de tecla en la barra de controles
COLOR_FONDO_CHIP = (30, 28, 62)
COLOR_BORDE_CHIP = (72, 68, 118)
ALTO_CHIP = 26
MARGEN_CHIP = 8
SEPARACION_CONTROLES = 22

# ----------------------------------------------------------------------
# Jugador (comunes a los 4 roles). Velocidad, vida, daño, cadencia y
# carga de cada rol viven en src/core/balance.py.
# ----------------------------------------------------------------------
TAMANIO_JUGADOR = 36
COLOR_CIUDADANO = COLOR_TEAL
COLOR_INFLUENCER = (255, 120, 220)
COLOR_PERIODISTA = (236, 236, 246)
COLOR_CANDIDATO = COLOR_AMARILLO
# Cono de apuntado: abanico translúcido hacia donde mira el jugador.
COLOR_CONO_APUNTADO = (255, 56, 120, 46)  # RGBA
LARGO_CONO_APUNTADO = 230
ANGULO_CONO_ESTRECHO = 8  # grados a cada lado, roles sin abanico

# Dash: partículas (src/ui/particulas.py) e imágenes fantasma. Solo visual;
# la duración y velocidad del dash viven en src/core/balance.py.
DASH_PARTICULAS_POR_FRAME = 3  # partículas emitidas por frame durante el dash
DASH_PARTICULA_RADIO = 5  # radio inicial de cada partícula
DASH_PARTICULA_DISPERSION = 10  # px: desvío aleatorio de la partícula respecto al jugador
DASH_PARTICULA_DURACION = 0.2  # segundos que vive cada partícula
DASH_PARTICULA_ALFA_INICIAL = 160  # alfa 0-255
DASH_AFTERIMAGES = 3  # cuántas imágenes fantasma dejar
DASH_AFTERIMAGE_ALFA = (120, 70, 30)  # alfa de cada una, de la más nueva a la más vieja

# Cooperativo: separación entre jugadores al aparecer (entrada, puerta, arena).
SEPARACION_JUGADORES_COOP = 56
# Indicador de apuntado del J2 (no tiene mira de mouse).
LARGO_INDICADOR_J2 = 34  # px desde el centro del jugador hasta la punta
TAMANIO_PUNTA_INDICADOR_J2 = 8

# ----------------------------------------------------------------------
# Proyectiles
# ----------------------------------------------------------------------
TAMANIO_PROYECTIL = 8
COLOR_PROYECTIL_JUGADOR = COLOR_TEAL
COLOR_PROYECTIL_ENEMIGO = COLOR_MORADO
VELOCIDAD_PROYECTIL = 420  # píxeles por segundo
DANIO_PROYECTIL_ENEMIGO = 1
# Estela punteada detrás de cada proyectil (solo dibujo, sin estado).
PUNTOS_ESTELA_PROYECTIL = 4
ESPACIADO_ESTELA_PROYECTIL = 14
ALFA_ESTELA_PROYECTIL = 130

# ----------------------------------------------------------------------
# Enemigo
# ----------------------------------------------------------------------
TAMANIO_ENEMIGO = 40
TAMANIO_ENEMIGO_MAXIMO = 64  # la hitbox más ancha de las variantes: lo que debe caber entre dos coberturas
COLOR_ENEMIGO = COLOR_MAGENTA
COLOR_ENEMIGO_SECUNDARIO = COLOR_MORADO
VELOCIDAD_ENEMIGO = 90  # píxeles por segundo
VIDA_ENEMIGO = 3
RANGO_DISPARO_ENEMIGO = 260  # píxeles
COOLDOWN_DISPARO_ENEMIGO = 1.2  # segundos entre disparos
# Marco amarillo sobre el enemigo al que apunta el jugador
COLOR_OBJETIVO = COLOR_AMARILLO
MARGEN_OBJETIVO = 6
LARGO_ESQUINA_OBJETIVO = 9
GROSOR_OBJETIVO = 2
TOLERANCIA_OBJETIVO = 28  # px de distancia a la línea de apuntado
COLOR_LINEA_OBJETIVO = (255, 56, 120, 150)  # línea discontinua jugador -> objetivo
# Números de daño flotantes ("-1")
COLOR_TEXTO_DANIO = COLOR_AMARILLO
DURACION_TEXTO_DANIO = 0.7  # segundos
VELOCIDAD_TEXTO_DANIO = 40  # px/s hacia arriba
# Globo con el nodo activo del behavior tree (tecla Tab)
COLOR_FONDO_GLOBO = (18, 16, 40)
COLOR_BORDE_GLOBO = COLOR_TEAL
DESPLAZAMIENTO_GLOBO = (64, -84)  # desde el centro del enemigo (hacia un lado y arriba)

# Habilidad del Ciudadano: Burbuja Comunitaria
COLOR_BURBUJA = COLOR_TEAL
GROSOR_BURBUJA = 2
RADIO_BURBUJA = 70  # píxeles
DURACION_BURBUJA = 4.0  # segundos

# ----------------------------------------------------------------------
# Selección de personaje: 4 tarjetas (una por rol) con barras de stats
# ----------------------------------------------------------------------
POSICION_TITULO_SELECCION = (640, 52)  # centro
ORIGEN_COLUMNAS_SELECCION = (70, 112)  # esquina superior izq. de la 1ra tarjeta
ANCHO_COLUMNA_SELECCION = 290  # paso entre tarjetas
ANCHO_TARJETA_SELECCION = 270
ALTO_TARJETA_SELECCION = 420
SEPARACION_FILAS_SELECCION = 28
DESPLAZAMIENTO_BARRA_X = 80  # de la etiqueta de la stat al inicio de su barra
ANCHO_MAXIMO_BARRA = 110  # barra segmentada de 10 casillas (puntaje 1-10)
SEPARACION_SEGMENTOS_BARRA = 2
COLOR_SEGMENTO_VACIO = (40, 36, 78)  # ancho de la barra del rol con el valor máximo
ALTO_BARRA = 10
# Lobby (src/ui/seleccion_rol.py): paleta neón, animación y paneles.
ESCALA_SPRITE_LOBBY = 4  # sprite animado de cada tarjeta
ELEVACION_TARJETA_LOBBY = 10  # px que sube la tarjeta bajo un cursor
SUAVIZADO_TARJETA_LOBBY = 12.0  # 1/s: qué tan rápido sube y baja (exponencial)
DURACION_ENTRADA_LOBBY = 0.35  # s del fundido desde negro al entrar
DURACION_SALIDA_LOBBY = 0.35  # s del destello + fundido al confirmar todos
COLOR_NEON_LOBBY = (196, 120, 255)  # violeta Civitas
COLOR_NEON_LOBBY_2 = (80, 220, 255)  # cian
COLOR_REJILLA_LOBBY = (120, 70, 200)
CANTIDAD_PARTICULAS_LOBBY = 36
RECT_PANEL_RESUMEN_LOBBY = (70, 548, 1140, 96)
# Menú de pausa (src/ui/pausa_render.py): la misma paleta neón del lobby.
ALFA_VELO_PAUSA = 175
# Instrucciones de mazmorra (src/ui/instrucciones_render.py).
ANCHO_TARJETA_INSTRUCCIONES = 280
ALTO_TARJETA_INSTRUCCIONES = 450
SEPARACION_TARJETAS_INSTRUCCIONES = 18
Y_TARJETAS_INSTRUCCIONES = 116
ALTO_SPRITE_INSTRUCCIONES = 140  # alto máximo del sprite grande (escala entera)
ALTO_ICONO_VARIANTE = 30
DURACION_VARIANTE_INSTRUCCIONES = 1.2  # s que se muestra cada aspecto antes de pasar al siguiente
COLOR_JEFE_INSTRUCCIONES = COLOR_MORADO
COLOR_REGLAS_INSTRUCCIONES = COLOR_AMARILLO
RECT_PANEL_PAUSA = (440, 130, 400, 440)
ALTO_OPCION_PAUSA = 50
RECT_CONFIRMACION_PAUSA = (360, 270, 560, 180)
ANCHO_BOTON_CONFIRMACION = 140
# Cursores de cada jugador sobre las tarjetas (chip "J1"/"J2" del color del
# rol, arriba a la derecha)
GROSOR_TARJETA_RESALTADA = 4
ALFA_TARJETA_CONFIRMADA = 36  # tinte del color del rol sobre la tarjeta elegida
POSICION_ESTADO_SELECCION = (640, 590)  # centro de "J1: ... · J2: ..."

# ----------------------------------------------------------------------
# Pantalla de modo: 1 o 2 jugadores (antes de elegir personaje)
# ----------------------------------------------------------------------
RECTS_OPCION_MODO = (
    (130, 170, 320, 340),
    (480, 170, 320, 340),
    (830, 170, 320, 340),
)  # x, y, ancho, alto para 1 jugador, 2 jugadores y Online
POSICION_AVISO_MODO = (640, 570)  # centro del estado del control / aviso
DURACION_AVISO_MODO = 2.5  # s que se muestra "Conecta un control..."

# Influencer: cono de sonido (proyectil ancho que empuja) / Live Stream Viral
COLOR_PROYECTIL_INFLUENCER = (255, 150, 230)
TAMANIO_PROYECTIL_INFLUENCER = 26
VELOCIDAD_PROYECTIL_INFLUENCER = 300  # píxeles por segundo
IMPULSO_EMPUJE_INFLUENCER = 30  # píxeles que retrocede el enemigo golpeado
DURACION_LIVE_STREAM = 3.0  # segundos de aggro forzado

# Periodista: rayo perforante / Fact-Checking
COLOR_RAYO_PERIODISTA = (140, 220, 255)
COLOR_RAYO_FACT_CHECK = (90, 255, 140)
TAMANIO_RAYO = 10
VELOCIDAD_RAYO = 900  # píxeles por segundo
LARGO_ESTELA_RAYO = 40  # píxeles de la línea dibujada detrás del rayo
GROSOR_ESTELA_RAYO = 4

# Candidato: onda expansiva radial / Debate Rebotante
COLOR_ONDA_CANDIDATO = COLOR_AMARILLO
GROSOR_ONDA = 3
RADIO_MAXIMO_ONDA = 90  # píxeles
DURACION_ONDA = 0.3  # segundos que tarda en expandirse
COLOR_PROYECTIL_REBOTANTE = (255, 140, 60)
ANGULOS_DEBATE_REBOTANTE = (-20, 0, 20)  # grados respecto a la mirada
MAXIMO_REBOTES = 3
TIEMPO_VIDA_REBOTANTE = 4.0  # segundos

# ----------------------------------------------------------------------
# Cuarto: piso, muros, puertas, grafitis y terminal
# ----------------------------------------------------------------------
ANCHO_CUARTO = 1000
ALTO_CUARTO = 560
CENTRO_CUARTO = (640, 360)
TAMANIO_BALDOSA = 40
COLOR_BALDOSA_A = (30, 27, 62)
COLOR_BALDOSA_B = (36, 33, 72)
COLOR_MURO = (52, 44, 98)
COLOR_MURO_LINEA = (78, 66, 134)  # juntas de los ladrillos
COLOR_MURO_BORDE = (104, 90, 170)
GROSOR_MURO = 18
ALTO_LADRILLO = 9
ANCHO_LADRILLO = 28
ANCHO_PUERTA = 80
GROSOR_PUERTA = 18
COLOR_PUERTA_BLOQUEADA = COLOR_MAGENTA
COLOR_PUERTA_ABIERTA = COLOR_TEAL
COLOR_PUERTA_SELLADA = (170, 130, 30)  # dorado oscuro: no es por enemigos
COLOR_X_PUERTA_SELLADA = (50, 35, 10)
GROSOR_X_PUERTA_SELLADA = 3
# Grafitis: texto girado y manchas, con transparencia, sobre el piso
COLOR_GRAFITI = (255, 56, 120, 70)
COLOR_MANCHA = (255, 56, 120, 34)
TAMANIO_FUENTE_GRAFITI = 40
TEXTOS_GRAFITI = ("SIN FUENTE", "COMPARTE YA", "URGENTE!!", "FAKE", "RT x1000", "#VIRAL")
# Terminal física del cuarto final (sprite + aviso de bloqueo)
MARGEN_TERMINAL_CUARTO = 24  # px entre el muro derecho y la terminal
COLOR_FONDO_TERMINAL_CUARTO = (18, 16, 40)
TEXTO_TERMINAL_BLOQUEADA = "Terminal bloqueada"
TEXTO_TERMINAL_LISTA = "Terminal lista"

# Mazmorra multi-cuarto: al cruzar una puerta el jugador aparece a esta
# distancia (px) de la puerta opuesta, hacia dentro del cuarto nuevo.
DISTANCIA_APARICION_PUERTA = 56
DURACION_MENSAJE_MAZMORRA = 2.0  # s de "Cuarto final desbloqueado" / "Limpia todos..."
COLOR_MENSAJE_MAZMORRA = COLOR_AMARILLO
POSICION_MENSAJE_MAZMORRA = (640, 112)  # centro: bajo el muro superior del cuarto

# ----------------------------------------------------------------------
# Mazmorra final: arena, jefe, charcos y "juice"
# ----------------------------------------------------------------------
ANCHO_ARENA = 1000
ALTO_ARENA = 540
CENTRO_ARENA = (640, 370)  # deja libre la franja superior para el HUD
TAMANIO_JEFE = 128  # hitbox del Flame Golem (el sprite mide 160x140)
COLOR_JEFE = COLOR_MORADO
COLOR_DESTELLO_JEFE = (255, 255, 255)
COLOR_ESCUDO_JEFE = (90, 230, 255)
GROSOR_ESCUDO_JEFE = 3
MARGEN_ESCUDO_JEFE = 10
PERIODO_PARPADEO_JEFE = 0.1  # s entre visible/invisible durante el cambio de fase
COLOR_PROYECTIL_JEFE = COLOR_MAGENTA
TAMANIO_PROYECTIL_JEFE = 12
ALFAS_ESTELA_JEFE = (150, 90, 40)  # de la posición más reciente a la más vieja
COLOR_CHARCO = (120, 230, 80)
ALFA_CHARCO_ACTIVO = 90
GROSOR_CONTORNO_CHARCO = 2
SHAKE_DURACION = 0.25
SHAKE_INTENSIDAD = 5  # px máximos de desplazamiento

# Barra de vida del jefe y textos de la mazmorra final (en el HUD)
RECT_BARRA_JEFE = (440, 40, 400, 12)  # x, y, ancho, alto
COLOR_BARRA_JEFE = COLOR_MAGENTA
COLOR_MARCA_FASE = COLOR_TEXTO_HUD
ANCHO_MARCA_FASE = 2
POSICION_MENSAJE_CENTRAL = (640, 112)  # centro del texto de derrota
COLOR_MENSAJE_VICTORIA = COLOR_TEAL
COLOR_MENSAJE_DERROTA = COLOR_MAGENTA
DURACION_MENSAJE = 2.5  # s que se muestra la derrota contra el jefe
ESPACIADO_ESTELA_JEFE = 9  # px entre posiciones guardadas de la estela
SEPARACION_INVOCACION = 70  # px a cada lado del jefe donde aparecen súbditos

# Invulnerabilidad del jugador tras un golpe
PERIODO_PARPADEO_INVULNERABLE = 0.08  # s entre visible/invisible

# ----------------------------------------------------------------------
# Pantallas de victoria (jefe) y derrota global
# ----------------------------------------------------------------------
COLOR_VELO_VICTORIA = (8, 20, 24, 200)  # RGBA: oscurece la arena detrás del panel
RECT_PANEL_VICTORIA = (340, 220, 600, 260)  # x, y, ancho, alto
COLOR_FONDO_PANEL_VICTORIA = COLOR_FONDO_PANEL
COLOR_BORDE_PANEL_VICTORIA = COLOR_TEAL
GROSOR_BORDE_PANEL_VICTORIA = 2
SEPARACION_LINEAS_VICTORIA = 44
COLOR_VELO_COLAPSO = (40, 6, 20, 210)
RECT_PANEL_COLAPSO = (340, 220, 600, 260)
COLOR_FONDO_PANEL_COLAPSO = (40, 18, 34)
COLOR_BORDE_PANEL_COLAPSO = COLOR_MAGENTA
GROSOR_BORDE_PANEL_COLAPSO = 2

# ----------------------------------------------------------------------
# Minimapa de la mazmorra (tecla M): panel en la esquina superior
# derecha del cuarto.
# ----------------------------------------------------------------------
ORIGEN_MINIMAPA = (1020, 98)  # esquina superior izquierda de la celda (0, 0)
TAMANIO_CELDA_MINIMAPA = 26
PASO_CELDA_MINIMAPA = 38  # distancia entre celdas vecinas (celda + pasillo)
COLOR_FONDO_MINIMAPA = (18, 16, 40)
MARGEN_FONDO_MINIMAPA = 10
COLOR_PASILLO_MINIMAPA = (80, 74, 130)
GROSOR_PASILLO_MINIMAPA = 3
COLOR_RUTA_MINIMAPA = COLOR_AMARILLO
GROSOR_RUTA_MINIMAPA = 4
GROSOR_BORDE_RUTA_MINIMAPA = 2  # contorno de los cuartos que están en la ruta
COLOR_TOXICIDAD_BAJA = (62, 230, 196)  # teal: toxicidad 0
COLOR_TOXICIDAD_ALTA = (255, 56, 120)  # magenta: toxicidad 100
FACTOR_OSCURO_NO_VISITADO = 0.35  # brillo de un cuarto aún no visitado
COLOR_CUARTO_ACTUAL = (255, 255, 255)
GROSOR_CUARTO_ACTUAL = 2
COLOR_MARCA_FINAL = (20, 20, 24)
COLOR_CANDADO = COLOR_AMARILLO
COLOR_FINAL_DESBLOQUEADO = (255, 255, 255)
TAMANIO_CANDADO = 12  # ancho del cuerpo del candado en px
GROSOR_CANDADO = 2

# ----------------------------------------------------------------------
# Mapa del mundo (tecla M en la escena CIUDAD): el grafo de calles en
# abstracto. Cada nodo se dibuja en ORIGEN + casilla * ESCALA, así el
# dibujo conserva la forma de la ciudad y el jugador cae en su lugar.
# ----------------------------------------------------------------------
# Misma escala en x y en y: el largo dibujado de cada calle es
# proporcional a su largo real (y a su peso base, ver grafo_ciudad.py).
# El origen centra la red de calles (columnas 6-55, filas 8-42) en la pantalla.
ORIGEN_MAPA_MUNDO = (244, -18)  # px de pantalla de la casilla (0, 0)
ESCALA_MAPA_MUNDO = (13, 13)  # px de pantalla por casilla, en x y en y
POSICION_ESCALA_MAPA = (1240, 606)  # extremo derecho de la barra de escala (junto al panel de la ruta)
COLOR_ESCALA_MAPA = COLOR_TEXTO_SECUNDARIO
# Dónde va el nombre de cada zona respecto a su círculo: (ancla del
# panel, dx, dy) desde el centro. Fuera del anillo de calles para que
# las líneas no lo crucen.
ETIQUETAS_MAPA_MUNDO = {
    "Plaza": ("topleft", 22, 18),
    "Colegio": ("midbottom", 0, -32),
    "Alcaldía": ("midbottom", 0, -32),
    "Hospital": ("midtop", 0, 32),
    "Empresa de Medios": ("midbottom", -40, -32),  # arriba (abajo está el panel de la ruta), sin tapar el peso de Medios-Este
}
RADIO_ZONA_MAPA = 22
RADIO_CRUCE_MAPA = 7
COLOR_ZONA_MAPA = (66, 60, 120)
COLOR_ZONA_ALCALDIA = COLOR_MORADO
COLOR_ZONA_ACTUAL = COLOR_TEAL
COLOR_ZONA_SELECCIONADA = COLOR_AMARILLO
GROSOR_ZONA_SELECCIONADA = 3
COLOR_CALLE = (70, 64, 120)
GROSOR_CALLE = 3
COLOR_CALLE_BLOQUEADA = COLOR_MAGENTA
COLOR_RUTA_SEGURA = COLOR_AMARILLO
GROSOR_RUTA_SEGURA = 6
RADIO_ETIQUETA_PESO = 13
GROSOR_BORDE_ETIQUETA_PESO = 2
COLOR_FONDO_ETIQUETA_PESO = COLOR_FONDO_PANEL
RECT_PANEL_RUTA = (40, 590, 760, 62)
POSICION_TEXTO_RUTA = (56, 598)
ESCALA_JUGADOR_MAPA_MUNDO = 2  # el jugador en el mapa del mundo, más chico
TITULO_MAPA_MUNDO = "Mapa del mundo"
POSICION_MENSAJE_MAPA = (640, 162)  # centro del mensaje del último resultado (bajo el chip de la ruta)
DURACION_MENSAJE_MAPA = 4.0  # s que se muestra el resultado al volver a la ciudad

# ----------------------------------------------------------------------
# Ciudad Nova (escena CIUDAD): casillas en pixel art, edificios, auras,
# barricadas, ruta sugerida y cintillo de noticias.
# ----------------------------------------------------------------------
ALTO_CINTILLO = 28  # (cintillo anterior; el actual es ALTO_CINTILLO_FINO)
# ----------------------------------------------------------------------
# HUD de la partida por bloques (src/ui/hud_partida.py; qué se ve, en
# src/ui/hud_visibilidad.py). Paneles chicos en las esquinas, mismo
# margen, misma transparencia y la misma fuente pequeña en todos.
# ----------------------------------------------------------------------
MARGEN_HUD = 12
ALFA_PANEL_HUD = 168
COLOR_PANEL_HUD = (14, 12, 34)
RECT_PANEL_VIDA_HUD = (MARGEN_HUD, 10, 300, 50)
POSICION_J1_HUD = (MARGEN_HUD + 20, 35)  # centro de "J1"
POSICION_CORAZONES_HUD = (MARGEN_HUD + 42, 15)
POSICION_HABILIDAD_HUD_COMPACTA = (MARGEN_HUD + 42, 42)
ANCHO_BARRA_HABILIDAD_HUD = 150
RECT_PANEL_COLAPSO_HUD = (1280 - MARGEN_HUD - 264, 10, 264, 50)
ANCHO_BARRA_COLAPSO_HUD = 176
POSICION_CONTADOR_HUD = (640, 12)  # midtop del chip "Enemigos · Cuartos"
POSICION_TITULO_HUD_COMPACTO = (640, 52)  # midtop del título (solo con HUD detallado)
POSICION_LINEA_MISION = (MARGEN_HUD, 68)  # topleft de la misión en una línea
ALTO_LINEA_MISION = 26
ANCHO_MAXIMO_LINEA_MISION = 420
DURACION_CONTROLES_AYUDA = 3.0  # s de barra de controles al entrar a una escena o con H
DURACION_MISION_ABIERTA = 3.0  # s que la misión se abre tras cambiar de destino con Tab
# Zona de pantalla donde se ve el mundo: entre el cintillo y la barra de controles.
# La ciudad ocupa toda la pantalla: el HUD (src/ui/hud_partida.py) flota
# encima en paneles semitransparentes en las esquinas.
RECT_VISTA_CIUDAD = (0, 0, 1280, 720)
# Cintillo de noticias: franja fina abajo, que no pisa el HUD ni los edificios.
ALTO_CINTILLO_FINO = 22
RECT_CINTILLO = (0, 720 - ALTO_CINTILLO_FINO, 1280, ALTO_CINTILLO_FINO)
ALFA_CINTILLO = 190
TITULO_CIUDAD = "Ciudad Nova"

# Casillas (paleta nocturna, misma familia que el piso de los cuartos)
COLOR_PASTO = (20, 38, 48)
COLOR_PASTO_BROTE = (30, 60, 64)
COLOR_PASTO_SOMBRA = (15, 28, 40)
COLOR_ACERA = (38, 35, 70)
COLOR_ACERA_JUNTA = (28, 26, 54)
COLOR_ACERA_BRILLO = (48, 45, 86)
COLOR_PLAZA = (46, 40, 84)
COLOR_PLAZA_ROMBO = (56, 50, 102)
COLOR_PLAZA_JUNTA = (34, 31, 64)
# Mosaico circular en el centro de la Plaza: anillos (radio en casillas, color)
ANILLOS_MOSAICO_PLAZA = ((3.2, (40, 70, 92)), (2.6, (30, 28, 58)), (2.2, (70, 56, 128)), (1.3, (30, 28, 58)),
                         (0.9, (62, 230, 196)), (0.6, (30, 28, 58)))
COLOR_ASFALTO = (24, 22, 40)
COLOR_ASFALTO_GRANO = (31, 29, 52)
COLOR_CARRIL = (150, 116, 50)  # amarillo apagado: la marca del carril no compite con el neón
COLOR_COPA = (22, 82, 76)
COLOR_COPA_BRILLO = (40, 124, 108)
COLOR_COPA_SOMBRA = (14, 52, 54)
COLOR_COPA_BORDE = (10, 34, 40)
COLOR_TRONCO = (64, 42, 54)
COLOR_SOMBRA_SUELO = (12, 24, 34)
COLOR_SOMBRA_ENTIDAD = (4, 5, 16, 120)  # RGBA: sombra bajo personajes y objetos
# Escenarios por lugar (src/ui/temas_mazmorra.py).
TEMA_POR_ZONA = {"Colegio": "colegio", "Hospital": "hospital", "Empresa de Medios": "medios", "Alcaldía": "servidor"}
Y_MUNDO_TEMA = 62  # bajo el HUD
ALTO_MUNDO_TEMA = 600  # hasta la barra de controles
COLOR_TEMA_NOVA_OSCURO = (150, 30, 96)
COLOR_TEMA_PANTALLA = ((120, 30, 60), (24, 84, 120), (64, 44, 130))
COLOR_TEMA_ECG = (90, 255, 170)
COLOR_TEMA_INFO = (40, 120, 170)

# Arte de mazmorra generado con Higgsfield,
# reducido a pixel art con tools/procesar_higgsfield.py y colocado por
# src/ui/decor_mazmorra.py. Los objetos son coberturas rompibles con hitbox
# (src/dungeon/coberturas.py; números en balance.py).
RUTA_MAZMORRAS = os.path.join("assets", "mazmorras")
CARPETA_ARTE_TEMA = {"colegio": "colegio", "hospital": "hospital", "medios": "medios", "servidor": "alcaldia"}
ESCALA_ARTE_MAZMORRA = 2  # 1 píxel de arte = 2 px de pantalla (la rejilla nativa de la imagen generada)
ESCALA_MURO_MAZMORRA = 1  # la franja del muro ya mide los 36 px de la cara
# Color base del piso por tema: la textura se MULTIPLICA sobre él, así la
# luz, la viñeta y las grietas de NOVA pintadas debajo siguen viéndose y el
# piso queda más oscuro que los personajes.
BASE_PISO_TEMA = {"hospital": (138, 150, 164), "medios": (196, 200, 220), "servidor": (176, 164, 190)}
TINTE_MURO_TEMA = {"hospital": (150, 166, 172), "medios": (210, 210, 228), "servidor": (176, 150, 160)}
FACTOR_PROPS_TEMA = {"colegio": 0.85, "hospital": 0.74, "medios": 0.86, "servidor": 0.8}  # < 1 oscurece
COLOR_SOMBRA_PROP = (4, 5, 16, 96)
BANDA_DECOR_MAZMORRA = 140  # px desde el muro: fuera de esa franja el piso queda libre para combatir
BANDA_DECOR_ARENA = 140  # la arena: las columnas (136 px) caben junto al muro y el centro (720x224) queda libre
SEPARACION_PROPS = 10  # px mínimos entre dos objetos
ZONA_LIBRE_TERMINAL = (300, 170)  # px junto al muro derecho, a media altura: la terminal y su rótulo
# Variantes de cuarto por tema: la semilla visual del cuarto elige una, así
# los cuartos de una mazmorra no son iguales. "aula" es el pack escolar
# comprado (src/ui/arte_colegio.py); "pack:<pieza>" pide una pieza de ese pack.
VARIANTES_CUARTO = {
    "colegio": ("aula", "biblioteca", "laboratorio"),
    "hospital": ("sala", "urgencias", "laboratorio"),
    "medios": ("redaccion", "estudio", "servidores"),
    "servidor": ("salon",),
}
# Reglas de colocación: (lugar, objetos, cantidad). Lugares: "fondo" (junto al
# muro de arriba), "costados" (izquierdo y derecho, por pares), "esquinas" (abajo)
# "sueltos" (al azar, solo dentro de la franja BANDA_DECOR desde los muros) y
# "centro" (las coberturas del medio del cuarto, por pares espejo: ver
# src/ui/plan_decor.py). Casi todos son sólidos y rompibles
# (src/dungeon/coberturas.py); los de balance.OBJETOS_SIN_HITBOX son adorno.
DECORADO_VARIANTE = {
    ("colegio", "biblioteca"): (
        ("fondo", ("estanteria", "estanteria", "ficus", "estanteria", "estanteria"), 8),
        ("costados", ("estanteria", "mesa_lectura", "estanteria"), 3),
        ("centro", ("mesa_lectura", "globo"), 4),
        ("esquinas", ("globo", "pack:maceta"), 2),
        ("sueltos", ("libros", "libros", "pack:mochila"), 4),
    ),
    ("colegio", "laboratorio"): (
        ("fondo", ("pizarra_movil", "pack:estante", "esqueleto", "pack:estante"), 5),
        ("costados", ("mesa_lab", "mesa_lab", "pack:casillero"), 3),
        ("centro", ("mesa_lab", "pack:pupitre"), 4),
        ("esquinas", ("ficus", "globo"), 2),
        ("sueltos", ("libros", "pack:mochila"), 3),
    ),
    ("hospital", "sala"): (
        ("fondo", ("gabinete", "monitor", "planta", "gabinete"), 5),
        ("costados", ("camilla", "suero", "camilla"), 3),
        ("centro", ("camilla", "carro"), 4),
        ("esquinas", ("biombo", "silla_ruedas"), 2),
        ("sueltos", ("carro", "contenedor"), 2),
    ),
    ("hospital", "urgencias"): (
        ("fondo", ("sillas_espera", "planta", "sillas_espera", "contenedor"), 5),
        ("costados", ("camilla", "monitor", "biombo"), 3),
        ("centro", ("sillas_espera", "carro"), 4),
        ("esquinas", ("silla_ruedas", "oxigeno"), 2),
        ("sueltos", ("carro", "suero"), 2),
    ),
    ("hospital", "laboratorio"): (
        ("fondo", ("mesa_lab", "gabinete", "mesa_lab", "oxigeno"), 5),
        ("costados", ("carro", "monitor", "gabinete"), 3),
        ("centro", ("mesa_lab", "contenedor"), 4),
        ("esquinas", ("planta", "contenedor"), 2),
        ("sueltos", ("suero",), 1),
    ),
    ("medios", "redaccion"): (
        ("fondo", ("escritorio_pc", "impresora", "escritorio_pc", "dispensador"), 5),
        ("costados", ("escritorio_pc", "silla_oficina", "escritorio_pc"), 3),
        ("centro", ("escritorio_pc", "impresora"), 4),
        ("esquinas", ("planta", "maletas"), 2),
        ("sueltos", ("silla_oficina", "impresora"), 2),
    ),
    ("medios", "estudio"): (
        ("fondo", ("pantalla", "mesa_noticias", "pantalla"), 3),
        ("costados", ("camara", "softbox", "aro_luz"), 3),
        ("centro", ("mesa_noticias", "camara"), 4),
        ("esquinas", ("maletas", "microfono"), 2),
        ("sueltos", ("silla_oficina",), 1),
    ),
    ("medios", "servidores"): (
        ("fondo", ("rack", "rack", "rack", "maletas", "rack", "rack"), 7),
        ("costados", ("rack", "escritorio_pc", "rack"), 3),
        ("centro", ("rack", "maletas"), 4),
        ("esquinas", ("maletas", "planta"), 2),
        ("sueltos", ("dispensador",), 1),
    ),
    ("servidor", "salon"): (
        ("fondo", ("columna", "bandera", "columna", "busto", "columna", "columna"), 8),
        ("costados", ("columna", "bloque_glitch", "columna", "terminal"), 4),
        ("centro", ("banca", "mesa_consejo"), 4),
        ("esquinas", ("palmera", "archivador"), 2),
        ("sueltos", ("cordon", "urna"), 2),
    ),
}
# Objetos que brillan (pantallas, LEDs, glitch): `dibujar_animado` los hace
# latir con un halo de este color. Son unos pocos blits por frame.
FOCO_PROP = {
    "monitor": (90, 255, 170), "escritorio_pc": (70, 220, 240), "pantalla": (70, 160, 255),
    "mesa_noticias": (70, 220, 240), "rack": (62, 230, 196), "terminal": (255, 56, 170),
    "bloque_glitch": (255, 56, 170), "archivador": (255, 56, 170),
}
ALFA_FOCO_MAXIMO = 70
# Coberturas rompibles (src/ui/cobertura_render.py): cómo se ven al dañarse.
COLOR_GRIETA_COBERTURA = (16, 12, 26)
GROSOR_GRIETA_COBERTURA = 2  # px: un píxel del arte a escala 2
GRIETAS_POR_ETAPA = (0, 3, 6)  # grietas dibujadas en cada etapa de daño
MUESCAS_POR_ETAPA = (0, 0, 5)  # pedazos que le faltan en el borde
FACTOR_ETAPA_COBERTURA = (1.0, 0.92, 0.8)  # se oscurece al dañarse
DESTELLO_GOLPE_COBERTURA = 70  # brillo que suma al recibir un impacto (0-255)
TEMBLOR_GOLPE_COBERTURA = 2  # px
ESCOMBROS_COBERTURA = 18  # pedazos que quedan en el piso al romperse
FACTOR_ESCOMBROS = 0.72
COLOR_POLVO_COBERTURA = (214, 204, 190)
POLVO_POR_IMPACTO = 3  # partículas
POLVO_AL_ROMPER = 16
# Vida de los personajes (src/entities/player.py, src/ui/enemigo_render.py).
DURACION_DESTELLO_DANIO = 0.14  # s de destello blanco al recibir un golpe
DURACION_RETROCESO_DISPARO = 0.09  # s del pequeño empujón visual al disparar
DISTANCIA_RETROCESO_DISPARO = 3  # px
AMPLITUD_PASO = 2  # px de rebote al caminar
FRECUENCIA_PASO = 11.0  # rad/s
COLOR_POSTE = (84, 80, 130)
COLOR_POSTE_OSCURO = (52, 48, 90)
COLOR_LAMPARA = (255, 226, 150)
COLOR_HALO_FAROLA = (255, 190, 90, 64)  # RGBA del halo de luz
RADIO_HALO_FAROLA = 78
DESPLAZAMIENTO_HALO_FAROLA = (0, -14)  # el halo se centra en la lámpara, no en la casilla
COLOR_MURO_CASA = (42, 38, 80)
COLOR_MURO_CASA_JUNTA = (34, 30, 66)
COLOR_TECHO_CASA = (56, 46, 96)
COLOR_TECHO_CASA_BRILLO = (78, 66, 132)
COLOR_TECHO_CASA_LINEA = (44, 36, 78)
COLOR_ALERO = (20, 18, 40)
COLOR_MARCO_VENTANA = (16, 14, 30)
COLOR_VENTANA_ENCENDIDA = (255, 204, 110)
COLOR_VENTANA_APAGADA = (30, 28, 56)
COLOR_VENTANA_NEON = (120, 220, 255)

# Edificios de zona: un color de neón por zona (rótulo, puerta y emblema)
# y una paleta sobria propia (PALETA_FACHADA_ZONA) para que no sean tres
# bloques iguales. COLOR_MURO_EDIFICIO queda para quien no tenga paleta.
COLOR_MURO_EDIFICIO = COLOR_ZONA_MAPA
COLOR_MURO_EDIFICIO_LINEA = (54, 48, 100)
COLOR_BASE_EDIFICIO = (34, 30, 64)
COLOR_COLUMNA = (150, 144, 200)
COLORES_NEON_ZONA = {
    "Colegio": COLOR_TEAL,
    "Hospital": COLOR_MAGENTA,
    "Empresa de Medios": COLOR_AMARILLO,
    "Alcaldía": COLOR_ZONA_ALCALDIA,
}
FACTOR_PUERTA_OSCURA = 0.35  # brillo de la puerta respecto al neón de la zona
# Muro, juntas, techo y base de cada edificio de zona en pixel art.
PALETA_FACHADA_ZONA = {
    "Hospital": {"muro": (150, 156, 164), "linea": (118, 124, 134), "techo": (62, 92, 98),
                 "techo_brillo": (84, 120, 126), "techo_linea": (48, 72, 78), "base": (70, 74, 84)},
    "Alcaldía": {"muro": (112, 102, 88), "linea": (88, 80, 70), "techo": (58, 50, 66),
                 "techo_brillo": (80, 70, 90), "techo_linea": (44, 38, 52), "base": (56, 50, 46)},
    "Empresa de Medios": {"muro": (52, 64, 82), "linea": (40, 50, 66), "techo": (36, 40, 52),
                          "techo_brillo": (54, 60, 76), "techo_linea": (28, 32, 42), "base": (30, 34, 46)},
}
ANCHO_ROTULO_CASILLAS = 6  # ancho de la placa del rótulo, en casillas
TAMANIO_FUENTE_ROTULO = 15
ALFA_BRILLO_ROTULO = 70  # resplandor detrás de las letras del rótulo

# Aura neón sobre cada edificio: color de toxicidad (verde -> rojo),
# alfa que pulsa entre MIN y MAX con el periodo dado.
GROSOR_AURA = 5
MARGEN_AURA = 8
ALFA_AURA_MIN = 120
ALFA_AURA_MAX = 230
PERIODO_AURA = 1.6  # s
CAPAS_AURA = 3  # bordes concéntricos cada vez más tenues

# Barricada (franjas amarillo/negro sobre la calle)
COLOR_BARRICADA_A = COLOR_AMARILLO
COLOR_BARRICADA_B = (16, 14, 30)
COLOR_PATA_BARRICADA = (110, 104, 150)

# Ruta sugerida (tecla G): línea punteada sobre las calles
COLOR_RUTA_CIUDAD = COLOR_AMARILLO
GROSOR_RUTA_CIUDAD = 4
LARGO_TRAZO_RUTA = 14
HUECO_TRAZO_RUTA = 10
RADIO_DESTINO_RUTA = 10

# Avisos de la ciudad (chips sobre la parte baja de la vista)
POSICION_AVISO_ENTRADA = (640, 624)
POSICION_AVISO_RUTA = (1280 - 12, 130)  # topright del chip "Ruta: ..." / "Sin ruta" (bajo el colapso y la reputación)
COLOR_AVISO_ENTRADA = COLOR_TEAL
COLOR_AVISO_SELLADA = COLOR_MAGENTA
TEXTO_AVISO_ENTRADA = "E: entrar a {zona} (Toxicidad {nivel:.0f})"
TEXTO_ALCALDIA_SELLADA = "Alcaldía sellada: purifica una mazmorra"
TEXTO_SIN_RUTA = "Sin ruta"
TEXTO_RUTA_DESTINO = "Ruta a {destino}  ·  costo {costo:g}"

# Cintillo "Breaking News Civitas"
ETIQUETA_CINTILLO = "BREAKING NEWS CIVITAS"
COLOR_FONDO_CINTILLO = COLOR_FONDO_PANEL
COLOR_ETIQUETA_CINTILLO = COLOR_MAGENTA
COLOR_TEXTO_CINTILLO = COLOR_TEXTO_HUD
VELOCIDAD_CINTILLO = 45  # px/s hacia la izquierda (lento: se lee de reojo)
SEPARADOR_CINTILLO = "   ·   "

# Fundido corto al entrar y salir de un edificio
DURACION_FUNDIDO = 0.35  # s
COLOR_FUNDIDO = COLOR_FONDO

# ----------------------------------------------------------------------
# Mira del apuntado con mouse (se dibuja sobre el HUD, sin sacudida)
# ----------------------------------------------------------------------
COLOR_MIRA = COLOR_TEAL
RADIO_MIRA = 9
GROSOR_MIRA = 2
LARGO_CRUZ_MIRA = 5  # px de cada brazo de la cruz que sale del círculo
COLOR_LINEA_APUNTADO = (62, 230, 196, 70)  # RGBA: línea tenue jugador -> mira
GROSOR_LINEA_APUNTADO = 1
# Opacidad del cono ajustable (pestaña CONTROLES): 100% = este alfa. El
# 40% predeterminado da el alfa 46 de COLOR_CONO_APUNTADO.
ALFA_MAXIMO_CONO = 115
ANGULO_CONO_VISTA_PREVIA = 14  # grados a cada lado en la vista previa de los ajustes

# ----------------------------------------------------------------------
# Pantalla de inicio: paleta retrofuturista (negro, azul noche, violeta
# neón y cian de acento)
# ----------------------------------------------------------------------
COLOR_CIAN_NEON = (80, 220, 255)
COLOR_MENU_SELECCION = (196, 120, 255)  # violeta neón: foco, títulos, bordes activos
COLOR_RESPLANDOR_MENU = (150, 70, 255)
COLOR_MENU_PULSADO = (150, 80, 240)
COLOR_TEXTO_PULSADO = (20, 8, 40)
COLOR_TEXTO_DESHABILITADO = (88, 84, 120)
COLOR_FONDO_MENU = (8, 6, 24, 205)  # RGBA: panel detrás de las opciones
COLOR_BORDE_MENU = (84, 60, 140)
COLOR_ENGRANAJE = (176, 170, 214)
TAMANIO_FUENTE_MENU = 24

# Título CIVITAS (src/ui/titulo_civitas.py)
CENTRO_Y_TITULO = 0.2  # fracción del alto de la pantalla
ESCALA_TITULO = 13  # px por píxel de letra (5x7)
COLOR_TITULO = (176, 96, 255)
COLOR_TITULO_LUZ = (226, 184, 255)
COLOR_TITULO_SOMBRA = (52, 20, 96)
COLOR_RESPLANDOR_TITULO = (140, 50, 255)
RADIO_RESPLANDOR_TITULO = 14
COLOR_GLITCH_CIAN = (30, 190, 230)
COLOR_GLITCH_MAGENTA = (230, 40, 150)
COLOR_DESTELLO_TITULO = (60, 44, 84)
INTERVALO_GLITCH_TITULO = (2.5, 6.0)  # s entre glitches (al azar)
DURACION_GLITCH_TITULO = 0.22
SEPARACION_CROMATICA_TITULO = (3, 7)  # px
DESPLAZAMIENTO_FRANJA_TITULO = (6, 18)  # px
PASO_SCANLINES_TITULO = 4  # una fila oscura cada 4 px
BRILLO_SCANLINES_TITULO = 175  # 0-255: brillo que conserva la fila oscura

# Opciones del menú (src/ui/menu_principal_render.py)
INICIO_OPCIONES_MENU = 0.39  # y de la primera opción, fracción del alto
PASO_OPCIONES_MENU = 50
ANCHO_OPCION_MENU = 360
ALTO_OPCION_MENU = 42
DURACION_PULSADO_MENU = 0.14  # s que se ve la opción pulsada antes de actuar
DURACION_REALCE_MENU = 0.12  # s de la animación de entrada al seleccionar
DESLIZAMIENTO_OPCION_MENU = 14  # px desde los que entra la opción seleccionada
PULSO_OPCION_MENU = 4.0  # rad/s del pulso de brillo de la opción seleccionada
RADIO_RESPLANDOR_MENU = 6
LADO_BOTON_ENGRANAJE = 52
MARGEN_BOTON_ENGRANAJE = 22
ESCALA_ENGRANAJE = 3
GIRO_ENGRANAJE = 90  # grados/s mientras tiene el foco
TAMANIO_PANEL_VISTA = (760, 360)  # EXTRAS / CRÉDITOS
CENTRO_Y_PANEL_VISTA = 0.6
COLUMNA_CREDITOS = 220  # x (desde el borde del panel) donde empiezan los valores

# Modal de ajustes (src/ui/ajustes_render.py)
TAMANIO_MODAL_AJUSTES = (900, 520)
CENTRO_Y_MODAL_AJUSTES = 0.47
DURACION_TRANSICION_MODAL = 0.18
DESPLAZAMIENTO_ENTRADA_MODAL = 24  # px desde los que sube el modal al abrirse
ALFA_VELO_MODAL = 153  # 60% de negro sobre el fondo
REDUCCION_DESENFOQUE_MODAL = 4  # el fondo se reduce a 1/4 y se vuelve a ampliar
COLOR_FONDO_MODAL = (12, 10, 30)
COLOR_FONDO_MODAL_ALFA = (12, 10, 30, 225)
COLOR_BORDE_MODAL_INTERIOR = (40, 90, 120)
COLOR_FILA_ENFOCADA = (34, 22, 66)
COLOR_PESTANA_ACTIVA = (60, 34, 112)
COLOR_FONDO_VISTA_PREVIA = (18, 16, 40)
ANCHO_BOTON_CERRAR = 130
ANCHO_PESTANA = 190
ALTO_FILA_AJUSTES = 56
ALTO_ZONA_INFERIOR_AJUSTES = 52  # notas de audio o muestras de color bajo las filas
ANCHO_ETIQUETA_AJUSTES = 300
ANCHO_ETIQUETA_COLUMNA = 196  # filas de la columna derecha (cono, en la vista MANDO)
ANCHO_ZONA_MANDO = 450
SEGMENTOS_SLIDER = 20
COLOR_SEGMENTO_ACTIVO = (164, 90, 255)
COLOR_SEGMENTO_LUZ = (214, 170, 255)
COLOR_SEGMENTO_INACTIVO = (36, 30, 66)
COLOR_CUERPO_MANDO = (34, 30, 64)
COLOR_BORDE_MANDO = (110, 80, 180)
COLOR_LINEA_GUIA_MANDO = (70, 110, 150)
COLORES_BOTONES_PS = {"✕": (120, 170, 255), "○": (255, 90, 110), "□": (230, 130, 220), "△": (80, 220, 170)}

# Ciudad animada del fondo (src/ui/fondo_ciudad.py). Velocidades en px/s
# de pantalla; tamaños de edificios en píxeles de la baja resolución.
SEMILLA_FONDO_CIUDAD = 2026  # misma ciudad en cada arranque
ESCALA_PIXEL_FONDO = 3
COLOR_CIELO_ARRIBA = (6, 5, 22)
COLOR_CIELO_HORIZONTE = (46, 18, 82)
COLOR_NUBE = (14, 12, 40)
COLOR_BORDE_NUBE = (32, 26, 76)
CANTIDAD_NUBES = 9
COLOR_ESTRELLA = (120, 120, 190)
CANTIDAD_ESTRELLAS = 24
COLOR_BRUMA = (255, 60, 170)
ALFA_BRUMA = 70
INICIO_BRUMA = 0.45  # la bruma empieza a esta fracción del alto
COLOR_LUZ_ANTENA = (255, 50, 70)
CAPAS_FONDO_CIUDAD = (
    {   # lejana: siluetas azules con pocas ventanas
        "velocidad": 5, "ancho": (10, 26), "alto": (90, 175), "hueco": (0, 3),
        "cuerpo": (22, 24, 64), "borde": (40, 46, 100), "cornisa": None,
        "ventanas": ((44, 52, 120), (64, 44, 116)), "paso_ventana": 3, "densidad_ventanas": 0.18,
        "prob_antena": 0.25, "prob_letrero": 0.0,
    },
    {   # media: torres azul eléctrico con cornisa cian
        "velocidad": 12, "ancho": (14, 34), "alto": (70, 150), "hueco": (1, 6),
        "cuerpo": (30, 38, 110), "borde": (70, 120, 220), "cornisa": (90, 220, 255),
        "ventanas": ((90, 140, 255), (150, 190, 255), (255, 80, 170)), "paso_ventana": 3,
        "densidad_ventanas": 0.3, "prob_antena": 0.35, "prob_letrero": 0.15,
    },
    {   # cercana: edificios oscuros con borde magenta y letreros holográficos
        "velocidad": 26, "ancho": (24, 48), "alto": (45, 120), "hueco": (2, 10),
        "cuerpo": (16, 14, 48), "borde": (130, 44, 170), "cornisa": (200, 70, 200),
        "ventanas": ((255, 90, 180), (255, 140, 90), (120, 90, 220)), "paso_ventana": 4,
        "densidad_ventanas": 0.16, "prob_antena": 0.2, "prob_letrero": 0.6,
    },
    {   # primer plano: azoteas casi negras
        "velocidad": 48, "ancho": (30, 80), "alto": (10, 30), "hueco": (0, 14),
        "cuerpo": (9, 7, 24), "borde": (70, 30, 100), "cornisa": (110, 40, 140),
        "ventanas": ((60, 30, 90),), "paso_ventana": 6, "densidad_ventanas": 0.05,
        "prob_antena": 0.3, "prob_letrero": 0.0,
    },
)
# Letreros holográficos: textos del universo del juego.
TEXTOS_LETREROS = ("VERIFICA", "#VIRAL", "FAKE?", "REPORTA", "TRENDING", "FUENTE?", "LIKE x1000",
                   "NOTICIAS 24H", "CIVITAS", "VOTA")
COLORES_LETREROS = ((255, 56, 120), (255, 80, 80), (62, 230, 240), (200, 110, 255))
COLOR_FONDO_LETRERO = (24, 10, 34)
COLOR_LETRERO_APAGADO = (10, 6, 20, 170)  # RGBA encima del letrero que parpadea
TAMANIO_FUENTE_LETRERO = 13
PROB_LETRERO_VERTICAL = 0.35
LETRAS_MAXIMAS_LETRERO_VERTICAL = 6  # textos más largos van siempre en horizontal
INTERVALO_PARPADEO_LETRERO = (0.8, 2.5)  # s entre parpadeos
DURACION_PARPADEO_LETRERO = 0.14
# Naves: una por profundidad; "capa" = se dibuja justo encima de esa capa.
PROFUNDIDADES_NAVES = (
    {"capa": 0, "escala": 2, "velocidad": (35, 55), "altura": (0.12, 0.35), "largo_estela": 24},
    {"capa": 0, "escala": 2, "velocidad": (40, 60), "altura": (0.1, 0.3), "largo_estela": 24},
    {"capa": 1, "escala": 3, "velocidad": (70, 100), "altura": (0.15, 0.45), "largo_estela": 40},
    {"capa": 2, "escala": 4, "velocidad": (130, 180), "altura": (0.2, 0.5), "largo_estela": 70},
)
ESPERA_MAXIMA_NAVE = 6.0  # s de pausa máxima antes de volver a cruzar
COLOR_ESTELA_NAVE = COLOR_CIAN_NEON
ALFA_ESTELA_NAVE = 170
# Lluvia
CANTIDAD_GOTAS_LLUVIA = 120
VELOCIDAD_LLUVIA = (520, 760)
LARGO_GOTA_LLUVIA = (8, 16)
INCLINACION_LLUVIA = 0.18  # px en x por px en y
COLORES_LLUVIA = ((70, 80, 170), (100, 90, 200), (60, 120, 200))

# ----------------------------------------------------------------------
# Audio (src/audio/gestor_audio.py, el único que toca el mezclador). Todo archivo
# vive en assets/audio/ y se pide por su ID: SONIDOS[id] = (ruta,
# categoría) y MUSICA[id] = ruta. Si falta un archivo o no hay
# dispositivo de audio, ese ID simplemente no suena (nunca se cae).
# Volúmenes y ganancias por categoría e ID: balance.py.
# Elección evento por evento (pack nuevo Bitcade vs. audio propio de
# tools/generar_audio.py): docs/ARQUITECTURA.md, sección de audio.
# ----------------------------------------------------------------------
RUTA_AUDIO = os.path.join("assets", "audio")
CATEGORIA_MUSICA = "musica"
CATEGORIA_SFX = "sfx"
CATEGORIA_UI = "ui"
CATEGORIA_CINEMATICA = "cinematica"  # banda sonora completa de una película (con voces)
PISTAS_CINEMATICA = frozenset({"prologo_umbral"})  # suenan con el volumen general, no el de música


def _sfx(carpeta, archivo):
    return os.path.join(RUTA_AUDIO, "sfx", carpeta, archivo)


SONIDOS = {
    # Jugador: disparo y habilidad de cada rol, dash, golpe recibido.
    "disparo_ciudadano": (_sfx("jugador", "bitcade_laser_pew.wav"), CATEGORIA_SFX),
    "disparo_influencer": (_sfx("jugador", "bitcade_jump_double.wav"), CATEGORIA_SFX),
    "disparo_periodista": (_sfx("jugador", "bitcade_laser_blaster.wav"), CATEGORIA_SFX),
    "disparo_candidato": (_sfx("jugador", "bitcade_explosion_crunch.wav"), CATEGORIA_SFX),
    "habilidad_ciudadano": (_sfx("jugador", "bitcade_magic_teleport.wav"), CATEGORIA_SFX),
    "habilidad_influencer": (_sfx("jugador", "bitcade_magic_spell.wav"), CATEGORIA_SFX),
    "habilidad_periodista": (_sfx("jugador", "bitcade_laser_charged.wav"), CATEGORIA_SFX),
    "habilidad_candidato": (_sfx("jugador", "bitcade_jump_spring.wav"), CATEGORIA_SFX),
    "habilidad_lista": (_sfx("jugador", "bitcade_powerup_charge.wav"), CATEGORIA_SFX),
    "dash": (_sfx("jugador", "bitcade_jump_classic.wav"), CATEGORIA_SFX),
    "jugador_herido": (_sfx("jugador", "bitcade_hit_hurt.wav"), CATEGORIA_SFX),
    # Enemigos.
    "impacto_enemigo": (_sfx("enemigos", "bitcade_hit_punch.wav"), CATEGORIA_SFX),
    "muerte_perseguidor": (_sfx("enemigos", "bitcade_hit_defeated.wav"), CATEGORIA_SFX),
    "muerte_tirador": (_sfx("enemigos", "bitcade_explosion_small.wav"), CATEGORIA_SFX),
    "muerte_curandero": (_sfx("enemigos", "bitcade_hit_defeated.wav"), CATEGORIA_SFX),
    "disparo_tirador": (_sfx("enemigos", "glitch.wav"), CATEGORIA_SFX),
    "curacion": (_sfx("enemigos", "bitcade_magic_sparkle.wav"), CATEGORIA_SFX),
    # Jefe.
    "jefe_rafaga": (_sfx("jefe", "viral.wav"), CATEGORIA_SFX),
    "jefe_fase": (_sfx("jefe", "bitcade_explosion_big.wav"), CATEGORIA_SFX),
    "jefe_escudo_roto": (_sfx("jefe", "bitcade_hit_sword.wav"), CATEGORIA_SFX),
    "jefe_derrotado": (_sfx("jefe", "bitcade_explosion_big.wav"), CATEGORIA_SFX),
    # Mazmorra: puertas, cuartos, gracia de entrada.
    "puerta": (_sfx("ciudad", "bitcade_land_thud.wav"), CATEGORIA_SFX),
    # Coberturas: una bala que pega en un mueble y el mueble que se rompe.
    "impacto_cobertura": (_sfx("ciudad", "bitcade_land_thud.wav"), CATEGORIA_SFX),
    "cobertura_rota": (_sfx("enemigos", "bitcade_explosion_small.wav"), CATEGORIA_SFX),
    "puerta_sellada": (_sfx("ui", "bitcade_ui_error.wav"), CATEGORIA_UI),
    "cuarto_liberado": (_sfx("ui", "bitcade_jingle_level_up.wav"), CATEGORIA_SFX),
    "cuarto_final_desbloqueado": (_sfx("ui", "bitcade_powerup_extra_life.wav"), CATEGORIA_SFX),
    "gracia_entrada": (_sfx("ui", "bitcade_ui_confirm.wav"), CATEGORIA_UI),
    # Ciudad Nova.
    "transicion": (_sfx("ciudad", "transicion.wav"), CATEGORIA_SFX),
    "barricada": (_sfx("ciudad", "bitcade_land_thud.wav"), CATEGORIA_SFX),
    "ruta": (_sfx("ui", "bitcade_ui_confirm.wav"), CATEGORIA_UI),
    "noticia": (_sfx("ui", "notificacion.wav"), CATEGORIA_UI),
    # Minijuego de decisión.
    "tick": (_sfx("ui", "bitcade_ui_select.wav"), CATEGORIA_UI),
    "decision_buena": (_sfx("ui", "bitcade_jingle_victory.wav"), CATEGORIA_SFX),
    "decision_mala": (_sfx("jefe", "bitcade_explosion_big.wav"), CATEGORIA_SFX),
    "error_decision": (_sfx("ui", "bitcade_ui_error.wav"), CATEGORIA_UI),
    # Interfaz (src/ui/navegacion.py) y modo historia.
    "navegar": (_sfx("ui", "bitcade_ui_select.wav"), CATEGORIA_UI),
    "confirmar": (_sfx("ui", "bitcade_ui_confirm.wav"), CATEGORIA_UI),
    "volver": (_sfx("ui", "bitcade_ui_back.wav"), CATEGORIA_UI),
    "notificacion": (_sfx("ui", "notificacion.wav"), CATEGORIA_UI),
    "evidencia": (_sfx("ui", "bitcade_coin_bell.wav"), CATEGORIA_UI),
    "mision": (_sfx("ui", "bitcade_powerup_rise.wav"), CATEGORIA_UI),
    "reputacion_sube": (_sfx("ui", "bitcade_coin_ring.wav"), CATEGORIA_UI),
    "reputacion_baja": (_sfx("ui", "reputacion_baja.wav"), CATEGORIA_UI),
    "victoria": (_sfx("ui", "bitcade_jingle_victory.wav"), CATEGORIA_SFX),
    "derrota": (_sfx("ui", "bitcade_jingle_game_over.wav"), CATEGORIA_SFX),
    "crisis": (_sfx("ui", "crisis.wav"), CATEGORIA_SFX),
    "redencion": (_sfx("ui", "redencion.wav"), CATEGORIA_SFX),
    "glitch": (_sfx("enemigos", "glitch.wav"), CATEGORIA_SFX),
    "viral": (_sfx("jefe", "viral.wav"), CATEGORIA_SFX),
}


def _musica(archivo):
    return os.path.join(RUTA_AUDIO, "musica", archivo)


# Una pista en bucle por momento del juego (Main._pista_para).
MUSICA = {
    "menu": _musica("bitcade_title.ogg"),
    "lobby": _musica("bitcade_overworld.ogg"),
    "ciudad": _musica("bitcade_town.ogg"),
    "combate": _musica("bitcade_battle.ogg"),
    "jefe": _musica("bitcade_boss.ogg"),
    "misterio": _musica("bitcade_cave.ogg"),
    "decision": _musica("decision.wav"),
    "crisis": _musica("crisis.wav"),
    "redencion": _musica("redencion.wav"),
    "victoria": _musica("victoria.wav"),
    "derrota": _musica("derrota.wav"),
    # Banda sonora completa del prólogo «La ciudad que perdió» (música, voces y
    # efectos ya mezclados, sincronizada con assets/story/video/prologo_umbral).
    "prologo_umbral": _musica("prologo_umbral.ogg"),
}
FUNDIDO_MUSICA_MS = 1400  # fundido cruzado entre pistas
CANALES_MEZCLADOR = 32  # canales simultáneos de pygame.mixer

# ----------------------------------------------------------------------
# Hojas de sprites (arte real, pixel art hecho con Pixelbolt). Cada hoja
# es <carpeta>/<id>.png (tira horizontal a resolución nativa) con su
# <id>.atlas.json al lado (rect y duración de cada cuadro, animaciones).
# Si falta el PNG se usa el pixel art dibujado en código (sprites.py).
# Las recetas editables viven en assets/sprites/fuentes/<id>.pixel.json.
# ----------------------------------------------------------------------
RUTA_SPRITES_JUGADORES = os.path.join("assets", "sprites", "jugadores")  # <rol>.png (arte de Higgsfield)
# Hojas del jugador hechas desde los personajes de Higgsfield
# (tools/generar_jugadores_higgsfield.py): cuadros de ALTO_JUGADOR_HF px de
# alto, el doble que las hojas viejas de 16x20, por eso sprites.sprite_jugador
# las dibuja a la mitad de la escala pedida (redondeando hacia arriba).
# <rol>.partes.png marca con estos colores qué píxel es de qué parte.
ALTO_JUGADOR_HF = 40
CORTE_CABEZA_JUGADOR = 0.5  # vista previa del vestidor: arriba (pelo y cara) / abajo (ropa)
COLOR_PARTE_JUGADOR = {
    "piel": (255, 0, 0),
    "pelo": (0, 255, 0),
    "ropa": (0, 0, 255),
    "pantalon": (255, 255, 0),
    "zapatos": (255, 0, 255),
}
RUTA_SPRITES_JEFE = os.path.join("assets", "sprites", "jefe")
ID_SPRITE_JEFE = "servidor_central"  # 24x24
RUTA_SPRITES_RETRATOS = os.path.join("assets", "sprites", "retratos")  # <rol>.png (ilustración grande)
ANIMACION_CAMINAR = "caminar"  # jugadores y enemigos
ANIMACION_DASH = "dash"  # jugadores (un solo cuadro)
ANIMACION_JEFE_IDLE = "idle"
ANIMACION_JEFE_FURIA = "furia"  # fase 3
ESCALA_SPRITE_JEFE = 4  # hoja anterior: 24 px * 4 = 96 px
# Jefe final con arte "enemigos 2.0": Flame Golem (32x28 nativo). Si es None
# o falta el PNG se usa la hoja anterior del Servidor Central.
JEFE_V2 = "Flame Golem"
ESCALA_JEFE_V2 = 5  # 160x140 px
DURACION_CUADRO_JEFE_V2 = 0.12
DURACION_CUADRO_JEFE_V2_FURIA = 0.06  # en fase 3 camina el doble de rápido
ALTO_RETRATO_SELECCION = 92  # alto del retrato en la tarjeta de selección
# ----------------------------------------------------------------------
# Packs de arte en hojas (src/ui/cargador_assets.py): se recortan por
# rect y se dibujan a ESCALA_ARTE_PACKS. Están hechos para celdas de
# 32-64 px, así que a escala 1 ya tienen el tamaño de mundo correcto
# junto a casillas de 16 px * ESCALA_PIXEL (un banco ~ una casilla, un
# pupitre ~ un jugador). Si falta la hoja, quien los pide dibuja su
# placeholder de siempre (pixel art en código).
# ----------------------------------------------------------------------
ESCALA_ARTE_PACKS = 1
# Proporción de los props urbanos frente al jugador (48x60 px). El pack
# viene dibujado para personajes de ~32 px: a escala 1 una farola (62 px)
# medía lo mismo que el jugador. Lo que es un poste (farolas, paradas)
# va al doble: una farola mide dos jugadores. El mobiliario (bancas,
# papeleras, mesas) va a 1.5: una banca sienta a dos y llega al pecho.
# Lo que ya tenía buen tamaño (hidrante, macetas grandes) queda en 1.
ESCALA_PROP_URBANO_PREDETERMINADA = 1.5
ESCALA_PROP_URBANO = {
    "farola": 2, "farola_ornamental": 2, "farola_baja": 2, "farola_curva": 2,
    "farola_jardin": 2, "farola_farol": 2, "casita_pajaros": 2,
    "hidrante": 1, "maceta_grande": 1, "maceta_planta": 1, "basurero_verde": 1,
    "armario_electrico": 1, "barricada": 1, "parrilla": 1,
    "cerca_madera": 1.25,  # a 1.5 se montaba sobre la parrilla de al lado
}
# Props urbanos ("Modern Urban RPG Pixel Asset Pack"): hoja de 15x16
# celdas de 64 px. Nombre -> (columna, fila) de su celda.
RUTA_PROPS_URBANOS = os.path.join("assets", "sprites", "props", "props_urbanos.png")
CELDA_PROPS_URBANOS = 64
PROPS_URBANOS = {
    "farola": (11, 1),
    "barricada": (10, 1),
    "banca": (6, 0),
    "basurero": (2, 1),
    "reciclaje": (14, 0),
    "parada_bus": (14, 1),
    "maquina": (12, 1),
    "hidrante": (7, 15),
    "jardinera": (7, 0),
    "maceta_grande": (9, 2),
    "buzon": (4, 0),
    "bicicletero": (4, 1),
    "bicicleta": (12, 15),
    "cartelera": (3, 1),
    # Ciudad por zonas (src/dungeon/zonas_ciudad.py): farolas por zona y mobiliario propio.
    "farola_ornamental": (3, 0),
    "farola_baja": (8, 0),
    "farola_curva": (11, 0),
    "farola_jardin": (8, 2),
    "farola_farol": (13, 10),
    "banca_corta": (6, 1),
    "banca_parada": (0, 1),
    "cartel_parada": (6, 15),
    "bebedero": (13, 1),
    "bebedero_pajaros": (2, 0),
    "casita_pajaros": (7, 1),
    "maceta_planta": (10, 0),
    "maceta_flores": (8, 1),
    "aire_acondicionado": (9, 1),
    "basurero_verde": (4, 2),
    "buzon_azul": (5, 2),
    "cerca_madera": (6, 2),
    "carrito_comida": (7, 2),
    "letrero_bienvenida": (10, 2),
    "mesa_cafe": (11, 2),
    "barril": (12, 2),
    "parrilla": (2, 2),
    "mesa_sombrilla": (9, 0),
    "kiosco_digital": (5, 8),
    "armario_electrico": (14, 8),
    "bolardo": (10, 8),
    "jardinera_flores": (12, 14),
    "jardinera_larga": (4, 7),
    "toldo": (13, 3),
}
# Árboles (pack Trees_Vol2, reducidos a sprites nativos de 18-48 px de
# alto; arbol_<número del pack>.png). Se dibujan a ESCALA_PIXEL, como el
# resto del pixel art, apoyados en el borde inferior de su casilla.
RUTA_ARBOLES = os.path.join("assets", "sprites", "props", "arboles")
ESCALA_ARBOLES = ESCALA_PIXEL
# Lobby: siluetas de árboles al fondo (números del pack, escala entera y
# x relativa al ancho de pantalla). Se tiñen con la paleta neón nocturna.
ARBOLES_LOBBY = ((24, 10, -0.01), (1, 13, 0.035), (18, 10, 1.01), (3, 13, 0.965))
COLOR_SILUETA_LOBBY = (54, 30, 104)
COLOR_BORDE_SILUETA_LOBBY = (120, 70, 210)
ALFA_SILUETA_LOBBY = 150
AMPLITUD_BALANCEO_LOBBY = 0.9  # grados que se mecen las siluetas
# Edificios de Ciudad Nova: de qué arte sale cada fachada y con qué escala
# entera se dibuja (vecino más cercano, sin suavizado). La huella en
# casillas vive en ciudad_mapa.EDIFICIOS; la imagen mide exactamente
# huella * TAM_CASILLA y se ancla por su base-centro a la base de la huella.
ANCLA_EDIFICIOS = "midbottom"
ARTE_EDIFICIOS = {
    "Colegio": {"fuente": "pack_colegio", "escala": 2},  # tejas de 32 px: 2 px de pantalla por píxel
    # Los packs cyberpunk no traen edificios completos: pixel art en código,
    # cada uno con su paleta sobria (PALETA_FACHADA_ZONA).
    # Fachadas generadas con Higgsfield con el pack escolar como referencia de
    # estilo (tools/procesar_higgsfield.py fachada): miden exactamente la huella
    # / escala. Si falta el PNG, vuelve el pixel art en código.
    "Hospital": {"fuente": "fachada", "ruta": os.path.join("assets", "ciudad", "fachadas", "hospital.png"), "escala": 2},
    "Empresa de Medios": {"fuente": "fachada", "ruta": os.path.join("assets", "ciudad", "fachadas", "medios.png"),
                          "escala": 2},
    "Alcaldía": {"fuente": "fachada", "ruta": os.path.join("assets", "ciudad", "fachadas", "alcaldia.png"), "escala": 2},
}
FACTOR_FACHADA_GENERADA = 0.82  # de noche: un poco en penumbra, como la del Colegio
COLOR_PUERTA_COLEGIO = (34, 46, 70)
COLOR_MARCO_PUERTA_COLEGIO = (84, 62, 44)
COLOR_TECHO_COLEGIO = (40, 34, 56)

# Colegio ("Traditional School Asset pack 32x32", assets/colegio/).
# Pieza -> (archivo, rect en px de la hoja).
RUTA_COLEGIO = os.path.join("assets", "colegio")
PIEZAS_COLEGIO = {
    "piso": ("suelos.png", (64, 0, 32, 32)),  # tablones de madera
    "muro_ventana": ("muros_autotile.png", (64, 96, 64, 64)),  # pared crema con ventana
    "muro_liso": ("muros_autotile.png", (0, 96, 64, 64)),
    "muro_ventana_alta": ("muros_autotile.png", (192, 96, 64, 64)),
    "pupitre": ("props.png", (96, 55, 32, 39)),
    "silla": ("props.png", (68, 50, 22, 44)),
    "escritorio": ("props.png", (4, 32, 57, 64)),
    "pizarra": ("props.png", (128, 192, 64, 32)),
    "reloj": ("props.png", (100, 3, 23, 23)),
    "casillero": ("props.png", (1, 250, 30, 70)),
    "estante": ("props.png", (168, 394, 48, 86)),
    "maceta": ("props.png", (289, 201, 30, 42)),
    "mochila": ("props.png", (36, 129, 24, 30)),
}
# Los muebles del pack (pupitre 32x39, casillero 30x70...) están hechos para
# personajes de 32 px; el jugador mide 48x60. A 1.5 un pupitre llega a la
# cintura y un casillero es más alto que él, como el resto de los objetos.
ESCALA_MUEBLES_COLEGIO = 1.5
PIEZAS_COLEGIO_DE_MURO = ("pizarra", "reloj")  # cuelgan de la cara del muro: escala 1, sin hitbox
# El piso del aula se multiplica sobre el piso pintado (que ya trae luz,
# viñeta y grietas de NOVA): este gris neutro es su base. Los muebles se
# oscurecen un poco para que personajes y balas se lean siempre encima.
COLOR_BASE_PISO_COLEGIO = (124, 116, 122)
FACTOR_MUEBLES_COLEGIO = 0.82
FACTOR_FACHADA_COLEGIO = 0.9  # la pared real del Colegio en la ciudad, un poco en penumbra
# Cuarto: piso y muro (cuarto.png, 16x16 por cuadro), puertas (puerta.png,
# 27x6: abierta / bloqueada / sellada) y charco tóxico (charco.png, 30x30:
# aviso / activo). Sin el PNG se dibujan con formas, como antes.
RUTA_SPRITES_CUARTO = os.path.join("assets", "tiles", "interior")
ID_SPRITE_CUARTO = "cuarto"
ID_SPRITE_PUERTA = "puerta"
ID_SPRITE_CHARCO = "charco"
CUADROS_PISO = ("piso_a", "piso_b")  # tablero: (fila + columna) par / impar
CUADROS_PISO_DETALLE = ("piso_grieta", "piso_rejilla")  # reemplazan a una baldosa de vez en cuando
PROBABILIDAD_PISO_DETALLE = 0.06
CUADRO_MURO = "muro"
TAMANIO_BALDOSA_HOJA = 16 * ESCALA_PIXEL  # 48 px por baldosa cuando hay hoja
CUADRO_PUERTA = {"abierta": "abierta", "bloqueada": "bloqueada", "sellada": "sellada"}
ANIMACION_CHARCO_AVISO = "aviso"
ANIMACION_CHARCO_ACTIVO = "activo"
ALFA_CHARCO_SPRITE = 215  # el charco dibujado deja ver un poco el piso

# ----------------------------------------------------------------------
# Personalización del jugador (vestidores). El personaje es el arte de
# Higgsfield de su rol; el vestidor tiñe su piel, cabello, camisa,
# pantalón y zapatos (src/ui/tinte_jugador.py). SIMBOLOS_CABEZA y
# SIMBOLOS_TRAJE eligen la mitad de arriba o la de abajo en las vistas
# previas (sprites.sprite_parte_jugador).
# ----------------------------------------------------------------------
RUTA_RECETAS_SPRITES = os.path.join("assets", "sprites", "fuentes")  # <id>.pixel.json
ROLES_APARIENCIA = ("ciudadano", "influencer", "periodista", "candidato")  # roles con personaje de Higgsfield
SIMBOLOS_CABEZA = ("cabeza",)
SIMBOLOS_TRAJE = ("torso", "piernas_rest", "piernas_a", "piernas_b", "dash")
# Pestaña COLOR (tonos de piel, de claro a oscuro).
TONOS_PIEL = (
    (255, 226, 200),
    (242, 200, 160),
    (226, 176, 128),
    (200, 144, 90),
    (172, 114, 68),
    (141, 86, 48),
    (110, 66, 40),
    (80, 48, 32),
)
# Pestañas HAIR / SHIRT / PANTS (y SHOES, más abajo): colores que tiñen esa
# parte del personaje. Los nombres están en Online/personalizacion.py.
TONOS_PELO = (
    (24, 22, 34), (74, 46, 28), (128, 84, 50), (226, 186, 92), (186, 74, 40),
    (168, 168, 180), (70, 120, 230), (240, 110, 190), (150, 96, 230),
)
COLORES_ROPA = (
    (164, 110, 255), (220, 60, 70), (246, 140, 52), (250, 206, 60), (70, 180, 90),
    (46, 200, 190), (90, 170, 250), (240, 110, 200), (44, 40, 58),
)
COLORES_PANTALON = (
    (52, 84, 150), (34, 32, 46), (104, 104, 122), (98, 66, 44), (84, 96, 52),
    (190, 170, 128), (112, 36, 52), (92, 64, 160), (220, 220, 232),
)
# Pestaña SHOES: color de los zapatos.
COLORES_ZAPATOS = (
    (232, 70, 96), (34, 32, 46), (240, 240, 248), (70, 120, 230), (250, 206, 60),
    (70, 180, 90), (150, 96, 230), (120, 80, 50), (246, 140, 52),
)
# Modal del vestidor (Online/personalizacion_render.py).
COLOR_ACENTO_VESTIDOR = COLOR_CIAN_NEON
COLOR_SOMBRA_VESTIDOR = (0, 0, 0, 110)  # RGBA: sombra bajo el jugador de la vista previa

# ----------------------------------------------------------------------
# Revelación de rol del modo Online (Online/pantalla_rol.py), estilo Among
# Us: sale al iniciar la partida desde el lobby. El texto "pixelado" es la
# fuente del juego sin suavizado, ampliada sin interpolar.
# ----------------------------------------------------------------------
COLOR_IMPOSTOR = (255, 26, 26)  # #FF1A1A
COLOR_TRIPULANTE = (112, 229, 255)  # #70E5FF
COLOR_FONDO_IMPOSTOR = (0, 0, 0)
COLOR_FONDO_TRIPULANTE = (11, 14, 20)  # #0B0E14
COLOR_RESPLANDOR_IMPOSTOR = (128, 10, 14)  # centro del óvalo rojo; se suma al fondo
COLOR_VELO_REVELACION = (0, 0, 0)  # fundido desde y hacia negro
TEXTO_TITULO_IMPOSTOR = "IMPOSTOR"
TEXTO_SUBTITULO_IMPOSTOR = "Evita que los demás completen sus tareas saboteándolos"
TEXTO_ENCABEZADO_TRIPULANTE = "Tu rol es"
TEXTO_SUBTITULO_TRIPULANTE = "Completa tus tareas y descubre al impostor"
DURACION_REVELACION = 3.8  # s en total: fundido, jugador fijo y fundido
DURACION_FUNDIDO_REVELACION = 0.5
TIEMPO_MINIMO_OMITIR_REVELACION = 2.0  # s antes de poder omitir con Espacio o Enter
CENTRO_REVELACION = (640, 360)
ESCALA_AVATAR_REVELACION = 10  # 160x200 px
AMPLITUD_FLOTACION_REVELACION = 6  # px
FRECUENCIA_FLOTACION_REVELACION = 3.0  # rad/s
TAMANIO_OVALO_RESPLANDOR = (980, 600)
PASOS_OVALO_RESPLANDOR = 48  # elipses concéntricas de la que sale el degradado
REDUCCION_OVALO_RESPLANDOR = 4  # el óvalo se dibuja a 1/4 y se amplía con suavizado
CURVA_OVALO_RESPLANDOR = 2  # exponente del degradado: más alto = centro más concentrado
DT_MAXIMO_REVELACION = 0.25  # s: un cuadro trabado no se come la pantalla
FRECUENCIA_PULSO_RESPLANDOR = 2.5  # rad/s
BRILLO_MINIMO_RESPLANDOR = 0.7  # fracción del brillo en lo más bajo del pulso
# Cada texto: (tamaño de la fuente, ampliación, y del centro).
TEXTO_ENCABEZADO_REVELACION = (14, 3, 74)
TEXTO_TITULO_TRIPULANTE_REVELACION = (20, 5, 168)
TEXTO_TITULO_IMPOSTOR_REVELACION = (24, 6, 142)
TEXTO_SUBTITULO_REVELACION = (13, 2, 590)

# Sabotaje del impostor en la terminal de decisión (Online/sabotaje_render.py):
# solo lo ve el impostor, arriba al centro, entre el título y el reloj.
RECT_INDICADOR_SABOTAJE = (440, 20, 400, 64)
TEXTO_SABOTAJE_TITULO = "Impostor · sabotaje"
TEXTO_SABOTAJE_LISTO = "Listo: ya puedes mover y confirmar"
TEXTO_SABOTAJE_BLOQUEO = "Se habilita en {segundos} s"
TEXTO_SABOTAJE_AUN_NO = "Aún no: faltan {segundos} s"
DURACION_AVISO_SABOTAJE = 0.6  # s que el indicador marca "aún no" tras una tecla durante el bloqueo
COLOR_FONDO_BARRA_SABOTAJE = (60, 14, 22)
# Online, en combate: el mundo espera a quien siga leyendo una escena en otra PC.
TEXTO_ESPERA_LECTURA_UNO = "Esperando a que {quien} termine de leer"
TEXTO_ESPERA_LECTURA_VARIOS = "Esperando a que {quienes} terminen de leer"
POSICION_AVISO_ESPERA_LECTURA = (640, 116)
POSICION_AVISO_VERSION = (640, 150)  # "J2 tiene otra versión del juego..."
ALFA_FANTASMA = 110  # el expulsado se ve a sí mismo medio transparente

# Reunión de emergencia (Online/reunion_render.py). Botón REPORTAR abajo a la
# derecha (sobre la barra de controles, fuera de la mazmorra); la reunión es
# un modal encima de todo: tarjetas para votar a la izquierda, chat a la derecha.
# Dónde van los botones REPORTAR y SABOTEAR: Online/disposicion_hud.py (a la izquierda).
TEXTO_BOTON_REPORTAR = "REPORTAR"
COLOR_REPORTAR = (236, 52, 64)  # rojo de alarma (el botón listo)
COLOR_REPORTAR_APAGADO = (70, 66, 104)  # mientras recarga
COLOR_SABOTEAR = (150, 28, 44)  # rojo oscuro: el botón del impostor
TEXTO_BOTON_SABOTEAR = "SABOTEAR"
# Tarjetas de la reunión: el morado de Civitas (no el azul de la ciudad).
COLOR_FONDO_TARJETA_REUNION = (38, 22, 70)
COLOR_FONDO_AVATAR_REUNION = (70, 42, 124)
ALFA_VELO_REUNION = 215
RECT_PANEL_REUNION = (40, 28, 1200, 620)
RECT_CANDIDATOS_REUNION = (64, 132, 680, 380)  # rejilla de tarjetas (2 columnas)
SEPARACION_CANDIDATOS_REUNION = 16
RECT_SALTAR_REUNION = (64, 530, 680, 52)
RECT_CHAT_REUNION = (768, 132, 448, 450)
ALTO_ENTRADA_CHAT_REUNION = 44
ESCALA_AVATAR_REUNION = 5
ESCALA_AVATAR_RESULTADO_REUNION = 6
TEXTO_TITULO_REUNION = "Reunión de emergencia"
TEXTO_PISTA_CHAT_REUNION = "Escribe y presiona Enter para enviar"
TEXTO_SALTAR_REUNION = "Saltar votación"
TEXTO_EXPULSADO_PROPIO = "Fuiste expulsado: solo puedes mirar"
TEXTOS_MOTIVO_REUNION = {
    "empate": "Nadie fue expulsado: hubo empate",
    "saltada": "Nadie fue expulsado: la mayoría saltó",
    "sin_votos": "Nadie fue expulsado: nadie votó",
}
TEXTO_ERA_IMPOSTOR = "Era el impostor"
TEXTO_NO_ERA_IMPOSTOR = "No era el impostor"
TEXTO_IMPOSTOR_DESCUBIERTO = "Impostor descubierto"
CONTROLES_REUNION = [("← →", "elegir"), ("Enter", "votar (dos veces)"), ("Esc", "cancelar"), ("Teclado", "chat")]

# Fin de la partida Online por votación (Online/reunion_render.dibujar_fin_partida).
ESPERA_SALIR_FIN_PARTIDA = 2.0  # s antes de aceptar Enter (que nadie la salte sin verla)
TEXTOS_FIN_PARTIDA = {
    # (fin, ¿esta PC es la del impostor?) -> (título, subtítulo, remate)
    ("tripulacion", False): ("¡Felicidades!", "Has descubierto al impostor", "Civitas se ha salvado"),
    ("tripulacion", True): ("Te descubrieron", "La tripulación te expulsó", "Civitas se ha salvado"),
    ("impostor", False): ("El impostor quedó en pie", "y él destruyó Civitas",
                          "Civitas cayó en manos de la desinformación"),
    ("impostor", True): ("¡Felicidades!", "Has eliminado a los demás jugadores", "Has destruido Civitas con éxito"),
}
TEXTO_FIN_ERA_IMPOSTOR = "{nombre} era el impostor"
CONTROLES_FIN_PARTIDA = [("Enter", "volver al menú")]
CANTIDAD_CONFETI = 70

# Publicación del botón SABOTEAR (Online/post_sabotaje.py): se dibuja con la
# terminal tipo celular; arriba al centro, el aviso para la tripulación (el
# impostor ve ahí su bloqueo) y al terminar, una tarjeta con cómo terminó.
TEXTO_SUBTITULO_POST_SABOTAJE = "¡Alerta!  ·  Publicación viral"
TEXTO_ALERTA_POST_SABOTAJE = "¡Publicación viral! Decidan rápido qué hacer"
RECT_RESULTADO_POST_SABOTAJE = (340, 250, 600, 190)
TEXTO_POST_FRENADO = "¡Sabotaje frenado!"
TEXTO_POST_VIRAL = "El sabotaje funcionó"
TEXTO_POST_ELIGIERON = "Eligieron: {opcion}"
TEXTO_POST_SIN_TIEMPO = "Se acabó el tiempo: el rumor se volvió viral"
TEXTO_POST_EFECTO_FRENADO = "La información verificada sube"
TEXTO_POST_EFECTO_VIRAL = "Sube la desinformación y la barra de colapso"
TEXTO_AVISO_FANTASMA = "Eres un fantasma: los demás no te ven"

# ----------------------------------------------------------------------
# Tipos de enemigo: todo lo visual de cada tipo, en un solo lugar. Las
# claves son los valores de TipoEnemigo (src/entities/tipos_enemigo.py).
# Para usar arte real basta con dejar <ID_SPRITE_ENEMIGO[tipo]>.png en
# RUTA_SPRITES_ENEMIGOS (ver sprites.sprite_enemigo).
# ----------------------------------------------------------------------
RUTA_SPRITES_ENEMIGOS = os.path.join("assets", "sprites", "enemigos")
ID_SPRITE_ENEMIGO = {
    "perseguidor": "perseguidor",
    "tirador": "tirador",
    "curandero": "curandero",
}
# Arte "enemigos 2.0": cada variante (balance.STATS_VARIANTE_ENEMIGO) es un
# personaje de esta carpeta, en su subcarpeta <slug> (nombre en minúsculas
# con guiones bajos: "Black Knight_A" -> black_knight_a). Cada tira
# <slug>_<tira>.png es una fila de cuadros de 100x100 con el personaje
# mirando a la derecha; sombra/ guarda las mismas tiras con sombra (sin
# usar). Los proyectiles del pack están en sprites/efectos/proyectiles/ y
# los .aseprite en sprites/fuentes/enemigos/.
RUTA_SPRITES_ENEMIGOS_V2 = os.path.join("assets", "sprites", "enemigos", "variantes")


def slug_asset(nombre):
    """Nombre de archivo/carpeta de un asset: minúsculas, sin espacios ni
    símbolos ("Black Knight_A" -> "black_knight_a")."""
    return "_".join("".join(c if c.isalnum() else " " for c in nombre.lower()).split())


def ruta_tira_variante(nombre, tira):
    """Ruta de la tira `tira` ("Walk", "Attack01"...) de la variante `nombre`."""
    carpeta = slug_asset(nombre)
    return os.path.join(RUTA_SPRITES_ENEMIGOS_V2, carpeta, f"{carpeta}_{slug_asset(tira)}.png")
CUADRO_ENEMIGO_V2 = 100  # lado de cada cuadro de la tira
DURACION_CUADRO_ENEMIGO_V2 = 0.1  # s por cuadro al caminar
# Arte de cada variante: tira de movimiento ("Walk" o "Flying"), tira de
# ataque, escala (px nativos * escala), hitbox (px de lado) y color de su
# proyectil. El Hellhound (escala 2) queda pequeño y el Warlock (escala 4)
# grande. Los números de combate viven en balance.STATS_VARIANTE_ENEMIGO.
ARTE_VARIANTE = {
    "Hellhound": dict(tira_mov="Walk", tira_ataque="Attack01", escala=2, tamanio=38, color=(232, 52, 64)),
    "Minotaur": dict(tira_mov="Walk", tira_ataque="Attack01", escala=3, tamanio=56, color=(200, 120, 60)),
    "Blood Monster_A": dict(tira_mov="Walk", tira_ataque="Attack01", escala=3, tamanio=40, color=(200, 30, 50)),
    "Blood Monster_B": dict(tira_mov="Flying", tira_ataque="Attack01", escala=3, tamanio=34, color=(220, 40, 70)),
    "Hellbat": dict(tira_mov="Flying", tira_ataque="Attack01", escala=3, tamanio=38, color=(180, 60, 200)),
    "Demon_A": dict(tira_mov="Walk", tira_ataque="Attack01", escala=3, tamanio=42, color=(230, 80, 50)),
    "Demon_E": dict(tira_mov="Walk", tira_ataque="Attack01", escala=2, tamanio=48, color=(210, 40, 60)),
    "Black Knight_A": dict(tira_mov="Walk", tira_ataque="Attack01", escala=3, tamanio=44, color=(120, 120, 150)),
    "Black Knight_C": dict(tira_mov="Walk", tira_ataque="Attack01", escala=3, tamanio=64, color=(150, 80, 200)),
    "Demoness_A": dict(tira_mov="Walk", tira_ataque="Attack01", escala=3, tamanio=54, color=(240, 90, 160)),
    "Warlock": dict(tira_mov="Walk", tira_ataque="Attack01", escala=4, tamanio=56, color=(190, 90, 255)),
    "Demon_B": dict(tira_mov="Walk", tira_ataque="Attack01", escala=3, tamanio=40, color=(255, 200, 80)),
    "Black Knight_B": dict(tira_mov="Walk", tira_ataque="Attack01", escala=3, tamanio=44, color=(255, 150, 60)),
    "Eyeball Monster": dict(tira_mov="Walk", tira_ataque="Attack01", escala=3, tamanio=36, color=(255, 70, 200)),
    "Lava Slime": dict(tira_mov="Walk", tira_ataque="Attack01", escala=3, tamanio=40, color=(255, 110, 30)),
    "Demon_C": dict(tira_mov="Walk", tira_ataque="Attack01", escala=3, tamanio=48, color=(255, 90, 90)),
    "Demon_D": dict(tira_mov="Walk", tira_ataque="Attack01", escala=3, tamanio=52, color=(255, 60, 120)),
    "Ghostfire": dict(tira_mov="Flying", tira_ataque="Attack01", escala=3, tamanio=36, color=(120, 255, 200)),
    "Demoness_B": dict(tira_mov="Walk", tira_ataque="Attack01", escala=3, tamanio=40, color=(255, 180, 220)),
}
# Debug de balance: nombre exacto de la variante flotando sobre cada
# enemigo. Poner en False cuando termine el balanceo.
MOSTRAR_NOMBRE_ENEMIGO = False
COLOR_NOMBRE_ENEMIGO = (255, 255, 255)
COLOR_SOMBRA_NOMBRE_ENEMIGO = (10, 10, 20)
SEPARACION_NOMBRE_ENEMIGO = 4  # px entre el texto y lo alto del sprite
COLOR_PRINCIPAL_ENEMIGO = {
    "perseguidor": (232, 52, 64),  # rojo: agresivo
    "tirador": (255, 120, 60),  # naranja
    "curandero": (70, 200, 120),  # verde
}
COLOR_SECUNDARIO_ENEMIGO = {
    "perseguidor": (120, 20, 40),
    "tirador": COLOR_MAGENTA,
    "curandero": (236, 246, 236),
}
TAMANIO_ENEMIGO_TIPO = {  # hitbox lógica (px de lado)
    "perseguidor": 38,
    "tirador": 56,  # Warlock grande (el sprite mide 84x104)
    "curandero": 36,
}
COLOR_PROYECTIL_TIRADOR = (255, 140, 70)
TAMANIO_PROYECTIL_TIRADOR = 10
COLOR_TELEGRAFIA_TIRADOR = (255, 230, 150)  # el tirador se ilumina antes de disparar
COLOR_RAYO_CURA = (90, 240, 140)
GROSOR_RAYO_CURA = 3
COLOR_PARTICULA_CURA = (140, 255, 170)
CANTIDAD_PARTICULAS_CURA = 6
TAMANIO_PARTICULA_CURA = 5
COLOR_PANICO_CURANDERO = COLOR_MAGENTA  # contorno del curandero en pánico

# Gracia al entrar al cuarto: anillo de cuenta regresiva sobre el
# jugador y enemigos que parpadean (alfa pulsante) mientras dura.
COLOR_ANILLO_GRACIA = COLOR_TEAL
COLOR_FONDO_ANILLO_GRACIA = (40, 60, 80)
RADIO_ANILLO_GRACIA = 30
GROSOR_ANILLO_GRACIA = 4
ALFA_MIN_ENEMIGO_GRACIA = 90
ALFA_MAX_ENEMIGO_GRACIA = 220
PERIODO_PARPADEO_GRACIA = 0.35  # s por pulso

# ----------------------------------------------------------------------
# Modo historia "Código Nova" (src/story/, dibujo en src/ui/dialogo_render.py,
# tarjetas_render.py e indicadores_render.py)
# ----------------------------------------------------------------------
# Diálogo: velo sobre la escena y panel inferior con retrato, nombre y texto.
COLOR_VELO_DIALOGO = (6, 6, 18, 150)  # RGBA
RECT_PANEL_DIALOGO = (120, 470, 1040, 180)
COLOR_FONDO_DIALOGO = (18, 16, 42)
COLOR_BORDE_DIALOGO = COLOR_MORADO
ALTO_RETRATO_DIALOGO = 140
COLOR_NOMBRE_DIALOGO = COLOR_TEAL
COLOR_TITULO_DIALOGO = COLOR_MORADO
POSICION_TITULO_DIALOGO = (640, 430)  # centro del rótulo del capítulo
COLOR_RETRATO_CIVITAS = COLOR_TEAL  # icono en código del sistema Civitas
COLOR_RETRATO_NOVA = COLOR_MAGENTA  # icono en código de NOVA_404
DURACION_PARPADEO_INDICADOR = 0.8  # s del ciclo del "▸ Enter" del diálogo
# Retratos opcionales para los hablantes que no son roles:
# assets/sprites/retratos/<id>.png (civitas.png, nova.png). Sin archivo,
# se dibuja el icono en código.
ID_RETRATO_CIVITAS = "civitas"
ID_RETRATO_NOVA = "nova"
ID_RETRATO_MENTORA = "rosa"
RECT_INDICADOR_REPUTACION = (290, 170, 700, 380)
POSICION_CHIP_REPUTACION = (1096, 82)  # bajo el panel de colapso, a la derecha
RECT_FEED_CIVITAS = (900, 560, 360, 80)
RADIO_RECOGER_EVIDENCIA = 46  # px: tocar la prueba del suelo la recoge
PERIODO_REACCION_CIUDAD = 24.0  # s entre comentarios de ciudadanos
DURACION_FEED_CIVITAS = 7.0
ALCANCE_BALIZA = 70  # px para abrir una etapa de la misión de redención
PAUSA_ANTES_DE_DECIDIR = 0.6  # s: un Enter de más al abrir una decisión no cuenta
TITULO_ETAPA_REDENCION = {
    "reconocer": "Reconocer el error",
    "corregir": "Corregir la información",
    "confianza": "Recuperar la confianza",
}

# Tarjeta de evidencia (aparece en combate al limpiar un cuarto).
RECT_TARJETA_EVIDENCIA = (350, 72, 580, 128)
COLOR_FONDO_EVIDENCIA = (248, 244, 232)
COLOR_BORDE_EVIDENCIA = COLOR_AMARILLO
COLOR_TITULO_EVIDENCIA = (34, 30, 48)
COLOR_FUENTE_EVIDENCIA = (110, 106, 128)
COLOR_PISTA = COLOR_MAGENTA  # chip "PISTA NOVA_404"
DURACION_TARJETA_EVIDENCIA = 6.0  # s visible en combate

# Panel de estado de Ciudad Nova (tecla I en la ciudad y pantalla final).
RECT_PANEL_ESTADO = (780, 80, 470, 560)
COLOR_FONDO_PANEL_ESTADO = (18, 16, 42, 236)  # RGBA
COLOR_INDICADOR_BUENO = COLOR_TEAL
COLOR_INDICADOR_MALO = COLOR_MAGENTA
COLOR_FONDO_INDICADOR = (40, 36, 78)
ALTO_BARRA_INDICADOR = 12
SEPARACION_INDICADORES = 44
COLOR_DELTA_POSITIVO = COLOR_TEAL
COLOR_DELTA_NEGATIVO = COLOR_MAGENTA
# Color de cada rol por su clave (JugadorBase.rol), para quien solo tiene la clave.
COLOR_POR_ROL = {
    "ciudadano": COLOR_CIUDADANO,
    "influencer": COLOR_INFLUENCER,
    "periodista": COLOR_PERIODISTA,
    "candidato": COLOR_CANDIDATO,
}
# Pantalla de propagación por la red social (src/ui/red_social_render.py).
RECT_PANEL_GRAFO_SOCIAL = (60, 120, 660, 500)
CENTRO_GRAFO_SOCIAL = (390, 352)
RADIO_GRAFO_SOCIAL = 168
RADIO_NODO_SOCIAL = 16
COLOR_NODO_SOCIAL = (60, 56, 104)
COLOR_BORDE_NODO_SOCIAL = COLOR_BORDE_PANEL
COLOR_ARISTA_SOCIAL = (52, 48, 92)
COLOR_NODO_ORIGEN = COLOR_AMARILLO
COLOR_NODO_RUMOR = COLOR_MAGENTA
COLOR_NODO_CORREGIDO = COLOR_TEAL
COLOR_ARISTA_RUMOR = COLOR_MAGENTA
COLOR_ARISTA_CORRECCION = COLOR_TEAL
GROSOR_ARISTA_PROPAGADA = 3
SEGUNDOS_POR_CAPA = 0.6  # la onda del BFS avanza una capa cada tanto
RECT_PANEL_DATOS_SOCIAL = (760, 120, 460, 500)
# Pantalla de elecciones (src/ui/elecciones_render.py).
RECT_PANEL_CANDIDATOS = (60, 150, 640, 330)
RECT_PANEL_ESTADO_FINAL = (740, 110, 480, 540)
RECT_PANEL_EPILOGO = (60, 500, 640, 150)
ALTO_BARRA_CANDIDATO = 22
SEPARACION_CANDIDATOS = 70
COLORES_CANDIDATOS = (COLOR_TEAL, COLOR_AMARILLO, COLOR_MORADO, COLOR_MAGENTA)
COLOR_FINAL_RENACE = COLOR_TEAL
COLOR_FINAL_DIVIDIDA = COLOR_MAGENTA
COLOR_FINAL_ARQUITECTO = COLOR_AMARILLO
# Alto contraste (preferencia de accesibilidad): la imagen final se suma a
# sí misma (lo claro brilla más) y se le resta un gris (lo oscuro se hunde).
ALTO_CONTRASTE_RESTA = (28, 28, 34)
# Ayuda del modo historia (tecla H en la ciudad, src/ui/ayuda_render.py).
RECT_PANEL_AYUDA = (90, 70, 1100, 580)
COLOR_FONDO_AYUDA = (18, 16, 42, 240)  # RGBA
# Fondos ilustrados del modo historia (assets/story/<id>.png, 1280x720,
# Higgsfield nano_banana_2; ver docs/ASSET_MANIFEST.md). Si falta el
# archivo, las pantallas se dibujan como antes (velo o fondo liso).
RUTA_FONDOS_HISTORIA = os.path.join("assets", "story")
RUTA_VIDEOS_HISTORIA = os.path.join("assets", "story", "video")
FONDO_PROLOGO = "portada"
FONDO_ELECCIONES = "elecciones"
FONDO_POR_ZONA = {
    "Colegio": "capitulo_colegio",
    "Hospital": "capitulo_hospital",
    "Empresa de Medios": "capitulo_medios",
    "Alcaldía": "servidor_central",
}
ALFA_FONDO_DIALOGO = 200  # cuánto se ve la ilustración detrás del diálogo (0-255)
ALFA_FONDO_ELECCIONES = 90

# ----------------------------------------------------------------------
# Capa de interfaz común (src/ui/layout.py): márgenes y zonas seguras.
# Toda pantalla nueva mide contra estas constantes; ningún texto puede
# salir de RECT_ZONA_SEGURA ni pisar el HUD (arriba) o la barra de
# controles (abajo).
# ----------------------------------------------------------------------
MARGEN_PANTALLA = 40  # px desde el borde de la ventana al primer texto
MARGEN_PANEL = 20  # px internos de un panel
SEPARACION_SECCION = 12  # px entre bloques de texto
RECT_ZONA_SEGURA = (MARGEN_PANTALLA, MARGEN_PANTALLA, 1280 - 2 * MARGEN_PANTALLA, 720 - 2 * MARGEN_PANTALLA)
RECT_ZONA_JUEGO = (0, ALTO_HUD + 2, 1280, 720 - ALTO_HUD - 2 - ALTO_BARRA_CONTROLES)  # entre HUD y controles
DURACION_ENTRADA_PANEL = 0.22  # s de la animación de entrada de un panel/overlay
COLOR_VELO_OVERLAY = (4, 4, 14, 170)  # RGBA detrás de cualquier overlay modal

# ----------------------------------------------------------------------
# Cinemáticas (src/story/cinematica.py, dibujo en src/ui/cinematica_render.py)
# ----------------------------------------------------------------------
ALTO_LETTERBOX = 64  # franjas negras arriba y abajo
COLOR_LETTERBOX = (0, 0, 0)
RECT_SUBTITULO_CINEMATICA = (120, 532, 1040, 130)  # caja de subtítulos: hablante + 3 líneas
COLOR_FONDO_SUBTITULO = (4, 4, 12, 190)
COLOR_SUBTITULO = COLOR_TEXTO_HUD
COLOR_SUBTITULO_NOVA = COLOR_MAGENTA
COLOR_SUBTITULO_HABLANTE = COLOR_TEAL
TAMANIO_FUENTE_SUBTITULO = TAMANIO_FUENTE_MEDIA
VELOCIDAD_MAQUINA_ESCRIBIR = 46.0  # caracteres por segundo del subtítulo
DURACION_FUNDIDO_TOMA = 0.6  # s de fundido a negro entre tomas
ZOOM_KEN_BURNS = 1.10  # escala de la imagen que se pasea lentamente
PERIODO_PANEO = 38.0  # s de un vaivén completo del paneo
INTENSIDAD_GLITCH_NOVA = 14  # px máximos de desplazamiento de las bandas de glitch
FILAS_GLITCH_NOVA = 9
COLOR_TINTE_NOVA = (255, 56, 120, 46)  # RGBA sobre la imagen cuando habla NOVA_404
# Notificaciones flotantes (escenas de Civitas y del caos).
CANTIDAD_NOTIFICACIONES_CIVITAS = 7
CANTIDAD_NOTIFICACIONES_CAOS = 18
ANCHO_NOTIFICACION = 300
ALTO_NOTIFICACION = 58
COLOR_FONDO_NOTIFICACION = (244, 240, 230)
COLOR_TEXTO_NOTIFICACION = (34, 30, 48)
COLOR_FONDO_NOTIFICACION_FALSA = (255, 226, 234)
COLOR_BORDE_NOTIFICACION_FALSA = COLOR_MAGENTA
# Tarjeta de título (capítulos, estilo "presentación de ronda").
TAMANIO_FUENTE_TARJETA_SUPERIOR = TAMANIO_FUENTE_TITULO
TAMANIO_FUENTE_TARJETA = 56
COLOR_TARJETA_CAPITULO = COLOR_TEXTO_HUD
COLOR_LINEA_TARJETA = COLOR_MORADO
DURACION_TARJETA_CAPITULO = 9.0  # s de lectura de la tarjeta de capítulo; Enter la pasa antes
# Título de la cinemática y pantalla de objetivos.
TAMANIO_FUENTE_TITULO_CINEMATICA = 64
COLOR_TITULO_CINEMATICA = COLOR_MENU_SELECCION
COLOR_RESPLANDOR_TITULO_CINE = (164, 110, 255, 70)
RECT_PANEL_OBJETIVOS = (340, 140, 600, 450)
COLOR_BOTON_COMENZAR = COLOR_TEAL
COLOR_TEXTO_BOTON_COMENZAR = COLOR_FONDO
RECT_BOTON_COMENZAR = (470, 496, 340, 50)
# Protagonista en la cinemática: retrato grande a la izquierda.
ALTO_RETRATO_CINEMATICA = 300
POSICION_RETRATO_CINEMATICA = (260, 330)  # centro
# Prólogo «La ciudad que perdió»: película con rótulos cronometrados.
VIDEO_PROLOGO = "prologo_umbral"  # assets/story/video/prologo_umbral/ (lineal, 15 fps)
PISTA_PROLOGO = "prologo_umbral"  # assets.MUSICA
FONDO_PROLOGO_UMBRAL = "umbral_colapso"  # respaldo si faltan los cuadros
Y_SUBTITULO_PELICULA = 720 - ALTO_LETTERBOX - 14  # base del subtítulo de la película
TAMANIO_FUENTE_SUBTITULO_PELICULA = 30
TAMANIO_FUENTE_HABLANTE_PELICULA = 18
COLOR_FONDO_SUBTITULO_PELICULA = (0, 0, 0, 215)  # RGBA: contraste alto sobre cualquier toma
COLOR_HABLANTE_PELICULA = COLOR_AMARILLO  # hablante sin color propio
COLOR_POR_HABLANTE_PELICULA = {"TEO": COLOR_AMARILLO, "LÍA": COLOR_TEAL, "CIUDADANA": (255, 120, 110)}
# Rótulos de juego dentro de la película (misión, días, publicaciones, colapso, lugares).
RECT_MISION_PELICULA = (40, 96, 470, 0)  # x, y, ancho (alto según renglones)
COLOR_MISION_PELICULA = COLOR_AMARILLO
COLOR_DESCARTADA_PELICULA = COLOR_GRAVE
RECT_BARRA_COLAPSO_PELICULA = (860, 92, 380, 16)
COLOR_BARRA_COLAPSO_PELICULA = COLOR_GRAVE
COLOR_LUGAR_PELICULA = COLOR_TEAL
TAMANIO_FUENTE_ROTULO_PELICULA = 22
COLOR_NARRADOR_PELICULA = COLOR_TEXTO_HUD
TAMANIO_FUENTE_ALERTA_PELICULA = 46
COLOR_ALERTA_PELICULA = COLOR_GRAVE
TAMANIO_FUENTE_LEMA_PELICULA = 40
COLOR_LEMA_PELICULA = COLOR_TEXTO_HUD
ALFA_VELO_LEMA = 150  # oscurece la imagen detrás de un lema
COLOR_SOMBRA_PELICULA = (0, 0, 0)

# ----------------------------------------------------------------------
# Misiones (src/story/misiones.py, dibujo en src/ui/mision_render.py)
# ----------------------------------------------------------------------
RECT_PANEL_MISION_CIUDAD = (12, 100, 340, 140)  # bajo la línea de misión, a la izquierda
RECT_PANEL_MISION_COMBATE = (20, 720 - ALTO_BARRA_CONTROLES - 12 - 116, 340, 116)  # abajo a la izquierda
COLOR_FONDO_MISION = (14, 12, 34, 215)  # RGBA
COLOR_BORDE_MISION = COLOR_AMARILLO
COLOR_TITULO_MISION = COLOR_AMARILLO
COLOR_OBJETIVO_PENDIENTE = COLOR_TEXTO_HUD
COLOR_OBJETIVO_HECHO = COLOR_TEAL
COLOR_OBJETIVO_FUTURO = COLOR_TEXTO_APAGADO
RECT_TOAST_MISION = (440, 150, 400, 56)  # aviso "Objetivo completado" (centro superior)
DURACION_TOAST_MISION = 2.6  # s visible
COLOR_FONDO_TOAST = (14, 36, 34, 235)
COLOR_BORDE_TOAST = COLOR_TEAL

# ----------------------------------------------------------------------
# Epílogo: cinemática de la caída del servidor, elecciones animadas y final.
# ----------------------------------------------------------------------
DURACION_CONTEO_ELECCIONES = 2.2  # s que tardan las barras en llenarse
FONDO_SERVIDOR_CAIDO = "servidor_caido"
FONDO_CRISIS = "crisis_reputacion"
FONDO_REDENCION = "redencion"
FONDO_CONFIANZA_PERDIDA = "final_confianza_perdida"
VIDEO_CRISIS = "crisis"
VIDEO_JEFE = "jefe"
VIDEO_REDENCION = "redencion"
FONDO_CIUDADANOS = "ciudadanos_civitas"
FONDO_PANTALLAS_NOVA = "pantallas_nova"
FONDO_POR_FINAL = {"renace": "final_renace", "dividida": "final_dividida", "arquitecto": "servidor_caido",
                   "confianza_perdida": FONDO_CONFIANZA_PERDIDA}

# ----------------------------------------------------------------------
# Terminal de decisión como celular (src/ui/terminal_decision_render.py;
# piezas del celular en src/ui/celular_render.py). Dos capturas de la app
# Civitas: a la izquierda el perfil de quien publicó, con las pruebas
# reunidas como capturas; a la derecha la publicación en el feed, con las
# opciones del árbol como botones de la app. Al centro, la consola: título,
# reloj y el árbol N-ario. Nada importante cae bajo RECT_INDICADOR_SABOTAJE
# (x 440-840, y 20-84) ni bajo la barra de controles (ALTO_BARRA_CONTROLES).
# ----------------------------------------------------------------------
RECT_CELULAR_PERFIL = (40, 14, 368, 638)
# Fondo detrás de los celulares: morado oscuro de Civitas (la red social), no el azul de la ciudad.
COLOR_FONDO_TERMINAL_CIVITAS = (24, 12, 46)
COLOR_TRAMA_TERMINAL_CIVITAS = (44, 24, 80)
RECT_CELULAR_FEED = (872, 14, 368, 638)
RECT_CONSOLA_TERMINAL = (428, 96, 424, 552)  # columna central, debajo del indicador del impostor
RADIO_CELULAR = 34  # esquinas del cuerpo
GROSOR_MARCO_CELULAR = 4  # canto entre el borde del cuerpo y la pantalla
SALIENTE_BOTON_CELULAR = 3  # px que asoman los botones laterales
ALTO_BARRA_ESTADO_CELULAR = 28
ALTO_BARRA_APP_CELULAR = 38
ANCHO_ISLA_CELULAR = 66  # la "isla" negra de la cámara
ALTO_HISTORIAS_CELULAR = 70
DIAMETRO_HISTORIA_CELULAR = 42
ALTO_FOTO_POST = (150, 206)  # alto mínimo y máximo de la foto de la publicación
ALTO_FILA_ACCIONES = 66
ANCHO_MAXIMO_BOTON_ACCION = 88  # con 2 o 3 opciones los botones no se estiran
ALTO_NAV_CELULAR = 42
TAMANIO_ICONO_ACCION = 24
TAMANIO_FUENTE_CELULAR = 12
TAMANIO_FUENTE_CELULAR_MINIMA = 10
COLOR_MARCO_CELULAR_ARRIBA = (128, 94, 216)  # canto con degradado violeta (la marca Civitas)
COLOR_MARCO_CELULAR_ABAJO = (50, 42, 108)
COLOR_BOTON_LATERAL_CELULAR = (70, 58, 140)
COLOR_PANTALLA_CELULAR = (12, 13, 30)
COLOR_SEPARADOR_CELULAR = (38, 40, 76)
COLOR_ISLA_CELULAR = (0, 0, 0)
COLOR_HOJA_CELULAR = (26, 26, 58)  # hoja inferior del 2.º nivel del árbol
COLOR_FONDO_AVATAR_POST = (42, 36, 90)
COLOR_BARRA_CAPTURA = (226, 220, 204)  # franja de arriba de cada captura de prueba
COLOR_LINEA_DOCUMENTO = (176, 170, 192)
COLOR_MEMBRETE_DOCUMENTO = (64, 54, 124)
COLOR_LEYENDA_FOTO = (6, 6, 16, 205)  # RGBA: franjas de texto sobre la foto
COLOR_PANEL_GRAFICO = (10, 12, 32, 220)  # RGBA: tarjeta del gráfico sobre la foto
HORA_CELULAR = "22:14"
HORA_FOTO_POST = "HOY 21:38"  # marca de la cámara en la foto "con hora"
SEGUNDOS_RELOJ_ALERTA = 12  # el reloj se vuelve ámbar
SEGUNDOS_RELOJ_GRAVE = 5  # y rojo
# Foto de la publicación: la ilustración del capítulo de la zona (FONDO_POR_ZONA)
# recortada; el árbol fijo y las zonas sin ilustración usan FONDO_POST_GENERICO.
FONDO_POST_GENERICO = "elecciones"
RECORTE_FOTO_POST = {  # (x, y, ancho, alto) dentro de la ilustración de 1280x720
    "capitulo_colegio": (300, 330, 660, 370),
    "capitulo_hospital": (60, 40, 760, 426),
    "capitulo_medios": (180, 180, 540, 304),
    "elecciones": (420, 300, 760, 426),
}
# Fila de historias del feed: (retrato de assets/sprites/retratos, nombre,
# recorte de la cara = (centro x en fracción del ancho, centro y y lado en
# fracción del alto)).
HISTORIAS_CELULAR = (
    ("civitas", "civitas", (0.50, 0.48, 0.66)),
    ("rosa", "rosa", (0.50, 0.15, 0.24)),
    ("periodista", "periodista", (0.45, 0.17, 0.30)),
    ("ciudadano", "ciudadano", (0.30, 0.18, 0.30)),
    ("influencer", "influencer", (0.32, 0.17, 0.30)),
    ("candidato", "candidato", (0.47, 0.16, 0.30)),
)

# ----------------------------------------------------------------------
# Nuevo mundo: "Backrooms Liminal Interiors v1.0" de bubbabba (16x16, vista
# 3/4). Los packs completos viven en _packs/ (fuera de git: la licencia no
# deja redistribuirlos); tools/empaquetar_backrooms.py copia a
# assets/backrooms/<grade>/ solo lo que el juego usa: atlas.json + tiles.png,
# props.png, animaciones.png y luces.png. Los 5 "grades" (ambientes de luz)
# tienen los mismos nombres y layout: cambiar de ambiente es cambiar de
# carpeta. Se piden por src/ui/cargador_backrooms.py (rutas puras en
# src/ui/rutas_backrooms.py). 16 px * ESCALA_PIXEL = 48 = TAM_CASILLA.
# ----------------------------------------------------------------------
RUTA_BACKROOMS = os.path.join("assets", "backrooms")
GRADES_BACKROOMS = ("hum", "blackout", "emergency", "nightshot", "sodium")
GRADE_POR_DEFECTO = "hum"  # luz fluorescente amarillenta: el "Backrooms" clásico
ARCHIVO_ATLAS_BACKROOMS = "atlas.json"
HOJAS_BACKROOMS = {"tiles": "tiles.png", "props": "props.png", "animaciones": "animaciones.png",
                   "luces": "luces.png"}
TAM_TILE_BACKROOMS = 16
ESCALA_BACKROOMS = ESCALA_PIXEL
COLOR_FALTANTE_BACKROOMS = (255, 0, 255)  # damero magenta/negro: asset que falta (se ve, no se cae)
RUTA_COMPOSICIONES = os.path.join("src", "dungeon", "datos", "composiciones")
RUTA_TERRENOS_BACKROOMS = os.path.join("src", "dungeon", "datos", "terrenos_backrooms.json")
CREDITO_BACKROOMS = "Backrooms Liminal Interiors by bubbabba"

# Lobby del hotel (src/ui/escena_lobby.py + escena_lobby_render.py): la
# recepción se dibuja a ESCALA_BACKROOMS, corrida para centrar 27 tiles
# (1296 px) en 1280. Las tarjetas son más bajas que en el lobby clásico:
# el sprite de cada rol posa en la escena, sobre su tarjeta.
COMPOSICION_LOBBY = "lobby_hotel"
GRADE_LOBBY = GRADE_POR_DEFECTO
DESPLAZAMIENTO_ESCENA_LOBBY = (-8, 0)  # px de pantalla
ORIGEN_COLUMNAS_HOTEL = (70, 270)
ALTO_TARJETA_HOTEL = 258
RECT_PANEL_RESUMEN_HOTEL = (70, 540, 1140, 96)
POSICION_TITULO_HOTEL = (640, 40)
ESCALA_SPRITE_PUESTO = 4  # rol posando en su puesto (si falta su retrato)
ALTO_RETRATO_PUESTO = 120  # el personaje de Higgsfield posando en su puesto del hotel
ALFA_TARJETA_HOTEL = 226
RECT_TABLERO_MAZMORRAS = (966, 10, 306, 150)  # cartelera colgada en la pared del fondo
COLOR_TABLERO = (34, 24, 20)
COLOR_MARCO_TABLERO = (150, 112, 62)
COLOR_TEXTO_TABLERO = (236, 214, 160)
COLOR_PENDIENTE_TABLERO = (236, 180, 70)
COLOR_COMPLETADA_TABLERO = (120, 220, 150)
ALFA_VELO_TITULO_HOTEL = 150  # franja oscura bajo el título para que se lea sobre la pared
ANCHO_VELO_TITULO_HOTEL = 640
COLOR_HALO_PUESTO_ALFA = 80
DURACION_PARPADEO_LOBBY = 0.07  # s de cada "corte" de una luz que falla
FACTOR_APAGADO_LOBBY = 0.45  # brillo de un prop sin versión apagada cuando su luz falla
COLOR_POLVO_LOBBY = (255, 238, 190)
COLOR_MANECILLA_RELOJ = (40, 30, 26)
ALTO_SOMBRA_TECHO_LOBBY = 96  # px de pantalla
ALFA_SOMBRA_TECHO_LOBBY = 200
SEPARACION_FILAS_HOTEL = 23  # filas de estadísticas en la tarjeta compacta
ANCHO_NOMBRE_TABLERO = 134
TOXICIDAD_MEDIA_TABLERO = 34
TOXICIDAD_ALTA_TABLERO = 67
COLOR_TOXICIDAD_ALTA_TABLERO = (255, 96, 96)

# ----------------------------------------------------------------------
# Ciudad Nova (exteriores): POCOS assets, bien elegidos. De los packs
# cyberpunk solo la calzada (asfalto, bordillo, banqueta, línea central y
# cebra de una misma celda de PATHS ROADS 4) y el agua de la alberca; el
# resto es el arte que ya se veía bien: pasto oscuro, árboles de Trees_Vol2,
# mobiliario del pack urbano y los edificios completos (pixel art en código
# y el pack escolar). tools/empaquetar_ciudad.py recorta esas piezas 1:1 a
# assets/ciudad/atlas.png; src/ui/arte_ciudad.py es la única puerta por la
# que el render de la ciudad pide imágenes y solo entrega ids de la lista
# blanca ASSETS_CIUDAD_PERMITIDOS.
# ----------------------------------------------------------------------
RUTA_ATLAS_CIUDAD = os.path.join("assets", "ciudad", "atlas.png")
RUTA_ATLAS_CIUDAD_JSON = os.path.join("assets", "ciudad", "atlas.json")
# Árboles permitidos (número del pack Trees_Vol2): pinos, frondosos verdes,
# sauce, otoñales y frutales, más dos arbustos. Fuera: los de fantasía
# (rosa, violeta, azul, magenta) que rompen la paleta.
PINOS = (1, 3, 5, 7)
FRONDOSOS = (9, 12, 15, 18, 47, 52, 53, 57, 62, 67)
SAUCES = (24,)
OTONALES = (27, 30, 33)
FRUTALES = (43, 44, 49, 64, 69)
ARBUSTOS = (36, 38)
ARBOLES_CIUDAD = PINOS + FRONDOSOS + SAUCES + OTONALES + FRUTALES + ARBUSTOS
# Mobiliario discreto del pack urbano (assets.PROPS_URBANOS) que usa la ciudad.
MOBILIARIO_CIUDAD = (
    "farola", "farola_ornamental", "farola_baja", "farola_curva", "farola_jardin", "farola_farol",
    "banca", "banca_corta", "banca_parada", "cartel_parada", "basurero", "basurero_verde", "buzon",
    "buzon_azul", "jardinera", "jardinera_flores", "jardinera_larga", "maceta_grande", "maceta_planta",
    "maceta_flores", "bolardo", "bicicletero", "bicicleta", "cartelera", "letrero_bienvenida", "bebedero",
    "bebedero_pajaros", "casita_pajaros", "mesa_cafe", "mesa_sombrilla", "carrito_comida", "kiosco_digital",
    "armario_electrico", "parada_bus", "reciclaje", "cerca_madera", "parrilla", "barricada", "toldo",
    "aire_acondicionado",
)
# Lista blanca de todo lo que el render de Ciudad Nova puede dibujar, como
# "origen:nombre": "ciudad:" pieza del atlas de los packs nuevos, "urbano:"
# prop del pack urbano, "arbol:" número de Trees_Vol2, "backrooms:" prop del
# pack Backrooms. Lo que no está aquí no se usa aunque el pack lo tenga.
ASSETS_CIUDAD_PERMITIDOS = frozenset(
    {f"ciudad:{n}" for n in ("asfalto", "acera", "bordillo", "linea_carril", "cebra", "agua")}
    | {f"urbano:{n}" for n in MOBILIARIO_CIUDAD}
    | {f"arbol:{n}" for n in ARBOLES_CIUDAD}
    | {"backrooms:antena", "backrooms:cono", "backrooms:letrero_prohibido"}
)
# Texturas de suelo por terreno (piezas del atlas; la plaza usa la misma
# losa gris de la banqueta, como el parque).
TEXTURA_TERRENO_CIUDAD = {"calle": "asfalto", "acera": "acera", "agua": "agua"}
PIEZA_BORDILLO = "bordillo"  # borde banqueta-calzada (también el canto de la alberca)
PIEZA_LINEA_CARRIL = "linea_carril"
PIEZA_CEBRA = "cebra"
GROSOR_BORDILLO = 8  # px
LARGO_TRAZO_CARRIL = 24  # px de cada trazo de la línea central (uno por casilla)
# Ajuste central de paleta (cargador_assets.ajustar_paleta): id -> (saturación,
# brillo). Baja lo que en el pack es demasiado saturado o claro para la noche.
AJUSTE_PALETA_CIUDAD = {
    "ciudad:asfalto": (0.5, 0.36),  # calzada oscura: la banqueta gris resalta
    "ciudad:acera": (0.6, 0.8),
    "ciudad:bordillo": (0.6, 0.7),
    "ciudad:linea_carril": (0.85, 0.9),
    "ciudad:cebra": (0.5, 0.78),
    "ciudad:agua": (0.38, 0.62),  # agua discreta, no el cian del pack
    "urbano:mesa_sombrilla": (0.6, 1.0),
    "urbano:carrito_comida": (0.6, 1.0),
    "urbano:bicicleta": (0.7, 1.0),
}
# Ajuste por origen cuando el id no tiene uno propio: las copas de Trees_Vol2
# son de día (verde lima, naranja vivo); de noche se bajan un poco.
AJUSTE_PALETA_POR_ORIGEN = {"arbol": (0.62, 0.84)}
AJUSTE_PALETA_CIUDAD.update({f"arbol:{n}": (0.5, 0.82) for n in OTONALES})  # los otoñales, más apagados
# Paleta máxima de la ciudad: base nocturna azul-gris, banqueta gris,
# vegetación verde y acentos de neón solo en carteles, puertas, ventanas
# puntuales y la línea amarilla de la calzada. El tope de píxeles saturados
# vive en balance.MAX_FRACCION_SATURADA_CIUDAD.
PALETA_CIUDAD = {
    "base_nocturna": (24, 28, 40),
    "banqueta": (78, 80, 92),
    "vegetacion": (40, 70, 52),
    "acento_neon": (255, 204, 110),  # ventanas cálidas, línea amarilla
}
# Jardines ('J' y el camellón 'k'): pasto un poco más oscuro que el del
# parque, con un bordillo de piedra donde dan a la banqueta.
FACTOR_PASTO_JARDIN = 0.82
ALFA_SOMBRA_PROP = 90
# Vida urbana: vapor que sube de las alcantarillas de los cruces y rótulos
# neón de los edificios que fallan un instante cada tanto.
COLOR_VAPOR = (200, 210, 235)
ALFA_VAPOR = 60
RADIO_VAPOR = 18
BOCANADAS_VAPOR = 3
PERIODO_VAPOR = 3.2  # s que tarda una bocanada en subir y desvanecerse
SUBIDA_VAPOR = 70  # px
PERIODO_FALLA_ROTULO = 7.0  # s entre dos fallas de un rótulo
DURACION_FALLA_ROTULO = 0.18  # s que se apaga
# Agua: la textura se desplaza despacio (CUADROS_AGUA cuadros).
CUADROS_AGUA = 4
DURACION_CUADRO_AGUA = 0.3
DESPLAZAMIENTO_CUADRO_AGUA = 8  # px que avanza la textura por cuadro

# Casas (edificios secundarios): sprites completos en pixel art de código
# (src/ui/casas_render.py) con la plantilla de ESTILOS_CASA, a ESCALA_PIXEL
# y del tamaño exacto de su huella, apoyadas en su borde inferior. Dos
# plantillas cualesquiera difieren en al menos VARIACION_MINIMA_ESTILOS de
# sus atributos y dos casas vecinas nunca comparten plantilla.
GRADE_CIUDAD = GRADE_POR_DEFECTO  # props del pack Backrooms en la ciudad (antena, conos, letrero)
VARIACION_MINIMA_ESTILOS = 2
ATRIBUTOS_ESTILO = ("muro", "techo", "color_techo", "ventanas", "toldo")
ESTILOS_CASA = {
    "ladrillo": {"muro": (96, 46, 44), "junta": (70, 32, 32), "techo": "tejas", "color_techo": (60, 34, 40),
                 "ventanas": "doble", "toldo": False},
    "estuco": {"muro": (122, 108, 92), "junta": (96, 84, 72), "techo": "plano", "color_techo": (74, 68, 66),
               "ventanas": "banda", "toldo": False},
    "pizarra": {"muro": (44, 62, 92), "junta": (32, 46, 70), "techo": "mansarda", "color_techo": (30, 34, 46),
                "ventanas": "vertical", "toldo": False},
    "salvia": {"muro": (62, 90, 74), "junta": (46, 68, 56), "techo": "tejas", "color_techo": (36, 58, 52),
               "ventanas": "doble", "toldo": True},
    "terracota": {"muro": (140, 82, 56), "junta": (108, 60, 42), "techo": "terraza", "color_techo": (64, 92, 52),
                  "ventanas": "vertical", "toldo": True},
    "madera": {"muro": (92, 66, 48), "junta": (70, 50, 36), "techo": "mansarda", "color_techo": (48, 36, 32),
               "ventanas": "banda", "toldo": True},
}
COLOR_MARCO_CASA = (18, 16, 30)
COLOR_VIDRIO_CASA = (36, 44, 70)
COLORES_VENTANA_CASA = ((255, 204, 110), (255, 226, 160), (150, 220, 255), (255, 160, 200))
COLOR_PUERTA_CASA = (34, 26, 30)
COLOR_ESCALON_CASA = (96, 92, 104)
FRACCION_VENTANAS_ENCENDIDAS = 0.45
FRACCION_VENTANAS_PARPADEAN = 0.12  # de las encendidas: se apagan y prenden despacio
PERIODO_VENTANA = (9.0, 22.0)  # s de un ciclo de parpadeo (cada ventana el suyo)
# Hojas que caen en el parque y la zona escolar (muy sutiles).
CANTIDAD_HOJAS = 14
COLORES_HOJA = ((140, 170, 70), (200, 150, 60), (170, 90, 60))
LADO_CHUNK_CIUDAD = 512  # px: el fondo estático se cachea en cuadrados de este lado
