# P06 — Perfiles de CPU 6–25 MHz y MAX

Estado: especificación futura, actualizada el 2026-10-03. Base: implementación
única tras la limpieza P20, con CPU/puente/SDRAM sobre el reloj común de 50 MHz;
P21 mantiene pendiente la aceptación del cierre de tiempos. No hay perfiles
históricos implementados ni precisión temporal validada. Aplican los
[requisitos comunes](README.md) y el
[modelo de temporización SPK286](../../vendor/spk286/SPK286_TIMING_MODEL.md).

El primer hito es definir y medir la referencia antes de modificar RTL/OSD:
[plan P06-M1](P06_TIMING_REFERENCE_PLAN_20261003.md). P12 documenta el
[contrato de referencia y la atribución de rendimiento](P12_REAL_CHECKNUM_MEMORY_ATTRIBUTION_20261002.md).
La parte nativa de 86Box está completada en
[los resultados P06-M1](P06_NATIVE_REFERENCE_RESULTS_20261003.md); las mediciones
físicas a 6/12 MHz permanecen `NOT_MEASURED` y el alcance histórico de M1 sigue abierto.

Ya están completadas la [extracción Intel de los kernels](P06_INTEL_TIMING_REFERENCE_20261003.md)
y la [especificación del piloto de 6 MHz](P06_TIMING_CONTRACT_20261003.md), con
captura/publicación de respuestas, unidades temporales, pruebas dirigidas y
base de recursos del fit seleccionado. Se han identificado diferencias entre
las tablas Intel y los handlers nativos de 86Box; sus medidas se conservan como
contraste. Falta implementar y validar el piloto, completar los hitos internos
de cada instrucción y obtener la referencia de placa/CPU física.

## 1. Objetivo y alcance de precisión

Ofrecer las velocidades de la familia Intel 286 de 86Box:
**6, 8, 10, 12,5, 16, 20, 25 MHz y MAX**, con una única CPU funcional y una
política de temporización separada. La entrada de 86Box etiquetada `12` usa
12.500.000 Hz; una futura selección se identificará como 12,5 MHz. La referencia
física de 12 MHz ofrecida por el colaborador se registra por separado: no es una
medición a 12,5 MHz ni añade automáticamente un perfil de producto.

La intención de producto es conservar el modo rápido sin retardos históricos
añadidos y permitir activar T-states históricos con perfiles de velocidad.
`Fast` aquí describe esa intención; no presupone la BIU histórica del modo
conceptual Fast de SPK286 ni una nueva codificación de OSD. Ninguna política
puede eliminar dependencias reales, trabajo de instrucciones o accesos visibles.

P06-R01. Una frecuencia nominal no demuestra exactitud. Para cada perfil se
deben declarar y validar separadamente:

| Nivel | Qué se compara |
| --- | --- |
| Frecuencia nominal | Reloj virtual de CPU y tiempo transcurrido |
| Ciclos de instrucción | Finalización bajo operandos/condiciones especificados |
| Ciclos de bus | Secuencia, lanes, espera READY y relaciones temporales |
| Eventos | Reconocimiento de IRQ/NMI, INTA, HOLD/HLDA y puntos de interrupción |
| Flancos físicos | Resolución y fase respecto al reloj FPGA; no se presupone exactitud de pines |

El objetivo principal es precisión de instrucciones y bus lógico. La emulación
de cada transición eléctrica del encapsulado 286 no se declara cubierta salvo
que exista una implementación y evidencia específica.

## 2. Estado de los perfiles

| Selección prevista | Política | Estado al 2026-10-03 |
| --- | --- | --- |
| 6 MHz | Histórica; requiere evidencia de CPU/placa | Pendiente; primer candidato |
| 8 MHz | Histórica; requiere evidencia de CPU/placa | Pendiente |
| 10 MHz | Histórica; requiere evidencia de CPU/placa | Pendiente |
| 12,5 MHz | Histórica, entrada Intel 286 de 86Box etiquetada `12` | Pendiente; no sustituye la referencia física de 12 MHz |
| 16 MHz | Histórica; requiere variante rápida identificada | Pendiente |
| 20 MHz | Histórica; requiere variante rápida identificada | Pendiente |
| 25 MHz | Histórica; requiere variante rápida identificada | Pendiente |
| MAX | Avance por dependencias reales, sin padding histórico | Comportamiento acelerado actual; aceptación física final por P21 |

La precisión estimada de todos los perfiles históricos es **no validada**.
Las cifras de CheckIT/CHECKNUM sólo acreditan rendimiento en sus cargas. En la
integración actual, `execute_enable` está fijo a 1 y `timing_policy_request` a 0;
SPK286 acepta las políticas internas 0 y 2 con el mismo calendario funcional.
Esto no implementa un selector histórico ni demuestra ciclos de un 286 real.

