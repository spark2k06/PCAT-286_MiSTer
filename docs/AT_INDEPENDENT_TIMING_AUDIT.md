# Auditoría independiente de timing, relojes y equivalencia XT/AT

Fecha: 2026-09-12. Repositorio inspeccionado: `D:\GitHub\PCAT-286_MiSTer`.
HEAD al iniciar: `cab2f32d20398e4ca544c2dba6fc2c5242232c94`, con numerosos
cambios locales y perfiles AT sin seguimiento. No se revirtieron esos cambios.
Este informe describe el estado encontrado antes de las correcciones de esta
revisión y distingue el netlist ya compilado de los RTL que se están corrigiendo.

## Conclusiones comprobadas

1. El CPU del AT compilado **no cumple setup a 50 MHz**. Una extracción nueva
   de TimeQuest sobre la base de datos ya existente encuentra `-3.962 ns`
   dentro del SPK286. La peor ruta parte de `micro_pc[5]` y acaba en
   `gpr_q[24]`. No es una ruta de vídeo ni una excepción CDC.
2. La restricción del reloj externo SDRAM estaba ausente en AT: su fuente
   `emu|pll|...` no existe en el perfil `emu_at`. TimeQuest descartaba todos
   los `set_input_delay` y `set_output_delay` de SDRAM. El mensaje
   «0 unconstrained clocks» ocultaba 16 entradas de datos SDRAM y sus salidas
   sin restricciones.
3. Se corrigió exclusivamente la fuente de ese reloj, usando el cable real
   `FPGA_CLK2_50 -> SDRAM_CLK`, sin cambiar frecuencias, fases, RTL, QSF ni
   presupuestos externos. TimeQuest acepta la corrección y ahora descubre
   `-0.813 ns` de hold en `SDRAM_A[1]`, además de otras violaciones de hold
   en direcciones, comandos y datos. Estos valores usan los presupuestos
   heredados del proyecto; todavía no constituyen una medición del módulo
   SDRAM físico ni una validación de sus especificaciones.
4. El peor setup global, `-21.623 ns`, corresponde a `vga_out|rgb[8] ->
   SDIO_CMD`, una salida de vídeo analógico comparada contra `VCLK_SDIO`.
   Ese número no describe por sí solo al CPU. Existen, independientemente,
   las violaciones internas del CPU del punto 1.
5. Los reportes y el RBF de `output_files_pcat286_at_fast` **no pertenecen al
   RBF de la última prueba indicada por el usuario**. El hash de la release
   indicada sí coincide. No se atribuye al RBF probado el detalle de rutas
   de un fit posterior.

Estas evidencias impiden afirmar que cambiar sólo el mapeo de direcciones
resuelve la estabilidad física. Tampoco demuestran que un CS/IP concreto se
haya corrompido por timing: para eso hace falta capturar el primer fetch real.

## Identidad de los artefactos

| Artefacto | Tamaño | SHA-256 | Fecha local del archivo |
| --- | ---: | --- | --- |
| `releases/PCAT-286_20260912_at_sdram_word_address_AT_FAST.rbf` | 3,511,140 | `9CA0E727CC4585B009AB1054E999FB7D213EFFB6F080ADDA733F9975AF2EF3EC` | 12/09/2026 07:59:40 |
| `output_files_pcat286_at_fast/PCAT-286_AT_FAST.rbf` | 3,504,012 | `323D4FB86A1BDCE9C69878A28AD0CEDF1940B3012CD7A32B593A689F7E034A4D` | 12/09/2026 10:43:21 |
| `db/PCAT-286_AT_FAST.cmp.cdb` | 15,424,166 | `8D96B5FDAE941B5299815955A0E46C0BDC76111BCC5F920E73315F8C579EC37C` | 12/09/2026 10:42:44 |

El `sta.rpt` existente fue actualizado a las 10:44:46, después del RBF de
salida. Los reportes internos de Quartus usan hora UTC; las fechas de archivo
anteriores son las fechas locales que mostró PowerShell. No hay manifiesto
que vincule el hash de la release probada a una copia conservada de su netlist.

