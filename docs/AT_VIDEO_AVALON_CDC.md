# CDC de vídeo y Avalon — implementación y verificación

Fecha: 24 de septiembre de 2026. Rama: `beta-04`.

**Estado actualizado: los CDC intervenidos cumplen tras el fit del usuario;
el timing global sigue abierto.** Existe un RBF nuevo. Véase el
[resultado del fit](AT_VIDEO_AVALON_CDC_FIT_20260924.md) para slacks, recursos,
rutas restantes y procedencia del binario.
La corrección anterior del recorte HDMI está en `497cf49`; Sound Blaster, en
`120f67d`.

## Referencia antes del cambio

Se conservó el fit que había en `output_files` y se reanalizó con sus fuentes y
restricciones congeladas, sin ejecutar síntesis ni Fitter:

`build/at-cdc-avalon/20260924-reference/`

`timing/` contiene el análisis general por esquina. `focused-v2/` contiene las
cuatro familias concretas. El fit es el que aportó el usuario; no se supone que
su netlist corresponda al HEAD actual. El manifiesto de la copia conserva la
procedencia de fuentes y resultados.

| Familia | Setup anterior, Slow 1100 mV / 100 °C | Después |
|---|---:|---|
| `o_ibuf1` → `avl_i_offset1` | −6,948 ns | Banco coherente +6,949 ns; comando de escritura +1,657 ns |
| `o_ibuf0` → `avl_i_offset0` | −6,908 ns | Banco coherente +6,949 ns; comando de escritura +1,657 ns |
| `o_adrs` → `avl_radrs` | −6,849 ns | Payload de lectura +1,849 ns |
| `ega_gfx.misc_reg` → `vga_packed_memory_sync1_q` | −6,893 ns | Decode registrado +31,326 ns; etapa 1→2 +18,666 ns |

La columna posterior corresponde a las rutas de la nueva arquitectura y usa
el peor slack de las cuatro esquinas, no a un cambio de excepción sobre la
misma ruta. La llegada asíncrona a la primera etapa se excluye según se justifica
más abajo; las etapas síncronas y los payloads acotados sí se analizan.

En la referencia también existen violaciones ajenas a estas cuatro familias:
por ejemplo CPU interna (−3,907 ns en esa esquina), `HDMI_shadowmask` y controles
de geometría. Resolver estos CDC no acredita el cierre global del proyecto.

## Clasificación y solución

### Bancos del escalador

`o_ibuf0/1` y `o_obuf0/1` se asignan en el reloj HDMI. Aunque cambian con poca
frecuencia, el receptor Avalon es asíncrono. Muestrear continuamente el banco y
sumar su base a una petición pendiente permitía mezclar la dirección de una
petición con el banco del siguiente cuadro.

En `AT_CDC`, el par de bancos de captura llega de forma coherente al reloj de
entrada mediante `capture_bank_config` (payload retenido y request/ack). La
asignación ocurre en VS; debe completarse durante el blanking antes de la primera
escritura del cuadro siguiente. Se conserva esa condición de funcionamiento del
escalador. El historial de campos y entrelazado vuelve mediante
`capture_field_history`.

Cada escritura congela dirección, base de banco y selección del buffer de burst
junto al toggle. Avalon los captura juntos una sola vez. La cola y la capacidad
de los buffers de datos son las originales: no se promete soportar esperas
ilimitadas de DDR mientras sigue entrando vídeo.

### Lecturas HDMI → Avalon

La dirección es un bus asociado a un evento, no un conjunto de bits que puedan
sincronizarse por separado. Se congelan `o_read_address_q` y `o_read_base_q` al
emitir la petición. Permanecen estables hasta que vuelve el acuse de aceptación
Avalon. `o_read_pending` impide sobrescribirlos incluso si la máquina de salida
se reinicia en VS antes de recibir ese acuse.

El receptor captura ambos registros tras el toggle sincronizado y calcula
`avl_address` a partir de su copia local. La dirección permanece estable durante
`waitrequest`. La base del framebuffer externo se toma en VS en el dominio HDMI
y viaja con la petición; se elimina la copia independiente hacia Avalon.

Los eventos de petición, aceptación, datos y fin de cuadro pasan por dos etapas;
la detección de flancos utiliza la segunda y un registro adicional de historial.
La primera etapa ya no alimenta los detectores de eventos en `AT_CDC`.

### Selección VGA empaquetada/planar

