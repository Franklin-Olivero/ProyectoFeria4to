# QA visual y de experiencia

Qué se comprobó, cómo repetirlo y qué falta que revise una persona. Fecha: 5 nov 2026.

## Cómo repetir las pruebas

```
python -m pytest                                  # suite completa
python tools/recorrido_campania.py --capturas X   # campaña entera, 90 capturas, sin ventana
python tools/recorrido_campania.py --ventana      # igual, con ventana real
python tools/prueba_ventana.py X                  # 25 s a tiempo real: FPS y audio
python tools/generar_audio.py --revisar           # niveles y costura de cada pista
```

`recorrido_campania.py` usa el `Main.main()` real y envía teclas frame a frame. Para ir
rápido quita enemigos y coloca al jugador junto a las puertas, así que **no prueba la
dificultad del combate**.

Mientras corre con ventana, esta toma el foco del teclado: no escribas en otra aplicación.
La primera corrida con ventana falló porque una escena avanzó sola; la siguiente, sin tocar
el teclado, pasó completa. La causa más probable es una tecla real que recibió la ventana,
pero **no quedó demostrado**. Si vuelve a ocurrir, investigar.

Otra corrida de `prueba_ventana.py`, justo después de la suite completa, no devolvió salida;
repetida por separado midió 62,5 FPS con y sin `pygame.SCALED`. No se reprodujo ni se aclaró
la causa: si la prueba no imprime nada, repetirla sola.

## Verificado

| Comprobación | Resultado | Cómo |
|---|---|---|
| Campaña completa: menú, intro, 3 zonas, crisis, rechazo, punto de control, misión, jefe, elecciones, final | Pasa | Recorrido, sin ventana y con ventana macOS |
| Las escenas con texto esperan al jugador | Pasa: 40 s sin avanzar | Recorrido y `test_cinematicas_lectura.py` |
| Avance automático respeta lectura y escritura | Pasa | Tests |
| Todo el guion de intro, crisis, redención y capítulos cabe sin «…» | Pasa, medido con la fuente real, 4 roles y 3 niveles de reputación | Tests |
| Ventana real en macOS | 62,5 FPS en menú, intro con video, ciudad y mazmorra | `prueba_ventana.py` |
| Costo de dibujo sin ventana | Cuarto 0,5 ms · Terminal 2,9 ms · Cinemática 1,9 ms · Redención 7,9 ms | Medición propia |
| Mezclador con dispositivo real | Canal de música activo en intro y combate | `prueba_ventana.py` |
| Bucles sin costura | Salto máximo 0,056 de amplitud (`decision`) | `generar_audio.py --revisar` |
| Red con sockets reales en localhost | Aceptar, completar, rechazar, reintentar, actor de la decisión | `test_historia_online.py` |
| Lobby sigue abriendo y sus vestidores intactos | Sala visible, sus tests pasan | Captura y tests existentes |
| Sin ningún archivo de video o retrato | Cae a la ilustración o al retrato base | `test_cinematicas_lectura.py` |

Capturas curadas en `docs/capturas/premium/`.

## Límites conocidos

- **Resolución:** la lógica del juego es siempre 1280×720. Ahora la ventana se puede
  redimensionar y se escala con barras negras (`pygame.SCALED`). Con otro tamaño de ventana
  el contenido es idéntico, solo escalado. No hay otros diseños de pantalla.
- **Textos largos de datos** (nombre de cuenta muy largo en una fila) pueden reducirse o
  llevar «…». La narrativa no: se pagina.
- **Etapa 2 con poca exposición:** si casi nadie recibió el rumor, se completa con una sola
  publicación.
- **El lobby no se rediseñó:** se conservó para no arriesgar la red; hereda la paleta de los
  tokens, pero su texto sigue siendo pequeño.
- **Dos jugadores en crisis en la misma pantalla:** se presentan de una en una; no probado
  con un control físico.

## Requiere validación humana

Antes de la Feria, una persona debe hacer esto; ninguna herramienta lo reemplaza.

1. **Escuchar todo el audio.** No se pudo oír. Revisar si las 10 pistas gustan, si `combate`
   y `jefe` cansan, si `crisis` asusta de más y el volumen relativo. Nada de esto se mide.
2. **Jugar el combate de verdad** en los 4 escenarios: confirmar que balas y enemigos se
   distinguen del fondo, sobre todo en Colegio (madera) y Servidor (trazas magenta).
3. **Terminal con reloj:** ¿45 s alcanzan para leer publicación y 3 pruebas? Probarlo con
   alguien que no conozca el juego. Ajustar `DURACION_TERMINAL_HISTORIA`.
4. **Video en el equipo de la Feria:** los cuadros se decodifican en un hilo. En un portátil
   lento puede verse a saltos. Si pasa, hay fallback: renombrar `assets/story/video/`.
5. **Windows:** todo se validó en macOS. Abrir en Windows, probar una ventana a pantalla
   completa y una partida entre dos PCs.
6. **Online con dos equipos y un DualShock 4 real.** Solo se probó en localhost y con
   control simulado. Especialmente: crisis de un invitado mientras el host entra a una zona.
7. **Balance:** ¿llega alguien a -60 sin querer? ¿Es fácil volver? Observar 5 partidas.
8. **Comprensión educativa:** preguntar a 3 personas qué aprendieron del Hospital.
9. **Filtros de daltonismo** sobre los escenarios nuevos y la barra de reputación.

## Lista rápida antes de presentar

- [ ] `python -m pytest` pasa
- [ ] `python tools/prueba_ventana.py` da 55 FPS o más en el equipo de la Feria
- [ ] Sonido y volumen revisados en el lugar
- [ ] `preferencias.json` borrado para que empiece con valores de fábrica
