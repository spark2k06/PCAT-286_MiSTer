# P05 AT sin debug: referencia seed 2

Rama de referencia: `codex/spk286-p05-nodebug-seed2`.
Conserva el estado local P05 (comprobacion paralela de limites), retirada de
observadores AT y correccion de la cadena de configuracion sin bytes NUL.
La siguiente experiencia CDC debe partir de esta referencia en otra rama.

## Artefacto conservado

- Proyecto: `PCAT-286_AT.qsf`, seed 2, SMART_RECOMPILE OFF.
- RBF: `releases/PCAT-286_20260914_AT_nodebug_seed2.rbf`.
- Origen: `output_files_pcat286_at/PCAT-286_AT.rbf`.
- Fecha del fichero: 2026-09-14 19:03:53 Europe/Madrid.
- Tamano: 3665816 bytes.
- SHA-256: `7cb5bc0bc3fa523a9c7a895c1508cc33ffb0e85fa157f8d1d143f9c12b3df8fe`.
- Quartus 17.0.2: 0 errores, 686 advertencias; 19 min 05 s reales segun
  el resultado comunicado por el usuario.
- Estado: **pendiente de prueba en placa**. La compilacion correcta no implica
  cierre de timing ni confirma que haya desaparecido el fallo de HDMI anterior.

## Resultado fisico de referencia

| Medida | Valor |
| --- | ---: |
| ALM | 18686 |
| Registros | 21769 |
| Setup global multicorner | -7.145 ns |
| Hold global multicorner | -1.592 ns |
| Setup CPU, Slow 100 C | -4.270 ns |
| Setup salida SDRAM, Slow 100 C | +0.291 ns |
| Hold salida SDRAM, Slow 100 C | +0.423 ns |
| TNS setup multicorner | -3745.07 ns |

El inventario fisico confirma cero observadores de debug.

Recorridos relevantes: `video_calc` de reloj de video a 50 MHz; configuracion
OSD de 50 MHz a video; `cfg_done` hacia el ajuste PLL; dimensiones de entrada
del scaler hacia HDMI. Deben corregirse los protocolos CDC antes de introducir
excepciones especificas. No se autoriza ocultar logicamente recorridos internos
de CPU, SDRAM ni relaciones de fase entre relojes del mismo PLL.

No se incluyen ROMs privadas de prueba, resultados DOS ni bases de datos de
Quartus en Git. Se conserva el RBF nombrado para no depender de un directorio
de salida que otra compilacion pueda sobrescribir.
