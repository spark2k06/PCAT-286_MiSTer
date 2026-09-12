# Revisión independiente del arranque PCAT-286 MiSTer

Fecha: 12 de septiembre de 2026. Repositorio: `D:\GitHub\PCAT-286_MiSTer`.

## Resultado y alcance

**La causa única de los fallos observados en placa todavía no está cerrada.** Se han
reproducido y corregido cuatro defectos de control de arranque, y se ha descubierto
que la SDRAM del perfil AT no estaba siendo analizada por sus restricciones de
entrada/salida. El fit conservado también incumple setup dentro de la CPU.

El recorrido lógico completo de primer fetch sí funciona en la nueva simulación:
HPS -> loader de producción -> arbitraje -> propietario -> KFSDRAM -> pines de
SDRAM modelados -> propietario -> puente -> dato aceptado por SPK286. Cuatro ROM
originales cargadas por este recorrido alcanzan el salto de reset correcto. Esto
no valida timing físico ni permite declarar solucionado el arranque en hardware.

No se ha hecho una compilación completa ni generado un RBF. Se ejecutó únicamente
TimeQuest sobre una copia aislada del fit existente. Se conservaron los cambios
locales encontrados; no se cambiaron las ROM ni el motor SPK286 importado.

La referencia se contrastó tanto con `PCAT-286.sv` (SPK286 sobre chipset XT) como
con `PCXT-EGA.sv` y la copia funcional de `D:\GitHub\PCXT-EGA_MiSTer_devel`.
Los archivos RAM y KFSDRAM de ambos repositorios son idénticos byte a byte:

- RAM.sv: SHA256 `13CE7F8C9ED1D6C3C544CF7DE1ACCD78E89B5D06E004865DEC89A841064C340B`.
- KFSDRAM.sv: SHA256 `F5B9335C86DC8AD52ECA58D7FEA91D8AA35BA7126CDE559D9E63FC5A31B86AEF`.

## Hallazgos clasificados

| Área | Evidencia | Corrección/estado |
| --- | --- | --- |
| Reset/splash | AT liberaba CPU mientras `splash_pending_q=1` y `splash_active=0`, hasta el siguiente tick; entonces la reseteaba otra vez. XT incluye pending en reset. Se reprodujo un fetch FFFFF0 en esa ventana. | `boot_hold` cubre pending y visible; regresión con fetch real falla antes y pasa después. |
| Reset y transacción retenida | Una petición CPU anterior al reset podía permanecer en memory_port antes de aceptación y aportar su dirección al siguiente fetch. La regresión reproduce el fallo. | Nuevo cancel_cpu: elimina solicitudes no aceptadas y drena las aceptadas sin devolver su respuesta a la CPU reiniciada; conserva loader/DMA/refresh. |
| Reset OSD | La opción R0 estaba anunciada pero `hps_status[0]` y `hps_buttons[1]` no entraban en `at_boot_reset`. | Se conectan como en XT. `RST` de debug también observa el reset efectivo pedido por 8042. |
| Carga de BIOS | `main_rom_loaded` y `main_seen_q` conservaban la ROM anterior al iniciar otra descarga. Se podía liberar reset antes de acabar la última escritura. | Presencia invalidada al comenzar cada descarga dirigida; sólo se confirma al acabarla y drenar la escritura. Test antiguo falla diez comprobaciones nuevas; corregido pasa. |
| Fetch/ROM | Cuatro ROM llegan desde 32.768 escrituras HPS al opcode EA aceptado por CPU y al destino correcto del salto lejano. | No se reproduce un fallo lógico inicial con el mapeo y handshake actuales. No se cambia nuevamente la dirección. |
| SDRAM lógica | KFSDRAM usa banco/fila/columna de una dirección de palabra. La captura actual coincide con CL2 nominal y DQ finito. | Se conserva A>>1 y el alias existente; nuevo modelo independiente y control negativo de desfase. |
| SDRAM física | SDC buscaba el PLL XT inexistente y descartaba todos los delays SDRAM. | Se corrige la fuente del reloj generado AT. Aparece hold negativo bajo los presupuestos heredados; todavía requiere cierre físico. |
| Timing CPU | En el fit conservado, ruta micro_pc -> gpr_q de 23.291 ns con reloj de 20 ns; slack -3.962 ns. | No corregido mediante cambios especulativos de frecuencia o esperas. Es un incumplimiento síncrono real, distinto de vídeo. |
| Modo protegido | MSW.PE se mantiene a cero durante todas las secuencias iniciales comprobadas. Segment reload sigue siendo real-mode. | Limitación posterior real; no explica el primer fetch fallido ni justifica parchear ROM. |
| Splash/vídeo | El raster debe seguir activo mientras CPU permanece reseteada; existen CDC nuevos y diferencias de periféricos. | Se conserva la separación CPU/raster; no se afirma equivalencia completa de vídeo ni POST. |

