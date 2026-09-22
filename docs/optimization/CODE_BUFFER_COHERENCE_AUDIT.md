# Auditoría de coherencia del búfer de código

**Registro histórico previo a la corrección.** La implementación posterior de
[512 bytes](CODE_BUFFER_512B_50MHZ.md) corrige los fallos descritos aquí. Los
recibos de esta auditoría conservan la evidencia original; el banco y su
ejecutor actuales son una regresión positiva que exige que los tres casos
terminen correctamente, ya no que fallen.

Fecha: 2026-09-22. Base de producción: `266f5b49c4c63b25bb5d7e857a77084bcb9511a7`.
La auditoría acompaña la evaluación de varias líneas en simulación. No modifica
el RTL de producción, no genera un RBF y no establece una relación causal con
el problema de arranque de Windows.

El [recibo de evidencia](code_buffer_coherence_audit.json) conserva SHA-256 del
RTL, del banco, del modelo experimental revisado y de los logs; versiones de
simulador y resultados. El banco y su ejecutor están versionados. Las seis ejecuciones
reproducen deliberadamente fallos de aserción: no son una regresión funcional
aprobada ni errores de compilación.

## 1. Escritura al último byte impar: dato obsoleto reproducido

El owner SDRAM transforma una dirección de byte en palabra mediante
`address[24:1]` y aplica DQM por lane. Por tanto:

| Lane habilitada | Byte físico escrito |
| --- | --- |
| `BE[0]` | `{address[24:1], 1'b0}` |
| `BE[1]` | `{address[24:1], 1'b1}` |

La función `write_touches_line` del
[`spk286_at_sdram_read_buffer`](../../rtl/spk286_integration/spk286_at_sdram_read_buffer.sv)
de producción compara, en cambio, `address` y `address+1`. Una petición con
dirección terminada en `...7` y `BE=10` escribe físicamente ese último byte de
la línea, pero la invalidación compara la línea siguiente.

Reproducción dirigida, repetida con owner CPU y owner DMA:

1. Llenar la línea `001000h`; la última palabra contiene `A004h`.
2. Escribir `CC00h` con dirección `001007h` y `BE=10`.
3. Verificar que el backend contiene `CC04h` en la palabra `001006h`.
4. Volver a solicitar código en `001006h`: el búfer devuelve `A004h` porque
   sigue válido. La aserción que exige `CC04h` falla.

Las direcciones impares son alcanzables en producción. El
[`spk286_at_bus_bridge`](../../rtl/spk286_integration/spk286_at_bus_bridge.sv)
conserva A0 y elige upper lane para un byte impar; el mapper de máquina no
elimina A0. El
[`spk286_at_dma`](../../rtl/spk286_integration/spk286_at_dma.sv)
hace lo mismo para los canales de byte. El loader HPS real emite `BE=11`
siempre; estos casos CPU/DMA no prueban un fallo equivalente originado por una
transferencia normal HPS de upper lane aislada.

Este hallazgo exige corregir la comparación de lanes y probar que la línea
adyacente no se invalida indebidamente. No requiere aumentar la capacidad del
búfer ni cambiar el backend de SDRAM.

## 2. Cancelación CPU estando IDLE: requisito no cumplido

P03-R15 exige invalidación conservadora ante reset CPU. El RTL actual solo
invalida por `cancel_cpu` cuando hay una operación CPU activa. Después de
llenar una línea, aplicar `cancel_cpu` durante dos ciclos en IDLE y retirarlo,
la línea sigue válida y la siguiente lectura es un hit:

```text
AUDIT_IDLE_CANCEL valid_after_cancel=1
AUDIT_IDLE_CANCEL physical_reads_before=4 after=4 hits=1
```

Esto reproduce un incumplimiento del requisito documentado. **Conservar esa
línea por sí solo no demuestra corrupción:** la memoria del reproducer no
cambia durante el reset y los datos retornados siguen siendo correctos.

Los resets OSD también pueden llegar por este camino. El top conecta el reset
del buffer a `RESET`, pero conecta `at_machine_reset | at_cpu_reset_request`
a su entrada `cancel_cpu`. El cambio de tamaño de RAM se captura durante
`at_boot_reset`, que incluye controles OSD y llega como cancelación CPU sin
exigir un reset físico de SDRAM.

## 3. Resultados de los dos simuladores

| Caso | Icarus Verilog 12.0 | Verilator 5.020 | Evidencia |
| --- | --- | --- | --- |
| CPU, último byte impar | Falla esperada, salida 1 | Falla esperada, señal 6 | Backend `CC04`, línea válida `A004`, fetch obsoleto |
| DMA, último byte impar | Falla esperada, salida 1 | Falla esperada, señal 6 | Backend `CC04`, línea válida `A004`, fetch obsoleto |
| Cancelación CPU en IDLE | Falla esperada, salida 1 | Falla esperada, señal 6 | Hit tras cancelación; sin nuevo fill |

