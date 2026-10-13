# Reglas del proyecto — Civitas (PruebaPythonGame)

## Identidad del proyecto

* Videojuego para el curso Estructura de Datos II, Ingeniería de Sistemas, Universidad del Norte.
* Meta final: demo en vivo en la VI Feria Gamer, 26 nov 2026.
* Stack: Python 3.14, `pygame-ce`, `venv`. **Prohibido usar librerías de terceros para árboles o grafos** — implementación manual obligatoria.
* Regla académica innegociable: ninguna estructura de datos puede ser decorativa. Todo árbol/grafo debe gobernar una mecánica real del juego (aunque sea lógica de fondo, no una interfaz que el jugador navega) y ser explicable en voz alta (complejidad, diseño).

## Visión completa del juego

Civitas es un action-RPG top-down **cooperativo, de 1 a 4 jugadores** (soporta solitario). Inspirado en *The Binding of Isaac*: el jugador recorre libremente Ciudad Nova (hub abierto) y entra físicamente a distintas mazmorras repartidas por la ciudad.

Cada zona de la ciudad tiene un **nivel de toxicidad por mal uso de redes/internet** propio de su contexto: un colegio con mucho ciberbullying genera una mazmorra de dificultad alta (más enemigos, más agresivos); una empresa con acoso leve genera una mazmorra más fácil. La dificultad de cada mazmorra se deriva de ese nivel de toxicidad, no es fija.

Dentro de cada mazmorra: cuartos cerrados, puertas selladas al entrar, enemigos con agresividad absoluta (nunca huyen), la puerta se abre al limpiar el 100% del cuarto — igual que Isaac.

**Importante — lo que NO es el juego:** el jugador **no navega menús de árbol** (nada de "Verificar / Compartir / Reportar / Ignorar" como interacción). El árbol de decisión es lógica de fondo (ver sección dedicada), invisible para el jugador durante el combate.

## Cuarto final de cada mazmorra: minijuego + defensa

El cuarto final no se resuelve solo peleando ni navegando un árbol — es **minijuego + combate simultáneo**:
* Un jugador del equipo queda "resolviendo" el minijuego (una mecánica de habilidad/tiempo, a definir en detalle — ej. QTE, secuencia, precisión).
* El resto del equipo (o el mismo jugador si es solitario, alternando) debe **defenderlo** de oleadas de enemigos usando las habilidades activas de su rol.
* Si el equipo protege al que resuelve el minijuego hasta completarlo → mazmorra purificada. Si el jugador que resuelve muere o el minijuego falla → detonación.
* Este es el evento contra reloj (10s en mazmorras normales, 5s en mazmorras avanzadas) — el reloj corre sobre el minijuego, no sobre un menú de árbol.

*(Nota: el diseño exacto del minijuego —qué se hace, cómo se ve— queda abierto; se define en un prompt aparte cuando se vaya a construir.)*

## Árbol de decisión (lógica de fondo, NO interfaz del jugador)

El árbol N-ario manual se usa para **clasificar y procesar publicaciones/reportes de toxicidad** al generar cada mazmorra — esto es lo que determina su nivel de dificultad, no algo que el jugador opera en tiempo real:

* Cada nodo del árbol representa una publicación/reporte con su tipo y gravedad (ej. comentario, publicación viral, denuncia).
* Recorrer el árbol (preorden/inorden/postorden/niveles) permite calcular el nivel agregado de toxicidad de una zona.
* Ese resultado alimenta la generación de la mazmorra: cantidad de enemigos, agresividad, tipo de spawns.
* Esto corre en el backend al entrar a la mazmorra — el jugador ve el resultado (una mazmorra más difícil o más fácil), nunca la estructura en sí.

Esto es lo que se sustenta ante la profesora: "el árbol procesa reportes de toxicidad y decide la dificultad de la mazmorra" — sigue siendo una estructura que resuelve un problema real del juego, solo que no es una pantalla de menú.

## Colapso Electoral
Barra 0.0%-100.0%. +0.2% por incursión fallida o muerte del equipo en mazmorra.
-0.1% por mazmorra purificada (restaura indicadores de convivencia).

## Mazmorra Imposible — "El Servidor Central"
En la Alcaldía. Se desbloquea al superar una mazmorra intermedia o si el colapso global escala a >80%. Cierre en vivo de la demo en la Feria: timer 180s, bullet hell, charcos tóxicos, enemigos con escudos de anonimato. Fuera de alcance del MVP actual.

## Los 4 roles jugables
Cada uno: ataque básico + activa con cooldown, usada tanto en combate normal como para defender al compañero en el minijuego del cuarto final. Sinergia: Influencer agrupa, Periodista expone, Candidato remata, Ciudadano sostiene.

* Influencer: cono de sonido expansivo (empuja) / Live Stream Viral (12s, fija aggro de todos los enemigos del cuarto hacia él por 3s)
* Periodista: rayo perforante lineal / Fact-Checking (10s, destruye escudos de anonimato de enemigos atrapados)
* Ciudadano: abanico frontal de 3 proyectiles / Burbuja Comunitaria (15s, domo que frena proyectiles hostiles y regenera vida de aliados dentro)
* Candidato: onda expansiva radial / Debate Rebotante (8s, proyectiles que rebotan en paredes)

