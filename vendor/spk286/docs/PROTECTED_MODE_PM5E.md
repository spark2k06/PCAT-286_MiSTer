# PM5e — integración de transferencias directas a TSS

> **Estado de revisión (2026-09-13): PM5 no aprobado.** La
> [revisión independiente](PROTECTED_MODE_PM5_INDEPENDENT_REVIEW_20260913.md)
> encontró discrepancias arquitectónicas bloqueantes en el orden y los efectos
> parciales del cambio de tarea, IRET anidado, entrega de fallos/códigos de error,
> NT de JMP y atomicidad BUSY. La descripción que sigue documenta el
> comportamiento implementado en la instantánea revisada; no constituye una
> aprobación de conformidad con el 80286.

PM5e conecta el servicio PM5d con el executor de microcódigo y con el límite
de memoria del BIU. La ruta integrada cubre las formas de puntero lejano
inmediato y por memoria de `CALL` y `JMP` cuando el selector nombra un TSS
80286 disponible.

## Secuencia integrada

1. `VALIDATE_CALL_GATE`/`VALIDATE_CS` resuelve el descriptor TSS y comprueba
   selector GDT, presencia, forma reservada y límite mínimo `002Bh`.
2. `TASK_SWITCH` arranca una única transacción PM5d. Las lecturas de la imagen,
   los descriptores de ES/CS/SS/DS, los guardados TSS y las escrituras de
   backlink/busy pasan por el request de memoria del CPU y respetan `READY`.
3. El executor espera la finalización real del servicio y realiza un commit
   por fases: AX..DI, FLAGS/IP, TR/MSW/LDTR, y las cuatro caches ocultas.
4. El bit `NT` se conserva desde la imagen de FLAGS para una entrada anidada,
   y el bit `TS` se establece al instalar el nuevo TR. La cola se redirige al
   IP y CS cargados por la tarea.

La carga es atómica respecto al estado visible del CPU: un fallo del TSS o de
las caches de segmento no modifica TR, FLAGS, IP, registros ni caches. El
servicio resuelve ahora el LDTR entrante no nulo desde la GDT, valida su forma,
tipo LDT y presencia, y publica su base/límite/acceso como candidato
transaccional antes de validar ES/CS/SS/DS. Los selectores con `TI=1` se
resuelven contra esa caché LDT entrante; un selector inválido produce `#TS` y
uno no presente produce `#NP` sin publicar el cambio de tarea.

## Verificación

`sim/unit/spk286_protected_task_tb.sv` cubre la cadena integrada en ambos
simuladores: LMSW/LGDT, salto protegido, LTR, CALL lejano directo a TSS,
backlink, busy, guardado de IP, carga de registros/FLAGS/NT, commit de CS/IP y
ejecución del handler de la tarea entrante. El banco pasa 20 comprobaciones,
con esperas `READY` deliberadas y una retención `HOLD/HLDA` durante el cambio.

La prueba aislada `spk286_task_switch_service` pasa 42 comprobaciones,
incluyendo la preservación del TSS saliente ante fallo. El lint y la
comprobación Yosys de síntesis también incluyen el nuevo servicio.

## PM5f — entrada mediante task gate

La ruta de eventos protegidos acepta ahora descriptores IDT de tipo task gate.
El selector contenido en el gate se valida como TSS disponible y el mismo
`TASK_SWITCH` transaccional se ejecuta antes de cualquier operación de marco
normal de interrupción. La entrada se etiqueta como llamada anidada, por lo
que el servicio escribe backlink, marca busy y carga NT sin empujar FLAGS/CS/IP
en la pila del contexto interrumpido.

`sim/unit/spk286_protected_task_gate_tb.sv` cubre `LIDT`, `INT 0`, el task gate,
backlink, busy, IP salvado, carga del contexto y ejecución del handler; pasa 9
comprobaciones con Icarus y Verilator.

## PM5g — retorno de tarea anidada mediante IRET

La secuencia `INT`/task gate puede retornar ahora mediante `IRET` cuando
`FLAGS.NT=1`. `TASK_RETURN` resuelve el selector backlink desde el TSS activo,
lee y valida el descriptor TSS ocupado en la GDT, y reutiliza la transacción
atómica de cambio de tarea para liberar el descriptor saliente y restaurar la
tarea anterior. El executor mantiene bloqueado el resto del marco IRET hasta
que termina el commit de la tarea y solo entonces permite retirar la secuencia
microcodificada.