P06-R02. Cada fila tendrá CPU de referencia, contrato de bus/placa, política de
wait states, versión de tabla temporal y evidencia. Si se extrapola la misma
secuencia temporal a otra frecuencia, debe identificarse como extrapolación,
no como validación independiente de otra variante de silicio.

P06-R03. No presentar al usuario perfiles pendientes como ciclo exactos. MAX
se etiqueta como acelerado, sin asignarle los MHz que estima CheckIt ni el
Fmax de Quartus como si fuesen una frecuencia histórica medida.

## 3. Separación de responsabilidades

| Componente | Responsabilidad |
| --- | --- |
| Motor funcional SPK286 | Ejecutar semántica, mantener estado, dependencias y excepciones |
| Política temporal CPU | Eventos/latencias históricas y oportunidades de avance |
| BIU SPK286 | Secuencia CPU visible, READY, lanes, LOCK, INTA y propiedad |
| Integración AT | Relación con memoria/periféricos y política de wait states |
| Generador temporal | Relación entre reloj físico y tiempo virtual CPU |
| OSD/reset | Selección pendiente, aplicación segura y persistencia |

P06-R04. No crear dos motores CPU con semántica distinta. No insertar NOPs de
microcódigo o estados sin trabajo para simular frecuencias particulares.
Los retardos históricos se expresan como metadatos/política explícitos.

P06-R05. `execute_enable` NO se usa como divisor general: no congela por sí solo
prefetch, BIU ni las respuestas aceptadas. Debe existir un protocolo de avance
que capture respuestas físicas y permita publicarlas en el instante correcto,
sin perderlas entre ticks virtuales.

La interfaz actual lo usa también para seleccionar el camino de ejecución
nativo frente al control externo de verificación. La BIU y la cola de prefetch
siguen recibiendo el reloj físico; el enable del microsecuenciador tampoco es
un protocolo global de pausa. Las trazas temporales existentes son observadores,
no un planificador. El nuevo contrato debe separar captura/retención de
respuestas y habilitación de hitos CPU antes de reutilizar esas interfaces.

## 4. Modelo de tiempo propuesto

Mantener tres magnitudes independientes:

- `fabric_cycles`: relojes del circuito físico cuya frecuencia ha pasado P05.
- `cpu_ticks`: unidades temporales del perfil CPU definido y documentado.
- Eventos funcionales: solicitud, aceptación, dato disponible, commit/retire,
  redirect, interrupción y transferencia de propiedad.

P06-R06. Definir la unidad `cpu_tick` contra la referencia 286 elegida. No
confundir frecuencia de entrada al reloj del chip, fases del bus y ciclos
publicados por un programa de benchmark; la relación debe quedar en el manifiesto.

Puede utilizarse un acumulador de fase o planificación racional. Para un
generador que produzca como máximo un tick por reloj físico, demostrar que la
frecuencia solicitada es representable y que no se pierde ningún tick. El
desfase acumulado respecto al reloj ideal debe estar acotado y documentado.

P06-R07. Con 50 MHz, varios periodos solicitados no son divisores enteros.
Una secuencia de enables puede obtener la frecuencia media correcta, pero sus
intervalos estarán cuantizados. Eso no es igualdad de flancos con un oscilador
independiente. Indicar resolución, patrón/jitter y nivel de exactitud permitido.
Si una prueba exige otra relación de fase, resolver el plan de reloj por P05,
sin fijar de antemano una nueva frecuencia maestra. La primera propuesta conserva
los 50 MHz comunes mediante enables/política pequeña, sin nuevas PLL, dominios,
copias de CPU, buffers mayores ni aumento de colas.

P06-R07a. El STA sigue presupuestando **20 ns en cada camino del dominio físico
de 50 MHz**, aunque el perfil emulado sea de 6 MHz. Un tick virtual no convierte
por sí solo un camino en multiciclo. Cualquier excepción temporal exige demostrar
los enables y relaciones reales de lanzamiento/captura. Medir antes/después
ALM equivalentes, ALM colocados, FF y M10K con el mismo alcance y herramienta;
el coste compartido debe aceptarse antes de adoptar RTL. No se promete coste cero.

## 5. Planificación de instrucciones, bus y eventos

P06-R08. Una tabla temporal debe depender de la clase de operación y de las
condiciones relevantes: registro/memoria, alineación, branch tomado, prefijos,
cantidad de REP, operandos variables y contexto protegido cuando corresponda.
No se valida una familia sólo con un presupuesto medio por opcode.

