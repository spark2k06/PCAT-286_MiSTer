# Revisión del ajuste del scaler — 25/09/2026, 06:44

## Resultado

**Las dos rutas corregidas en la tanda anterior cumplen setup y hold en las
cuatro condiciones de TimeQuest. Los DSP vuelven a 39. El proyecto completo
todavía no cumple timing.**

Este informe compara con el fit de las 05:59 documentado en
`AT_SCALER_CONFIG_FIT_20260925.md`. Los 36 archivos del manifiesto revisado
coincidían antes de la auditoría. Se conservaron las fuentes, SDC y base de
datos del fit en `build/at-scaler-config/20260925-0644-fit/work/`; los análisis
usan esa copia, sin ejecutar síntesis ni Fitter.

## Comprobación de las correcciones

Peor margen entre Slow/Fast, −40/100 °C:

| Familia | Setup anterior | Setup actual | Hold actual |
|---|---:|---:|---:|
| Configuración de cuadro → todos sus consumidores | −5,254 ns | **+0,959 ns** | +0,170 ns |
| Opciones OSD → todos sus consumidores | −0,118 ns | **+0,140 ns** | +0,333 ns |
| ARX/ARY → captura de fase `aspect_video_q` | — | +0,140 ns | +13,393 ns |
| Aspecto ya capturado → comparación/cálculo local | — | +8,600 ns | +0,289 ns |
| Configuración local de shadowmask → consumidores | +3,447 ns | +3,002 ns | +0,227 ns |

La habilitación LFB aplicada en HDMI ya no vuelve al paquete de shadowmask
formado a 50 MHz. Se comprueban todos los consumidores de la configuración
de cuadro; el margen indicado corresponde a la peor ruta que permanece.
ARX/ARY entra primero en un registro de vídeo +90°, y la comparación posterior
dispone de un ciclo completo. La captura directa sigue siendo una ruta normal
entre relojes relacionados; no se ha excluido de TimeQuest.

El margen **+0,140 ns** de esa captura es pequeño y debe revisarse en los fits
posteriores. La ausencia de violaciones en este fit no garantiza el mismo
resultado después de cambiar la colocación.

Otras familias comprobadas:

| Familia | Setup / max-delay | Hold |
|---|---:|---:|
| Paquete de geometría → captura | +9,684 ns | Excluido por protocolo |
| Configuración local del cálculo → consumidores | +7,923 ns | +0,170 ns |
| Paquete de cuadro → captura HDMI | +0,927 ns | Excluido por protocolo |
| Actualización/reinicio de raster → scaler | +2,542 ns | +0,319 ns |
| Modo de entrada → `ascal.i_mode` | +13,853 ns | +0,432 ns |
| Aspecto de retorno → HPS | +15,668 ns | +0,201 ns |
| Dirección/base de lectura → Avalon | +1,859 ns | Excluido por protocolo |
| Dirección/base de escritura → Avalon | +1,776 ns | Excluido por protocolo |

Hay **103 combinaciones de familia/tipo fuera de los grupos globales**, todas
con rutas activas y margen positivo en las cuatro condiciones. Incluyen los
sincronizadores de petición/acuse y las familias reparadas en tandas anteriores.
Al añadir setup, hold, recovery y removal globales son 107 combinaciones;
los grupos globales de setup siguen fallando. No hay colecciones vacías.
No se añadieron excepciones ni se modificó el SDC en esta revisión.

## FMax

Mínimo de las cuatro condiciones, en MHz:

| Dominio | Requerido | Anterior | Actual | Cumple FMax |
|---|---:|---:|---:|:---:|
| CPU / `FPGA_CLK2_50` | 50 | 41,91 | **41,76** | No |
| HDMI | 148,54 | 105,09 | **146,56** | No |
| Avalon HPS | 100 | 146,56 | **165,78** | Sí |
| Vídeo base | 28,64 | 31,88 | **32,40** | Sí |
| Vídeo ×2 | 57,27 | 84,32 | **78,95** | Sí |
| Vídeo +90° | 57,27 | 81,96 | **81,67** | Sí |
| `FPGA_CLK1_50` | 50 | 85,95 | **86,14** | Sí |
| Audio | 24,58 | 37,38 | **37,92** | Sí |

FMax considera las rutas de un mismo reloj. No incluye los cruces entre
dominios, aunque los dos relojes procedan de un mismo PLL.

Una auditoría adicional de rutas HDMI → HDMI identifica el límite actual:

- `ascal.o_hsize[6] → ascal.o_hacc_next[13]`: **−0,091 ns**, Slow/−40 °C.
- `ascal.o_hcpt[5] → ascal.o_vcpt_pre2[10]`: **−0,033 ns**, misma condición.

Son rutas síncronas internas del escalador. Requieren reducir la lógica o
reorganizar sus etapas conservando el ciclo de cada píxel; no un sincronizador
ni una excepción de CDC. La primera tiene un retardo de datos de 6,515 ns para
un período de 6,732 ns, antes de considerar skew, setup e incertidumbre.

## Timing global

| Métrica | Anterior | Actual |
|---|---:|---:|
| Peor setup | −5,458 ns | **−5,701 ns** |
| Peor hold | +0,067 ns | **+0,006 ns** |
| Recovery | +2,798 ns | +3,311 ns |
| Removal | +0,260 ns | +0,324 ns |
| Ancho mínimo de pulso | +0,793 ns | +0,793 ns |
| TNS setup, Slow/100 °C | −2.683,257 ns | **−2.505,423 ns** |
| Grupos reloj/condición con setup negativo | 12 | 12 |

