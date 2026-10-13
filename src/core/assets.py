"""Constantes visuales centralizadas (colores y tamaños placeholder).

Todo elemento visual nuevo del juego debe referenciar sus colores,
tamaños y velocidades desde aquí en lugar de usar valores hardcodeados
dispersos en la lógica. La versión actual usa placeholders (rectángulos
de color); cuando se agregue arte real, el cambio se limita a
reemplazar los valores de este archivo por rutas de sprite, sin tocar
la lógica de juego.
"""

# Jugador (comunes a los 4 roles). Velocidad, vida, daño, cadencia y
# carga de cada rol viven en src/core/balance.py.
TAMANIO_JUGADOR = 36
COLOR_CIUDADANO = (60, 140, 220)

# Proyectiles
TAMANIO_PROYECTIL = 8
COLOR_PROYECTIL_JUGADOR = (250, 240, 120)
COLOR_PROYECTIL_ENEMIGO = (230, 60, 60)
VELOCIDAD_PROYECTIL = 420  # píxeles por segundo
DANIO_PROYECTIL_ENEMIGO = 1

# Enemigo
TAMANIO_ENEMIGO = 40
COLOR_ENEMIGO = (230, 160, 20)
VELOCIDAD_ENEMIGO = 90  # píxeles por segundo
VIDA_ENEMIGO = 3
RANGO_DISPARO_ENEMIGO = 260  # píxeles
COOLDOWN_DISPARO_ENEMIGO = 1.2  # segundos entre disparos

# Texto en pantalla (indicador de colapso)
COLOR_TEXTO_HUD = (235, 235, 235)
TAMANIO_FUENTE_HUD = 28
POSICION_TEXTO_COLAPSO = (10, 10)
POSICION_TEXTO_CARGA = (10, 40)
POSICION_TEXTO_RESULTADO = (10, 70)

# Habilidad del Ciudadano: Burbuja Comunitaria
COLOR_BURBUJA = (120, 220, 200)
GROSOR_BURBUJA = 2
RADIO_BURBUJA = 70  # píxeles
DURACION_BURBUJA = 4.0  # segundos

# Terminal del minijuego de decisión
COLOR_FONDO_TERMINAL = (20, 22, 28)
COLOR_BORDE_TERMINAL = (120, 200, 255)
COLOR_TEXTO_TERMINAL = (235, 235, 235)
COLOR_OPCION_SELECCIONADA = (255, 220, 80)
COLOR_TIEMPO_TERMINAL = (230, 90, 90)
ANCHO_TERMINAL = 600
ALTO_TERMINAL = 220
GROSOR_BORDE_TERMINAL = 3
MARGEN_TERMINAL = 20
SEPARACION_LINEAS_TERMINAL = 50

# Selección de personaje: 4 columnas (una por rol) con barras de stats
POSICION_TITULO_SELECCION = (20, 60)
ORIGEN_COLUMNAS_SELECCION = (20, 130)  # esquina superior izq. de la 1ra columna
ANCHO_COLUMNA_SELECCION = 195
TAMANIO_FUENTE_SELECCION = 22
SEPARACION_FILAS_SELECCION = 30
DESPLAZAMIENTO_BARRA_X = 80  # de la etiqueta de la stat al inicio de su barra
ANCHO_MAXIMO_BARRA = 100  # ancho de la barra del rol con el valor máximo
ALTO_BARRA = 12
COLOR_FONDO_BARRA = (70, 74, 84)
COLOR_TEXTO_SECUNDARIO = (170, 175, 185)

# Influencer: cono de sonido (proyectil ancho que empuja) / Live Stream Viral
COLOR_INFLUENCER = (220, 80, 200)
COLOR_PROYECTIL_INFLUENCER = (250, 150, 240)
TAMANIO_PROYECTIL_INFLUENCER = 26
VELOCIDAD_PROYECTIL_INFLUENCER = 300  # píxeles por segundo
IMPULSO_EMPUJE_INFLUENCER = 30  # píxeles que retrocede el enemigo golpeado
DURACION_LIVE_STREAM = 3.0  # segundos de aggro forzado

