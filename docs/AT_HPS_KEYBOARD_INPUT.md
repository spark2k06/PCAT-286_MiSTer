# Entrada de teclado HPS en AT

Fecha: 2026-09-13

## Causa comprobada

Con `xtsergey_mod_at.rom`, A se interpretaba como Enter y B como M, con dos
caracteres por pulsación/liberación. `hps_io` entrega código set 2 en
`ps2_key[7:0]`, extended en bit 8, pressed en bit 9 y alternancia de evento en
bit 10. La conexión AT anterior reenviaba sólo los ocho bits inferiores:

| Tecla | Evento HPS (set 2) | Interpretación incorrecta como set 1 | Salida corregida: pulsar / soltar |
|---|---|---|---|
| A | 1Ch | Enter | 1Eh / 9Eh |
| B | 32h | M | 30h / B0h |
| Enter | 5Ah | Código distinto | 1Ch / 9Ch |

Como el código inferior es igual al pulsar y al soltar, perder el bit 9
generaba el segundo carácter. La BIOS no puede recuperar esa información
después de que el core la descarte.

La tabla set 2 -> set 1 se contrastó con `nont_to_t` de
`D:/GitHub/86Box_dev/src/device/kbc_at.c`. El camino XT ya aplica esa conversión
a las teclas habituales en `KFPS2KB.sv`. Se usa el protocolo del 8042 AT; no
se incorpora el PPI XT.

## Implementación

`spk286_at_keyboard.sv` transforma eventos HPS en secuencias de bytes según
el bit 6 del byte de mando del 8042. Con la traducción activada emite set 1
y su bit de liberación; desactivada reconstruye set 2 con prefijos F0/E0.
También reconstruye las secuencias Print Screen y Pause que `hps_io` compacta.

Una FIFO de 32 eventos retiene las pulsaciones y liberaciones mientras la
BIOS atiende el búfer de salida. El acuerdo `keyboard_byte_valid/ready`
impide perder los bytes siguientes de una secuencia extendida mientras OBF
está ocupado. AD inhibe el envío y AE lo reanuda. Las respuestas internas del
8042 conservan prioridad y no pasan por la tabla de traducción.

El reset vacía la cola y cualquier secuencia parcial, pero sigue el nivel del
bit de evento HPS para evitar reproducir una tecla antigua. El desbordamiento
no sobrescribe entradas antiguas: descarta el nuevo evento y activa una señal
persistente, visible en el indicador B de error de debug y LED_USER hasta reset.

El módulo se incorpora en `spk286_integration.qip`, incluido por
`PCAT-286_AT_FAST.qsf` y `PCAT-286_AT.qsf`. El camino XT no cambia.

## Verificación

* `bash scripts/test_at_keyboard.sh`: Icarus y Verilator, 102 lecturas
  verificadas, letras, make/break, Shift, Ctrl derecho, flechas, Enter de
  teclado numérico, F7, Print Screen, Pause, traducción desactivada, OBF
  ocupado, inhibición, respuestas del controlador, reset y desbordamiento.
* `python scripts/test_xtsergey_at_keyboard.py --scan-trace build/at-keyboard/scan_trace.txt`:
  reproduce los bytes realmente leídos del 8042 simulado en la IRQ1 y la
  INT 16h de la ROM. Resultado exacto: `abA` y Enter, sin duplicados. Es una
  prueba de rutinas x86 con Unicorn, no una simulación completa de SPK286.
* `bash scripts/test_a5_at_devices.sh`: regresión de dispositivos AT pasa en
  Icarus y Verilator, incluyendo los comandos del 8042 usados por Landmark.
* `bash scripts/test_at_profile_elab.sh`: integración del perfil AT correcta.
  Se actualiza su lista de fuentes de simulación con IDE y el modelo de su
  RAM, dependencias que faltaban desde la incorporación de XT-IDE.

La ROM de 64 KiB `SW/ROMs/xtsergey_mod_at.rom` no cambia en esta revisión.
Su suma de bytes módulo 256 sigue siendo 00h, su byte final es 6Ah y su SHA-256
es `D023FD7B2777845775C78F0A149CA379ABA2A4BFF61D057BD184731691897624`.

Queda la validación en placa: recompilar AT_FAST, cargar el RBF nuevo y la
misma ROM, y escribir `ab`, Shift+A y Enter. No se ha ejecutado Quartus ni
86Box. El diálogo de comandos de dispositivo físico (LEDs, typematic, etc.)
no se amplía en este cambio.

## Cursores con teclado AT 101 (ANSI) — 2026-09-28

La configuración que funciona en 86Box usa el teclado **101 (ANSI)**. Ese
modelo entrega las teclas de navegación como `E0` más el código de cursor;
eliminar `E0` no reproduciría esa configuración. La comparación con
`D:/GitHub/86box_dev/src/device/keyboard_at.c` y `keyboard.c` mostró
diferencias en el modelo de teclado. El ejecutable facilitado de *Prince of
Persia* 1.3 (SHA-256 `1315BBF282C85A5D014FF4EF24B3A015F639A503044B43ABE17FE0A33E55341D`)
mostró además la causa directa del fallo con cursores:

* Su IRQ1 lee `60h` y luego encadena la IRQ1 del BIOS, que vuelve a leer ese
  puerto. El adaptador ponía el segundo byte de `E0 48` en el buffer del 8042
  inmediatamente después de la primera lectura. La lectura encadenada podía
  consumir `48h` antes de que la IRQ1 del juego lo viera. Con el numérico solo
  llegaba un byte y no había esa carrera.

* El comando `F2h` no contestaba. En 86Box el teclado AT 101 responde
  `FAh ABh 83h`; la identificación permite a la BIOS detectar el teclado
  ampliado.
* El core emitía solo `E0` y el código de navegación. 86Box añade eventos
  temporales de Shift alrededor de Home, cursores, PgUp/PgDn, Insert y Delete
  cuando Num Lock o Shift lo requieren. El teclado actualiza Num Lock con el
  parámetro del comando de LEDs `EDh`, que el core tampoco atendía.

Ahora el 8042 virtual responde a `F2h` y a las dos fases de `EDh`. El adaptador
usa el estado de Num Lock y de ambos Shift para emitir las mismas secuencias
de navegación del teclado 101 en set 1 traducido y set 2 sin traducir. Las
teclas del bloque numérico siguen usando sus códigos originales y no reciben
los eventos temporales de Shift. El 8042 espera además un intervalo equivalente
a un byte PS/2 (1 ms a 50 MHz) tras consumir un byte de teclado antes de
presentar el siguiente. No se añade ningún modo de teclado al OSD.

`scripts/test_at_keyboard.sh` comprueba ambas simulaciones, la identidad
`FA AB 83`, el cambio de LEDs, los códigos con Num Lock/Shift y la doble
lectura de IRQ1 de Prince. Esa prueba falló antes de introducir la espera y
pasó después. También pasan
`scripts/test_a5_at_devices.sh`, `scripts/test_at_profile_elab.sh` y ambas
variantes de `scripts/test_at_mrbios_restart.sh`. Queda por comprobar Prince
en placa con la BIOS usada por el usuario.
