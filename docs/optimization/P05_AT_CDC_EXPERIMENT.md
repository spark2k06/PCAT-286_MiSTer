# P05: experimento CDC de control y metadatos AT

Fecha: 2026-09-14. Rama de trabajo: `codex/spk286-p05-cdc`.
Base preservada: `codex/spk286-p05-nodebug-seed2`, commit `9af1a39`.
Este candidato conserva P05, AT sin debug y seed 2. **No esta sintetizado ni
probado en placa.** Tampoco se ha probado en placa la referencia seed 2.

## Alcance implementado

| Cruce de la referencia | Cambio |
| --- | --- |
| `video_calc`: video/100 MHz -> HPS 50 MHz | Dos snapshots coherentes con confirmacion. Una consulta HPS conserva sus palabras, incluidas las mitades de contadores, hasta el siguiente comando. |
| Configuracion OSD: 50 MHz -> VGA/HDMI | Bundle de 132 bits; se publica despues de terminar el comando y estabilizar sus dimensiones derivadas. RAM de bitmap y pipeline de pixeles sin cambios. |
| `cfg_done` -> ajuste PLL HDMI | `lltune` conserva sus relojes sin enmascararlos con `cfg_done`. La habilitacion se sincroniza localmente; las medidas se reinician mientras no es valida. |
| Ventanas de imagen y `lowlat` -> gestion PLL | Primera etapa aislada de los consumidores; historial separado para detectar flancos. Reset con liberacion sincronizada. Retardo de cuatro lineas conservado. |
| Dimensiones efectivas scaler: entrada -> salida | Ancho, alto y flags de downscale viajan juntos, con payload congelado hasta confirmar recepcion. Se mantiene el punto original de aplicacion en VS. |
| Dimensiones scaler: salida -> entrada | Ancho y alto de destino viajan juntos por un segundo mailbox. |

Los helpers SV y VHDL usan el mismo protocolo: registrar payload y toggle,
sincronizar el toggle mediante dos etapas, capturar en el tercer flanco de
destino y devolver confirmacion sincronizada. No son FIFOs: pueden omitir
estados intermedios de metadatos, pero entregan el ultimo cuando los relojes
siguen funcionando. No deben usarse para comandos, bytes ni completados DDR.
La inicializacion de FPGA establece ambos extremos. Los resets de CPU/OSD no
reinician unilateralmente el handshake. Una pausa de reloj retiene la transaccion.

No hay cambios en instrucciones, frecuencia, ciclos CPU, bus AT, latencia de
memoria del procesador, EGA de 8 bits ni ROMs. Los modulos comunes tienen opcion
desactivada por defecto; **solo `PCAT-286_AT.qsf` activa `SPK286_AT_CDC`**.
XT y AT_FAST no activan este experimento.

## Restricciones: mejora real frente a excepciones

- Excepciones nuevas limitadas a la llegada al primer registro sincronizador
  y al enlace entre registros de payload retenido y captura.
- Maximo de 5 ns para esos payloads, menor que un periodo HDMI nominal de
  6.73 ns; excepcion hold solo entre esos endpoints. Las etapas sincronizadoras
  y el resto de la logica siguen sujetos a timing normal.
- Las colecciones de registros son obligatorias: un fit que no encuentre
  los endpoints debe fallar la comprobacion SDC, no aceptar una excepcion vacia.
- Se reagrupan los dominios participantes (50 MHz de control/CPU, HPS 100 MHz
  y PLL HDMI) para retirar las exclusiones entre ellos que anulaban los
  max-delay de los mailboxes. Se conservan las exclusiones heredadas ajenas
  a este experimento (audio, SPI, etc.); no se anaden exclusiones con los
  relojes del PLL de video AT. Se retiran tambien las excepciones amplias del
  OSD y de las dimensiones del
  scaler, incluido el multicycle OSD que no es valido cuando `ce_pix=1`.
- No se toca la fase del PLL, ni los presupuestos externos de SDRAM.

**El nuevo WNS/TNS puede empeorar al descubrir caminos antes excluidos.**
Debe compararse la referencia con las mismas reglas de analisis, ademas del
informe original. El numero de advertencias o el Fmax minimo de cualquier
dominio por si solos no miden el exito. Revisar setup, hold, recovery/removal,
las excepciones efectivas y las colecciones de los nuevos mailboxes en el fit.
Ni la sintaxis SDC ni la simulacion prueban metastabilidad o cierre fisico.

## Limites importantes y trabajo posterior

Este cambio repara los enlaces de metadatos indicados, **no certifica todo el
scaler como CDC-safe ni garantiza coherencia de una transicion de modo completa**.
Se conservan su politica de bancos y el instante original de aplicacion de
geometria. Un paquete coherente de dimensiones no equivale a un descriptor
de frame/banco con propiedad confirmada. La latencia anadida puede hacer que
una nueva geometria se aplique en el siguiente frame.

Quedan para un experimento separado con tests de memoria y frames completos:

1. Propiedad explicita de bancos y mitades del buffer del scaler, completados
   Avalon, backpressure y drenaje de respuestas durante reset. No basta con
   sincronizar bits de direcciones ni con retrasar un toggle.
2. Configuracion de salida/crop, framebuffer base/stride/formato y generacion
   de configuracion. Persisten, entre otros, `hmin -> o_hmin` y controles de
   coeficientes/paleta. Los comandos multiword necesitan un commit propio.
3. Comandos PLL `cfg_custom_p1/p2/t` y `cfg_got/cfg_ready`: requieren entrega
   ordenada con confirmacion, no el helper de ultimo valor.