La extracción independiente no ejecutó síntesis, fitter, assembler ni una
compilación completa. Se montó el repositorio como sólo lectura, se copiaron
su base de datos y configuración a un directorio efímero del contenedor, y
se ejecutó únicamente `quartus_sta`. Esto evita que la obligación de Quartus
de disponer de una base de datos escribible altere el fit original.

## Rutas extraídas del fit existente

Modelo extraído: **Slow 1100mV 100C**, Quartus Prime 17.0.2 Lite.

| Grupo | Inicio -> final | Slack | Interpretación |
| --- | --- | ---: | --- |
| CPU interno y dominio síncrono 50 MHz | `u_cpu|cpu|microsequencer|micro_pc[5] -> u_cpu|cpu|registers|gpr_q[24]` | -3.962 ns | Violación real del camino registrado CPU a CPU; 30/30 rutas solicitadas violadas |
| Otro camino CPU | `microsequencer|micro_pc[7] -> micro_executor|tmp0_q[2]` | -3.855 ns | Segundo endpoint interno afectado |
| Llegada a 50 MHz desde vídeo | `hps_io_at|video_calc|vid_nres[7] -> hps_io_at|video_calc|dout[7]` | -7.678 ns | Cruce 57.27 MHz a 50 MHz; no es camino interno del CPU |
| Global | `vga_out|rgb[8] -> SDIO_CMD` | -21.623 ns | Vídeo analógico frente al reloj virtual SDIO |
| Splash a vídeo | `u_at_splash_control|splash_active -> u_video|u_ega|ega_text_inst|glyph_shift[1]` | -9.740 ns | Cruce directo de la opción splash desde 50 MHz a 28.64 MHz |

La peor ruta CPU tiene relación de reloj de 20.000 ns, retardo de datos
23.291 ns, skew -0.491 ns y 17 niveles lógicos. Atraviesa la ROM combinacional
de microcódigo, selección de servicios, suma/comparación de límite en
`operand`, control de escritura de SP y selección del dato de GPR.
`cpu_setup.rpt` contiene el recorrido completo, incluidas coordenadas del fit.
El Fmax de 41.73 MHz del reporte original es consistente con esta violación.
No se introdujo una excepción multicycle para ocultarla.

El reporte original también identifica un bucle combinacional de 21 nodos
en `operand_decode`, `opcode_start`, `allowed`, `fault_request`, `events`,
`queue_consume_ready` y `unsupported_decode_fault` (`sta.rpt`, línea 1979).
Su impacto funcional requiere una revisión separada del decode; no se afirma
que todos los fetch de reset activen ese camino ni que la simulación RTL
sin retardos reproduzca su comportamiento físico.

Los números de hold positivo citados para otra compilación no deben mezclarse
con el fit actual: el resumen actual ya contiene hold global de `-0.076 ns`
en Slow -40C y `-0.088 ns` en Fast -40C, aun antes de restringir SDRAM.

## SDRAM: restricción corregida y resultado

El estado previo de `PCAT-286.sdc`, líneas 6 y 19, esperaba una PLL principal
llamada `emu|pll`. El perfil AT conecta directamente:

```
sys_top.FPGA_CLK2_50 -> emu_at.CLK_50M
emu_at.CLK_50M -> u_at_sdram_owner.clk
emu_at.CLK_50M -> SDRAM_CLK
```

Referencias: `sys/sys_top.v:1772`, `spk286_at_emu.sv:147` y `:377` en el estado
auditado. El cambio de `PCAT-286.sdc` detecta la PLL privada AT existente y
crea el reloj SDRAM desde el puerto real `FPGA_CLK2_50`, divisor 1. Para XT
permanece literalmente la creación del reloj desde `CLOCK_CHIP` anterior.
No se añade un desfase artificial ni se modifica la frecuencia.

