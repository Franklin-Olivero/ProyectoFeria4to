# CIVITAS — Pantalla principal, navegación y sistema de ajustes

## Objetivo general

Analiza el contexto, la arquitectura y los archivos existentes del proyecto **CIVITAS**. Implementa una pantalla de inicio completa y un modal de ajustes funcional, con una identidad visual retrofuturista, cyberpunk y pixel art, integrados en el juego actual.

**No entregues únicamente una maqueta, una demostración aislada ni código de ejemplo.** Modifica los archivos reales del proyecto, conecta la interfaz con los sistemas existentes y verifica los cambios. Reutiliza componentes, recursos, convenciones y dependencias existentes siempre que sea posible. No reescribas sistemas que no sean necesarios para esta tarea ni inventes APIs del motor o del framework.

## 0. Inspección obligatoria antes de implementar

Antes de programar, inspecciona el proyecto y determina, según lo que realmente exista:

- Motor, framework, lenguaje, estructura de carpetas y punto de entrada de la aplicación.
- Escenas, pantallas, componentes o interfaces que ya existan y cómo se navega entre ellas.
- Flujo real para iniciar una partida, continuar una partida guardada y regresar al menú.
- Sistema de guardado y forma de determinar si existe una partida válida.
- Sistema de entrada: teclado, ratón, mando, navegación por foco, acciones configuradas y comportamiento del botón de retroceso.
- Sistema de audio: música, efectos, mezcladores, canales o grupos disponibles y recursos de sonido reutilizables.
- Sistema de configuración y persistencia de preferencias.
- Mecánicas reales de combate y apuntado Twin-Stick, incluida la representación del cono de disparo, si existe.
- Sistemas de subtítulos, accesibilidad, shaders, postprocesado, filtros de color y reducción de movimiento.
- Fuentes, sprites, iconos, música, efectos de sonido y demás recursos que puedan reutilizarse.
- Créditos, contenido adicional y pruebas, scripts o comandos de compilación existentes.

Después de inspeccionar, implementa la solución de acuerdo con la arquitectura encontrada. No te detengas tras presentar un diagnóstico. Si una característica solicitada no tiene infraestructura, implementa la alternativa compatible más pequeña y deja documentada su limitación, sin simular una integración que no existe.

## 1. Dirección artística y ambientación

### Identidad visual

Usa una estética de videojuego retrofuturista, cyberpunk y pixel art, con una composición cuidada y legible.

Paleta principal:

- Negro profundo para fondos y zonas de sombra.
- Azul noche y azul eléctrico para iluminación ambiental.
- Violeta y morado neón para títulos, selección e interacción.
- Cian como acento secundario, usado con moderación.
- Tonos claros para el texto normal y estados deshabilitados claramente diferenciados.

Prioriza los recursos gráficos y las fuentes que ya estén incluidos en el proyecto. Si no existe una fuente pixel art adecuada, utiliza una alternativa disponible antes de incorporar dependencias nuevas. No añadas paquetes externos salvo que sean realmente necesarios y compatibles con el proyecto.

### Ciudad animada en segundo plano

Crea una ciudad futurista nocturna con edificios de distintas alturas, ventanas iluminadas, rascacielos, anuncios holográficos y profundidad visual. Implementa varias capas de parallax que se muevan a velocidades diferentes para dar sensación de distancia.

Añade naves espaciales que crucen continuamente la pantalla de un extremo al otro. Varía discretamente su tamaño, velocidad, altura y profundidad; usa estelas luminosas breves y sutiles. Puedes incorporar niebla, partículas, lluvia o destellos ambientales si no dificultan la lectura ni afectan el rendimiento.

Requisitos técnicos de la animación:

- Movimiento continuo, fluido y eficiente; evita reconstruir la interfaz completa en cada fotograma.
- Reutiliza sprites, recursos y sistemas de animación existentes.
- Evita fugas de memoria, listeners duplicados y procesos que continúen activos innecesariamente al destruir o abandonar la pantalla.
- Mantén el fondo animado al abrir los ajustes; no reinicies la escena ni detengas la ambientación sin motivo.
- Adapta la composición a distintas resoluciones y relaciones de aspecto, sin cortar el menú ni deformar el título.
- Respeta la opción de reducción de movimiento del sistema o implementa una opción coherente si no existe. En ese modo, reduce o desactiva el parallax, las naves y los glitches intensos sin ocultar información.