`sim/unit/spk286_protected_task_iret_tb.sv` verifica en ambos simuladores la
entrada por task gate, backlink, `NT`, liberación del descriptor ocupado,
restauración de `CS:IP`, guardado del IP posterior al `INT` y ejecución del
`HLT` de la tarea exterior: 10 comprobaciones, con esperas `READY` deliberadas.

## PM5h — carga transaccional de LDTR no nulo

El cambio de tarea lee el selector `TSS.LDT`, obtiene el descriptor LDT de la
GDT y carga su caché oculta solo después de validar descriptor, forma reservada
y presencia. La validación de los cuatro segmentos del TSS entrante recibe ya
esa caché, de modo que ES/SS/DS con `TI=1` se comprueban contra el LDT recién
cargado. El commit de LDTR se realiza junto al TR y las caches de segmento,
conservando el límite de commit atómico del PM5.

`sim/unit/spk286_protected_task_ldt_tb.sv` cubre en ambos simuladores un TSS
entrante con `LDTR=0030h`, LDT en `006000h` y ES/SS/DS seleccionados desde el
LDT; verifica selector, base, límite, derechos de acceso y ejecución del
handler: 8 comprobaciones. La prueba se ejecuta con `READY` intermitente.

## PM5i — task gates en transferencias lejanas

La validación de `CALL FAR` y `JMP FAR` acepta ahora un descriptor task gate
como primer descriptor. El executor conserva el selector de TSS contenido en
el gate, resuelve el descriptor TSS disponible en una segunda transacción de
descriptor y entrega el candidato al mismo servicio transaccional PM5. `CALL`
marca la entrada como anidada, escribe backlink y carga `NT`; `JMP` libera el
descriptor saliente y no crea backlink ni tarea anidada.

`sim/unit/spk286_protected_task_gate_far_tb.sv` ejecuta ambos caminos con
`READY` intermitente en Verilator e Icarus y comprueba busy, liberación del
descriptor anterior, backlink, `NT`, IP salvado, contexto entrante y llegada
al handler: 14 comprobaciones.

## PM5j — fallos de task gate y cancelación por reset

La validación de task gates rechaza ahora explícitamente el `word0` reservado
no nulo de un descriptor 80286 task gate. La prueba integrada cubre además la
comparación `DPL/RPL`, gates no presentes, TSS objetivo ocupado o no presente,
límite TSS inferior a `002Bh` y la retención de `TR`/busy ante cada rechazo.
También mantiene la operación retenida por `READY`, aplica reset y verifica que
el candidato de cambio de tarea se cancela sin publicar `TR`, `NT` ni busy del
TSS objetivo.

`sim/unit/spk286_protected_task_gate_fault_tb.sv` ejecuta ahora cada fallo de
transferencia lejana con `CALL FAR` y `JMP FAR`, además de la cancelación por
reset bajo `READY`. Pasa 49 comprobaciones en Verilator e Icarus para 13 casos.

## PM5k — autoridad CPL/RPL/DPL en TSS directo

La ruta integrada de `CALL/JMP` directo a un descriptor TSS aplica ahora la
regla de autoridad `DPL >= max(CPL, RPL)` antes de iniciar el servicio de
cambio de tarea. Una violación de esa regla produce `#GP(13)` y conserva el
`TR`, el descriptor TSS objetivo y el estado visible de la tarea actual. La
comprobación no se aplica al TSS nombrado por un task gate: en ese caso la
autoridad de acceso la proporciona el propio gate, como exige el modelo de
protección 80286.

`sim/unit/spk286_protected_task_privilege_tb.sv` cubre las 16 combinaciones
DPL/RPL para CPL0 tanto en `CALL FAR` como en `JMP FAR`, con aceptación de
todos los casos `DPL >= RPL`, rechazo de los restantes, comprobación de `#GP`,
conservación de estado, actualización de busy y, para `JMP`, liberación del
TSS saliente y ausencia de backlink. Recorre 32 casos y pasa 116
comprobaciones en Verilator e Icarus.

## PM5l — matriz integrada de CPL1–CPL3

