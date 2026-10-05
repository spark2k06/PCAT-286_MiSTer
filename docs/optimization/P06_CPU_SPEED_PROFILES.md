# P06 — Perfiles de CPU 6–25 MHz y MAX

Functional acceptance, 2026-10-05: the user accepts closure of the first
P06/P12 product version: MAX / 6 / 8 / 10 / 12.5 / 16 / 20 / 25 MHz,
integrated profile waits, main-menu selection and safe live changes without
reset. The preceding directed MiSTer measurements and dual-simulator
qualification remain the evidence for their declared scopes. Exact internal
EU/native pin timing and further physical-board calibration remain future
precision work; this functional acceptance does not certify them. The full
regression remains user-deferred. Physical 50 MHz setup/hold closure continues
separately, with the verified [deadline/buffer/palette candidate](P06_DEADLINE_FOLD_20261005.md).

Status, 2026-10-05: [main-menu selection and safe live changes](P06_LIVE_SPEED_20261005.md)
pass directed dual-simulator qualification. The all-features RBF is available;
its four-corner fit gives setup -6.051 ns and original-SDC hold +0.015 ns,
with the additional palette route requirement still missing by 0.065 ns.
MiSTer live-switch validation is pending. The dated reset-applied candidates
below remain historical evidence; physical setup closure is still open.

Previous status, 2026-10-04: the first general reset-applied OSD candidate is synthesized
and passes directed validation; its physical setup does not close. See
[the public candidate record](P06_OSD_CANDIDATE_20261004.md) and
[measured fit](P06_OSD_FIT_20261004.md) for
its current integration, evidence and bitstream milestones. It uses one CPU
and the existing common 50 MHz CPU/bridge/SDRAM clock. Historical instruction
intervals and normalized bus timing are provisional; full internal EU/native
pin timing and board-specific physical calibration remain open. P21 physical
timing acceptance is separate. The dated private milestones below preserve
their original limited scope. Aplican los
[requisitos comunes](README.md) y el
[modelo de temporización SPK286](../../vendor/spk286/SPK286_TIMING_MODEL.md).

El primer hito es definir y medir la referencia antes de modificar RTL/OSD:
[plan P06-M1](P06_TIMING_REFERENCE_PLAN_20261003.md). P12 documenta el
[contrato de referencia y la atribución de rendimiento](P12_REAL_CHECKNUM_MEMORY_ATTRIBUTION_20261002.md).
La parte nativa de 86Box está completada en
[los resultados P06-M1](P06_NATIVE_REFERENCE_RESULTS_20261003.md); las mediciones
físicas del colaborador a 6/12 MHz ya están
[recibidas y validadas como datos RAW](P06_PHYSICAL_REFERENCE_RESULTS_20261004.md).
El temporizador y las frecuencias físicas siguen sin calibración independiente;
el alcance histórico de M1 continúa abierto.

Ya están completadas la [extracción Intel de los kernels](P06_INTEL_TIMING_REFERENCE_20261003.md)
y la [especificación del piloto de 6 MHz](P06_TIMING_CONTRACT_20261003.md), con
captura/publicación de respuestas, unidades temporales, pruebas dirigidas y
base de recursos del fit seleccionado. Se han identificado diferencias entre
las tablas Intel y los handlers nativos de 86Box; sus medidas se conservan como
contraste. Ya hay componentes provisionales de reloj, bus retenido y primeras
duraciones con pruebas dirigidas. El [piloto M3 de registro](P06_CORE_REGISTER_PILOT_20261004.md)
ya conecta arranque y compromiso temporal a una CPU completa privada, con
mínimos de 2/3 relojes, equivalencia MAX y cancelaciones validados. Quedan el
bus completo histórico, los hitos restantes y la referencia física. El
[piloto M4 de fetch](P06_CORE_FETCH_PILOT_20261004.md) ya conecta Ts/Tc de CODE
con la respuesta retenida y seis bytes con reservas; su ámbito sigue siendo
privado y no incluye datos/INTA/HOLD/LOCK ni toda la planificación de instrucciones.

Tras reanudar la pausa de M5, el [piloto M6a de lecturas](P06_CORE_DATA_READ_PILOT_20261004.md)
califica Ts/Tc de byte y palabra par en la BIU y servicio de operandos reales,
con CODE desactivado y reutilizando la respuesta retenida. Es un componente
privado: M6b ya valida la propiedad lógica compartida CODE/DATA y M6c conecta
una primera lectura alineada a la CPU completa. M6d califica lecturas
consecutivas y M6e añade A1 impar privado con dos accesos y corrección +2.
Faltan las restantes operaciones.

El desarrollo provisional de componentes temporales y sus pruebas dirigidas
se registra en [el progreso del piloto](P06_PILOT_PROGRESS_20261003.md).
La conexión privada cubre instrucciones de registro calificadas y lecturas
A1 alineadas e impares, escrituras A3 y XOR RMW directo calificado;
esa conexión privada conserva su alcance original. La integración general
posterior se registra en el documento del candidato OSD enlazado al inicio.

## 1. Objetivo y alcance de precisión

