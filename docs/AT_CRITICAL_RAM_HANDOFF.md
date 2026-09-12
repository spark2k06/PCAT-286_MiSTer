# AT: captura del primer fallo de RAM — 12 de septiembre de 2026

> Entrega histórica de instrumentación (`c581864`). Las capturas ya recibidas
> permitieron reproducir el fallo FF00 y corregir las máscaras de placa A12/A11.
> Ver [AT_SDRAM_DQM_HANDOFF.md](AT_SDRAM_DQM_HANDOFF.md) para el estado actual y
> la prueba siguiente. El modelo descrito aquí aún omitía ese cableado de DQM.

## Estado comprobado

El AT ya arranca y el usuario confirma PASS en Timer0/1/2, DMA1/2, registros
de página, paridad y SYSTEM BIOS. Sigue fallando **16K CRITICAL MEMORY REGION**.
First Fault contiene cuatro palabras cero: no se disparó ninguno de sus
indicadores de protocolo/CPU. Eso no certifica el dato leído ni las flags.

La aclaración final del usuario y sus capturas confirman que **XT con SPK286 y
la misma BIOS sí pasa 16K**. Lo que falla allí es MEMORY REFRESH, la prueba
siguiente. El AT no llega a esa prueba mientras falle 16K. XT sólo se usa como
referencia; no se desarrollan prestaciones ni correcciones para ese perfil.

La BIOS evalúa AX en F000:8E08 y, si hay error, toma 8E0F -> 9B68 con SP=8325.
El camino de éxito usa SP=8329 y continúa en 8E18, donde imprime el encabezado
de MEMORY REFRESH. Por tanto, repetir el diagnóstico no es un nuevo fallo de
reset ni el antiguo bucle de fetch F000:FFFx.

El usuario probó también la ROM **original sin parche** en el mismo AT: ambos
checksums pasan y 16K sigue fallando. El parche no es una condición necesaria
para este fallo. `rom-patch-audit.json` verifica ocho bytes distintos en total:
94D8..94DA cambia a JMP 971A, B0EB ajusta el checksum y se repiten los cambios en
la copia inferior. Ni el código de preparación ni 9F14..9FAF cambian.

El bloque original omitido carga GDT/IDT y activa PE mediante LMSW en 94F6;
no equivale sólo a una prueba de RAM por encima de 1 MiB. Esta observación no
certifica los tests posteriores al bloque omitido. La nueva captura funciona
con ambas ROM para esta rutina, que conserva direcciones e instrucciones.

No se ha cerrado todavía la causa del fallo físico de 16K. Esta entrega añade
observabilidad comprobada, no una supuesta corrección de memoria. No modifica
la BIOS, el CPU vendorizado, el mapeo SDRAM, sus latencias, el reset, los relojes
ni las restricciones de timing. No se ha sintetizado ni generado un nuevo RBF.

## Auditoría de simulación

Se ejecutan CPU, bridge AT, cargador HPS, propietario SDRAM y KFSDRAM reales.
La memoria de simulación sólo responde a los pines ACT/READ/WRITE, con geometría
x16, BL1, CL2, DQM de lectura con latencia 2 y de escritura con latencia 0.
Tiene ventana DQ finita y verifica que KFSDRAM muestrea ambas lanes válidas.
La dirección física completa se decodifica sin módulo ni alias artificial.
Sigue siendo un modelo funcional, no un modelo de cierre temporal o retención
de una SDRAM concreta ni una captura física de la placa.

Dos carencias del test anterior estaban ocultando contexto:

- La prueba aislada empezaba con DS=ES=0. El nuevo caso 12 usa DS=B800 y ES=0.
- El caso 11 ejecuta desde 8DDD: borrado de 64 KiB, impresión del encabezado
  original y prueba de cinco patrones. Esa ruta deja CX=SI=06E4 al entrar en
  9F14; el MOV ES,SI de la ROM hace que la ventana sea 006E40–00AE3F. Se exige
  ese contexto explícitamente. El título «16K» no basta para deducir la dirección.

En ambos casos se comprueban desde fuera del CPU las 81.920 escrituras y las
81.920 lecturas de FF/01/55/AA/00, la secuencia completa de direcciones, los datos
y las lanes. Un acceso RAM fuera de la ventana es error; no se ignora.

También se corrige el criterio de llegada a los manejadores: debe comenzar una
instrucción real. Un READ de código por sí solo no lo prueba. En particular,
9B67 es RET y el prefetch puede leer 9B68 sin ejecutar su manejador de error.
El primer intento del caso 11 descubrió este falso fallo del testbench.

