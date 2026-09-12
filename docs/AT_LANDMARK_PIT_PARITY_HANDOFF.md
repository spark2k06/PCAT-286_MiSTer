# AT: temporizadores, paridad y memoria — 12 de septiembre de 2026

## Estado y alcance

El usuario confirma que DMA2 y los registros de página pasan en hardware. El
commit `785231e` conserva las capturas, el RBF local asociado y su SHA-256;
`98690c0` contiene las correcciones de DMA. No se ha vuelto a sintetizar Quartus
ni se ha generado un RBF durante esta revisión. Esta entrega requiere síntesis
y prueba física del usuario.

El criterio es el IBM AT y las instrucciones reales del diagnóstico. El XT es
una comparación, no una especificación: la captura posterior del usuario muestra
que también falla su canal 2 y su prueba de refresco. No se modifican el perfil
XT, sus contadores KF8253 ni la BIOS del disco.

ROM seleccionada: `SW/ROMs/test/Supersoft_Landmark_1.2.0_AT_5170_SKIP_PM_64K.BIN`.
SHA-256: `E9A3F0605996FF6802F44AD1744675C01DF9B5832273BB7472C878A6AAD03EC6`.
Se mantienen las exclusiones de modo protegido que ya traía y se ignoran
checksums por instrucción del usuario. No se afirma un POST completo.

## Causas comprobadas

| Síntoma | Evidencia | Corrección |
|---|---|---|
| `B:1` desde el arranque | First Fault: T0=`0000A000`, T1=`F000FFF0`, T2=`00000000`, T3=`81E8A000`. Bits 13 RTC y 15 agregado; CPU en reset. `protocol_error` del RTC carecía de reset. Icarus devuelve X en frío y retiene 1 tras reset; Yosys optimiza el RTL anterior a constante 1. | Inicializar el indicador en el reset real del RTC. |
| Paridad U126/8042 | La rutina F000:8DCB lee 61h y prueba C0h. El AT no decodificaba ese puerto: respondía FF en la lane alta. Se observa el fetch real del manejador de fallo 0F9B68h. | Puerto B del AT independiente del 8042: latches de paridad/channel check, controles y lectura de estado. |
| Región crítica de 16 KiB | La rutina F000:9F14 escribe un patrón y compara cada byte; después lee 61h. Con el RTL anterior, el primer byte coincide, pero FF provoca el salto a 0F9E93h, la salida de **paridad**, tras 1 lectura y 16.385 escrituras (incluye reescritura del byte al fallar). | La misma corrección de 61h permite terminar cinco patrones, 81.920 escrituras y 81.920 lecturas. Ningún cambio de SDRAM. |
| PIT1/PIT2 y lectura de contadores | El PIT AT anterior sólo descontaba canal 0. No tenía puntero de lectura independiente ni latch correcto. La nueva prueba detecta que leer 1234h devuelve 3333h en el anterior después de un tick. | Adaptador de transacciones AT sobre los tres KF8253 existentes; verificados contra secuencias y resultados observables, no sólo contra su implementación. |
| Frecuencia PIT | El top alternaba counter_clock cada ciclo de 50 MHz: entrada de 25 MHz. | Acumulador fraccional de 1.193.182 Hz, muestreado en el mismo dominio de 50 MHz. |
| Estado de refresco | Leer 61h devolvía FF; bit 4 no podía mostrar ambas fases. | Bit 4 cambia por flancos ascendentes de OUT1. Los bucles originales 8E48h/8E52h observan las dos fases. |

El indicador B:1 anterior era una alarma de protocolo falsa; por sí solo no
demostraba un fallo de ejecución. Además ocupaba First Fault desde reset y
evitaría que esa captura mostrase un fallo posterior.

`SYSTEM BIOS` también es checksum: F000:973Eh selecciona DS=E000h, suma 65.536
bytes con LODSB/ADD AH,AL y comprueba AH=0. No se ha parcheado ni considerado
un fallo adicional de CPU. Los errores A/B y esta suma quedan fuera del objetivo
acordado para esta iteración.

La captura de pantalla por sí sola no identifica una celda SDRAM defectuosa ni
permite reconstruir la dirección que presenta el formateador de errores. La
reproducción anterior demuestra una ruta de falsa paridad; la prueba física
siguiente determinará si existe además otro fallo.

