# Manifiesto de assets del modo historia

Regla: **nada se genera con Higgsfield sin aprobación del equipo** (créditos). El
juego arranca completo sin ningún archivo de esta lista: cada imagen y video tiene un
fallback. Costos: Higgsfield los muestra al pedir una generación;
no se inventan aquí.

## Lo que ya se dibuja en código o con hojas existentes (reutilizado)
- Retratos de los 4 roles (`assets/sprites/retratos/<rol>.png`, 512 px, Higgsfield,
  ya existentes) → diálogos y selección.
- Hojas de sprites de roles, enemigos, jefe, cuarto, puertas, charco (Pixelbolt).
- Ciudad Nova, HUD, terminal, tarjetas, paneles, grafo social, elecciones: Pygame.
- Iconos de Civitas y NOVA_404 en los diálogos: dibujados en código
  (`dialogo_render._icono_sistema`).

## Style guide (inglés, para reutilizar sin gastar tokens)
Top-down 2D pixel-art-inspired cyberpunk civic mystery. Crisp readable silhouettes,
restrained teal (#3EE6C4) / violet (#A46EFF) / amber (#FFBE3C) palette on deep navy
(#0F0D22), consistent soft neon lighting, night city mood. No text, no watermark,
no UI typography, no logos. Original design, game-ready, 16:9 unless stated.

## Generadas el 3 nov 2026 (aprobadas por el equipo)
Modelo Higgsfield `nano_banana_2` (servido como nano_banana_flash), 1k, 1.5 créditos
cada una (12 créditos en total de 1200). Re-guardadas con pygame (sin metadatos
C2PA/XMP) y escaladas a 1280×720; retratos con fondo recortado a transparente, 512×512.

| Id | Archivo | Uso |
|---|---|---|
| A01 | `assets/story/portada.png` | Fondo del prólogo (`assets.FONDO_PROLOGO`). |
| A02 | `assets/sprites/retratos/civitas.png` | Retrato de Civitas en diálogos. |
| A02b | `assets/sprites/retratos/nova.png` | Retrato de NOVA_404 en diálogos. |
| A03 | `assets/story/capitulo_colegio.png`, `capitulo_hospital.png`, `capitulo_medios.png` | Fondo de la intro de cada capítulo (`assets.FONDO_POR_ZONA`). |
| A04 | `assets/story/servidor_central.png` | Fondo del diálogo pre-jefe. |
| A06 | `assets/story/elecciones.png` | Fondo de la pantalla de elecciones. |

Carga: `sprites.fondo_historia(nombre, tamanio)` con caché; `retrato_rol("civitas"/"nova")`.
Si falta un archivo, cada pantalla dibuja su versión anterior (velo / icono en código).

## Generadas el 3 nov 2026 (cinemáticas, 7,5 créditos de un tope autorizado de 12)
Modelo `nano_banana_2` (servido como nano_banana_flash), 16:9 1k (1376×768), **1,5 créditos cada una**
(costo verificado con `get_cost`), con `portada.png` como referencia de estilo. Re-guardadas con pygame
a 1280×720 sin metadatos. Prompts completos en `docs/PLAN_ASSETS_CINEMATICOS.md`.

| Id | Archivo | Uso |
|---|---|---|
| C01 | `assets/story/ciudadanos_civitas.png` | Intro: escenas «Civitas» y «El caos» (`assets.FONDO_CIUDADANOS`). |
| C02 | `assets/story/pantallas_nova.png` | Intro: «La amenaza»; cinemática de derrota global (`FONDO_PANTALLAS_NOVA`). |
| C03 | `assets/story/servidor_caido.png` | Caída del servidor y final «El arquitecto» (`FONDO_SERVIDOR_CAIDO`). |
| C04 | `assets/story/final_renace.png` | Final «Ciudad Nova renace» (`FONDO_POR_FINAL`). |
| C05 | `assets/story/final_dividida.png` | Final «La ciudad dividida». |

## Generadas el 5 nov 2026 (reputación y redención, 57 créditos)

Saldo: 1180,5 → 1123,5 (verificado con `balance`). Costos verificados con `get_cost` antes de
generar. Sin descartes: cada generación se usa en el juego. Referencias: `portada.png` para
lugares, retrato base para personajes, para que nadie cambie de cara.

| Id | Archivo | Modelo | Créditos | Uso |
|---|---|---|---|---|
| D01 | `assets/story/crisis_reputacion.png` | nano_banana_2 | 1,5 | Crisis |
| D02 | `assets/story/redencion.png` | nano_banana_2 | 1,5 | Elección, misión y recuperación |
| D03 | `assets/story/final_confianza_perdida.png` | nano_banana_2 | 1,5 | Final de derrota |
| D04 | `assets/story/nova_aparicion.png` | nano_banana_2 | 1,5 | Cuadro base del clip de NOVA_404 |
| D05 | `assets/sprites/retratos/rosa.png` | nano_banana_2 | 1,5 | Rosa Beltrán, la mediadora |
| D06 | `assets/sprites/retratos/<rol>_preocupado.png` y `<rol>_decidido.png` (8) | nano_banana_2 | 12 | Retratos según reputación |
| V01 | `assets/story/video/intro_ciudad/` | kling3_0, 5 s, sin sonido | 7,5 | Primera toma de la intro (recortado a 44 cuadros) |
| V02 | `assets/story/video/nova_aparicion/` | kling3_0 | 7,5 | Primera aparición de NOVA_404 |
| V03 | `assets/story/video/crisis/` | kling3_0 | 7,5 | Crisis (recortado a 34 cuadros: al final se deformaba) |
| V04 | `assets/story/video/redencion/` | kling3_0 | 7,5 | Recuperación |
| V05 | `assets/story/video/jefe/` | kling3_0 | 7,5 | Entrada al Servidor Central |

Se descartó Seedance 2.5 (35 créditos por clip de 5 s) porque Kling mantenía bien el pixel art.

Video: cuadros JPG de 1280×720 a 12 FPS (30 MB en total), extraídos con
`tools/extraer_cuadros.py`. El juego no necesita ffmpeg ni internet; si falta la carpeta,
la toma usa la ilustración con paneo. Clips con sonido apagado: el audio lo pone el juego.

Retratos: fondo verde quitado con `tools/procesar_retrato.py`.

## Audio (propio, sin costo ni licencias de terceros)

`tools/generar_audio.py` compone por síntesis matemática 10 pistas en `assets/musica/`
(menu, ciudad, combate, jefe, misterio, decision, crisis, redencion, victoria, derrota; 15 MB,
WAV de 22 kHz) y 15 efectos en `assets/sonidos/`. Si faltan, el juego sintetiza colchones y
pitidos. **Nadie las ha escuchado aún:** ver `docs/QA_VISUAL.md`.

## Escenarios (sin Higgsfield)

Colegio, Hospital, Medios y Servidor Central se pintan en código (`src/ui/temas_mazmorra.py`),
sin créditos: coherentes con los sprites y sin pixel art roto al escalar.

## Pendiente (opcional, sin generar)

| Id | Nombre lógico | Archivo esperado | Tamaño | Dónde se usaría | Fallback actual |
|---|---|---|---|---|---|
| A05 | Iconos de interfaz (pista, evidencia, candidato) | `assets/story/iconos/*.png` | 32×32, transparente | Tarjetas | Chips de texto |

## Procedencia y licencia
Todas las imágenes de `assets/story/` y los retratos de Civitas, NOVA_404, Rosa y las emociones: generados el 3 y 5 nov 2026
con Higgsfield (nano_banana_2) desde la cuenta del equipo, con los prompts del style guide
(sin texto ni logos), para uso en este proyecto académico. Se guardan en el repo; nunca se
referencian URL temporales en runtime.
