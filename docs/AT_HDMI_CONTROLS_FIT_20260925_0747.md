# Resultados finales de la revisión — 25/09/2026, 07:47

## Resultado y alcance

**El filtro adaptativo y la recepción de VSYNC HDMI cumplen timing en las
cuatro condiciones de TimeQuest. El proyecto completo mantiene violaciones
de setup.** HDMI supera ahora su frecuencia requerida, pero empeoran la FMax
de CLK2 y el TNS acumulado en ese dominio.

Esta revisión no modifica RTL, SDC, QSF ni CPU, y no ejecuta síntesis ni Fitter.
Se detiene el trabajo de implementación por indicación del usuario. SPK286
se tratará en otras sesiones. El candidato compilado sigue sin commit sobre
`6aee2bf`, rama `beta-04`.

Referencia anterior: fit de las 06:44 descrito en
[AT_SCALER_CONFIG_FIT_20260925_0644.md](AT_SCALER_CONFIG_FIT_20260925_0644.md).
La implementación y las simulaciones de este candidato están descritas en
[AT_HDMI_CONTROLS_CDC.md](AT_HDMI_CONTROLS_CDC.md); sus menciones a un fit pendiente
corresponden al estado previo a esta revisión.

Los 42 archivos del manifiesto del candidato coinciden. Se congelaron fuentes,
SDC, bases de datos y resultados en
`build/at-hdmi-controls/20260925-0747-fit/work/`.
TimeQuest se ejecutó sobre esa copia con Quartus 17.0.2. Las auditorías focalizada,
general y HDMI interno terminaron sin errores. Se comprobaron Slow/Fast a
−40/100 °C, 1100 mV. Los 54 archivos de resultados conservan su hash tanto en
el proyecto como en la copia congelada.

## Rutas reparadas

Peor margen de las cuatro condiciones. La comparación anterior/actual sigue
la misma función; el rediseño sustituye las rutas asíncronas originales por
transferencias con protocolo y consumidores locales.

| Familia | Setup anterior | Setup actual | Hold actual |
|---|---:|---:|---:|
| Indicadores adaptativos → consumidores del filtro | −5,701 ns | **+5,528 ns** | +0,201 ns |
| VSYNC HDMI → consumidores a 50 MHz | −5,563 ns | **+17,867 ns** | +0,272 ns |
| Primera → segunda etapa de VSYNC | — | +18,680 ns | +0,290 ns |
| VSYNC sincronizado → espera HPS | — | +18,519 ns | +0,272 ns |
| VSYNC sincronizado → aceptación de configuración PLL | — | +17,867 ns | +0,466 ns |
| Captura → aplicación de indicadores | — | +5,495 ns | +0,225 ns |
| Habilitación de aplicación en blanking | — | +3,457 ns | +0,779 ns |
| Configuración de cuadro → consumidores, tanda anterior | +0,959 ns | +1,050 ns | +0,184 ns |
| Captura de fase del aspecto, tanda anterior | +0,140 ns | +0,489 ns | +13,077 ns |

El paquete estable de indicadores presenta +5,332 ns en el reporte de setup
con su restricción de max-delay. El mayor retardo físico de datos es
**1,545 ns**, menor que el presupuesto de 5 ns. La simulación había medido
13,469 ns como intervalo mínimo entre publicación y captura.

Se comprobaron **124 combinaciones de familia/tipo fuera de los grupos
globales**, todas con rutas activas, margen positivo y presencia en las
cuatro condiciones. Incluyen vídeo/Avalon, framebuffer, shadowmask, opciones,
geometría, scanlines y sincronizadores de petición/acuse. Con las cuatro
comprobaciones globales son 128 combinaciones. No son 124 rutas individuales.

Se mantienen las excepciones justificadas del candidato: sólo primera etapa
asíncrona de los sincronizadores y hold de los paquetes estables protegidos
por protocolo. Las etapas posteriores y los consumidores siguen analizados.
Esta revisión no añadió excepciones para hacer pasar el fit.

## FMax

