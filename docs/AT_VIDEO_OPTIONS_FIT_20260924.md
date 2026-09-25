# Fit del perfil EGA y opciones OSD — 24/09/2026, 21:46

Actualización posterior: `AT_SCANLINES_STATUS_FIT_20260924.md` documenta el fit
de las 22:41, que ya cierra el retorno de scanlines y conserva las correcciones
anteriores. Este documento mantiene los resultados del primer fit y el ajuste
que motivó; su RBF es anterior al arreglo del retorno.

## Conclusión

**El perfil EGA y el trayecto de opciones OSD hacia vídeo cumplen en las cuatro
esquinas. La revisión completa encuentra un retorno de scanlines a HPS que
todavía falla con −5,431 ns. No se declara cerrada esta tanda.**

Se ha preparado una corrección RTL de ese retorno, descrita al final. Requiere
otro fit: el RBF revisado aquí es anterior a esa corrección.

Los 20 archivos del manifiesto previo coincidían con los fuentes al empezar
la revisión. Se conservaron netlist, informes y fuentes en
`build/at-video-options/20260924-fit/work/`. Las auditorías usan esa copia y su
SDC original, incluso después de preparar el ajuste RTL posterior.

## Rutas intervenidas: resultado físico

Peores márgenes entre las cuatro esquinas:

| Trayecto | Setup/max-delay | Hold |
|---|---:|---:|
| Payload conjunto de geometría/perfil → captura | +8,237 ns | Excluido por protocolo |
| Perfil capturado → consumidores de vídeo | **+11,232 ns** | **+0,574 ns** |
| Petición del mailbox de geometría, primera → segunda etapa | +33,760 ns | +0,246 ns |
| Acuse del mailbox de geometría, primera → segunda etapa | +18,718 ns | +0,270 ns |
| Payload OSD → captura | +10,238 ns | Excluido por protocolo |
| Captura OSD → aplicación en blanking | **+15,167 ns** | **+0,252 ns** |
| Petición OSD, primera → segunda etapa | +16,381 ns | +0,226 ns |
| Acuse OSD, primera → segunda etapa | +18,786 ns | +0,253 ns |
| Opciones aplicadas → todos los consumidores | **−5,431 ns** | +0,217 ns |

Antes fallaban `applied[1] → ega_monitor_profile_video_sync1_q[1]` con
−6,106 ns y `status[9] → at_video_ary_q[0]` con −5,866 ns. Los registros de
sincronización independiente del perfil ya no existen.

El payload de geometría tiene 16 registros de origen y 18 de destino por las
duplicaciones del Fitter. Los retardos de datos máximos reportados son
4,294 ns para geometría/perfil y 1,696 ns para OSD, dentro de sus presupuestos
de 10 ns y de la ventana de asentamiento del handshake.

El primer filtro del informe del perfil buscaba sólo consumidores dentro de
`u_ega` y devolvió cero rutas. Se corrigió el alcance: el perfil también actúa
sobre señales que terminan registrándose fuera de ese módulo. Una auditoría
suplementaria sobre la misma netlist (`profile_consumers/`) reportó 20 rutas
de setup y 20 de hold por esquina, con los márgenes de la tabla. El script
principal ya incluye ese alcance para los próximos fits. No se interpretan
los informes vacíos originales como una comprobación satisfactoria.

## Retorno de scanlines detectado

La escala aplicada en `u_at_video_options` se decodifica en `VGA_SL`. El
procesado VGA la consume en el reloj de vídeo, pero `sys_top` también la
capturaba directamente en `sl_r`, a 50 MHz, para responder al comando HPS
`0x2B`. Ese segundo cruce es asíncrono y no estaba resuelto por el mailbox de ida.

Las cuatro rutas negativas de esa familia en Slow/100 °C son:

| Ruta | Setup |
|---|---:|
| `scale[1] → sl_r[0]` | −5,431 ns |
| `scale[1] → sl_r[1]` | −5,399 ns |
| `scale[0] → sl_r[0]` | −5,186 ns |
| `scale[0] → sl_r[1]` | −5,162 ns |

Los consumidores de aspecto entre los relojes de vídeo relacionados siguen
siendo rutas de timing reales; entre las reportadas a Slow/100 °C aparece un
margen de +0,267 ns. No se han excluido por ser ajustes OSD.

## Comparación global

| Métrica | Fit anterior | Este fit |
|---|---:|---:|
| Peor setup | −6,106 ns | **−5,881 ns** |
| Peor hold | +0,084 ns | **+0,066 ns** |
| Recovery | +3,789 ns | +3,743 ns |
| Removal | +0,385 ns | +0,276 ns |
| Ancho mínimo de pulso | +0,793 ns | +0,793 ns |
| TNS setup, Slow/100 °C | −6.628,166 ns | −6.537,149 ns |
| Grupos reloj/esquina con setup negativo | 20 | **12** |