P06-R09. El planificador habilita hitos observables en orden. No basta ejecutar
todo lo antes posible y retrasar únicamente `instruction_retired`: escrituras,
I/O y oportunidades de interrupción ya serían visibles demasiado pronto.

P06-R10. Separar el mínimo temporal de una operación de sus dependencias reales.
Nunca completar con datos inexistentes ni ocultar READY bajo. Las esperas
adicionales del dispositivo se incorporan según la secuencia de bus del perfil.

P06-R11. El solapamiento EU/BIU y la cola de seis bytes forman parte del modelo.
Un contador por instrucción que sume fetch+ejecución+memoria sin considerar ese
solapamiento no basta para reclamar ciclo exacto.

P06-R12. IRQ/NMI, sombras tras STI/carga de SS, INTA, HLT, REP y excepciones
mantienen la semántica validada. Las muestras temporales y el instante permitido
para reconocer cada evento deben formar parte de las pruebas, incluido PM5.

## 6. Capacidad real y subejecución

P06-R13. Antes de habilitar un perfil, demostrar con P04 que la implementación
puede cumplir sus deadlines para las cargas/casos certificados y con el reloj
físico validado. El motor que tarda 12 relojes físicos en una dependencia no
se acelera por asignarle un presupuesto histórico más corto.

Registrar `deadline_miss` cuando la implementación no puede producir un evento
en su fecha contractual por sobrecoste interno. Distinguirlo de una espera READY
externa permitida por la placa de referencia.

P06-R14. No detener el tiempo virtual de PIT/RTC ni cambiar silenciosamente la
frecuencia anunciada para ocultar esos incumplimientos. Un perfil que incumple
se mantiene experimental/no validado, y se optimiza la ruta o el reloj físico.
Un modo funcional lento puede existir, pero no se etiqueta ciclo exacto.

## 7. Relación con P01–P03

P01/P02 pueden reducir latencia interna de MAX. En un perfil exacto la política
temporal debe conservar oportunidades de bus y prefetch de su referencia.
P03 puede ocultar SDRAM física, pero un hit no autoriza responder a la CPU antes
del instante permitido por el modelo histórico.

P06-R15. La actividad extra de llenado físico de un buffer no se publica como
tráfico CPU histórico. Se conservan, sin embargo, el arbitraje y capacidad
física para DMA/refresco; no puede fingirse que el recurso está libre si está
ocupado por una operación real. Si no se demuestra transparencia temporal, el
perfil no se acepta. Los buffers actuales forman parte de la implementación
única; esta especificación no presupone que existan variantes desactivables ni
propone restaurar opciones de configuración retiradas.

## 8. Bases de tiempo de periféricos

P06-R16. PIT, RTC, vídeo, audio y protocolo de teclado mantienen sus relojes
propios. El cambio de CPU no multiplica su frecuencia. Los accesos CPU a estos
dispositivos sí se programan con la política de bus del perfil elegido.

La frecuencia ISA/AT y sus wait states deben definirse como propiedades de
placa, no como una división automática aplicada a toda la RAM. Los puertos
XT-IDE de 8 bits conservan la secuencia de bytes, latch y tiempos requeridos.

## 9. OSD, estado guardado y cambio de modo

P06-R17. Antes del RTL, definir la relación entre selección de velocidad y
T-states opcionales: qué significa una frecuencia con temporización histórica
apagada y qué niveles están certificados al activarla. Mostrar sólo perfiles
con el estado de validación declarado. Distinguir selección pendiente de perfil
activo hasta aplicar reset. MAX no promete una frecuencia histórica concreta.

La selección necesita al menos tres bits. Antes de asignarlos, producir un
inventario de `CONF_STR`, usos `hps_status` y compatibilidad AT/XT. El overlay
hardware de debug y la opción CPU de 25 MHz fueron retirados en P20: no son una
base para asignar perfiles. Actualmente el bit 71 figura reservado y 74:72
selecciona RAM instalada; también existen selecciones de almacenamiento.
Los números definitivos son una decisión de
integración pendiente, que deberá quedar escrita antes del RTL/OSD.

P06-R18. Definir codificación y valor predeterminado compatibles con configuraciones
guardadas. Si un estado antiguo selecciona un perfil no disponible, aplicar MAX
o una política de migración explícita y mostrar el modo realmente activo.

P06-R19. Primera versión: aplicar cambios mediante `Reset & apply settings`.
Bloquear nuevas solicitudes CPU, cancelar las no aceptadas, drenar las aceptadas
y aplicar el perfil al reiniciar el contexto CPU/chipset definido. No resetear
la SDRAM ni invalidar el contenido BIOS/VHD. Documentar qué periféricos se
reinician y no cambiar velocidad en mitad de una instrucción o transacción.