El destino ya tenía dos registros, pero el origen era una decodificación
combinacional de varios registros gráficos. Se registra primero el resultado
en `clk_video` y después se sincroniza el nivel hacia CPU. La escritura de E/S
que cambia el modo atraviesa el mailbox existente; su acuse deja tiempo para
que la selección llegue antes del siguiente acceso de CPU a VRAM.

## Restricciones justificadas

- Se excluye únicamente la llegada asíncrona a la primera etapa de cada
  sincronizador identificado. Las rutas de primera a segunda etapa conservan
  setup y hold normales.
- Los payloads retenidos tienen `set_max_delay`, no una exclusión completa.
  Los comandos usan 10 ns; el historial de campos, 5 ns.
- Se excluye hold exclusivamente en esos payloads asíncronos: su estabilidad
  viene del protocolo, no de una relación fija entre fases de reloj.
- En Quartus 17, `set_max_delay` incluye las latencias de las redes de reloj.
  El informe posterior debe verificar también el retardo real de datos frente
  a la ventana de captura; no basta con que desaparezca la ruta antigua.
- Las escrituras mantienen el payload un mínimo de seis ciclos de entrada
  (104,8 ns a 57,272 MHz). La captura requiere dos etapas, detección y registro
  de payload: aproximadamente 30–40 ns a 100 MHz, más la eventual resolución
  del sincronizador. Las lecturas lo retienen hasta el acuse de aceptación.

Este tratamiento distingue sincronizadores y buses retenidos, conforme a las
[guías de CDC de Intel](https://www.intel.com/content/www/us/en/docs/programmable/683243/25-1/constraining-cdc-paths.html).
La sintaxis utilizada se comprobó con la ayuda de Quartus 17.0.2, que es la
versión del proyecto; no se han aplicado opciones exclusivas de Quartus Pro.

## Verificación ejecutada

| Prueba | Resultado |
|---|---|
| `scripts/test_at_scaler_avalon.sh`, progresivo | 185 lecturas, 240 bursts de escritura, 826 ciclos de espera |
| Mismo test, entrelazado y fase HDMI desplazada 3 ns | 202 lecturas, 240 bursts de escritura, 827 ciclos de espera |
| Scoreboard de comandos reales | Dirección/banco correctos; ningún comando perdido o duplicado; colas vacías al acabar |
| Estabilidad | Payload de lectura retenido hasta acuse; dirección y datos Avalon estables durante esperas |
| Cobertura | Bancos 0/1/2; framebuffer `24000000h`/`24800000h`; stop/run; pausa de reloj HDMI |
| Ventana observada | Captura mínima 30,070 ns; separación mínima de escrituras 1.676,160 ns en estos estímulos |
| `scripts/test_at_video_window.sh` | 640 píxeles sin recorte en texto 200/350 y gráficos 200, offsets 0/6 |
| Mismo test, memoria VGA | Readback `A5h` empaquetado y `3Ch` planar conservados tras 16 cambios de GC06 |
| `scripts/test_at_cdc.sh` | Snapshot, OSD, métricas, PLL y elaboración VHDL 93/2008: PASS |

La simulación conserva las comprobaciones de rangos de GHDL. Se evita un valor
natural negativo en `o_pshift` cuando el offset es cero, caso en que no se hace
desplazamiento. Los estímulos habilitan la salida después de conocer la
geometría, como hace la configuración del sistema. Estas pruebas digitales no
simulan metastabilidad ni sustituyen al fit o a la comprobación en placa.

## Reproducción del análisis

Compilar la revisión `PCAT-286` con el `PCAT-286.qsf` de esta carpeta. No hace
falta añadir fuentes al proyecto. Tras el fit, el análisis específico se ejecuta
desde la raíz del repositorio:

```text
quartus_sta -t scripts/report_at_video_avalon_timing.tcl PCAT-286 build/at-cdc-avalon/candidate-timing
```

La carpeta de salida debe ser nueva. El script comprueba que existan los nuevos
extremos, que hayan desaparecido los offsets asíncronos antiguos y que las rutas
requeridas sigan siendo analizadas. Exporta setup, hold, recovery, removal,
FMax, excepciones y rutas no restringidas para las cuatro esquinas. Una colección
vacía no cuenta como éxito. `timing_open=1` mantiene abierto el cierre cuando
faltan rutas requeridas o hay slacks negativos.

La revisión de payloads, sincronizadores, lógica Avalon, excepciones y recursos
está recogida en el informe del fit. Quedan las violaciones globales allí
identificadas y la prueba de vídeo/framebuffer en placa. El RBF generado por la
compilación del usuario está en `output_files/PCAT-286.rbf`.