Mínimo entre las cuatro condiciones, en MHz:

| Dominio | Requerido | Anterior | Actual |
|---|---:|---:|---:|
| CPU / `FPGA_CLK2_50` | 50,00 | 41,76 | **40,84** |
| HDMI | 148,54 | 146,56 | **152,70** |
| Avalon HPS | 100,00 | 165,78 | **182,55** |
| Vídeo base | 28,64 | 32,40 | **32,72** |
| Vídeo ×2 | 57,27 | 78,95 | **79,59** |
| Vídeo +90° | 57,27 | 81,67 | **85,73** |
| `FPGA_CLK1_50` | 50,00 | 86,14 | **89,05** |
| Audio | 24,58 | 37,92 | **36,40** |

La FMax describe las rutas internas de cada dominio; superar la frecuencia
requerida no demuestra el cierre de sus cruces con otros relojes.

HDMI → HDMI tiene ahora un peor setup de **+0,183 ns**, ruta
`ascal.o_hcpt[2] → ascal.o_vcpt[8]` en Slow −40 °C. En la referencia el mínimo
era −0,091 ns. El margen actual es positivo, pero pequeño.

## Timing global

| Métrica | Anterior | Actual |
|---|---:|---:|
| Peor setup / WNS | −5,701 ns | **−5,596 ns** |
| Peor hold | +0,006 ns | **+0,051 ns** |
| Recovery | +3,311 ns | **+2,993 ns** |
| Removal | +0,324 ns | **+0,389 ns** |
| Anchura mínima de pulso | +0,793 ns | **+0,793 ns** |
| TNS de setup, Slow 100 °C | −2.505,423 ns | **−4.103,489 ns** |

Setup mide el margen antes del flanco de captura; hold, el margen después.
Recovery/removal comprueban la liberación de señales asíncronas respecto al
reloj. Los valores positivos cumplen las restricciones analizadas.

El peor hold está en
`ascal.o_vpixq_pre[0].g[7] → ascal.o_vpixq[0].g[7]`, Slow −40 °C.
No hay violaciones de hold, recovery, removal o anchura mínima de pulso en
los resúmenes revisados.

### Qué significa TNS

