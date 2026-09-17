# Reglas del proyecto — Civitas (PruebaPythonGame)

## Identidad del proyecto
- Videojuego para el curso Estructura de Datos II, Ingeniería de Sistemas, Universidad del Norte.
- Meta final: demo en vivo en la VI Feria Gamer, 26 nov 2026.
- Stack: Python 3.14, `pygame-ce`, `venv`. **Prohibido usar librerías de terceros para árboles o grafos** — implementación manual obligatoria.
- Regla académica innegociable: ninguna estructura de datos puede ser decorativa. Todo árbol/grafo debe gobernar una mecánica real del juego y ser explicable en voz alta (complejidad, diseño).

## Visión completa del juego
Civitas es un action-RPG top-down cooperativo (2-4 jugadores). Exploración en
"Ciudad Nova" (hub top-down estilo Pokémon, cintillo "Breaking News Civitas").
Combate en mazmorras cerradas estilo The Binding of Isaac dentro de edificios
(Colegio, Hospital, Empresa de Medios, Alcaldía): puertas se sellan al entrar,
enemigos con agresividad absoluta (nunca huyen), puerta se abre solo al limpiar
100% de enemigos.

## Concepto general (para mantener coherencia narrativa y de nombres)
- Hub top-down "Ciudad Nova" + mazmorras cerradas estilo *The Binding of Isaac*.
- Métrica de Colapso Electoral 0-100% (ver sección dedicada abajo).
- 4 roles jugables (diseño completo, no todos implementados aún): Influencer, Periodista, Ciudadano, Candidato — ver sección dedicada abajo.
- Árbol de decisión contra reloj en terminal de cada mazmorra — ver sección dedicada abajo.
- Behavior tree para enemigos (Selector, Sequence, Action).
- Grafo de cuartos (BFS de propagación) y grafo espacial de la ciudad (pesos dinámicos) — diseño futuro, Entrega 2.

## Terminal de decisión (árbol N-ario)
Raíz "Publicación Viral" → Verificar / Compartir / Reportar / Ignorar →
Contrastar con fuente oficial / Creer rumor → Purificación Exitosa / Detonación.
Contra reloj: 10s normal, 5s en la mazmorra final.

## Colapso Electoral
Barra 0.0%-100.0%. +0.2% por incursión fallida o muerte del equipo en mazmorra.
-0.1% por mazmorra purificada (restaura indicadores de convivencia).

## Mazmorra Imposible — "El Servidor Central"
En la Alcaldía. Se desbloquea al superar mazmorra intermedia o si colapso >80%.
Cierre de la demo en Feria: timer 180s, bullet hell, charcos tóxicos, enemigos
con escudos de anonimato. Fuera de alcance del MVP actual.

## Los 4 roles jugables
Cada uno: ataque básico + activa con cooldown. Sinergia: Influencer agrupa,
Periodista expone, Candidato remata, Ciudadano sostiene.
- Influencer: cono de sonido expansivo (empuja) / Live Stream Viral (12s, fija
  aggro de todos los enemigos del cuarto hacia él por 3s)
- Periodista: rayo perforante lineal / Fact-Checking (10s, destruye escudos de
  anonimato de enemigos atrapados)
- Ciudadano: abanico frontal de 3 proyectiles / Burbuja Comunitaria (15s, domo
  que frena proyectiles hostiles y regenera vida de aliados dentro)
- Candidato: onda expansiva radial / Debate Rebotante (8s, proyectiles que
  rebotan en paredes)
MVP actual solo implementa Ciudadano; los otros 3 son visión futura, no crear
código placeholder para ellos todavía.

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

## Estado real del MVP (no la lista aspiracional)
1. `tree.py` con CRUD/recorridos — completado
2. Cuarto con puertas bloqueables y spawn placeholder — completado
3. Behavior tree (Selector→Sequence) + Ciudadano + proyectiles — completado
4. `docs/ARQUITECTURA.md` — completado
5. Terminal de decisión contra reloj conectada a `tree.py` — pendiente, siguiente paso
6. Variable de colapso simple en pantalla — pendiente

No agregues código de Influencer, Periodista, Candidato, Ciudad Nova, sockets,
Mazmorra Imposible ni `graph.py` salvo que se te pida explícitamente — son
alcance de entregas futuras.

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


## Instrucciones de Git

- Al hacer commits, NO incluyas la línea "Co-Authored-By: Claude" ni ninguna
  línea de atribución a Claude/Anthropic en el mensaje del commit.

## Fechas relevantes
- Entrega 1 (árboles): propuesta del equipo — 22 sep 2026
- Entrega 2 (grafos): 19-23 oct 2026
- Entrega Final (integración + red): 16-20 nov 2026
- Feria Gamer: 26 nov 2026
