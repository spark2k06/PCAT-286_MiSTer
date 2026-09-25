# Subportadora y vídeo directo: fit del 25/09/2026, 09:00

## Estado

**No aceptado como solución final.** El usuario confirma que la TV analógica
recupera imagen al seleccionar 480i 15 kHz, pero HDMI sigue sin imagen.
Los nuevos cruces auditados
cumplen, pero queda una violación síncrona en el scaler y las violaciones de
CLK2. La investigación posterior identificó un bloqueo de arranque del
transmisor en la netlist. Hay una corrección RTL pendiente de nuevo fit y
comprobación física, detallada abajo.

La síntesis, Fitter y ensamblado los realizó el usuario. Esta revisión ejecutó
TimeQuest sobre una copia congelada del fit, sin recompilar. Se verificaron
los 49 archivos del manifiesto del candidato. QSF y CPU permanecen intactos.

Evidencias locales: `build/at-native-output/20260925-0900-fit/`, con `work/`,
`manifest.json`, los tres logs de TimeQuest, informes `focused/`, `timing/`,
`hdmi-local/` y `analysis.json`. Los tres procesos terminaron sin errores.
La auditoría enfocada contiene 166 combinaciones familia/tipo, todas con
rutas presentes en cuatro condiciones; las familias específicas son positivas.
El indicador `timing_open=1` mantiene abierto el resultado global.

## Timing

Peores márgenes de las cuatro condiciones, en ns. Referencia: fit de las 07:47.

| Medida | Anterior | Actual |
|---|---:|---:|
| Setup global (WNS) | −5,596 | −4,812 |
| Hold global | +0,051 | +0,033 |
| Recovery | +2,993 | +1,579 |
| Removal | +0,389 | +0,285 |
| Ancho mínimo de pulso | +0,793 | +0,793 |
| Setup local HDMI, sin cruces | +0,183 | **−0,124** |
| TNS setup Slow 100 °C | −4.103,489 | −4.821,461 |

El TNS indicado suma el déficit de los endpoints con setup negativo en una
misma condición; no es una duración de fallo ni el peor camino individual.
En Slow 100 °C todos esos déficits actuales están en CLK2. En Slow −40 °C
también aparecen dos endpoints negativos del scaler HDMI.

| Familias nuevas activas | Setup | Hold |
|---|---:|---:|
| Captura estable del paquete analógico | +9,076 | Excepción por handshake |
| Aplicación del paquete en vídeo | +15,386 | +0,220 |
| Configuración local → consumidores | +9,604 | +0,229 |
| Acumulador → acumulador/subcarrier_out | +13,168 | +0,250 |
| Vídeo directo → primera etapa nativa | +15,787 | +0,221 |
| Etapas nativas → salida directa | +10,171 | +0,279 |
| Scaler → etapa HDMI | +3,494 | +0,214 |
| Etapa HDMI → salida escalada | +0,383 | +0,150 |

Las antiguas rutas `subcarrier → subcarrier_out` (−5,596 ns) y
`dv_data → hdmi_dv_data` (−4,775 ns) se sustituyen por esos trayectos.
Las dos ramas seleccionadas del transmisor conservan análisis activo.
Recovery/removal de sus registros de salida también cumplen en ambos modos.

Rutas pendientes comprobadas:

- `ascal|o_h_lum_pix.r[4] → ascal|o_poly_lum[4]`: **−0,124 ns**,
  Slow −40 °C, mismo PLL HDMI; el endpoint `[0]` tiene −0,117 ns.
  Es lógica de luminancia del filtro, no un CDC. Hace falta acortar la lógica
  o distribuir el cálculo conservando la alineación de píxeles y coeficientes.
  No procede excluirla por SDC. Su existencia no prueba la causa del fallo
  de sincronización observado.
- CPU `prefetch_queue|head_q[1] → registers|gpr_q[68]~DUPLICATE`:
  **−4,812 ns**, Slow −40 °C. Fuera del alcance acordado para esta sesión.
- CPU/owner `biu|ack_active_q~DUPLICATE → u_KFSDRAM|sdram_address[9]`:
  **−1,836 ns**, Slow 100 °C. Se conserva para la futura revisión de CPU/bus.

FMax mínima reportada en las cuatro condiciones:

| Dominio | MHz |
|---|---:|
| CLK2 | 40,30 |
| PLL HDMI | 145,86 |
| Avalon | 183,12 |
| Vídeo base | 32,93 |
| Vídeo ×2 | 73,66 |
| Vídeo +90° | 83,46 |
| CLK1 | 85,73 |
| Audio | 37,61 |

Las cifras de FMax de los relojes derivados del mux (866,55/914,08 MHz)
sólo describen sus pequeños caminos internos; no son frecuencias utilizables
del enlace ni sustituyen el análisis entre el PLL y los registros finales.

Uso físico: **3.974/4.191 LAB**, quedan **217** (5,18 %); 37 LAB más que antes.
ALM: 27.959; registros: 35.633; M10K: 409/553; DSP: 39/112.

## Diagnóstico con la configuración del usuario

Leído en modo consulta `\\192.168.0.135\sdcard\MiSTer.ini`:

```ini
direct_video=0
vga_scaler=0
forced_scandoubler=0
composite_sync=1
ypbpr=0
video_mode=8
vsync_adjust=0
```