Los casos 13 y 14 corrompen exclusivamente un bit del almacenamiento simulado,
después de escribir el primer patrón y antes del READ. Direcciones 000000 y
000001: esperado FF, recibido FE. El diagnóstico real alcanza 9E49 y la nueva
traza captura exactamente ese error, comprobando byte CPU, palabra CPU,
palabra backend, palabra KF, direcciones, BE, DQM y flags del propietario.
No se añade esa inyección al hardware.

El caso 15 selecciona el vector original sin modificar el buffer ROM y trata
de llegar al primer test RAM a través de los tests previos. Su resultado y
límite se registran por separado; no confundirlo con los casos aislados.
**Resultado de esta revisión:** no alcanzó el marcador de entrada a RAM ni un
resultado del test dentro de 600 segundos. Es una investigación inconclusa,
no un PASS del POST completo; ver `original-post-result.md`.

## Timing del RBF que aportó el usuario

Se ejecutó únicamente TimeQuest sobre el fit existente. En slow 1100mV 100C:

| Grupo | Peor setup slack |
|---|---:|
| Registros del CPU | **-4,338 ns** |
| Entrada SDRAM -> reloj de máquina, según SDC actual | +5,401 ns |
| Máquina -> salida SDRAM, según SDC actual | +5,915 ns |

La ruta CPU identificada parte de micro_pc[0], atraviesa ROM de microcódigo y
selecciones del ejecutor, y termina en gpr_q[27], bit 11 de CX. Tiene 23,678 ns
de retardo de datos para una relación de reloj de 20 ns. Es un incumplimiento
real del informe; aún no demuestra por sí solo la causa del error RAM.

El informe antiguo del perfil XT documenta un cierre CPU positivo, pero no se
ha equiparado ese informe histórico con el RBF XT que el usuario tiene cargado.
No se añaden falsos caminos ni excepciones multiciclo para ocultar estas rutas.
La instrumentación es pasiva, pero puede alterar colocación/ruteado: revisar el
nuevo fit, sin atribuir una eventual mejoría sólo al cambio de depuración.

Evidencia: `analysis/at_critical_ram_20260912/`, incluidos `audit.tcl`, informes
de caminos y `hardware-checkpoint.md`. El RBF anterior está conservado como
`releases/PCAT-286_20260912_pit_parity_hardware_checkpoint_AT_FAST.rbf`.

## Instrumentación y contrato de interfaces

`spk286_at_ram_trace.sv` observa únicamente señales y no tiene salidas de control.
El wrapper y la máquina exponen tres salidas de observación que ya existían en
SPK286: `debug_instruction_retired`, `debug_instruction_ip` y
`debug_segment_bases`. No se añaden entradas ni cambios al protocolo del CPU.

La captura se arma al retirar CLD en F000:9F14, base de CS=0F0000. Registra cada
CMP AH,BL retirado en 9F37 y conserva el primero cuyo ZF es cero. También retiene
el último CMP si se alcanza la salida de error de datos o de paridad pese a
haber observado ZF=1. El IP es el de la instrucción, no el cursor de prefetch.
Las lecturas de código y de otros propietarios no sustituyen el último dato RAM.

Se congela hasta el reset completo del core. Cambiar de página, repetir el POST
o hacer un reset sólo del CPU no borra una captura. No hace falta abrir la
página antes del fallo. Es una sonda específica para esta versión de Landmark;
no debe interpretarse como un detector universal para otras BIOS.

OSD AT: bit 82 activa **Landmark RAM Trace**; bits 84:83 seleccionan cuatro
páginas. Los bits anteriores conservan su función. Esta vista tiene prioridad
sobre First Fault y Boot Fetch. El overlay reutiliza el traslado de snapshot
coherente; su nuevo selector queda desactivado en XT y no se añade menú XT.

`VALID=1` indica una captura; `ARMED=1` que se ejecutó la entrada de la rutina.
`COMPARISONS` cuenta comparaciones retiradas y satura en FFFF. `SNAP` es el
contador de actualización de pantalla: puede cambiar con la captura congelada.

Cada página muestra T0..T3, palabras de 32 bits hexadecimales:

| Página | T0 | T1 | T2 | T3 |
|---|---|---|---|---|
| 0 Compare | formato / AH esperado / BL recibido / byte aceptado en bus (8 bits cada uno) | CS / IP del CMP | CX / DI después del INC | FLAGS / SI |
| 1 Read path | flags / dirección CPU de byte | flags / dirección backend de byte | flags / dirección KF de palabra | palabra aceptada por CPU / palabra backend |
| 2 SDRAM | muestra KF y señales físicas, abajo | ES / DS | 00 / base oculta ES (24 bits) | 00 / base oculta DS (24 bits) |
| 3 Registers | AX / BX | DX / BP | BE (byte superior) / última dirección escrita (24 bits) | último dato escrito / SP |

Separación «/» entre valores de 16 bits salvo indicación distinta. El dato de la
última escritura corresponde normalmente al final del patrón, no necesariamente
al byte que acaba de fallar.

Formato P0T0: C1=comparación con ZF=0; C2=salida de error de datos tras CMP con
ZF=1; C3=salida de paridad. Por ejemplo C1FFFEFE significa esperado FF, BL=FE,
y byte del bus=FE. DI ya fue incrementado: la dirección comparada se contrasta
con base ES + ((DI-1) & FFFF), y con el registro de dirección del bus.

Flags P1T0 (bits31:24): visto, VLD, RDY, BHE_n, estado CPU[3:0].
Flags P1T1: visto, READY, RVALID, WRITE, BE[1:0], owner[1:0].
Flags P1T2: KF read_request visto, KF read_flag visto, READ visto,
owner_state[3:0], reservado=0. owner_state={activo,respuesta_pendiente,refresh,idle}.

P2T0: bits31:16=muestra KF; 15:14=DQM durante READ; 13:12=DQM al muestrear;
11:10=BE; 9:6=owner_state al muestrear; 5:0=0. DQM observado en las salidas
dedicadas del FPGA; no se deduce de BE ni observa la conexión A12/A11 de la
placa. La lectura completa usa ambas lanes.

## Prueba física siguiente

1. Sintetizar el perfil **PCAT-286_AT_FAST** y dar al RBF un nombre nuevo, por
   ejemplo `PCAT-286_AT_FAST_ram_trace.rbf`. Esta revisión no lo ha generado.
2. Usar exactamente `Supersoft_Landmark_1.2.0_AT_5170_SKIP_PM_64K.BIN`.
   SHA-256: E9A3F0605996FF6802F44AD1744675C01DF9B5832273BB7472C878A6AAD03EC6.
3. Hacer reset completo del core y esperar al primer fallo de 16K. Permitir que
   la BIOS repita los tests: la traza permanece guardada.
4. En System & BIOS activar **SPK286 Debug** y **Landmark RAM Trace**.
5. Capturar las cuatro opciones de **RAM Trace Page**: Compare, Read path,
   SDRAM y Registers. Mantener legibles T0..T3 y VALID/ARMED/COMPARISONS.
6. Si VALID=0, capturar igualmente Compare con esos indicadores y la página
   CPU normal. Si el test pasa, informar también de ello y conservar el timing
   del nuevo fit. MEMORY REFRESH se evaluará por separado cuando AT lo alcance.

Estas capturas permitirán distinguir un dato ya incorrecto en SDRAM, una
transformación incorrecta en el bus, un registro distinto del byte entregado o
una comparación/flag errónea. No hace falta detener ni parchear la BIOS.

## Validación de la entrega

- `test_at_ram_trace.sh`: lint limpio del módulo; Icarus y Verilator PASS,
  incluyendo retención, reset completo, error de rama y ruta de paridad.
- `test_at_landmark_ram.sh`: casos 13/14 de inyección, 11 con encabezado original
  y 12 con DS distinto de ES, todos PASS. Los casos positivos recorren cinco
  patrones y 81.920 lecturas/escrituras cada uno.
- `test_at_bios_first_fetch.sh`: cuatro ROM, carga por HPS y primeros fetches PASS.
- `test_at_machine_boundary.sh`: elaboración, lint y transacciones PASS.
- Rutinas originales de paridad, PIT0/1/2, estado de refresco y NMI: PASS.
  La rutina aislada de estado de refresco no certifica retención física de RAM.
- Overlay AT/XT en ambos simuladores y elaboración del perfil AT: PASS.
- `decode_at_ram_trace.py` se comprobó contra los dos registros de inyección.
  Recibe cuatro palabras T0 T1 T2 T3 por opción `--compare`, `--read`, `--sdram`
  y `--registers`; emite valores decodificados en JSON.

El checkpoint de hardware anterior se conserva en el commit `1c71fb2`.
Esta entrega posterior añade únicamente diagnóstico, pruebas y documentación.
La validación física del nuevo observador queda para la síntesis del usuario.