4. Direct-video: AT fija el reloj HDMI al PLL pero hereda una seleccion de
   pixeles directos de otro reloj. **Probar este candidato con HDMI escalado,
   `direct_video=0`**; el cambio no declara soportado ese modo alternativo.
5. Rutas internas CPU (referencia: -4.270 ns) y logica local scaler/OSD que
   ahora se deja visible. La mejora CDC no cierra esas rutas automaticamente.

## Verificacion y reproduccion

Desde WSL, raiz del proyecto:

```sh
bash scripts/test_at_cdc.sh
bash scripts/test_at_profile_elab.sh
bash scripts/check_at_cdc_quartus.sh
bash scripts/build_at_no_debug.sh --prepare-only
```

La suite dirigida prueba los helpers con relojes distintos, cambios de relacion
de velocidades y pausas; comandos reales OSD, cuatro rotaciones, bitmap y
disable; consultas de varias palabras HPS; codigo VHDL en estandares 93 y 2008;
reloj sin gating, dos etapas antes de consumir ventanas y retardo de cuatro
lineas en el VHDL real del ajuste PLL. Usa Icarus y la imagen local
`ghdl/ghdl:ubuntu22-llvm-11`. Resultados locales: `build/at-cdc/`.

Resultados dirigidos: 172 transferencias SV, 1881 VHDL; OSD completo de control;
dos consultas HPS coherentes; 5630 comprobaciones del sampler PLL, 13 eventos
de entrada y 24 cambios con retardo de cuatro lineas. El test de defaults
legacy se elabora sin incluir el helper: comprueba las rutas directas, sin
introducir latencia ni congelacion de consultas cuando la opcion esta apagada.

`check_at_cdc_quartus.sh` copia las entradas a un contenedor desechable y solo
ejecuta comprobacion de proyecto y Analysis & Elaboration. No ejecuta sintesis
de mapeo, fitter ni assembler. Registra los hashes de las fuentes principales
y exige que no exista RBF. Esto no valida las colecciones del futuro netlist
fisico: esa comprobacion es obligatoria durante la sintesis del usuario.

Comprobacion final Quartus 17.0.2: proyecto correcto (0 errores, 0 avisos);
Analysis & Elaboration correcto (0 errores, 98 avisos, 1 min 30 s).
Los hashes comprobados estan en `build/at-cdc/frontend-inputs.sha256`.
El test de perfil mantiene `AT_CONFIG_NO_DEBUG_PASS bytes=401`.

Se ha reanalizado tambien **el fit antiguo**, sin sintetizar RTL nuevo, con
las reglas del experimento. Resultado: 0 errores de ejecucion STA, 6 avisos
heredados; no implica timing aprobado.
Las colecciones de los helpers nuevos se omiten SOLO en esta reanalisis
marcada `P05_REFERENCE_FIT=1`; no existen en el fit de referencia.

| Misma referencia fisica, Slow 100 C | Reglas originales | Reglas CDC |
| --- | ---: | ---: |
| Setup global | -7.145 ns | -12.093 ns |
| Hold global | -1.592 ns | -5.210 ns |
| Setup interno CPU | -4.270 ns | -4.270 ns |

Las nuevas rutas expuestas incluyen `init_reset_n -> micro_pc` (HPS 100 MHz
a CPU) y `avl_readdataack -> o_readdataack_sync` (HPS 100 MHz a HDMI).
El OSD antiguo tambien muestra -10.935 ns hacia `osd_vcnt` al retirar su
excepcion amplia. **Estas cifras NO son resultados del candidato CDC** ni una
regresion fisica: es exactamente el mismo fit bajo un analisis mas amplio.
El reset de entrada a CPU se suma al inventario de cruces a revisar; no se ha
modificado aqui la secuencia de reset de la maquina.

Limitacion encontrada: el test completo `at_scaler_cdc_tb.vhd` se detiene en
GHDL estricto por `o_pshift <= o_off(0)-1` con `o_off(0)=0` (destino natural
0..15). Se reproduce con `ENABLE_CDC=false` y `true`, antes de comprobar
frames. No se desactivan los controles de rango ni se modifica ese datapath
heredado para convertirlo en un PASS. La suite dirigida no incluye ese test
como criterio superado. La simulacion integral de frames sigue pendiente.

## Sintesis a cargo del usuario

Se mantiene el proyecto **`PCAT-286_AT.qsf`**, sin FAST. El nuevo directorio
de salida es **`output_files_pcat286_at_cdc/`**, para evitar confundir el
resultado con el RBF seed 2 anterior. El script de build descubre la salida
desde el QSF y exige un RBF realmente nuevo.

Para generar el candidato cuando se decida:

```sh
bash scripts/build_at_no_debug.sh
```

O compilar el proyecto AT desde la raiz con el flujo habitual. Despues revisar
todos los corners y comprobar HDMI/splash/OSD, arranque, teclado, cambios de
modo EGA y CheckIt con la misma configuracion de BIOS y discos.
No se promete mejora de CheckIt: el objetivo inmediato es seguridad CDC y
reducir presion fisica del routing, sin cambiar el trabajo de la CPU.

Referencia recuperable sin recompilar:
`releases/PCAT-286_20260914_AT_nodebug_seed2.rbf` (hash y metricas en
`P05_NODEBUG_SEED2_SNAPSHOT.md`). Base de datos fisica conservada localmente en
`build/p05/20260914-nodebug-seed2-reference/`, sin incorporarla a Git.
