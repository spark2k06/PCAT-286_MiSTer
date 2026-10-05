# SPK286 — Auditoría de los tres commits iniciales de Phase 9

**Fecha:** 15 de septiembre de 2026.  
**Repositorio:** `spark2k06/SPK286` — privado.  
**Rama:** `codex/phase9-timing-tstates`.  
**HEAD auditado:** `151b9c7006a5275ac31efeaa7d5f7ee10bb38c23`.  
**Base anterior al alcance:** `698c7a8cf541f6400c25204344e1209441b94eae`.  
**Dictamen:** **requiere correcciones y validación focalizada antes del cierre técnico de Phase 9A**. La orientación arquitectónica es adecuada, pero hay problemas de medición y de integridad de las evidencias. **La regresión completa se realizará al finalizar Phase 9; su ausencia en este punto no bloquea por sí sola Phase 9A ni el avance entre subfases.** El fallo heredado de CI sigue registrado y deberá resolverse antes de la aprobación global de Phase 9.

Esta auditoría corresponde al snapshot indicado, no a los commits posteriores que incorporan o actualizan este informe. La actualización del 15 de septiembre de 2026 recoge la decisión de Aitor de reservar la regresión completa para el final de Phase 9. Solo se modifica este informe: no se alteran RTL, microcódigo, scripts, expectativas de pruebas, configuración de CI ni otros documentos de política del repositorio.

## 1. Alcance y metodología

Se revisaron los tres commits siguientes, en orden cronológico:

| Commit | Mensaje | Aportación |
| --- | --- | --- |
| [`000cabbae9`](https://github.com/spark2k06/SPK286/commit/000cabbae9ea994aa78218019e04157b8bfaa255) | `docs: establish phase 9 timing dependency register` | Inventario de dependencias obligatorias y separación respecto a retardos de compatibilidad. |
| [`8d32d69c05`](https://github.com/spark2k06/SPK286/commit/8d32d69c05ff09fd2cc2754699a744fe6ff52048) | `feat: add phase 9A timing observation trace` | Módulo observador, contadores, salidas de depuración e integración con la CPU. |
| [`151b9c7006`](https://github.com/spark2k06/SPK286/commit/151b9c7006a5275ac31efeaa7d5f7ee10bb38c23) | `test: add reproducible phase 9A timing capture` | Banco de captura, CSV, manifiesto JSON y comando de generación. |

La [comparación completa](https://github.com/spark2k06/SPK286/compare/698c7a8cf541f6400c25204344e1209441b94eae...151b9c7006a5275ac31efeaa7d5f7ee10bb38c23) contiene exactamente tres commits y diez archivos cambiados. Se contrastaron los cambios con `AGENTS.md`, la especificación de Phase 9, la selección de fuentes de compilación y las interfaces de fetch, cola, operandos y eventos.

La auditoría combina revisión estática, contraejemplos de las expresiones RTL, pruebas Python aisladas del capturador y consulta del estado y los logs reales de GitHub Actions. **No se ha ejecutado localmente Verilator, Icarus, Yosys ni la regresión completa.** Los pases de simulación mencionados en la documentación del proyecto son resultados declarados allí, no resultados reproducidos en esta auditoría.

Para el capturador se ejecutó una copia cuyo contenido coincide exactamente con el blob Git `a0502c724fa5183c387546245b99600ca2e35d59`. Las llamadas al simulador y a su consulta de versión se sustituyeron por entradas sintéticas; Git operó sobre un repositorio temporal real. Esto permite probar el comportamiento del programa Python, pero **no constituye una simulación de la CPU ni una captura física**.

### 1.1. Criterio de validación acordado para Phase 9

Por indicación expresa de Aitor, **la regresión completa queda diferida hasta finalizar Phase 9**, no hasta finalizar cada subfase. Este criterio actualiza las recomendaciones de calendario de esta auditoría; no modifica los resultados obtenidos ni convierte verificaciones pendientes o fallidas en pases.

| Momento | Validación exigida por esta auditoría |
| --- | --- |
| Durante el desarrollo y para cerrar técnicamente 9A | Corregir H1–H4 y verificar los cambios mediante pruebas focalizadas, casos negativos, bancos afectados en ambos simuladores y lint/síntesis cuando corresponda. |
| Al finalizar Phase 9 | Ejecutar la regresión completa y las cadenas globales de validación aplicables, con V1 resuelto y evidencias del snapshot final. |

No disponer todavía de una regresión completa aprobada es una **validación final pendiente planificada**, no un defecto adicional de 9A. V1 es distinto: existe un fallo real de CI en el snapshot auditado, que se conserva como incidencia heredada. Su corrección debe comprobarse de forma focalizada; no exige relanzar ahora toda la cadena global. Cualquier fallo de las pruebas focalizadas de un incremento sí debe resolverse antes de dar ese incremento por validado.

El cierre técnico de 9A y el avance entre subfases no equivalen a la aprobación global de Phase 9 ni a una certificación de exactitud histórica. La decisión no desactiva ni cambia automáticamente los workflows de CI existentes.

## 2. Conclusión ejecutiva

La separación entre observación y ejecución funcional es una buena base. El observador no introduce retardos de compatibilidad ni realimenta las decisiones de la CPU; la política `0` se identifica como baseline funcional normalizada, sin atribuirle exactitud histórica. La incorporación del nuevo módulo a las compilaciones también queda cubierta por la selección dinámica de `rtl/*.sv`.

No se ha identificado en estos cambios una regresión arquitectónica demostrada de la CPU. Eso no equivale a certificar su ausencia: la regresión completa queda pendiente para el cierre de Phase 9. Independientemente de ese calendario, la nueva instrumentación tiene defectos que deben corregirse porque pueden producir conclusiones equivocadas sobre tiempos y esperas.

Se distinguen **cuatro hallazgos nuevos de prioridad P2**, **un fallo P1 heredado pendiente para la aprobación global de Phase 9** y varias revisiones de cobertura/documentación. P1 se mantiene por el fallo real de validación, no por la decisión de aplazar la regresión completa. P2 identifica defectos relevantes que deben corregirse antes de utilizar la nueva captura como evidencia fiable. Ninguna de estas prioridades implica que se haya probado corrupción funcional de instrucciones.

| ID | Prioridad | Procedencia | Resultado |
| --- | --- | --- | --- |
| H1 | P2 | `8d32d69c05` | `operand_wait_cycles` no representa de forma fiable la espera real del servicio de operandos. |
| H2 | P2 | `151b9c7006` | Una carpeta de compilación externa provoca `ValueError` después de generar el CSV. |
| H3 | P2 | `151b9c7006` | El manifiesto puede atribuir al mismo origen capturas de un árbol limpio y de RTL modificado sin commit. |
| H4 | P2 | `151b9c7006` | El validador puede emitir `PASS` para un CSV temporalmente incoherente e incompleto. |
| V1 | P1, pendiente de cierre global de Phase 9 | Heredado del baseline | La CI del snapshot auditado falla en tres anclas de mutación; corregirlas y comprobarlas de forma focalizada. La validación global queda para el final de Phase 9. |

**Recomendación:** conservar la infraestructura, corregir H1–H4 y completar las pruebas focalizadas y la cobertura necesarias para cerrar técnicamente 9A. Mantener V1 abierto hasta su corrección, sin debilitar los controles, y reservar la regresión completa para el final de Phase 9. No utilizar los contadores afectados como referencia fiable de calibración mientras sus defectos sigan abiertos. La regresión completa pendiente no constituye por sí sola un impedimento para cerrar técnicamente 9A una vez resueltos sus hallazgos y controles específicos.

## 3. Hallazgos nuevos y revisiones necesarias

### H1 — El contador de operandos confunde disponibilidad de la BIU con espera efectiva

**Ubicación:** [`rtl/spk286.sv:609`](https://github.com/spark2k06/SPK286/blob/151b9c7006a5275ac31efeaa7d5f7ee10bb38c23/rtl/spk286.sv#L599-L624).  
**Contraste:** [`spk286_operand.sv`](https://github.com/spark2k06/SPK286/blob/151b9c7006a5275ac31efeaa7d5f7ee10bb38c23/rtl/spk286_operand.sv) y [conexión efectiva del servicio](https://github.com/spark2k06/SPK286/blob/151b9c7006a5275ac31efeaa7d5f7ee10bb38c23/rtl/spk286.sv#L832-L855).  
**Evidencia:** defecto de clasificación identificado estáticamente; no se ha ejecutado un programa completo para medir su frecuencia.

La entrada del observador se calcula así:

```systemverilog
.operand_wait(operand_request && !operand_register_direct && !memory_request_ready),
```

Sin embargo, `operand_register_direct` describe el contexto ModRM, no necesariamente el operando que se está atendiendo. El servicio real distingue `select_rm`, accesos a registro, accesos forzados a memoria, solicitudes pendientes y respuestas disponibles.

Un contraejemplo de la lógica revisada es:

| Condición | Valor |
| --- | --- |
| Hay solicitud de operando válida, sin cancelación ni bloqueo | `1` |
| El contexto ModRM identifica una forma de memoria | `operand_register_direct = 0` |
| La microoperación selecciona REG, no RM | `operand_select_rm = 0` |
| No existe solicitud pendiente del servicio | `pending_q = 0` |
| La BIU no admite una nueva solicitud de memoria | `memory_request_ready = 0` |

El servicio calcula `is_memory = 0` y puede devolver `done = 1`, pero la expresión del observador vale `1`: **cuenta espera cuando ese acceso a registro termina localmente**. Tampoco excluye explícitamente el ciclo en que ya llega la respuesta de memoria. En sentido contrario, utilizar el ModRM sin los modificadores efectivos no representa correctamente todos los accesos forzados a memoria, como los de pila o determinados servicios protegidos.

**Impacto:** la separación entre trabajo de la EU, espera de operandos y actividad de bus puede quedar sesgada. Es un problema de instrumentación, no una prueba de ejecución incorrecta de la instrucción.

**Revisión necesaria:** definir primero la unidad exacta del contador. Derivar la observación del servicio que conoce si existe una operación de memoria pendiente y si puede completarse; distinguir, cuando corresponda, espera de admisión, espera de respuesta y finalización. Aplicar las mismas condiciones de cancelación y clasificación efectiva que utiliza el servicio. No sustituir la expresión por otra aproximación basada únicamente en el ModRM.

**Criterio de aceptación:** un acceso REG con BIU ocupada no incrementa espera de memoria; un acceso de memoria con respuesta retrasada cuenta únicamente el intervalo definido; la finalización no se contabiliza como espera; los accesos forzados a memoria y las cancelaciones tienen casos dirigidos. Un scoreboard independiente debe contrastar los incrementos, no solo comprobar que sean mayores que cero.

### H2 — `--build-dir` externo rompe la generación del manifiesto

**Ubicación:** [`tools/capture_timing_trace.py:54–90`](https://github.com/spark2k06/SPK286/blob/151b9c7006a5275ac31efeaa7d5f7ee10bb38c23/tools/capture_timing_trace.py#L54-L94).  
**Evidencia:** reproducido ejecutando el capturador con la llamada al simulador sustituida por un generador de CSV sintético.

El argumento admite una ruta absoluta, y `SPK286_BUILD_DIR` también permite dirigir la salida fuera del repositorio. Tras ejecutar el banco y leer su CSV, el programa hace:

```python
relative_trace = trace_path.relative_to(ROOT).as_posix()
```

Una ruta como `/tmp/spk286-build/timing/spk286_timing_capture.csv` no es descendiente de `ROOT`. El resultado es `ValueError`: existe CSV, pero no se termina el manifiesto.

**Revisión necesaria:** definir la base de las rutas del manifiesto y permitir una salida externa, preferentemente usando rutas relativas al propio manifiesto. Normalizar las rutas antes de utilizarlas. Si se decide restringirlas por contrato, validar la restricción antes de compilar y documentarla expresamente; no fallar al final.

**Criterio de aceptación:** generación correcta con carpeta predeterminada, ruta relativa, ruta absoluta interna y ruta absoluta externa, tanto por argumento como por variable de entorno. Verificar que la ruta almacenada permite localizar el CSV desde la base documentada.

### H3 — La identidad de fuentes no detecta cambios locales en RTL compilado

**Ubicación:** [`tools/capture_timing_trace.py:86–94, 118–120`](https://github.com/spark2k06/SPK286/blob/151b9c7006a5275ac31efeaa7d5f7ee10bb38c23/tools/capture_timing_trace.py#L86-L120).  
**Contraste:** [`scripts/rtl_sources.sh`](https://github.com/spark2k06/SPK286/blob/151b9c7006a5275ac31efeaa7d5f7ee10bb38c23/scripts/rtl_sources.sh).  
**Evidencia:** reproducido en un repositorio temporal real, con fuentes y CSV sintéticos.

El manifiesto guarda `git rev-parse HEAD`, la rama y los hashes de tres archivos: observador, banco e include de señales. No comprueba si el árbol tiene modificaciones y no calcula una identidad de todos los archivos que entran realmente en la compilación.

La compilación utiliza los paquetes y la ROM generados, además de todo `rtl/*.sv`. Cambios sin commit en `spk286.sv`, la BIU u otros módulos no aparecen en esos tres hashes ni cambian `HEAD`.

La reproducción creó un manifiesto, modificó un archivo seguido por Git en `rtl/spk286.sv` y volvió a ejecutar el programa con el mismo CSV sintético. Git detectó el cambio, pero **los dos manifiestos resultaron idénticos**. Esto demuestra la carencia del registro de procedencia; no demuestra que dos simulaciones distintas deban generar el mismo CSV.

**Matiz:** en un checkout limpio e inmutable, un SHA completo sí identifica el contenido versionado. El defecto afecta a la aceptación no señalizada de un árbol modificado y a la falta de garantías sobre las entradas utilizadas durante la ejecución.

**Revisión necesaria:** rechazar modificaciones en las entradas relevantes, o marcar el árbol como modificado y registrar una huella completa de fuentes, includes, microcódigo generado, capturador, scripts y configuración de compilación. Obtener la identidad antes de ejecutar y verificar que no cambia durante la captura, o compilar desde un snapshot inmutable. Para fuentes externas, registrar también su identidad.

**Criterio de aceptación:** modificar un módulo RTL fuera de los tres archivos actuales debe provocar rechazo o una identidad de entrada diferente y explícita. Las capturas de un árbol limpio deben conservar la trazabilidad al commit. El hash del CSV verifica el archivo producido; por sí solo no identifica el código que lo produjo.

### H4 — La validación del CSV no comprueba el contrato temporal

**Ubicación:** [`tools/capture_timing_trace.py:62–84, 121–135`](https://github.com/spark2k06/SPK286/blob/151b9c7006a5275ac31efeaa7d5f7ee10bb38c23/tools/capture_timing_trace.py#L62-L135).  
**Evidencia:** reproducido con entradas sintéticas entregadas al programa original.

El programa comprueba que haya filas, ocho cabeceras y valores uniformes para esquema y política. No valida las 32 columnas emitidas por el banco, la continuidad de ciclos, los rangos, las relaciones entre contadores ni la coherencia de los campos de bus.

Una reproducción con solo diez columnas fue aceptada con `TIMING CAPTURE MANIFEST PASS` y código de salida `0`, aunque faltaban 22 columnas y el resumen contenía:

```json
{
  "first_cycle": 10,
  "last_cycle": 9,
  "accepted_transfers": -1,
  "ready_wait_cycles": -2,
  "prefetch_requests": 1,
  "queue_consumes": 1,
  "halted": false
}
```

Otra reproducción eliminó `prefetch_requests`: superó la comprobación inicial de cabeceras y terminó después con `KeyError`, porque esa columna se utiliza en el resumen pero no forma parte del conjunto requerido.

El banco SV sí tiene aserciones sobre su ejecución. Por tanto, esto **no significa que el banco actual produzca esos valores ni que el programa ignore un código de error del simulador**. El problema es que el CSV publicado y sus observaciones no se validan como evidencia temporal independiente.

**Revisión necesaria:** añadir un esquema completo con tipos y rangos, detección de datos desconocidos, filas incompletas, columnas duplicadas y ausencia de campos. Verificar ciclos, contadores y coherencia de bus. Mantener separadas las reglas generales del formato y las expectativas específicas de MOV/XCHG/HLT.

La captura se toma **antes del flanco ascendente**. Para un intervalo sin reset, el incremento observado en la fila siguiente corresponde al bus de la fila actual. Un ejemplo de relación a verificar es:

```text
accepted_transfers[i + 1] - accepted_transfers[i] == (phase[i] == 2)
ready_wait_cycles[i + 1] - ready_wait_cycles[i] == (phase[i] == 1)
biu_busy_cycles[i] == accepted_transfers[i] + ready_wait_cycles[i]
```

Estas relaciones deben aplicarse al esquema y las condiciones actuales; un futuro reset por épocas, otro protocolo o una política distinta necesitarán reglas explícitas, no excepciones silenciosas.

**Criterio de aceptación:** cada mutación del CSV anterior se rechaza con diagnóstico útil y salida distinta de cero. Las capturas válidas de ambos simuladores pasan el mismo validador. Comprobar también `queue_count` dentro de capacidad, política y versión conocidas, contadores no negativos y resultado final esperado para este workload.

## 4. V1 — Fallo heredado de CI pendiente para el cierre global de Phase 9

**Evidencia consultada:** [run `34939650034`, job `104285156452`](https://github.com/spark2k06/SPK286/actions/runs/34939650034/job/104285156452), ejecución por `push` del HEAD auditado. El job terminó en `failure` el 15 de septiembre de 2026, aproximadamente a las 07:02 UTC.

`make phase7-check` falla al ejecutar validaciones heredadas. Los logs muestran 261 pruebas Python ejecutadas y tres fallos en [`tests/test_mutation_anchors.py:17`](https://github.com/spark2k06/SPK286/blob/151b9c7006a5275ac31efeaa7d5f7ee10bb38c23/tests/test_mutation_anchors.py#L10-L20):

| Auditor / mutación | Módulo objetivo | Ocurrencias encontradas; se esperaba una |
| --- | --- | --- |
| `audit_events / restore-system-bits` | `spk286_micro_executor` | `2` |
| `audit_data / exchange-accumulator` | `spk286_decoder` | `0` |
| `audit_far / far-context-offset` | `spk286_micro_executor` | `0` |

Las [definiciones de eventos](https://github.com/spark2k06/SPK286/blob/151b9c7006a5275ac31efeaa7d5f7ee10bb38c23/tools/audit_events.py), [datos](https://github.com/spark2k06/SPK286/blob/151b9c7006a5275ac31efeaa7d5f7ee10bb38c23/tools/audit_data.py) y [saltos lejanos](https://github.com/spark2k06/SPK286/blob/151b9c7006a5275ac31efeaa7d5f7ee10bb38c23/tools/audit_far.py) apuntan a esos módulos. Ni esos auditores, ni el test de anclas, ni los dos módulos objetivo cambian en el rango auditado. Por ello, la incompatibilidad de esas anclas se clasifica como **heredada respecto a la base de esta revisión**, no como un fallo introducido por la nueva instrumentación. No se ha determinado aquí el commit histórico que la originó.

El log también contiene un pase anterior de 88 pruebas de microcódigo, pero eso no convierte el job en un pase. Las etapas posteriores de Phase 8 y de clasificación de evidencias quedaron omitidas. La consulta de estados clásicos vacía tampoco significa que GitHub Actions haya pasado.

**Revisión necesaria:** actualizar cada ancla para inyectar exactamente una vez el defecto semántico previsto en el RTL actual; ejecutar de forma focalizada el test de anclas, el banco original y los mutantes afectados para confirmar su rechazo por la aserción funcional correspondiente. **No cambiar la expectativa de una ocurrencia, saltarse la mutación ni aceptar un fallo de compilación como rechazo funcional.** La repetición de las cadenas completas heredadas y de la regresión global se realizará al finalizar Phase 9, conforme al criterio acordado. V1 deberá estar resuelto para esa aprobación global; no se exige una regresión completa inmediata como condición previa para continuar con 9A.

La documentación de Phase 9 ya reconoce que la regresión completa local se interrumpió durante una compilación y no la declara aprobada. Ese intento conserva su resultado histórico; la ejecución completa pendiente se programa ahora para el cierre de Phase 9. La CI fallida tampoco se transforma en un pase, pero no contradice por sí sola los pases focalizados declarados ni demuestra un defecto introducido por 9A. Esta actualización del calendario no aporta nuevas ejecuciones ni acredita que V1 se haya corregido.

## 5. Cobertura y documentación pendientes de cierre

### 5.1. Probar la observación, no solo que existan contadores

El [test unitario del observador](https://github.com/spark2k06/SPK286/blob/151b9c7006a5275ac31efeaa7d5f7ee10bb38c23/sim/unit/spk286_timing_trace_tb.sv) cubre contadores básicos, espera READY, propietario de código y una combinación de carriles. No basta para validar todas las combinaciones del esquema: `execution_enable` permanece desactivado y HOLD/HLDA no se ejercitan; tampoco se comprueban de forma completa datos de lectura/escritura, propietario INTA y carriles bajo/alto.

La [captura integrada](https://github.com/spark2k06/SPK286/blob/151b9c7006a5275ac31efeaa7d5f7ee10bb38c23/sim/unit/spk286_timing_capture_tb.sv) aporta un programa acotado y útil, con READY determinista y XCHG implícitamente bloqueado. No sustituye pruebas de I/O, palabra impar, INTA, cesión HOLD/HLDA, cancelación con transacción pendiente o reset durante espera.

Añadir casos dirigidos para esas situaciones y comprobar todos los campos exportados contra expectativas independientes. En el workload actual, comprobar también el AX final `C35A`, además del valor `1234` escrito en memoria. Ejecutar las capturas de ambos simuladores en carpetas separadas para conservar sus evidencias y compararlas; la ruta compartida de `test_units.sh both` actualmente conserva el CSV de la última ejecución.

### 5.2. No confundir ocupación con ciclos perdidos

`queue_empty_cycles` mide `execution_enable && queue_count == 0`; no representa por sí solo que la EU quisiera consumir un byte y estuviese detenida por su ausencia. El nombre puede conservarse como medida de ocupación, pero no utilizarlo como contador de starvation sin una señal adicional de demanda.

Asimismo, READY, cola vacía y espera de operandos pueden coincidir. Los contadores no forman automáticamente una partición del tiempo total. Documentar qué métricas se solapan y cuáles son eventos, ciclos o transferencias físicas.

### 5.3. El inventario debe enlazar dependencias con observaciones concretas

El [nuevo registro de dependencias](https://github.com/spark2k06/SPK286/blob/151b9c7006a5275ac31efeaa7d5f7ee10bb38c23/docs/PHASE9_SYSTEM_TIMING_DEPENDENCIES.md) acierta al preservar dependencias reales en todos los modos y mantener el chipset fuera de SPK286. Sin embargo, una tabla de categorías no demuestra todavía su propio criterio de cierre: clasificar cada espera actual del RTL.

Completar una matriz con módulo/señal o estado, condición de entrada/salida de espera, clase, contador/campo y test exacto. El registro exige observar el orden entre aserción de interrupción y reconocimiento; el observador actual no recibe `intr`/`nmi`. Los contadores de petición y finalización internas no permiten reconstruir por sí solos ese intervalo externo. Añadir las señales/contexto necesarios o delimitar explícitamente esa observación como pendiente.

No es necesario incorporar lógica PC/AT ni exigir hashes de un RBF inexistente para este banco CPU-only. La metadata de consumidores reales corresponderá a las pruebas de integración que los utilicen.

### 5.4. Definir muestreo, reset y fin de captura

Especificar que cada fila es una muestra previa al flanco y que sus contadores contienen los flancos ya ejecutados. El banco escribe antes del último flanco, pero imprime contadores después de él: no identificar automáticamente el resumen de la última fila con el estado posterior a la última llamada a `tick`.

Decidir si se publica una muestra terminal adicional o se documenta un intervalo de captura semiabierto. También debe quedar definido cómo se representaría un reset intermedio: hoy `trace_valid` se desactiva en reset y el contador de ciclos vuelve a cero. No se ha demostrado que el workload actual sufra un error funcional por ello; falta fijar el contrato para futuros consumidores.

Actualizar el encabezado de estado de `PHASE9_TIMING_FIDELITY.md`, que sigue describiendo la fase como planificada, para distinguir **9A implementada parcialmente**, validaciones ejecutadas, pendientes y ausencia de aprobación histórica.

## 6. Pruebas efectuadas durante esta auditoría

Entorno de las reproducciones: Python `3.13.5`. Se verificó la identidad del archivo con la fórmula de blob Git, obteniendo `a0502c724fa5183c387546245b99600ca2e35d59` antes de ejecutarlo. Se ejecutaron cinco comprobaciones de caracterización:

| Comprobación | Resultado observado |
| --- | --- |
| Entrada sintética de control | Retorno `0`; manifiesto creado. |
| Carpeta de salida externa | `ValueError` tras crear CSV; sin manifiesto. |
| CSV incompleto, ciclos decrecientes y contadores negativos | Aceptado con `PASS`; demuestra H4. |
| Falta `prefetch_requests` | `KeyError` no detectado en la validación inicial. |
| Modificación de RTL seguido por Git y no incluido en hashes | Mismo manifiesto antes y después; demuestra H3. |

Las cinco comprobaciones reprodujeron el comportamiento esperado por la auditoría. **Ese resultado no significa que el software esté corregido**: son pruebas que confirman sus defectos actuales. El código del capturador no se alteró; las sustituciones afectaron únicamente a sus dependencias externas y al directorio de fixtures.

La observación de H1 procede del código y del contraejemplo lógico descrito, no de esas cinco pruebas Python. El fallo de CI procede de la ejecución real de GitHub, no del entorno local.

## 7. Plan de revisión: validación incremental y cierre global

### 7.1. Durante Phase 9 y para el cierre técnico de 9A

1. **Corregir la semántica y verificabilidad del observador.** Resolver H1, documentar ocupación frente a starvation, solapamientos y flanco de muestreo; añadir scoreboards para bus, operandos y ciclos.
2. **Endurecer la herramienta de evidencias.** Resolver H2–H4, introducir pruebas negativas del CSV y procedencia completa o rechazo explícito de árboles modificados.
3. **Completar y conservar las evidencias focalizadas.** Ejecutar los bancos y pruebas afectados, con ambos simuladores para el RTL y lint/síntesis cuando corresponda; guardar CSV, JSON y logs separados e identificados por el snapshot realmente comprobado. Cerrar o delimitar explícitamente las observaciones pendientes de la matriz de dependencias, sin declarar completada cobertura ausente.
4. **Tratar V1 como incidencia heredada separada.** Corregir y verificar las anclas y los mutantes afectados de forma focalizada. Mantener constancia de su estado real hasta resolverlo, sin exigir una ejecución inmediata de toda la regresión para cada avance de 9A.

Para el cierre técnico de 9A se requieren sus correcciones y evidencias específicas. **No se requiere todavía la regresión completa del proyecto**, que queda para el final de Phase 9. Tampoco se concede una aprobación automática de 9A por aplazarla: H1–H4 y cualquier fallo de sus controles específicos siguen pendientes hasta demostrar su resolución.

Comandos existentes de validación focalizada para el repositorio corregido; esta lista no afirma que ya se hayan ejecutado aquí y debe completarse con las pruebas específicas añadidas para H1–H4:

```bash
bash scripts/test_units.sh both spk286_timing_trace
python3 -m tools.capture_timing_trace --simulator verilator --build-dir build/timing-audit-verilator
python3 -m tools.capture_timing_trace --simulator iverilog --build-dir build/timing-audit-iverilog
bash scripts/lint.sh
bash scripts/synth_check.sh
```

Para comprobar las anclas al corregir V1, sin lanzar la cadena completa:

```bash
python3 -m unittest discover -s tests -p 'test_mutation_anchors.py' -v
```

Ese test de anclas no sustituye la comprobación del banco original y del rechazo funcional de cada mutante afectado.

### 7.2. Al finalizar Phase 9

Ejecutar la **regresión completa** y las cadenas globales heredadas/aplicables, incluidas las etapas de Phase 8 exigidas por la CI, sobre el snapshot final. Entre los comandos existentes figuran:

```bash
bash scripts/test.sh
make phase7-check
```

Estos comandos quedan en el bloque de cierre global, no como requisitos inmediatos de cierre de 9A. La aprobación global de Phase 9 requiere V1 resuelto, resultados reales de todas las validaciones aplicables y evidencias reproducibles del estado final; las etapas omitidas, las ejecuciones interrumpidas y los fallos no cuentan como pases.

Una revisión documental, una captura que alcanza HLT o un número de MHz nominal no reemplazan esos controles ni certifican exactitud histórica. En esta actualización solo se ha ajustado el informe; no se han relanzado pruebas ni modificado la CI.

**Conclusión final:** los tres commits son una base aprovechable de observación funcional, no una implementación ni una certificación de tiempos históricos. Las correcciones propuestas se concentran en hacer fiable esa base y sus evidencias, sin reabrir innecesariamente la arquitectura de la CPU ni añadir retardos artificiales. Se mantiene el desarrollo incremental con validación focalizada y se reserva la regresión completa para la finalización de Phase 9, conforme a la decisión de Aitor.