Ofrecer las velocidades de la familia Intel 286 de 86Box:
**6, 8, 10, 12,5, 16, 20, 25 MHz y MAX**, con una única CPU funcional y una
política de temporización separada. La entrada de 86Box etiquetada `12` usa
12.500.000 Hz; una futura selección se identificará como 12,5 MHz. La referencia
física de 12 MHz ofrecida por el colaborador se registra por separado: no es una
medición a 12,5 MHz ni añade automáticamente un perfil de producto.

Decisión de producto confirmada el 2026-10-04: un único selector
**MAX / 6 / 8 / 10 / 12,5 / 16 / 20 / 25 MHz**. MAX conserva el comportamiento
rápido actual, sin retardos históricos añadidos. Las selecciones en MHz aplican
la política histórica del perfil CPU/placa correspondiente. No habrá un segundo
selector público de T-states: las esperas forman parte de ese perfil. Las
herramientas conservan variantes 0/1/2 para comparar y calibrar referencias.
Ninguna política puede eliminar dependencias reales, trabajo de instrucciones
o accesos visibles.

El usuario autoriza completar el desarrollo y la validación inicial de todas
las tareas necesarias con 86Box como referencia, sin esperar las mediciones
del colaborador. Intel fija el contrato arquitectónico y las diferencias
conocidas del emulador se registran expresamente. Un perfil podrá aceptarse
provisionalmente contra esa referencia con su alcance declarado; la posterior
evidencia física servirá para revisar calibración y discrepancias. Esta decisión
no convierte resultados ausentes en PASS ni certifica precisión de pines.

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

P06-R17. Un único selector relaciona MAX con avance por dependencias y las
frecuencias en MHz con temporización histórica. Las esperas CPU/placa se
definen dentro del perfil versionado; no son un ajuste público independiente.
Mostrar sólo perfiles con el estado de validación declarado. Distinguir
selección pendiente de perfil activo hasta aplicar reset. MAX no promete una
frecuencia histórica concreta.

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
completado. Las cuatro capturas físicas a 6 y 12 MHz nominales en el mismo PC
ya pasan la validación de 168 muestras y sus resúmenes; el temporizador mantiene
`NOT_CALIBRATED`. La aceptación RAW del
programa no acepta temporización histórica de SPK286 ni cierra M1 completo.

El primer perfil candidato será **6 MHz**, empezando por casos dirigidos de
Real Mode de registro, branch/prefetch y RAM alineada con referencias calificadas.
Su alcance inicial no cubre todas las instrucciones, PM ni flancos de pines.
Antes de implementarlo deben estar fijados los hitos EU/BIU, READY y arbitraje,
la captura de respuestas entre ticks, el coste previsto y la frontera de prueba.
La falta de mediciones físicas se declara pendiente, nunca como PASS. Los otros
perfiles requieren sus propias matrices; no basta escalar un benchmark.

Mantener MAX disponible, sin retardos históricos artificiales y con todas las
dependencias reales. La asignación de bits OSD del único selector de velocidad
sigue pendiente del inventario de integración. La referencia física pendiente
no bloquea el desarrollo ni su aceptación provisional frente a 86Box.

El [hito privado M6b](P06_CORE_SHARED_BUS_PILOT_20261004.md) ya valida propiedad
lógica compartida CODE/READ mediante fetch, cola, operand y BIU reales: 1.087
casos en ambos simuladores, con 972 cambios de propietario en el mismo Tc.
MAX conserva sus trazas originales. Esto no habilita todavía perfiles en el
core: falta integrar y validar los hitos de instrucciones completas de
memoria, los servicios restantes y cada velocidad declarada.

El [hito privado M6c](P06_CORE_MEMORY_CPU_PILOT_20261004.md) añade ejecución
real de `MOV AX,[moffs16]` alineado en Real Mode, con retención en TMP0 y
escritura de AX al primer límite permitido. Pasan 1.782 casos temporizados
en ambos simuladores; las trazas MAX y los streams de registro previos se
conservan. No se ha modificado el RBF ni habilitado un perfil público.
El mínimo de cinco relojes más esperas READ no certifica todavía todas las
fases de ejecución Intel: dependencias físicas y de fetch pueden alargarlo.
Palabras impares, escrituras, read/modify/write y los servicios restantes
siguen pendientes, al igual que los perfiles completos y la calibración física.

The [M6d private milestone](P06_CORE_READ_STREAM_20261004.md) qualifies
consecutive aligned A1 reuse without changing the M6c generated CPU or adding
hardware. Both simulators pass 240 programs/1,120 instructions per warm/cold
matrix and targeted lifecycle/recovery cases; MAX remains trace-identical.
It preserves the existing serialized handoff and does not accept its issue
gap as an Intel requirement. Public speeds and remaining memory services
are still pending.

The [M6e private milestone](P06_CORE_ODD_READ_CPU_PILOT_20261004.md) extends A1
to two-beat odd words, retaining the existing payload storage and DATA owner
until final Tc. A single alignment event adds two clocks separately from
each half's READ waits. Both simulators pass 2,143 timed cases and 43 identical
trace pairs; MAX and frozen aligned traces remain unchanged. Eight specified
negative controls, lint, affected units, microcode and bypass proofs pass.
The isolated BIU/duration delta is +30 generic cells/+4 register bits, not
complete FPGA ALMs. Writes/RMW, events, decoded lookahead and complete public
speeds remain open; production config and RBF are unchanged.