La misma autoridad se ha comprobado ahora desde los tres niveles no nulos. El
test prepara cada CPL mediante un `IRET` protegido real, con validación de
CS, SS, RPL, DPL, `SP` y cambio de pila, y ejecuta desde allí el `CALL` o
`JMP` directo al TSS. Recorre las 16 combinaciones DPL/RPL para cada CPL y
ambos opcodes: 96 casos y 328 comprobaciones entre aceptaciones, `#GP(13)`,
conservación del `TR`, busy del descriptor objetivo, liberación del TSS
saliente en `JMP` y backlink.

`sim/unit/spk286_protected_task_privilege_outer_tb.sv` pasa 328 comprobaciones
en Verilator e Icarus. Esta cobertura confirma la regla integrada
`DPL >= max(CPL,RPL)` para los cuatro CPL, no sólo el servicio aislado.

## PM5m — autoridad DPL/RPL del task gate

La ruta de `CALL FAR` y `JMP FAR` mediante task gate queda cubierta para las 16
combinaciones DPL/RPL del gate desde CPL0. Los casos autorizados entran en un
TSS destino DPL0, demostrando que el gate proporciona la autoridad de acceso y
que no se aplica indebidamente el DPL del TSS destino. `CALL` conserva ocupado
el TSS saliente, escribe backlink y carga `NT`; `JMP` lo libera y no escribe
backlink. Los casos rechazados producen `#GP(13)` antes de modificar `TR` o el
descriptor destino.

`sim/unit/spk286_protected_task_gate_privilege_tb.sv` pasa 116 comprobaciones
en Verilator e Icarus para los 32 casos CALL/JMP.

## PM5n — matriz de task gates CPL1–CPL3

La autoridad de `CALL FAR` y `JMP FAR` mediante task gate se ha verificado
también desde CPL1, CPL2 y CPL3. Cada caso entra primero al nivel solicitado
mediante un `IRET` protegido real y después recorre las 16 combinaciones DPL/RPL
del gate. Los 96 casos comprueban aceptación, `#GP(13)`, conservación de `TR`,
busy del TSS DPL0 nombrado por el gate, la política `NT` de CALL/JMP y la
liberación del descriptor saliente en JMP.

`sim/unit/spk286_protected_task_gate_privilege_outer_tb.sv` pasa 232
comprobaciones en Verilator e Icarus.

## PM5o — matriz de task gates por evento en CPL1–CPL3

La ruta de entrada por `INT` software mediante task gate queda cubierta ahora
desde CPL1, CPL2 y CPL3. Cada nivel recorre los cuatro DPL posibles del gate
y los cuatro RPL posibles del selector TSS, para 48 casos y 144
comprobaciones. La autorización depende del DPL del gate frente al CPL
origen; el DPL/RPL del TSS nombrado no se reaplica como si fuera una
transferencia directa. Los casos válidos publican el TR, CS, IP, FLAGS y NT
del TSS entrante; los rechazados producen `#GP(13)` sin publicar busy ni
modificar el TR actual.

La entrada por task gate de IDT termina además en el commit del task switch y
no ejecuta el tail de marco de una interrupción ordinaria, evitando que ese
camino sobrescriba el CS/IP cargado por el TSS.

`sim/unit/spk286_protected_task_gate_event_privilege_outer_tb.sv` pasa 324
comprobaciones en Verilator e Icarus: además de las 48 combinaciones de
autoridad, recorre desde cada CPL1–CPL3 y RPL0–RPL3 los cinco rechazos del TSS
objetivo (no presente, busy, tipo incorrecto, límite corto y forma reservada).

## PM5ad — matriz de task gates por evento completa

La matriz de entrada por `INT` software se ha cerrado también para CPL0. El
escenario entra explícitamente en el código protegido de nivel 0 y recorre las
16 combinaciones DPL/RPL del gate, manteniendo la regla `DPL >= CPL` y sin
reaplicar la autoridad del TSS destino. La misma extensión ejecuta desde CPL0
los cinco rechazos del descriptor TSS objetivo, con conservación transaccional
de `TR`, busy y `NT`.

El conjunto completo cubre ahora CPL0–CPL3, 64 combinaciones de autoridad y 80
combinaciones de fallos del TSS destino: 144 casos y 448 comprobaciones en
Icarus y Verilator.

