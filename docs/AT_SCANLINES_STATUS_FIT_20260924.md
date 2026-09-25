# Fit del retorno de scanlines a HPS — 24/09/2026, 22:41

## Conclusión

**La tanda de perfil EGA, opciones OSD y retorno de scanlines cumple timing
en las cuatro condiciones de TimeQuest. El proyecto completo sigue abierto.**

La captura directa `scale → sl_r`, que fallaba con −5,431 ns en el fit anterior,
se sustituye por un snapshot coherente de dos bits con petición y acuse.
El payload retenido cumple su presupuesto; los sincronizadores, la aplicación
local y la lectura HPS tienen setup y hold positivos. Las familias corregidas
anteriormente también mantienen márgenes positivos.

Los 21 archivos de `build/at-video-options/scanlines-candidate-source-manifest.json`
coincidían al iniciar la revisión. Se congelaron fuentes, SDC, netlist e informes
en `build/at-scanlines-status/20260924-fit/work/`. Sobre esa copia se ejecutó
TimeQuest 17.0.2, sin síntesis ni Fitter y sin cambiar el SDC del fit.

## Rutas corregidas

Peores márgenes entre Slow/100 °C, Slow/−40 °C, Fast/100 °C y Fast/−40 °C:

| Trayecto | Setup / max-delay | Hold |
|---|---:|---:|
| Retorno: payload retenido → captura | **+3,660 ns** | Excluido por protocolo |
| Retorno: petición, primera → segunda etapa | +18,794 ns | +0,245 ns |
| Retorno: acuse, primera → segunda etapa | +16,266 ns | +0,258 ns |
| Retorno: captura → registro `status` | +18,600 ns | +0,247 ns |
| Retorno: `status` → `io_dout_sys` | **+17,285 ns** | **+0,543 ns** |
| Opciones OSD aplicadas → todos los consumidores | **+0,253 ns** | +0,173 ns |
| Captura OSD → aplicación en blanking | +14,217 ns | +0,230 ns |
| Payload OSD → captura | +10,633 ns | Excluido por protocolo |
| Perfil EGA capturado → consumidores | +10,898 ns | +0,734 ns |
| Payload geometría/perfil → captura | +8,639 ns | Excluido por protocolo |

El mínimo del conjunto de consumidores OSD pasa de −5,431 a +0,253 ns.
Son rutas distintas antes y después del rediseño: el margen restante más
estrecho corresponde a `u_at_video_options|arx[0] → arx[*]/arxy`, entre los
relojes de vídeo ×2 y salida +90°. Esa relación de fase se analiza normalmente;
no se ha excluido. El margen positivo es pequeño y debe vigilarse en futuros fits.

La transferencia nueva presenta dos rutas activas de payload, dos de aplicación
y dos de lectura HPS por condición, más petición y acuse. El perfil y los
consumidores OSD tienen 20 rutas reportadas por tipo y condición. No hay grupos
específicos vacíos ni márgenes negativos. El indicador `timing_open=1` se
mantiene por las violaciones globales.

El retardo máximo de datos del payload de retorno es **1,485 ns**, dentro del
presupuesto de 10 ns y la ventana de asentamiento del handshake. Los payloads
OSD y geometría/perfil alcanzan 1,040 y 3,893 ns. Se mantienen las excepciones
limitadas a las primeras etapas asíncronas y al hold de los buses retenidos;
las etapas siguientes siguen verificadas con setup/hold normales.

## Comparación global

Referencia: fit de las 21:46, documentado en `AT_VIDEO_OPTIONS_FIT_20260924.md`.

| Métrica | Antes | Ahora |
|---|---:|---:|
| Peor setup | −5,881 ns | **−5,877 ns** |
| Peor hold | +0,066 ns | **+0,045 ns** |
| Recovery | +3,743 ns | +3,445 ns |
| Removal | +0,276 ns | +0,328 ns |
| Ancho mínimo de pulso | +0,793 ns | +0,793 ns |
| TNS de setup, Slow/100 °C | −6.537,149 ns | **−6.611,606 ns** |
| Grupos reloj/condición con setup negativo | 12 | 12 |

El peor setup global apenas cambia (+0,004 ns). La magnitud del TNS empeora
74,457 ns, un 1,14 %, y el margen de hold disminuye 0,021 ns, aunque permanece
positivo. Cerrar la familia intervenida no supone una mejora uniforme del fit.

FMax mínima entre las cuatro condiciones, en MHz:

| Dominio | Requerido | Antes | Ahora |
|---|---:|---:|---:|
| CPU / `FPGA_CLK2_50` | 50 | 41,42 | **41,51** |
| HDMI | 148,54 | 113,10 | **119,85** |
| Avalon HPS | 100 | 169,95 | **180,90** |
| Vídeo base | 28,64 | 33,72 | 31,98 |
| Vídeo ×2 | 57,27 | 74,37 | 76,27 |
| Vídeo de salida +90° | 57,27 | 87,10 | 87,86 |
| `FPGA_CLK1_50` | 50 | 89,13 | 90,64 |
| Audio | 24,58 | 37,56 | 38,21 |

FMax sólo considera caminos dentro del mismo reloj. No sustituye al análisis
de cruces. CPU y HDMI continúan por debajo de sus frecuencias requeridas.

## Rutas pendientes y siguiente intervención

