# Fit de geometría y scaler — 25/09/2026, 05:59

## Resultado

**El rediseño reduce el TNS un 59,4 %, pero esta tanda todavía no está cerrada.**
Se detectan dos rutas activas negativas relacionadas con la integración nueva
y una regresión de recursos. Se han preparado los ajustes RTL descritos al
final; sus resultados físicos requieren otra compilación.

Los 33 archivos del manifiesto del candidato coincidían al iniciar la revisión.
Fuentes, SDC, netlist e informes originales están congelados en
`build/at-scaler-config/20260925-fit/work/`. Ambas auditorías TimeQuest usan
esa copia, incluso después de modificar el candidato posterior.

## Rutas intervenidas

Peores márgenes entre las cuatro condiciones Slow/Fast, −40/100 °C:

| Familia | Setup / max-delay | Hold |
|---|---:|---:|
| Geometría: payload → captura | +9,307 ns | Excluido por protocolo |
| Geometría: captura → configuración del cálculo | +7,617 ns | +0,156 ns |
| Configuración del cálculo → consumidores | +7,595 ns | +0,192 ns |
| Cuadro: payload → captura HDMI | **+0,685 ns** | Excluido por protocolo |
| Cuadro: petición, primera → segunda etapa | +4,798 ns | +0,475 ns |
| Cuadro: acuse, primera → segunda etapa | +16,281 ns | +0,270 ns |
| Cuadro aplicado → todos los consumidores | **−5,254 ns** | +0,150 ns |
| Actualización/reinicio del raster → scaler | +2,938 ns | +0,227 ns |
| Modo de entrada → `ascal.i_mode` | +10,283 ns | +0,940 ns |
| Retorno del aspecto: payload → captura | +3,304 ns | Excluido por protocolo |
| Aspecto capturado → respuesta HPS | +15,155 ns | +0,196 ns |
| Opciones OSD → consumidores | **−0,118 ns** | +0,202 ns |

Las anteriores capturas directas de `HDMI_PR`, `LFB_EN`, modo y habilitación
han sido sustituidas por los paquetes y las etapas locales de estas familias.
El conjunto aún falla por los dos consumidores siguientes:

1. `scaler_frame_config|dst_data[235]` (LFB aplicado en HDMI) →
   `HDMI_shadowmask|g_at_config.config_mailbox|payload_q[10]`: **−5,254 ns**.
   El puerto `enable` del shadowmask todavía se incorporaba a su paquete de
   configuración en `clk_sys`. Al suministrarle el LFB aplicado en HDMI se
   había creado un cruce de vuelta a 50 MHz. Es un CDC real.
2. `u_at_video_options|arx[0]` → `u_at_scaler_config|active_q.fb_base[12]`:
   **−0,118 ns**. El aspecto interviene en la detección de cambios que habilita
   la carga de todo el paquete del calculador. Esa lógica quedaba dentro de
   los 4,365 ns entre vídeo ×2 y vídeo +90°. Son relojes relacionados y la
   ruta debe cumplir timing normal.

Se comprobaron **99 combinaciones de familia/tipo**, cada una con rutas activas
en las cuatro condiciones. Sólo las dos familias señaladas presentan setup
negativo; todos sus holds son positivos. No se interpretan grupos vacíos como
comprobaciones satisfactorias.

Los retardos máximos de datos de geometría, cuadro y aspecto son 3,034, 2,848
y 1,845 ns, respectivamente. El margen del paquete de cuadro (+0,685 ns) es
positivo pero debe comprobarse de nuevo tras cada fit.

Las anteriores familias Avalon, packed/planar, VSYNC, perfil EGA y scanlines
mantienen márgenes positivos. Ejemplos: payload de lectura/escritura Avalon
+1,588/+1,859 ns; consumidores locales de shadowmask +3,447 ns de setup y
+0,190 ns de hold. El fallo de shadowmask encontrado aquí está en su origen
de configuración, fuera del tramo local que ya se había reparado.

## Comparación global

| Métrica | Fit anterior | Este fit |
|---|---:|---:|
| Peor setup | −5,877 ns | **−5,458 ns** |
| Peor hold | +0,045 ns | **+0,067 ns** |
| Recovery | +3,445 ns | +2,798 ns |
| Removal | +0,328 ns | +0,260 ns |
| Ancho mínimo de pulso | +0,793 ns | +0,793 ns |
| TNS setup, Slow/100 °C | −6.611,606 ns | **−2.683,257 ns** |
| Grupos reloj/condición con setup negativo | 12 | 12 |

El peor setup mejora 0,419 ns. La magnitud del TNS baja 3.928,349 ns (59,4 %).
Esto no equivale a cierre global ni implica que todas las rutas mejoren.

FMax mínima entre las cuatro condiciones, en MHz:

| Dominio | Requerido | Anterior | Este fit |
|---|---:|---:|---:|
| CPU / `FPGA_CLK2_50` | 50 | 41,51 | **41,91** |
| HDMI | 148,54 | 119,85 | **105,09** |
| Avalon HPS | 100 | 180,90 | **146,56** |
| Vídeo base | 28,64 | 31,98 | 31,88 |
| Vídeo ×2 | 57,27 | 76,27 | 84,32 |
| Vídeo +90° | 57,27 | 87,86 | 81,96 |
| `FPGA_CLK1_50` | 50 | 90,64 | 85,95 |
| Audio | 24,58 | 38,21 | 37,38 |

FMax sólo considera caminos dentro de un mismo reloj. CPU y HDMI siguen por
debajo de sus frecuencias requeridas; HDMI y Avalon retroceden en este fit.

