# Scaler HDMI: fit del 25/09/2026, 11:39

## Resultado

El usuario confirma que el nuevo RBF funciona en hardware. La división de
`max(R,G,B)` conserva la funcionalidad en las simulaciones previas y sus dos
etapas cumplen setup y hold en las cuatro condiciones de TimeQuest. El
dominio HDMI completo también tiene setup positivo. **El cierre global de
timing sigue pendiente en CPU/CLK2 y su interfaz con SDRAM.**

La ruta mínima de HDMI ya no está en luminancia: ahora es
`ascal|o_hsize[2] → ascal|o_hacc_next[13]`, con **+0,125 ns** en Slow −40 °C.
Cumple, aunque el margen es pequeño. No se propone otro cambio de RTL en
esta revisión: se conserva este fit como referencia funcional para abordar
CPU/bus en las sesiones dedicadas.

## Trazabilidad y alcance

- Rama `beta-04`, sobre `a8bc4f12e50317f29bb316367e1bbf477aee262b`, cambios
  de esta serie todavía sin commit.
- Los 23 hashes de entrada de la elaboración previa coinciden con los
  archivos actuales, incluido `sys/ascal.vhd`, QSF y SDC.
- Copia congelada de fuentes, base de datos y resultados:
  `build/at-scaler-luminance/20260925-1139-fit/work/`.
- La compilación es del usuario. La revisión sólo ejecuta TimeQuest sobre
  copias aisladas de esa base de datos; no sintetiza ni genera otro RBF.
- Tres procesos TimeQuest: **0 errores**, 51/51/11 advertencias, igual que
  la auditoría anterior. Duraciones: 4:33, 3:36 y 0:24.
  Los dos primeros se ejecutaron en paralelo, en copias
  separadas de la base de datos.
- **172 combinaciones familia/tipo**, todas con rutas presentes en las
  cuatro condiciones. Ninguna familia específica tiene slack negativo.
  `timing_open=1` se mantiene por los caminos globales de CPU/CLK2.
- Se conservan los avisos existentes sobre restricciones incompletas de
  la plataforma; el resultado se refiere a las rutas y relojes analizados.
- No se modifica RTL, QSF ni SDC durante esta revisión.

## Luminancia: rutas corregidas

La antigua ruta combinacional tenía setup **−0,294 ns**. Ha sido sustituida
por dos etapas con la misma latencia total, seguidas por los pesos existentes.
Los siguientes valores son el mínimo de las cuatro condiciones; setup y
hold pueden alcanzar su mínimo en condiciones distintas.

| Familia de rutas | Setup mínimo | Hold mínimo |
|---|---:|---:|
| Píxel H/V → `o_poly_lum_rg` / `o_poly_lum_b` | +1,305 ns | +0,202 ns |
| Máximo parcial y B → `o_poly_lum1` | +1,976 ns | +0,208 ns |
| `o_poly_lum1` → pesos adaptativos | +1,749 ns | +0,106 ns |
| Acumulador → acumulador/subportadora | +13,368 ns | +0,120 ns |
| Pipeline nativo → salida directa | +10,399 ns | +0,365 ns |
| Pipeline HDMI → salida escalada | +0,451 ns | +0,303 ns |

No se añadieron excepciones de timing para conseguir esta mejora. Las
capturas de bus y los sincronizadores anteriores mantienen sus restricciones.

## Comparativa general

Slacks mínimos de las cuatro condiciones. El TNS se compara exclusivamente
en **Slow 1100 mV 100 °C**, sumando los relojes de esa condición una sola vez.

| Medida | Fit 10:30 | Fit 11:39 |
|---|---:|---:|
| Setup mínimo HDMI | −0,294 ns | **+0,125 ns** |
| Setup mínimo CPU / global | −4,932 ns | −4,639 ns |
| Setup mínimo CPU → SDRAM owner | −1,684 ns | −1,149 ns |
| Hold global | +0,081 ns | +0,095 ns |
| Recovery global | +2,520 ns | +2,623 ns |
| Removal global | +0,160 ns | +0,195 ns |
| Ancho mínimo de pulso | +0,793 ns | +0,793 ns |
| TNS setup, Slow 100 °C | −3.667,041 ns | −3.575,923 ns |

