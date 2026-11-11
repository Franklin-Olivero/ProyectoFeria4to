# Guía de sustentación: respuestas breves y defendibles

Estructura de Datos II · Civitas: Código Nova. Cada respuesta cabe en 20-40 segundos.

## Árbol N-ario
**¿Dónde está y qué gobierna?** `src/structures/tree.py` (manual, sin librerías).
Gobierna (1) la dificultad de cada mazmorra: el árbol de reportes de toxicidad de la
zona se recorre y su promedio da el nivel; (2) la terminal de decisión: el jugador
navega el árbol de la zona hasta una hoja; (3) los diálogos no, son listas.

**Inserción / búsqueda / eliminación.** `insertar(id_padre, id, etiqueta)` busca al
padre con DFS: O(n). `buscar(id)`: DFS, O(n). `eliminar(id)`: busca al padre O(n) y
quita el hijo; el subárbol se libera (garbage collector). No hay índice id→nodo a
propósito: el costo se explica en voz alta. Demo: `tests/test_tree.py` y
`test_story_escenarios.py::test_crud_y_recorridos_del_arbol_sobre_un_escenario`
(inserta «Pedir contexto», elimina «Compartir» y su hoja).

**Recorridos.** Preorden, postorden y por niveles (cola `deque`) son O(n). El
«inorden» de un N-ario no está definido de forma única: el nuestro visita el primer
hijo, el nodo y el resto de hijos (documentado en el código). En la terminal el
render usa el camino raíz→nodo actual (DFS) y por niveles para posicionar.

**¿Por qué la evidencia cambia el resultado sin cambiar el árbol?** Las hojas tienen
ids fijos; la consecuencia asociada a cada hoja se resuelve al construir el árbol
según el estado de evidencia (`por_evidencia`). Así host e invitado en Online
comparten ids y «Publicar aclaración sin pruebas» puede detonar.

## Grafos
**¿Cuántos grafos hay?** Tres, todos sobre `src/structures/graph.py` (lista de
adyacencia `nodo -> {vecino: peso}`, O(V+E) memoria):
1. **Cuartos de la mazmorra**: DFS aleatorio para generar el layout (+1 arista = ciclo),
   BFS para el cuarto final y la propagación de toxicidad, `es_conexo` para garantizar
   que el final no desconecta.
2. **Calles de Ciudad Nova**: **Dijkstra** con `MinHeap` manual para la ruta sugerida;
   pesos dinámicos; barricadas solo si la ciudad sigue conexa (DFS).
3. **Red social** (nuevo): BFS para la propagación de una publicación, DFS para el
   rastreo de origen.

**BFS vs DFS vs Dijkstra.** BFS visita por capas → distancia en saltos exacta
(cuartos, capas de contagio). DFS sigue un hilo hasta el final → alcanzabilidad y
conectividad (conexo, rastreo). Dijkstra suma pesos → la ruta más segura cuando las
calles tienen saturación distinta. Complejidades: BFS/DFS O(V+E); Dijkstra
O((V+E) log V) con montículo binario.

**¿La propagación cuenta dos veces?** No: el BFS lleva un conjunto de visitados;
aunque Ana reciba el rumor por Hugo y por Camila, entra una sola vez, en su capa.
Test: `test_bfs_no_cuenta_dos_veces_y_respeta_saltos`.

**¿La corrección borra el rumor?** No. Marca `corregidos` (rebotan con 0.25 en vez
de 0.70) y deja `expuestos` intacto. Las propagaciones siguientes (eventos) alcanzan
menos. Test: `test_correccion_reduce_rebotes_sin_borrar_la_memoria`.

## Montículo mínimo
`src/structures/min_heap.py`: binario, en lista; `insertar` y `extraer_minimo`
O(log n). Lo usa Dijkstra con borrado perezoso (una entrada vieja se descarta al
salir si su distancia ya no coincide).

## Aleatoriedad
Toda la aleatoriedad va por `random.Random(semilla)` inyectable: layout de la
mazmorra, composición de enemigos, patrones del jefe, propagación social y eventos.
El azar elige **qué** pasa (qué evento, qué contactos reenvían); **cuánto** pesa
depende de las decisiones (correcciones publicadas, evidencia reunida). Con la misma
semilla el resultado es idéntico (tests con semillas fijas). La excepción es el
sorteo del impostor en Online (`random.choice` global en el host): no necesita
reproducirse y los tests lo fijan con monkeypatch. El bloqueo del sabotaje (10 a
15 s por terminal) sí usa un `random.Random` inyectable en `Sabotaje`: en la
partida va sin semilla y los tests le pasan una.

## Decisiones, puntuación y finales
- Un solo punto aplica la decisión: `Partida.cerrar_mazmorra` → `Mazmorra.completar()`
  (una vez) → colapso + pesos de calles + consecuencia narrativa.
- Indicadores 0-100 acotados en un único método (`EstadoCiudad.aplicar`).
- Final determinista por umbrales (`balance.py`), nunca por un botón:
  `determinar_final`. El secreto exige 3 pistas + origen de la señal rastreado + jefe,
  y reputación colectiva de -19 o más. Si nadie del equipo conserva la voz: «La confianza perdida».
- Elecciones: fórmula transparente en `calcular_apoyos`; se normaliza a 100 %.

