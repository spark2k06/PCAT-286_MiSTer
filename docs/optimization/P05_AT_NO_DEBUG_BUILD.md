# P05 AT sin debug: corrección y preparación de compilación

Fecha: 2026-09-14. Rama: `codex/spk286-pm5-vendor-sync`.

Estado: fuentes y configuración verificadas, pendiente de nueva síntesis y
validación de HDMI en placa por el usuario. No se ha generado otro RBF aquí.

## Por qué se reutilizaba el RBF

El informe del fitter del RBF de las 17:32:38 ya indicaba:

```text
Optimize Hold Timing       All Paths       Default: All Paths
Use smart compilation      On
Fitter Initial Placement Seed  1
```

Añadir `OPTIMIZE_HOLD_TIMING ALL_PATHS` sólo explicitaba el valor que ya estaba
en uso. No era una mejora nueva ni obligaba a repetir el fit. Con recompilación
inteligente, una ejecución corta podía terminar correctamente sin regenerar
el bitstream. El cambio anterior fue insuficiente.

En `PCAT-286_AT.qsf` se establece ahora `SMART_RECOMPILE OFF` y `SEED 2`.
Se conserva `ALL_PATHS` explícito y se explica que era el valor predeterminado.
No se cambian frecuencias, fases de PLL ni excepciones temporales para forzar PASS.

## Error reproducido al retirar el menú de debug

`CONF_STR_AT_DEBUG = ""` dentro de una concatenación de constantes Verilog
introducía un byte `00`. No representaba una secuencia de cero bytes.

La nueva prueba del parámetro real entregado a `hps_io` falló antes del arreglo:

```text
AT_CONFIG: invalid byte at offset 350 of 402
```

El código local de `Main_MiSTer/user_io.cpp`, `user_io_read_confstr()`, termina
la lectura al recibir ese cero. Quedaban fuera las entradas posteriores:
reset, botones y versión. `V,v` es el marcador de versión; no es un control
de activación de HDMI.

Se ha eliminado el elemento completo de la concatenación cuando está definido
`SPK286_AT_NO_DEBUG`. La prueba comprueba ausencia de NUL, presencia de las
opciones necesarias y ausencia de opciones de debug. Resultado:

```text
AT_CONFIG_NO_DEBUG_PASS bytes=401
AT_PROFILE_SELECTOR_PASS
AT_PROFILE_ELAB_PASS
```

## Qué demuestra el análisis del RBF anterior

RBF analizado: `output_files_pcat286_at/PCAT-286_AT.rbf`, 3.656.496 bytes,
SHA-256 `a7b571f4a1878cbefcf4bb9ba92573788e0a6f9b2c98fd3b586603a665eb5eea`.

TimeQuest se ejecutó sobre una copia de su base de datos, sin síntesis ni fit.
Los informes están en `analysis/p05/20260914-no-debug-original-fit/reports/`.
La configuración actual no sustituye el placement de esa base de datos antigua.

- `no_debug=1 observers=0`: el fit sí eliminó overlay y trazas de boot/RAM/fallo.
- Hold -1,808 ns: `vga_osd|info` hacia `vga_osd|osd_de[0]`, de 50 MHz al reloj
  de vídeo de 57,27 MHz/+90°. Es un cruce del OSD común de MiSTer.
- Setup -6,873 ns: `cfg_done` hacia `pll_hdmi_adj|i_vss2`.
- Setup -5,225 ns hacia HDMI: metadatos del scaler `ascal|i_hdown` hacia
  `ascal|o_ihsize[7]`, entre los relojes de entrada y salida del scaler.

Estos recorridos no prueban que el PLL HDMI dejara de funcionar. La atribución
anterior de la falta de señal al hold a partir del resumen era demasiado firme.
El defecto de configuración está reproducido y corregido; recuperar HDMI y
cerrar timing requieren probar el nuevo fit. No se han ocultado estos cruces.

El script `report_p05_at_timing.tcl` ya admite producción sin observadores,
comprueba su ausencia y genera recorridos de setup/hold de vídeo y HDMI en los
cuatro modelos de operación. No exige una colección de debug inexistente.

## Compilación preparada

Proyecto: `D:\GitHub\PCAT-286_MiSTer\PCAT-286_AT.qsf`.
La comprobación con Quartus 17.0.2 confirmó SDC AT, macros AT/P05/NO_DEBUG,
recompilación inteligente desactivada, seed 2 y generación de RBF activada:
0 errores, 0 advertencias. FAST y XT no se han modificado en esta corrección.

Para una compilación limpia y con identidad de fuentes registrada, ejecutar
desde WSL en la raíz del repositorio:

```bash
bash scripts/build_at_no_debug.sh
```

El script reutiliza la utilidad de snapshots del proyecto. Crea una copia nueva
en `build/at-no-debug/<fecha>-<proceso>/work/`, incluyendo los cambios locales;
no copia `db`, `incremental_db` ni bitstreams anteriores. Verifica configuración
y OSD, compila explícitamente `PCAT-286_AT`, exige un RBF nuevo y registra su
SHA-256, tamaño y fecha. Después genera los informes detallados de timing.
Imprime la ruta del RBF obtenido; los binarios anteriores quedan conservados.
Generar un artefacto no equivale a aprobar timing ni la prueba de placa.

Para preparar y comprobar sin sintetizar:

```bash
bash scripts/build_at_no_debug.sh --prepare-only
```

Esta modalidad se ha validado en
`build/at-no-debug/20260914-prepared-seed2/`. Su `manifest.json` conserva las
fuentes de esa preparación; `profile-check.log` y `project-check.log` contienen
los resultados. No hay un RBF nuevo en ese directorio.

La compilación habitual desde la raíz también sigue disponible con
`quartus_sh --flow compile PCAT-286_AT -c PCAT-286_AT`, utilizando el QSF
corregido. En ese caso la salida permanece en `output_files_pcat286_at/`.