No hay sección específica de PCAT que sobrescriba esos campos. HDMI debería
seleccionar el PLL y la salida escalada; VGA utiliza el raster del core.
El selector nativo de HDMI no debería activarse con esa configuración.
La ruta analógica RGB de HS/CSync conserva su lógica anterior cuando YC está
deshabilitado. Los avisos de power-up de `pll_hdmi_adj|logcpt` son idénticos
a los del fit anterior; no identifican una regresión nueva.

El archivo `config/MiSTer/PCAT-286.CFG` tiene a cero `status[35:34]`; el formato
de guardado se contrastó con `user_io_status_save` en Main_MiSTer. El usuario
también confirmó en el OSD **«350-line CRT = Native»**. En modo EGA de 350
líneas esto deja desactivada la conversión a 15 kHz. Se indicó probar
**480i 15 kHz**, o **240p 15 kHz**. El usuario confirmó después que **480i
recupera la imagen en la TV**. La foto muestra 15,74 kHz / 59,9 Hz en la
entrada y 1920×1080 / 148,5 MHz / **0,0 Hz** en HDMI. En Main_MiSTer,
`video_scaler_description` muestra el reloj configurado (`vm->Fpix`) y calcula
el refresco desde `vi->vtimeh`: los 148,5 MHz no son una medición física del
reloj de salida. El 0,0 Hz indica que no se dispone de un periodo VSYNC HDMI
válido. Sigue abierta la investigación del transmisor, su reloj/reset y el
raster escalado; el fallo analógico comunicado se resuelve con el modo CRT.

También se solicitó comparar con el RBF anterior, sin alterar el resto de
ajustes. No se cambiaron archivos de la MiSTer.

## Causa HDMI reproducida y corrección de arranque

Se exportó la netlist funcional del fit de las 09:00 con `quartus_eda`, sin
volver a sintetizar: `build/at-native-output/netlist/PCAT-286.vo`. La
exportación terminó sin errores. No es una nueva compilación ni un nuevo RBF.

En el RTL original `state_q` se inicializaba a 2 (liberar reset), pero el
primer caso, de valor 0, era reposo. La FSM extraída por Quartus 17 arranca
con sus tres registros `state_q.00`, `.01` y `.10` a cero. Su lógica y la
tabla de codificación corresponden entonces al estado de reposo. Mientras
`direct_video=0` y `select_direct=0`, no se solicita cambio de modo y tampoco
se ejecuta la rama que libera `switch_reset_q`.

El reset lógico activo se representa invertido en los registros físicos:
`switch_reset_q~q=0` mantiene CLRN de `reset_meta` y `reset_sync` a cero;
éstos mantienen CLRN de la salida a cero. Por eso no hay VSYNC HDMI aunque
las rutas tengan márgenes positivos.

`scripts/check_at_hdmi_startup_netlist.py` evalúa las LUT reales y los valores
de power-up del controlador SYS de la netlist exportada, con configuración
escalada constante y UIO inactivo:

- **Fit original: FAIL**, sigue en reset tras 128 ciclos SYS.
- Prueba contrafactual de diagnóstico: conservando todas las ecuaciones del
  mismo fit y poniendo únicamente los bits de estado en el estado 2 que
  pretendía el RTL, **libera reset en el ciclo 32**. No es un fit corregido.
- Logs: `startup-before.log` y `startup-counterfactual.log` en
  `build/at-native-output/`.

La corrección hace que **RELEASE_RESET sea el primer caso y tenga valor 0**,
con inicialización explícita a ese estado. ASSERT_RESET vale 1 y RUN vale 2.
Así el arranque con estado cero libera reset incluso sin cambios de modo.
Se conservan la secuencia de conmutación, los tiempos de espera, los resets
asíncronos y los sincronizadores, el mux físico y las tuberías de píxeles.
No se retoca el SDC para esta corrección.

Las tres simulaciones (148,54 / 74,25 / 25 MHz) pasan con una comprobación
explícita adicional de arranque escalado sin ninguna transición de modo.
También pasan vídeo directo, prioridad del framebuffer, relojes parados,
CSync y los comandos analógicos. Evidencia: `startup-fix/sim/`.
Quartus 17 Analysis & Elaboration también pasa: **0 errores, 131 avisos**,
finalizado a las **09:57:55 locales**, duración 1:37. Los 23 archivos de
entrada registrados coinciden con el candidato. No se ejecutó síntesis ni
Fitter de la corrección. Evidencia: `startup-fix/frontend/`.
Faltan el nuevo fit, la comprobación de arranque de esa netlist y la prueba
física HDMI. La violación del cálculo de luminancia del fit de las 09:00
permanece documentada y debe revisarse de nuevo en el próximo fit.

## Imágenes

Imagen investigada, **con fallo funcional comunicado**:

- `output_files/PCAT-286_20260925_085822.rbf`, 4.022.872 bytes.
- SHA256: `CDA0BA5F2BA102E653F70C90F6324ADBF60B02D50E46433510CDB1ED4922D881`.
- La copia en `sdcard/_Computer/` coincide en SHA256 con el fit auditado.

Imagen anterior para comparación:

- `output_files/PCAT-286_20260925_074516.rbf`, 4.005.468 bytes.
- SHA256: `2CC59228C88758A6350A5CD48F6E08001BB267307B314D08ED1C07E7B18BD20E`.

No se declara resuelta la sincronización ni cerrado el timing de vídeo.
