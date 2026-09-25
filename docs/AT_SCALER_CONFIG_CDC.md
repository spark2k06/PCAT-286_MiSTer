# Configuración de geometría y scaler — candidato del 25/09/2026

Estado actual: el ajuste posterior al primer fit está revisado en
`AT_SCALER_CONFIG_FIT_20260925_0644.md`. Las rutas de shadowmask y aspecto
corregidas cumplen setup y hold en las cuatro condiciones, y los DSP vuelven
a 39. Las 103 combinaciones de familia/tipo de los bloques intervenidos tienen
margen positivo; persisten otras violaciones globales. Este fit corresponde a
`build/at-scaler-config/revised-candidate-source-manifest.json` y al RBF
`output_files/PCAT-286_20260925_064223.rbf`. El texto siguiente conserva el
diseño y la validación del primer candidato; su primer fit está documentado
en `AT_SCALER_CONFIG_FIT_20260925.md`.

## Referencia y alcance

Rama `beta-04`. El último fit revisado es el del 24/09/2026, terminado a las
22:41, documentado en `AT_SCANLINES_STATUS_FIT_20260924.md` y conservado en
`build/at-scanlines-status/20260924-fit/`. Este candidato todavía necesita un
nuevo fit: no se atribuyen slacks ni ocupación física al RTL sin compilar.

Rutas de partida:

| Ruta | Setup anterior |
|---|---:|
| `HDMI_PR → videow[9]` | −5,877 ns |
| `lowlat → ascal\|i_mode[3]` | −5,790 ns |
| `LFB_EN → hmini[*]` | −5,749 ns |
| `lowlat → ascal\|o_mode[3]` | −5,732 ns |
| `scaler_out → ascal\|o_vpix_outer/inner[*]` | −5,666 ns |

Los registros HPS viven a 50 MHz; el cálculo de geometría y la entrada del
scaler, en vídeo +90°; la salida, en HDMI. Son cruces CDC reales. Que un ajuste
cambie pocas veces no garantiza que su transición respete el reloj de destino.
Además, UIO escribe tiempos, límites y direcciones por palabras: una captura
durante la transacción puede combinar campos de dos configuraciones.

No se modifica SPK286. Los protocolos Avalon de comandos, los bancos de imagen,
los datos RGB y los filtros conservan sus algoritmos; cambian la entrega de
configuración y el momento de aplicación del descriptor del framebuffer.

## Protocolo implementado

`sys/at_scaler_config.sv` sustituye el cálculo AT antes incluido en `sys_top`.
La rama sin `SPK286_AT_CDC` conserva el cálculo original.

1. **UIO completa → vídeo.** `geometry_config` transporta un paquete de 309 bits:
   tiempos y polaridades, repetición de píxeles, escalado, aspectos personalizados,
   modo, VRR, habilitación, límites LFB y descriptor del framebuffer. El origen
   sólo publica cuando UIO está inactivo y ha transcurrido un ciclo adicional
   para que `FB_*` registre el descriptor completo. Sus datos quedan retenidos
   hasta el acuse.
2. **Cálculo estable.** La máquina toma la configuración pendiente y ARX/ARY al
   iniciar un cálculo, y los mantiene hasta terminar. Reutiliza `sys_umuldiv`,
   con el mismo ancho, truncamiento, límites y centrado del cálculo anterior.
   ARX/ARY proceden del reloj de vídeo relacionado; ese camino mantiene análisis
   normal de setup y hold. Se recalcula cuando cambia alguna entrada.
3. **Vídeo → HDMI.** `scaler_frame_config` transporta 244 bits con tiempos ya
   calculados, ventana, modo, VRR, polaridades, descriptor y una marca de cambio
   del raster. Su receptor captura y acusa **al aplicar**, en el flanco de bajada
   de VSYNC. El origen conserva el paquete hasta entonces. No existe una captura
   intermedia que pueda descartar dos cambios y perder su marca de cambio.
4. **Arranque.** Con el raster deshabilitado se acepta el primer paquete sin
   esperar VSYNC; así se evita depender de un VSYNC que aún no puede generarse.
5. **Modo de entrada.** La copia para `ascal.i_mode` se aplica en el VSYNC de
   entrada. La copia de salida se entrega junto con el paquete HDMI.
6. **Retorno HPS.** El aspecto calculado vuelve mediante `aspect_readback`, un
   snapshot de 25 bits. Las respuestas `0x40` y su CRC ya no leen el bus de
   aspecto directamente desde el reloj de vídeo.

Los mailboxes comparten la inicialización de la FPGA y no tienen resets locales
independientes. Si un reloj se para, el paquete en vuelo permanece retenido;
tras reanudarse se procesan los paquetes pendientes y la última configuración.
Con cambios rápidos puede haber más de un cuadro de latencia. Es configuración,
no una cola destinada a conservar todos los comandos UIO intermedios.

## Framebuffer y cambios de raster

`ascal` añade `AT_LOCAL_CONFIG`, activado sólo por el wrapper AT. En ese modo,
sus parámetros de salida y framebuffer ya pertenecen a `o_clk`. Se elimina la
transferencia independiente `framebuffer_out_config` del diseño AT: base,
formato, stride y dimensiones viajan junto a la ventana LFB y el modo.
El pulso local `at_config_update` actualiza la base de cuadro; los comandos
Avalon que ya están en vuelo mantienen sus direcciones y datos retenidos.

