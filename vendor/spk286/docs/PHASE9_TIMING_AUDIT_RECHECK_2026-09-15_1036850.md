# SPK286 — Segunda revisión del cierre del validador de Phase 9A

**Fecha:** 15 de septiembre de 2026.  
**Rama:** `codex/phase9-timing-tstates`.  
**Commit auditado:** [`1036850a0b4a486d012108739a9bdf5e3c06562b`](https://github.com/spark2k06/SPK286/commit/1036850a0b4a486d012108739a9bdf5e3c06562b), `test: close phase 9A trace validator follow-up`.  
**Base:** `517d5a7402a356ff57213d6553a70bc66f7931e1`.  
**Alcance:** los cuatro archivos de este commit: validador, pruebas y dos documentos. No es una nueva auditoría exhaustiva de la CPU.

Este documento complementa el [seguimiento anterior](PHASE9_TIMING_AUDIT_FOLLOWUP_2026-09-15_a1976ac.md) y la [respuesta de implementación](PHASE9_TIMING_AUDIT_FOLLOWUP_RESOLUTION_2026-09-15.md); conserva sus resultados históricos. La regresión completa continúa reservada para el final de Phase 9, por decisión de Aitor. No se exige adelantarla para corregir este validador.

## 1. Dictamen

**Los ejemplos concretos reproducidos en el seguimiento anterior ya se rechazan. La mejora es real, pero H4 no queda completamente cerrado: persisten dos omisiones de comprobación, demostradas mediante tres trazas sintéticas que el capturador acepta y publica.**

| Elemento | Estado tras esta revisión |
| --- | --- |
| H1–H3 | Se mantiene la aceptación acotada del seguimiento anterior. Este commit no altera el RTL ni el flujo de procedencia y rutas. No se ha repetido toda su verificación. |
| H4: propietario, dirección impar, saltos de contadores y política 0 | Corregidos para los contraejemplos anteriores. Se verificaron rechazos independientes. |
| H4: paridad completa de carriles | Pendiente, P2: sigue aceptándose una dirección par con máscara 2. |
| H4: continuidad de una transacción en espera | Pendiente, P2: una petición puede desaparecer sin READY; los datos de una escritura pueden cambiar durante la espera. |
| V1 | Sigue abierto por `call-stack-precheck`, tal como declara la respuesta de implementación. No es un fallo nuevo introducido por este commit. |
| Regresión completa | Pendiente planificada para el cierre global de Phase 9; no se convierte en requisito inmediato de esta revisión. |

Los problemas residuales afectan a la **admisión de evidencias por el validador**. No se ha demostrado que el RTL genere esas trazas incorrectas ni que este commit produzca una regresión funcional de instrucciones. P2 conserva el significado de defecto relevante que corregir antes de presentar el validador como conforme al contrato revisado.

## 2. Lo que se acepta del commit

El [validador actualizado](https://github.com/spark2k06/SPK286/blob/1036850a0b4a486d012108739a9bdf5e3c06562b/tools/capture_timing_trace.py) incorpora correctamente la correspondencia entre `status` y `owner`, el carril alto para direcciones impares, datos cero en reposo, límites de 64 bits y de ciclos transcurridos, incrementos de cero o uno para los contadores indicados y ausencia de retardo de compatibilidad bajo política 0. Mantiene la convención previa al flanco y no suma métricas que pueden solaparse.

También detecta cambios de dirección, estado, carriles, dirección de transferencia y propietario entre muestras activas de una transacción en espera. Las [pruebas nuevas](https://github.com/spark2k06/SPK286/blob/1036850a0b4a486d012108739a9bdf5e3c06562b/tests/test_capture_timing_trace.py) separan el caso de contador negativo del de discontinuidad y comprueban que una traza rechazada no publique un manifiesto nuevo.

**Las 13 pruebas del repositorio pasaron en esta revisión.** La verificación adicional confirmó que las alteraciones concretas del seguimiento anterior ya son rechazadas. La reserva de cierre se limita a las variantes descritas a continuación, dentro de las mismas reglas de carriles y estabilidad de transacción.

## 3. H4-A — Falta la mitad par de la regla de carriles

**Ubicación:** [`tools/capture_timing_trace.py:180–194`](https://github.com/spark2k06/SPK286/blob/1036850a0b4a486d012108739a9bdf5e3c06562b/tools/capture_timing_trace.py#L180-L194).  
**Referencia:** [`rtl/spk286_timing_trace.sv:88–90`](https://github.com/spark2k06/SPK286/blob/1036850a0b4a486d012108739a9bdf5e3c06562b/rtl/spk286_timing_trace.sv#L88-L90).

La condición añadida rechaza una máscara distinta de 2 cuando la dirección es impar. Sin embargo, para dirección par permite cualquier máscara activa no nula, incluida 2. El observador actual no puede producir esa combinación: con A0=0 solo publica máscara 1 o 3, según `bus_bhe_n`.

Se comprobó la tabla completa de dos paridades por cuatro máscaras:

| Dirección de una muestra activa | Máscaras permitidas por el observador | Resultado del validador |
| --- | --- | --- |
| Par | 1 o 3 | Acepta 1, **2** y 3. |
| Impar | 2 | Acepta únicamente 2; correcto. |

**Reproducción:** partir de una fixture de seis filas aceptada, con una transferencia en espera y su finalización; mantener la dirección `0x0100` y cambiar la máscara a `2` en ambas muestras. No se modifica ningún otro campo respecto a esa fixture. `read_trace()` y `validate_capture_workload()` la aceptan. El `main()` original, ejecutado con Git temporal real y el simulador sustituido, devuelve `0` y publica el manifiesto.

**Corrección necesaria:** completar la tabla de carriles para muestras activas. Mantener la comprobación impar existente y rechazar también máscara 2 con dirección par. En reposo la máscara debe continuar siendo cero.

**Aceptación:** conservar las ocho combinaciones como casos independientes. Deben pasar par/1, par/3 e impar/2; las otras cinco combinaciones activas deben rechazarse. La nueva comprobación no exige cambios de RTL ni temporización histórica.

## 4. H4-B — La estabilidad de READY tiene dos vías sin verificar

**Ubicación:** [`tools/capture_timing_trace.py:226–232`](https://github.com/spark2k06/SPK286/blob/1036850a0b4a486d012108739a9bdf5e3c06562b/tools/capture_timing_trace.py#L226-L232) y `BUS_IDENTITY_COLUMNS`.  
**Referencias:** [contrato normalizado de bus](https://github.com/spark2k06/SPK286/blob/1036850a0b4a486d012108739a9bdf5e3c06562b/docs/BUS_INTERFACE.md#L59-L99) y [RTL de la BIU](https://github.com/spark2k06/SPK286/blob/1036850a0b4a486d012108739a9bdf5e3c06562b/rtl/spk286_biu.sv).

### B1. Una petición puede desaparecer sin haber completado

La comprobación solo se ejecuta cuando la muestra anterior está en fase 1 **y la actual está en fase 1 o 2**. Una transición `1 -> 0` evita el bloque entero. Los contadores de bus pueden seguir siendo aritméticamente coherentes, porque contabilizan correctamente la espera anterior, sin que se detecte que la petición desapareció.

La reproducción contiene esta secuencia, dentro de una época continua y sin reset ni cancelación observada:

| Ciclo | Fase | Actividad | Busy acumulado | Aceptaciones | Esperas READY |
| --- | --- | --- | --- | --- | --- |
| 1 | 1 | Código en `0x0100`, READY=0 | 0 | 0 | 0 |
| 2 | 0 | Reposo; la petición anterior desaparece | 1 | 0 | 1 |
| 3 | 2 | Otra transferencia en `0x0200`, READY=1 | 1 | 0 | 1 |
| 4 | 0 | Reposo tras la segunda transferencia | 2 | 1 | 1 |

El parser, la comprobación del workload y el `main()` la aceptan; se publica manifiesto con retorno 0. No es un resultado de simulación HDL: demuestra que el validador no comprueba esa relación temporal.

El contrato normalizado exige conservar la petición hasta READY. Una cancelación semántica drena la transacción, no autoriza a borrarla sin completar. RESET puede abortarla, pero el esquema actual rechaza filas de reset y exige una época continua; no hay en esta fixture una excepción de reset que justifique la transición.

**Corrección necesaria:** cuando la fila anterior está en fase 1 y hay una siguiente fila de la misma época, exigir primero que continúe activa en fase 1 o 2. Después, comparar su identidad. Una futura representación de reset/abort debe tener una regla y evidencia explícitas, no quedar admitida por omisión.

### B2. Los datos conducidos de una escritura pueden cambiar

`BUS_IDENTITY_COLUMNS` no contiene `data`. En una escritura en espera se puede conservar dirección, estado, carriles, sentido y propietario, pero cambiar los datos antes de READY. El validador también lo acepta.

**Reproducción:** transferencia de escritura en `0x0100`, `status=6`, `owner=2`, `write=1`, máscara 3; datos `0x1234` durante la espera y `0x5678` en la muestra de finalización. Los demás campos de identidad no cambian. El `main()` publica la evidencia con retorno 0.

El contrato y la BIU actual mantienen los datos de escritura registrados durante la espera. **Esto no debe aplicarse indiscriminadamente a lecturas:** `data_in` puede cambiar antes de READY. Se incluyó un control positivo con datos de lectura distintos entre espera y finalización, que pasa correctamente.

**Corrección necesaria:** bajo la misma condición de transacción anterior en espera, verificar `data` cuando `previous["write"] == 1`. No imponer esa estabilidad a datos de lectura ni a señales externas HOLD/READY que pueden cambiar legítimamente.

**Aceptación conjunta de B1/B2:** rechazar espera a reposo sin una excepción representada; rechazar cambios de datos de escritura tanto en `1 -> 1` como en `1 -> 2`; aceptar lecturas cuyo dato cambie antes de la finalización. Las transacciones ya completadas pueden cambiar de identidad en la muestra siguiente. Una captura acotada puede terminar durante una espera: no se exige inventar una fila de finalización más allá del intervalo registrado.

## 5. Verificaciones ejecutadas y límites

Se ejecutaron localmente con **Python 3.13.5**:

| Comprobación | Resultado |
| --- | --- |
| Suite original de `test_capture_timing_trace.py` | **13/13 pasan.** |
| Casos adicionales del contrato del CSV | **66 casos:** 63 coinciden con el contrato; tres aceptaciones incorrectas, descritas arriba. |
| Flujo `main()` con fixture válida | Retorno 0 y manifiesto publicado. |
| Flujo `main()` con datos no nulos en reposo | Rechazo y ausencia de manifiesto nuevo. |
| Flujo `main()` con cada uno de los tres casos pendientes | Los tres devuelven 0 y publican manifiesto. |

Las copias del capturador y de su suite se verificaron contra los blobs Git del commit:

| Archivo | Blob Git verificado |
| --- | --- |
| `tools/capture_timing_trace.py` | `d2f3383d6596015e7b6d33a8dbf2ffb218d149c8` |
| `tests/test_capture_timing_trace.py` | `0be2975eda8450b0acdc4ab689188cd6fd9207e0` |

Las 13 pruebas originales se ejecutaron sin modificar sus aserciones ni el capturador; se proporcionaron archivos de apoyo sintéticos para la parte de huellas del `main()` que ya emplea llamadas simuladas en la propia suite. Los 66 casos adicionales utilizan CSV sintéticos. Las cinco reproducciones independientes de `main()` emplean Git real en repositorios temporales, fuentes auxiliares sintéticas y sustitución únicamente de las llamadas al simulador y su versión. **No son capturas funcionales de MOV/XCHG/HLT.**

Los scripts, fixtures y resultados se conservan en el paquete de evidencias entregado con este informe. El resultado de caracterización no debe presentarse como 66 pases del producto: los tres casos incorrectamente admitidos siguen abiertos.

**No se ejecutaron Verilator, Icarus, Yosys ni regresión completa.** El pase de una captura real de 221 registros aparece declarado en la respuesta de implementación; no se ha reproducido esa captura en esta revisión y no se utiliza como resultado propio.

## 6. V1, CI y cierre recomendado

La respuesta de implementación mantiene V1 abierto por el mutante `call-stack-precheck`. Este commit no modifica los auditores ni los bancos de llamadas lejanas; no se considera que lo haya resuelto ni empeorado. Se conserva el tratamiento acordado para el cierre global de Phase 9.

Se consultó el [run `34948522966`, job `104313622741`](https://github.com/spark2k06/SPK286/actions/runs/34948522966/job/104313622741) asociado al SHA auditado. En la consulta realizada durante esta revisión estaba **en curso**, en la validación heredada de Phase 7, sin conclusión final. Ese estado no es un pase ni un fallo demostrado. No se solicitó manualmente ninguna ejecución de CI ni se relanzaron, cancelaron o modificaron workflows.

**Siguiente ajuste recomendado:** completar H4-A y H4-B en el validador y añadir los casos negativos y controles positivos indicados. No hace falta reabrir H1–H3, modificar el RTL ni adelantar la regresión completa. Tras comprobar esos casos, actualizar el estado de H4 en el documento de resolución sin reescribir los resultados históricos.

**Conclusión:** el commit resuelve los contraejemplos anteriores y refuerza significativamente la evidencia, pero la afirmación de cierre completo de H4 sigue siendo prematura por estas dos omisiones concretas. La revisión pendiente es pequeña y pertenece al contrato ya existente, no a una ampliación de Phase 9 ni a nuevas exigencias de exactitud histórica.