**TNS = Total Negative Slack**, suma de los márgenes negativos de los puntos
de destino que incumplen timing en el análisis. En los resúmenes de TimeQuest
se utiliza endpoint TNS, evitando contar repetidamente todas las rutas que
terminan en un mismo destino. Véase la
[definición de Intel](https://www.intel.co.id/content/www/id/id/programmable/quartushelp/19.1/analyze/sta/sta_com_report_recovery_summary.htm).

Ejemplo: dos destinos con slack de −1 ns y −0,5 ns producen TNS = −1,5 ns;
el peor slack, WNS, es −1 ns. Los márgenes positivos no compensan los negativos.
TNS = 0 significa que no quedan incumplimientos de ese tipo en el análisis.
No representa latencia acumulada de ejecución del core ni se convierte
directamente en MHz.

Aquí se suman los resúmenes de setup por dominio **sólo en Slow 100 °C**,
con la misma metodología antes y después. No se suman las cuatro condiciones.

| Dominio de captura | TNS anterior | TNS actual |
|---|---:|---:|
| CLK2 / 50 MHz | −2.362,925 ns | **−3.973,181 ns** |
| HDMI | −137,248 ns | **−124,712 ns** |
| Vídeo +90° | −5,250 ns | **−5,596 ns** |
| Resto | 0 ns | 0 ns |

La magnitud del TNS global empeora **1.598,066 ns, un 63,8 %**. CLK2 concentra
el **96,8 %** del TNS actual. Es una atribución al dominio de reloj, no una
afirmación de que todos esos destinos estén dentro de SPK286. La auditoría
encuentra como peor ruta interna de CLK2 una ruta de la CPU.
Un WNS algo mejor puede coexistir con un TNS peor porque hay más déficit
acumulado en otros destinos. Estos resúmenes no determinan por sí solos
cuántos destinos nuevos han empezado a fallar.

## Violaciones que permanecen

| Familia / ruta representativa | Peor setup | Relojes |
|---|---:|---|
| `subcarrier → subcarrier_out` | **−5,596 ns** | CLK2 → vídeo +90° |
| `dv_data[20] → hdmi_dv_data[20]` | **−4,775 ns** | Vídeo +90° → HDMI |
| CPU: `prefetch_queue.head_q[1] → registers.gpr_q[71]` | **−4,484 ns** | CLK2 → CLK2 |
| CPU/SDRAM: `biu.data_active_q → u_KFSDRAM.sdram_address[7]` | **−0,693 ns** | CLK2 → CLK2 |

Son las peores rutas de familias seleccionadas, no una enumeración de todos
los endpoints que fallan. Permanecen diez combinaciones reloj/condición con
setup negativo; eso tampoco equivale a diez rutas.

`check_timing` conserva 3.713 elementos sin reloj, 20 entradas sin input delay,
85 salidas sin output delay y 22 restricciones min/max parciales. Cero bucles
combinacionales y cero latches en esa comprobación. La auditoría dirigida no
tiene colecciones vacías. Estos avisos de cobertura requieren clasificación
antes de afirmar que todo el diseño está completamente restringido; no se
deben convertir en excepciones globales automáticamente.

## Recursos y duración

| Recurso | Anterior | Actual | Libre |
|---|---:|---:|---:|
| ALM, utilización lógica | 27.497 | **27.284 / 41.910** | 14.626 |
| LAB ocupados total o parcialmente | 3.973 | **3.937 / 4.191** | **254** |
| Registros totales | 35.252 | **35.341** | — |
| RAM M10K | 409 | **409 / 553** | 144 |
| DSP | 39 | **39 / 112** | 73 |
| PLL | 3 | **3 / 6** | 3 |

Los LAB ocupan **93,94 %**; queda **6,06 %** libre, 36 LAB más que antes.
El porcentaje de ALM lógico no refleja por sí solo el margen de colocación:
LAB parcialmente usados, distribución de relojes y enrutado también limitan.
Las diferencias de recursos entre fits incluyen cambios de empaquetado y
duplicación física, incluso en módulos cuyo RTL no se ha modificado.

Compilación del usuario: síntesis 5:53, Fitter 16:00, ensamblado 0:30 y
TimeQuest 1:53; total **24:16**. Fitter terminó a las 07:44:22 y el flujo
a las 07:47:14, hora local. Las auditorías posteriores sólo analizaron el fit.

## RBF y recomendaciones

RBF para probar:
`output_files/PCAT-286_20260925_074516.rbf`.
Es idéntico a `output_files/PCAT-286.rbf`, generado a las 07:45:16,
con 4.005.468 bytes.

SHA-256:
`2CC59228C88758A6350A5CD48F6E08001BB267307B314D08ED1C07E7B18BD20E`.

1. Probar este RBF en hardware: filtros normal/adaptativo y cambios H/V,
   cambios de resolución HDMI y framebuffer, regresión de EDIT y Sound Blaster.
   Las simulaciones y TimeQuest han pasado para el bloque, pero no sustituyen
   la comprobación física de su funcionamiento.
2. Conservar este fit como referencia. Vigilar en futuros fits el setup interno
   HDMI de +0,183 ns, el hold de +0,051 ns y el margen de LAB.
3. Fuera de CPU, priorizar en una sesión posterior la clasificación de los
   cruces de subportadora y vídeo directo: determinar su modo activo, relación
   entre relojes y ventana de captura antes de elegir un mecanismo CDC o una
   restricción. No justificar un false-path únicamente porque el slack falla.
4. Reservar CPU y su interfaz SDRAM para las sesiones dedicadas indicadas por
   el usuario. El proyecto todavía no debe etiquetarse como cerrado en timing.

Evidencias: `focused/`, `timing/`, `hdmi-local/`, `analysis.json`,
`manifest.json` y `review-verification.json`, dentro de
`build/at-hdmi-controls/20260925-0747-fit/`.
