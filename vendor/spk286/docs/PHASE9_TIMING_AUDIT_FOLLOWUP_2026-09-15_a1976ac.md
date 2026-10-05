# SPK286 — Revisión de las correcciones de la auditoría de Phase 9A

**Fecha:** 15 de septiembre de 2026.  
**Rama:** `codex/phase9-timing-tstates`.  
**Commit revisado:** [`a1976acb3794421dc0d5631dfe436064a0bfb7bb`](https://github.com/spark2k06/SPK286/commit/a1976acb3794421dc0d5631dfe436064a0bfb7bb), `fix: resolve phase 9A timing audit findings`.  
**Padre del commit:** `e162efb3921595df76362732bdfba6de7eb42f74`.  
**Alcance:** las correcciones del commit —14 archivos— y su contraste con H1–H4, V1 y los criterios de validación acordados. No es una auditoría exhaustiva de toda la CPU.

Este seguimiento complementa la [auditoría histórica](PHASE9_TIMING_AUDIT_2026-09-15_151b9c7.md) y la [respuesta de implementación](PHASE9_TIMING_AUDIT_RESOLUTION_2026-09-15.md). No sustituye ni reescribe sus resultados históricos. El snapshot evaluado es el indicado arriba, no el commit posterior que añade este documento.

**Se mantiene la decisión de Aitor: la regresión completa se realizará al finalizar Phase 9.** No se exige adelantarla para avanzar entre subfases ni se contabiliza su aplazamiento como un defecto nuevo.

## 1. Dictamen

**La corrección es sustancial y va en la dirección adecuada. H1, H2 y H3 se consideran corregidos dentro del alcance verificado. H4 queda parcialmente resuelto: todavía pueden publicarse como válidas trazas incompatibles con las propias reglas del observador. V1 sigue parcialmente abierto, como reconoce la respuesta de implementación.**

| Hallazgo | Estado tras la revisión | Evidencia y límite |
| --- | --- | --- |
| H1 — espera de operandos | Corregido en el código revisado | La señal procede del servicio efectivo de operandos. Se inspeccionaron la conexión y las aserciones añadidas; no se reprodujo localmente la simulación HDL. |
| H2 — salida externa | Corregido y reproducido en Python | El flujo del capturador publica el manifiesto con una carpeta absoluta externa; también se comprobaron rutas internas absolutas y relativas. |
| H3 — procedencia | Corregido para el defecto original | El capturador rechaza un árbol modificado antes de compilar, cambios de RTL durante la captura y cambios de HEAD. Se inspeccionó además el hash de entradas antes/después. |
| H4 — validación del CSV | Parcial; permanece P2 | Los casos originales de formato y contadores negativos se rechazan, pero faltan invariantes entre campos y límites de incremento de varios contadores. |
| V1 — validación heredada | Anclas originales corregidas; cierre global pendiente | La CI confirma que el test de anclas pasa. La auditoría de mutación de llamadas lejanas sigue pendiente por `call-stack-precheck`, según la respuesta de implementación. |

No se ha demostrado una regresión funcional de instrucciones causada por este commit. El defecto residual H4 afecta a la fiabilidad de la herramienta que admite las evidencias, no demuestra que el RTL esté generando las trazas artificialmente alteradas usadas en esta revisión.

## 2. Correcciones aceptadas

### H1 — La espera ya pertenece al servicio que la conoce

La [modificación de RTL](https://github.com/spark2k06/SPK286/commit/a1976acb3794421dc0d5631dfe436064a0bfb7bb) sustituye la inferencia desde `operand_register_direct` y la disponibilidad global de la BIU por `operand_service_wait`, conectada a la nueva salida `spk286_operand.timing_wait`.

```systemverilog
assign timing_wait = allowed && is_memory &&
                     ((!pending_q && !request_check && within_limit && !memory_request_ready) ||
                      (pending_q && !memory_response_valid));
```

La condición utiliza la selección efectiva REG/RM, la solicitud pendiente y la disponibilidad de respuesta. Evita contar como espera un acceso local a registro; excluye la admisión ya disponible, las comprobaciones previas sin transferencia, los límites inválidos antes de admisión, la cancelación y la respuesta disponible para aceptación. No introduce realimentación hacia el camino funcional.

Los cambios en [el banco de servicio](https://github.com/spark2k06/SPK286/blob/a1976acb3794421dc0d5631dfe436064a0bfb7bb/sim/unit/spk286_operand_service_tb.sv) y en el banco de bytes añaden comprobaciones explícitas de espera durante admisión/respuesta y ausencia de espera en acceso local/finalización. Esto resuelve la causa identificada en H1 por revisión estática.

Como refuerzo no bloqueante, conviene añadir `!timing_wait` explícito a las aserciones existentes de cancelación, límites inválidos y prechecks. Esas rutas ya tienen pruebas funcionales, pero no todas verifican directamente la nueva salida de observación.

### H2 — Rutas relativas al manifiesto

El [capturador](https://github.com/spark2k06/SPK286/blob/a1976acb3794421dc0d5631dfe436064a0bfb7bb/tools/capture_timing_trace.py#L65-L74) utiliza una ruta relativa al directorio del manifiesto y declara `path_base = manifest_directory`. La ruta relativa al repositorio es opcional y queda a `null` cuando la salida es externa.

Se ejecutó el `main()` original con Git real en un repositorio temporal y con la simulación sustituida por un generador de CSV sintético. Se publicaron manifiestos correctamente con salida externa absoluta e interna absoluta/relativa. La excepción tardía de H2 ya no aparece en esos casos.

### H3 — Rechazo del árbol modificado y huella de entradas

El [flujo de procedencia](https://github.com/spark2k06/SPK286/blob/a1976acb3794421dc0d5631dfe436064a0bfb7bb/tools/capture_timing_trace.py#L76-L105) incorpora las fuentes RTL, paquetes, ROM generada y archivos de apoyo de la captura. El `main()` exige limpieza inicial, guarda HEAD y hashes antes de compilar, y comprueba árbol, HEAD y hashes después de la simulación y antes de publicar el manifiesto.

Las reproducciones independientes confirmaron el rechazo de: un RTL seguido por Git modificado antes de comenzar; un RTL modificado durante la llamada al simulador; y un nuevo commit durante esa llamada. En el primer caso no se lanzó siquiera la llamada sustituida al simulador. En los tres casos no se publicó un manifiesto nuevo en la carpeta de prueba.

La aceptación se refiere al defecto original de atribuir silenciosamente un árbol modificado al HEAD anterior. No constituye una certificación de resistencia a modificaciones transitorias adversarias ni una prueba de reproducibilidad de toda la toolchain.

## 3. H4 residual — Aún se admite evidencia semánticamente imposible

**Prioridad:** P2.  
**Ubicación:** [`tools/capture_timing_trace.py:159–190`](https://github.com/spark2k06/SPK286/blob/a1976acb3794421dc0d5631dfe436064a0bfb7bb/tools/capture_timing_trace.py#L159-L190).  
**Contrato de referencia:** las asignaciones y actualizaciones de [`rtl/spk286_timing_trace.sv`](https://github.com/spark2k06/SPK286/blob/a1976acb3794421dc0d5631dfe436064a0bfb7bb/rtl/spk286_timing_trace.sv#L73-L140), no un modelo de temporización histórica externo.

### Qué ya está resuelto

El validador exige las 32 columnas ordenadas, convierte los campos a enteros, comprueba los rangos definidos, rechaza valores desconocidos y verifica continuidad de ciclos. También comprueba la suma de ciclos ocupados y los incrementos exactos de los tres contadores de bus utilizando correctamente la muestra previa al flanco. Las expectativas específicas de la carga de prueba están separadas de las reglas generales del formato.

Se verificó el rechazo de cabeceras incompletas o duplicadas, `x` como valor, ciclos no contiguos, cola con ocupación 7, READY incompatible con la fase, contadores decrecientes y carga que no llega a HLT.

### Qué sigue escapándose

Las comprobaciones de dominio no aseguran la correspondencia entre campos. Para los contadores distintos de los tres de bus se exige monotonía, pero no se limita el incremento por ciclo ni se comprueba el valor constante del retardo de compatibilidad de la política 0.

Se introdujo cada alteración siguiente en una fixture de seis filas con formato válido. Todas fueron aceptadas por `read_trace()` y `validate_capture_workload()`:

| Alteración aceptada | Por qué contradice el RTL actual |
| --- | --- |
| Transferencia activa con `status = 13` y `owner = 3` | El observador asigna propietario 1 a código (`status = 13`); el 3 corresponde a INTA (`status = 0`). |
| Dirección impar `257` con `lane_mask = 1` | La asignación del observador exige carril alto, máscara 2, para dirección impar. |
| `operand_wait_cycles` pasa de 0 a 1000 entre muestras consecutivas | El contador aumenta como máximo una unidad en cada flanco. |
| `compatibility_delay_cycles = 1` con política 0 | En la baseline actual ese contador permanece en cero. |

Además, el validador aceptó cambiar dirección, propietario y tipo de operación entre una muestra de espera READY y la de finalización. Conviene verificar también la estabilidad de la identidad de transacción bajo el contrato normalizado, con las excepciones de reset/cancelación que realmente correspondan; no inferirlas sin documentarlas.

Una reproducción adicional ejecutó el `main()` completo sobre Git temporal limpio, sustituyendo únicamente la llamada al simulador y su consulta de versión. El CSV entregado contenía propietario/carril incompatibles y el salto del contador a 1000. **El programa devolvió 0, escribió el manifiesto y emitió `TIMING CAPTURE MANIFEST PASS`.** No se sustituyeron el parser, el validador ni las comprobaciones de Git/hashes.

Estas pruebas caracterizan una debilidad de admisión del archivo. **No son capturas HDL reales, no demuestran un fallo de la CPU y no implican que se ignore un error devuelto por el simulador.**

### Revisión necesaria para cerrar H4

Completar las reglas derivadas del observador: correspondencia exacta entre `status` y `owner`, carriles compatibles con la paridad de dirección, datos cero en reposo, ancho de 64 bits de los contadores y del ciclo, e incrementos de 0 o 1 para los contadores de eventos/esperas que así se actualizan. En una época acotada sin reset ni desbordamiento, ningún contador acumulativo de este observador puede superar `cpu_cycles`. La política 0 debe mantener a cero el retardo de compatibilidad.

Mantener las reglas ya implementadas y el desfase correcto entre muestra y actualización. No forzar relaciones de suma entre métricas solapadas ni tratar la ocupación vacía de la cola como starvation.

**Criterio de aceptación:** cada alteración de la tabla se rechaza por separado con un diagnóstico útil; una traza válida sigue pasando. Verificar también que `main()` no publica un manifiesto nuevo cuando recibe una traza rechazada. Para proteger cada regla, evitar pruebas que mezclen varias corrupciones y fallen siempre por la primera.

El test existente `test_rejects_negative_and_non_contiguous_counters` combina dos defectos y comprueba únicamente el error de valor negativo. Se confirmó por separado que la continuidad sí se valida, pero conviene conservar ese caso independiente dentro de la suite del proyecto.

## 4. V1 y estado real de GitHub Actions

### Las anclas originales ya no son el fallo actual

Los auditores de [eventos](https://github.com/spark2k06/SPK286/blob/a1976acb3794421dc0d5631dfe436064a0bfb7bb/tools/audit_events.py), [datos](https://github.com/spark2k06/SPK286/blob/a1976acb3794421dc0d5631dfe436064a0bfb7bb/tools/audit_data.py) y [llamadas lejanas](https://github.com/spark2k06/SPK286/blob/a1976acb3794421dc0d5631dfe436064a0bfb7bb/tools/audit_far.py) actualizan las tres expresiones afectadas y ordenan primero los paquetes. Conservan la exigencia de ancla única y de rechazo por una aserción funcional, sin considerar suficiente un error de compilación.

En los logs del [run `34945693486`, job `104304425142`](https://github.com/spark2k06/SPK286/actions/runs/34945693486/job/104304425142) del commit revisado consta:

- Pase de `test_each_fault_can_be_injected_once_into_current_rtl`.
- Pase de las cuatro pruebas Python nuevas del capturador, dentro de una ejecución de 265 pruebas Python con resultado `OK`.
- `LINT PASS` y pases de los bancos que llegaron a ejecutarse, incluidos registros, segmentos y varias pruebas protegidas.

La ejecución terminó a las **08:19:26 UTC del 15 de septiembre de 2026** con salida **143** y un mensaje de señal de apagado del runner. GitHub marca el job como `failure`; las etapas posteriores quedaron omitidas. **Los logs consultados no muestran que esta terminación se deba a las anclas originales ni a una aserción funcional fallida.** No se ha determinado quién o qué originó el apagado. Tampoco se considera una regresión completa aprobada.

### Lo que sigue pendiente de V1

La respuesta de implementación declara pases focalizados de las auditorías de eventos y datos, pero mantiene abierto el mutante `call-stack-precheck` de la auditoría de llamadas lejanas: el banco actual no lo rechaza. Esta limitación es explícita en el propio commit; no se ha reproducido localmente su simulación en esta revisión y no debe confundirse con la causa de terminación del job de CI anterior.

Antes de cerrar V1 debe determinarse si ese mutante evidencia una carencia de cobertura o resulta equivalente por otras protecciones del RTL actual. Si falta cobertura, añadir el caso discriminante; si es equivalente, documentar la equivalencia y sustituirlo por un defecto semántico efectivo. No eliminarlo silenciosamente ni rebajar los criterios de rechazo.

El cierre global sigue reservado para el final de Phase 9. La incidencia heredada debe permanecer visible, pero no obliga a relanzar ahora toda la cadena global para continuar el trabajo de instrumentación.

## 5. Evidencia ejecutada y límites de esta revisión

Se ejecutaron localmente **las cuatro pruebas existentes del capturador** y **21 comprobaciones adicionales de caracterización** con Python 3.13.5. Las copias de los dos archivos se verificaron mediante su hash de blob Git:

| Archivo | Blob Git verificado |
| --- | --- |
| `tools/capture_timing_trace.py` | `74e998c546d06aa84e4942e8ae71ef4ae1cdcffb` |
| `tests/test_capture_timing_trace.py` | `9fd9d3e37e76902b59aa319a33393fbd06a8fb1a` |

Las cuatro pruebas existentes pasaron. Las 21 adicionales reprodujeron el comportamiento esperado por la revisión; **seis de ellas confirman que el código actual acepta evidencia inválida**, por lo que su resultado `OK` no significa que H4 esté corregido. Las demás comprueban casos admitidos, rechazos y los flujos de rutas/procedencia descritos.

Las pruebas del `main()` utilizan repositorios Git temporales reales y archivos de entrada sintéticos. Sustituyen la ejecución/versionado del simulador para probar el programa Python, no para certificar el comportamiento del programa MOV/XCHG/HLT. Se conservan el harness, los logs y los resultados de fixtures como evidencias complementarias entregadas con este seguimiento; no se incorporan al RTL ni a las expectativas de la suite del proyecto.

**No se ejecutaron localmente Verilator, Icarus, Yosys ni la regresión completa.** Los pases HDL y de síntesis declarados por el autor se distinguen de los resultados consultados en CI y de las comprobaciones Python realizadas aquí.

## 6. Siguiente paso recomendado

La corrección pendiente inmediata es **completar H4 y añadir las pruebas negativas independientes**. No hace falta reabrir H1–H3 ni introducir cambios en la temporización funcional para ello. Después, ejecutar los controles focalizados del capturador y conservar las capturas de ambos simuladores en directorios separados.

Las mejoras documentales del commit —matriz de dependencias, muestreo previo al flanco y métricas solapadas— son adecuadas. El timestamp de aserción externa INTR/NMI y las épocas de reset intermedio permanecen explícitamente pendientes: no se exige resolverlos en este ajuste del validador ni se presentan como funciones ya implementadas.

**Conclusión:** se aceptan las correcciones verificadas de H1–H3; H4 requiere una revisión adicional acotada antes de declarar íntegramente resueltos los hallazgos de 9A. V1 se mantiene abierto para su resolución y aprobación global conforme al calendario acordado. Este dictamen no exige adelantar la regresión completa del final de Phase 9.