`sim/unit/spk286_protected_task_gate_event_privilege_outer_tb.sv` mantiene la
comprobación de que la entrada por task gate de IDT termina en el commit del
task switch y no ejecuta el tail de marco de una interrupción ordinaria.

## PM5p — matriz de fallos de TSS directo

`spk286_protected_task_fault_tb` cubre el rechazo de `CALL/JMP` lejano directo
ante TSS no presente, ocupado, descriptor no-TSS, límite insuficiente, forma
reservada, selector fuera del límite de la GDT y selector cualificado por LDT.
Cada uno de los ocho fallos se ejecuta con ambos opcodes. La matriz comprueba
los vectores #NP/#GP y que `TR`, busy, backlink y la imagen TSS saliente
permanecen sin cambios cuando falla la validación del descriptor.

`sim/unit/spk286_protected_task_fault_tb.sv` pasa 64 comprobaciones en Icarus
y Verilator para los 16 casos CALL/JMP.

## PM5q — validación del estado entrante

La ruta integrada valida ahora también que el `IP` del TSS entrante esté dentro
del límite del CS ya validado, antes de iniciar cualquier escritura del cambio
de tarea. La validación de las cuatro caches rechaza además cualquier
descriptor no presente antes del commit y conserva la distinción #TS/#NP para
selectores inválidos y descriptores no presentes.

`spk286_protected_task_state_fault_tb` pasa 156 comprobaciones en 36 casos
CALL/JMP con Verilator e Icarus: imágenes válidas para CPL0–CPL3, ES/DS nulos,
código legible usado como dato, tipos incompatibles, presencia, límite de GDT,
formas reservadas, selectores LDT sin LDTR y combinaciones RPL/DPL inválidas.
Todos los rechazos comprueban la ausencia de guardado, busy, backlink o
publicación parcial del cambio; los casos válidos comprueban además la
diferencia busy/backlink entre CALL y JMP.

## PM5r — retención HOLD/HLDA durante el cambio

La prueba integrada de TSS mantiene `HOLD` después de iniciar el servicio de
cambio de tarea y espera la concesión `HLDA` en un límite legal del bus. Durante
la retención no se publica `TR`, `NT` ni el busy del TSS destino; al liberar
`HOLD`, la transacción continúa hasta el commit normal.

## PM5s — fallos del TSS objetivo en eventos desde CPL1–CPL3

La matriz de task gates por evento amplía ahora la cobertura de autoridad con
fallos del descriptor TSS destino. Para cada CPL no nulo y cada RPL del
selector, un gate DPL3 prueba TSS no presente, busy, descriptor no-TSS, límite
inferior a `002Bh` y forma reservada. Los rechazos producen #NP/#GP sin
publicar `TR`, `NT` ni busy, y no se inicia el servicio de cambio de tarea.

## PM5t — matriz de caches de segmento del TSS entrante

La matriz del estado entrante cubre ahora los cuatro CPL arquitectónicos para
CS/SS coherentes con sus DPL/RPL, además de los tipos de descriptor y límites
que pueden aparecer en ES, CS, SS y DS. El servicio conserva la atomicidad y
clasifica los fallos de tabla o tipo como #TS y los de presencia como #NP antes
de cualquier escritura del TSS saliente o del descriptor destino.

## PM5u — matriz del selector LDTR entrante

La validación del `TSS.LDT` queda cubierta ahora de forma independiente en el
servicio de cambio de tarea. La matriz acepta el selector nulo, un descriptor
LDT presente y el descriptor situado exactamente en el último límite válido de
la GDTR. También recorre el selector fuera de límite, `TI=1`, todas las clases
de descriptor no-LDT soportadas por el parser (datos, TSS disponible/ocupado,
call gate, task gate, interrupt gate y trap gate), ausencia de `P` y forma
reservada. Los casos inválidos conservan el vector #TS/#NP y no escriben el
TSS saliente ni el byte busy del destino.

`sim/unit/spk286_task_switch_service_tb.sv` pasa 42 comprobaciones en Icarus y
Verilator, incluyendo la carga de base, límite, clase y presencia de la caché
LDTR para los casos válidos y la atomicidad de los once rechazos.

## PM5v — estado MSW.TS en las rutas de cambio de tarea

