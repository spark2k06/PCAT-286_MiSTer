# P05 — Cierre de timing del perfil AT en FPGA

Update 2026-10-01: see the [current fitted-path audit](P05_50MHZ_AUDIT_20261001.md)
for the single `PCAT-286` project, verified CDC correction and next bounded
RTL candidates. Earlier figures below belong to their stated historical fits.

Estado: especificación de auditoría y corrección física. Base: `4a05f97`,
2026-09-13. Aplican los [requisitos comunes](README.md).

Actualización 2026-09-14: primer candidato P05 preparado exclusivamente para
AT. Véase [implementación, pruebas y pendientes](P05_TIMING_RESULTS.md).
El usuario realizará la síntesis y el RBF; no se declara cierre físico.
XT queda fuera de alcance por indicación expresa del usuario. Se conserva su
implementación previa, sin mantener una línea de optimización o pruebas XT.

## 1. Objetivo y evidencia

Conseguir que el circuito implementado cumpla sus requisitos temporales al
reloj de operación declarado. La referencia inicial es el reloj actual de
50 MHz del dominio CPU/memoria; no se fija una frecuencia futura superior.

El informe AT_FAST disponible presenta Fmax 33,88 MHz y slack de setup -9,515 ns
para `FPGA_CLK2_50` en Slow 1100 mV/100 °C. Ese resumen agrupa el dominio:
no identifica por sí solo qué ruta CPU, chipset o cruce produce el peor valor.
El resultado CheckIt de 34,80 MHz es una estimación software diferente.

Existe una [auditoría anterior](../AT_INDEPENDENT_TIMING_AUDIT.md) con rutas CPU,
SDRAM y CDC concretas. Es evidencia de otro fit: orienta qué revisar, pero sus
endpoints y slacks no se presentan como resultados del circuito actual.

## 2. Perfiles de compilación

| Revisión | Finalidad actual | Política |
| --- | --- | --- |
| `PCAT-286_AT_FAST.qsf` | Iteración rápida, FAST FIT, ajustes balanced | Validar integración rápidamente; evaluar su propio STA |
| `PCAT-286_AT.qsf` | Ajustes orientados a rendimiento/timing | Candidato a cierre físico, sin garantía previa de éxito |

P05-R01. Compilar AT_FAST y AT con fuentes, ROM, opciones y versión de herramientas
identificadas. Cambiar fitter no equivale a optimizar RTL. Registrar por separado
ganancia de P01/P02/P03/P04 y mejora atribuible al ajuste de Quartus.

## 3. Identidad reproducible de la evidencia

Antes de modificar un candidato, conservar un manifiesto con:

- Commit y diff no comprometido de todas las fuentes incluidas por QSF/QIP.
- Revisión, familia/dispositivo exactos, versión Quartus y seed.
- QSF/SDC efectivos, macros, parámetros, fuentes de PLL y memoria inicializada.
- SHA-256 de RBF y ROM; nombre del report y copia de su netlist/base de datos.
- Fecha interna del report y fecha local, sin confundir zona horaria.
- Recursos ALM/FF/memoria/DSP y mensajes de latches, lazos e inferencia de RAM/ROM.

P05-R02. No vincular una captura a un fit por proximidad temporal. La validación
de placa registra el RBF exacto instalado. Si sólo se dispone de una captura,
su resultado queda como medida del usuario sin atribución de rutas específicas.

## 4. Inventario y auditoría de constraints

P05-R03. Enumerar todos los relojes reales y derivados: CPU/memoria, SDRAM
reenviada, vídeo, HDMI, HPS y audio. Comprobar periodo, fuente y relación física.
El inventario debe partir del netlist, no de nombres heredados de XT.

P05-R04. `PCAT-286.sdc` contiene jerarquías históricas como `emu|pll` y una
selección específica AT para `SDRAM_CLK`. Verificar qué colecciones resuelven
realmente en cada revisión. Un target vacío requiere una decisión documentada:
constraint no aplicable a ese perfil o nombre incorrecto; no se ignora sin revisión.

P05-R05. Verificar input/output delays de SDRAM DQ, dirección, comandos y máscaras,
incluida la conexión MiSTer DQM/A11/A12. Los presupuestos deben derivar del modelo
de SDRAM soportado, placa y relación de fase; valores heredados no validan por
sí solos el módulo físico. La identificación del módulo es un dato necesario
para cerrar este contrato, no para escribir o simular P01.

P05-R06. Clasificar CDC reales y mecanismos de sincronización. Un bus multibit
debe usar handshake, captura estable o FIFO apropiada; no se sincronizan sus
bits de forma independiente. Un false path sólo documenta una relación válida
ya tratada por diseño, no repara un CDC incorrecto.

P05-R07. Revisar resets asíncronos y liberación por dominio. Mantener visible la
distinción entre reset CPU, reset de memoria, loader y refresco.

## 5. Informes requeridos

Extraer, al menos, las 20 peores rutas setup y hold de cada grupo existente:

