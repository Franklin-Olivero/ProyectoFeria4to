"""Constantes visuales centralizadas (colores y tamaños placeholder).

Todo elemento visual nuevo del juego debe referenciar sus colores,
tamaños y velocidades desde aquí en lugar de usar valores hardcodeados
dispersos en la lógica. La versión actual usa placeholders (rectángulos
de color); cuando se agregue arte real, el cambio se limita a
reemplazar los valores de este archivo por rutas de sprite, sin tocar
la lógica de juego.
"""

# Jugador (comunes a los 4 roles)
TAMANIO_JUGADOR = 36
COLOR_CIUDADANO = (60, 140, 220)
VELOCIDAD_JUGADOR = 220  # píxeles por segundo
VIDA_JUGADOR = 5

# Proyectiles
TAMANIO_PROYECTIL = 8
COLOR_PROYECTIL_JUGADOR = (250, 240, 120)
COLOR_PROYECTIL_ENEMIGO = (230, 60, 60)
VELOCIDAD_PROYECTIL = 420  # píxeles por segundo
DANIO_PROYECTIL_JUGADOR = 1
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

# Selección de personaje
POSICION_TITULO_SELECCION = (60, 180)
POSICION_OPCIONES_SELECCION = (60, 240)
SEPARACION_OPCIONES_SELECCION = 40

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