La evidencia integrada comprueba ahora el bit `TS` del MSW después de un
`CALL` directo a TSS, una entrada por task gate y el retorno anidado mediante
`IRET`. En los tres recorridos `PE` permanece activo y el cambio de tarea no
publica el nuevo contexto hasta el commit transaccional. El retorno por `IRET`
reafirma `TS`, como una nueva instalación de `TR`, en lugar de heredarlo de
forma accidental del contexto restaurado.

Las pruebas pasan 20 comprobaciones para la transferencia directa, 9 para el
task gate y 10 para `IRET`, en Icarus y Verilator.

## PM5w — matriz directa CALL/JMP completa en CPL0

La matriz de autoridad directa se ha extendido para ejecutar las 16
combinaciones DPL/RPL con ambos opcodes de transferencia lejana a TSS. La
variante `CALL` conserva ocupado el TSS saliente y escribe el backlink; la
variante `JMP` libera el descriptor saliente y no escribe backlink. En ambos
casos los rechazos por autoridad se producen antes del servicio transaccional
y conservan el contexto, el descriptor objetivo y el enlace.

`sim/unit/spk286_protected_task_privilege_tb.sv` pasa 116 comprobaciones en
Icarus y Verilator para los 32 casos CALL/JMP.

## PM5x — matriz directa CALL/JMP en CPL1–CPL3

La matriz directa se ha completado también para los niveles no nulos. El mismo
conjunto de 48 combinaciones DPL/RPL se ejecuta como `CALL FAR` y como `JMP
FAR` después de entrar realmente en CPL1, CPL2 y CPL3 mediante `IRET`. Los
casos válidos comprueban busy del TSS destino; `CALL` conserva ocupado el TSS
saliente y escribe backlink, mientras `JMP` lo libera y no escribe backlink.
Los casos no autorizados fallan con `#GP(13)` antes de cualquier escritura.

`sim/unit/spk286_protected_task_privilege_outer_tb.sv` pasa 328 comprobaciones
en Icarus y Verilator para los 96 casos CALL/JMP.

## PM5z — estado entrante simétrico para CALL/JMP

La matriz de validación del estado entrante se ejecuta ahora por igual para
`CALL FAR` y `JMP FAR`. Los casos válidos cubren los cuatro CPL y la carga de
las cuatro cachés de segmento; los casos inválidos recorren límites, tipos,
presencia, RPL/DPL y selectores LDT sin LDTR. Cada rechazo queda verificado
antes del guardado del TSS saliente y de cualquier cambio de busy o backlink.

`sim/unit/spk286_protected_task_state_fault_tb.sv` pasa 156 comprobaciones en
Icarus y Verilator para los 36 casos CALL/JMP.

## PM5aa — autoridad CPL0 de task gates simétrica

La matriz de autoridad de task gates desde CPL0 cubre ahora ambos opcodes de
transferencia lejana. Los 16 pares DPL/RPL se ejecutan como `CALL FAR` y `JMP
FAR`; el gate sigue siendo la única fuente de autoridad y el TSS destino DPL0
se acepta en todos los casos autorizados. La prueba también verifica `NT`,
backlink, busy y la liberación del TSS saliente según el opcode.

`sim/unit/spk286_protected_task_gate_privilege_tb.sv` pasa 116 comprobaciones
en Icarus y Verilator para 32 casos CALL/JMP.

## PM5y — fallos de descriptor directo completos para CALL/JMP

La matriz de fallos de transferencia directa cubre de forma simétrica `CALL
FAR` y `JMP FAR`: TSS no presente u ocupado, clase no-TSS, límite inferior,
forma reservada, selector fuera de GDTR y selector con `TI=1`. Los ocho tipos
de rechazo se ejecutan con ambos opcodes y se verifica que el fallo ocurre
antes de cualquier guardado, modificación de busy o backlink.

`sim/unit/spk286_protected_task_fault_tb.sv` pasa 64 comprobaciones en Icarus
y Verilator para los 16 casos.

## PM5ab — fallos de task gate simétricos para CALL/JMP

Los fallos de transferencia lejana mediante task gate se ejecutan ahora con
ambos opcodes: autoridad DPL/RPL insuficiente, gate no presente, forma
reservada, TSS ocupado, TSS destino no presente y límite TSS insuficiente.
Además de `TR`, busy y la imagen saliente, cada rechazo comprueba que el
backlink no se escribe; la cancelación por reset bajo `READY` permanece
cubierta.

