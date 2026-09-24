# CDC de VSYNC y shadowmask — candidato posterior a 061030c

## Estado

Actualización: el fit posterior ya está revisado en
`AT_FRAME_SHADOWMASK_FIT_20260924.md`. Las rutas de esta tanda cumplen en las
cuatro esquinas; persisten violaciones globales. El resto de este documento
describe el candidato y su verificación previa a ese fit.

Rama `beta-04`. El commit `061030c` guarda la corrección anterior de vídeo y
Avalon, verificada con el fit del 24/09/2026. Esta siguiente revisión está
preparada para que el usuario compile `PCAT-286.qsf`; todavía no tiene fit ni
RBF propio. No permite afirmar cierre de timing del proyecto.

El resultado anterior queda documentado en `AT_VIDEO_AVALON_CDC_FIT_20260924.md`.
Las rutas de partida para esta revisión son:

| Ruta anterior | Peor setup |
|---|---:|
| `sync_v|pol → vs_r` | −6,356 ns |
| `emu|at_video_vs_out_q → vs_r` | −6,208 ns |
| `HDMI_shadowmask|hmax[3] → hmax2[3]` | −6,168 ns |
| `HDMI_shadowmask|mask_rotate → mask_lut` (dirección de lectura) | −6,023 ns |

## Contador de cuadros

`vs_fix` pertenece al reloj de vídeo y se forma mediante un XOR de señales
registradas. Se registra su salida en ese dominio para evitar glitches en el
cruce. `at_frame_counter` la lleva a `clk_sys` con dos etapas, y detecta flancos
únicamente después de la segunda. El contador conserva sus ocho bits y su
incremento en el flanco ascendente de VS normalizado.

Es un cruce de nivel: los pulsos VS reales duran muchos ciclos de `clk_sys`.
Requiere niveles alto y bajo de al menos dos ciclos receptores para reconocer
todos los flancos. Si el receptor se detiene durante cuadros completos, no
almacena esos eventos; al arrancar reconoce el nivel que siga presente.

SDC excluye únicamente la llegada asíncrona al primer registro (`vs_meta`).
La formación del registro fuente, la primera→segunda etapa y la lógica del
contador conservan análisis normal de setup y hold.

## Configuración de shadowmask

Los campos escritos por HPS pertenecen a `clk_sys`, mientras que el procesado
de píxeles pertenece a `clk_hdmi`. Sincronizar sus bits individualmente podría
mezclar dimensiones y modo de dos configuraciones distintas.

Se ha comprobado el protocolo real en `D:/GitHub/Main_MiSTer/video.cpp`, función
`setShadowMask`: flags, palabras de LUT, dimensiones y fin de transacción UIO
`0x3E`. `sys_top` registra una señal de transacción alineada con `cmd_wr`.
Al terminar la transacción se retienen los 11 bits de flags y dimensiones.
`at_cdc_snapshot` los transfiere mediante petición/acuse, manteniendo el bus
estable hasta que vuelve el acuse. La habilitación por LFB también entra por
ese mecanismo. HDMI aplica la configuración completa en el flanco descendente
de VS; una llegada próxima a ese flanco puede esperar al siguiente cuadro.

Las escrituras de LUT siguen realizándose en `clk_sys`, admitiendo palabras
consecutivas y cargas con HDMI detenido. La LUT de 256×11 bits conserva su
lectura desde HDMI; no se envían sus escrituras por el snapshot de último
valor. Tampoco se duplica la LUT: una escritura durante la visualización puede
afectar al cuadro en curso, igual que antes. La aplicación en frontera de
cuadro corresponde a flags/dimensiones/habilitación, no a un intercambio de
dos bancos de LUT.

La aritmética de píxeles y su latencia permanecen iguales. El camino original
se conserva bajo `AT_CDC=0`; PCAT activa el nuevo mediante `SPK286_AT_CDC`.
El coste físico adicional se medirá con el siguiente fit.

SDC limita a 5 ns el payload retenido hacia su captura, excluyendo su hold
entre relojes sin relación de fase. Las únicas otras exclusiones nuevas son
las llegadas a las primeras etapas de petición y acuse. Sus segundas etapas,
la aplicación de configuración y el procesado HDMI conservan setup/hold.

## Verificación previa al fit

`bash scripts/test_at_frame_shadowmask.sh`:

- Contador: 272 flancos, desbordamiento de ocho bits y pausas de ambos relojes.
- Shadowmask: 18.432 píxeles activos comparados con el camino original, con
  detección de valores desconocidos; cuatro combinaciones de rotación/escala.
- 2.048 palabras de LUT comprobadas, escrituras consecutivas, tres cargas
  completas con HDMI detenido, transacción parcial mantenida varios cuadros
  y cambios de habilitación LFB.
- Aserciones de aplicación de configuración en VS y de igualdad de latencia
  de las señales de vídeo.

Quartus 17.0.2 completó **Analysis & Elaboration** de `PCAT-286` el 24/09/2026 a
las 20:11:45 locales: **0 errores, 130 avisos**. Registro en
`build/at-cdc/quartus-final-elaboration.log`. Esa comprobación no ejecutó
síntesis, Fitter ni generación de RBF.

## Siguiente fit

Compilar `PCAT-286.qsf` con estos fuentes. El manifiesto previo está en
`build/at-frame-shadowmask/candidate-source-manifest.json`. Después, ejecutar
el informe sobre la netlist nueva, con un directorio de salida que no exista:

```text
quartus_sta -t scripts/report_at_video_avalon_timing.tcl PCAT-286 build/at-frame-shadowmask/postfit
```

El informe exige registros presentes y rutas activas para el contador, el
payload de shadowmask, sus sincronizadores y sus controles locales. Comprueba
las cuatro esquinas disponibles y conserva la auditoría de Avalon y vídeo de
la revisión anterior. Hay que revisar setup, hold, max-delay, cobertura y
retardos de payload antes de aceptar la corrección física. Las restantes
violaciones del proyecto siguen pendientes, incluidas las de SPK286 reservadas
para su revisión específica.