Cambiar a un raster más alto al terminar el VSYNC antiguo puede convertir la
posición actual en una línea activa de la nueva resolución. `at_config_retime`
reinicia el barrido en la última línea de blanking del nuevo raster y vacía las
señales de display del pipeline. Sólo se genera ante un cambio de tiempos o al
habilitar la salida. Los cambios de aspecto, formato o base de framebuffer no
recortan el back porch ni alteran la cadencia periódica.

La detección de tiempos reutiliza la configuración anterior del calculador;
no guarda otra copia de 96 bits. En HDMI sólo se compara una marca de un bit,
cuyos cambios no pueden perderse porque el acuse espera a la aplicación.

La habilitación del shadowmask y la anulación de imagen usan la copia HDMI de
`LFB_EN`. Las polaridades de la salida VGA escalada usan también la configuración
aplicada. El control de PLL mantiene sus sincronizadores existentes.

## Restricciones y auditoría del próximo fit

`SYSTEM.sdc` establece únicamente estas excepciones de protocolo:

| Instancia | Presupuesto payload → captura |
|---|---:|
| `u_at_scaler_config\|geometry_config` | 10 ns |
| `u_at_scaler_config\|scaler_frame_config` | 5 ns |
| `u_at_scaler_config\|aspect_readback` | 10 ns |

Se excluye la llegada de cada toggle a su primera etapa y el hold del payload
retenido. La petición atraviesa dos etapas antes de poder capturarse; el acuse
sólo permite reutilizar el payload después de la captura. El receptor HDMI
puede esperar hasta VSYNC, alargando esa ventana. No se añaden excepciones
generales entre relojes ni a la lógica que consume los parámetros.

El script `report_at_video_avalon_timing.tcl` incluye los tres mailboxes,
sus etapas de sincronización, la captura del calculador, sus consumidores,
los consumidores HDMI, los pulsos de actualización, el modo de entrada y el
retorno HPS. Exige rutas activas. Se mantienen las familias de las correcciones
anteriores y se retira el grupo del mailbox independiente de framebuffer,
que ya no existe en esta topología.

## Validación y entrega

`scripts/test_at_scaler_config.sh` verifica el módulo de producción:

- 14 comprobaciones de configuraciones completas, con relojes distintos.
- Arranque y rehabilitación sin VSYNC previo; aplicación en frontera de cuadro.
- Transacciones UIO parciales que permanecen abiertas durante varios cuadros.
- Aspecto 4:3, 16:9, aspectos personalizados, dimensiones explícitas y límites.
- Repetición de píxeles, modo, VRR y descriptor completo de framebuffer.
- Cambios durante el cálculo y retorno coherente del aspecto a HPS.
- Parada de cada reloj y recuperación de la última configuración.
- Dos cambios de raster pendientes, sin perder ninguna marca de aplicación.
- Los cambios sólo de aspecto conservan la cadencia del raster.

`scripts/test_at_scaler_avalon.sh` utiliza el scaler VHDL real y un esclavo
Avalon con esperas y respuestas diferidas. Ejecuta las variantes progresiva y
entrelazada, tanto con el mailbox anterior como con configuración local. En la
variante nueva cambia a un raster más alto durante la simulación y comprueba
el blanking. El scoreboard comprueba comandos, direcciones, datos retenidos,
bancos 0/1/2, ambas bases de framebuffer y actividad de píxeles.

Los resultados del candidato están en `build/at-scaler-config/`: simulación
del controlador, `avalon-final/` y `frontend-final/`. El manifiesto
`candidate-source-manifest.json` identifica los archivos que debe usar el
próximo fit. La revisión de Quartus es sólo Analysis & Elaboration; no ejecuta
síntesis, Fitter ni genera un RBF nuevo.

Resultado del candidato final:

- Controlador SV: **PASS**, 14 comprobaciones; incluye dos marcas de cambio
  pendientes y las dos paradas de reloj.
- Scaler con configuración anterior: **PASS** progresivo/entrelazado, con
  185/202 lecturas y 240 ráfagas de escritura en cada variante.
- Scaler con configuración local y cambio de raster: **PASS**
  progresivo/entrelazado, con **188/205 lecturas**, **273 ráfagas de escritura**
  en cada variante y **27.648/25.344 píxeles** correctos.
- Los cuatro scoreboards pasan: sin cambios del payload bajo espera Avalon,
  bancos 0/1/2 y bases `0x24000000`/`0x24800000`. Margen mínimo de retención
  hasta captura observado: 30,070 ns; entre escrituras, 1.676,160 ns.
- Quartus 17.0.2 Analysis & Elaboration: **0 errores, 131 avisos**;
  terminó el **25/09/2026 a las 05:30:32 locales**, en 1:34. El aviso añadido
  respecto al candidato anterior corresponde al alias `applied_epoch`, que
  sólo descarta el bit superior al desempaquetar las salidas; la marca sí se
  consume a través del campo del paquete. No es una entrada sin conectar.
- `git diff --check`: correcto. El RBF del último fit permanece intacto.

**Pendiente:** compilar `PCAT-286.qsf`, medir setup/hold y recursos de la nueva
netlist en las cuatro condiciones, y probar el RBF en hardware. Las nuevas
etapas añaden registros; el efecto neto sobre ALM/LAB no se conoce antes del
fit. El RBF de las 22:39:10 del día 24 corresponde a la revisión anterior.