La segunda extracción confirma `SDRAM_CLK = 20.000 ns`, fuente
`FPGA_CLK2_50`, flancos 0.000/10.000 ns. Las entradas sin restricciones pasan
de 21 a 4 y las salidas de 87 a 49. SDRAM ya no aparece como puerto sin
input/output delay. Los presupuestos heredados se mantienen en entrada
max/min 6/3 ns y salida max/min 2/1.5 ns.

| Grupo SDRAM tras corregir el reloj SDC | Peor slack | Rutas solicitadas/violadas |
| --- | ---: | ---: |
| Entrada DQ, setup | +6.406 ns | 16/0 |
| Entrada DQ, hold | +6.880 ns | 16/0 |
| Salida comandos/dirección/datos, setup | +3.383 ns | 16/0 |
| Salida comandos/dirección/datos, hold | -0.813 ns | 16/16 |

Peor hold: `u_at_sdram_owner|u_KFSDRAM|sdram_address[1] -> SDRAM_A[1]`;
también fallan `SDRAM_A[10]` (-0.775), `SDRAM_BA[0]` (-0.530), `SDRAM_nCS`
(-0.523) y salidas DQ. El reloj externo y los comandos registrados no deben
presumirse alineados porque proceden del mismo nombre RTL: el fit tiene
retardos de red y de salida distintos. La corrección SDC sólo hace visibles
esos requisitos; no repara el circuito ya compilado.

Se necesitan todavía el modelo exacto de SDRAM instalado, sus requisitos
de setup/hold/tAC, el presupuesto de placa y los cuatro corners. Los signos
y valores de los delays heredados también deben revisarse contra ese contrato.
No se declara cumplimiento físico a partir de estos cuatro números.

## Tabla de diferencias funcionales

Referencias XT: `PCXT-EGA.sv` y `rtl/KFPC-XT/HDL/`; referencias AT:
`rtl/spk286_integration/`. Los números de línea son del inicio de la revisión;
los nombres de señales/instancias identifican los puntos tras cambios posteriores.

