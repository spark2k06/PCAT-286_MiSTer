# Subportadora y vídeo directo — revisión del 25/09/2026

## Estado

Preparado sobre `a8bc4f1`, rama `beta-04`. El usuario compiló `PCAT-286.qsf`
y confirmó la recuperación de la imagen con el fit terminado a las 10:30
del 25/09/2026. La TV recuperó imagen al seleccionar 480i 15 kHz y el bloqueo
HDMI de arranque se corrigió en el transmisor. **La recuperación funcional
está confirmada; el timing global aún no está cerrado.**
Véanse [el diagnóstico del fit de las 09:00](AT_NATIVE_OUTPUT_FIT_20260925_0900.md)
y [los resultados del fit de las 10:30](AT_NATIVE_OUTPUT_FIT_20260925_1030.md).
Las pruebas funcionales y Analysis & Elaboration previas habían pasado;
no cubren el enlace físico. La CPU no se modifica. La revisión posterior usa
TimeQuest y consulta/exportación de la netlist sobre copias del fit del usuario,
sin volver a sintetizar.

La investigación posterior reprodujo un bloqueo de arranque en la netlist
del transmisor. Se corrigió la codificación/orden del estado inicial en
`at_hdmi_output.sv`. La netlist del fit de las 10:30 libera reset en el ciclo
SYS 32; el comprobador sigue reproduciendo el bloqueo del fit de las 09:00.
Los slacks de cada informe pertenecen exclusivamente al fit allí identificado.

Referencia física: fit terminado a las 07:47, conservado en
`build/at-hdmi-controls/20260925-0747-fit/` y descrito en
[AT_HDMI_CONTROLS_FIT_20260925_0747.md](AT_HDMI_CONTROLS_FIT_20260925_0747.md).

| Ruta anterior | Setup de referencia |
|---|---:|
| `subcarrier → subcarrier_out` | −5,596 ns |
| `dv_data[20] → hdmi_dv_data[20]` | −4,775 ns |

Esos valores describen el RTL anterior. No se extrapolan slacks del candidato
a partir de simulación o de una netlist antigua con restricciones nuevas.

## Clasificación de los cruces

### Subportadora: configuración estable entre transacciones

HPS escribe la habilitación y `PhaseInc` en CLK2, mientras el acumulador y la
salida funcionan con vídeo +90°. El incremento tiene 40 bits y llega en tres
palabras UIO. Su captura requiere conservar el valor completo, incluso con
pausas entre palabras. También forman parte del comando los indicadores
PAL/CVBS/YC y el rango de burst.

Se revisó el protocolo `UIO_SET_YC_PAR` en
`D:/GitHub/Main_MiSTer/video.cpp`: envía los campos bajo la misma transacción
y termina con `DisableIO()`. Existe también un comando corto que sólo
deshabilita YC y conserva los campos no escritos.

`at_video_output_config` transfiere un paquete de 62 bits mediante el
`at_cdc_snapshot` ya utilizado en el proyecto:

- Incremento de fase, rango de burst y PAL/CVBS/YC.
- Habilitación efectiva de subportadora, calculada en el dominio HPS con las
  condiciones originales de CSync, YPbPr, scandoubler y salida escalada.
- CSync para la preparación del flujo de vídeo directo.

La publicación espera a que UIO esté inactivo durante dos muestras. El
payload permanece congelado hasta el acuse. La configuración local se aplica
en el flanco de bajada de VS, con una primera captura de arranque. El
acumulador mantiene su fase al actualizar el incremento; no se reinicia en
cada comando. Tanto YC como la subportadora usan los parámetros locales.

Los registros de parámetros y el acumulador reciben inicialización explícita
a cero. Una pausa de cualquiera de los relojes conserva el intercambio
pendiente. No se añaden resets independientes al protocolo.

En este perfil `VGA_SCALER` del core vale cero; las condiciones de salida
escalada del paquete proceden de la configuración HPS.

### Vídeo directo: flujo continuo con su reloj nativo

El perfil AT forzaba `hdmi_tx_clk = hdmi_clk_out`, incluso seleccionando datos
directos producidos por `clk_vid`. Esto era un cruce real, no una ventana de
datos estables. Un sincronizador por bit rompería la coherencia; un buzón de
último valor perdería muestras y no conservaría el raster.

La referencia disponible en
`D:/GitHub/PCXT-EGA_MiSTer_devel2/sys/sys_top.v` utiliza un multiplexor de reloj
para seleccionar vídeo nativo en modo directo y PLL HDMI en modo escalado.
Se recupera esa relación entre reloj y datos, con registros separados antes
de la salida:

| Trayecto | Registros antes del registro final | Reloj de salida |
|---|---|---|
| Vídeo directo | `direct_q1`, `direct_q2`, ambos en vídeo nativo | Vídeo +90° |
| Scaler/framebuffer | `scaled_q`, en HDMI | PLL HDMI |

El registro final `tx_pixel` conserva juntos RGB, HS, VS y DE, y sigue siendo
elegible para los registros de salida de los pines HDMI. Se conserva la
latencia: tres flancos desde `dv_*` en directo y dos desde la salida OSD
escalada. Avalon, el framebuffer y el scaler no se modifican.

La selección es `direct_video && !vga_fb`; el framebuffer tiene prioridad.
CSync de la salida escalada conserva la condición `direct_video && csync`,
con registro en SYS y sincronizador de dos etapas en HDMI.

`at_hdmi_output` espera al cierre de UIO para aceptar un cambio de modo.
Primero afirma reset de transmisión, espera 160 ns, cambia **el mismo selector
para reloj y datos**, espera 640 ns y libera reset mediante dos etapas en el
reloj seleccionado. La aserción funciona aunque el reloj anterior esté parado.
Las tuberías de entrada continúan ejecutándose en sus respectivos dominios.

