# IBM AT 8042 y diagnóstico Landmark

Fecha: 2026-09-12

## Alcance y causa raíz

La revisión se hizo sobre la ruta AT. El controlador XT no se modificó porque
su teclado usa el enlace serie KFPS2KB/PPI y no representa el protocolo de host
del 8042 de un IBM 5170.

La ROM `Supersoft_Landmark_1.2.0_AT_5170_SKIP_PM_V2_64K.BIN` ejecuta dos
secuencias relevantes:

* `F000:9191`, **U126 KEYBOARD CONTROLLER**: envía `AAh` a `64h`, exige `55h`
  en `60h`, envía `ABh` a `64h` y exige `00h` en `60h`.
* `F000:91C0`, **KEYBOARD SCAN LINES**: envía `60h` a `64h`, escribe `44h` en
  `60h` como nuevo byte de mando y comprueba durante dos ventanas que `OBF`
  (estado bit 0) permanezca a cero.

El RTL anterior contestaba `AAh`, pero no implementaba `ABh`. Por eso U126
agotaba siempre la espera de respuesta y entraba en el manejador de fallo de
Landmark. Tampoco implementaba la fase de parámetro de `60h`: el valor `44h`
escrito después en el puerto de datos se descartaba.

Había además una fuente determinista de intermitencia condicionada por el
estado anterior de HPS: `hps_io` conserva y alterna `ps2_key[10]` con cada
evento, mientras el detector AT forzaba su copia histórica a cero durante
reset. Si el nivel conservado era uno, al liberar reset se fabricaba un evento
de teclado y el 8042 levantaba `OBF`. El detector ahora sigue el nivel de HPS
también durante reset, por lo que no reproduce como nuevo un evento anterior.
Una pulsación real durante la prueba puede seguir levantando `OBF`, como debe
hacer el hardware.

## Comparación comprobada

| Operación | IBM PC AT | RTL anterior | ao486/z486 | 86Box | RTL corregido |
|---|---|---|---|---|---|
| `20h` leer byte de mando | Respuesta en buffer de salida | Sí | Sí | Sí | Sí |
| `60h` escribir byte de mando | Siguiente escritura a `60h` es el parámetro | No | Sí | Sí | Sí |
| `AAh` autoprueba | `55h`, activa system flag | `55h`, flag fijo | `55h` | `55h` | `55h`, flag activo |
| `ABh` prueba de interfaz | `00h` sin error | Sin respuesta | `00h` | `00h` | `00h` |
| `ADh/AEh` | Deshabilitar/habilitar interfaz | Estado privado | Sí | Sí | Estado y bit 4 del byte de mando |
| `C0h` leer puerto de entrada | Imagen de configuración 5170 | No | Valor fijo `80h` | Modelo de P1 | `A0h`: interfaz no inhibida, EGA/color, jumper ausente, 512 KiB planar |
| `D0h/D1h` | Leer/escribir puerto de salida | Sólo escritura | Sí | Sí | Lectura y escritura |
| `E0h` leer T0/T1 | Estado de reloj/datos | No | No usado | Modelo fijo | `03h`, ambas líneas decodificadas en reposo alto |
| Estado bit 4 | Interruptor físico de inhibición | Confundido con enable interno | Fijo según modelo | Modelo de P1 | Uno: interruptor abierto |
| Estado bit 3 | Última escritura fue comando/dato | Siempre cero | Sí | Sí | Sí |
| Estado bit 2 | System flag | Siempre uno | Sí | Sí | Cero al reset; `AAh` o byte de mando lo actualizan |

Las referencias de implementación se consultaron en:

* IBM Personal Computer AT Technical Reference, sección del controlador de
  teclado y tablas de puertos/comandos:
  <https://ftpmirror.your.org/pub/misc/bitsavers/pdf/ibm/pc/at/6183355_PC_AT_Technical_Reference_Mar86.pdf>
* `D:/GitHub/ao486_MiSTer/rtl/soc/ps2.v`.
* `D:/GitHub/z486_MiSTer/src/soc/ps2.v`.
* `D:/GitHub/86box_dev/src/device/kbc_at.c`.

ao486 y z486 contienen prácticamente el mismo controlador PS/2 y confirman
las respuestas que usa Landmark. 86Box confirma de forma independiente
`ABh -> 00h` y el tratamiento de `60h` como una orden con parámetro.

## Señales observadas en simulación

El caso 19 ejecuta los bytes originales desde `F000:9191` y, tras la
corrección, observa:

```text
OUT 64h,AAh
IN  64h     -> 1Dh (OBF=1, system=1, command=1, inhibit switch=1)
IN  60h     -> 55h
OUT 64h,ABh
IN  60h     -> 00h
F000:9CB5   -> manejador PASS
```

El caso 20 ejecuta los bytes originales desde `F000:91C0`:

```text
OUT 64h,60h
IN  64h     -> 18h (command=1, espera parámetro)
OUT 60h,44h
IN  64h     -> 14h (system=1, command=0, OBF=0)
F000:9CB5   -> manejador PASS
```

El arnés acorta sólo los contadores de espera, sin cambiar comandos,
comparaciones ni destinos PASS/FAIL. Para que los `CALL` de ambas rutinas sean
reales, el selector aislado prepara `SS:SP=0000:0800`; la versión anterior
intentaba guardar las direcciones de retorno en la ventana ROM F000.

## Cambios de interfaz y límites

No cambia ningún puerto de módulo ni el protocolo request/accept/ready del
chipset. La prioridad del buffer impide que un evento HPS simultáneo sustituya
la respuesta interna de un comando del 8042.

En esta revisión del 12 de septiembre, la entrada física AT aún recibía
directamente el código de ocho bits de `hps_io`, sin convertir los indicadores
make/break/extended (`ps2_key[9:8]`). Esto no intervenía en las dos pruebas de
controlador, pero impedía escribir correctamente. La conversión de eventos y
la cola de entrada se completan en la revisión del 13 de septiembre descrita
en [AT_HPS_KEYBOARD_INPUT.md](AT_HPS_KEYBOARD_INPUT.md). El diálogo de comandos
con un teclado físico sigue siendo un alcance distinto.

## Verificación

```text
scripts/test_a5_at_devices.sh
  Icarus:   A5_AT_DEVICES_PASS
  Verilator:A5_AT_DEVICES_PASS

scripts/test_at_landmark_keyboard.sh
  case 19: LANDMARK_KEYBOARD_PASS, F000:9191, AA/55 y AB/00
  case 20: LANDMARK_KEYBOARD_PASS, F000:91C0, 60/44 y OBF=0
```

No se ha ejecutado Quartus ni se ha generado un RBF.

## Prueba en MiSTer

1. Sintetizar el perfil AT con este commit y asignar al RBF un nombre nuevo.
2. Cargar `Supersoft_Landmark_1.2.0_AT_5170_SKIP_PM_V2_64K.BIN`.
3. No pulsar teclas durante **KEYBOARD SCAN LINES**.
4. Confirmar que **U126 KEYBOARD CONTROLLER** y **KEYBOARD SCAN LINES** muestran
   `PASSED` en el mismo pase.
5. Después del diagnóstico, comprobar una pulsación y su IRQ1 por separado;
   esa prueba evalúa la ruta física pendiente, no las órdenes internas U126.
