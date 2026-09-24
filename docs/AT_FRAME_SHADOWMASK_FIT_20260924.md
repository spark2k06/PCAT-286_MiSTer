# Fit de VSYNC y shadowmask — 24/09/2026, 20:46

## Resultado

**Las rutas sustitutas de VSYNC y configuración de shadowmask cumplen en las
cuatro esquinas. El proyecto completo sigue teniendo violaciones de setup.**
Las familias de vídeo y Avalon corregidas en `061030c` también siguen cumpliendo.

Los 15 hashes del manifiesto previo coinciden con los archivos disponibles,
incluidos QSF, RTL, SDC y script de auditoría. El informe original de TimeQuest
reconoce el nuevo contador y los 11 bits del mailbox de shadowmask. La revisión
posterior usa una copia de esa netlist, con sus restricciones correspondientes;
no modifica RTL ni SDC y no ejecuta síntesis ni Fitter.

La referencia inmediata es el fit documentado en
`AT_VIDEO_AVALON_CDC_FIT_20260924.md`.

## Rutas intervenidas

Peores márgenes entre Slow/Fast y −40/100 °C. Las rutas de primera a segunda
etapa y toda la lógica local mantienen análisis normal de setup y hold.

| Ruta nueva | Peor setup/max-delay | Peor hold |
|---|---:|---:|
| Formación de VS → registro en el dominio de vídeo | +13,097 ns | +0,601 ns |
| VSYNC: primera → segunda etapa en `clk_sys` | +18,750 ns | +0,269 ns |
| Detección de flanco → contador | +17,986 ns | +0,374 ns |
| Shadowmask: payload retenido → captura | +5,263 ns | Excluido por protocolo |
| Shadowmask: primera → segunda etapa de petición | +5,590 ns | +0,226 ns |
| Shadowmask: primera → segunda etapa de acuse | +18,762 ns | +0,260 ns |
| Shadowmask: captura → aplicación en VS | +4,588 ns | +0,215 ns |
| Shadowmask: configuración aplicada → lógica local HDMI | +3,610 ns | +0,215 ns |

La familia anterior VSYNC→contador tenía −6,356 ns; las anteriores de
dimensiones y rotación de shadowmask tenían −6,168 y −6,023 ns. La comparación
corresponde a sus nuevos caminos funcionales, no a una relajación de sus relojes.

El bus del mailbox de shadowmask presenta como máximo **1,641 ns de retardo de
datos** entre las rutas reportadas. Cumple el presupuesto max-delay de 5 ns;
la captura espera las dos etapas de petición y mantiene el payload hasta el
acuse. Las exclusiones se limitan a primeras etapas y hold del bus retenido,
según `AT_FRAME_SHADOWMASK_CDC.md`.

### Regresión de las correcciones anteriores

| Familia | Peor setup/max-delay | Peor hold |
|---|---:|---:|
| Comando de lectura Avalon | +2,398 ns | Excluido por protocolo |
| Comando de escritura Avalon | +2,151 ns | Excluido por protocolo |
| Dirección local → Avalon, lectura | +4,167 ns | +0,339 ns |
| Dirección local → Avalon, escritura | +7,371 ns | +0,222 ns |
| Selección VGA: decode registrado | +29,991 ns | +1,246 ns |
| Selección VGA: primera → segunda etapa | +18,683 ns | +0,298 ns |
| Snapshot de bancos | +7,125 ns | Excluido por protocolo |
| Snapshot de historial de campos | +2,794 ns | Excluido por protocolo |
| Snapshot de configuración del framebuffer | +9,669 ns | Excluido por protocolo |

Todos sus sincronizadores tienen márgenes positivos. Los mayores retardos de
datos reportados de los comandos son 1,731 ns en lectura y 2,139 ns en escritura.
No reaparecen los registros de offsets asíncronos antiguos. Las colecciones de
cada familia contienen registros y se reportan rutas activas en cada esquina.

## Timing global y FMax

| Métrica | Fit anterior | Fit nuevo |
|---|---:|---:|
| Peor setup | −6,356 ns | **−6,106 ns** |
| Peor hold | +0,026 ns | **+0,084 ns** |
| Recovery | +3,797 ns | +3,789 ns |
| Removal | +0,371 ns | +0,385 ns |
| Ancho mínimo de pulso | +0,793 ns | +0,793 ns |
| TNS de setup, Slow 1100 mV / 100 °C | −8.209,493 ns | **−6.628,166 ns** |

El peor setup mejora 0,250 ns. La magnitud del TNS mejora 1.581,327 ns, un
**19,3 %**. Persisten 20 grupos reloj/esquina con setup negativo; esa cifra no
representa el número de rutas individuales que fallan.

FMax mínimo de las cuatro esquinas, en MHz:

| Dominio | Requerido | Anterior | Nuevo |
|---|---:|---:|---:|
| CPU / `FPGA_CLK2_50` | 50 | 40,14 | **42,43** |
| HDMI | 148,54 | 108,07 | **109,10** |
| Avalon HPS | 100 | 148,46 | **171,44** |
| Vídeo base | 28,64 | 33,13 | 32,55 |
| Vídeo ×2 | 57,27 | 85,46 | 74,52 |
| Vídeo de salida +90° | 57,27 | 87,05 | 91,05 |
| `FPGA_CLK1_50` | 50 | 83,12 | 84,40 |
| Audio | 24,58 | 38,74 | 37,83 |

FMax sólo cubre rutas dentro del mismo reloj. CPU y HDMI todavía no alcanzan
su frecuencia requerida; resolver los CDC pendientes no garantiza por sí solo
el cierre de esas rutas internas.

## Ocupación y duración

| Recurso | Anterior | Nuevo | Diferencia |
|---|---:|---:|---:|
| ALM necesarios / 41.910 | 27.150 | 27.601 | +451 |
| Registros | 33.469 | 33.736 | +267 |
| LAB ocupados / 4.191 | 3.910 | **3.934** | +24 |
| Bloques RAM / 553 | 409 | 409 | 0 |
| Bits de RAM / 5.662.720 | 3.240.923 | 3.240.923 | 0 |
| DSP / 112 | 39 | 39 | 0 |
| PLL / 6 | 3 | 3 | 0 |

Quedan **257 LAB libres (6,13 %)**: ocupación del 93,87 %. La holgura de
colocación sigue siendo reducida y esta revisión consume 24 LAB adicionales.

El incremento global de ALM no equivale al coste RTL directo del nuevo CDC.
La tabla jerárquica atribuye a shadowmask 132,4→135,2 ALM necesarios y
255→306 registros, conservando una sola RAM de 2.816 bits. El contador aparece
ahora en su propio módulo (4,9 ALM, 12 registros); antes formaba parte de
`sys_top`. La mayor variación de ALM se encuentra en `emu` (+410), cuyos fuentes
no han cambiado entre estos fits. Esto apunta a diferencias de optimización y
colocación; la métrica física relevante sigue siendo el aumento global medido.

Duración del flujo del usuario: síntesis **5:42**, Fitter **15:10**, ensamblado
**0:27**, TimeQuest **1:41**; total **23:00**.

## Violaciones pendientes y siguiente trabajo

Las prioridades fuera de SPK286 son:

| Ruta observada | Setup |
|---|---:|
| Perfil EGA `applied[1] → ega_monitor_profile_video_sync1_q[1]` | −6,106 ns |
| OSD `status[9] → at_video_ary_q[0]` | −5,866 ns |
| `vrr_mode → ascal|o_vrr` | −5,668 ns |
| `LFB_EN → ascal|i_mode[2]` | −5,632 ns |
| `scaler_out → ascal` (procesado de píxeles) | −5,631 ns |

El perfil EGA ya tiene dos etapas, pero es un bus de dos bits actualizado
durante reset: hay que comprobar la ventana de estabilidad y su relación con
la liberación del reset de vídeo antes de justificar una excepción de primera
etapa o modificar la captura. Los campos OSD de aspecto se decodifican hoy
directamente en el reloj de vídeo; conviene trasladar su configuración de forma
coherente. Después, revisar VRR, modo del scaler y LFB por dominio y frontera
de aplicación. No basta con excluir todos estos cruces en SDC.

La revisión no cambia SPK286. Su peor ruta interna observada es
`prefetch_queue|storage_q → microsequencer|micro_pc`, con −3,569 ns. La ruta
BIU→dirección SDRAM tiene −0,550 ns; ambas quedan en su revisión específica.

## Cobertura y artefactos

`check_timing` mantiene 3.713 elementos sin reloj, cero bucles y cero latches.
`report_ucp` mantiene 10 puertos de entrada y 52 de salida sin restricciones,
y cero relojes sin restricciones. Los avisos `partial_min_max_delay` pasan de
16 a 17 por el nuevo payload con presupuesto máximo y hold excluido. Estos
resultados no permiten declarar cobertura completa del diseño.

La copia del fit y las auditorías se guardan en
`build/at-frame-shadowmask/20260924-fit/`: `focused/` contiene las rutas CDC,
`timing/` el desglose general, `work/output_files/` los informes originales y
`manifest.json` los hashes de los resultados. `timing_open=1` señala las
violaciones globales pendientes.

Ambas ejecuciones de TimeQuest finalizaron con **0 errores y 54 avisos**; se
comprobó que todas las familias CDC auditadas tienen rutas activas y márgenes
positivos en las cuatro esquinas.

RBF generado por la compilación del usuario el **24/09/2026 a las 20:44:21**:

- `output_files/PCAT-286_20260924_204421.rbf`
- `output_files/PCAT-286.rbf` contiene el mismo binario.
- Tamaño: **4.028.528 bytes**.
- SHA-256: `2AE9669C76AC79703FD104CB91337DD9FE79D4E2ABC3C60EF72EA101C074CF6E`.

Está disponible para la prueba funcional en placa; las simulaciones previas
verificaron píxeles, latencia de vídeo, cargas de LUT y contador, pero la
prueba en hardware de esta revisión corresponde al usuario.