Los defectos de recarga, petición retenida y pending pueden contribuir a una historia de estados
diferente entre intentos. **No explican por sí solos un arranque en frío fallido
con splash desactivado.** Esa observación del usuario sigue abierta y es coherente
con la necesidad de verificar señales físicas y timing.

## Dirección y bytes: qué hace realmente el hardware descrito

En `rtl/KFPC-XT/HDL/KFSDRAM/HDL/KFSDRAM.sv`:

- ACTIVE presenta `address[21:9]` como fila y `[23:22]` como banco.
- READ/WRITE presentan `[8:0]` como columna, con un contador de columnas por beat.
- Una posición física almacena 16 bits. El controlador no interpreta una
  dirección de byte 8088/80286 y no desplaza la dirección por dentro.
- La implementación emite ACTIVE antes del READ/WRITE. El modo es BL1 y CL2.

XT utiliza `kf_address=A` y guarda cada byte lógico en el byte bajo de una palabra.
El cargador XT descompone la palabra WIDE en dos escrituras de byte. AT conserva
la palabra WIDE: carga `ioctl_data[7:0]` en lane baja y `[15:8]` en lane alta,
`byte_enable=11`, dirección lógica `0F0000+ioctl_addr`, dirección física A>>1.
Su puente de CPU sigue serializando un fetch de palabra en dos beats, BE=01 y 10,
que vuelven a leer la misma palabra física. Después recompone el dato para CPU.

Para el vector:

```
CS=F000, base oculta=FF0000, IP=FFF0
CPU byte=FFFFF0 -> alias byte=0FFFF0 -> palabra=07FFF8
banco=0, fila=03FF, columna=1F8
```

La BIOS se carga en F0000..FFFFF. El alias FFF000..FFFFFF permite usar esa misma
copia al reset. El decoder mantiene la dirección de CPU de 24 bits; el propietario
traduce antes de los pines. El mapeo es del chipset de este proyecto: la prueba no
presupone que una SDRAM haga mirroring automáticamente.

La expresión anterior `{A[23:1],1'b0}` era **A & ~1**, no un desplazamiento en
sentido contrario. Podía describir una distribución dispersa de palabras, pues
cargador y CPU pasaban por el mismo propietario. Se corrigió el comentario que
atribuía sin evidencia ubicaciones distintas a ambos. Confirmar la convención
actual no demuestra retrospectivamente la causa del fallo del RBF anterior.

DQM es activo alto: una escritura BE=01 usa DQM=10, BE=10 usa DQM=01, BE=11 usa
DQM=00. El propietario permite ambos bytes durante lecturas y la selección se
hace al devolver el beat. Se probaron ambas lanes y el cruce de columna 1FF a la
fila siguiente. No hay truncamiento silencioso de banco/fila en el nuevo modelo.

## Latencia y validez

La secuencia nominal, nombrando E0 al flanco que acepta la solicitud, es:

| Flanco | FPGA/controlador | Memoria externa modelada |
| --- | --- | --- |
| E0 | Aceptación, registra salida ACTIVE | Todavía observa comando anterior |
| E1 | Registra salida READ | Muestrea ACTIVE |
| E2 | Registra NOP | Muestrea READ |
| E3 | Espera | DQ empieza a ser válido tras tAC |
| E4 | Captura DQ y registra `read_flag` | DQ válido en el flanco; después termina su ventana |
| E5 | Owner captura juntos `kf_data_out` y `kf_read_flag` | DQ ya no necesita permanecer válido |
| E6 | Arbitraje/bridge consumen respuesta estable | Ciclo físico se drena |