# Periodista: rayo perforante / Fact-Checking
COLOR_PERIODISTA = (240, 240, 240)
COLOR_RAYO_PERIODISTA = (140, 220, 255)
COLOR_RAYO_FACT_CHECK = (90, 255, 140)
TAMANIO_RAYO = 10
VELOCIDAD_RAYO = 900  # píxeles por segundo
LARGO_ESTELA_RAYO = 40  # píxeles de la línea dibujada detrás del rayo
GROSOR_ESTELA_RAYO = 4

# Candidato: onda expansiva radial / Debate Rebotante
COLOR_CANDIDATO = (240, 170, 60)
COLOR_ONDA_CANDIDATO = (255, 200, 90)
GROSOR_ONDA = 3
RADIO_MAXIMO_ONDA = 90  # píxeles
DURACION_ONDA = 0.3  # segundos que tarda en expandirse
COLOR_PROYECTIL_REBOTANTE = (255, 120, 40)
ANGULOS_DEBATE_REBOTANTE = (-20, 0, 20)  # grados respecto a la mirada
MAXIMO_REBOTES = 3
TIEMPO_VIDA_REBOTANTE = 4.0  # segundos

# Mazmorra final: arena, jefe, charcos y "juice"
ANCHO_ARENA = 760
ALTO_ARENA = 470
CENTRO_ARENA = (400, 355)  # deja libre la franja superior para la barra del jefe
TAMANIO_JEFE = 90
COLOR_JEFE = (150, 60, 200)
COLOR_DESTELLO_JEFE = (255, 255, 255)
COLOR_ESCUDO_JEFE = (90, 230, 255)
GROSOR_ESCUDO_JEFE = 4
MARGEN_ESCUDO_JEFE = 8
PERIODO_PARPADEO_JEFE = 0.1  # s entre visible/invisible durante el cambio de fase
COLOR_PROYECTIL_JEFE = (255, 90, 160)
TAMANIO_PROYECTIL_JEFE = 12
ALFAS_ESTELA_JEFE = (150, 90, 40)  # de la posición más reciente a la más vieja
COLOR_CHARCO = (110, 210, 60)
ALFA_CHARCO_ACTIVO = 110
GROSOR_CONTORNO_CHARCO = 2
SHAKE_DURACION = 0.25
SHAKE_INTENSIDAD = 5  # px máximos de desplazamiento

# Barra de vida del jefe y textos de la mazmorra final
RECT_BARRA_JEFE = (220, 14, 360, 16)  # x, y, ancho, alto
COLOR_BARRA_JEFE = (200, 50, 90)
COLOR_FONDO_BARRA_JEFE = (60, 60, 70)
COLOR_MARCA_FASE = (255, 255, 255)
ANCHO_MARCA_FASE = 2
POSICION_TEXTO_FASE = (220, 36)
POSICION_TEXTO_TIEMPO_JEFE = (620, 10)
POSICION_MENSAJE_CENTRAL = (400, 90)  # centro del texto de victoria/derrota
COLOR_MENSAJE_VICTORIA = (120, 255, 160)
COLOR_MENSAJE_DERROTA = (255, 110, 110)
DURACION_MENSAJE = 2.5  # s que se muestra "Bloqueada" o la derrota
POSICION_MENSAJE_BLOQUEADA = (10, 70)  # mismo lugar que "Resultado": nunca coinciden
ESPACIADO_ESTELA_JEFE = 9  # px entre posiciones guardadas de la estela
COLOR_MURO_ARENA = (200, 200, 210)
GROSOR_MURO_ARENA = 4
SEPARACION_INVOCACION = 70  # px a cada lado del jefe donde aparecen súbditos
