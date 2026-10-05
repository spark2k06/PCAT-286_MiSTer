# Plan de optimización de PCAT-286 AT

Current pending-only project register: [Remaining work](../REMAINING_WORK.md).
The dated proposal and fit records below retain their individual scope; a
historical "pending" label does not reopen a subsequently accepted story.

Estado: especificaciones de trabajo; P03 dispone de una implementación
experimental validada en simulación, todavía no cerrada en timing ni placa.
Fecha: 2026-09-13. Base funcional: commit `4a05f97`, rama
`codex/spk286-pm5-vendor-sync` de `PCAT-286_MiSTer`.

## 1. Objetivo y documentos

Experimento AT del 14/09/2026: referencia
[sin debug, seed 2](P05_NODEBUG_SEED2_SNAPSHOT.md) y candidato
[CDC de control y metadatos](P05_AT_CDC_EXPERIMENT.md).

Mejorar el rendimiento útil de SPK286 en la máquina AT, conservar la corrección
funcional y preparar perfiles de temporización verificables. El aumento de
frecuencia física no se fija como requisito ni se promete una puntuación final.

| ID | Especificación | Área responsable | Resultado esperado |
| --- | --- | --- | --- |
| P01 | [Latencia del puente de memoria](P01_AT_MEMORY_BRIDGE_LATENCY.md) | Integración PCAT | Quitar dos estados de espera en accesos de memoria elegibles |
| P02 | [Encadenamiento del fetch](P02_SPK286_FETCH_PIPELINING.md) | CPU SPK286 | Reducir huecos entre peticiones sin alterar el flujo de instrucciones |
| P03 | [Buffer de lectura SDRAM](P03_AT_SDRAM_READ_BUFFER.md) | Memoria PCAT | Amortizar activación y precarga mediante lecturas de varias palabras |
| P04 | Perfilado y optimización de ejecución; measured follow-up in [PERF01 attribution](P12_REAL_CHECKNUM_MEMORY_ATTRIBUTION_20261002.md) | Verificación y CPU | Separar costes de memoria/ejecución y elegir cambios medidos |
| P05 | [Cierre de timing FPGA](P05_AT_FPGA_TIMING_CLOSURE.md) | Integración, CPU y constraints | Cumplir los tiempos del diseño físico a la frecuencia declarada |
| P06 | [Perfiles de velocidad de CPU](P06_CPU_SPEED_PROFILES.md) | Política CPU e integración OSD | First P06/P12 functional version accepted: MAX / 6–25 MHz, integrated waits, main-menu selection and safe live changes; exact EU/native pin timing remains future precision work. Physical 50 MHz setup/hold closure continues separately with the [verified deadline/buffer/palette candidate](P06_DEADLINE_FOLD_20261005.md); full regression is user-deferred |
| P07 | [Camino EGA byte-preservado](P07_EGA_BYTE_PRESERVING_PATH.md) | Vídeo y frontend VRAM | Reducir latencia interna sólo cuando sea seguro, sin convertir EGA en un dispositivo de 16 bits |

P01–P04 corresponden a las cuatro mejoras iniciales. P03 tiene ya una primera
implementación experimental integrada en el perfil AT; su aceptación definitiva
queda condicionada a las pruebas de coherencia, síntesis y placa descritas en
su documento. P05 y P06 especifican las
dos condiciones transversales: viabilidad física y compatibilidad temporal. P07
es una optimización posterior y condicionada del camino de vídeo; no se activa
por defecto ni se considera parte de P01/P02.
Los nombres nuevos de módulos, parámetros, pruebas y artefactos que aparezcan
en estos documentos son contratos propuestos, no interfaces existentes.

## 2. Evidencia de partida

| Medida | Antes de x16 | Base x16 actual | 86Box, captura del usuario |
| --- | ---: | ---: | ---: |
| CheckIt Dhrystones | 1.586 | 2.368 | 4.143 |
| CheckIt Whetstones, sin NPU | 28,9K | 45,7K | 70,9K |
| MHz estimados por CheckIt | 34,60 | 34,80 | 25,00 |
| Ciclos del programa A/B RTL | 282.858 | 188.037 | No aplicable |

La prueba RTL retira 4.399 instrucciones en ambos modos; las iteraciones de REP
no se cuentan como instrucciones retiradas independientes. No es CheckIt.
Las lecturas CPU promedian 12,12 relojes del diseño y las escrituras 11,15 en
la variante x16. La captura de 86Box no identifica todos sus wait states,
modelo de placa o parámetros de memoria; no es una referencia ciclo exacta.

El AT utiliza `CLK_50M` y `execute_enable=1`. El informe AT_FAST disponible
indica 33,88 MHz de Fmax y -9,515 ns de setup para `FPGA_CLK2_50` en Slow
1100 mV/100 °C. Ni Fmax ni CheckIt cambian automáticamente ese reloj de 50 MHz.
La fecha del informe por sí sola no vincula una captura a un RBF: las próximas
pruebas DEBEN registrar sus hashes. Véase [investigación](../AT_MEMORY_THROUGHPUT.md).

## 3. Convenciones y límites comunes

- **DEBE**: condición de aceptación. **DEBERÍA**: opción preferida cuya desviación
  se documentará. **PUEDE**: alternativa permitida dentro del alcance indicado.
- Un valor observado se identifica como evidencia; un objetivo como objetivo;
  una hipótesis debe tener una prueba que permita refutarla.
- La prioridad es corrección, después rendimiento medido y viabilidad física.
- Una petición aceptada produce una única finalización o un drenaje cancelado
  explícito. Una escritura física aceptada no se deshace mediante reset.