## Interfaces y comportamiento

- `spk286_at_pit` añade `counter_2_gate`, conectado a 61h bit 0. GATE0/1 siempre
  activos. IRQ0 utiliza el nivel OUT0, como el AT; deja de ser un pulso artificial.
- El adaptador retiene dirección, dato y lane. Tras aceptar: STROBE -> RELEASE
  -> DONE. KF8253 aplica la escritura al subir /WR; READY aparece después.
  Las lecturas se capturan durante /RD y el puntero avanza al soltarlo.
- `spk286_at_system_control` responde exclusivamente a 61h, byte alto del bus
  286. Escritura bits 0 GATE2, 1 habilitación de datos de altavoz, 2 deshabilitar/
  borrar paridad RAM, 3 deshabilitar/borrar channel check. Bits 7:4 de escritura
  ignorados. Reset del control=0Ch; ambos checks deshabilitados hasta habilitación.
- Lectura bits 7 paridad RAM, 6 channel check, 5 OUT2, 4 alternancia de refresco,
  3:0 controles. Los latches se comprueban mediante eventos inyectados; no se
  fuerzan a cero para ocultar errores. La paridad pendiente se enmascara mediante
  70h bit 7 y puede generar NMI al habilitarse. Un nivel retenido produce un NMI.
- La salida de depuración `debug_keyboard_port_b` muestra ahora ese puerto.
  First Fault conserva sus bits: bit 15 incluye también errores de protocolo de
  61h. Una máscara 8000h sin fuentes 11..14 apunta al nuevo puerto.
- La planificación física de AUTO REFRESH SDRAM sigue independiente del PIT,
  como exige la memoria usada en MiSTer. El bit 4 representa solicitudes del
  temporizador AT; no certifica retención física ni finalización de AUTO REFRESH.
- Reloj PIT: 23.863 transiciones en 500.000 ciclos de 50 MHz; semiperíodos de
  20 o 21 ciclos. No introduce un dominio de reloj derivado. Los ticks RTC de
  calendario/periódico no se han ampliado ni corregido en esta entrega.
- El backend KF8253 cubre las órdenes de contador/latch usadas aquí. **No se
  afirma implementar por completo el 8254**, en particular read-back de estado.
  Tampoco queda validado sonido físico: el bit de habilitación se almacena,
  pero la ruta de audio AT aún no está conectada al altavoz.

## Simulaciones y límites

`bash scripts/test_at_pit_ports.sh`: Icarus y Verilator; reset RTC frío/caliente,
reloj, tres contadores, latch LSB/MSB con 300 ticks entre bytes, conteo mientras
hay latch, GATE2, cero=65.536, OUT1/OUT2, paridad/channel-check inyectados,
limpieza de latches y rechazo de lanes inválidas.

`bash scripts/test_at_landmark_peripherals.sh`: SPK286, PIC real, carga HPS
completa de 32.768 palabras, puente AT, propietario SDRAM, **KFSDRAM real** y
modelo de pines SDRAM con ACT/READ/WRITE, CL2 y DQM. Casos:

| Caso | Rutina ejecutada | Criterio |
|---|---|---|
| 4 | Paridad, 8DCBh | Fetch del manejador PASSED 9CB5h, no del FAILED 9B68h |
| 5 | Memoria, 8DF6h -> 9F14h | Los cinco patrones FF/01/55/AA/00 en los 16 KiB y mismo manejador PASSED |
| 6/7/8 | Contadores 0/1/2, 8A45h/8ADBh/8AF3h | Rutinas originales de latch y lectura que comprueban todos los bits a uno y a cero |
| 9 | Refresco, 8E48h | Bucles originales esperan bit 4 alto y bajo, con PIT1 modo 2/count 18 |
| 10 | Fixture de integración de NMI | Provocar paridad, esperar enmascarada, habilitar NMI, un handler, borrar alarma, IRET y continuar |

Los casos 4..9 preparan el contexto anterior mediante un prólogo en la copia
privada de ROM del test (SS=F000h, contexto de contador y salto a rutina). Las
instrucciones de las rutinas originales permanecen idénticas. Caso 9 comprueba
las señales de refresco, **no** el largo retardo de retención completo 8E21h.
Caso 10 es firmware de prueba, no una rutina de Supersoft. No se publica ni se
escribe ninguna de esas modificaciones en la ROM del usuario.