El TNS mejora otros **177,834 ns (6,6 %)**, mientras que el peor setup empeora
0,243 ns en otra familia. Hold sigue sin violaciones, con sólo 6 ps de margen
en su peor ruta. No se declara cierre global.

El hold de **+0,006 ns**, Fast/−40 °C, corresponde a
`u_at_sdram_read_buffer.request_line_base_q[20]` → registro de entrada de la
RAM `line_tag_q_rtl_0`. Está en el buffer de lectura SDRAM; sigue positivo,
pero debe vigilarse al cambiar la colocación.

### Rutas pendientes

| Ruta | Peor setup | Dominio |
|---|---:|---|
| `ascal.o_h_poly_adaptive → o_h_poly_use_adaptive` | **−5,701 ns** | 50 MHz → HDMI |
| `hdmi_out_vs → vs_d1` | **−5,563 ns** | HDMI → 50 MHz |
| `hdmi_out_vs → vsd` | −5,527 ns | HDMI → 50 MHz |
| `hdmi_out_vs → vs_d0` | −5,505 ns | HDMI → 50 MHz |
| `ascal.o_v_poly_adaptive → o_v_poly_use_adaptive` | −5,500 ns | 50 MHz → HDMI |
| `subcarrier → subcarrier_out` | −5,250 ns | 50 MHz → vídeo +90° |
| `dv_data[18] → hdmi_dv_data[18]` | −4,825 ns | Vídeo +90° → HDMI |
| CPU: `prefetch_queue.head_q[1] → registers.gpr_q[74]` | −3,947 ns | 50 MHz |
| `biu.address_q[23] → u_KFSDRAM.sdram_address[8]` | **−0,476 ns** | 50 MHz |

La peor ruta hacia el controlador SDRAM mejora desde −1,825 ns a −0,476 ns,
pero no se cierra. El peor setup dentro del adaptador de vídeo es +1,510 ns.
No se ha modificado la CPU SPK286.

El siguiente bloque prioritario es el control del filtro adaptativo y el
retorno de VSYNC HDMI a 50 MHz. En RTL, los indicadores adaptativos se escriben
con `poly_clk` durante la carga de coeficientes y se consumen con `o_clk`.
Su traslado debe considerar cuándo acaba la carga de la tabla, para publicar
una configuración coherente. VSYNC requiere una recepción sincronizada y
detección de flanco en el dominio de destino; el comparador actual de `vs_d1`
todavía consume directamente la señal asíncrona.

La mejora de FMax HDMI exige además tratar las rutas síncronas de acumulador
y contadores indicadas arriba. Los datos de vídeo directo necesitan un análisis
de sus modos y relojes antes de elegir un mecanismo de cruce. Estas tareas
siguen pendientes; el resultado positivo de esta tanda no las cubre.

## Recursos

| Recurso | Anterior | Actual | Cambio |
|---|---:|---:|---:|
| ALM necesarios / 41.910 | 27.938 | **27.497** | −441 |
| Registros | 35.723 | **35.252** | −471 |
| LAB / 4.191 | 4.004 | **3.973** | −31 |
| DSP / 112 | 75 | **39** | −36 |
| Bloques RAM / 553 | 409 | 409 | 0 |
| Bits RAM | 3.240.923 | 3.240.923 | 0 |
| PLL / 6 | 3 | 3 | 0 |

Quedan **218 LAB libres (5,20 %)**; ocupación **94,80 %**. El diseño continúa
apretado en LAB. Fijar los bits constantes del modo permite recuperar los
36 DSP añadidos accidentalmente: `ascal` vuelve de 59 a 23 DSP, y el conjunto
de 75 a 39. Sus ALM bajan de 2.379,7 a 2.023,5 y sus registros de 5.106 a 4.680.

## RBF y evidencia

- Fit finalizado el **25/09/2026 a las 06:44:14 locales**.
- RBF: `output_files/PCAT-286_20260925_064223.rbf`.
- `output_files/PCAT-286.rbf` tiene el mismo contenido.
- Generación del RBF: **06:42:23**, tamaño **4.018.956 bytes**.
- SHA-256: `0C555DCD05AA6CEB61FDF4D07B20F9F96D409E8FEB12F8A245A95B879FC0C3F2`.
- Flujo del usuario: síntesis **5:46**, Fitter **15:16**, ensamblado **0:29**,
  TimeQuest **1:47**; total **23:18**.
- Auditorías, fuentes, hashes, comparación y reportes por condición:
  `build/at-scaler-config/20260925-0644-fit/`.

Este RBF sí contiene los tres ajustes: habilitación local de shadowmask,
captura de aspecto y modo del scaler con bits constantes. La verificación de
timing de esas correcciones es positiva; falta la prueba funcional en hardware.

Las auditorías específica y general terminaron con **0 errores y 63 avisos**
cada una, en 3:01 y 2:35, respectivamente. La comprobación adicional HDMI →
HDMI terminó con 0 errores y 11 avisos, en 0:25. Todas usan las cuatro
condiciones del dispositivo y las restricciones del fit revisado.

`check_timing` mantiene 3.713 elementos sin reloj, 20 entradas sin input delay,
85 salidas sin output delay y 21 entradas de `partial_min_max_delay`. No hay
bucles ni latches. Persisten los nombres antiguos del calculador en algunas
restricciones heredadas ignoradas de `sys_top.sdc`. No se declara cobertura
global completa a partir de estos informes.

Se verificaron los hashes de los 36 archivos del candidato y de los 53 archivos
de salida, tanto en el original como en la copia congelada. La revisión no
cambia RTL, QSF, SDC ni el RBF; sólo añade esta evidencia y actualiza el estado
de la documentación. No se ha creado un commit.