`sim/unit/spk286_protected_task_gate_fault_tb.sv` pasa 49 comprobaciones en
Icarus y Verilator para 13 casos CALL/JMP y reset.

## PM5ac — disposición fija del TSS 80286

La prueba independiente del servicio TSS comprueba contra la tabla de estado
de tarea del Intel 80286 Programmer's Reference Manual 210498-005, sección
8.1, figura 8-1, los 22 words del TSS y todos sus offsets: backlink, SPn/SSn,
IP, FLAGS, AX..DI, ES/CS/SS/DS y LDT. También comprueba el límite mínimo `2Bh`
como último byte de la imagen fija de `2Ch` bytes. Estas aserciones mantienen
los literales de referencia separados de la generación de direcciones del
servicio para evitar una validación circular. La misma prueba conserva además
la comprobación funcional de guardado, carga, backlink, busy y rechazo de un
TSS corto.

`sim/unit/spk286_tss_service_tb.sv` pasa 38 comprobaciones en Icarus y
Verilator.

## PM5af — LTR y validación del TSS fijo

La ruta de `LTR` comprueba ahora explícitamente el límite mínimo `002Bh` de
la imagen fija 80286 antes de publicar TR o escribir el bit busy. La prueba de
nivel CPU cubre dos cargas consecutivas de TSS disponible, preservación del
busy anterior, TSS ocupado, TSS no presente, descriptor no-TSS, límite corto,
selector LDT y selector nulo. Los fallos se entregan por la puerta protegida
correspondiente y no dejan cambios parciales en TR ni en el descriptor.

`sim/unit/spk286_protected_ltr_tb.sv` pasa 23 comprobaciones en Icarus y
Verilator.

## PM5ae — metadata funcional de transacciones protegidas

El puerto de depuración `debug_bus_transaction` identifica la actividad lógica
protegida asociada a cada petición normalizada del BIU: `1` descriptor, `2`
TSS, `3` gate, `4` frame/stack y `5` fetch de instrucción protegida. El valor
se mantiene mientras la petición espera `READY` y no sustituye a `bus_status`
ni introduce una afirmación de timing histórico.

`sim/unit/spk286_protected_task_tb.sv` verifica en ambos simuladores que el
cambio directo expone transacciones de descriptor, TSS y fetch protegido;
`sim/unit/spk286_protected_task_gate_tb.sv` verifica que la entrada por task
gate expone las transacciones de gate y TSS. La categoría frame/stack comparte
el calificador funcional de las operaciones de pila; `spk286_protected_system`
la verifica en ambos simuladores junto con las trazas de llamadas, eventos y
retornos protegidos.

## Alcance que permanece abierto

- la suite completa de bancos unitarios Icarus termina con todos los resultados
  registrados en `PASS`, incluyendo `EVENT_LIFECYCLE` (468 escenarios y 48927
  comprobaciones) después de ajustar su observación a la nueva posición del
  micro-op `TASK_RETURN`;
- la validación agregada Verilator sigue abierta: la compilación de
  `spk286_protected_expand_down_tb` no alcanza el ejecutable en el entorno
  disponible por consumo extremo de memoria/tiempo. Las matrices PM5 dirigidas
  sí pasan en Icarus y Verilator de forma aislada;
- revisión independiente completada el 2026-09-13, con aprobación retenida y
  hallazgos bloqueantes registrados en
  `docs/PROTECTED_MODE_PM5_INDEPENDENT_REVIEW_20260913.md`;
- evidencia física adicional y cierre PM6.

Las matrices dirigidas de PM5 quedan cubiertas para la disposición fija del
TSS, la autoridad CPL0–CPL3
de las rutas directas y task gates por `CALL FAR`/`JMP FAR`, task-gate por
eventos y transferencias lejanas, fallos simétricos de descriptor, IRET
anidado y carga de LDTR no nulo con su matriz de descriptor, validación del
estado entrante, retención `HOLD/HLDA` en su alcance acotado y el estado
`MSW.TS` de las rutas principales, y deja explícitamente abiertas las
correcciones exigidas por la revisión independiente, su revalidación y nueva
revisión, la evidencia física adicional y el cierre de PM6.