Los resultados se detectan por un fetch del manejador remoto, no comparando
simplemente el IP del overlay: el IP puede avanzar mientras aún se muestra el
opcode previo. Se elevó el límite a 50 millones de ciclos para terminar los
23,8 millones que necesita la prueba de memoria; no se redujo su cobertura.

Regresiones adicionales: DMA2/páginas originales (casos 1/2), primeras lecturas
de cuatro BIOS, A4 DMA/PIT/arbitraje, frontera de máquina (PIC real en elaboración
/lint; modelo de PIC en el escenario histórico), A5 dispositivos, First Fault y
overlay XT/AT, y elaboración del perfil de producción. Los recursos del splash
se resuelven desde el directorio de vídeo en las pruebas A5/máquina.

Además, un oráculo independiente de los flags de CPU comprueba la secuencia
de todas las direcciones, la lane y el dato de cada uno de los cinco patrones.

Las evidencias y comandos reproducibles están en
`analysis/at_pit_parity_20260912/`. No hay cambio en la convención de dirección,
lanes ni protocolo SDRAM: son las mismas rutas físicas probadas antes del cambio.
No se ha simulado todo el POST ni se certifica todo modo real del 286.

## Timing del RBF anterior suministrado por el usuario

Se han leído los informes existentes de `output_files_pcat286_at_fast`; no son
informes de las nuevas correcciones. En slow 1100 mV/100 C:

| Dominio | Setup | Hold |
|---|---:|---:|
| VCLK_SDIO | -22,197 ns | +11,603 ns |
| CPU/sistema FPGA_CLK2_50 | -7,696 ns | +0,255 ns |
| SDRAM_CLK | +2,273 ns | +0,272 ns |
| Vídeo PLL general[2] | -7,378 ns | -0,730 ns |

Fmax del dominio CPU/sistema: 37,28 MHz frente a 50 MHz configurados. El diseño
**no tiene timing cerrado**. Los informes no bastan para atribuir cada violación
a una ruta concreta; hará falta report_timing de endpoints si se aborda ese
trabajo. No se han añadido false paths ni relajado constraints. Estos problemas
son distintos del puerto ausente y del reset RTC, reproducidos independientemente.

## Prueba física siguiente

1. Sintetizar el perfil AT_FAST desde esta revisión. Generar un nombre nuevo,
   por ejemplo `PCAT-286_20260912_pit_port61_rtc_AT_FAST.rbf`; guardar SHA-256
   e informes de timing. Conservar el checkpoint DMA anterior.
2. Cargar exactamente la ROM SKIP_PM indicada arriba. Hacer un reset completo
   del core (o recarga del RBF); el reset sólo de CPU no borra First Fault.
3. Comprobar `B:0` y First Fault T0=00000000 desde el arranque. Si cambia,
   capturar la página First Fault completa antes de otro reset.
4. Dejar correr al menos tres pasadas. Resultados esperados de esta corrección:
   Timer0/1/2, DMA1/2/páginas, paridad y 16K CRITICAL MEMORY REGION en PASSED.
   MEMORY REFRESH debería poder superar también la lectura de sus dos fases;
   su prueba completa de retención queda para esta validación física.
5. Ignorar ROM A/B y SYSTEM BIOS (checksums). Registrar cualquier otra línea
   nueva y el número de pasadas; una foto con el overlay apagado permite leerlo.
6. Si persiste un fallo o una parada: enviar POST sin overlay, página CPU y
   First Fault. Para un problema de memoria, añadir página Registers y Bus
   mientras se reproduce, sin resetear. Si T0 sigue cero, la ausencia de una
   alarma de protocolo no demuestra por sí sola que todos los datos sean correctos.

## Referencias primarias

- IBM Personal Computer AT Technical Reference, septiembre 1985, System Timers
  1-22/1-23, NMI 1-38/1-39 y listado POSTEQU/WAITF:
  https://www.scribd.com/document/585267906/IBM-5170-Technical-Reference-6280070-SEP85-Page109
- Intel 8254 datasheet, Counter Latch Command y Read-Back Command:
  https://www.cs.umb.edu/cs341/Intel8254/I8254PIT.pdf
- RTL local de KF8253 y Peripherals.sv como comparación de implementación;
  no se toma su comportamiento como sustituto de las pruebas del AT.