El peor setup mejora 0,225 ns y la magnitud del TNS mejora 91,017 ns (1,37 %).
El hold permanece positivo, con menos margen. Los relojes de vídeo base y ×2
tienen ahora setup mínimo +5,260 y +1,766 ns, respectivamente; la salida
de vídeo +90° todavía tiene rutas negativas.

FMax mínimo entre las cuatro esquinas, en MHz:

| Dominio | Requerido | Anterior | Este fit |
|---|---:|---:|---:|
| CPU / `FPGA_CLK2_50` | 50 | 42,43 | **41,42** |
| HDMI | 148,54 | 109,10 | **113,10** |
| Avalon HPS | 100 | 171,44 | 169,95 |
| Vídeo base | 28,64 | 32,55 | 33,72 |
| Vídeo ×2 | 57,27 | 74,52 | 74,37 |
| Vídeo de salida +90° | 57,27 | 91,05 | 87,10 |
| `FPGA_CLK1_50` | 50 | 84,40 | 89,13 |
| Audio | 24,58 | 37,83 | 37,56 |

FMax no incluye cruces entre relojes distintos. CPU y HDMI siguen por debajo
de sus frecuencias requeridas. La mejora no es uniforme entre dominios.

## Recursos y tiempo

| Recurso | Anterior | Este fit |
|---|---:|---:|
| ALM necesarios / 41.910 | 27.601 | **27.264** |
| Registros | 33.736 | 33.649 |
| LAB ocupados / 4.191 | 3.934 | **3.923** |
| RAM: bloques / bits | 409 / 3.240.923 | Sin cambio |
| DSP / PLL | 39 / 3 | Sin cambio |

Se recuperan 337 ALM y 11 LAB en el resultado global. Quedan **268 LAB libres
(6,39 %)**; la ocupación sigue siendo alta, 93,61 %. Estos valores incluyen
las variaciones de optimización y colocación de todo el diseño, no sólo el
coste de los nuevos registros.

Duración del flujo: síntesis **6:02**, Fitter **16:04**, ensamblado **0:26**,
TimeQuest **1:42**; total **24:14**.

## Otras rutas pendientes y regresiones

La peor ruta ahora es `LFB_EN → hmini[4]`, **−5,881 ns**. Hacia HDMI destaca
`LFB_EN → ascal|o_mode[2]`, **−5,643 ns**. Los controles de geometría/LFB y
VRR continúan siendo la siguiente familia de trabajo tras cerrar scanlines.

SPK286 no se modifica: su peor ruta interna observada es
`prefetch_queue|storage_q[4][1] → registers|gpr_q[70]`, **−4,141 ns**. El peor
camino al controlador SDRAM observado parte ahora de `main_rom_loaded` hacia
`sdram_address[7]`, **−0,171 ns**.

Las familias anteriores de Avalon, packed/planar, contador VSYNC y shadowmask
siguen cumpliendo en las cuatro esquinas. Ejemplos: comandos de lectura y
escritura +1,830/+2,440 ns; sincronizador VSYNC +18,709 ns de setup y +0,290 ns
de hold; controles locales de shadowmask +2,932/+0,204 ns.

`check_timing` mantiene 3.713 elementos sin reloj y cero bucles/latches.
`partial_min_max_delay` pasa de 17 a 18 por el payload OSD. Las auditorías
principal y general terminan con 0 errores/58 avisos; la suplementaria del
perfil, 0 errores/2 avisos. El diseño sigue sin cobertura/cierre global completo.

## RBF revisado y ajuste posterior

Binario generado por el usuario el **24/09/2026 a las 21:44:50**:

- `output_files/PCAT-286_20260924_214450.rbf` y `output_files/PCAT-286.rbf`.
- Tamaño: **4.049.264 bytes**.
- SHA-256: `083017FC1B073E31BA8C2FC65B341976A6A41225AF740A16292638989C31358B`.

Después de este fit se añadió `at_scanlines_status`: toma juntos los dos bits
de intensidad en `clk_vid`, los transfiere mediante payload retenido y acuse a
`clk_sys`, y aplica allí la anulación por `FB_EN` antes de responder a HPS.
El camino VGA conserva su valor aplicado. El retorno tiene un presupuesto
max-delay de 10 ns; sus etapas siguientes y la respuesta HPS mantienen setup
y hold normales. No se excluye la ruta que fallaba sin reparar el protocolo.

La simulación conjunta de opciones y retorno pasa 128 combinaciones y 137
comprobaciones, con reloj de salida +90°, reloj de vídeo detenido, reset local,
transacciones HPS parciales y anulación por framebuffer. Este ajuste posterior
necesita un nuevo fit antes de afirmar que las rutas activas cumplen.

Quartus Analysis & Elaboration del ajuste terminó el 24/09/2026 a las
22:11:51 locales con **0 errores y 130 avisos**, sin síntesis ni Fitter.
El manifiesto para la próxima compilación está en
`build/at-video-options/scanlines-candidate-source-manifest.json`; los logs,
en `build/at-video-options/scanlines-candidate/`.
