# P05 — Primer candidato AT: implementación y evidencia

Actualización posterior: [corrección y compilación AT sin debug](P05_AT_NO_DEBUG_BUILD.md).
Ese documento recoge la retirada de observadores, el error de cadena OSD y la
preparación con seed 2. Los apartados siguientes describen el primer candidato.

Fecha: 2026-09-14. Rama: `codex/spk286-pm5-vendor-sync`.
HEAD de partida: `92bf7e1a23975482651602f1c627a68ba73616e1` (P03).

**Estado: preparado para síntesis del usuario, no cerrado en timing.**
No se ha ejecutado síntesis, fitter ni assembler ni generado un RBF en P05.
Las ejecuciones de Quartus descritas aquí son comprobaciones de configuración
y TimeQuest sobre una copia del netlist ya existente. No miden el RTL nuevo.

## 1. Alcance y separación de XT

El trabajo se limita a AT, por indicación expresa del usuario. Para la próxima
compilación se recomienda `PCAT-286_AT.qsf`, con su esfuerzo de rendimiento
existente. `PCAT-286_AT_FAST.qsf` selecciona el mismo candidato funcional, pero
su resultado físico será independiente. No se han cambiado relojes, seed,
esfuerzo del fitter, OSD, ROM, política P01/P02/P03 ni ancho del bus EGA.

- Las dos revisiones AT usan `files_pcat286_at.qip` y `PCAT-286_AT.sdc`.
- El listado AT tiene las mismas fuentes que `files_pcat286.qip`; sólo cambia
  la línea del SDC. Se conserva separado para no modificar los proyectos XT.
- `PCAT-286.sdc`, `files_pcat286.qip`, `PCAT-286.qsf` y `PCAT-286.sv`
  conservan su contenido previo. No se modifican ni mantienen perfiles XT.
- La optimización de CPU está protegida por
  `SPK286_P05_PARALLEL_LIMIT_CHECK`, definido únicamente por AT/AT_FAST.
  Sin esa opción se conserva literalmente la expresión anterior. Se comprobó
  que el contenido efectivo de la CPU coincide con el snapshot anterior a P05.
- Los puertos de observación P04 que ya estaban pendientes en `spk286.sv` y
  `spk286_machine_cpu.sv` se conservan; no son cambios introducidos por P05.

No se modifica el repositorio independiente SPK286 ni su manifiesto de importación.
La modificación local de CPU queda identificada aquí para su eventual traslado.

## 2. Referencia preservada

`build/p05/20260914-reference/manifest.json` identifica 1.202 ficheros de fuentes
y 22 ficheros del fit con SHA-256. Incluye diff y estado Git del árbol de trabajo.
`work/` contiene la copia de fuentes y bases de datos tomada antes de P05.

La fuente capturada estaba sobre HEAD `92bf7e1` con observación P04 pendiente.
**Esto no demuestra que el fit anterior se generase con ese mismo HEAD.**
La identidad de fuentes capturadas y la de la base de datos se registran por
separado. No se atribuye una captura del usuario a un RBF sin su hash.

Referencia física disponible: revisión `PCAT-286_AT_FAST`, dispositivo
`5CSEBA6U23I7`, Quartus 17.0.2 Lite; 20.129 ALM y 24.236 registros.
Imagen Docker usada para STA:
`sha256:1fba8b9347973365e9f7851d73f7cb035e38fefb827cbf0ed2ea291b48bdf6dd`.

## 3. Rutas observadas en el fit anterior

Los cuatro modelos disponibles se analizaron, no sólo Slow/100 °C.
Todos los valores siguientes son ns; un valor negativo incumple el requisito.

| Modelo | CPU setup | Owner SDRAM setup | EGA/vídeo setup | Global setup | Global hold |
| --- | ---: | ---: | ---: | ---: | ---: |
| Slow 1100 mV, 100 °C | -8,898 | -1,137 | -8,440 | -21,435 | +0,224 |
| Slow 1100 mV, -40 °C | -9,168 | -0,973 | -8,912 | -21,019 | +0,094 |
| Fast 1100 mV, 100 °C | +4,533 | +8,348 | -5,172 | -13,547 | +0,101 |
| Fast 1100 mV, -40 °C | +6,826 | +9,316 | -4,036 | -12,723 | +0,080 |

El reloj real CPU/memoria sigue siendo 50 MHz. Fmax es una estimación de
capacidad del circuito, no el reloj que pasa a utilizar automáticamente.
Los MHz estimados por CheckIt tampoco sustituyen ese reloj físico.

Rutas concretas en Slow/100 °C:

- CPU: `prefetch_queue|head_q[1]` hacia `destination_q[0]`, a través de
  decodificación, servicios de operandos, comprobación de protección y eventos.
  23 niveles, 28,269 ns de datos, aproximadamente 58 % routing y 42 % celdas.
  Hay un incremento condicional de offset antes de la comparación de límite.
- Vídeo: `splash_active` a habilitaciones de VRAM y registros de píxel.
  Es un cruce directo de 50 MHz al reloj de vídeo de 28,64 MHz.
