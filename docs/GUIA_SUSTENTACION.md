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
semilla el resultado es idéntico (tests con semillas fijas).

## Decisiones, puntuación y finales
- Un solo punto aplica la decisión: `Partida.cerrar_mazmorra` → `Mazmorra.completar()`
  (una vez) → colapso + pesos de calles + consecuencia narrativa.
- Indicadores 0-100 acotados en un único método (`EstadoCiudad.aplicar`).
- Final determinista por umbrales (`balance.py`), nunca por un botón:
  `determinar_final`. El secreto exige 3 pistas + coordinadora correcta + jefe.
- Elecciones: fórmula transparente en `calcular_apoyos`; se normaliza a 100 %.

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
