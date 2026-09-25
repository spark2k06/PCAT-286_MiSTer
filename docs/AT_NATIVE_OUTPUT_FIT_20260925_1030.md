# Subportadora y vídeo directo — fit del 25/09/2026, 10:30

## Estado y trazabilidad

El usuario confirma que **se ha resuelto el problema de imagen**. La nueva
netlist libera el reset HDMI al cabo de **32 ciclos SYS** con modo escalado
constante, sin necesitar un cambio a vídeo directo. El comprobador sigue
detectando el bloqueo del fit anterior. La TV analógica funciona seleccionando
480i 15 kHz para el modo EGA de 350 líneas.

**La recuperación de imagen no implica cierre global de timing**: el resumen
nativo conserva setup negativo en CPU/CLK2 y en el scaler HDMI.

- Rama `beta-04`, sobre `a8bc4f1`, con cambios todavía sin commit.
- Se verificaron los 51 archivos del manifiesto antes de congelar el fit.
- La síntesis y Fitter son del usuario; esta revisión sólo consulta el fit,
  exporta su netlist funcional y ejecuta TimeQuest en una copia aislada.
- Evidencias: `build/at-native-output/20260925-1030-fit/`.
- El comprobador se amplió para interpretar la ecuación booleana de una LUT
  extendida usada por el nuevo fit. El comprobador original rechazaba ese
  tipo de LUT explícitamente; no era un fallo del RTL. No se modificó RTL,
  SDC, QSF ni CPU durante esta revisión.
- Los tres procesos TimeQuest terminaron sin errores. La auditoría enfocada
  tardó 3:59, la general 3:06 y la local HDMI 0:22. La evaluación del arranque
  con el comprobador ampliado consta en `startup-netlist.log`.

## Resultados globales

Márgenes en ns, tomando el peor de las cuatro condiciones. El TNS de la
tabla corresponde exclusivamente a Slow 1100 mV 100 °C, para comparar la
misma condición entre ambos fits.

| Medida | Fit 09:00 | Fit 10:30 |
|---|---:|---:|
| Setup global (WNS, CPU) | −4,812 | −4,932 |
| Setup local HDMI | −0,124 | −0,294 |
| Hold global | +0,033 | +0,081 |
| Recovery | +1,579 | +2,520 |
| Removal | +0,285 | +0,160 |
| Ancho mínimo de pulso | +0,793 | +0,793 |
| TNS setup Slow 100 °C | −4.821,461 | −3.667,041 |

El déficit total TNS baja aproximadamente un 23,9 %, aunque el peor camino
individual de setup empeora. En el fit nuevo, el TNS de esa condición se
reparte en CLK2 (−3.666,947 ns) y HDMI (−0,094 ns).

## Bloques modificados y FMax

Las 166 combinaciones familia/tipo de la auditoría enfocada tienen caminos
presentes en las cuatro condiciones. No hay familias específicas negativas
ni colecciones vacías. Se mantiene `timing_open=1` por los caminos globales.

| Trayecto activo | Setup mínimo | Hold mínimo |
|---|---:|---:|
| Captura estable del paquete analógico | +8,985 | Excepción por handshake |
| Aplicación de la configuración en vídeo | +12,173 | +0,251 |
| Configuración local → consumidores | +7,348 | +0,165 |
| Acumulador → acumulador/subcarrier_out | +13,581 | +0,121 |
| Pipeline nativo → salida directa | +11,942 | +0,081 |
| Pipeline HDMI → salida escalada | +0,886 | +0,163 |

Recovery/removal de la salida: directo +13,308/+0,160 ns; escalado
+2,520/+0,160 ns. Las ramas seleccionadas y los resets de salida siguen
analizados con las mismas restricciones del candidato anterior.

| Dominio | FMax mínima (MHz) |
|---|---:|
| CPU / CLK2 | 40,11 |
| HDMI | 142,33 |
| Avalon | 165,18 |
| Vídeo base | 33,20 |
| Vídeo ×2 | 75,18 |
| Vídeo +90° | 84,23 |
| CLK1 | 86,44 |
| Audio | 38,04 |

Son mínimos de las cuatro condiciones de análisis. FMax sólo incluye rutas
con el mismo reloj; los márgenes entre relojes se revisan por separado.
Las cifras elevadas de los relojes derivados del mux no son una frecuencia
de enlace admisible ni sustituyen la FMax del PLL HDMI.

## Rutas pendientes y siguiente recomendación

- **Scaler HDMI:** `ascal|o_h_lum_pix.g[4] → ascal|o_poly_lum[1]`,
  −0,294 ns en Slow −40 °C; −0,094 ns en Slow 100 °C. Es una ruta síncrona
  del cálculo `max(R,G,B)` de `poly_lum`, no un CDC ni una configuración
  estable. La FMax de 142,33 MHz queda por debajo de los 148,54 MHz analizados.
- **CPU:** `prefetch_queue|storage_q[2][4] → events|event_error_code[8]`,
  −4,932 ns en Slow 100 °C. Queda para las sesiones dedicadas a CPU.
- **CPU/owner:** `biu|address_q[23] → u_KFSDRAM|sdram_address[7]`,
  −1,684 ns en Slow 100 °C. Se conserva para la revisión de CPU/bus.

La siguiente optimización recomendada es dividir el máximo de RGB entre
las dos etapas ya existentes `o_poly_lum` y `o_poly_lum1`: registrar primero
`max(R,G)` y B alineado, y comparar ambos en la segunda etapa. El resultado
debe conservar la misma latencia total que hoy para no desalinear los pesos
adaptativos, sus coeficientes ni los píxeles. Hay que mantener también la
selección horizontal/vertical y la retención del último valor cuando ningún
filtro adaptativo está activo. Esto acorta la cadena de comparaciones sin
necesitar una excepción de timing. **Recomendación todavía no implementada.**

## Recursos y compilación

| Recurso | Fit 09:00 | Fit 10:30 | Libres ahora |
|---|---:|---:|---:|
| LAB | 3.974 | 3.952 / 4.191 | 239 (5,70 %) |
| ALM | 27.959 | 27.185 / 41.910 | 14.725 |
| Registros | 35.633 | 35.655 | — |
| M10K | 409 | 409 / 553 | 144 |
| DSP | 39 | 39 / 112 | 73 |

Se recuperan 22 LAB. Las variaciones de lógica de todo el diseño incluyen
los efectos de optimización y colocación del nuevo fit; no representan una
optimización RTL de la CPU.

El informe de flujo del usuario registra 24:58 de tiempo total: Analysis &
Synthesis 6:17, Fitter 16:27, Assembler 0:27 y TimeQuest 1:47. Estos son los
tiempos de compilación, no las duraciones de la auditoría posterior.

## RBF verificado

`output_files/PCAT-286_20260925_102906.rbf`, **4.026.236 bytes**.

SHA256: `965EEA69904E057BEAE9FAA3245909F9DA24C6B7DA624FE000FDF7A547B4756F`.

La copia en `\\192.168.0.135\sdcard\_Computer\` tiene el mismo hash. Es la
imagen probada por el usuario; no se generó otro RBF durante esta revisión.
