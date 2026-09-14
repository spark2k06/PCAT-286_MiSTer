# P02 — Encadenamiento de peticiones de instrucciones en SPK286

Estado: propuesta de implementación. Base: `4a05f97`, 2026-09-13.
Aplican los [requisitos comunes](README.md). Responsable funcional: CPU SPK286.

## 1. Problema observado

`spk286_fetch` mantiene una petición activa y un registro de respuesta. Su
`request_ready` exige que no exista ni petición ni respuesta pendiente.
Cuando la cola acepta una respuesta, `response_valid` se borra en ese flanco,
pero la condición de lanzamiento sigue viendo el valor anterior. Esto deja
un hueco evitable antes de iniciar la siguiente lectura.

La CPU YA permite que el fetch trabaje mientras se ejecutan instrucciones.
P02 mejora el encadenamiento entre lecturas; no introduce desde cero ejecución
y fetch en paralelo. La cifra de cola vacía del programa A/B tampoco equivale
por sí sola a tiempo de ejecución bloqueada.

## 2. Alcance e interfaces

| Archivo actual | Responsabilidad |
| --- | --- |
| `vendor/spk286/rtl/spk286_fetch.sv` | Cursor, petición retenida, respuesta y cancelación |
| `vendor/spk286/rtl/spk286_prefetch_queue.sv` | FIFO de seis bytes y consumo |
| `vendor/spk286/rtl/spk286.sv` | Política de solicitud y conexiones |
| `vendor/spk286/rtl/spk286_biu.sv` | Propiedad del ciclo físico y prioridad de datos/INTA |
| `rtl/spk286_integration/spk286_machine_cpu.sv` | Adaptación del snapshot CPU a PCAT |

El cambio se prepara como mejora genérica de SPK286 y se importa con revisión
y procedencia identificables. Un prototipo local se documenta como divergencia
temporal; no se mantiene otra CPU completa. La lista activa del QIP es la
autoridad para compilar, incluidos los paquetes de modo protegido.

No se aumenta la cola arquitectónica de seis bytes, no se añaden múltiples
transacciones físicas simultáneas y no se altera la prioridad BIU por defecto.

## 3. Arquitectura propuesta por etapas

### 3.1 P02-A: consumir la respuesta y preparar la siguiente petición

P02-R01. Definir explícitamente el evento de entrega
`response_valid && response_ready`. Si no existe petición activa y la respuesta
se entrega en este flanco, se puede registrar la siguiente petición también
en ese flanco, si el solicitante la permite y no hay reset, redirect o suspensión.

P02-R02. Se usan cursor, base y límite del contexto vigente. En esta primera
etapa el cursor ya habrá avanzado al completar la lectura anterior. No se
recalcula sumando otra vez su longitud durante la entrega a la cola.

P02-R03. El significado de `request_ready` debe coincidir con la posibilidad
real de aceptar una solicitud en ese flanco. No anunciar readiness y luego
rechazar silenciosamente por una condición secuencial diferente.

| Evento | Referencia | P02-A |
| --- | --- | --- |
| Llega READY del bus | Guarda respuesta y avanza cursor | Igual |
| La cola acepta esa respuesta | Borra respuesta | Borra respuesta y puede preparar siguiente lectura |
| Flanco posterior | Puede preparar siguiente lectura | La siguiente lectura ya puede estar pendiente de BIU |

La ganancia objetivo es eliminar un hueco en esta frontera cuando existe
capacidad y demanda. No se promete un reloj menos en todos los fetches.

### 3.2 P02-B: aprovechar capacidad liberada por consumo simultáneo

P02-R04. Tras validar P02-A, se puede calcular la ocupación siguiente de la
cola teniendo en cuenta llenado y consumo del mismo flanco. Actualmente
`queue_count <= 4` y el cálculo de `fill_ready` son conservadores.

La decisión debe distinguir bytes ya almacenados, bytes de respuesta que se
entregan y espacio reservado para una petición en vuelo. El contador de FIFO
siempre queda entre 0 y 6; el registro de respuesta es almacenamiento de
transporte y no autoriza consumir más de seis bytes de cola.

P02-R05. La capacidad se obtiene de eventos efectivos, no de un `consume_ready`
sin datos válidos. No puede existir un lazo combinacional entre `fill_ready`,
solicitud, decode, fallo y `queue_consume_ready`.

La combinación de finalización de bus y relanzamiento en el mismo flanco queda
fuera de P02-A/B. Sólo se plantearía con una medición posterior y una revisión
separada del contrato BIU, porque implica más cambios de propiedad y cursor.

## 4. Reglas funcionales obligatorias

P02-R06. Una respuesta conserva datos, IP y longitud hasta su aceptación.
La nueva petición nunca sobrescribe una respuesta que la cola todavía rechaza.

P02-R07. A lo sumo hay una petición física activa. La BIU mantiene estable su
propietario ante READY bajo, aunque aparezcan operandos o interrupciones.
El fetch no puede robar un bus concedido a datos, INTA o HOLD.

