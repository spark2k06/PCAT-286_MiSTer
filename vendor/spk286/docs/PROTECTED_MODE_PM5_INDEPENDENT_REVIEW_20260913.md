# Revisión independiente de PM5 — 2026-09-13

## Dictamen

**PM5 no queda aprobado ni arquitectónicamente cerrado.** La implementación
revisada supera sus pruebas dirigidas, lint y síntesis, pero esas pruebas
codifican en varios puntos un comportamiento distinto del Intel 80286. Se
retiene por tanto la aprobación de PM5 y no debe usarse este estado como base
cerrada de PM6 hasta corregir los hallazgos P1/P2, repetir la validación y
realizar una nueva revisión independiente.

La revisión no ha modificado RTL, microcódigo ni expectativas. Este documento
registra el resultado contra la instantánea congelada siguiente:

- instantánea PM5 revisada: `f62ec3b6d325a7025a53e39a2d7825e1b72f0a63`;
- base del alcance PM5: `0d4af0b1cd52666d03193ebf4c612310443fc457`;
- rango revisado: 55 archivos, 8727 inserciones y 2478 eliminaciones.

## Fuente normativa y método

La referencia primaria es el *80286 and 80287 Programmer's Reference Manual*
de Intel, edición de 1987, capítulos 8 y 9 y apéndice B. La copia examinada
procede de
[Bitsavers](https://bitsavers.trailing-edge.com/components/intel/80286/210498-005_80286_and_80287_Programmers_Reference_Manual_1987.pdf)
y tiene SHA-256
`AD487BA99B48CD9F61B14C0FE912A04C7CDB4C7C14A18419AA9FAF62D8962460`.

Se contrastaron los requisitos de PM5 con el flujo RTL y de microcódigo, las
expectativas de los bancos, las trazas disponibles y los efectos parciales
documentados por Intel. En particular:

- capítulo 8, sección 8.3 y apéndice B `SWITCH_TASKS`, para el orden y los
  efectos parciales del cambio de tarea;
- tabla 8-2 y la descripción de `IRET`, para BUSY, NT y retorno anidado;
- capítulo 9, secciones 9.5 y 9.6, para código de error, contexto de fallo y
  vectores `#TS`, `#NP` y `#SS`.

## Validación reproducida

| Comprobación | Resultado en la instantánea |
| --- | --- |
| `spk286_task_switch_service`, Icarus + Verilator | PASS, 42 comprobaciones |
| `spk286_protected_task_state_fault`, Icarus + Verilator | PASS, 156 comprobaciones, 36 casos |
| `spk286_protected_task_iret`, Icarus + Verilator | PASS, 10 comprobaciones |
| `spk286_protected_task_gate_event_privilege_outer`, Icarus + Verilator | PASS, 448 comprobaciones, 144 casos |
| consistencia de microcódigo y lint Verilator | PASS, 120 entradas y 717 palabras |
| síntesis de control Yosys | PASS |

Estos resultados prueban que la implementación coincide con sus expectativas
actuales; no resuelven las discrepancias arquitectónicas detalladas abajo. La
regresión completa registrada en `f62ec3b` también estaba verde en Icarus. La
ejecución agregada de Verilator continúa limitada por recursos al compilar
`spk286_protected_expand_down_tb`, aunque los bancos PM5 aquí citados sí pasan
aisladamente en ambos simuladores.

## Hallazgos

### P1 — El cambio de tarea valida demasiado pronto y revierte efectos que el 80286 conserva

`rtl/spk286_task_switch_service.sv:1-7` define expresamente una transacción que
prelee la imagen entrante y valida LDTR, ES, CS, SS, DS e IP antes de permitir
escrituras. El autómata realiza esas comprobaciones en
`rtl/spk286_task_switch_service.sv:408-473` y sólo inicia el servicio que cambia
el TSS en `rtl/spk286_task_switch_service.sv:475`.

Intel especifica otro orden: marca BUSY el TSS entrante, guarda el estado
saliente, carga TR y los registros de la nueva tarea y, ya en el contexto de la
tarea entrante, valida LDTR y los segmentos. Los fallos tardíos dejan efectos
parciales observables; no existe una reversión transaccional general.

Además, `rtl/spk286_tss_service.sv:218-229` guarda antes de marcar BUSY en CALL,
y en JMP libera el TSS saliente antes de marcar BUSY el entrante. Esto tampoco
respeta el orden indicado por `SWITCH_TASKS`.

Los bancos refuerzan la semántica incorrecta: por ejemplo,
`sim/unit/spk286_task_switch_service_tb.sv:196-200` y
`sim/unit/spk286_protected_task_state_fault_tb.sv:243-251` exigen que un fallo
de la imagen entrante preserve TR, el descriptor BUSY y el TSS saliente.

**Impacto:** los fallos se entregan en el contexto de la tarea equivocada y se
pierden escrituras de TSS/descriptores que el procesador real ya habría hecho.

### P1 — IRET con NT no guarda el estado de la tarea que retorna

En `rtl/spk286_tss_service.sv:203-215`, `return_task` salta directamente a
`ST_OLD_FREE`; el estado `ST_SAVE` sólo se recorre para entradas que no son un
retorno. Intel exige que la tarea que ejecuta `IRET` guarde su estado actualizado
antes de volver por el backlink, de modo que una reentrada posterior continúe
después del `IRET`.

`sim/unit/spk286_protected_task_iret_tb.sv:179-186` comprueba la restauración de
la tarea exterior, pero no comprueba que IP, FLAGS, GPR, segmentos y LDTR de la
tarea saliente hayan quedado actualizados en su propio TSS.

**Impacto:** al reentrar en esa tarea se recupera una imagen obsoleta y tampoco
queda persistido correctamente el estado NT saliente.

### P1 — El contrato de fallos de estado de tarea no produce vector, código ni precedencia fiables

Hay varios casos concretos contrarios a las secciones 9.6.3–9.6.5 de Intel:

| Caso | Implementación/expectativa actual | Comportamiento 80286 |
| --- | --- | --- |
| TSS entrante con límite menor que `002Bh` | `rtl/spk286_micro_executor.sv:606-610` lo convierte en fallo genérico de descriptor y `rtl/spk286_micro_executor.sv:844-865` devuelve `#GP`; el banco lo exige en `sim/unit/spk286_protected_task_fault_tb.sv:211-220` | `#TS` con selector del TSS |
| LDT entrante no presente | `rtl/spk286_task_switch_service.sv:442-451` y `sim/unit/spk286_task_switch_service_tb.sv:229-230` devuelven `#NP` | `#TS` con selector LDT |
| SS entrante no presente | `rtl/spk286_task_segment_service.sv:224-226` sólo puede elegir `#TS` o `#NP` | `#SS` con selector SS |
| IP entrante mayor que `CS.limit` | `rtl/spk286_task_switch_service.sv:468-472` devuelve `#TS` con el selector del TSS y el banco lo exige en `sim/unit/spk286_protected_task_state_fault_tb.sv:311-314` | comprobación posterior al cambio y `#GP(0)` |

Además, `rtl/spk286_task_segment_service.sv:176-190` agrega los fallos de cuatro
segmentos; `rtl/spk286_task_segment_service.sv:280-295` restablece el índice a
ES antes de resolver el resultado. Por ello un fallo de CS, SS o DS puede
publicar el selector ES, y cualquier ausencia domina a otros fallos sin respetar
el orden arquitectónico de comprobación.

Finalmente, los códigos se forman a partir de selectores sin metadatos del
origen. `rtl/spk286_micro_executor.sv:866-869` incluso devuelve cero para
fallos de validación de event gate. No se codifican de forma general los bits
EXT/IDT requeridos para atribuir correctamente una excepción originada por un
evento externo o por la IDT.

**Impacto:** software de sistema y manejadores de excepción observan el vector,
el selector causante o los bits de procedencia equivocados.

### P1 — Una excepción entregada mediante task gate pierde su código de error

El microprograma de evento ejecuta `TASK_SWITCH` en
`microcode/source/z_interrupts.mc:61-67` y deja `PUSH_EVENT_ERROR` para
`microcode/source/z_interrupts.mc:81`. Tras completar el cambio por task gate,
`rtl/spk286_micro_executor.sv:1170-1173` activa el salto terminal y
`rtl/spk286_micro_executor.sv:1192-1193,1240-1242` omite toda la cola restante,
incluido ese push.

Intel especifica que, cuando una excepción que lleva código de error se entrega
mediante task gate, el código se apila en la pila de la nueva tarea. El banco
integrado usa `INT 0` sin código de error
(`sim/unit/spk286_protected_task_gate_event_privilege_outer_tb.sv:151-153`) y
no cubre este requisito.

**Impacto:** el manejador de excepción de la nueva tarea recibe una pila
incorrecta.

### P2 — JMP a tarea no fuerza NT a cero

`rtl/spk286_tss_service.sv:160-167` conserva el NT almacenado en el TSS cuando
`nested_call_q` es cero. Para un JMP, la tabla 8-2 de Intel exige limpiar NT en
la tarea entrante. Las pruebas sólo usan una imagen entrante con NT ya limpio.

**Impacto:** un TSS con NT preexistente puede convertir un `IRET` posterior en
un retorno de tarea espurio.

### P2 — La actualización de BUSY no está protegida por LOCK

`rtl/spk286_tss_service.sv:126-153` realiza escrituras de byte separadas sobre
el descriptor BUSY, sin solicitud de bloqueo ni revalidación atómica. En el
tope, `rtl/spk286.sv:546-555` conecta `lock_request` exclusivamente al prefijo
LOCK o al bloqueo implícito de una instrucción de memoria; el servicio de tarea
no participa.

Intel exige bloquear el bus durante la prueba y activación del bit BUSY para
evitar que otro procesador seleccione simultáneamente el mismo TSS. No hay un
banco PM5 que observe `bus_lock` durante este ciclo.

**Impacto:** falta la atomicidad del cambio de tarea en un sistema
multiprocesador o con otro dueño coherente del bus.

## Cobertura confirmada

La revisión sí confirma que la instantánea contiene y ejercita:

- el formato fijo de 22 palabras del TSS 80286 y sus offsets;
- LTR, CALL/JMP directos a TSS, task gates y retorno anidado en casos válidos;
- carga de LDTR no nulo y resolución GDT/LDT;
- matrices amplias de CPL/RPL/DPL y tipos/presencia/límites;
- establecimiento de `MSW.TS`, esperas READY y retención HOLD/HLDA en el
  alcance de un único CPU;
- microcódigo generado consistente, lint limpio y síntesis de control limpia;
- ausencia de campos TSS/paginación propios de 80386 en el alcance revisado.

## Límites de esta revisión

- No se ha aportado una campaña nueva sobre silicio 80286 físico; el dictamen
  se apoya en la documentación primaria de Intel y en la evidencia ejecutable
  del repositorio.
- La limitación de recursos de la ejecución agregada Verilator permanece como
  déficit de evidencia, no como dispensa de un fallo.
- No se evaluó lógica de placa o chipset, fuera del límite CPU-only del
  proyecto.

## Condiciones para una nueva aprobación

1. Reordenar el cambio de tarea para reproducir los efectos parciales del
   80286, incluido el guardado en IRET, sin una reversión global ficticia.
2. Implementar un contrato explícito de fallo con vector, código, selector
   causante, EXT/IDT y orden de comprobación.
3. Apilar el código de error en la nueva tarea para excepciones vía task gate.
4. Corregir NT para JMP y hacer atómica con LOCK la prueba/actualización BUSY.
5. Sustituir las expectativas que hoy validan el comportamiento incorrecto
   por matrices derivadas de Intel, añadir casos adversarios y ejecutar la
   cadena completa de validación.
6. Someter la corrección resultante a una nueva revisión independiente antes
   de declarar PM5 cerrado o continuar el cierre arquitectónico de PM6.