| Ruta observada | Setup | Relación |
|---|---:|---|
| `HDMI_PR → videow[9]` | **−5,877 ns** | 50 MHz → vídeo de salida +90° |
| `lowlat → ascal\|i_mode[3]` | −5,790 ns | 50 MHz → vídeo de salida +90° |
| `LFB_EN → hmini[*]` | −5,749 ns | 50 MHz → vídeo de salida +90° |
| `lowlat → ascal\|o_mode[3]` | **−5,732 ns** | 50 MHz → HDMI |
| `scaler_out → ascal\|o_vpix_outer/inner[*]` | −5,666 ns | 50 MHz → HDMI |
| CPU: `prefetch_queue\|storage_q[3][1] → events\|event_error_code[9]` | −4,093 ns | Interna de 50 MHz |
| `biu\|data_active_q → u_KFSDRAM\|sdram_address[7]` | −0,087 ns | Interna de 50 MHz |

La siguiente familia fuera de SPK286 es la configuración de geometría y modo
del scaler: `HDMI_PR`, `LFB_EN`, límites LFB, `lowlat`, `scaler_out` y sus campos
asociados. En `sys_top` la geometría se calcula en `clk_vid`, mientras estos
controles proceden del dominio HPS. El scaler también captura `mode` desde
sus dominios de entrada y salida. Deben definirse las actualizaciones completas
de cada configuración y transferirlas con datos retenidos y acuse hacia cada
dominio consumidor, aplicándolas en una frontera segura del vídeo. El análisis
debe abarcar sus consumidores directos para evitar dejar otro retorno sin tratar.

Éste es el siguiente trabajo propuesto; este fit no contiene su corrección.
No se ha modificado SPK286 durante esta tanda. Su ruta interna peor mejora
de −4,141 a −4,093 ns por el resultado global de colocación, pero sigue fallando.

Las correcciones anteriores mantienen márgenes positivos en las cuatro
condiciones, por ejemplo:

| Familia | Setup / max-delay | Hold |
|---|---:|---:|
| Payload de comandos de lectura Avalon | +1,577 ns | Excluido por protocolo |
| Payload de comandos de escritura Avalon | +2,350 ns | Excluido por protocolo |
| Dirección de lectura → Avalon | +5,150 ns | +0,307 ns |
| Dirección de escritura → Avalon | +8,088 ns | +0,225 ns |
| Packed/planar, segunda etapa | +18,680 ns | +0,288 ns |
| VSYNC, segunda etapa | +18,805 ns | +0,244 ns |
| Shadowmask, consumidores locales | +3,813 ns | +0,209 ns |

Se verificaron 77 combinaciones de familia/tipo de timing específicas, cada
una con rutas activas y margen positivo en las cuatro condiciones. Las dos
ejecuciones de TimeQuest finalizaron con **0 errores y 58 avisos** cada una.
Los hashes de los informes y binarios originales y congelados permanecen
iguales tras la auditoría.

`check_timing` mantiene 3.713 elementos sin reloj, cero bucles y cero latches.
`partial_min_max_delay` pasa de 18 a 19 al añadir el presupuesto del nuevo
payload. `report_ucp` mantiene 10 puertos de entrada y 52 de salida sin
restricción. Estos asuntos de cobertura previos impiden afirmar una validación
temporal completa de todo el proyecto.

## Recursos y tiempos

| Recurso | Antes | Ahora |
|---|---:|---:|
| ALM necesarios / 41.910 | 27.264 | **27.190** |
| Registros | 33.649 | **33.667** |
| LAB ocupados / 4.191 | 3.923 | **3.927** |
| Bloques RAM / 553 | 409 | 409 |
| Bits RAM / 5.662.720 | 3.240.923 | 3.240.923 |
| DSP / 112 | 39 | 39 |
| PLL / 6 | 3 | 3 |

Quedan **264 LAB libres (6,30 %)**; la ocupación es **93,70 %**. Se consumen
cuatro LAB más y 18 registros, mientras el total de ALM baja 74. Estos deltas
incluyen cambios de optimización y colocación de todo el diseño.

Flujo ejecutado por el usuario: síntesis **5:43**, Fitter **15:59**, ensamblado
**0:28**, TimeQuest **1:45**; total **23:55**. El Fitter terminó correctamente.

## RBF y evidencia

- Binario: `output_files/PCAT-286_20260924_223910.rbf`.
- Generado el **24/09/2026 a las 22:39:10**, hora local; fin del flujo a las 22:41.
- Tamaño: **4.022.280 bytes**.
- SHA-256: `E80ECA5D9CE243B1EFC3F980F5F111194BAA15B6CC0D4C76F831F9D66AB53433`.
- `output_files/PCAT-286.rbf` tiene el mismo hash al realizar esta revisión.
- Auditoría: `build/at-scanlines-status/20260924-fit/`, con manifiestos,
  fuentes congelados, `focused/`, `timing/`, logs y `analysis.json`.

La simulación previa del candidato pasó 128 combinaciones y 137 comprobaciones,
incluyendo transacciones HPS parciales, parada del reloj, reset y anulación
por framebuffer. Analysis & Elaboration pasó con 0 errores y 130 avisos.
Los fuentes auditados son los mismos. La comprobación funcional del nuevo RBF
en hardware sigue pendiente del usuario; este informe acredita los márgenes
físicos de las rutas enumeradas, sin afirmar cierre global del proyecto.