| Grupo | Pregunta que resuelve |
| --- | --- |
| CPU → CPU | Decode, ROM de microcódigo, operandos, FLAGS y writeback |
| CPU ↔ bridge | Coste de captura, selección y respuesta |
| Bridge/arbiter/memory port/owner | Controles y multiplexores de integración |
| SDRAM entradas/salidas | Relación externa con reloj reenviado y márgenes de placa |
| CPU/chipset → debug | Fanout y coste de observación |
| Vídeo/HPS/CPU entre dominios | CDC y constraints aplicables |
| Global | Rutas restantes, relojes virtuales y endpoints no previstos |

Añadir recovery/removal, mínimos de pulso, clocks, exceptions y puertos/rutas
sin constraints. Hacerlo en todos los corners del dispositivo/configuración,
incluidos modelos lentos/rápidos y extremos de temperatura admitidos.

P05-R08. Las colecciones obligatorias vacías hacen fallar el script de auditoría.
`scripts/report_i5_spk286_timing.tcl` apunta al perfil XT y no se considera un
extractor AT válido sin adaptar revisión y jerarquías. Un script AT nuevo o
parametrizado debe informar el número de registros/relojes de cada colección.

## 6. Estrategia de corrección

| Hallazgo confirmado | Acción candidata | Verificación necesaria |
| --- | --- | --- |
| Mucha lógica entre registros | Factorizar control, compartir/precalcular resultados | Equivalencia funcional y STA |
| ROM microcódigo combinacional en ruta crítica | Evaluar inferencia/registro de microinstrucción | Validez, branches de microcódigo, cancels y latencia |
| Fanout de enables/debug | Duplicación controlada, registros de observación locales | Datos coherentes y ausencia de control por debug |
| Multiplexor de respuesta grande | Selección predecodificada y payload registrado | READY/datos atómicos, un propietario |
| CDC real sin contrato | Handshake/FIFO y resets por dominio | Pruebas de cruce y de cancelación |
| Hold/setup SDRAM externo | Ajuste de fase/registro/colocación según presupuesto | Todos los corners y prueba de placa |
| Restricción heredada no aplicable | Constraints exclusivos de AT | Auditoría de cobertura; no modificar la configuración XT |

Estas acciones no se aplican por intuición. El informe debe mostrar la ruta
antes/después y distinguir retraso lógico de routing. Registrar un camino puede
añadir latencia; se evalúa conjuntamente con P04.

P05-R09. No introducir false paths o multicycle para esconder una ruta que se
usa cada reloj. Una excepción multicycle requiere un enable real, estable y
demostrable en launch/capture, con análisis de hold correspondiente.

P05-R10. No reducir la frecuencia declarada en SDC mientras el reloj físico
permanezca igual. Un cambio real de reloj necesita revisión de SDRAM, periféricos
y CDC, y comparación a su nueva frecuencia; no es un arreglo documental.

P05-R11. Si 50 MHz no resulta viable con el diseño elegido, registrar el coste
de seguir optimizando frente a operar a otra frecuencia física validada. No se
presenta MAX como una frecuencia histórica ni se altera silenciosamente el target.

## 7. Verificación funcional y rendimiento

Los refactors combinacionales se comparan ciclo a ciclo donde proceda. Los
cambios con pipeline se comparan por transacciones/commit, con backpressure,
reset, flush y eventos, sin exigir igualdad de latencia que se está modificando.

Reutilizar pruebas de CPU/PM, memoria, pines SDRAM, primeros fetches, XT-IDE,
teclado, DMA y refresco según las rutas modificadas. Un script antiguo de
equivalencia sobre `spk286_operand_timing.sv` no valida automáticamente el
`spk286_operand.sv` PM5 actualmente seleccionado por el QIP.

Medir cycles/work, reloj físico válido y tiempo total; no aceptar más Fmax
como mejora de rendimiento si la latencia extra empeora el resultado útil.

## 8. Aceptación

P05 se cierra para UNA configuración identificada cuando:

- Todas las rutas activas tienen constraints válidos o una exclusión razonada.
- Setup/hold, recovery/removal y pulse width aplicables cumplen en los corners
  soportados; no hay violaciones activas ocultas por cambiar el nombre del perfil.
- No quedan lazos combinacionales o latches involuntarios sin resolver.
- El presupuesto externo SDRAM y los CDC tienen evidencia y cobertura.
- La regresión funcional afectada pasa y se publica el efecto de latencia.
- El RBF identificado arranca y supera memoria, disco, teclado y carga sostenida
  en placa. Esta prueba complementa, no reemplaza, STA.

Si sólo cierra CPU→CPU pero falla vídeo o SDRAM, registrar cierre parcial y
mantener abierta la configuración completa. Del mismo modo, cerrar AT no
declara automáticamente cerrado AT_FAST: cada RBF tiene su propia evidencia.

## 9. Entregables

Manifiesto reproducible, script AT de extracción, inventario de constraints y
CDC, tabla de rutas antes/después, cambios mínimos de RTL/SDC/QSF y resultados
funcionales. Informe final de rendimiento/recursos, límites físicos soportados
y hash del RBF probado. La selección de seeds y esfuerzo debe ser reproducible,
no una búsqueda cuyo único resultado conservado sea el mejor Fmax.
