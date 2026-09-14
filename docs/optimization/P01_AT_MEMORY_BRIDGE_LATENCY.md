# P01 — Reducción de latencia del puente de memoria AT

Estado: propuesta de implementación. Base: `4a05f97`, 2026-09-13.
Aplican los [requisitos comunes](README.md). Responsable: integración PCAT.

## 1. Problema y objetivo

El puente captura dirección, datos, clase, ancho y LOCK en `STATE_IDLE`, pero
atraviesa después `STATE_SNAPSHOT` y `STATE_DECODE`, que sólo cambian de estado.
Todavía no exponen `at_valid`. Cada petición paga dos relojes adicionales antes
de solicitar el recurso de memoria, aunque la ruta funcional ya conoce sus datos.

El objetivo es omitir ambos estados para memoria elegible, conservando captura,
arbitraje y fases de aceptación/finalización. No se atribuirá a esos dos relojes
la totalidad de los aproximadamente 12,12 relojes medios de lectura actuales.

## 2. Archivos y límites

| Archivo actual | Papel |
| --- | --- |
| `rtl/spk286_integration/spk286_at_bus_bridge.sv` | Captura y máquina de estados que se optimiza |
| `rtl/spk286_integration/spk286_at_memory_decode.sv` | Clasificación autoritativa `word_capable` |
| `rtl/spk286_integration/spk286_at_machine.sv` | Conexión, grants y protección ROM |
| `rtl/spk286_integration/spk286_at_mister_memory_port.sv` | Selección retenida del propietario |
| `sim/spk286_integration/spk286_at_bus_bridge_tb.sv` | Pruebas unitarias actuales |

No se modifica SPK286, KFSDRAM, el mapa de memoria o la duración de las fases
de I/O, EGA, INTA y memoria no asignada. No se elimina el estado ADDRESS:
permite que el árbitro y el puerto capturen la petición antes de COMMAND.

## 3. Selección de ruta

P01-R01. Introducir una selección de elaboración, nombre propuesto
`FAST_MEMORY_START`, cuyo valor desactivado reproduzca la secuencia actual.
La opción no necesita un bit OSD. El valor de producción se habilita al pasar
los criterios de aceptación; XT mantiene su perfil de integración.

P01-R02. La elegibilidad se decide únicamente en la captura inicial:
petición válida, clase `5`, `6` o `D`, y `cpu_memory_word_capable` activo.
No se condiciona al opcode, CS/IP, contenido de la ROM o valor de los datos.

P01-R03. La clasificación de ancho identifica el tipo de destino. Un byte o
un acceso impar a RAM también puede acelerar su inicio; no se convierte por ello
en palabra alineada. `request_native_word_q` conserva su cálculo independiente.

P01-R04. Las escrituras sobre ROM siguen bloqueadas por la máquina. Acelerar
su llegada al receptor de escrituras descartadas nunca autoriza tocar SDRAM.

## 4. Secuencia temporal propuesta

| Caso | Secuencia de estados |
| --- | --- |
| Referencia y destinos no elegibles | IDLE → SNAPSHOT → DECODE → ADDRESS → COMMAND → WAIT → COMPLETE → IDLE |
| Memoria elegible con P01 activo | IDLE → ADDRESS → COMMAND → WAIT → COMPLETE → IDLE |
| Petición inválida | Política actual de error y COMPLETE, sin aceptación de backend |
| Segundo byte de palabra serializada | Secuencia ADDRESS → COMMAND → WAIT actual |

En el flanco de captura se registran todos los campos, y sólo después del
flanco pueden observarse `at_valid` y ADDRESS. No se crea una ruta combinacional
directa desde las entradas CPU a comandos SDRAM. El adelanto esperado de
ADDRESS es exactamente dos relojes frente a la referencia para la misma
petición presentada en IDLE; con contención, la finalización puede mejorar menos.

## 5. Invariantes del protocolo

P01-R05. La aceptación sigue exigiendo COMMAND y `at_accept`. READY alto antes
de aceptar no completa la operación. Una lectura necesita datos válidos.

P01-R06. Dirección, datos, byte enables, clase y LOCK permanecen estables desde
la captura hasta la finalización; cambios posteriores de entradas CPU no influyen.

P01-R07. Una petición repetida idéntica es una nueva operación si el protocolo
la presenta como tal. No se deducen límites por cambio de dirección o datos.