The [M6f private milestone](P06_CORE_WRITE_CPU_PILOT_20261004.md) qualifies
serialized A3 aligned/odd writes with mutable-memory checks at every physical
acceptance. Both simulators pass 2,227 timed cases and 47 identical pairs;
MAX and prior READ traces are preserved. The isolated increment is 13 generic
cells and one control bit, without new payload capacity. The minimum is three
plus two for an odd word; WRITE waits extend real dependencies without being
charged as READ waits. This does not close historical write-buffer EU overlap
or full C08/C09/C10/C15. RMW, consecutive WRITE/READ ordering and remaining
public-speed/event coverage remain open; production and selected RBF unchanged.

The [M6g private milestone](P06_CORE_RMW_CPU_PILOT_20261004.md) qualifies
bounded prefix-free `81 36 disp16 imm16` XOR word RMW. Original READ/TMP0,
ALU/TMP2, WRITE disposition and COMMIT_FLAGS remain the functional sequence;
FLAGS and retirement share the first permitted boundary after the store.
Retained ModR/M metadata corrects the existing three-clock RI admission to
seven once, then each odd reference adds two; only READ waits charge the EU
budget. Both simulators pass 2,503 timed cases and 67 identical trace pairs.
MAX, frozen READ/WRITE and register-stream traces are preserved. Nine specific
mutants, lint, affected units, microcode and component bypass proofs pass.
The isolated BIU/duration/executor-fragment increase is twenty generic cells
and zero register bits, excluding full FPGA cost. Serialized dependencies
make the aggregate seven/eleven-clock minimum nonbinding in the fastest
observed cases; exact Intel issue phases and write-buffer EU overlap remain
open. Production config, source selection and selected RBF are unchanged.

## 2026-10-04 physical anchors and profile approximation

The [physical reference analysis](P06_PHYSICAL_REFERENCE_RESULTS_20261004.md)
retains all four collaborator CSVs, independent 6/12 hardware-selector labels
and 168 validated fixed-work samples. The program argument changes metadata,
not workload. These are provisional behavioral anchors; board identity,
executable identity on the physical machine and actual clocks remain unverified.

Additional native visible-zero controls at 6/12.5 MHz pass host and guest
checks. Automatic config zero differs from visible-zero config one. At 12.5,
the latter changes memory/prefetch service from three to two cycles and R0
from 1,017 to 643 ticks. Against visible-zero native and illustrative frequency
normalization, physical12 is approximately +5.4% elapsed for R0, +17.1% for B0
and +46.9% for M0. The automatic comparisons remain archived unchanged.

User direction: use Intel, native 86Box and the physical6/12 anchors to make
the best coherent approximation for every historical profile. Calibrate
execution, CODE prefetch/branches and DATA/board READY separately; one global
benchmark multiplier cannot explain these different sensitivities. Use the
same causal model at 8/10/12.5/16/20/25 MHz and explicitly identify those
unmeasured predictions. Interpolation/extrapolation of aggregate kernel times
alone does not define instruction timing. MAX remains dependency-driven.
No CPU RTL, public profile, OSD, clock or RBF adjustment is made by this analysis.

## 2026-10-04 MiSTer profile measurements

The first synthesized eight-profile selector has
[hardware fixed-work observations](P06_MISTER_REFERENCE_RESULTS_20261004.md)
from the user, with reset applied for every selection. All 336 samples pass
the unchanged T286REF validator. MAX CHECKNUM preserves 6906 / 121.6K, and
BIOS/CheckIT reportedly display each intended nominal MHz.

Historical calibration remains open: the gross kernels complete earlier
than the retained physical 6/12 anchors and native 6/12.5 visible-zero controls.
R0 at 25 MHz is also slower than at 20 MHz in this capture, despite CHECKNUM
improving. Next work should qualify per-instruction deadline/implementation
extensions at 20/25 MHz, taken-target/refill timing and separate board READ/WRITE
policy. Keep Intel minima and unchanged benchmark bytes; neither a global
multiplier nor MHz detection alone establishes the intended AT timing model.
The analysis changes evidence/documentation only and does not close P06/P12
calibration or the candidate's physical setup failure.

## 2026-10-05 target-handoff hardware measurements

The [eight-profile follow-up](P06_MISTER_TARGET_HANDOFF_RESULTS_20261005.md)
validates 336 samples and 48 summaries on the user-identified first
target-handoff RBF. MAX remains 6906 / 121.6K, and its three fixed-work gross
medians are unchanged. Every adjacent historical profile remains faster.
The added target-length allowance increases B0 gross by about 14.4% at 6..20
MHz and 10.1% at 25, with approximately 23 nominal clocks per body through
20 MHz. R0/M0 gross remain within 0.6% of the preceding capture. This closes
the targeted hardware measurement gate, not general historical calibration.
Resume physical setup/hold work without a benchmark multiplier or MHz retune.
