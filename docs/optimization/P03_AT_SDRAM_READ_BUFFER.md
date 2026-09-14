# P03 — Buffer coherente de lectura sobre la SDRAM AT

Estado: implementación experimental integrada, validada en simulación y
compilada en RBF; pendiente de validación en placa. Base: `1d6dbb1`,
2026-09-14. No es todavía un cierre de timing.
Aplican los [requisitos comunes](README.md). Responsable: memoria de PCAT.

## 1. Problema y objetivo

El propietario físico solicita a KFSDRAM `access_num = 1`. Cada palabra provoca
su propio acceso de fila y posterior precarga. KFSDRAM dispone de un contador
para varias palabras consecutivas, pero el propietario actual captura sólo una.

El objetivo es amortizar ese coste y responder a peticiones próximas desde un
pequeño buffer. Se propone comenzar con **una línea de 8 bytes, cuatro palabras**,
y evaluar 16 bytes como variante posterior. No se prescribe un ahorro porcentual.
Los saltos, la localidad de datos y el coste de llenar una línea fría pueden
hacer que una configuración grande sea peor.

## 2. Arquitectura inicial y alcance

Integrar el buffer en el propietario físico o en una capa inmediatamente
adyacente, por debajo del arbitraje común de CPU, DMA, refresco y loader. Debe
observar todas las escrituras que lleguen a esa memoria, no sólo las de CPU.
La implementación puede separarse en un módulo propio, propuesto
`spk286_at_sdram_read_buffer`, sin alterar el límite CPU/chipset.

| Elemento | Política de primera versión |
| --- | --- |
| Líneas | Una, sin asociatividad ni reemplazo complejo |
| Tamaño | 8 bytes, potencia de dos y alineación natural |
| Almacenamiento | Datos, tag físico canónico y valid; sin dirty |
| Asignación | Sólo por lecturas CPU de código en RAM/ROM elegibles |
| Lecturas de datos/DMA/loader | Bypass inicial |
| Escrituras | Siempre al backend, sin write-back ni aceptación anticipada |
| Miss | Llenado completo antes de responder a la CPU |
| Hit | Aceptación registrada y respuesta posterior; no respuesta combinacional |
| Reset global | Invalidación completa |

P03-R01. Separar elección de tamaño de cambios en el protocolo. La primera
versión no devuelve la palabra crítica antes de terminar la línea: facilita
demostrar orden y drenaje. La entrega temprana es una extensión medida, con
especificación de las operaciones que permanecen en vuelo.

P03-R02. No aumentar automáticamente la cola de seis bytes de SPK286. El buffer
es memoria de placa: sólo entrega bytes a la CPU cuando ésta los solicita.

### 2.1 Metadata y señales de integración

La capa DEBE recibir dirección, lanes, dirección de transferencia, datos,
clase, `code_fetch` y propietario como una sola petición retenida. El puerto
de memoria ya expone `backend_owner`; el owner físico actual sólo distingue
refresco. Propagar el identificador completo si el buffer se instala allí,
para distinguir CPU, DMA y loader en aceptación, invalidación y cancelación.

Añadir una entrada explícita de cancelación CPU y un evento de invalidación
de mapa cuando corresponda. Son interfaces propuestas. El reset CPU puede
invalidar globalmente los datos cacheados, pero sólo cancela la entrega de la
operación cuyo propietario sea CPU; no debe suprimir una finalización DMA/loader.
No reutilizar `request_code_fetch` como identificador universal de propietario.

El canal de respuesta conserva READY y read-data-valid. La aceptación de un
hit, el lanzamiento de un fill y su terminación física son eventos diferentes
con contadores independientes. El backend debe seguir pudiendo informar busy
hasta completar todo el trabajo aceptado, incluso ante cancelación lógica.

## 3. Contrato de direcciones y elegibilidad

P03-R03. Los tags usan dirección física canónica de byte. El desplazamiento
interno de KFSDRAM a palabras ocurre después; no se mezcla byte address con
word address al comparar o indexar la línea.

P03-R04. Canonicalizar el alias `FFF000–FFFFFF` hacia la copia BIOS
`0FF000–0FFFFF` de la misma forma que el mapper actual. Las escrituras del
loader sobre esa copia deben invalidar también los hits realizados por el alias.

P03-R05. A20 es una política del chipset. La integración actual expone
`a20_enable`, pero no debe presuponerse que ya exista un enmascaramiento completo
en la ruta CPU–SDRAM. Antes de implementar tags se documentará el mapa efectivo.
Si se añade o cambia A20/remapping, el buffer verá la dirección posterior al
mapper y/o invalidará al cambiar su generación. P03 no corrige A20 de forma
encubierta ni implementa la máscara en el core CPU.

P03-R06. Una línea se llena sólo si TODOS sus bytes pertenecen a memoria sin
efectos de lectura y con una traducción contigua. Se usa la clasificación
autoritaria; `word_capable` por sí solo no es un contrato de cacheabilidad.
Excluir EGA `A0000–BFFFF`, I/O, INTA, memoria no instalada y huecos del mapa.