## 10. Evidencia de calibración

Usar documentación Intel y evidencia física/hardware-derived identificada.
SingleStepTests/80286 sirve donde su captura temporal y alcance lo permiten;
un PASS de registros/FLAGS no demuestra una traza temporal correcta. El modelo
de 86Box sirve de contraste, no de autoridad única para los ciclos históricos.
En su CPU nativa, sin overrides de cache, `cpu_waitstates=0` selecciona la tabla
automática de memoria;
no desactiva los ciclos intrínsecos de instrucciones (`CLOCK_CYCLES`). La tabla
Intel 286 local asigna memoria de 2 ciclos al perfil 6 MHz y de 3 al perfil
etiquetado `12` (12,5 MHz). Se registra esa configuración al medir, sin tratar
esos valores como captura física del bus de una placa real.

Para cada dato temporal registrar fuente, revisión/página o ID de traza, CPU,
condiciones iniciales, señales observadas y ambigüedades. No inventar constantes
para que CheckIt muestre un MHz específico. Las discrepancias entre evidencias
se registran y delimitan, sin cambiar resultados esperados arbitrariamente.

## 11. Matriz de validación

| ID | Prueba | Criterio |
| --- | --- | --- |
| P06-T01 | Cada frecuencia, ventana larga | Número de ticks y error de fase dentro del contrato |
| P06-T02 | Instrucciones register/memory y branches | Hitos y ciclos contra referencia identificada |
| P06-T03 | READY bajo, palabra impar, I/O de 8 bits | Secuencia y wait states correctos |
| P06-T04 | Prefetch lleno/vacío, saltos y prefijos | Solapamiento y descartes según el modelo |
| P06-T05 | IRQ/NMI, INTA, HLT, STI/SS y REP | Reconocimiento temporal y semántica correctos |
| P06-T06 | Descriptores, faults y tareas PM soportadas | Temporización declarada sin perder comprobaciones |
| P06-T07 | DMA/LOCK/refresco | Propiedad y tiempos del contrato de placa |
| P06-T08 | Cambio de selección con operación pendiente | Reset/drenaje y persistencia seguros |
| P06-T09 | PIT/RTC/audio/vídeo/teclado en todos los modos | Bases de tiempo independientes de CPU |
| P06-T10 | Programa determinista en todas las políticas | Estado arquitectónico equivalente con inputs controlados |
| P06-T11 | Backends y cargas adversas | Cero deadlines internos incumplidos en perfiles certificados |
| P06-T12 | DOS, disco y benchmarks en placa | Estabilidad; cifras identificadas como mediciones auxiliares |

## 12. Criterios de aceptación y entregables

Cada perfil se acepta individualmente con alcance de precisión, referencia,
tabla temporal versionada, métricas de ticks/deadlines, suite CPU/bus/eventos,
integración OSD, STA y RBF probado. Un perfil parcialmente validado se identifica
como tal; no se extrapola su aprobación al resto de frecuencias o a todo PM.

P06-M1 ya dispone del programa DOS canónico
`build/p06-timing-reference-20261003/T286REF.COM`, con fuentes en `SW/CPUTIME`,
y de [resultados aceptados del 286 ORIGINAL nativo de 86Box](P06_NATIVE_REFERENCE_RESULTS_20261003.md)
a 6 MHz y en su entrada `12`/12,5 MHz: host RC0, guest RC0 y validación estricta
de 42 muestras y seis resúmenes por perfil. Este paso previo al colaborador está
completado. Las mediciones físicas a 6 y 12 MHz en el mismo PC siguen
`NOT_MEASURED`; el temporizador mantiene `NOT_CALIBRATED`. La aceptación RAW del
programa no acepta temporización histórica de SPK286 ni cierra M1 completo.

El primer perfil candidato será **6 MHz**, empezando por casos dirigidos de
Real Mode de registro, branch/prefetch y RAM alineada con referencias calificadas.
Su alcance inicial no cubre todas las instrucciones, PM ni flancos de pines.
Antes de implementarlo deben estar fijados los hitos EU/BIU, READY y arbitraje,
la captura de respuestas entre ticks, el coste previsto y la frontera de prueba.
La falta de mediciones físicas se declara pendiente, nunca como PASS. Los otros
perfiles requieren sus propias matrices; no basta escalar un benchmark.

Mantener el modo rápido disponible, sin retardos históricos artificiales y con
todas las dependencias reales. La codificación OSD de Fast/T-states/velocidad se
decidirá tras ese contrato; esta actualización sólo introduce documentación.
