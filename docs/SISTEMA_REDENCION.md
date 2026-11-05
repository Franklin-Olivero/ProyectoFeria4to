# Crisis y redención

Qué pasa cuando un jugador cae a -60 o menos. Código: `src/story/redencion.py` (puro),
`Campania` (crisis, punto de control, final), `src/ui/redencion_render.py`, guiones en
`src/story/cinematica.py`, textos en `content/campaign.json` → `redencion`.
Pruebas: `tests/test_redencion.py`, `tests/test_historia_online.py`, `tests/test_campania_completa.py`.

## Estados

```
sin_crisis ──(≤ -60)──> crisis_pendiente ──aceptar──> en_redencion ──misión──> redimido
                              │                            │
                              └──rechazar──> rechazada     └──falla 2 veces──> fallida
```
`rechazada` y `fallida` dejan al jugador **sin voz**. Desde ambas se puede volver al punto
de control. `redimido` puede volver a caer: la crisis se abre de nuevo y la recompensa baja
a la mitad.

## La crisis

Nunca interrumpe: se presenta al volver a Ciudad Nova, tras el indicador de reputación.

1. Publicaciones de Civitas contra el protagonista (`EFECTO_TITULARES`, video `crisis`).
2. El protagonista preocupado: *«Las decisiones que tomaste no desaparecieron…»*
3. Rosa Beltrán, mediadora comunitaria: *«Todos podemos equivocarnos…»*
4. Dos opciones, sin reloj. Moverse no decide nada, y un Enter de más al salir de la
   cinemática no cuenta (`PAUSA_ANTES_DE_DECIDIR`).

## Misión «Segunda oportunidad»

| Etapa | Dónde | Qué hace el jugador | Estructura |
|---|---|---|---|
| 1. Reconocer | Justo al aceptar | Identifica la publicación que dañó entre señuelos y, con las pruebas a la vista, elige cómo responder | Árbol N-ario (`ArbolEtapa`) |
| 2. Corregir | Kiosco Civitas, en la Plaza | Elige desde qué ciudadano sale la corrección | Grafo social + **BFS real** (`RedSocial.corregir`, 2 saltos) |
| 3. Confianza | Frente a la zona dañada | Ayuda a un ciudadano afectado a encontrar una fuente confiable | Árbol N-ario |

La etapa 2 muestra el grafo: magenta quien aún cree lo falso, cian quien ya recibió la
corrección. Meta: **75 % de los expuestos** con 2 publicaciones. El cursor empieza en quien
tiene menos contactos, porque elegir bien pide leer el grafo.

Las etapas 2 y 3 se abren caminando hasta una baliza (con flecha en el borde si está fuera
de pantalla). Se puede pausar con Esc y entrar a una mazmorra entre medias.

## Fallar es justo

- 3 oportunidades, visibles en pantalla. Cada error explica por qué estuvo mal.
- Sin oportunidades: **un reintento** con otras 3, sin perder lo logrado.
- Sin cobertura en la etapa 2: gasta una oportunidad, explica qué falta y da otra publicación.
- Solo después queda `fallida`, y hasta ahí se puede volver al punto de control.
- La etapa 2 siempre tiene solución: desde Ana se llega a toda la red en 2 saltos.

## Al completarla

`Campania.completar_redencion`:

- +45 de reputación (la mitad si recae). No llega a positivo si la caída fue grande.
- **El pasado queda:** el historial no se borra y el tope baja a +59: no se vuelve a ser
  «Referente» en esa campaña.
- Efectos: desinformación -10, confianza +8, información verificada +5, convivencia +4.
- Cinemática de recuperación: *«Una segunda oportunidad no significa que el pasado haya
  desaparecido…»*. El epílogo final también lo menciona.
- Se cobra una vez por misión, aunque el mensaje de red llegue repetido.

## Al rechazarla

`Campania.rechazar_redencion`: pierde la voz; el rumor vuelve a viajar por el BFS porque
NOVA_404 usa sus publicaciones de ejemplo; confianza -12, desinformación +8, conflictos +6.
Aparece el final **La confianza perdida** con reputación final, información difundida,
quiénes siguen sin corrección, consecuencias reales de su historial, estado de la ciudad y
un mensaje educativo.

Salidas (nunca queda atrapado):

| Opción | Efecto | Cuándo aparece |
|---|---|---|
| Volver al punto de control | Restaura reputación, indicadores y red al abrirse la crisis, y reabre la decisión | Siempre que haya punto de control |
| Seguir con mi equipo, sin voz | Sigue jugando; no decide en terminales | Si alguien del equipo conserva la voz |
| Comenzar una nueva campaña | Reinicia la partida | Host o juego local |

## Multijugador

- La crisis es **individual**: solo la ve quien la tiene, en su pantalla.
- El invitado corre su misión en una copia local y avisa al host con `HISTORIA`
  (aceptar, rechazar, completar, fallar, reintentar). **El host fija la reputación** y
  recalcula la corrección con BFS desde los orígenes recibidos, ignorando los inválidos.
- El servidor pone el id de la conexión: nadie decide por otro.
- Rechazar no termina la partida de los demás: quien lo hace queda sin voz (su navegación se
  ignora) y sigue combatiendo. Solo si **todos** quedan sin voz el final global es «La
  confianza perdida».
- Si el equipo entra a una mazmorra durante la crisis de un invitado, se cierra su pantalla
  y se le vuelve a presentar al regresar. Mientras el host lee una escena, las entradas
  pedidas por los invitados esperan.

## Finales

`determinar_final`, en este orden:

1. **La confianza perdida:** nadie del equipo tiene voz.
2. **El arquitecto:** 3 pistas, origen de la señal rastreado, jefe derrotado y reputación
   colectiva ≥ -19.
3. **Ciudad Nova renace:** indicadores altos y reputación colectiva ≥ -19.
4. **La ciudad dividida:** cualquier otro caso.

## Para sustentar

> «La redención no devuelve puntos por apretar un botón. Debes reconocer con un árbol,
> corregir con un BFS real y ayudar a alguien. Aun así, tu nombre queda marcado: el tope
> baja y el historial no se borra.»