Otras rutas pendientes, fuera de los ajustes posteriores de esta tanda:

- `hdmi_out_vs → vsd`: **−5,458 ns**, HDMI → HPS.
- `hdmi_out_vs → vs_d0`: −5,442 ns, HDMI → HPS.
- `ascal.o_h_poly_adaptive → o_h_poly_use_adaptive`: **−5,351 ns**, 50 MHz → HDMI.
- `subcarrier → subcarrier_out`: −5,230 ns, 50 MHz → vídeo +90°.
- `dv_data[16] → hdmi_dv_data[16]`: −4,830 ns, vídeo +90° → HDMI.
- CPU interna: `events.event_error_valid → registers.gpr_q[69]`: **−3,860 ns**.
- `biu.ack_active_q → u_KFSDRAM.sdram_address[8]`: **−1,825 ns**; el peor margen
  al controlador SDRAM empeora desde −0,087 ns. No se ha modificado SPK286.

## Recursos

| Recurso | Anterior | Este fit | Cambio |
|---|---:|---:|---:|
| ALM necesarios / 41.910 | 27.190 | **27.938** | +748 |
| Registros | 33.667 | **35.723** | +2.056 |
| LAB / 4.191 | 3.927 | **4.004** | +77 |
| DSP / 112 | 39 | **75** | +36 |
| Bloques RAM / 553 | 409 | 409 | 0 |
| Bits RAM | 3.240.923 | 3.240.923 | 0 |
| PLL / 6 | 3 | 3 | 0 |

Quedan **187 LAB libres (4,46 %)**; ocupación **95,54 %**. Esta regresión de
recursos debe corregirse antes de considerar aceptada la tanda.

El informe por entidad sitúa los 36 DSP adicionales en `ascal`, que pasa
de 23 a 59 DSP. `u_at_scaler_config` usa **0 DSP**, 403,7 ALM y 2.181 registros
en esta colocación. No se pueden sumar LAB por entidad porque pueden compartirse.

El modo original sólo variaba en los bits `[3:2]`; `[4]` y `[1:0]` eran constantes.
Transportar el modo completo por registros preservados dejó visibles para la
síntesis códigos de interpolación que el core no selecciona. La netlist incluso
conserva cuatro bits en `i_mode`, frente a los dos variables del protocolo.
El ajuste posterior fija esos bits a cero en ambos puertos del scaler. El
coste físico que se recupere debe medirse; aún no se afirma volver a 39 DSP.

Flujo del usuario: síntesis **5:48**, Fitter **15:48**, ensamblado **0:28**,
TimeQuest **1:45**; total **23:49**. Fitter y flujo correctos.

## Cobertura y evidencia

Las auditorías específica y general terminaron con **0 errores y 63 avisos**
cada una. `check_timing` mantiene 3.713 elementos sin reloj, cero bucles/latches
y 21 entradas de `partial_min_max_delay` (antes 19). Persisten restricciones
heredadas de `sys_top.sdc` que apuntan a los antiguos nombres del calculador y
se ignoran por no existir esos registros. Los grupos nuevos sí tienen rutas.
No se declara cobertura completa ni cierre global.

RBF correspondiente exclusivamente al fit revisado:

- `output_files/PCAT-286_20260925_055724.rbf`, copia conservada del RBF del usuario.
- Tamaño: **4.009.756 bytes**; generado a las **05:57:24**, hora local.
- SHA-256: `7709B768D5A8FA3F2A9D3D9AB0D52A524EC18A577299C02271A5C6318C5462E8`.
- `output_files/PCAT-286.rbf` conserva el mismo contenido al terminar la revisión.
- Informes, hashes, fuentes originales y análisis: `build/at-scaler-config/20260925-fit/`.

## Ajuste posterior, listo para otra compilación

1. `shadowmask.AT_VIDEO_ENABLE`: usa la habilitación del framebuffer directamente
   en HDMI y la retira del paquete que se forma a 50 MHz. El comportamiento
   anterior se conserva por defecto para otros llamadores.
2. `aspect_video_q`: captura primero ARX/ARY en vídeo +90°. Sólo esa conexión
   directa usa el cuarto de ciclo; la comparación y la habilitación del paquete
   disponen después de un ciclo completo. No se cambia ni se excluye la relación
   de fase de los relojes.
3. Los puertos de modo de `ascal` reciben `{1'b0, modo[3:2], 2'b00}`, igual que
   en la integración original, para eliminar interpoladores no seleccionables.

No se amplían presupuestos ni se añaden `false_path`. La auditoría del próximo
fit añade comprobaciones explícitas de la captura de aspecto y sus consumidores.

Pruebas del ajuste: controlador **PASS, 14 comprobaciones**; contador VSYNC
**PASS, 272 flancos**; shadowmask **PASS, 18.432 píxeles comparados**, cuatro
modos, 2.048 escrituras LUT, transacción parcial, reloj detenido y habilitación
local HDMI. El VHDL del scaler no cambia respecto al fit y mantiene las cuatro
simulaciones Avalon del candidato previo.

Quartus Analysis & Elaboration del ajuste terminó el **25/09/2026 a las
06:10:34 locales**, con **0 errores y 131 avisos**, sin síntesis ni Fitter.
Logs: `build/at-scaler-config/revised-candidate/`. Manifiesto para el siguiente
fit: `build/at-scaler-config/revised-candidate-source-manifest.json`.
El RBF anterior **no contiene estos tres ajustes**. Debe recompilarse
`PCAT-286.qsf` y repetirse TimeQuest antes de cerrar las rutas activas.