P01-R08. LOCK conserva su duración y exclusión de otros propietarios durante
la operación. No se concede DMA antes de la liberación permitida por HOLD/HLDA.

P01-R09. El reset CPU cancela una petición no aceptada; las aceptadas se drenan
en el puerto de memoria sin entregar respuestas al nuevo contexto. No se
reinicia la SDRAM ni se interrumpe el cargador HPS por esta optimización.

P01-R10. La llegada más temprana puede cambiar qué petición gana ante una
contención real. Se conserva la política del árbitro, no una coincidencia
accidental del reloj absoluto en que la referencia obtenía el grant.

## 6. Pruebas dirigidas

Cada prueba ejecuta la referencia y P01, con scoreboard de aceptación,
finalización y efectos, además de los siguientes estímulos:

| ID | Caso | Comprobación |
| --- | --- | --- |
| P01-T01 | Lectura/escritura RAM x16 | ADDRESS se adelanta dos relojes; datos y lanes idénticos |
| P01-T02 | Byte par/impar y palabra impar | No se pierde, duplica ni intercambia ningún byte |
| P01-T03 | Fetch de `FFFFF0` y ROM normal | Mismo alias, vector y datos que la referencia |
| P01-T04 | Escritura ROM/option ROM | Cero escrituras físicas y finalización sin bloqueo |
| P01-T05 | EGA, IN/OUT e INTA | Secuencia del puente sin variación con el mismo backend |
| P01-T06 | READY prematuro, tardío y sostenido | No hay aceptación ficticia ni doble finalización |
| P01-T07 | Datos válidos posteriores a READY | La lectura espera al contrato completo |
| P01-T08 | Payload cambia tras captura | Sólo se utiliza la copia retenida |
| P01-T09 | Peticiones iguales consecutivas | Una operación por petición real |
| P01-T10 | Reset en cada estado y en aceptación | Cancelación/drenaje correctos, nuevo reset vector limpio |
| P01-T11 | CPU, DMA, refresco y LOCK | Propietario único, servicio finito bajo demanda finita |
| P01-T12 | Clases/líneas inválidas | Error determinista y ningún comando físico espurio |

Añadir una prueba integrada con el puerto y KFSDRAM reales. No basta un backend
que conceda todo inmediatamente: debe incluir busy de SDRAM y refresco físico.
Reutilizar las suites A1, A2, memory port, XT-IDE, A4, first-fetch y AT profile.

## 7. Medidas de rendimiento

Extender el harness A/B existente para seleccionar P01 independientemente de
la transferencia x16. La base comparada DEBE ser x16 activado en ambos lados.
Registrar ciclos de inicio, aceptación y respuesta por clase y destino;
informar media y máximo, no sólo tiempo total.

Las cuatro cargas del programa `at_memory_perf.asm` conservan sus resultados.
Registrar lecturas/escrituras, instrucciones y efectos. Una variación de fetch
especulativo por distinto solapamiento se investiga; no se exige una igualdad
ciega que impida una ejecución legal, ni se elimina la verificación de trabajo.

El ahorro agregado no se calcula restando dos por petición sin simular: parte
puede quedar oculta tras otra dependencia o una espera de SDRAM.

## 8. Criterios de aceptación

- P01-T01 a T12 pasan, con Icarus y Verilator donde el harness lo permita.
- El adelanto unitario de ADDRESS es de dos relojes en peticiones elegibles;
  no se alarga ninguna secuencia aislada no elegible.
- El programa A/B real tarda menos que la base x16 con idéntico trabajo útil.
- Boot DOS, teclado, disco y CheckIt siguen funcionando en AT_FAST.
- Se entrega informe STA comparativo; cualquier regresión temporal se trata
  según P05, aunque la simulación sea más rápida.
- La selección de referencia permite reproducir el resultado anterior.

## 9. Entregables y orden de implementación

1. Test de secuencia temporal y parámetro de referencia.
2. Cambio mínimo en el destino del estado de captura y propagación del parámetro.
3. Regresiones integradas, medidas A/B y tabla de resultados.
4. Candidato físico identificado por hash y validación en placa.

Riesgo principal: que un consumidor dependa implícitamente de los dos estados
no visibles. Debe demostrarlo una prueba de protocolo; no se compensará con una
espera global que vuelva a introducirlos sin explicar la dependencia.