Se conserva el `cyclonev_clkselect` utilizado por MiSTer. Cambiar entre modos
puede producir una interrupción de imagen y requiere que el receptor vuelva
a sincronizarse: no se promete una conmutación externa sin pulsos truncados.
Los registros de transmisión permanecen en reset durante la conmutación.

## Restricciones: sólo transferencias funcionalmente posibles

El SDC crea dos relojes derivados en la salida de `hdmi_clk_sw`:

- `AT_HDMI_TX_SCALED`, derivado del PLL HDMI.
- `AT_HDMI_TX_DIRECT`, derivado de vídeo +90°.

Son alternativas de un mismo multiplexor. Se declaran mutuamente excluyentes
sólo esas dos copias; los dominios originales de vídeo, HDMI, CPU y Avalon
siguen analizados entre sí. Es el uso de exclusividad lógica descrito en
la [referencia de TimeQuest](https://resources.altera.com/quartushelp/17.0/tafs/tafs/tcl_pkg_sdc_ver_1.5_cmd_set_clock_groups.htm).

Hay dos excepciones de datos limitadas a los registros de entrada del mux:

- `direct_q2 → AT_HDMI_TX_SCALED`: rama no seleccionada con ese reloj.
- `scaled_q → AT_HDMI_TX_DIRECT`: rama no seleccionada con ese reloj.

Las rutas `direct_q2 → tx_pixel` con reloj directo y `scaled_q → tx_pixel`
con reloj escalado permanecen activas, con setup y hold normales. La auditoría
exige caminos en ambas. No se corta globalmente el dominio de vídeo.

`select_direct → tx_pixel` conserva un presupuesto max-delay de 10 ns; el
hold no depende de la fase entre SYS y TX, porque el selector cambia bajo
reset y permanece estable al menos 640 ns antes de liberarlo. Su control
síncrono en SYS sigue analizado.

Para subportadora/YC se usa max-delay de 10 ns sobre el payload y excepción
de hold por el protocolo de datos estables. Se eliminan en AT las excepciones
heredadas desde `PhaseInc`, `ColorBurst_Range`, `pal_en`, `cvbs` e `yc_en`.
Las etapas posteriores y los consumidores permanecen analizados.

Las primeras etapas de recepción de VSYNC y métricas aceptan ahora ambos
relojes de transmisión. El sincronizador CSync sólo excluye su primera etapa.
En reset sólo se excluyen las entradas asíncronas de las dos etapas de
liberación; **reset_sync → registros de salida conserva recovery/removal**.

Las colecciones de reloj, pines y registros son obligatorias: un nombre que
no coincida con la netlist del nuevo fit debe producir error, no una auditoría
vacía considerada exitosa. La elaboración no valida los nombres físicos del
SDC; esa comprobación corresponde al próximo fit y TimeQuest.

## Validación realizada

`scripts/test_at_native_output.sh`, con relojes de vídeo de aproximadamente
57,27 MHz y HDMI de tres frecuencias/fases distintas:

| Reloj HDMI simulado | Píxeles directos comprobados | Píxeles escalados comprobados | Transacciones analógicas |
|---|---:|---:|---:|
| 148,54 MHz | 320 | 1.037 | 3 |
| 74,25 MHz | 320 | 517 | 3 |
| 25 MHz | 320 | 173 | 3 |

Todos los casos terminan en PASS. Se comprueban muestras RGB/HS/VS/DE juntas,
latencia, prioridad del framebuffer, CSync escalado, UIO parcial, cambios de
modo y salida de un reloj parado hacia el otro. Para configuración analógica
se incluyen escrituras parciales de 40 bits, pausas largas, VS durante el
comando, actualización en VS y comandos cortos que conservan otros campos.
La simulación usa un modelo lógico del selector de reloj, sin modelar los
retardos físicos del multiplexor ni la adquisición de enlace del receptor.

Quartus 17.0.2 Analysis & Elaboration: **0 errores, 131 avisos**, finalizado
el 25/09/2026 a las **08:24:31 locales**, duración 1:37. Sin nuevos avisos en
los módulos añadidos o en `sys_top.v`. Se ejecutó en una copia aislada,
sin síntesis, Fitter ni ensamblado. El cambio posterior del comentario de
`at_hdmi_vsync.sv` no cambia RTL; el ajuste posterior del SDC conserva
recovery/removal de la liberación local de reset y no interviene en elaboración.

Logs: `build/at-native-output/sim/` y `build/at-native-output/frontend/`.
El primer intento de lanzar el contenedor rechazó una ruta relativa de
volumen; el intento final usa la ruta absoluta y es el elaborado correctamente.

## Seguimiento tras las compilaciones del usuario

1. Verificados: colecciones activas y slacks positivos para paquete analógico, aplicación,
   acumulador y salida de subportadora en las cuatro condiciones.
2. Verificados: rutas activas directas y escaladas, registros finales, resets,
   CSync y los dos relojes derivados.
3. Auditados: familias CDC anteriores, FMax, hold, recovery/removal y LAB.
   Sigue negativo el setup de luminancia del scaler, además de CPU/CLK2.
4. El usuario confirma recuperación de HDMI escalado y TV analógica en 480i.
   No hay confirmación física específica de `direct_video=1`, subportadora/YC,
   framebuffer Linux, EDIT o audio después de esta corrección. Los modos
   de vídeo directo requieren un receptor compatible.

No se declara cierre global de timing. El RBF vigente probado por el usuario
es `PCAT-286_20260925_102906.rbf`; los resultados están en el informe de las 10:30.