P02-R08. Se mantiene la selección de lanes: una lectura impar o del último
byte del límite devuelve un byte; las demás elegibles devuelven dos. La FIFO
los recibe en orden de dirección ascendente, independientemente de D15:8/D7:0.

P02-R09. El cursor conserva su bit de desbordamiento: avanzar desde el final
de segmento no debe reiniciar accidentalmente en offset cero. No se cambia
la política existente de límite ni la semántica protegida por acelerar.

P02-R10. Reset y redirect tienen prioridad sobre entrega y relanzamiento.
Una lectura vieja aceptada se drena y su resultado no entra en la cola nueva.
Se conserva el ciclo necesario para que la nueva caché de CS esté disponible;
no se calcula la primera dirección con una base de segmento obsoleta.

P02-R11. La suspensión impide peticiones nuevas y respeta el drenaje de las
aceptadas. No se cancela o repite una transacción sólo por cambiar la política
de ejecución. Se conservan las reglas actuales de HLT, eventos y shutdown.

P02-R12. P02 no implementa coherencia de caché de memoria. La cola de CPU y un
futuro buffer SDRAM son objetos distintos. Una escritura no provoca un flush
extra de la cola sin evidencia arquitectónica que lo justifique.

## 5. Riesgos y pruebas

| ID | Estímulo | Propiedad comprobada |
| --- | --- | --- |
| P02-T01 | Flujo lineal, READY rápido, cola con sitio | Entrega y siguiente preparación coinciden |
| P02-T02 | READY aleatorio y prolongado | Payload estable, una petición física y una respuesta |
| P02-T03 | Cola llena y liberación de un byte | No overflow ni consumo de huecos |
| P02-T04 | Fill de uno/dos bytes y consumo simultáneo | Punteros y ocupación exactos, orden íntegro |
| P02-T05 | IP/dirección impares, límite en byte par/impar | BHE, longitud y cursor correctos |
| P02-T06 | Final de segmento y overflow | No lectura autorizada más allá del contrato |
| P02-T07 | Redirect en solicitud, READY y entrega | Cero bytes del contexto anterior tras flush |
| P02-T08 | Cambio de CS real/protegido y reset alto | Primera dirección calculada con base correcta |
| P02-T09 | Dato prioritario, LOCK, HOLD/HLDA e INTA | Respeta la propiedad y secuencia del BIU |
| P02-T10 | Saltos repetidos, RET/IRET y prefijos | Flujo decodificado y estado arquitectónico correctos |
| P02-T11 | Código automodificable con salto de sincronización | Se ejecuta la versión de código correspondiente |
| P02-T12 | Carga protegida rechazada/excepción | Acelerar no omite comprobaciones ni altera el fault |

El scoreboard de flujo debe etiquetar contextos de redirect y verificar bytes
consumidos por cada contexto. No se exige el mismo número de lecturas de código
especulativas en MAX si las diferencias son legales y canceladas correctamente.
Sí se compara el orden y número de efectos de datos e I/O del programa controlado.

## 6. Integración y verificación

Primero pruebas unitarias de fetch/FIFO; después lint Verilator y pruebas de BIU,
ejecución, eventos, segmentos y modo protegido afectadas. Ejecutar muestra
SingleStep y familias completas relevantes según las reglas de SPK286. Conservar
el inventario de limitaciones previo; un PASS de real mode no cubre PM.

En PCAT: programa A/B de memoria, first-fetch con las ROM disponibles, reset
de CPU con memoria pendiente, XT-IDE y regresión del perfil XT que comparte CPU.
Se puede usar una selección de elaboración para comparar P02 con la referencia;
no debe contaminar los encodings OSD ni duplicar semántica.

## 7. Métricas y aceptación

Registrar huecos desde entrega de respuesta hasta siguiente solicitud, tasa de
bytes útiles entregados, bytes descartados por redirect, ocupación de cola,
stalls reales por falta de código y ciclos por instrucción/clase. P04 define
cómo distinguir cola vacía de una dependencia que realmente detiene ejecución.

Criterios:

- P02-T01 demuestra el hueco eliminado bajo sus condiciones de elegibilidad.
- Todas las pruebas de flujo, eventos y límites pasan sin modificar expectativas
  arquitectónicas para acomodar la aceleración.
- Una carga limitada por fetch mejora y la suite mixta informa el efecto total;
  no basta reducir ciclos de un handshake que no afecta al programa.
- La comparación P01/P02/ambas evita sumar ganancias no independientes.
- No aparecen nuevos lazos combinacionales ni rutas no temporizadas; P05 evalúa
  el posible coste físico de calcular capacidad y dirección anticipadamente.
- Se registra snapshot CPU, cambio importado, evidencia y posibilidad de volver
  a la referencia, sin sustituir el core por uno con instrucciones especiales.

## 8. Entregables

Tests con scoreboard de flujo, mejora P02-A, medición de sus resultados y, sólo
si aporta beneficio, P02-B con su propio resultado. Informe final con regresión
CPU, integración AT/XT, STA y prueba DOS/CheckIt en la placa identificada.
