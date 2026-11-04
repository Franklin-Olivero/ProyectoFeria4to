# Plan de assets cinematográficos — Civitas: Código Nova

Presupuesto autorizado: **12 créditos de Higgsfield** para nuevas generaciones.
Costo verificado con `get_cost` el 3 nov 2026: `nano_banana_2`, 16:9, 1k = **1,5 créditos por imagen**.
Plan ejecutado: **5 imágenes = 7,5 créditos** (quedan 4,5 sin usar del tope).
No se genera video: el costo de video no estaba cubierto por el tope y la cinemática se
resuelve con ilustraciones animadas en Pygame (paneo lento, fundidos, glitch, notificaciones).

El juego arranca completo sin ninguno de estos archivos: cada toma tiene un fondo de
respaldo dibujado en código (`cinematica_render._fondo_en_codigo`).

## Style guide (se repite en cada prompt)
Top-down-inspired 2D pixel-art cyberpunk civic mystery. Crisp readable silhouettes,
restrained teal (#3EE6C4) / violet (#A46EFF) / amber (#FFBE3C) palette on deep navy
(#0F0D22), soft neon lighting, night city mood. No text, no letters, no watermark, no
UI typography, no logos. Original design, game illustration, 16:9.

## Assets reutilizados (ya existían, 0 créditos)

| Archivo | Uso en las cinemáticas |
|---|---|
| `assets/story/portada.png` | Escena 1 (Ciudad Nova), 5 (mensaje), 6 (protagonista), rol, título, objetivos, amanecer tras el jefe, fondo genérico. |
| `assets/story/capitulo_colegio.png` / `capitulo_hospital.png` / `capitulo_medios.png` | Tarjetas de capítulo 1-3 y sus diálogos. |
| `assets/story/servidor_central.png` | Cinemática de entrada al jefe y primera toma de la caída. |
| `assets/story/elecciones.png` | Pantalla de elecciones. |
| `assets/sprites/retratos/<rol>.png` (4) | Protagonista en la cinemática y en los diálogos. |
| `assets/sprites/retratos/civitas.png`, `nova.png` | Retratos de los sistemas en diálogos. |

## Assets nuevos (generados el 3 nov 2026)

| Id | Archivo | Función | Resolución / formato | Prioridad | Prompt |
|---|---|---|---|---|---|
| C01 | `assets/story/ciudadanos_civitas.png` | Escenas 2 y 3 de la intro (la red viva / el caos). Sobre ella se dibujan en código las notificaciones que se multiplican. | 1280×720 PNG (desde 16:9 1k) | 2 (cinemática inicial) | Pixel-art night plaza in a cyberpunk city, a crowd of diverse citizens seen from slightly above, each face lit by the glow of a smartphone, floating soft holographic speech-bubble shapes above the crowd (empty, no text), teal and violet neon signs, wet pavement reflections, deep navy sky. Style guide. |
| C02 | `assets/story/pantallas_nova.png` | Escena 4 (la amenaza): las pantallas de la ciudad fallan; también la derrota global. | 1280×720 PNG | 3 (amenaza NOVA_404) | Pixel-art cyberpunk street at night, every billboard and giant screen glitching with magenta static and broken scanlines, a hooded faceless silhouette looming inside the largest screen, citizens below looking up, teal/violet/amber neon, deep navy, ominous mood. Style guide. |
| C03 | `assets/story/servidor_caido.png` | Caída del Servidor Central (tras la victoria) y final «El arquitecto». | 1280×720 PNG | 5 (introducción/cierre del jefe) | Pixel-art underground server hall after shutdown: tall black server towers with dead cables, a last dim magenta light fading at the core, soft teal emergency lights returning along the floor, dust in the air, wide shot, calm after the storm. Style guide. |
| C04 | `assets/story/final_renace.png` | Final «Ciudad Nova renace». | 1280×720 PNG | 6 (escena final) | Pixel-art city plaza at dawn, warm amber sunrise over cyberpunk towers, citizens of all ages talking face to face, phones put away, a clean bright public screen showing only a soft teal glow (no text), hopeful, wide shot. Style guide. |
| C05 | `assets/story/final_dividida.png` | Final «La ciudad dividida». | 1280×720 PNG | 6 (escena final) | Pixel-art city plaza at night split in two halves by a dark street, two crowds facing each other, left half lit magenta, right half lit teal, barricades and scattered flyers on the ground, screens still glitching faintly, tense mood, wide shot. Style guide. |

Referencias visuales: `portada.png` y `capitulo_colegio.png` (misma paleta y grano);
se pasaron como `medias` de referencia cuando el modelo lo permitió.

## Post-proceso
Cada imagen se descarga a una carpeta nueva, se abre con pygame, se escala a 1280×720 con
`smoothscale` y se vuelve a guardar (sin metadatos C2PA/XMP), igual que los 8 assets previos.
Nunca se referencia una URL temporal en runtime.

## No generado (prompts listos por si se aprueba más presupuesto)
| Id | Función | Prompt |
|---|---|---|
| C06 | Clip de video de 4 s para la escena 1 (paneo real sobre la ciudad) | Image-to-video from `portada.png`: slow push-in over the night city, neon flicker, light rain, no camera shake. |
| C07 | Iconos 32×32 (pista, evidencia, candidato) | Pixel-art 32px icons, flat, two-tone teal/amber, transparent background: magnifying glass, folded document, ballot box. |