## 2. Título CIVITAS

Coloca **CIVITAS** en una posición superior central y destacada. Utiliza tipografía pixel art o equivalente, color violeta/morado neón y un resplandor exterior controlado.

Añade efectos decorativos breves y recurrentes:

- Glitch sutil y poco frecuente.
- Separación cromática ocasional entre canales.
- Scanlines y pequeñas distorsiones digitales.
- Variaciones cortas de brillo o desplazamiento.

El texto debe permanecer legible en todo momento: los glitches no pueden deformarlo permanentemente, ocultarlo ni reducir el contraste del menú. Respeta la reducción de movimiento.

## 3. Menú principal y flujo real de navegación

Crea un menú central con estas opciones:

1. **JUGAR:** inicia una partida nueva mediante el flujo real del juego. Respeta la lógica actual de inicialización, selección de escena, reinicio de partida y preparación del estado de juego.
2. **CONTINUAR:** carga o reanuda una partida guardada si existe una partida válida. Si no existe, debe estar deshabilitado y explicar visualmente ese estado. No inventes datos de guardado ni permitas continuar con un archivo inválido.
3. **EXTRAS:** abre una sección secundaria funcional. Si aún no hay contenido, crea una pantalla sencilla con el estilo visual del juego y un mensaje claro de contenido pendiente, además de una forma de regresar.
4. **CRÉDITOS:** muestra los créditos presentes en el repositorio. Si no existen, crea una pantalla básica que no invente nombres ni atribuciones y permita volver al menú.
5. **AJUSTES:** abre el modal descrito en esta especificación.
6. **SALIR:** utiliza el mecanismo de salida apropiado para el motor y la plataforma. Si la plataforma no permite cerrar la aplicación —por ejemplo, un entorno de navegador—, presenta una alternativa útil y coherente; no dejes un botón que parezca funcionar pero no haga nada.

No añadas más opciones salvo que mejoren de forma clara la experiencia y no sobrecarguen el menú.

### Selección, navegación y microinteracciones

Permite usar todos los métodos de entrada realmente compatibles con el proyecto: ratón, teclado y mando cuando estén soportados. Si ya existe un sistema de navegación por foco o acciones abstractas, reutilízalo.

Cuando una opción esté seleccionada mediante hover, teclado o mando:

- Aplica un brillo neón violeta/morado.
- Presenta el texto con espaciado estilizado y corchetes, por ejemplo: `[ J U G A R ]`.
- Añade una animación breve de entrada, desplazamiento o intensidad luminosa.
- Reproduce el sonido de navegación disponible, si existe.

Al confirmar una opción, utiliza un sonido distinto de confirmación si los recursos lo permiten. Diferencia visualmente los estados normal, seleccionado, pulsado y deshabilitado. El estado deshabilitado debe ser comprensible y no parecer seleccionable.

Evita reproducir sonidos varias veces cuando una sola acción se recibe simultáneamente de más de un dispositivo o se disparan varios eventos de foco. El sonido debe activarse por un cambio real de selección, no por cada actualización de la interfaz.

Asegura que la navegación por teclado y mando tenga un foco visible, un orden lógico y una forma clara de regresar. No dejes el foco perdido detrás de overlays ni permitas que las opciones del menú subyacente se activen mientras un modal o una pantalla secundaria esté abierta.

## 4. Botón de ajustes

Ubica en la esquina superior derecha un botón con icono de engranaje, preferiblemente pixel art o visualmente coherente con el juego.

- En hover o foco de teclado/mando, aplica un resplandor violeta y una rotación sutil.
- Reproduce un sonido de interacción sin duplicarlo.
- Al activarlo, abre el modal de ajustes sin recargar la pantalla ni reiniciar la animación de fondo.
- Incluye un nombre accesible o etiqueta para tecnologías de asistencia; no dependas exclusivamente del icono.
- Mantén el botón dentro de la zona segura de la interfaz en resoluciones pequeñas.

## 5. Modal de ajustes

El modal debe integrarse visualmente con el universo de CIVITAS. Al abrirlo:

- Oscurece el fondo aproximadamente un 60 %.
- Aplica desenfoque al fondo si el motor/framework lo soporta de forma eficiente.
- Muestra un panel oscuro con bordes definidos, detalles violeta neón y acentos cian discretos.
- Usa transiciones breves de entrada y salida, respetando la reducción de movimiento.
- Mantén el foco de navegación dentro del modal mientras está abierto.
- Impide que el menú situado detrás reciba interacciones.
- Permite cerrarlo mediante un botón visible y Escape o el botón de retroceso equivalente compatible con el proyecto.
- Al cerrarlo, devuelve el foco al control que lo abrió y conserva los ajustes modificados.

Crea tres pestañas funcionales: **AUDIO**, **ACCESIBILIDAD** y **CONTROLES**. Debe poder cambiarse entre ellas con ratón, teclado y mando cuando esos métodos estén soportados.

La selección de pestaña debe ser visible, accesible y coherente con el sistema de foco. Cambiar de pestaña no debe reinicializar los valores ni perder cambios sin guardar.

### 5.1. Pestaña AUDIO

Incluye dos sliders principales:

- **MÚSICA:** controla el volumen de la música del juego.
- **EFECTOS DE SONIDO:** controla los sonidos de interfaz y los efectos de juego.

Cada slider debe mostrar el valor actual en porcentaje, permitir cambios por ratón y por los métodos de entrada compatibles, y aplicar los cambios inmediatamente al sistema de audio real. Si el proyecto tiene mezclador, canales o grupos separados, utiliza los existentes. Evita duplicar canales o crear un segundo sistema de audio.

Apariencia de los sliders:

- Barra pixelada o fragmentada.
- Segmentos activos en violeta neón y segmentos restantes en tonos oscuros.
- Indicador visible del valor y un estado claro para hover, foco y arrastre.
- Contraste suficiente y lectura numérica del valor.

No añadas un control de volumen maestro redundante. Incorpóralo únicamente si la arquitectura de audio existente lo justifica claramente y explica por qué es necesario.

Los valores deben limitarse al rango que admita el sistema real y convertirse correctamente a la escala de audio utilizada. Un valor visual de 0 % debe silenciar el grupo correspondiente; 100 % debe representar su máximo configurado, no provocar amplificación accidental por encima de ese máximo.

Si no hay música o efectos de audio disponibles durante el desarrollo, conecta los sliders a la arquitectura real de audio y documenta la limitación de recursos; no inventes una reproducción de audio paralela.

### 5.2. Pestaña ACCESIBILIDAD

#### Subtítulos

Incluye un interruptor para activar/desactivar los subtítulos, con texto y apariencia que indiquen claramente su estado. Conéctalo al sistema de subtítulos existente. Si el juego no tiene sistema de subtítulos, prepara una preferencia persistente e intégrala con la arquitectura de interfaz/texto disponible, dejando documentado qué contenido puede mostrar subtítulos actualmente.

#### Filtro de daltonismo

Incluye un selector con estas opciones exactas:

- Ninguno
- Protanopia
- Deuteranopia
- Tritanopia

Debe existir una forma clara de restaurar la presentación de color predeterminada, seleccionando **Ninguno**. La selección debe aplicarse de manera global a la presentación del juego mediante el mecanismo apropiado para el motor: por ejemplo, una solución de postprocesado, shader o transformación de color compatible con el renderizado actual.

No basta con cambiar los colores de los controles del menú si el objetivo es afectar al juego completo. Inspecciona la arquitectura gráfica antes de elegir una solución. Si el motor no permite aplicar un filtro global sin una modificación desproporcionada, implementa la alternativa compatible menos invasiva y documenta exactamente su alcance. No afirmes que el filtro es global si solo afecta a una capa o a la interfaz.

Los filtros deben evitar que la interfaz pierda contraste o que los estados importantes se comuniquen exclusivamente mediante el color. No afirmes que sustituyen las pruebas de accesibilidad con usuarios.

#### Reducción de movimiento

Si el proyecto ya incluye una preferencia o un ajuste de accesibilidad para reducir el movimiento, respétalo. Si no existe y puede integrarse sin crear un sistema paralelo, añade una opción para reducir los efectos decorativos del título, el parallax, las naves y las transiciones. Evita alterar animaciones necesarias para entender el estado del juego.

