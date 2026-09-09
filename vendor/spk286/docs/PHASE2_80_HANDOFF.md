# SPK286 Phase 2.80 — Microcode Toolchain Validation & Hardening

Fecha de validación: 2026-09-07. Rama: `codex/phase2.80-toolchain-hardening`.

## Resultado y baseline contractual

Phase 2.80 terminada. La CPU conserva exclusivamente `MOV r16, imm16`
(`B8..BF`) y el comportamiento arquitectónico de Phase 2.75. No se ha cambiado
ningún fichero de RTL, banco RTL, harness de simulación, source `.mc`,
compilador de producción ni artefacto generado.

Baseline recibido limpio: `b7eaa46bc4cb9a2fc51f8a63f0f5b3e6f00c60df`, handoff
final de Phase 2.75. Sus commits de implementación son `10c30f8` y `ad7b71a`.
Antes de modificar código se leyeron los handoffs de Phase 2, 2.5 y 2.75, el
informe histórico PRE_PHASE3_AUDIT, el contrato de microcódigo y timing y las
reglas del proyecto. El informe PRE_PHASE3_AUDIT describe un bloqueo anterior
a Phase 2.75: no invalida el handoff más reciente ni se reescribe su historia.
Los ejemplos amplios del documento de formato no son funciones implementadas:
el subconjunto contractual continúa siendo FETCH_IMM16, MOVE y END.

Se reprodujo la regresión del baseline desde un directorio nuevo,
`build/phase2.80-baseline`, con 42 tests Python, diez bancos RTL por simulador,
cuatro vectores de estado, lint y síntesis completos; SingleStep smoke 80/80,
sample 800/800 y full 40.000/40.000. El full del baseline recibido tardó
5,594 s, 7.150,2 tests/s. El handoff anterior había medido 5,324 s; no es una
discrepancia funcional ni una medida de timing histórico.

Corpus conservado limpio: `SingleStepTests/80286`,
`37c73caf53dcd22d3dd369ff09305d13d117a4fe`, versión 1.1.0, MIT,
capturas Harris N80C286-12. No se refrescó, filtró adicionalmente ni modificó
ningún resultado esperado.

## Fuentes y reconstrucción MCL86

El [informe de formato](../research/mcl86/README.md) contiene la gramática,
ambigüedades, comandos, restricciones y evidencias completas;
[sources.json](../research/mcl86/sources.json) fija los seis ficheros por
repositorio, commit, URL y SHA-256.

Fuentes primarias:

- [MicroCoreLabs/Projects, commit 78f3fb0](https://github.com/MicroCoreLabs/Projects/tree/78f3fb0eb230e014f4a53397d8577c3570681b9d/MCL86/Core):
  `Microcode_MCL86.txt`, ROM v4 de 4096 × 32 y `eu.v`.
- [Reescritura SystemVerilog, commit 1021f78](https://github.com/MiSTer-devel/PCXT_MiSTer/tree/1021f7877b672e21a17e002f2b686ee4e3d3dfe9/rtl/8088):
  `mcl86_ucode.mem`, `mcl86_ucode.sv`, `mcl86_eu_core.sv`.
  Atribución de cabecera: Ted Fried y Marcus Andrade; incorporación
  `1dd8ac50098cfe29239313f7379d111064778a98`, coautor Boogermann.

Las cabeceras de fuente/RTL inspeccionadas contienen MIT. Las ROMs no tienen
cabecera individual. Los originales permanecen externos e ignorados bajo
`.cache/mcl86`; no se redistribuye ni reutiliza código de CPU ajeno. Los
scripts originales mencionados por el RTL no aparecen en los árboles públicos
consultados. Las herramientas creadas son independientes y mínimas.

El fuente original es un stream `p` de dirección/mitad alta/mitad baja, con
espacios ROM (`00001`) y control (`00010`) distintos, directivas de transporte
`d` y `x`, comentarios `#`/`//` y separadores de guiones. Las direcciones son
hexadecimales de palabra; se ensamblan 3.299 direcciones explícitas y se rellenan
797 huecos con cero. No hay duplicados ni direcciones fuera de rango en esta
revisión. No se atribuye una unidad o base numérica a las demoras opacas.
Los errores documentales de bitfields no se trasladan al empaquetado.

| Comprobación | Resultado exacto |
| --- | --- |
| TXT original → imagen frente a ROM pública v4 | 4.096/4.096 palabras iguales; 0 diferencias |
| Generada frente a referencia v4 normalizada | 36.864/36.864 bytes iguales |
| Generada frente a ROM reescrita | 431 palabras distintas |
| ROM v4 → disassemble → assemble | 4.096/4.096 palabras iguales |
| ROM reescrita → disassemble → assemble | 4.096/4.096 palabras iguales |

Las diferencias de la reescritura se distribuyen en 293 ceros sustituidos por
palabras no nulas, dos conversiones a cero y 136 sustituciones no nulas.
Primeras direcciones distintas: `014` (`00000000` → `488ffffe`), `015`
(`00000000` → `10000f1a`) y `016` (`00000000` → `4ebfffff`). También cambian
saltos existentes: `1D4` (`100002c7` → `100002db`), `1F6` (`10000e12` →
`10000e10`), `1F7` (`10000e83` → `10000f2b`).

El informe `build/phase2.80-final/mcl86/comparison.json` conserva las 431
diferencias. La igualdad exhaustiva con la ROM original demuestra que la
discrepancia no viene del parser, el orden de mitades ni el relleno. La imagen
entregada en el commit de la reescritura es distinta. Al no existir un source
simbólico público correspondiente, no se puede reconstruir la motivación
individual de cada cambio. No se aplicó ningún parche para igualar revisiones.

## Hashes reproducibles

SHA-256 de las entradas y salidas MCL86 principales:

| Representación | SHA-256 |
| --- | --- |
| TXT original descargado | `5c90aefa77a8b7459b6f9ac20b431368b07d0823f0dcb0b64af6af75bcd43883` |
| ROM v4 `.coe` descargada | `b3fa073a6046a6a68909e7fba950ad96f0daaf73b4c41cad00b53fc219fa3c54` |
| Generada / v4 canónica / v4 reconstruida | `815ae9daea502b70b6fd40d8158db0afad55a7f7eb6e83db309f3c97875631d0` |
| ROM reescrita descargada | `36331cfced4379edf63e8939478deed4ec1de961f818b5c0bbd3172b01ca7f93` |
| ROM reescrita canónica / reconstruida | `3ed0a2f830a99c70a7877b16a8a771730a650029a0bc1787bc7250b9f007acae` |

La `.coe` es una lista densa de tokens, sin cabecera COE. Su serialización
se normaliza a ocho dígitos minúsculos y LF por palabra. La `.mem` reescrita
carece únicamente del LF final: 36.863 bytes originales frente a 36.864
canónicos. Se verifica el hash de bytes descargados antes de interpretarlos;
no se confunde igualdad de palabras con igualdad de formato textual.

SHA-256 de SPK286, idénticos a Phase 2.75:

| Artefacto | SHA-256 |
| --- | --- |
| `spk286_microcode_pkg.sv` | `2319e58c5cd96a34b401e8b1f7fa1257926b54a4ff797b77d320a05fff82ac12` |
| `spk286_microcode_rom.sv` | `8a102fcbdb627c6dd9482cb19df1ae2c8d7a5943031ee7b9f9d278146d258309` |
| `spk286_microcode.lst` | `1786d059d510d2f86556d46f7efe1614d6c7a1a46819782e1df68ab1c96b895f` |
| `spk286_microcode_symbols.json` | `3086cb1d13f5de2c5459f7b4c76d02420a54541841a53eb231abad718d39a21a` |
| `spk286_microcode_validation.json` | `f2b5587415e995e32c1830a137d1f8dc9cb211e0eae8b89237685715bd8db774` |

El hash del source normalizado `data_move.mc` es
`da7aef70bc2c61c3c9019be91aab7b9c1fe30d11390b299cba762e926b09b88b`.
Se regeneraron los cinco artefactos también con Windows Python, comparando
todos sus bytes. Los informes de auditoría y comparación MCL86 coinciden
entre Windows y WSL. Una descarga adicional en una carpeta nueva reprodujo
los seis hashes públicos y exactamente el mismo informe de comparación.

## Auditoría SPK286 y cambios justificados

| Capacidad | Estado recibido / actuación de Phase 2.80 |
| --- | --- |
| Generación y símbolos deterministas | Ya existían orden de rutas y orden de fuente; tests nuevos entre procesos, semillas y CRLF/LF |
| Parsing estricto y diagnósticos | Ya rechazaba sintaxis/operandos/formatos inválidos con fichero, línea y entrada; se conserva |
| Direcciones duplicadas | El compilador asigna secuencialmente, sin sintaxis de dirección manual; extracción de ROM añade detección negativa independiente |
| Fuera de rango | Ya existían límites de profundidad y ancho; nuevos tests CLI y de ROM emitida |
| Labels indefinidos | Ya falla la consulta de símbolo; ramas ejecutables siguen siendo sintaxis no soportada |
| Entry points contractuales | Nuevo fixture fijo y validador de entrada ausente/desplazada, ejecutado por la regresión |
| Representación canónica y round-trip | Nuevo lector de la plantilla RTL encoding 1 y reconstrucción DSL con sidecar de símbolos |
| Hashes de ROM | Nuevo informe de SHA-256 de los cinco artefactos sin cambiar los outputs de producción |
| Acoplamiento source/ROM | Se mantiene la comparación íntegra de cinco artefactos; test nuevo demuestra que cambiar sólo un comentario invalida los metadatos |

La carencia demostrada era de verificación contractual: insertar una entrada
anterior desplaza MOV, pero regenerar todos los outputs no detecta por sí solo
ese desplazamiento. El test construye ese caso, constata la dirección movida
y exige un diagnóstico del nuevo validador. No es un defecto funcional del
RTL: el decoder ya usa el símbolo generado. El nuevo gate evita aceptar
accidentalmente otro contrato bajo el nombre de esta fase.

Se añadieron `tools/microcode/audit_microcode.py`, el fixture contractual y
tests; se integraron en `make microcode-test`, `make microcode-audit` y
`make regression`. El lector de RTL no pretende analizar SystemVerilog general:
se ejecuta tras verificar la plantilla completa contra el compilador. El
round-trip compara control, profundidad y símbolos, no comentarios o líneas
del fuente original. Las palabras no contienen nombres de entrada/labels;
por ello el sidecar es necesario. No se añade otro formato de producción.

## Diferencias con MCL86 y decisiones rechazadas

MCL86 utiliza ROM 4096 × 32 con lectura registrada, dispatch y saltos internos,
campos ALU/operandos y marcadores dependientes de direcciones. SPK286 conserva
su ROM combinacional de tres palabras de dos bits, decode B8..BF externo al
microsequencer y avance dependiente de operación completada. La lección común
es verificar determinismo y acoplamientos, no compartir organización interna.

Se rechazaron deliberadamente adoptar el microword MCL86, imponer profundidad
4096, cambiar latencia de ROM, importar ALU/saltos/dispatch, raspar marcadores
de RTL o añadir un lenguaje simbólico MCL86 completo. Tampoco se añadieron
HEX/MIF de producción, librerías externas, asignación manual de direcciones,
un parser SystemVerilog general ni refactors del compilador existente.
Ninguna de esas actuaciones estaba justificada por un defecto reproducido.

## Tests y comandos de regresión

Se añaden 36 tests Python: 24 de herramientas MCL86 y 12 de auditoría SPK286.
Los 42 anteriores se conservan: total 78. Los tests MCL86 incluyen empaquetado,
huecos, orden de direcciones, controles separados, comentarios, errores de
directiva/ancho/rango/duplicado/mitades, CLI y preservación de salida ante error,
round-trip de 4096 patrones sintéticos, hash de referencia, informe de
discrepancias y fallo real de comparación. Los tests SPK286 cubren contrato
fijo y mutaciones, símbolos, padding, corrupción de ROM, semántica al volver
a compilar, acoplamiento del source, procesos distintos y errores CLI.

El primer gate completo pasó antes del commit de implementación. Después se
ejecutó desde el checkout limpio de `b0d69e03c8d0df498a79eab3dc8610ac49216b23`,
con `build/phase2.80-final` todavía inexistente. No se reutilizaron ejecutables
de los builds baseline/precommit ni se borró evidencia anterior.

```bash
# WSL, desde /mnt/d/GitHub/SPK286
set -euo pipefail
test -z "$(git status --porcelain)"
test ! -e build/phase2.80-final
mkdir -p build/phase2.80-final
export SPK286_BUILD_DIR="$PWD/build/phase2.80-final"
export MAKEFLAGS=-j4
make phase2.80-check > "$SPK286_BUILD_DIR/validation.log" 2>&1
git diff --exit-code b7eaa46 -- rtl sim microcode/generated microcode/source tools/microcode/compile_microcode.py
test -z "$(git status --porcelain)"
```

En una máquina sin referencias: `make mcl86-fetch` y `make singlestep-fetch`
antes del gate. `scripts/validate_phase2_80.sh` contiene la secuencia completa:
Python/toolchains → lint → bancos duales → smokes/vectores → SingleStep
80/800/40.000 → Yosys → regresión → negativos/data/replay → consistencia.
Exige el corpus contractual limpio y no admite skips externos. La regresión
normal sigue siendo offline; CI añade la reconstrucción pública como gate
explícito. Una caché incorrecta o ausente falla, no se repara silenciosamente.

La secuencia final devolvió estado 0, `PHASE2_80_VALIDATION_PASS` y
`FINAL_CLEAN_VALIDATION_PASS`. `initial-status.txt` está vacío y `commit.txt`
registra el commit validado. Resultados finales:

| Gate | Resultado |
| --- | --- |
| Tests Python totales | 78/78 PASS, incluidos los 42 previos |
| Tests SPK286 de compilador/auditoría | 43/43 PASS (31 previos + 12 nuevos) |
| Tests MCL86 independientes | 24/24 PASS |
| Generación/consistencia SPK286 | Cinco artefactos idénticos al baseline |
| ROM MCL86 original / round-trips | 4.096/4.096, sin pérdidas; diferencias de revisión declaradas |
| Verilator lint | PASS, `--Wall`, core y componentes |
| Bancos RTL | 10/10 Verilator y 10/10 Icarus PASS |
| Registros | 200 comprobaciones más reset/commit, en ambos |
| Segmentos | 262.202 comprobaciones, incluidas 262.144 cargas de párrafo, en ambos |
| Fetch / core / cola | 26 / 7 / 19 comprobaciones contadas, en ambos |
| Microsequencer / ROM / decoder | 37 / 4 / 256 comprobaciones, en ambos |
| Ejecución heredada | 16 transacciones y casos single/multi-MOV, stalls, redirect y opcode no soportado, en ambos |
| Ejecución de microcódigo | 48 vectores MOV, flujo de ocho MOV, cuatro límites cancel/reset/resume; 5.380 comprobaciones y 375 ciclos de underfill, en ambos |
| Reset smoke | Ambos PASS, primer fetch `FFFFF0` |
| Vectores de estado | 1 + 3 = 4 PASS; este adaptador informa cero instrucciones ejecutadas |
| SingleStep smoke B8..BF | 40.000 descubiertos, 0 revocados, 39.920 no seleccionados, 80/80 PASS |
| SingleStep sample B8..BF | 40.000 descubiertos, 0 revocados, 39.200 no seleccionados, 800/800 PASS |
| SingleStep full B8..BF | 40.000 descubiertos, 0 revocados, 0 no seleccionados, 40.000 ejecutados/pasados, 0 fallidos |
| Yosys | Nueve ámbitos estructurales y una síntesis genérica completa; diez informes, todos con cero problemas |
| Síntesis genérica | 4.707 celdas, incluidas 607 flip-flops; mismo resultado que Phase 2.75 |
| Regresión completa | PASS |
| Fallo negativo de reset | Ambos simuladores rechazan la expectativa deliberadamente incorrecta |
| Data-loader smoke | Un fixture parseado/seleccionado; ejecución explícitamente deferred |
| Replay B8 índice 0 | 1/1 PASS, VCD generado |
| Fuente / waveform | PCs 0, 1, 2 observados programáticamente; PC 1 → data_move.mc:7, TMP0 → DST |

Cada opcode del full aporta exactamente 5.000/5.000 casos y 50.000 ciclos de
implementación, como Phase 2.75. Full final: **5,149 s / 7.767,9 tests/s**.
No se interpreta la variación de throughput del host como una optimización
de CPU o equivalencia de timing histórico. Las cantidades de comprobaciones
dirigidas no son porcentajes de cobertura ISA.

Versiones: Python WSL 3.12.3, Verilator 5.020, Icarus 12.0, Yosys 0.33,
GNU Make 4.3, G++ 13.3.0 y kernel WSL 6.6.87.2-microsoft-standard-WSL2.
No se instalaron herramientas ni se cambió configuración del host. WSL mostró
ocasionalmente su aviso previo de sesión systemd; los procesos concluyeron.
Make anidado informó `jobserver unavailable` y compiló en serie. No hubo
warnings RTL significativos ni fallos positivos sin resolver; los mensajes
FAIL/FATAL de reset pertenecen únicamente al gate negativo deliberado.

## What Phase 2.80 deliberately did NOT change

- Ninguna instrucción x86 nueva; sólo B8..BF continúa implementado.
- Ningún ModR/M, operando de memoria, EA o ALU arquitectónica adicional.
- Ningún Protected Mode, descriptor, privilegio o excepción nuevos.
- Ningún cambio en microword, formato/encoding, ROM de producción,
  microsequencer, decoder, datapath, interfaces, BIU o prefetch.
- Ningún cambio de retirement, READY, pausas, cancelación, FLAGS, IP o timing.
- Ninguna optimización, padding, modo Accurate/Fast/Max ni NOP semántico.
- Ninguna integración PC/AT/MiSTer, reutilización de microcódigo ajeno ni
  corrección de expectativas de vectores/corpus.

La identidad de esos ficheros frente al baseline se comprobó con Git y la
identidad de los cinco artefactos se verificó byte a byte. No hubo cambios
arquitectónicos excepcionales que requirieran un test de defecto previo.

## Limitaciones, estado del árbol y Phase 3

MCL86 se valida como formato/toolchain: no se ejecuta su ISA ni se certifica
su timing, pipeline o marcadores. La ROM de la reescritura no tiene source
simbólico público correspondiente; su disassembly canónico conserva todos
los bits, pero no reconstruye intención humana. El fetch inicial necesita
disponibilidad de las URLs públicas fijadas; después la validación es local.

Los límites de Phase 2.75 permanecen: interfaz de fetch normalizada, timing
histórico pendiente, sin ModR/M/datos/protección/excepciones. SingleStep sigue
comparando estado arquitectónico; no equivale a validación de ciclos de bus.
Quartus, FPGA física, ALM y Fmax no se midieron, como en el baseline.

Commits: `b0d69e0` implementa y documenta las herramientas; el commit que
contiene este handoff registra la validación limpia final. Los logs, traces,
ROMs reconstruidas y referencias permanecen ignorados bajo `build/` y `.cache/`.
El árbol de trabajo queda limpio al finalizar; no se hace push ni merge a main.

Recomendación: iniciar Phase 3 con `89 /r` y `8B /r` en registro directo,
probando sus 128 combinaciones REG/RM (64 por opcode), preservación de FLAGS
y retirement. Versionar explícitamente el contrato de la nueva fase conservando
el fixture histórico. Después incorporar EA de 16 bits y el servicio BIU de
datos con READY y arbitraje de prefetch antes de las formas de memoria.
Mantener los 40.000 casos B8..BF y añadir las familias SingleStep pertinentes;
no avanzar a otras funciones de ISA o timing por el mero hecho de disponer
de un toolchain validado.