Si una futura región no permite una línea completa, usar acceso simple. No
cruzar límites de fila/banco de SDRAM con una secuencia que el controlador no
soporte. Revalidar la clasificación al cambiar la configuración del mapa.

P03-R07. Leer bytes adicionales de RAM física no crea solicitudes CPU ni
comprobaciones de segmento adelantadas. La CPU conserva sus propias reglas de
límite y permiso; ningún dato del buffer se entrega sin una petición CPU válida.

## 4. Protocolo lógico y físico

| Estado conceptual | Responsabilidad |
| --- | --- |
| IDLE | Aceptar una petición y retener metadata; decidir hit/miss/bypass |
| HIT_RESPONSE | Devolver sólo la palabra/lanes solicitados |
| FILL_REQUEST | Lanzar secuencia física de cuatro palabras |
| FILL_WAIT | Capturar cada `read_flag` y sus datos, contar beats |
| FILL_RESPONSE | Publicar línea completa y respuesta solicitada |
| BYPASS_WAIT | Completar operación simple, incluida escritura |
| DRAIN | Terminar físicamente una operación cancelada sin responder al contexto viejo |

Los estados son conceptuales: pueden combinarse si se conservan los contratos.

P03-R08. Cada petición lógica tiene una aceptación y una respuesta. Los cuatro
beats físicos de un fill no son cuatro finalizaciones CPU. Sus direcciones y
datos deben validarse contra el modelo de pines, no sólo un array ideal.

P03-R09. Mantener estables los campos usados por KFSDRAM hasta que deje de
necesitarlos. No liberar el propietario porque la CPU ya no muestre VALID si
todavía existe una operación aceptada pendiente de terminar.

P03-R10. Una lectura hit también respeta propiedad y orden. No puede adelantar
una escritura aceptada, un drenaje o una operación bloqueada por LOCK. La
primera versión admite una única operación lógica pendiente.

P03-R11. Las lecturas dejan habilitadas ambas lanes físicas como en la base;
la respuesta selecciona las solicitadas. Las escrituras conservan DQM y la
conexión especial de máscaras a las placas SDRAM MiSTer compatibles.

## 5. Coherencia y reset

P03-R12. Una escritura física aceptada cuyo rango toque la línea invalida ésta
antes de que pueda servirse otro hit. Incluye escrituras de uno/dos bytes,
CPU, DMA y loader, y cualquier alias canónico. No se asigna línea en escritura.

P03-R13. El arbitraje único serializa fill y escritura. Si se permite observar
una invalidación externa durante un fill, usar un bit de invalidación pendiente
o generación para impedir que su finalización resucite datos obsoletos.

P03-R14. Una escritura ROM bloqueada por el chipset produce cero escrituras
físicas. Puede invalidar conservadoramente, pero no hacer modificable la ROM.

P03-R15. El reset global invalida. El reset CPU invalida de forma conservadora
el buffer y cancela respuestas CPU pendientes sin resetear loader/SDRAM.
Si la capa propuesta no observa `cancel_cpu`, añadir ese control explícito;
no deducir reset de una caída de VALID. Un fill ya aceptado se drena, y no se
publica válido después de invalidarlo. DMA/loader siguen su contrato de reset.

P03-R16. Código automodificable: invalidar el buffer de memoria no implica
vaciar la cola CPU ya prefetched. Se conserva la semántica del 286 que adopta
SPK286. Las pruebas distinguen escritura+salto, escritura sin salto y DMA;
no inventan una coherencia de instrucciones más fuerte para ocultar errores.

## 6. Refresco, arbitraje y límites de bloqueo

P03-R17. El llenado de línea tiene longitud finita. El árbitro no permitirá
inanición de DMA o refresco bajo demanda sostenida. Se medirá el bloqueo máximo
introducido por un fill frente a la palabra simple.

P03-R18. Conservar el refresco físico KFSDRAM y su mecanismo forzado. Los hits
de buffer no deben impedirlo cuando el controlador está libre. Las peticiones
de refresco AT y el refresco de retención SDRAM se contabilizan por separado.
No reducir la cadencia de refresco para obtener la ganancia de P03.

P03-R19. Verificar que `access_num=4` produce realmente cuatro muestras válidas
con el modelo y los parámetros actuales. Que el puerto tenga ese campo no
demuestra que su uso multibeat esté validado en esta integración.

## 7. Matriz de pruebas

