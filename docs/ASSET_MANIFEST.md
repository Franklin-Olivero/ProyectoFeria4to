# Manifiesto de assets del modo historia

Regla: **nada se genera con Higgsfield sin aprobación del equipo** (créditos). El
juego arranca completo sin ningún archivo de esta lista: cada imagen tiene un
fallback dibujado en Pygame. Costos: Higgsfield los muestra al pedir una generación;
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

## Pendiente (opcional, sin generar)

| Id | Nombre lógico | Archivo esperado | Tamaño | Dónde se usaría | Fallback actual |
|---|---|---|---|---|---|
| A05 | Iconos de interfaz (pista, evidencia, candidato) | `assets/story/iconos/*.png` | 32×32, transparente | Tarjetas | Chips de texto |

## Procedencia y licencia
Todas las imágenes de `assets/story/` y `civitas.png`/`nova.png`: generadas el 3 nov 2026
con Higgsfield (nano_banana_2) desde la cuenta del equipo, con los prompts del style guide
(sin texto ni logos), para uso en este proyecto académico. Se guardan en el repo; nunca se
referencian URL temporales en runtime.