Python registra la terminación por señal 6 de Verilator como `returncode=-6`;
un shell la expresa como salida 134.

El banco usa un backend con aceptación registrada y cuatro beats por fill.
No usa un modelo de pines SDRAM en estas reproducciones; la correspondencia
de direcciones y lanes se contrasta con el owner físico de producción.

El banco versionado es
[`spk286_code_buffer_coherence_audit_tb.sv`](../../sim/spk286_integration/spk286_code_buffer_coherence_audit_tb.sv).
El ejecutor
[`test_code_buffer_coherence_audit.sh`](../../scripts/test_code_buffer_coherence_audit.sh)
compila ambos simuladores y ejecuta `+CASE=0` (CPU), `+CASE=1` (cancelación) y
`+CASE=2` (DMA):

```sh
bash scripts/test_code_buffer_coherence_audit.sh
```

La salida `COHERENCE_AUDIT_PASS meaning=BUG_REPRODUCED` significa que se han
reproducido los tres casos en ambos simuladores, **no que el búfer sea correcto**.
El ejecutor exige el código de terminación, la observación de memoria y la
única línea de aserción esperada exacta. Un fallo de compilación, otro fallo de
aserción o la desaparición de uno de los fallos conocidos hacen fallar esta
auditoría explícitamente. Cuando se corrija el RTL habrá que convertir estos
casos en pruebas de corrección y actualizar el ejecutor.

Los logs y un recibo regenerable están en `build/code-buffer-coherence-audit/`;
el JSON enlazado arriba conserva la ejecución de esta auditoría. Las primeras
reproducciones exploratorias, equivalentes, quedan en `build/multiline-audit/`.

## 4. Revisión independiente del modelo de varias líneas

El modelo
[`spk286_at_multiline_code_buffer_model`](../../sim/spk286_integration/spk286_at_multiline_code_buffer_model.sv)
es exclusivo de simulación. Acepta entre 1 y 128 líneas, potencia de dos,
una o dos vías sin exceder el número de líneas, y cero o un ciclo adicional
en los hits. La revisión estática comprobó lo siguiente:

- El índice de set usa la dirección física canónica de la línea. Un miss
  prefiere una entrada inválida y después la vía LRU. Con dos vías, un hit o
  fill marca la otra vía como próxima víctima. Con una vía, ignora el bit LRU.
- El slot y offset de palabra aceptados quedan retenidos; una modificación
  posterior de los campos de entrada no selecciona otro dato en la respuesta.
- El slot víctima queda inválido desde la aceptación hasta capturar las
  cuatro palabras. No publica válido antes del último beat con READY.
- Las escrituras CPU/DMA/loader siguen haciendo bypass y se comparan con
  todas las líneas válidas usando direcciones de lane alineadas a palabra.
- `cancel_cpu` invalida todas las líneas incluso en IDLE o mientras se sirve
  otro owner; solo cancela la entrega de la operación cuyo owner es CPU.
  Una cancelación CPU capturada persiste hasta drenar el fill y no permite
  que su terminación resucite una línea.
- Durante la revisión se señaló que el primer beat de miss heredaba la clase
  de ciclo de la operación anterior. El modelo revisado ya presenta
  `in_cycle_class` al aceptar ese miss. El owner físico actual no utiliza
  esta clase; se trata de conservar el contrato de metadata. El RTL de
  producción permanece intacto también en este punto.

No se encontró otro fallo de selección, LRU, invalidación o drenaje en la
revisión estática. Esto no sustituye las pruebas del modelo, no demuestra
implementación en BRAM y no constituye cierre de timing.

## 5. Contratos que debe conservar el experimento

Los tags siguen siendo direcciones físicas de backend de 25 bits. A20 y EMS
se resuelven antes del buffer; un cambio ordinario de A20 o página EMS no
genera necesariamente reset. Con escrituras observadas y tags canónicos no
es necesario invalidar por ese cambio para evitar alias incorrectos. El alias
CPU BIOS `FFxxxxh` llega como `0Fxxxxh`; el backend `FFxxxxh` contiene RAM
desplazada y no debe reinterpretarse como BIOS.

Se mantienen una sola petición lógica pendiente, el burst de cuatro palabras,
READY final antes de responder a un miss, y el arbitraje común. Deben probarse
cancelación en cada beat y en HIT, todas las lanes de CPU/DMA/loader, conflicto
y reemplazo, A20/EMS/BIOS, límites del mapa y bloqueo máximo de DMA/refresco.
Los contadores del buffer no sustituyen a un contador de beats físicos durante
cancelaciones: el modelo deja de contabilizar datos descartados en ese camino.

Para atribuir correctamente la ganancia, comparar una línea corregida con
varias líneas corregidas, y medir por separado la equivalencia de la variante
de una línea frente a producción en las cargas que no ejercitan estos fallos.
Las correcciones funcionales aquí identificadas siguen pendientes de traslado
al RTL de producción y de su validación correspondiente.
