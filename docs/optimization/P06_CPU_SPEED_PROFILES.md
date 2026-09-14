# P06 — Perfiles de CPU 6–25 MHz y MAX

Estado: especificación de temporización e integración futura. Base: `4a05f97`,
2026-09-13. Aplican los [requisitos comunes](README.md) y el
[modelo de temporización SPK286](../../vendor/spk286/SPK286_TIMING_MODEL.md).

## 1. Objetivo y alcance de precisión

Ofrecer las selecciones solicitadas: **6, 8, 10, 12, 16, 20, 25 MHz y MAX**,
con una única CPU funcional y una política de temporización separada.
La lista solicitada usa 12 MHz; no se sustituye por el candidato 12,5 MHz que
aparece en documentación conceptual anterior de SPK286.

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

| Selección prevista | Política | Estado en la base de esta especificación |
| --- | --- | --- |
| 6 MHz | Histórica, evidencia de CPU/placa identificada | Pendiente |
| 8 MHz | Histórica, evidencia de CPU/placa identificada | Pendiente |
| 10 MHz | Histórica, evidencia de CPU/placa identificada | Pendiente |
| 12 MHz | Histórica, evidencia de CPU/placa identificada | Pendiente |
| 16 MHz | Histórica, variante rápida identificada | Pendiente |
| 20 MHz | Histórica, variante rápida identificada | Pendiente |
| 25 MHz | Histórica, variante rápida identificada | Pendiente |
| MAX | Avance por dependencias reales | Integración acelerada actual, aún en desarrollo |

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
sin fijar de antemano una nueva frecuencia maestra.

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
ocupado por una operación real. Si no se demuestra transparencia temporal,
desactivar el buffer para los perfiles exactos inicialmente.

## 8. Bases de tiempo de periféricos

P06-R16. PIT, RTC, vídeo, audio y protocolo de teclado mantienen sus relojes
propios. El cambio de CPU no multiplica su frecuencia. Los accesos CPU a estos
dispositivos sí se programan con la política de bus del perfil elegido.

La frecuencia ISA/AT y sus wait states deben definirse como propiedades de
placa, no como una división automática aplicada a toda la RAM. Los puertos
XT-IDE de 8 bits conservan la secuencia de bytes, latch y tiempos requeridos.

## 9. OSD, estado guardado y cambio de modo

P06-R17. Mostrar `CPU Speed` con las ocho opciones solicitadas. Distinguir
selección pendiente de perfil activo hasta aplicar reset. MAX no se convierte
en una promesa de una frecuencia concreta.

La selección necesita al menos tres bits. Antes de asignarlos, producir un
inventario de `CONF_STR`, usos `hps_status` y compatibilidad AT/XT. El bloque de
debug actual utiliza bits 71–84 y hay selecciones existentes de almacenamiento;
no se reutilizan a ciegas. Los números definitivos son una decisión de
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

Entregar primero infraestructura temporal y un perfil con evidencia suficiente;
añadir los demás mediante sus propias matrices. Mantener MAX disponible para
desarrollo, sin retardos históricos artificiales y con todas las dependencias
reales. No se introduce un modo FAST adicional en OSD en esta propuesta; la
arquitectura puede conservarlo como política interna para futuras pruebas.