La definición CL2 se contrastó con [ISSI, figura 6 y sección CAS Latency](https://www.issi.com/WW/pdf/42-45VM16160M.pdf): el dato comienza a salir un flanco antes del flanco en que debe estar válido. El modelo usa tAC=6 ns y tOH=3 ns como escenario explícito; no son una medición del módulo del usuario.

No se encontró evidencia que justifique añadir otro ciclo de captura. El nuevo
modelo vuelve a Z fuera de la ventana con Icarus; con Verilator usa DEAD y una
señal `dq_valid` independiente, comprobada en el flanco real de captura KF.
Un control negativo con 4 ns de desfase artificial del reloj y 1 ns de retardo de
comandos produce Z y falla. **Ese desfase es una inyección de prueba, no un valor
medido en la placa.**

No es un modelo de sign-off del fabricante. No reproduce todos los tRCD/tRP/tRFC,
setup/hold, retención ni efectos eléctricos. El test integrado nominal tampoco
simula el netlist colocado ni los retardos de PCB.

## Lo que ocultaban las pruebas anteriores

- El test owner recortaba la dirección física a 14 bits y mantenía la última
  palabra en DQ indefinidamente. No representaba el enmascaramiento de lectura.
- La última comprobación del alias miraba `kf_address` combinacional y terminaba
  sin aceptar y completar aquella lectura.
- El test machine dejaba loader desconectado y precargaba un array lógico de ROM.
  Su traducción inversa dependía de la misma hipótesis de mapeo que se quería probar.
- El test splash comprobaba la duración de la imagen, pero no que la CPU siguiera
  en reset durante pending.
- Una compilación correcta y cero errores en TimeQuest no implicaban restricciones
  válidas ni setup/hold cumplidos.

Las nuevas pruebas se añaden a las existentes; no se han cambiado sus resultados
esperados para hacer pasar el core ni se han modificado imágenes BIOS.

## Resultado de la prueba integrada

`test_at_bios_first_fetch.sh` carga cada ROM completa por el loader de producción;
ningún byte del modelo físico se precarga desde una dirección lógica de BIOS.
Comprueba cada lane backend y cada byte aceptado en CPU READY. Registra 32 beats
SDRAM y al menos 16 respuestas nativas, comprueba PE=0 y la asociación del nuevo
registrador hardware con el primer fetch. Se conserva una waveform FST por ROM.

| ROM | Primer dato físico/CPU | Destino después de EA | Resultado |
| --- | --- | --- | --- |
| pcat286_event_diag.rom | 00EA | F000:0000, base 0F0000 | PASS |
| pcxt_xtsergey.rom, original | 5BEA | F000:E05B, base 0F0000 | PASS |
| Supersoft_Landmark_1.2.0_AT_5170_64K.BIN, original | 65EA | F000:8065, base 0F0000 | PASS |
| IBM_AT_5170_15NOV85_62X082x_64K.BIN, original | 5BEA | F000:E05B, base 0F0000 | PASS |

Cada una produce exactamente 32.768 WRITE físicos durante la descarga. El test
no certifica que estas BIOS completen POST: se detiene al completar la ventana
inicial. Tampoco incluye el HPS ARM real ni todo el relevo de reset del emu; la
prueba de splash/reset es independiente y la interfaz ioctl se estimula en su
mismo dominio de reloj. La regresión machine completa continúa pasando con el
diagnóstico del proyecto: 207 beats, 12 escrituras I/O, IRQ0=1, refresh=37, POST=4.

## Comparación funcional XT frente a AT

| Señal o función | XT/SPK286 sobre XT | AT actual |
| --- | --- | --- |
| Reset de CPU | Reset por framework, OSD, PLL, splash visible y pending; ROM hold | Incluye OSD y pending tras esta corrección; también reset local 8042 |
| CS:IP inicial del SPK286 | F000:FFF0 | El mismo wrapper y registros: F000:FFF0 |
| Base oculta SPK286 | FF0000; proyección al bus XT | FF0000; dirección nativa de 24 bits |
| Generación de dirección | Base+IP, después adaptación XT | Base+IP, decoder AT, traducción del alias en owner |
| ROM/carga | WIDE descompuesto en bytes, un byte por palabra física | WIDE conservado, dos bytes por palabra física; presencia corregida al recargar |
| SDRAM | RAM.sv + KFSDRAM; source del reloj PLL declarado | Owner AT + mismo KFSDRAM; ahora se declara el source real FPGA_CLK2_50 |
| Lanes | Byte bajo de cada palabra; word requiere dos posiciones | Dos lanes de la misma palabra; puente serializa ambos bytes |
| Latencia lectura | CL2 + lógica RAM/Ready XT | CL2 + registro de respuesta owner + handshake AT |
| Ready/valid | Bus XT y adaptador, espera de RAM | Aceptación retenida; read completion necesita ready y read-valid |
| Reloj CPU SPK286 | 50 MHz de PLL, execute_enable=1 | 50 MHz directo, execute_enable=1; fit disponible falla CPU setup |
| Reloj vídeo | PLL 28.636/57.272 MHz y salida con fase | PLL equivalente con nueva jerarquía; cruces AT requieren revisión |
| Splash | CPU retenida durante toda fase; raster activo | Mismo principio tras boot_hold; no equivalencia completa del aviso de BIOS ausente |
| OSD | Configuración amplia; reset0, splash7, ROM C0/C2/C3, debug71/73:72 | Esos bits se conservan; se añaden 74..80 sólo para diagnóstico AT |
| Arbitraje | Dueño RAM y chipset XT | CPU/DMA/refresh y loader retenidos en interfaz normalizada; un solo owner SDRAM |
| Vídeo vs SDRAM ROM | VRAM EGA en su frontend BRAM | También BRAM; no hay segundo owner de ROM por vídeo |
| Periféricos en splash | Reset de chipset y tratamiento específico del raster | Reset CPU prolongado; dispositivos permanecen vivos para el raster |
| PIT | Base ~1.193 MHz; KF8253 de tres canales | Entrada actual 25 MHz; sólo canal0 decrementa en implementación AT. Diferencia posterior al primer fetch |
| EGA BIOS ausente | Hold/aviso real | Flag alimenta aviso; reset de boot sólo exige ROM principal. Diferencia aún pendiente |

La tabla detallada de relojes, CDC, OSD y periféricos está en
[AT_INDEPENDENT_TIMING_AUDIT.md](AT_INDEPENDENT_TIMING_AUDIT.md). No se copiaron sin
más todas las opciones XT: anunciar funcionalidades AT todavía ausentes daría
una equivalencia falsa.

## Interpretación de F000:FFFx, CS bajo y HLT

No hay una traza hardware que permita asignar una causa distinta a cada captura.
Los estados variables no deben reducirse a un bucle determinista único.

- **F000:FFFx con base FF0000:** el estado sigue en la región de reset. Puede estar
  leyendo/decodificando otra secuencia, esperando, redirigiendo o repitiendo.
  Las ROM comprobadas contienen EA y salen de allí cuando reciben los bytes correctos.
  Si la placa recibe lo mismo y no salta, hay que mirar aceptación CPU, cola y
  ejecución; si recibe otros bytes, hay que remontar datos, carga y pines SDRAM.
- **CS=0004, base=000040:** coincide exactamente con la lógica de recarga real-mode
  `base=selector<<4` de spk286_segments. Sugiere una recarga de segmento con ese
  selector; no demuestra qué instrucción o qué corrupción lo produjo. Una lectura
  errónea de operandos de salto o de un vector de excepción puede producirlo.
- **CS=0000:** puede provenir de una recarga/retorno/evento que lea un selector cero;
  no es el reset arquitectónico implementado. Opcode ilegal/formato inválido
  solicita #UD vector6; con IVT aún no inicializada el destino no será la BIOS.
  Hay que capturar vector/evento y lecturas de IVT antes de atribuirle ese origen.
- **HLT=1:** hace falta demostrar si CPU aceptó y ejecutó F4 o si se corrompió estado.
  La salida visual por sí sola no permite distinguirlos.
- **Opcode del overlay:** es `opcode_q`, una instantánea del decoder. No es DQ de
  la lectura que aparece a la vez ni necesariamente el byte de CS:IP por prefetch.
  En nuestras trazas el primer backend devuelve EA mientras debug_opcode aún es 00.
  Por tanto ver F4/FF en una foto no prueba que fueran los bytes del vector.

Las rutas con setup incumplido permiten que la simulación lógica estable difiera
entre temperaturas, colocaciones y arranques físicos. Aquí eso es una explicación
posible apoyada por STA, **no una captura de la corrupción concreta del usuario**.

## Modo protegido

`spk286_system_0f.sv` implementa SGDT/SIDT/LGDT/LIDT/SMSW/LMSW y transacciones de
pseudo-descriptores. `msw_q` conserva PE una vez escrito. Eso no equivale a un 286
con modo protegido completo: `spk286_segments.sv` sigue recargando bases como
selector<<4, sin consulta GDT/LDT, comprobación de descriptores ni LOADALL.
La propia cabecera del módulo lo declara y su lógica lo confirma.

Las cuatro secuencias iniciales verificadas no activan PE. No se parcheó ninguna
BIOS ni se eliminó ninguna prueba de memoria/modo protegido. La capacidad de
superar partes posteriores del POST debe investigarse después de estabilizar el
primer fetch físico.

## Evidencia de timing y RBF

La release indicada conserva SHA256
`9CA0E727CC4585B009AB1054E999FB7D213EFFB6F080ADDA733F9975AF2EF3EC`.
El fit conservado corresponde a un RBF posterior con hash `323D4FB86A1BDCE9C69878A28AD0CEDF1940B3012CD7A32B593A689F7E034A4D`.
**No son el mismo artefacto.** No se atribuyen las rutas del segundo al primero.

En el fit disponible, TimeQuest encuentra CPU setup -3.962 ns. Al corregir la
restricción ausente descubre SDRAM output hold -0.813 ns bajo los presupuestos
heredados. El peor setup global de -21.623 ns pertenece a una ruta de salida de
vídeo hacia SDIO_CMD, distinta de CPU. Ver informe de timing y reportes conservados.
El cambio SDC hace visible el problema: no lo corrige ni modifica un RBF existente.

Antes de un nuevo candidato deben cerrarse el camino CPU y los márgenes SDRAM con
el módulo físico identificado, y revisar CDC sin esconderlos mediante false paths
indiscriminados. No se ha bajado una opción de velocidad de BIOS/bus suponiendo
que eso resuelva una ruta CPU que sigue registrándose a 50 MHz.

## Cambios e interfaces de esta revisión

- `spk286_at_splash_control.sv`: nuevo output `boot_hold`; diferencia entre imagen
  visible y retención de CPU desde pending. Test con fetch real, no sólo contador.
- `spk286_at_emu.sv`: conecta OSD reset, reset real del 8042 en debug y cancelación
  de solicitudes CPU. Conecta el registrador y las opciones OSD 74..80.
- `spk286_at_mister_memory_port.sv`: nuevo input `cancel_cpu`. Impide aceptar
  comandos CPU durante reset; cancela los no aceptados; conserva metadata de los
  aceptados hasta completar físicamente y descarta su respuesta, incluso si el
  reset fue corto. No resetea memoria ni loader. Todas sus instancias actualizadas; contrato detallado en [AT_CPU_RESET_MEMORY_BOUNDARY.md](AT_CPU_RESET_MEMORY_BOUNDARY.md).
- `spk286_at_hps_rom_loader.sv`: presencia por descarga y drenaje final corregidos,
  sin cambiar dirección, endian ni protocolo de palabra.
- `spk286_at_mister_sdram_owner.sv`: sólo outputs de diagnóstico y comentario
  corregido. No se altera de nuevo A>>1, alias, DQM ni la captura de respuesta.
- Nuevo `spk286_at_boot_trace.sv`: RAM de 32x256 bits, lectura síncrona, captura
  pasiva y vista del fetch pendiente. Añadido al QIP.
- `spk286_debug_overlay.sv`: nuevo input `boot_trace_view`, enmascarado por
  `AT_MODE`; vista cruda de cuatro palabras y cabecera. La rama XT conserva su
  formato, verificado en Icarus y Verilator. No necesita cambiar el top XT.
- `PCAT-286.sdc`: sólo se declara el source real del reloj SDRAM en AT; la orden
  del perfil XT permanece equivalente. No se relajan presupuestos temporales.
- Tests nuevos y ampliados acompañan esos cambios. Las otras modificaciones
  locales visibles en `git diff` ya estaban presentes al comenzar la auditoría.

Las trazas FST, logs y el manifiesto de hashes/bytes de reset están conservados en
`analysis/at_boot_audit_20260912/`. El manifiesto de fuentes corresponde a los RTL finales probados en esta revisión. Los reportes de timing están en
`analysis/at_timing_audit_20260912/`. El test de primer fetch usa ahora los dos PIC
reales de producción, además de la CPU, bridge, arbiter, loader y owner reales.

## Reproducción y siguiente prueba en hardware

Desde WSL, en `/mnt/d/GitHub/PCAT-286_MiSTer`:

```sh
bash scripts/test_at_splash_control.sh
bash scripts/test_at_hps_rom_loader.sh
bash scripts/test_at_mister_memory_port.sh
bash scripts/test_at_boot_trace.sh
bash scripts/test_debug_overlay.sh
bash scripts/test_at_bios_first_fetch.sh
bash scripts/test_at_machine_boundary.sh
bash scripts/test_at_profile_elab.sh
```

Para el modelo físico con control negativo y VCD, desde PowerShell en el repo:

```powershell
./scripts/test_at_sdram_capture.ps1 -Vcd
```

El registrador hardware guarda los primeros 32 fetch nativos (hasta 64 beats
SDRAM), incluye el dato realmente aceptado por CPU y presenta una lectura en curso
si se queda sin READY. Usa el menú AT Boot Fetch Trace y la página de cuatro
palabras crudas. No interviene en reset, READY, HOLD, memoria ni ejecución.
La distribución detallada y manejo del menú están en [AT_BOOT_FETCH_TRACE.md](AT_BOOT_FETCH_TRACE.md).

**Estas opciones nuevas requieren un RBF futuro; no están en la release 9CA0… ni
se pueden activar simplemente copiando los fuentes al MiSTer.** El usuario se encarga de la síntesis y generación del RBF. No se entrega
ahora un bitstream etiquetado como validado. Se sugiere guardar el diagnóstico como
`releases/PCAT-286_20260912_independent_boot_diag_AT_FAST.rbf`. Deben conservarse hash, fuentes/diff, netlist y reportes juntos.

Una vez disponible ese candidato:

1. Cargar una ROM original exacta de la tabla, anotando su hash y el del RBF,
   y el módulo SDRAM usado. Cargar también EGA BIOS para evaluar imagen/POST.
2. Activar SPK286 Debug y Boot Fetch Trace. Para cada intento conservar índice00
   y las dos vistas Address/Data; después índices01..03 y, si diverge, hasta31.
   Anotar COUNT, WAIT, FULL, VALID y el primer índice distinto del esperado.
3. Hacer varios arranques en frío con splash Yes y No, y varios Reset OSD. RST
   debe ser continuo durante pending/visible; no debe haber ejecución previa.
4. En índice00 esperar CPU FFFFF0, palabra07FFF8, CS:IP F000:FFF0, baseFF0000,
   dato 5BEA para Sergey/IBM o 65EA para Landmark. Ambos beats del primer word
   deben conservar el dato y seleccionar BE01/10, DQM lectura00.
5. Después del salto esperar base0F0000 y el destino de la tabla. Comparar las
   muestras KF, backend y CPU del primer registro divergente, no sólo opcode visual.
6. Si WAIT queda activo sin registro completado: capturar owner/request/read_flag/
   read_valid/ready y dirección retenida. Si los datos aceptados son correctos
   pero CS cambia mal: capturar cola/decode, `opcode_start`, `opcode_q`,
   `micro_pc`, evento/vector y las lecturas de IVT mediante SignalTap.
7. Si KF ya devuelve datos distintos entre intentos, revisar primero WRITE de
   descarga al vector y READ de ese word: SDRAM_CLK, A, BA, CS/RAS/CAS/WE,
   DQM y DQ, con el flanco físico y setup/hold. Una foto del overlay no sustituye
   esa medición eléctrica ni un STA válido.

Lo que falta para cerrar la causa concreta es la primera secuencia fallida en
hardware que relacione dirección, dato KF, dato CPU y redirección, junto con la
identidad del módulo SDRAM y un fit asociado inequívocamente al RBF probado.

## Comprobaciones finales

- Primer fetch completo con cuatro ROM originales y PIC de producción: PASS.
  Por ROM: 32 beats, 16 respuestas CPU, PE=0; vector y registro hardware correctos.
- Machine boundary: elaboración Icarus, lint de producción Verilator y diagnóstico
  PASS (207 beats, 12 I/O, IRQ0=1, refresh=37, POST=4). El test heredado avisa de
  la ruta de su ROM gráfica splash ausente; no valida la imagen. El nuevo test
  de primer fetch sí ejecuta desde la carpeta del recurso, sin ese aviso.
- Profile selector/elaboración tras todas las interfaces nuevas: PASS.
- Splash/reset con fetch real: PASS Icarus/Verilator; baseline negativo conservado.
- Cancelación CPU antes/después de aceptación y loader conservado: PASS en ambos
  simuladores; baseline negativo conservado.
- Recarga y última escritura de ROM: PASS Icarus/Verilator; diez fallos antes.
- Recorder: PASS Icarus/Verilator, lint limpio e inferencia de memoria Yosys.
- Overlay: PASS de vista XT y palabras/cabecera AT crudas en ambos simuladores.
- Modelo físico: PASS de vector, lanes, fila y liberación DQ; control negativo
  de desfase detectado, con waveform VCD.
- No cambios al top/CPU/chipset XT ni al SPK286 importado; rama compartida del
  overlay comprobada. Sin síntesis ni nuevo RBF, conforme a la instrucción final.