- Se conservan READY, LOCK, HOLD/HLDA, INTA, máscaras de byte, arbitraje, refresco,
  protección de ROM, alias de reset y orden de efectos de los dispositivos.
- Las mejoras de MAX no autorizan acelerar PIT, RTC, vídeo, sonido o el reloj
  físico del protocolo de teclado. El chipset conserva sus bases de tiempo.
- Los cambios de CPU se diseñan como funciones reutilizables de SPK286. No se
  introducen direcciones de BIOS, puertos PCAT o dependencias HPS en la CPU.
- El QIP de producción determina las fuentes activas. Algunos documentos I5
  anteriores describen sustituciones de `operand` que ya no refleja el QIP PM5.
- Las modificaciones de CPU importada requieren trazabilidad del cambio y del
  snapshot. No se actualizará un manifiesto sólo para ocultar una divergencia.
- Estas especificaciones no modifican RTL, ROM, QSF, SDC ni selecciones OSD.

## 4. Orden de ejecución y dependencias

1. Conservar resultados, fuentes y artefactos de la base x16.
2. Ejecutar P01 con una comparación que sólo varíe su política de latencia.
3. Ejecutar P02 sobre una base identificada; comparar también P01+P02.
4. La instrumentación de P04 puede comenzar desde el primer paso. Sus medidas
   orientarán el tamaño de buffer P03 y las futuras optimizaciones de ejecución.
5. Implementar P03 primero como buffer pequeño de lecturas de código; ampliar
   su cobertura sólo después de validar coherencia y medir el beneficio.
6. P05 se aplica a cada candidato físico y antes de declarar una versión estable.
7. P06 consume la capacidad medida por P04 y el reloj validado por P05.
8. P07 sólo se estudia después de disponer de una traza de accesos EGA y de
   rutas STA que justifiquen que el frontend de vídeo es relevante.

No se sumarán porcentajes de mejoras aisladas: dos optimizaciones pueden actuar
sobre los mismos ciclos. La integración requiere una nueva medida conjunta.
Cada cambio DEBERÍA ser reversible mediante selección de elaboración o una
referencia versionada, sin duplicar la implementación funcional de la CPU.

## 5. Protocolo común de validación

### 5.1 Simulación

Registrar commit, diff, simulador/versión, lista de fuentes/QIP, ROM y SHA-256,
semilla, frecuencia, opciones, política de memoria y resultado funcional.
Usar la misma carga y memoria inicial para A/B. Separar arranque/carga de ROM
de la ventana medida. Una semilla fija ofrece reproducción; varias semillas
documentadas cubren posiciones diferentes de READY, reset y contención.

Comparar registros, FLAGS definidos, memoria, excepciones y efectos de I/O.
Las pruebas equivalentes inyectarán eventos en límites arquitectónicos
comparables. Con interrupciones en tiempo real fijo, el punto de interrupción
puede cambiar legítimamente al acelerar: verificar semántica y servicio, no
exigir una traza final idéntica sin controlar la entrada externa.

Las observaciones `bus_busy` y `queue_empty` se solapan. No se suman ni se
presentan como porcentajes de stall hasta disponer del clasificador P04.

### 5.2 FPGA y placa

Guardar QSF, SDC, versión Quartus, seed, recursos, relojes reales, reports STA
y hash del RBF. Usar configuración BIOS/VHD/OSD comparable; registrar hashes
de ROM y VHD o de su imagen base. No publicar ni versionar imágenes del usuario
como parte de la prueba.

Repetir CheckIt al menos tres veces por configuración, indicar valores y
mediana, y no seleccionar sólo el mejor resultado. Registrar boot DOS, teclado,
XT-IDE y una carga representativa adicional. Preservar una imagen base de prueba
para evitar que escrituras del invitado alteren la comparación.

### 5.3 Aceptación común

Una propuesta termina con evidencia separada de: funcionalidad, rendimiento,
síntesis/timing y placa. Un PASS de simulación no cierra P05; una captura CheckIt
no prueba modo protegido completo ni perfiles ciclo exactos. Las limitaciones
previas se mantienen identificadas, sin convertir errores nuevos en excepciones.

## 6. Comandos existentes de referencia

Desde la raíz del repositorio, en el entorno Linux de simulación:

```sh
bash scripts/test_a1_at_bridge.sh
bash scripts/test_a2_memory_arbiter.sh
bash scripts/test_at_mister_memory_port.sh
bash scripts/test_at_mister_sdram_owner.sh
bash scripts/test_at_memory_perf.sh
bash scripts/test_at_sdram_read_buffer.sh
bash scripts/test_at_profile_elab.sh
bash scripts/test_at_bios_first_fetch.sh
bash scripts/test_at_xtide_machine.sh
bash scripts/test_a4_dma_refresh_pit.sh
```

Cada especificación selecciona los aplicables y define pruebas adicionales.
Algunas pruebas de BIOS usan ROM opcionales: su ausencia se informa como no
ejecutado, nunca como validación de esa BIOS. Un harness histórico que no
elabore con PM5 se corrige conservando su intención antes de usarlo de evidencia.

## 7. Referencias de arquitectura

- [Contrato AT CPU/chipset](../AT_BUS_CPU_CHIPSET_SPEC.md).
- [Reset CPU y memoria retenida](../AT_CPU_RESET_MEMORY_BOUNDARY.md).
- [Auditoría histórica de timing](../AT_INDEPENDENT_TIMING_AUDIT.md), cuyos
  valores corresponden a otro fit y no sustituyen las medidas actuales.
- [Modelo temporal SPK286](../../vendor/spk286/SPK286_TIMING_MODEL.md).
- [Procedencia](../SOURCE_PROVENANCE.md) y
  [QIP realmente compilado](../../rtl/spk286_integration/spk286_integration.qip).
