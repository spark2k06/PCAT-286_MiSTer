# Perfil EGA y opciones OSD: siguiente candidato CDC

## Punto de partida

Estado actual: el fit terminado a las 22:41 cierra las rutas de esta tanda
en las cuatro condiciones de TimeQuest, incluido el retorno de scanlines.
Véase `AT_SCANLINES_STATUS_FIT_20260924.md`. El proyecto completo conserva
violaciones fuera de estas familias.

El primer fit, revisado en `AT_VIDEO_OPTIONS_FIT_20260924.md`, permitió detectar
el retorno asíncrono de scanlines. Su ajuste tiene el manifiesto
`build/at-video-options/scanlines-candidate-source-manifest.json`;
`candidate-source-manifest.json` conserva el candidato original. Los apartados
siguientes documentan la preparación y validación previa a ambos fits.

Rama `beta-04`, tras el commit `eaf5f09` (VSYNC y shadowmask). El fit de
referencia está conservado en `build/at-frame-shadowmask/20260924-fit/` y se
describe en `AT_FRAME_SHADOWMASK_FIT_20260924.md`.

Las rutas intervenidas en esta tanda son:

| Ruta anterior | Peor setup del fit de referencia |
|---|---:|
| Perfil `applied[1] → ega_monitor_profile_video_sync1_q[1]` | −6,106 ns |
| OSD `status[9] → at_video_ary_q[0]` | −5,866 ns |
| OSD `status[8] → at_video_arx_q[0]` | −5,771 ns |

Se corrige también el mismo mecanismo de captura directa de escala y modo de
imagen. VRR, modo LFB/scaler y SPK286 quedan pendientes de sus respectivas
revisiones. Este candidato requiere un nuevo fit del usuario para medir sus
slacks y recursos; el RBF de las 20:44:21 corresponde a la tanda anterior.

## Perfil EGA: bus estable durante ejecución, variable durante reset

`ega_monitor_profile_latch` conserva la selección aplicada mientras se ejecuta
la máquina y admite cambios durante `at_machine_reset`. Esa señal incluye el
intervalo del splash: durante ese intervalo el raster sigue funcionando.
No debe suponerse que todo cambio del perfil ocurre con el dominio de vídeo
parado o mantenido en reset.

La copia anterior usaba dos sincronizadores de bits independientes. Una
transición `01 ↔ 10` puede dar una combinación intermedia; excluir sólo la
primera etapa no acredita coherencia del bus.

Se amplía el snapshot de geometría ya existente de 14 a 16 bits, incorporando
el perfil aplicado en `[15:14]`. El payload completo se mantiene hasta el acuse,
y los dos bits llegan en una sola captura. Los 14 bits inferiores conservan
su posición. Se reutilizan petición, acuse y sus sincronizadores.

El latch de selección y el camino de lectura de switches por la BIOS siguen
en el dominio de 50 MHz. El mailbox continúa activo durante reset y paradas
de reloj: no se reinicia una sola mitad del protocolo. Durante reset la copia
de vídeo puede reflejar ya el perfil transferido, en lugar de forzarse a cero;
la salida EGA fuerza su perfil de splash como antes. Una selección posterior
al reset continúa pendiente hasta el siguiente reset de máquina.

## Opciones OSD: configuración completa y aplicación en blanking

`at_video_options_cdc` agrupa siete bits, conservando la codificación PCXT-EGA:

| Campo | Bits de `hps_status` | Bits del payload |
|---|---|---|
| Modo de imagen | `[16:14]` | `[6:4]` |
| Escala | `[2:1]` | `[3:2]` |
| Aspecto | `[9:8]` | `[1:0]` |

`hps_io` escribe `status` por palabras de 16 bits; el modo de imagen cruza la
frontera entre las dos primeras palabras. Por eso sólo se inicia una captura
con `HPS_BUS[34]` desactivado, cuando ha terminado la transacción UIO. Es la
misma selección usada por `hps_io`, muestreada en el mismo dominio de 50 MHz.
No se publica una configuración parcial mientras UIO permanece seleccionado.