- Owner: `u_bridge|beat_high_q` a `u_KFSDRAM|sdram_address[9]`:
  21,785 ns de datos y 15 niveles. **No modificado en este candidato**;
  requiere revisar la nueva ruta tras el fit antes de elegir otro refactor.
- Peor global anterior: vídeo reenviado a un pin compartido con SDIO,
  comparado con el reloj virtual SDIO. No es una medida del camino CPU.

Los márgenes SDRAM externos mínimos observados con el presupuesto heredado
son +5,411 ns de setup de entrada, +0,149 ns de setup de salida,
+5,266 ns de hold de entrada y +0,224 ns de hold de salida.
Son márgenes respecto a ese presupuesto, **no validación del módulo SDRAM**.

## 4. Cambios de RTL

### 4.1 Comprobación de límite de segmento

En la CPU, para operandos de uno o dos bytes:

```text
offset + (!byte) > limit
    equivale a
(offset > limit) || (!byte && offset == limit)
```

El desbordamiento superior de un segmento expand-down equivale a
`!byte && offset == FFFFh`. Las comparaciones trabajan en paralelo al bit
de anchura; no es necesario propagar un incremento por 17 bits antes de
comparar. Se conservan las comprobaciones de permisos, presencia, pila,
límites, modo protegido y selección de excepciones.

No se añade pipeline, espera, caché, microinstrucción ni excepción temporal.
No se cambia la fidelidad arquitectónica o el número de ciclos. Su beneficio
en routing/Fmax es una hipótesis que deberá medir el nuevo fit.

### 4.2 Cruces y resets exclusivos de AT

- `spk286_at_video_adapter.sv`: sincronización de dos etapas del splash antes
  de EGA; reset de vídeo con aserción asíncrona y liberación tras dos flancos
  del reloj local. La señal del splash no controla el READY de CPU.
- `spk286_at_emu.sv`: el mismo contrato de reset para las etapas de vídeo
  57 MHz y 57 MHz/+90°, y sincronización del enable de debug antes de la
  selección de salida durante blanking.

La prueba A5 comprueba que el splash no cruza directamente ni tras un único
flanco, y que un pulso de reset más corto que un periodo de vídeo se retiene
hasta completar la liberación local.

## 5. Constraints y límites de la auditoría

El SDC AT usa los nombres reales de su PLL de vídeo. Mantiene CPU/SDRAM a
50 MHz, la SDRAM reenviada 1:1 y las relaciones de fase del PLL de vídeo.
No contiene un grupo asíncrono indiscriminado entre CPU y vídeo ni multicycle
para aliviar caminos de CPU activos en todos los ciclos.

Las excepciones de los mailboxes EGA y debug se apoyan en datos retenidos
y toggles sincronizados de petición/respuesta. Sólo se excluye la llegada a
la primera etapa de los sincronizadores de control; entre etapas se sigue
analizando un ciclo normal. Los payloads tienen un máximo de 10 ns, menor
que un periodo de destino, y no se exige hold entre sus relojes de cruce.
Esa elección produce cuatro avisos `partial_min_max_delay` deliberados.
El coste de capturar el snapshot en CPU sigue siendo visible.

Los nuevos sincronizadores son obligatorios en el candidato. La ausencia sólo
se admite con `P05_REFERENCE_FIT=1`, utilizado por el script para reanalizar
explícitamente el fit anterior, que todavía no contiene esos registros.

La selección de SDC y macro se comprobó con Quartus en las dos revisiones AT
sin compilarlas: `build/p05/project-selection.log`.
Reanálisis con el listado AT separado (mismo fit anterior, sólo constraints).
Resultado: cuatro modelos procesados, 0 errores y 8 avisos de TimeQuest,
frente a 104 avisos en la auditoría de referencia.

La corrección de jerarquías y del receptor virtual SDIO reduce avisos descartados
y cambia el peor resumen global; **no representa una mejora física medida**.
El reanálisis mantiene el peor slack CPU de -9,168 ns. Permanecen visibles
cruces sin contrato completo, por ejemplo configuración de OSD a contadores
de vídeo, y métricas de vídeo leídas desde HPS. No se ocultan para obtener PASS.

Pendientes que impiden certificar P05:

- Nuevo fit del RTL, con setup/hold, recovery/removal, pulse width y Fmax en
  todos los corners. Reexaminar CPU, SDRAM y rutas de vídeo/OSD/HPS.
- Identificar el módulo SDRAM (chip, capacidad/revisión) para validar los
  presupuestos externos 6/3 ns de entrada y 2/1,5 ns de salida.
- Revisar las excepciones comunes heredadas de MiSTer y las interfaces sin
  presupuesto: el fit anterior ya tenía 4 entradas y 50 salidas sin constraint
  completo, y 3.094 registros reportados por `check_timing` como `no_clock`.
  `report_ucp` no muestra relojes ilegales ni relojes globales sin constrain.
  Estas dos categorías no son intercambiables ni justifican una certificación.
- Las cuatro entradas enumeradas por `report_ucp` son HDMI_I2C_SDA,
  HDMI_TX_INT, IO_SDA y SDCD_SPDIF. Las salidas incluyen interfaces HDMI/VGA
  y señales lentas. Requieren clasificar su contrato externo, no excluirlas todas.