### 5.3. Pestaña CONTROLES

Esta pestaña es una **guía visual informativa**, no una colección de botones decorativos.

Incluye un selector funcional entre:

- **TECLADO / RATÓN**
- **MANDO**

Antes de mostrar asignaciones, inspecciona el sistema de entrada y presenta las acciones y teclas/botones reales configurados en el proyecto. Reutiliza los mapas de entrada o las acciones abstractas existentes. No inventes asignaciones como si ya fueran reales. Si alguna acción no tiene una asignación configurada, indícalo claramente y, si es necesario para que la guía sea útil, propone una asignación predeterminada compatible y configúrala de verdad.

#### Vista TECLADO / RATÓN

Muestra teclas y botones estilizados con sus acciones correspondientes. Incluye las acciones relevantes que realmente existan, tales como movimiento, apuntar, disparar, interacción, pausa y navegación de menús. No añadas acciones que el juego no soporte solo para rellenar la guía.

#### Vista MANDO

Muestra una representación visual del tipo de mando compatible con el proyecto. Incluye los botones, gatillos y sticks que correspondan a las asignaciones reales, con una etiqueta clara por acción. No presentes un modelo de mando que sugiera compatibilidad con una plataforma que el proyecto no soporte.

Si el proyecto admite varios tipos de mando, utiliza los iconos o convenciones disponibles; si solo admite entrada genérica, representa un mando genérico y deja clara la correspondencia de acciones.

#### Cono de disparo para Twin-Stick

Dentro de la vista MANDO, integra los ajustes del cono de disparo relacionado con la asistencia de apuntado Twin-Stick:

- Interruptor para habilitar o deshabilitar la visualización del cono.
- Slider para regular su opacidad visual, con valor porcentual visible.
- Vista previa representativa que permita entender el efecto del valor seleccionado.

Inspecciona primero la mecánica real de apuntado. Si ya existe un cono, conecta las opciones con sus parámetros reales. **La opacidad debe modificar únicamente la representación visual**; no debe alterar la dirección, el alcance, la intensidad del disparo, el daño ni la fuerza de la asistencia.

Si el sistema de cono no existe, no crees un sistema de combate paralelo. Implementa únicamente la visualización y su conexión mínima con el sistema de apuntado existente, si este permite hacerlo de forma coherente. Si no hay una mecánica de apuntado compatible, prepara el ajuste y la vista previa sin fingir que afectan a una mecánica inexistente, y documenta lo pendiente.

Define valores predeterminados razonables. El interruptor y la opacidad deben conservarse como preferencias y recuperarse correctamente. La opacidad debe tener un rango explícito —preferiblemente de 0 % a 100 %— y el valor 0 % debe ocultar visualmente el cono sin desactivar la asistencia de apuntado.

## 6. Estado, persistencia y configuración

Los valores deben mantenerse coherentes cuando el jugador cambia de pestaña, cierra y vuelve a abrir el modal, regresa al menú o cambia entre pantallas.

Reutiliza el sistema de configuración o persistencia existente. Si no hay uno adecuado, implementa una solución pequeña que use el mecanismo habitual del motor o framework. No dupliques almacenamiento ni guardes estado derivado innecesario.

Persistir, como mínimo, las preferencias que la arquitectura permita:

- Volumen de música.
- Volumen de efectos de sonido.
- Estado de subtítulos.
- Filtro de daltonismo.
- Preferencia de reducción de movimiento, si se implementa.
- Tipo de esquema mostrado en la guía de controles, si tiene sentido para la experiencia.
- Activación y opacidad visual del cono de disparo.

Requisitos de estado:

- Define valores predeterminados explícitos para una instalación sin preferencias guardadas.
- Valida los datos cargados; si faltan, son inválidos o pertenecen a una versión anterior, usa valores seguros sin impedir el arranque.
- Actualiza el estado real del juego, no solo la apariencia de los controles.
- Evita guardar innecesariamente en cada fotograma; persiste al cambiar un valor, al confirmar un ajuste o mediante el mecanismo ya usado por el proyecto.
- Si una preferencia no puede aplicarse en caliente, indica qué requiere reinicio y por qué. Prioriza los cambios inmediatos cuando sea técnicamente posible.
- Evita que varias instancias del modal o varios listeners dupliquen los cambios.

