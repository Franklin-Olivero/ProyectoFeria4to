# Sistema de reputación

Cómo percibe Ciudad Nova a cada jugador. Código: `src/story/reputacion.py` (puro),
`Campania` (`src/story/campania.py`), números en `src/core/balance.py`.
Pruebas: `tests/test_reputacion.py`.

## En una frase

Cada decisión en la terminal cambia un entero individual de **-100 a +100** que empieza en
**0**, y ese número cambia lo que la ciudad te permite y te dice.

| Valor | Nivel | Qué cambia |
|---|---|---|
| +60 a +100 | Referente de Ciudad Nova | Correcciones a 4 saltos, +10 s en la terminal, titulares a favor |
| +20 a +59 | Ciudadano confiable | Un ciudadano te envía una prueba al entrar a cada zona, retrato decidido |
| -19 a +19 | Reputación neutral | Correcciones a 3 saltos |
| -20 a -59 | Reputación cuestionada | Correcciones a 2 saltos; **las pruebas parciales ya no bastan**; te niegan ayuda en diálogos |
| -60 a -100 | Crisis de reputación | Correcciones a 1 salto; se abre la crisis (`docs/SISTEMA_REDENCION.md`) |

## Cómo se decide si una acción fue responsable

No hay opciones «buenas» o «malas» por nombre. Cada hoja del árbol declara qué **acción**
hizo el jugador, y `valorar_accion` la cruza con dos preguntas:

1. **¿Era verdad?** El `veredicto` real de la publicación (`veraz` o `enganosa`).
2. **¿Qué podía saber?** Las pruebas que recogió: ninguna (`sin_saber`), algunas (`indicios`)
   o todas (`sabia`).

Tabla de `balance.VALORACION_ACCIONES` (sin saber, con indicios, sabiéndolo):

| Acción | Publicación engañosa | Publicación verdadera |
|---|---|---|
| Compartir | -12, -20, **-30** | +4, +8, **+15** |
| Publicar lo comprobado | -4, +8, **+20** | -2, +6, +15 |
| Reportar como falsa | -2, +8, **+25** | -10, -15, **-20** |
| Denunciar a los atacantes | -6, -8, -10 | -2, +10, +20 |
| Linchar (reportes en masa, acusar) | -10, -12, -15 | -15, -20, -25 |
| Afirmar de más | -8, -10, -12 | -10, -14, -18 |
| Insistir tras revisar | -15, -22, **-35** | -2, -2, -2 |
| Ignorar | **0**, -3, -8 | -2, -5, -10 |
| No decidir a tiempo | -3, -4, -6 | -3, -5, -8 |

Ejemplos de los matices pedidos:

- Compartir algo verdadero y comprobado suma; compartir algo falso sabiéndolo resta 30.
- Reportar algo verdadero daña a una persona inocente.
- Ignorar sin pruebas no castiga: no amplificar lo que no pudiste comprobar es válido.
- Equivocarse sin saber (-12) no pesa igual que manipular (-30 o -35).

Después se ajusta el número:

- **Gravedad** de la zona: `baja` ×0.75, `media` ×1, `alta` ×1.25. Solo escala el daño.
- **Alcance real:** `ajuste_por_alcance` usa cuántos ciudadanos alcanzó el BFS. Quien dañó a
  más gente pierde hasta 5 puntos más; quien informó a más gana hasta 3.
- **Candidato:** sus penalizaciones pesan ×1.5.

## Por qué el jugador no puede memorizar la respuesta

- **Colegio:** captura recortada (fuera de contexto).
- **Hospital:** la publicación es **verdadera**. Una enfermera pide sangre y 30 cuentas
  coordinadas la acusan de mentir. Aquí compartir ayuda y reportar hace daño.
- **Medios:** encuesta fabricada (falsa).

Además las **pruebas ya no son automáticas**: cada cuarto limpio deja una carpeta en el
suelo y hay que ir a recogerla. Se puede llegar a la terminal con 0, 1, 2 o 3 pruebas.

## Sin recompensas duplicadas

`ReputacionJugador.aplicar` recibe una `clave`. Con la clave `decision:<zona>` la ganancia se
cobra una vez por zona; `investigacion` y `redencion:<n>` funcionan igual. Las penalizaciones
no llevan clave: decidir mal otra vez vuelve a costar. Los efectos sobre los indicadores sí
se aplican cada vez, porque la ciudad reacciona a cada publicación.

## Consecuencias visibles

| Consecuencia | Dónde |
|---|---|
| Indicador animado con barra, cambio y mensaje narrativo | `src/ui/reputacion_render.py` |
| Comentarios de ciudadanos por nivel; nombran a quien recibió tu rumor o tu corrección | `Campania.reaccion_ciudadana`, `src/ui/feed_render.py` |
| Titulares del cintillo sobre el jugador | `Campania.titulares` |
| Líneas de diálogo según reputación (`requiere: reputacion_min/max`) | `src/story/dialogo.py`, `campaign.json` |
| Retrato preocupado o decidido | `resolver_lineas` |
| Prueba regalada por un ciudadano | `Campania.aporte_ciudadano` |
| Más o menos alcance de las correcciones | `Campania.saltos_correccion` |
| Exigencia de todas las pruebas | `Campania.preparar_escenario` |
| Votos y finales | `src/story/eleccion.py` |

Nada de esto bloquea la campaña: la terminal siempre se puede resolver y siempre se puede
llegar a la Alcaldía.

## Estructuras de datos

- **Árbol N-ario:** el camino de la decisión lleva a la hoja, y la hoja declara la acción.
- **Grafo social + BFS:** la publicación viaja de verdad; `afectados` sale de ese recorrido.
- **Grafo de cuentas + DFS:** el capítulo 3; señalar a una víctima cuesta 20.
- Costo: valorar y aplicar son O(1). La propagación es O(V + E).

## Multijugador

La reputación es de cada jugador (`Campania.reputaciones`, por índice).

- **Quién carga con la decisión:** quien confirma la opción final en la terminal
  (`registrar_actor`). Los demás ven cómo se mueve el cursor.
- **Host autoritativo:** solo el host aplica consecuencias. Los invitados tienen
  `Campania.espejo = True` y copian `resumen_red()` en cada snapshot, sin confiar en tipos
  ni rangos. Detectan novedades con un contador y muestran su propio indicador.
- **Cooperativo local:** el control del J2 también navega la terminal y se le cobra a él.
- **Indicadores compartidos:** colapso, indicadores y red social son de todos.
- Las elecciones usan el promedio del equipo (`reputacion_colectiva`).

## Para sustentar

> «La misma opción vale distinto según la verdad y lo que sabías. Compartir no es malo:
> compartir algo que sabes falso sí. Y el resultado no es un número fijo: el BFS dice a
> cuánta gente le llegó, y eso ajusta la reputación.»