| Elemento | XT funcional | AT encontrado | Consecuencia |
| --- | --- | --- | --- |
| Reloj chipset/SDRAM | PLL `emu|pll`, salida `clk_chipset`, 50 MHz | Puerto `CLK_50M`/`FPGA_CLK2_50`, 50 MHz | Misma frecuencia nominal, distinta distribución física y jerarquía SDC |
| CPU | MCL86 con EU 100 MHz y BIU con enables del bus XT | SPK286 y puente con `clk=50 MHz`, `execute_enable=1` | El ajuste de velocidad XT no existe en AT; 50 MHz CPU no equivale al reloj externo de un 286 |
| Reloj vídeo | `pll_system_inst`, base 28.636, x2 57.272, salida x2 +90°, opción VGA 25.2 MHz | `u_at_video_pll`, base y x2/salida equivalentes; VGA nativa no usada | La SDC de vídeo heredada apunta a nombres inexistentes en AT |
| Reset OSD | `reset_wire` incluye `status[0]` y `buttons[1]` | `R0` está en el menú, pero `hps_status[0]` no participa en `at_boot_reset` | Fallo comprobado de equivalencia del reset OSD; corregido por la revisión de reset |
| Splash | Opción bit 7 y CPU retenida en reset | Bit 7 conservado; `at_machine_reset = at_boot_reset | at_splashscreen` | La versión auditada sí retiene CPU; vídeo/periféricos continúan con `at_boot_reset` |
| Señal splash hacia raster | Gestión heredada en dominio de vídeo | `splashscreen` llega directamente a `ega_top` desde 50 MHz | CDC directo identificado por STA; sincronización local necesaria para evitar transición incoherente |
| BIOS presente | Reset retenido hasta las BIOS exigidas por XT | `main_rom_loaded` retiene CPU; `ega_rom_loaded` sólo alimenta aviso OSD | Puede arrancar sin EGA BIOS; no explica corrupción del primer opcode |
| OSD compartido | Bit 0 reset, bit 7 splash, índices ROM C0/C2/C3 | Mismos índices; debug bits 71 y 73:72, como perfil SPK286 de referencia | No se reasignan bits incompatibles en esas funciones |
| OSD restante | Velocidad 18:17, efectos 2:1, relación 9:8, monitor 45:44, offsets 49:46/52:50, anchos 66:64/69:67 | Ausente; 4:3 fijo, offsets cero, perfil EGA 00, audio cero | La equivalencia OSD completa aún no existe |
| Vídeo VRAM | EGA y frontend BRAM compartido; funciones VGA extendidas disponibles | Reutiliza `ega_top` y `ega_vram_bram_frontend`; I/O mediante mailbox toggle | Los bytes de vídeo no compiten con la ROM en SDRAM externa |
| I/O vídeo CDC | Ruta heredada con sincronizadores | Petición toggle en dos etapas; campos mantenidos; respuesta y ack con retardo | Diseño de mailbox visible, pero sus constraints no están trasladadas íntegramente |
| PIT | `peripheral_ce` a 50 MHz con razón 21/440; timer alterna con ese enable; tres canales KF8253 | `counter_clock` alterna cada ciclo de 50 MHz; PIT detecta flanco y decrementa sólo canal 0 | Tick de 25 MHz, frente a ~1.19318 MHz XT; canales 1/2 incompletos |
| RTC | Implementación heredada con su base temporal | `second_tick` 1 Hz; `periodic_tick` cada 4096 ciclos (~12.207 kHz) | No se puede asumir una frecuencia RTC programable equivalente sin revisar el dispositivo |
| Refresh | Ruta heredada del chipset y KFSDRAM | Solicitante normalizado cada 32 ciclos libres más latencia; prioridad sobre DMA; HOLD/HLDA | Sobrecoste y comportamiento distinto; no se ha demostrado inanición del CPU |
| Arbitraje | Árbitro XT, permisos de bus y owner RAM heredado | Prioridad loader > refresh > DMA; exige HLDA y puente drenado, excepto loader bajo reset | Interfaz distinta que necesita probarse con CPU real, no sólo modelo de memoria |
| Almacenamiento/audio | Interfaces de disco y audio del XT | Fronteras funcionales AT simplificadas; audio atado a cero | Están fuera del primer fetch y no debe prometerse equivalencia de la máquina completa |

Referencias auxiliares: `XT_CE_Generator.sv:26`, `PERIPHERALS.sv:468`,
`spk286_at_emu.sv:408`, `spk286_at_pit.sv:143`,
`spk286_at_refresh.sv:5`, `spk286_at_arbiter.sv:46`,
`spk286_at_video_adapter.sv:284` y `:453`.

## Pendientes concretos y límites de esta auditoría

- Capturar dirección/datos del primer fetch y su entrega a la cola CPU con
  el controlador SDRAM real. Un resultado correcto en RTL no elimina setup
  negativo ni prueba la integridad eléctrica de comandos/datos.
- Conservar juntos el próximo RBF, hash, fuentes/diff y base de datos o
  reportes de rutas. No se puede reconstruir el fit de una release sólo con
  su RBF y un `sta.rpt` que ya fue sobrescrito.
- Cerrar el camino síncrono `micro_pc -> gpr_q` y revisar el bucle decode.
  Reducir únicamente una opción de velocidad del bus no resuelve una ruta
  CPU que sigue registrándose a 50 MHz con `execute_enable=1`.
- Revisar los CDC de la nueva jerarquía AT uno a uno; no aplicar una
  excepción global que oculte el cruce directo de splash u otros buses.
- Volver a ejecutar STA con el contrato físico SDRAM comprobado y resolver
  hold en comandos/direcciones/DQ. No se alteraron presupuestos para hacer
  pasar los reportes.
- El cambio SDC no genera un nuevo RBF ni modifica uno existente. No hay
  validación de placa ni se atribuye aún una causa única a `F000:FFFx`,
  `CS=00xx` o `HLT=1`.

La extracción fue una auditoría puntual sobre un fit anterior, no una
compilación completa ni parte del flujo de producción actual.