El déficit TNS de esa condición baja aproximadamente un 2,5 %. El TNS HDMI
es cero en las cuatro condiciones. Sólo CLK2 conserva grupos de setup
negativos: −4,513 ns / TNS −3.575,923 ns en Slow 100 °C y −4,639 ns /
TNS −3.658,488 ns en Slow −40 °C.

Las peores rutas cambian con la colocación; las cifras anteriores comparan
bloques, no necesariamente los mismos bits de origen y destino:

- CPU: `prefetch_queue|storage_q[5][5] → registers|gpr_q[74]`,
  **−4,639 ns**, Slow −40 °C, ambos extremos en CLK2.
- CPU/SDRAM: `biu|data_active_q~DUPLICATE → u_KFSDRAM|sdram_address[7]`,
  **−1,149 ns**, Slow 100 °C, ambos extremos en CLK2.
- Peor hold: `ascal|o_vpixq_pre[1].r[0] → ascal|o_vpixq[1].r[0]`,
  **+0,095 ns**, Fast −40 °C.

## FMax

Mínimos de las cuatro condiciones. La FMax sólo representa rutas con el
mismo reloj; los cruces y fases se verifican con sus slacks separados.

| Dominio | Fit 10:30 | Fit 11:39 |
|---|---:|---:|
| HDMI | 142,33 MHz | **151,35 MHz** |
| CPU / CLK2 | 40,11 MHz | 40,59 MHz |
| Avalon | 165,18 MHz | 168,46 MHz |
| Vídeo base | 33,20 MHz | 32,56 MHz |
| Vídeo ×2 | 75,18 MHz | 80,54 MHz |
| Vídeo +90° | 84,23 MHz | 88,57 MHz |
| CLK1 | 86,44 MHz | 82,55 MHz |
| Audio | 38,04 MHz | 37,20 MHz |

HDMI supera los 148,54 MHz analizados. Las cifras FMax de los relojes
derivados del mux no se presentan como frecuencia admisible de enlace.

## Recursos y duración

| Recurso | Fit 10:30 | Fit 11:39 | Libres ahora |
|---|---:|---:|---:|
| LAB | 3.952 | 3.970 / 4.191 | **221 (5,27 %)** |
| ALM | 27.185 | 27.708 / 41.910 | 14.202 |
| Registros | 35.655 | 35.637 | — |
| M10K | 409 | 409 / 553 | 144 |
| DSP | 39 | 39 / 112 | 73 |
| PLL | 3 | 3 / 6 | 3 |

El fit usa 18 LAB más. La variación global incluye decisiones de
optimización y colocación en todo el diseño, no sólo los ocho bits añadidos
en RTL. En la atribución jerárquica, `ascal` pasa de 2.003,3 a 2.019,7 ALM
y de 4.702 a 4.725 registros; su memoria permanece igual. Los registros
totales del resumen incluyen recursos no contabilizados en esa tabla
jerárquica.

Compilación del usuario: **24:57** de tiempo total; Analysis & Synthesis
5:55, Fitter 16:45, Assembler 0:28 y TimeQuest 1:49. CPU total: 1:00:19.

## RBF probado

`output_files/PCAT-286_20260925_113743.rbf`, **4.051.896 bytes**.

SHA256: `3E9697C7721265FDDA791BF1EA7DE06F5BB3339B8EFAA5C3206B4B91C62815C6`.

La copia `\\192.168.0.135\sdcard\_Computer\PCAT-286_20260925_113743.rbf`
tiene el mismo hash. Se conserva el RBF generado y probado por el usuario.