MVP actual solo implementa Ciudadano; los otros 3 son visión futura, no crear código placeholder para ellos todavía.

## Estructura de carpetas obligatoria
```text
PruebaPythonGame/
│-- main.py
│-- requirements.txt
│-- assets/
│-- src/
│   │-- core/          # constantes, configuración de pantalla, reloj
│   │-- structures/     # árboles y grafos puros, sin dependencias de Pygame
│   │-- entities/       # jugadores (roles), proyectiles, enemigos
│   │-- dungeon/        # cuartos, puertas, spawners
│   │-- ui/             # HUD de colapso, cintillo, pantallas de carga
│   └-- network/        # protocolo sockets, serialización, server/client
```
No mezclar responsabilidades entre carpetas. `structures/` no debe importar `pygame`.

## Alcance ACTUAL — lo único que se construye ahora (Entrega 1, MVP)

1. `src/structures/tree.py`: árbol manual con insertar, eliminar, buscar, y los 4 recorridos (preorden, inorden, postorden, por niveles). Docstrings con la complejidad de cada operación.
2. Un solo cuarto en Pygame: puertas se bloquean al entrar, se liberan al limpiar el 100% de enemigos.
3. Behavior tree mínimo (Selector → Sequence: perseguir + disparar) para 2-3 enemigos. Comentar en el código qué nodo se ejecuta en cada frame.
4. Un solo personaje jugable: Ciudadano (abanico de 3 proyectiles). La clase base debe quedar lista para extenderse a los otros 3 roles después, sin reescritura.
5. Demo mínima de `tree.py` clasificando reportes de toxicidad y devolviendo un nivel de dificultad — conectado conceptualmente al spawn de enemigos del cuarto, sin necesidad de construir el minijuego completo del cuarto final todavía.
6. Variable de colapso simple (número que sube/baja, mostrado como texto en pantalla — sin HUD elaborado).

## Estado real del MVP (no la lista aspiracional)

1. `tree.py` con CRUD/recorridos — completado
2. Cuarto con puertas bloqueables y spawn placeholder — completado
3. Behavior tree (Selector→Sequence) + Ciudadano + proyectiles — completado
4. `docs/ARQUITECTURA.md` — completado
5. Conectar `tree.py` como clasificador de toxicidad que alimenta la dificultad del cuarto — pendiente, siguiente paso (reemplaza el diseño anterior de "terminal navegable")
6. Variable de colapso simple en pantalla — pendiente

No agregues código de Influencer, Periodista, Candidato, Ciudad Nova, sockets, Mazmorra Imposible, el minijuego del cuarto final, ni `graph.py` salvo que se te pida explícitamente — son alcance de entregas futuras.

## NO implementar todavía (a menos que se pida explícitamente)

* Sockets / red multijugador (Entrega Final)
* Los otros 3 roles jugables (Influencer, Periodista, Candidato)
* Ciudad Nova / hub abierto — usar transición directa "entrar a mazmorra" → cuarto
* Ticker de noticias en vivo
* Accesibilidad (daltonismo/alto contraste) y feedback sonoro pulido (Entrega Final)
* Mazmorra imposible / patrones bullet hell
* El minijuego del cuarto final (se diseña en detalle cuando se vaya a construir)
* `src/structures/graph.py` y cualquier lógica de grafos (Entrega 2)

## Convenciones de código

* Un módulo, una responsabilidad. No implementar varias piezas del MVP en un mismo archivo/commit si no se pidió así.
* Priorizar código explicable sobre código optimizado en exceso — se sustenta en voz alta ante la profesora.
* Todo árbol/grafo debe exponer sus operaciones de forma que se puedan probar de forma aislada (sin Pygame).
* Todo elemento visual (cuartos, personajes, enemigos, proyectiles) debe referenciar una constante o ruta de sprite definida en un solo lugar (ej. `src/core/assets.py`), nunca un color hardcodeado disperso en la lógica del juego.
* La versión actual usa placeholders (rectángulos de color) de forma intencional mientras se valida la mecánica. Cuando se agregue arte real, el cambio debe limitarse a reemplazar la ruta del sprite en ese archivo central — no debe requerir tocar la lógica de juego.

## Instrucciones de Git

* Al hacer commits, NO incluyas la línea "Co-Authored-By: Claude" ni ninguna línea de atribución a Claude/Anthropic en el mensaje del commit.
* No modifiques `git config user.name` ni `user.email` del repo bajo ninguna circunstancia.

## Fechas relevantes

* Entrega 1 (árboles): propuesta del equipo — 22 sep 2026
* Entrega 2 (grafos): 19-23 oct 2026
* Entrega Final (integración + red): 16-20 nov 2026
* Feria Gamer: 26 nov 2026