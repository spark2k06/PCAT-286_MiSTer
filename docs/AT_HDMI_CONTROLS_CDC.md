# Filtro adaptativo y retorno de VSYNC HDMI — 25/09/2026

## Estado y referencia

La tanda anterior está guardada en el commit `6aee2bf`
(`Fix AT video options and scaler configuration CDC`). Este candidato trabaja
sobre ese commit en `beta-04` y necesita un nuevo fit del usuario.

Referencia física: fit terminado a las 06:44, descrito en
`AT_SCALER_CONFIG_FIT_20260925_0644.md`, con fuentes y netlist congeladas en
`build/at-scaler-config/20260925-0644-fit/`.

| Ruta de partida | Peor setup |
|---|---:|
| `ascal.o_h_poly_adaptive → o_h_poly_use_adaptive` | −5,701 ns |
| `ascal.o_v_poly_adaptive → o_v_poly_use_adaptive` | −5,500 ns |
| `hdmi_out_vs → vs_d1` | −5,563 ns |
| `hdmi_out_vs → vsd` | −5,527 ns |
| `hdmi_out_vs → vs_d0` | −5,505 ns |

Estos valores corresponden al RTL anterior. Los slacks, FMax y recursos del
nuevo candidato sólo podrán medirse después de compilarlo. La ruta síncrona
HDMI `o_hsize → o_hacc_next` (−0,091 ns), vídeo directo, subportadora y las
violaciones CPU/SDRAM quedan pendientes de sus respectivos bloques.

## Filtro adaptativo: clasificación y solución

`Polikarpov` escribe las tablas y sus indicadores horizontal/vertical con
`poly_clk` (50 MHz). `PolyFetch` usaba esos indicadores directamente con
`o_clk` (HDMI). Son controles asíncronos que permanecen estables entre cargas,
pero pueden cambiar varias veces durante una carga normal/adaptativa.

