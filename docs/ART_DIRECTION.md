# Dirección de arte de Civitas: Código Nova

Guía para que todo lo que se agregue se vea del mismo juego. Si una pantalla nueva
contradice este documento, se cambia la pantalla, no el documento.

## La idea

Misterio urbano, de noche, en una ciudad cuya vida pasa por una red social. Cyberpunk
**moderado**: pantallas y neón sí; implantes, armas futuristas y distopía extrema no. Es
una ciudad reconocible con colegios, hospitales y vecinos. El peligro no es una máquina
de guerra: es lo que la gente cree.

## Paleta: cada color significa una sola cosa

Los tokens viven en `src/core/assets.py`. Nunca se escribe un color suelto en una pantalla.

| Color | Token | Significado | Dónde se ve |
|---|---|---|---|
| Azul oscuro | `COLOR_NOCHE`, `COLOR_FONDO` | La ciudad y la tecnología | Fondos, paneles |
| Violeta | `COLOR_CIVITAS` | Civitas y el foco de la interfaz | Selección, rótulos, árbol |
| Cian | `COLOR_VERIFICADO` | Información verificada | Pruebas, correcciones, reputación alta |
| Magenta | `COLOR_NOVA` | La manipulación de NOVA_404 | Rumores, huellas en cuartos infectados |
| Ámbar | `COLOR_ALERTA` | Advertencia | Misión, reloj, oportunidades |
| Rojo | `COLOR_GRAVE` | Consecuencia grave | Crisis, final de derrota |

Regla de oro: **en la terminal de decisión el foco siempre es violeta**. Si las opciones
usaran cian o rojo, el color le diría al jugador cuál es la respuesta.

## Tres capas visuales

1. **Gameplay en pixel art.** 1 píxel de arte = 3 px en pantalla. Contorno oscuro, luz
   desde arriba. Personajes de 16×20 con Pixelbolt; escenarios pintados en código
   (`src/ui/temas_mazmorra.py`).
2. **Ilustraciones de historia en pixel art detallado.** 1280×720, misma ciudad y misma
   familia de color que `assets/story/portada.png`, que es la referencia de todas.
3. **Interfaz en vectores limpios.** Paneles de vidrio oscuro con un filo de color
   (`src/ui/kit.py`) y JetBrains Mono. Texto, botones y valores siempre se dibujan por
   código: **ninguna imagen generada lleva texto**.

## Personajes

| Quién | Cómo se ve | Se reconoce por |
|---|---|---|
| Ciudadano | Chaqueta verde azulado, pelo rizado | Pancarta |
| Influencer | Sudadera rosa, pelo con mechas | Palo de selfie |
| Periodista | Bata blanca, gafas redondas, coleta | Micrófono y libreta |
| Candidato | Traje azul, corbata y escarapela amarillas, canas | Postura formal |
| Rosa Beltrán | Abrigo violeta, moño canoso, aretes | Tableta y credencial |
| NOVA_404 | Capucha magenta y violeta, sin rostro, estática adentro | Vacío donde va la cara |

Retratos: estilo chibi de 512 px, generados tomando el retrato base como referencia. Cada
rol tiene tres estados: base, `_preocupado` y `_decidido`. El diálogo elige solo según la
reputación (a -20 o menos se ve preocupado; a +20 o más, decidido).

## Lugares

Se debe reconocer el lugar sin leer el título. Todos comparten composición: cara del muro
de 36 px arriba (tan alta como un personaje, así la perspectiva 3/4 funciona con la misma
colisión), piso, mobiliario bajo desaturado y luz horneada.

| Lugar | Piso | Muro | Mobiliario | Luz | Vive porque |
|---|---|---|---|---|---|
| Colegio | Tablones de madera | Crema y friso verde, pizarra, tablero de avisos, reloj | Filas de pupitres, hojas tiradas | Cálida, de ventana | La pantalla de avisos parpadea |
| Hospital | Baldosa clínica con guías de color | Azulejo pálido, franja de seguridad, cruz | Camillas, suero, biombos, carros | Fluorescente fría | Monitores de ritmo cardíaco, alerta roja |
| Medios | Alfombra técnica | Paneles acústicos y muro de pantallas | Escritorios con monitores, cámaras, cables, bastidores | Focos magenta y cian | Noticias que cambian, letrero al aire |
| Servidor Central | Placas negras con circuitos hacia un núcleo | Torres de servidores | Cables gruesos que bajan | Magenta desde el núcleo | Onda que sale del núcleo, señal por las torres |

Lo que se ve más allá de los muros también cuenta: casilleros, pasillo clínico o racks.
Las grietas magenta crecen con la toxicidad del cuarto.

**Legibilidad primero:** nada del fondo compite con personajes y balas. Si un mueble se
confunde con un enemigo, se oscurece el mueble.

## Interfaz

- Un solo modal a la vez. Velo oscuro detrás, el mundo se sigue intuyendo.
- Jerarquía fija: rótulo pequeño en mayúsculas, valor o frase grande, detalle.
- Entrada corta (ease-out de 0,25 s). Nada rebota. «Reducir movimiento» quita lo decorativo.
- Texto largo: se pagina, no se recorta. El «…» solo se tolera en datos de apoyo, nunca
  en narrativa.
- El estado de foco siempre es el mismo: filo y fondo violeta con un latido leve.

## Cinemáticas

Fundidos cruzados, franjas de cine y subtítulos abajo con quién habla. Los videos son
clips cortos que parten de una ilustración existente, para que nada cambie de cara. Una
escena sin video no es peor: paneo lento continuo sobre la ilustración.

## Pantallas: qué se aplica a cada una

| Pantalla | Base | Acento |
|---|---|---|
| Menú principal | Ciudad pixel art con parallax | Violeta |
| Selección de personaje | Ilustración de la ciudad velada; retrato decidido al enfocar | Color del rol |
| Lobby | Sala tipo vestidor con vestidores (personalización) | Cian y ámbar |
| Ciudad Nova | Mapa de casillas | Auras por toxicidad |
| Diálogos | Escena velada, retrato según reputación | Violeta |
| Árbol de decisiones | Trama de consola oscura | Violeta |
| Reputación | Velo sobre la escena; barra con cero al centro | Cian o magenta |
| Crisis | Ilustración roja | Rojo |
| Redención | Ilustración al amanecer | Cian |
| Elecciones | Ilustración de la plaza | Por candidato |
| Finales | Ilustración según el final | Según el final |

## Generar arte nuevo

1. Primero reutilizar o animar en Pygame lo que ya existe.
2. `get_cost` antes de generar; registrar el gasto en `docs/ASSET_MANIFEST.md`.
3. Referencia obligatoria: `portada.png` para lugares, el retrato base para personajes.
4. Prompt: pedir la misma técnica de la referencia, terminar con «no text, no letters, no
   numbers, no logos». Para retratos, fondo verde `#00FF00` y `tools/procesar_retrato.py`.
5. Revisar el cuadro final de cada video: suelen deformarse al terminar (se recortan).