| ID | Caso | Resultado exigido |
| --- | --- | --- |
| P03-T01 | Miss a cada palabra de una línea | Cuatro beats correctos y una respuesta solicitada |
| P03-T02 | Hits y lanes par/impar | Sin nuevos READ de SDRAM y mismos datos CPU |
| P03-T03 | Sustitución de línea | No mezcla tags/datos de líneas diferentes |
| P03-T04 | Límites mapa/fila/banco | Bypass o secuencia legal, nunca cruce no permitido |
| P03-T05 | EGA/I/O/INTA/unmapped | Ningún hit/fill ni efecto adicional |
| P03-T06 | Escrituras CPU de byte/palabra y readback | Invalida y devuelve datos actuales |
| P03-T07 | DMA/loader escriben línea/alias BIOS | CPU no observa una copia obsoleta |
| P03-T08 | Reset/invalidación durante cada beat | Drenaje sin respuesta vieja ni línea resucitada |
| P03-T09 | HOLD, LOCK y refresco | Propiedad única y bloqueo acotado |
| P03-T10 | Código automodificable y redirect | Semántica de cola preservada y memoria coherente |
| P03-T11 | Carga protegida de código y cambios CS | CPU mantiene límites, faults y flujo correcto |
| P03-T12 | Boot con las ROM disponibles | Alias de reset, carga HPS y primeras lecturas correctos |
| P03-T13 | Repetición prolongada con escrituras aleatorias | Cero divergencias contra memoria de referencia |

## 8. Métricas y aceptación

Añadir contadores de hits/misses, fills, palabras físicas, invalidaciones por
origen, ciclos de hit/miss, espera máxima de DMA/refresco y tráfico desperdiciado.
Separar estado frío y caliente; registrar latencia del primer acceso de arranque.

Comparar buffer desactivado, 8 bytes y, después, 16 bytes a igual reloj y con
las mismas opciones P01/P02. Incluir flujo lineal, bucles pequeños, saltos entre
líneas, datos aleatorios, stack, REP y tráfico DMA. No seleccionar el tamaño
sólo por CheckIt o sólo por un bucle que cabe exactamente en el buffer.

Aceptación: matriz completa sin divergencias; menos accesos físicos en hits;
ganancia neta en las cargas objetivo con penalización de misses publicada;
refresco y DMA dentro de sus presupuestos documentados; recursos y timing
admisibles según P05; boot, disco, teclado y software en placa correctos.

Una regresión importante en cargas frías requiere corregir la política o
mantener el buffer opcional, con decisión justificada. No se promete que cuatro
palabras cuesten lo mismo que una ni que el rendimiento se multiplique por cuatro.

## 9. Entregables y extensiones

Entregar diseño del mapper/tag, RTL del buffer y multibeat, scoreboard coherente,
pruebas de pines, medidas y manifiesto de build. Después pueden estudiarse
asignación por lecturas de datos, varias líneas o respuesta de palabra crítica.
Write-back, write posting y un controlador de fila abierta general quedan fuera
de esta primera propuesta y necesitan sus propios contratos de orden y reset.

## 10. Implementación experimental actual

La primera versión está integrada en el perfil AT mediante:

- `rtl/spk286_integration/spk286_at_sdram_read_buffer.sv`;
- `rtl/spk286_integration/spk286_at_mister_sdram_owner.sv`, usando
  `access_num=4` sólo durante un fill P03;
- `rtl/spk286_integration/spk286_at_emu.sv` y el QIP AT.

La política activa es una línea de 8 bytes, sólo para lecturas CPU marcadas como
fetch de código en RAM convencional, BIOS y RAM extendida elegible. EGA, I/O,
lecturas de datos, DMA, loader y escrituras hacen bypass. Las escrituras CPU,
DMA y loader que tocan la línea invalidan la copia; no hay write-back ni
respuesta especulativa.

La señal `cancel_cpu` sólo cancela operaciones cuyo propietario es la CPU. El
loader, DMA y refresco siguen pudiendo completar durante `at_machine_reset`,
porque la carga inicial de BIOS mantiene ese reset activo hasta que
`main_rom_loaded` se afirma. Esta condición está cubierta por la prueba del
loader durante cancelación CPU; evita mantener el vídeo en reset por una carga
de BIOS bloqueada.

La regresión reproducible es:

```text
bash scripts/test_at_sdram_read_buffer.sh
bash scripts/test_at_memory_perf.sh
```

Resultados sobre `tests/firmware/at_memory_perf.asm`, con puente x16 y el mismo
RBF lógico de simulación:

| Variante | Ciclos | Retiradas | Escrituras CPU | Escrituras SDRAM | Resultado |
| --- | ---: | ---: | ---: | ---: | --- |
| P02 sin P03 | 188037 | 4399 | 2821 | 2821 | referencia |
| P02 + P03 | 175460 | 4399 | 2821 | 2821 | 1,072×; -6,69 % |

El RBF AT_FAST corregido se generó con Quartus sin errores. La validación de
placa debe confirmar primero señal HDMI, carga de BIOS y arranque antes de
medir CheckIt.

El número de solicitudes de lectura observadas por la CPU cambia de 9434 a
9820 porque el timing del prefetch cambia legítimamente al entregar bytes desde
la línea; no se usa como criterio arquitectónico. La prueba unitaria confirma
hits sin nuevo acceso físico, fills de cuatro palabras, invalidación por CPU y
DMA, alias de BIOS compartido y bypass de la apertura EGA.

La mejora es una evidencia inicial de beneficio del burst físico, no una
promesa para CheckIt. Falta repetirla con ROM/OS reales, tráfico DMA y cargas
frías, y realizar la síntesis AT/AT_FAST con STA antes de instalarla como
versión estable.