El protocolo de referencia agrupa las tablas que necesita actualizar bajo
`UIO_SET_FLTCOEF`, termina con `DisableIO()` y permite actualizar sólo un eje.
Se revisó `send_video_filters()` de
[Main_MiSTer](https://github.com/MiSTer-devel/Main_MiSTer/blob/master/video.cpp),
incluida la copia local en el commit
`76e9b9acd8377a5ce0522f71214a659b3bde20ea`.

La implementación ahora:

1. Registra `coef_active` junto al strobe `coef_wr` de la transacción UIO 0x2A.
2. Conserva las escrituras de coeficientes en `poly_clk`, sin descartar ninguna.
3. Publica `{vertical, horizontal}` únicamente con la transacción cerrada,
   `poly_wr=0` y `poly_wr_mode=000`. Así incluye la última escritura y el último
   cambio de indicador de la tubería original.
4. Transfiere el par mediante `at_cdc_snapshot_vhd`, con petición/acuse y
   payload congelado hasta recibir el acuse.
5. Aplica el par capturado a `poly_adaptive_local` en el flanco final de VS
   interno, o durante el arranque con salida deshabilitada. `PolyFetch` consume
   exclusivamente ese registro local HDMI.

Las pausas dentro de UIO no publican valores parciales. Una actualización de
un solo eje conserva el indicador del otro. Si un reloj se detiene, el paquete
pendiente conserva sus datos hasta completar el intercambio.

Las RAM de coeficientes mantienen su actualización en el mismo banco que usa
la implementación original. La atomicidad nueva corresponde al par de
indicadores. Durante una recarga en caliente, la imagen puede atravesar la
actualización de la tabla compartida; un cambio atómico de toda la tabla
requeriría bancos adicionales o coordinación con HPS y es un alcance distinto.
Este cambio no añade bancos de coeficientes ni multiplicadores.

## VSYNC: clasificación y solución

`HDMI_TX_VS` procede del registro `hdmi_out_vs`. Sus pulsos duran mucho más que
dos ciclos de 50 MHz; basta trasladar el nivel mediante dos etapas y detectar
el flanco después de la segunda etapa.

`at_hdmi_vsync` contiene `vs_meta`, `vs_sync` y `vs_seen`, con identificación
explícita de sincronizador y preservación de las dos primeras etapas. Se
ejecuta continuamente, incluso cuando HPS no espera un cuadro.

El pulso local `rise` alimenta:

- La liberación de `vs_wait`, solicitada por el comando HPS 0x30.
- La aceptación de `cfg_set` en el secuenciador de reconfiguración HDMI.

Los consumidores usan sólo el flanco después de `vs_sync`. Se elimina la
comparación de `vs_d1` con VSYNC asíncrono y la cadena condicional `vsd/vsd2`.
Si una petición llega después de haber recibido el nivel alto, espera el
siguiente flanco. El arranque con `cfg_ready=0` conserva su aceptación directa
para poder configurar el PLL antes de disponer de una señal de vídeo.

## Restricciones y comprobación posterior

Se amplía `SYSTEM.sdc` mediante los mecanismos que ya utiliza el proyecto:

- Paquete de indicadores: `set_max_delay 5.0` entre payload y captura, y
  exclusión de hold justificada por el protocolo de datos estables.
- Petición/acuse: excepción únicamente hacia la primera etapa asíncrona.
- VSYNC: excepción únicamente HDMI → `u_at_hdmi_vsync.vs_meta`.
- Primera → segunda etapa, detección de flanco, captura → aplicación y todos
  los consumidores conservan análisis normal de setup y hold.

`report_at_video_avalon_timing.tcl` añade colecciones obligatorias para el
origen, paquete, sincronizadores, aplicación en blanking y consumidores del
filtro. También verifica por separado VSYNC → espera HPS, VSYNC → PLL y todos
los consumidores de la recepción. Una colección vacía es un error de auditoría.

No debe aplicarse este SDC a la netlist del fit anterior. Tras el próximo fit
hay que comprobar estas familias en Slow/Fast y −40/100 °C, además de las
anteriores familias de vídeo/Avalon, FMax global y el hold de sólo +0,006 ns
del buffer SDRAM en la referencia.

## Validación del candidato

- VSYNC: `scripts/test_at_hdmi_vsync.sh`; 84 flancos, espera solicitada durante
  VS alto, arranque del PLL sin VS y pausas de los relojes origen/destino.
- Scaler: `scripts/test_at_scaler_avalon.sh`; configuraciones original/local,
  progresivo/entrelazado y cargas de filtros adaptativos bajo backpressure.
- `check_at_scaler_filter_vcd.py` comprueba la tubería real de 8.192 escrituras
  por caso, cuatro transacciones, cambios horizontal/vertical, mantenimiento
  del otro eje, payload estable, aplicación en blanking y píxeles de identidad.
- Quartus Analysis & Elaboration final: **0 errores y 131 avisos**, finalizado
  el 25/09/2026 a las **07:14:39 locales**, en 1:30. No se ejecutó síntesis ni
  Fitter. Entradas de frontend registradas en `frontend-inputs.sha256`.

Las seis simulaciones y sus scoreboards Avalon terminan en **PASS**:

| Caso | Lecturas Avalon | Ráfagas de escritura | Píxeles de identidad |
|---|---:|---:|---:|
| Configuración original, progresivo | 185 | 240 | 26.965 |
| Configuración original, entrelazado | 202 | 240 | 24.661 |
| Configuración local, progresivo | 188 | 273 | 27.648 |
| Configuración local, entrelazado | 205 | 273 | 25.344 |
| Filtro adaptativo, progresivo | 171 | 273 | 24.576 |
| Filtro adaptativo, entrelazado | 172 | 273 | 23.040 |

Las cuatro regresiones anteriores conservan sus contadores. En las dos nuevas,
el scoreboard del filtro verifica **8.192 palabras escritas, cuatro
transacciones, los cuatro bancos de dirección y la secuencia aplicada 1 → 2 →
0**. Se conserva el eje vertical durante una actualización sólo horizontal.
El menor intervalo entre publicación y captura es **13,469 ns**, por encima
del presupuesto de datos de 5 ns; esa comprobación digital deberá completarse
con los retardos físicos del próximo fit.

Logs finales: `build/at-hdmi-controls/vsync/`, `avalon-v2/` y `frontend-final/`.
El primer intento de compilación VHDL-93 detectó una concatenación no estática
en un puerto; se sustituyó por una señal explícita. Los seis casos finales
usan esa corrección, al igual que la elaboración final de Quartus.

Manifiesto para identificar el próximo fit:
`build/at-hdmi-controls/candidate-source-manifest.json`.
La copia de las fuentes y los hashes de las 21 entradas de frontend permiten
verificar que se compila exactamente el candidato probado. El RBF de las
06:42 permanece como referencia y todavía no contiene este bloque.