Tras la transferencia con acuse, los siete bits se decodifican juntos al
entrar en blanking vertical del raster de entrada, antes del conversor de
color. También pueden aplicarse mientras el pipeline está en reset. El cambio
puede esperar un cuadro si llega después de esa frontera. ARX/ARY mantienen
exactamente la tabla anterior: aspecto 0 produce 4:3; los demás producen
`(aspecto − 1):0`.

El procesamiento RGB, las memorias de imagen y la latencia del pipeline no
se modifican. La nueva lógica sólo transporta y aplica sus opciones; no añade
RAM. El coste físico se comprobará en el siguiente fit.

## Restricciones y auditoría posterior

El snapshot de perfil/geometría mantiene su presupuesto max-delay de 10 ns
hacia el reloj de 28,636 MHz. El nuevo snapshot OSD tiene un presupuesto de
10 ns hacia 57,272 MHz. Ambos esperan las dos etapas de petición antes de
capturar y retienen los datos hasta el acuse.

Las excepciones afectan únicamente a la llegada a la primera etapa de cada
toggle y al hold del bus retenido. Las etapas de sincronización siguientes,
la decodificación de opciones y los consumidores del perfil mantienen setup
y hold normales. No se añade ningún `false_path` general entre dominios.

`scripts/report_at_video_avalon_timing.tcl` añade las familias
`video_geometry_config`, `monitor_profile_local`, `video_options_config`,
`video_options_apply` y `video_options_local`, junto con los sincronizadores
de ambos mailboxes. Exige colecciones presentes y rutas activas; conserva la
comprobación de las correcciones anteriores.

## Pruebas funcionales

`bash scripts/test_at_video_options.sh`:

- 128 combinaciones de aspecto, escala y modo de imagen; 137 comprobaciones
  tras añadir el retorno de scanlines y la anulación por framebuffer.
- Configuración visible sólo en blanking vertical o reset local.
- Transacción HPS parcial mantenida durante varias fronteras de cuadro.
- Cambios acumulados con el reloj de vídeo detenido y recuperación del último.
- Reset local sin perder la configuración ni desajustar petición/acuse.
- Retorno coherente de scanlines desde el reloj de vídeo +90° al registro HPS,
  sin combinaciones intermedias y con `FB_EN` aplicado en su dominio local.

`bash scripts/test_at_video_window.sh`, con el adaptador EGA real:

- Perfiles 0/1/2, selección pendiente hasta reset y cambios durante splash.
- Las cuatro lecturas de switches BIOS del perfil MDA devuelven lo esperado.
- Cambios de perfil y geometría, reloj detenido y reset repetido.
- Texto de 200/350 líneas y gráficos de 200 líneas: 640 píxeles visibles sin
  recorte, con offsets horizontales 0 y 6.
- Lecturas/escrituras packed y planar conservadas, incluyendo 16 cambios de modo.

Ambas pruebas pasan. Quartus 17.0.2 completó Analysis & Elaboration de
`PCAT-286` el 24/09/2026 a las 21:08:02 locales, con **0 errores y 130 avisos**.
Esa comprobación no ejecutó síntesis, Fitter ni generación de RBF.

Los logs se guardan en `build/at-video-options/` y `build/at-video-window/`.
El manifiesto previo a la compilación está en
`build/at-video-options/candidate-source-manifest.json`. El resultado físico
queda pendiente del nuevo fit.

La corrección adicional de retorno usa `sys/at_scanlines_status.sv`, habilitada
en `sys_top` por `SPK286_AT_CDC`. Un snapshot de dos bits desde `clk_vid` a
`clk_sys` mantiene la intensidad aplicada hasta el acuse; `FB_EN` anula la
respuesta en su dominio local. Se conserva el análisis normal entre el reloj
de opciones y el de salida +90°, y entre la captura de retorno y `io_dout_sys`.
El presupuesto del payload de retorno es de 10 ns. El valor HPS puede actualizarse
unos ciclos después del de vídeo por la latencia del handshake.

Analysis & Elaboration de esta corrección adicional pasó el 24/09/2026 a las
22:11:51 locales: 0 errores, 130 avisos. Sus slacks físicos ya están revisados
en `AT_SCANLINES_STATUS_FIT_20260924.md`.
