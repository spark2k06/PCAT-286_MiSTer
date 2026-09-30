# Integración de la EGA de PCAT en 86Box — 30/09/2026

## Objetivo

Separar el comportamiento de la EGA del resto del equipo al investigar la
pantalla negra de OS/2 1.3. Primera combinación: CPU 286 nativa de 86Box y EGA
RTL de PCAT. Control: la misma CPU y la EGA IBM nativa de 86Box.

La implementación está en `D:\GitHub\86Box_dev`, rama
`codex/pcat-ega-backend`. Su descripción y comandos están en
`D:\GitHub\86Box_dev\docs\PCAT_EGA_BACKEND.md`.

## Cambios en este repositorio

Se añade la selección de compilación `PCAT_EGA_ONLY` en:

- `rtl/video/ega_top.v`: excluye los módulos VGA+ y el splash de MiSTer.
- `rtl/spk286_integration/spk286_at_video_adapter.sv`: excluye el framebuffer
  empaquetado VGA+.

El wrapper de simulación mantiene `vga_enabled=0` y `splashscreen=0`.
La compilación normal de la FPGA no define esta selección y conserva los
módulos habituales. Estos cambios no corrigen ni sustituyen el comportamiento
de registros, memoria o renderizado de la EGA.

Se reutilizan el adaptador AT, sus cruces de reloj, el frontend de VRAM y los
controladores y pipelines EGA. La lista de fuentes del modelo no contiene
módulos `vga_*.v`. `ega_vgaport.v` sí se incluye: convierte los colores EGA a RGB.

## Perfil y observación

MR BIOS 286, CPU nativa a 6 MHz, 4 MiB, EGA de 256 KiB, monitor ECD y una copia
privada de `D:\ISOs\MiSTer\IBM_OS2.vhd`. Lanzador:

`D:\GitHub\86Box_dev\build\pcat-ega\Run-PCAT-EGA-OS2.cmd`

También están preparados los perfiles separados a 25 MHz utilizados para la
comparación, con el ajuste de oscilador de la BIOS guardado:

- `Run-PCAT-EGA-OS2-25MHz.cmd`: CPU nativa y EGA RTL.
- `Run-Native-EGA-OS2-25MHz.cmd`: CPU nativa y EGA IBM nativa.