## Reputación y redención
- **¿Cómo se decide si una acción es responsable?** Se cruza la acción con la veracidad real
  y con lo que el jugador podía saber: `valorar_accion`, tabla en `balance.py`. Compartir algo
  verdadero y comprobado suma; reportarlo daña a una inocente. Ignorar sin pruebas no castiga.
  Un «Me gusta» es un compartir más suave: pesa la mitad, pero a lo engañoso igual lo amplifica.
- **¿No es un número decorativo?** No: decide cuántos saltos alcanza tu corrección en el BFS,
  si las pruebas parciales te bastan, diálogos, reacciones, votos y finales.
- **¿Cómo se evitan dobles recompensas?** Con claves: `aplicar(..., clave="decision:Colegio")`.
- **¿Cómo funciona la redención?** Árbol para reconocer, BFS real para corregir (75 % de los
  expuestos), árbol para ayudar. Da +45, baja el tope a +59 y no borra el historial.
- **¿Y si alguien se niega?** En solitario, final «La confianza perdida» con punto de control.
  En equipo queda sin voz y los demás siguen. El host fija la reputación de todos.
- **¿Hay un modo impostor?** En la campaña no: el capítulo 3 es un rastreo por DFS de cuentas.
  Lo inspirado en Among Us está en el modo Online: sala, vestidores, listos y, al iniciar, el host
  sortea un impostor entre los vértices del grafo de sala y cada PC revela su rol. El impostor
  sabotea la terminal de decisión: al abrirse queda bloqueado entre 10 y 15 s (lo sortea el
  host), así el resto tiene ese tiempo para elegir la respuesta correcta; después elige normal.
  También tiene un botón SABOTEAR: a todos les salta una publicación viral con 20 s para frenarla.
  Cualquiera puede apretar REPORTAR (cada 60 s): reunión de 60 s con chat y votación (solo cuentan
  los votos emitidos). El expulsado queda como fantasma; si expulsan al impostor gana la
  tripulación, y con 3 o más jugadores, si solo quedan él y uno más, gana el impostor.
- Detalle: `docs/SISTEMA_REPUTACION.md`, `docs/SISTEMA_REDENCION.md`.

## Cliente-servidor (Online)
Host autoritativo por TCP (`Online/`): el invitado envía input, el host simula y
difunde snapshots (~30 Hz). La sala es un `GrafoSala` (nodos = jugadores, arista =
conexión con el ping como peso). La terminal y la investigación las resuelve el
host; el invitado arma el mismo árbol (misma fábrica, mismos ids). Pendiente:
mensaje de votación colectiva para el capítulo 3.

## Requisitos de la rúbrica: estado
| Requisito | Estado |
|---|---|
| 2-4 jugadores | 1-2 local (teclado + DualShock 4); Online host + invitados por TCP. Probado con control simulado y en pruebas de red; pendiente prueba con 4 reales. |
| Sockets | Implementado (`Online/servidor.py`, `cliente.py`, `protocolo.py`). |
| Árbol | Implementado y gobierna dificultad y decisiones. |
| Grafo | Implementado: cuartos, calles (Dijkstra) y red social (BFS/DFS). |
| Ayudas | Tecla H (ayuda), I (estado), guía de controles en Ajustes. |
| Inclusividad | Filtro de daltonismo, reducir movimiento, alto contraste; subtítulos como texto (no hay voces). |
| Azar | Semillas inyectables; eventos y propagación. |
| Elecciones | Simulación determinista con 4 candidatos ficticios. |
| Demostración | Recorrido de 5-8 min en `docs/MODO_HISTORIA.md`. |


## Guía rápida para la Feria Gamer: qué mostrar y cómo explicarlo (3 nov 2026)

**Demo de 8-10 min:** JUGAR → Periodista → intro (Esc para ir a los objetivos) → Colegio
(recoger pruebas, terminal, indicador de reputación) → Hospital (la publicación es verdadera:
muestra que reportar hace daño) → Empresa de Medios (rastreo por DFS) → Alcaldía → elecciones.

**Demo de la crisis (3 min, mejor preparada):** elegir «Compartir» o insistir en dos zonas con
todas las pruebas. Al volver a la ciudad aparece la crisis. Aceptar y hacer la etapa 2 en el
Kiosco de la Plaza: es el BFS más visual del juego.

**Frases para explicar las mejoras:**
- «La intro cuenta quién eres, qué es Civitas y quién es NOVA_404, y espera a que leas; termina
  en una lista de objetivos.»
- «El panel MISIÓN ACTUAL no guarda estado: se calcula cada frame a partir de la campaña y de la
  mazmorra (grafo de cuartos), por eso nunca se desincroniza, ni en cooperativo ni en red.»
- «Cada decisión navega un árbol N-ario real; con menos pruebas la misma hoja lleva a otro
  resultado. La publicación viaja por BFS en el grafo social y el rastreo usa DFS.»
- «Las elecciones y el final salen de los indicadores, las pistas, la reputación y a quién
  señalaste: hay cuatro finales y las cinemáticas usan esos datos reales.»
- «El juego arranca sin internet ni Higgsfield: las ilustraciones son archivos del repo y cada
  pantalla tiene un respaldo dibujado en código.»

**Si algo falla en vivo:** Esc salta cualquier cinemática; EXTRAS → VER INTRODUCCIÓN la repite;
`python -m pytest -q` debe dar todas las pruebas en verde (más de 940) y
`python tools/prueba_ventana.py` confirma FPS y audio. Lista previa en `docs/QA_VISUAL.md`.