- Validación en placa del RBF exacto: HDMI, timeout del splash, arranque,
  memoria, disco, teclado y carga sostenida.

## 6. Verificación ejecutada

| Comprobación | Resultado y alcance |
| --- | --- |
| Equivalencia SAT de la expresión real de CPU | PASS para todos los valores de sus 70 bits de entrada; límites y controles sin restricciones |
| Control negativo de esa prueba | PASS: se rechaza un mutante que permite iniciar una palabra exactamente en el límite |
| Verilator lint de CPU con P05 activo | PASS; consistencia de microcódigo: 120 entradas, 717 palabras |
| Elaboración completa del perfil AT | PASS con P05 activo |
| A5 periféricos/vídeo | PASS en Icarus y Verilator; incluye los nuevos casos de CDC/reset |
| Cargas dirigidas de CheckIt, antes/después | 8 PASS; igualdad exacta de todos los contadores impresos, no sólo instrucciones |
| Primeros fetches y traza de arranque AT | PASS con P05 activo; las ROM opcionales no disponibles se registran como no ejecutadas |
| Overlay de traza AT | PASS; snapshots, traza de arranque, fallo y RAM |
| Configuración Quartus AT y AT_FAST | PASS, sin síntesis; SDC AT seleccionado y opción P05 presente |

Comparación antes/después con P03 activo:

| Carga dirigida | Ciclos antes | Ciclos P05 | Instrucciones retiradas |
| --- | ---: | ---: | ---: |
| Dhrystone | 1.220.887 | 1.220.887 | 38.656 |
| Whetstone | 1.026.205 | 1.026.205 | 44.486 |
| Working set | 1.162.323 | 1.162.323 | 56.886 |
| Dhrystone 2.1 | 1.350.819 | 1.350.819 | 59.249 |

Los cuatro pares con P03 desactivado también coinciden. No son puntuaciones
del CheckIt completo ni pruebas físicas de un 286.

Evidencia local en `build/p05/`: `limit-proof-at-only/`,
`cpu-lint-at-final.log`, `profile-at-final.log`, `a5-cdc.log`,
`checkit-reference.log`, `checkit-at-final.log`, `first-fetch-at-final.log`,
`debug-overlay.log`, `project-selection.log`.
`build/p05/validation-summary.json` registra el resultado y SHA-256 de los
17 ficheros de configuración, RTL y herramientas que identifican el candidato.

**No se declara verde la regresión completa del paquete importado.**
`vendor/spk286/scripts/test.sh` se detiene en ocho fallos de las pruebas de
microcódigo; los mismos ocho se reproducen en la copia anterior a P05.
Hay expectativas antiguas de formato 17/614 palabras frente al formato activo
20/717 y anclas de mutación antiguas. No se cambiaron sus expectativas.
El intento de `spk286_system_0f_integration` tampoco elabora: su conexión `.*`
no declara los puertos de observación existentes en la CPU importada/P04.
Estos intentos fallidos se conservan en `cpu-regression.log`,
`reference-compiler-tests.log` y `cpu-system.log`. No son cobertura PM pasada.
La prueba SAT cubre exactamente la expresión de protección modificada, no
certifica todo el modo protegido.

## 7. Síntesis y entrega al usuario

Compilar desde la raíz del proyecto la revisión **PCAT-286_AT**. No cambiar
su reloj objetivo ni usar `P05_REFERENCE_FIT=1` en una compilación nueva.
Comprobar que se leen `sys/sys_top.sdc` y `PCAT-286_AT.sdc`, no el SDC XT.
Guardar duración, informes completos, fuentes y SHA-256 del RBF antes de
instalarlo. La prueba de placa debe incluir splash activado/desactivado y
entrada/salida del debug, además de los benchmarks anteriores.

Herramientas preparadas, para ejecutar en WSL desde la raíz:

```sh
# Prueba lógica; salida nueva para preservar evidencia previa.
python3 scripts/test_p05_limit_equivalence.py --output build/p05/new-limit-proof

# Congelar una compilación terminada, sin modificar su base de datos.
python3 scripts/p05_snapshot.py build/p05/new-at-fit --revision PCAT-286_AT --with-fit

# Sólo TimeQuest sobre una copia desechable de esa base de datos.
bash scripts/run_p05_audit.sh build/p05/new-at-fit/work PCAT-286_AT build/p05/new-at-fit/audit
```

`run_p05_audit.sh` no sintetiza. Monta la referencia como sólo lectura, copia
el netlist dentro del contenedor y rechaza destinos de informes ya existentes.
`--current-sdc` es exclusivamente una comparación de constraints con un fit
anterior, no un sustituto de compilar el candidato. Su marcador PASS significa
que se extrajeron informes, no que sus slacks sean positivos.

El siguiente paso es evaluar el fit AT del usuario y elegir la próxima ruta
a corregir con esa evidencia. Este documento no promete cierre a 50 MHz ni
una subida de CheckIt por el mero cambio de expresión combinacional.