## 7. Calidad técnica, accesibilidad y compatibilidad

- Respeta la estructura, convenciones de código, arquitectura y estilo de programación del proyecto.
- Separa presentación, estado y lógica del juego en la medida que encaje con la arquitectura actual.
- Reutiliza componentes de interfaz, entrada, audio, guardado y navegación siempre que sea posible.
- Evita dependencias nuevas, código duplicado, listeners sin limpiar y actualizaciones innecesarias.
- Garantiza una distribución usable en resoluciones pequeñas, grandes, panorámicas y distintas relaciones de aspecto.
- Asegura contraste suficiente, tipografía legible, foco visible, estados diferenciados y alternativas textuales para iconos importantes.
- No dependas exclusivamente del color, el sonido, hover o animaciones para comunicar información.
- Si la aplicación pierde el foco, cambia de pantalla o cierra el modal, gestiona correctamente la entrada y el audio de interfaz.
- Respeta las convenciones de plataforma y no supongas que todas las plataformas permiten cerrar la aplicación de la misma forma.
- No inventes APIs del motor ni des por existentes sistemas que no hayas inspeccionado.
- No reemplaces ni rompas mecánicas existentes para facilitar la implementación de la interfaz.

## 8. Verificación y criterios de aceptación

Cuando termines, ejecuta las comprobaciones, pruebas, lint o compilación que existan en el proyecto. Corrige los errores relacionados con los cambios. Si hay pruebas automatizadas adecuadas, añade o actualiza pruebas para la lógica de preferencias y navegación.

Verifica, como mínimo:

1. La pantalla principal aparece al entrar en el flujo previsto del juego y se adapta a varias resoluciones.
2. El fondo, las capas de parallax, las naves y el título se animan sin bloquear la navegación ni causar trabajo innecesario.
3. JUGAR inicia el flujo real de una nueva partida.
4. CONTINUAR solo está disponible cuando se detecta una partida guardada válida y ejecuta la carga real.
5. EXTRAS y CRÉDITOS abren sus respectivas pantallas y permiten regresar al menú.
6. SALIR utiliza un mecanismo apropiado a la plataforma o presenta una alternativa explícita.
7. El menú funciona con los dispositivos de entrada soportados y el audio de navegación no se duplica.
8. El botón de engranaje abre el modal; Escape/retroceso y el botón visible lo cierran; el foco vuelve al control que lo abrió.
9. Las tres pestañas del modal funcionan con los métodos de navegación compatibles.
10. Los sliders de música y efectos cambian el audio real y muestran los porcentajes correctos.
11. Los subtítulos y el filtro de daltonismo actualizan el estado efectivo; documenta el alcance real de cada integración.
12. La guía de controles refleja las asignaciones configuradas de teclado/ratón y mando.
13. Los ajustes del cono solo afectan a su visualización, sin modificar el combate, el daño o la asistencia.
14. Las preferencias persisten, tienen valores predeterminados seguros y se recuperan correctamente al volver a abrir el juego.
15. La reducción de movimiento, si existe o se implementa, reduce los efectos decorativos correspondientes.
16. No se han introducido errores de compilación, referencias a recursos inexistentes, listeners duplicados ni procesos de animación huérfanos.

Si alguna prueba no puede ejecutarse por falta de herramientas, plataforma o infraestructura, dilo de forma explícita. No marques como verificado algo que solo hayas inspeccionado visualmente o supuesto.

## 9. Informe final obligatorio

Al completar la implementación, presenta un resumen breve y concreto con:

- Archivos creados y modificados, y el propósito de cada uno.
- Funcionalidades implementadas y sistemas existentes con los que se integraron.
- Cómo se gestionan la persistencia y los valores predeterminados.
- Comprobaciones ejecutadas, comandos utilizados y resultado real.
- Limitaciones pendientes, funciones que solo tengan una alternativa parcial y cualquier recurso que falte.

**Prioridad general:** identidad visual reconocible de CIVITAS, navegación propia de un videojuego, funcionalidad real y compatibilidad con el proyecto. No sacrifiques la estabilidad por efectos visuales innecesarios y no declares terminada una integración que no esté conectada al juego.