Ambos están en `D:\GitHub\86Box_dev\build\pcat-ega\` y tienen copias privadas
del VHD. La frecuencia de la CPU se indica en el título de esos lanzadores.

Se guardan todos los accesos a puertos de la EGA con CS:IP y tiempo simulado,
un histórico de accesos a VRAM, los registros reales del RTL, cuatro planos de
64 KiB y la imagen RGB. Las inspecciones no leen puertos ni alteran el flip-flop
del controlador de atributos o los latches de VRAM.

Los relojes del modelo son 50 MHz para el adaptador AT y 315/11 MHz para EGA,
independientes de los 6 MHz elegidos para la CPU. Avanzan también durante las
esperas de la CPU. La integración usa transacciones de 86Box por instrucciones;
no representa el cierre de tiempos de FPGA, la metastabilidad física, el
arbitraje de SDRAM ni la salida/scaler de MiSTer.

El primer POST detectó un cambio de configuración de vídeo. MR BIOS guardó
en su NVRAM el cambio de 1Bh=78h a 79h y actualizó los checksums. Ese archivo
guardado por la propia BIOS se ha utilizado para el perfil RTL. El siguiente
arranque pasó el POST y entró en OS/2 sin pedir una tecla.

## Pista adicional: lecturas de registros

Se observa una diferencia estática concreta, todavía sin relación causal
demostrada con la pantalla negra:

- `86Box/src/video/vid_ega.c`, función `ega_in`, devuelve FFh para lecturas
  de atributos, secuenciador y controlador gráfico en la **IBM EGA**. Sus
  ramas que devuelven registros se habilitan para `EGA_TYPE_OTHER`.
- `rtl/video/ega_top.v` enruta lecturas de 3C1h, 3C5h, 3CCh y 3CFh hacia los
  registros de atributos, secuenciador, miscellaneous output y gráficos,
  también con `vga_enabled=0`.
- El multiplexor de salida de PCAT devuelve 00h para puertos sin selección
  interna dentro de la ventana del adaptador; el valor por defecto de
  `ega_in` es FFh.

Esta diferencia podría afectar a una rutina de detección o guardado/restauración
de estado. Hay que identificar primero si OS/2 lee esos puertos, qué comprueba
y qué camino sigue. No basta con encontrar la diferencia para atribuirle el
bloqueo, ni se ha validado aquí la documentación eléctrica de una EGA real.
La prueba conserva esas respuestas de PCAT para que puedan observarse.

## Hallazgo reproducible: decodificación de la ventana de VRAM

El programa pequeño `86Box/tools/pcat_ega/probe_decode.cpp` usa el mismo archivo
de biblioteca RTL que el ejecutable. No necesita BIOS, CPU ni disco. Configura
acceso secuencial al plano 0, modo de escritura 0, máscara FFh y RAM habilitada.

Con GDC[6]=0Dh, la ventana seleccionada es B8000h..BFFFFh. El resultado es:

```text
write[B8000]=5A
read[A0000]=5A read[A8000]=5A read[B0000]=5A read[B8000]=5A
write[B0000]=A5
read[B8000]=A5
```

Por tanto, un acceso fuera de la ventana seleccionada llega a la misma VRAM;
también una escritura externa altera su contenido. No es solo una lectura de
bus abierto. La salida completa está en
`86Box/build/pcat-ega/probe-decode.txt`.

La ruta que lo permite es:

1. `spk286_at_video_adapter.sv`, `video_memory_request`, acepta A0000h..BFFFFh
   completo, sin comprobar `ega_mem_map_sel`.
2. `ega_vram_bram_frontend.sv` convierte esa petición en `cpu_mem_select`.
3. `ega_vram.v`, `remap_cpu_addr`, en mapas 2 y 3 enmascara con 7FFFh; no
   rechaza la dirección original. Las escrituras se confirman con selección,
   write-enable y máscara de planos.

En cambio, `86Box/src/video/vid_ega.c`, escritura de GDC[6], cambia el rango
publicado por `mem_mapping_set_addr` según la ventana seleccionada. Ese filtro
es distinto de la conversión posterior de dirección dentro de VRAM. Haber
copiado la conversión de dirección no sustituye el filtro de selección.

El sondeo confirma además 3BAh=00h con selección de puertos de color, así como
la lectura de los registros SEQ[4]=06h, miscellaneous=03h y GDC[6]=0Dh.
Estas respuestas son observaciones del RTL, sin atribuir aún una causa a OS/2.

## Observación de la BIOS: segunda tarjeta monocroma

En `trial-rtl-20260930-140732`, la pantalla de configuración de MR BIOS muestra
`Video-Primary V/EGA-Color` y `Video-Secondary Monochrome`. El perfil solo
configura `pcat_ega`; no existe una segunda tarjeta.

Captura: `86Box/build/pcat-ega/trial-rtl-20260930-140732/screenshots/`,
archivo `Monitor_1_1260830-141354-798.png`.

El alias de B0000h y las respuestas a puertos inactivos son candidatos concretos
para esa detección errónea. Falta identificar la prueba exacta de MR BIOS y
demostrar cuál la provoca; no se da por demostrado que sea la causa de la
pantalla negra de OS/2.

## Control de arranque y alcance de la evidencia

- `trial-native-20260930-141410`: CPU nativa 286 a 25 MHz, 4 MiB y EGA IBM
  nativa; OS/2 llega a Desktop Manager y al grupo Main. Capturas a los 15 y
  45 segundos de pared muestran el escritorio; salida del proceso 0.
- `trial-rtl-20260930-140732`: misma CPU a 25 MHz, 4 MiB y EGA RTL. La prueba
  ha cargado HPFS, completado CHKDSK y cargado los drivers de ratón. Después
  permanece en una pantalla negra. Los relojes de la EGA permanecen a
  50 MHz y 315/11 MHz. Terminó a las 14:32:36 con salida 0, tras 25 minutos
  de pared y unos 68 segundos invitados, incluyendo el tiempo en la BIOS.
- La BIOS pidió aceptar el cambio de oscilador de 6 a 25 MHz. Se registraron
  Enter y F10 en su buffer de teclado para guardar esa configuración; los
  archivos `bios-key.json` y `bios-f10.json` documentan esa intervención.
- Ejecutable inmutable de ambas pruebas:
  `95555427a5e0eeaf9466fb722bd5a65da8132f2cb6e942d765d8974dfb1df93c`.
- Imagen fuente original:
  `a51986db0a63ce8ab64a18b91c6ee6d96ea79c225fd6ca63b2898f6befcc6c2f`.
  Se usa una copia desechable distinta por ejecución.
- El binario combinado SPK286 + EGA RTL también compila y enlaza. Su arranque
  completo de OS/2 no se ha validado en esta sesión.

Una ejecución anterior (`trial-rtl-20260930-134907`) coincidió con una
reconstrucción del ejecutable que tenía abierto. Se excluye como comparación
controlada. El lanzador de pruebas ahora copia el binario antes de ejecutarlo.

Los hallazgos de decodificación y lecturas se han documentado sin corregirlos
en este paso: la integración debe permitir observar el comportamiento actual
de PCAT. No se ha lanzado una regresión general de SPK286 ni una síntesis FPGA.

## Pantalla negra con CPU nativa: estado observado

La captura válida `capture-20260930-142827-761220` del ensayo RTL contiene
los 4 MiB de RAM, registros nativos y tablas de segmentos. Se ha tomado
deteniendo brevemente ese proceso, leyendo su memoria y reanudándolo, sin
modificar RAM ni registros invitados. Los offsets se obtuvieron de `cpu.h`
con las opciones de esta compilación; tamaño de `cpu_state_t`: 416 bytes.

Estado: CS=01F8h, base=00001F80h, PC=3326h, oldpc=332Fh, CR0=000Dh,
sin excepción pendiente en `cpu_state.abrt`. El tramo observado contiene:

```text
01F8:3326  sti
01F8:3327  call 2CC6h
01F8:332A  test byte [0ED4h],FFh
01F8:332F  jz 3326h
```

La subrutina 2CC6h consulta una bandera en el segmento 0BF0h y retorna en
la ruta observada. Es una espera dentro de OS/2; este tramo no contiene un
sondeo de puertos EGA. Todavía falta identificar qué evento o tarea debe
despertarlo y qué error previo impide hacerlo.

Los snapshots periódicos muestran:

- ATC `video_enable_reg=0`: la salida negra coincide con vídeo deshabilitado
  en el propio RTL.
- Contadores de acceso fijos en 2322858 transacciones y 21312 accesos de I/O,
  mientras avanzan TSC y el contador de cuadros.
- Último I/O: `04AE:13A0`, escritura 02h en 3C4h, después de programar GDC[6]
  a 05h y GDC[8] a FFh. El CS:IP de la traza corresponde al punto del callback
  de 86Box, no necesariamente al primer byte de la instrucción.
- Últimas escrituras de VRAM registradas: `04AE:13EF`, ceros en A6Dxxh.

Al cerrar: CS:IP=01F8:332Fh, TSC=1698800004, 4013 cuadros. Desde el último
acceso a la EGA hasta el cierre transcurrieron 19,6 segundos invitados sin
actividad nueva de vídeo. Se conserva ese intervalo acotado como evidencia;
no se ha esperado indefinidamente. El SHA-256 de la imagen fuente fue idéntico
antes y después de ambos ensayos.

La combinación con CPU nativa reproduce por tanto el síntoma visible sin
necesitar SPK286. Esto centra la investigación en la ruta EGA y su integración;
no demuestra por sí solo que la causa exacta sea idéntica a la del hardware,
ni que el alias de ventanas sea el responsable de esta espera.

Evidencia compacta conservada en `docs/evidence/pcat-ega-86box-20260930/`.
Los discos, RAM completa y trazas extensas permanecen en el directorio local
de la prueba en `86Box/build/pcat-ega/`.

## Correcciones funcionales aplicadas después de la comparación

Aplicadas por petición del usuario para la siguiente síntesis de hardware:

- El adaptador AT decodifica las cuatro ventanas de GDC[6] antes de entregar
  un acceso al frontend de VRAM: A0000–BFFFF, A0000–AFFFF, B0000–B7FFF y
  B8000–BFFFF. Fuera de ellas completa la transacción con FFh en lectura e
  ignora la escritura, sin tocar los latches ni generar un evento de escritura
  de vídeo. Respeta además Miscellaneous Output[1], habilitación de RAM.
- El índice de GDC, selección de ventana y habilitación de RAM se mantienen
  en el dominio AT a partir de los OUT aceptados. La finalización del buzón
  garantiza que el OUT anterior llegue al vídeo antes del siguiente acceso a
  memoria. Esos campos siguen el reset del vídeo, que puede ser distinto del
  reset de CPU, y su liberación tiene sincronización en el dominio AT.
- El adaptador respeta `bus_dir`: los puertos no seleccionados devuelven FFh.
  En particular, el puerto de estado monocromo permanece sin responder cuando
  Miscellaneous Output selecciona los puertos de color, y viceversa.
- En modo EGA se restringen las lecturas de registros como en la IBM EGA de
  `86Box/src/video/vid_ega.c`, `ega_in`: secuenciador, gráficos, atributos y
  miscellaneous output no se leen; CRTC conserva lectura de 0Ch–0Fh. Las
  lecturas de 10h/11h corresponden al lápiz óptico sin conectar, no a los
  registros de retrazado escritos en esas posiciones. Devuelven cero.
- El modo VGA opcional mantiene su lectura extendida de registros y su
  selección previa de memoria. No se han desarrollado funciones de VGA+.

La prueba acotada `scripts/test_at_ega_decode.sh` ha terminado con:

```text
EGA_DECODE_PASS checks=75 maps=4 boundaries=1 latches=1 ram_disable=1 ports=1 reset=1
```

Incluye primeros y últimos bytes de cada ventana, ambos carriles del bus,
lecturas/escrituras fuera de rango, conservación de los latches, habilitación
de RAM, puertos de solo escritura, CRTC legible, selección color/mono y
distinción entre reset de CPU y reset de vídeo. No añade esperas artificiales
entre los OUT y los accesos a memoria.

Se ha recompilado también el ejecutable de comparación con CPU nativa y EGA
RTL. El sondeo independiente, enlazado con su nueva biblioteca, confirma:

```text
map=3 write[B8000]=5A read[A0000]=FF read[A8000]=FF read[B0000]=FF read[B8000]=5A
map=3 write[B0000]=A5 then read[B8000]=5A
read port[3BA]=FF
read port[3C1]=FF
read port[3C5]=FF
read port[3CC]=FF
read port[3CF]=FF
```

Los resultados posteriores a la corrección se conservan en
`docs/evidence/pcat-ega-86box-20260930/decode-fix/`. La evidencia anterior de
este documento conserva su binario y fuentes originales como referencia.
El binario combinado SPK286 + EGA de la comparación inicial aún corresponde
a la versión anterior; el ejecutable actualizado es `build/pcat-ega/src/86Box`.

Al preparar la corrección, la configuración de síntesis estaba a 25 MHz con
depuración; esta corrección no modificó `config.tcl`. El arranque completo de
OS/2 en el ejecutable de comparación corregido continúa pendiente.

## Validación en hardware y aceptación

El 30/09/2026, después de sintetizar y probar las correcciones en MiSTer, el
usuario confirma: «Ha funcionado perfectamente!». Se registra como resuelto
el bloqueo de OS/2 observado en hardware para esta prueba y se solicita el
commit de los cambios.

Esta confirmación valida el conjunto de correcciones aplicado. No separa la
contribución individual del filtro de memoria y la de las lecturas de puertos.
Las 75 comprobaciones específicas y el sondeo anterior siguen siendo la
evidencia automatizada; no se ha repetido una regresión general para hacer
el commit.

En el momento de registrar esta aceptación, el `config.tcl` de trabajo ya
está en 50 MHz sin depuración (`SPK286_AT_NO_DEBUG` activo y DIV2 comentado).
La configuración y los cambios previos del observador se conservan aparte del
commit funcional de EGA.
