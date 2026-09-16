# Reglas del proyecto — Civitas (PruebaPythonGame)

## Identidad del proyecto
- Videojuego para el curso Estructura de Datos II, Ingeniería de Sistemas, Universidad del Norte.
- Meta final: demo en vivo en la VI Feria Gamer, 26 nov 2026.
- Stack: Python 3.14, `pygame-ce`, `venv`. **Prohibido usar librerías de terceros para árboles o grafos** — implementación manual obligatoria.
- Regla académica innegociable: ninguna estructura de datos puede ser decorativa. Todo árbol/grafo debe gobernar una mecánica real del juego y ser explicable en voz alta (complejidad, diseño).

## Concepto general (para mantener coherencia narrativa y de nombres)
- Hub top-down "Ciudad Nova" + mazmorras cerradas estilo *The Binding of Isaac*.
- Métrica de Colapso Global 0-100%: +0.2% por incursión fallida, -0.1% por mazmorra purificada.
- 4 roles jugables (diseño completo, no todos implementados aún): Influencer, Periodista, Ciudadano, Candidato.
- Árbol de decisión contra reloj en terminal de cada mazmorra.
- Behavior tree para enemigos (Selector, Sequence, Action).
- Grafo de cuartos (BFS de propagación) y grafo espacial de la ciudad (pesos dinámicos) — diseño futuro, Entrega 2.

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
5. Terminal de decisión contra reloj, conectada al árbol de `tree.py`, navegable con teclado.
6. Variable de colapso simple (número que sube/baja, mostrado como texto en pantalla — sin HUD elaborado).

## NO implementar todavía (a menos que se pida explícitamente)
- Sockets / red multijugador (Entrega Final)
- Los otros 3 roles jugables (Influencer, Periodista, Candidato)
- Ciudad Nova / hub abierto — usar transición directa "entrar a mazmorra" → cuarto
- Ticker de noticias en vivo
- Accesibilidad (daltonismo/alto contraste) y feedback sonoro pulido (Entrega Final)
- Mazmorra imposible / patrones bullet hell
- `src/structures/graph.py` y cualquier lógica de grafos (Entrega 2)

## Convenciones de código
- Un módulo, una responsabilidad. No implementar varias piezas del MVP en un mismo archivo/commit si no se pidió así.
- Priorizar código explicable sobre código optimizado en exceso — se sustenta en voz alta ante la profesora.
- Todo árbol/grafo debe exponer sus operaciones de forma que se puedan probar de forma aislada (sin Pygame).
- Todo elemento visual (cuartos, personajes, enemigos, proyectiles)
  debe referenciar una constante o ruta de sprite definida en un solo
  lugar (ej. src/core/assets.py), nunca un color hardcodeado disperso
  en la lógica del juego.
- La versión actual usa placeholders (rectángulos de color) de forma
  intencional mientras se valida la mecánica. Cuando se agregue arte
  real, el cambio debe limitarse a reemplazar la ruta del sprite en
  ese archivo central — no debe requerir tocar la lógica de juego.

## Fechas relevantes
- Entrega 1 (árboles): propuesta del equipo — 22 sep 2026
- Entrega 2 (grafos): 19-23 oct 2026
- Entrega Final (integración + red): 16-20 nov 2026
- Feria Gamer: 26 nov 2026
