# Disquetera AT, DMA1 y diagnóstico Landmark

Fecha: 2026-09-12

## Causa raíz

La ruta AT no contenía un controlador de disquetera funcional. El bloque de
`spk286_at_storage_video.sv` sólo devolvía un MSR fijo, reconocía de forma
parcial los comandos `06h/46h/08h` y fabricaba dos transferencias DMA. No
implementaba el Digital Output Register, las fases de parámetros y resultados,
el estado del uPD765, el IRQ6 de reset, la geometría del medio ni el transporte
de sectores con HPS. Ese modelo no podía superar las pruebas **FLOPPY ADAPTER**
y **FLOPPY READ** aunque el PIC y el DMA estuviesen funcionando.

La integración reveló un segundo error independiente en DMA1. Los canales
byte-wide 0..3 emitían siempre `byte_enable=01`, incluso para una dirección
física impar. En la SDRAM de 16 bits, el byte impar debe usar el lane alto
(`byte_enable=10`). El comportamiento anterior hacía que cada par de bytes de
un sector de 512 bytes se dirigiese a la misma palabra y corrompiese el buffer.

## Implementación seleccionada

El AT utiliza ahora `rtl/common/floppy.v`, el mismo controlador que emplean los
perfiles XT, ao486 y z486. Los cuatro ficheros comparados tienen el SHA-256:

```text
CF88179395672377DB272D6D6B282ACED8730995D9BA20A765FCC2C988D70553
```

No se ha creado una variante del controlador. El nuevo
`spk286_at_fdc.sv` adapta únicamente las fronteras del AT:

* I/O `03F0h..03F7h` al bus normalizado `request/accept/ready`.
* DRQ/DACK del uPD765 al canal 2 de DMA1.
* IRQ del controlador a IRQ6.
* Gestión MiSTer `hps_ext` en la ventana `F2xx`.
* Byte del dispositivo en `[7:0]`; la ruta DMA lo coloca en el lane SDRAM que
  selecciona A0.

El pulso `dma_ack` se genera cuando termina la transferencia de memoria del
mismo beat. Así el FIFO del FDC no avanza antes de que la SDRAM haya aceptado
el byte. `dma_tc` acompaña al último DACK y el resultado normal del comando de
lectura queda disponible antes de retirar DRQ.

La comparación independiente con `D:/GitHub/86box_dev/src/floppy/fdc.c`
confirma las operaciones que usa Landmark: reset mediante el bit 2 del DOR,
habilitación de DMA/IRQ mediante el bit 3, `Specify` (`03h`), `Read Data`
(`06h/66h`), `Recalibrate` (`07h`), `Sense Interrupt` (`08h`) y `Seek`
(`0Fh`), además de la fase de siete bytes del resultado de lectura.

## OSD y medios

El perfil AT expone exactamente los controles de medio presentes en XT:

```text
S0,IMGIMAVFD,Floppy A:;
S1,IMGIMAVFD,Floppy B:;
OJK,Write Protect,None,A:,B:,A: & B:;
```

La protección usa `status[20:19]`, igual que XT. La geometría, presencia,
tamaño y flujo de sectores no son opciones manuales del OSD: `hps_ext` los
deriva de cada imagen montada y los entrega al controlador. Las opciones de
orden de arranque que aparecen en ao486/z486 alimentan su BIOS/plataforma y no
son un ajuste del FDC; no se añaden al perfil AT.

## Prueba que reproduce Landmark

`scripts/test_at_landmark_floppy.sh` ejecuta los bytes originales de la ROM
Landmark parcheada en dos puntos de entrada. El arnés sólo reduce los bucles de
espera largos y proporciona un manejador real para IRQ6; no sustituye las
operaciones del FDC ni las comparaciones PASS/FAIL.

El caso de adaptador ejecuta:

```text
DOR 0C,08,0C -> IRQ6
Sense Interrupt 08 -> ST0=C0, PCN=00
Specify 03 CF 02
```

El caso de lectura configura DMA1 canal 2 en `000A00h`, cuenta `01FFh`, modo
`46h`, monta una geometría de 1,2 MiB y ejecuta el comando:

```text
66 00 00 00 01 02 09 2A FF
```

Se comprueban 512 direcciones consecutivas, lanes `01/10` alternos, los datos
devueltos, la imagen final en SDRAM, terminal count, IRQ6 y el resultado normal
`ST0 & C0h = 00h`.

## Verificación

```text
scripts/test_a5_at_devices.sh
  Icarus:    A5_AT_DEVICES_PASS, floppy_dma_beats=512
  Verilator: A5_AT_DEVICES_PASS, floppy_dma_beats=512

scripts/test_at_landmark_floppy.sh
  case 21: AT_LANDMARK_FLOPPY_ADAPTER_PASS
  case 22: AT_LANDMARK_FLOPPY_READ_PASS, dma_bytes=512

scripts/test_at_dma_registers.sh
  Icarus/Verilator: AT_DMA_REGISTERS_PASS

scripts/test_a4_dma_refresh_pit.sh
  Icarus/Verilator: A4_DMA_REFRESH_PIT_PASS

scripts/test_at_machine_boundary.sh
  AT_MACHINE_ICARUS_ELAB_PASS
  AT_MACHINE_PRODUCTION_LINT_PASS
  AT_SYSTEM_BOUNDARY_PASS

scripts/test_at_profile_elab.sh
  AT_PROFILE_SELECTOR_PASS
  AT_PROFILE_ELAB_PASS

scripts/test_at_bios_first_fetch.sh
  AT_BIOS_FIRST_FETCH_PASS, opcode=EA

scripts/test_at_landmark_keyboard.sh
  cases 19/20: LANDMARK_KEYBOARD_PASS
```

No se ha ejecutado Quartus ni se ha generado un RBF.

## Prueba en MiSTer

1. Sintetizar el perfil AT con este commit y dar al RBF un nombre nuevo.
2. Montar una imagen válida en **Floppy A:**. Para reproducir la simulación se
   puede usar una imagen de 1,2 MiB; una imagen de 1,44 MiB también debe entregar
   su propia geometría por `hps_ext`.
3. Seleccionar **Write Protect: None** para permitir pruebas posteriores de
   escritura. Las dos pruebas de lectura no necesitan modificar la imagen.
4. Cargar la ROM Landmark AT parcheada y reiniciar el core.
5. Comprobar en el mismo pase **FLOPPY ADAPTER PASSED** y
   **FLOPPY READ PASSED**.
6. Si sólo falla la lectura, anotar el tamaño exacto de la imagen montada y
   capturar la página de debug durante el fallo. Las señales decisivas serán
   DRQ2, DACK2, TC, IRQ6, dirección DMA y `byte_enable`.

## 2026-10-04 escritura de sectores pendiente de corregir

El usuario detecta corrupción tras COPY y desmontar/remontar el disquete:
desaparecen también los archivos anteriores. Las lecturas funcionan y el
core PCXT-EGA escribe correctamente.

La [investigación de escritura DMA](AT_FLOPPY_WRITE_CORRUPTION_20261004.md)
identifica por inspección una respuesta de RAM consumida por el FDC un ciclo
después de perder validez, con selección de byte derivada de la dirección DMA
ya adelantada. La ruta actual puede entregar ceros al FIFO de escritura.
Este defecto de integración existe en código anterior a P06.

La verificación histórica de esta nota cubría lectura de sectores y escritura
de puertos/comandos. La corrección del payload y su prueba dirigida de sector
RAM a FDC, lectura posterior y remontaje siguen pendientes. Esta actualización
documenta el hallazgo; no modifica RTL ni acredita una corrección probada.
