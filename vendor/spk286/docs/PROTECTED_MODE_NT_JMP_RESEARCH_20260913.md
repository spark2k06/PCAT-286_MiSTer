# Investigación: semántica de `NT` en cambios de tarea mediante `JMP`

**Fecha:** 2026-09-13  
**Ámbito:** Intel 80286, cambios de tarea protegidos, `JMP` frente a `CALL`/`INT`/`IRET`  
**Estado:** investigación documental y de implementaciones; no constituye cierre mediante prueba física del 80286.

## Resumen ejecutivo

La evidencia documental más directa para una implementación estricta del 80286 indica que el bit `NT` de la tarea entrante se borra cuando el cambio de tarea lo provoca un `JMP`.

La discrepancia aparece porque el procedimiento general de cambio de tarea y el pseudocódigo `SWITCH_TASKS` describen que `NT` se establece cuando existe anidamiento, pero no expresan con la misma claridad el borrado específico de `JMP`. Además, Bochs conserva `NT` para `JMP` y afirma haber comprobado ese comportamiento en 386, 486 y Pentium.

La política vigente en SPK286 —borrar `NT` en la ruta `JMP`— se conserva provisionalmente porque:

1. está escrita explícitamente en la tabla 8-2 de varias ediciones del manual Intel del 80286;
2. coincide con PCem y 86Box;
3. coincide también con la tabla de task linking del 80386;
4. la evidencia contraria de Bochs procede de generaciones posteriores y no de una medición pública del 80286 original.

## 1. Evidencia primaria Intel

### 1.1 Tabla 8-2 del 80286

Las ediciones Intel de 1983, 1985 y 1987 muestran la misma tabla de efectos sobre `BUSY`, `NT` y el enlace anterior:

| Campo de la tarea entrante | `JMP` | `CALL` / `INT` | `IRET` |
|---|---|---|---|
| `NT` | Cleared | Set | Unchanged |

Fuentes:

- [iAPX 286 Programmer's Reference, 1983](https://kib.kiev.ua/x86docs/Intel/486/210498-001_1983_iAPX_286_Programmers_Reference_1983.pdf)
- [iAPX 286 Programmer's Reference, 1985](https://www.bitsavers.org/components/intel/80286/210498-003_iAPX_286_Programmers_Reference_1985.pdf)
- [80286 and 80287 Programmer's Reference, 1987](https://bitsavers.org/components/intel/80286/210498-005_80286_and_80287_Programmers_Reference_Manual_1987.pdf)

La misma tabla también aparece transcrita en [Intel 80287 Manual, sección de task switching](https://kitchen.manualsonline.com/manuals/mfg/intel/80287.html?p=157).

### 1.2 Texto procedimental y origen de la ambigüedad

La descripción general del cambio de tarea dice, en esencia, que si hay anidamiento se establece `NT` en la nueva tarea. El pseudocódigo no siempre hace explícita la operación complementaria de borrar `NT` para `JMP`.

La guía de sistemas operativos de Intel de 1983 describe de forma explícita que `CALL` e `INT` establecen `NT` y el backlink, sin detallar con la misma precisión el borrado provocado por `JMP`:

- [iAPX 286 Operating Systems Writer's Guide, 1983](https://www.bitsavers.org/components/intel/80286/121960-001_iAPX_286_Operating_Systems_Writers_Guide_1983.pdf)

Por tanto, el conflicto no es entre una tabla y una frase que diga literalmente “`JMP` conserva `NT`”, sino entre la tabla explícita y una descripción procedimental incompleta o ambigua.

### 1.3 Comparación con el 80386

La documentación pública del 80386 conserva la interpretación de que el `NT` de la tarea entrante se borra en un cambio provocado por `JMP`:

- [80386 Programmer's Reference Manual, sección 7.6](https://pdos.csail.mit.edu/6.828/2011/readings/i386/s07_06.htm)

Esto refuerza la política de `NT=0` para `JMP`, aunque no sustituye una medición específica del silicio 80286.

## 2. Implementaciones de emuladores

### 2.1 PCem

PCem separa la carga común de la tarea de la semántica de la operación:

```c
new_flags = readmemw(base, 0x10);
if (optype == OPTYPE_INT || optype == CALL)
    new_flags |= NT_FLAG;
```

En la ruta de task gate ejecutada como `JMP`, limpia posteriormente `NT`:

```c
optype = JMP;
taskswitch286(...);
cpu_state.flags &= ~NT_FLAG;
```

Fuente: [PCem, `src/cpu/x86seg.c`](https://raw.githubusercontent.com/sarah-walker-pcem/pcem/dev/src/cpu/x86seg.c).

Resultado funcional: `JMP` termina con `NT=0`; `CALL` e `INT` terminan con `NT=1`.

### 2.2 86Box

86Box utiliza la misma estructura. La rutina común carga los flags del TSS y solo añade `NT` para `CALL` o `INT`. La ruta de task gate con `JMP` limpia después el bit:

```c
optype = JMP;
op_taskswitch286(...);
cpu_state.flags &= ~NT_FLAG;
```

Fuente: [86Box, `src/cpu/x86seg.c`](https://raw.githubusercontent.com/86Box/86Box/9445945f605ff18accc56f7204dea9ec79e15e65/src/cpu/x86seg.c).

PCem y 86Box no deben interpretarse como dos pruebas físicas independientes, pero sí son dos referencias de emulación relevantes y convergen con la tabla 8-2 del 80286.

### 2.3 Bochs

Bochs adopta la interpretación opuesta para el `NT` entrante:

```text
new NT flag   No change   Set   No change
              jump        call  iret
```

El código solo fuerza `NT` para `CALL`/`INT`; para `JMP` deja el valor cargado desde el TSS. El propio código incluye esta nota:

> I checked 386, 486, and Pentium, and they all exhibited exactly the same behaviour as above. There seems to be some misprints in the Intel docs.

Fuente: [Bochs, `bochs/cpu/tasking.cc`](https://raw.githubusercontent.com/bochs-emu/Bochs/master/bochs/cpu/tasking.cc).

Esta es una evidencia relevante, pero no resuelve por sí sola el comportamiento del 80286: la comprobación declarada se hizo en 386, 486 y Pentium.

### 2.4 PCjs y otras implementaciones

PCjs también conserva el valor de `NT` restaurado desde el TSS salvo en las rutas que crean anidamiento:

- [PCjs, `segx86.js`](https://github.com/jeffpar/pcjs/blob/master/machines/pcx86/modules/v2/segx86.js)

DOSBox-X no sirve como referencia para este caso concreto: su ruta de cambio de tarea 286 no está implementada como una ejecución completa del task switch 286.

## 3. Evidencia física y pruebas públicas

El proyecto [SingleStepTests/80286](https://github.com/SingleStepTests/80286) genera pruebas a partir de un Harris N80C286 real y contiene aproximadamente 1,5 millones de ejecuciones de modo real. Sin embargo, el propio README indica que las pruebas de modo protegido todavía no están disponibles porque es necesario generar tablas de descriptores válidas para evitar fallos inmediatos.

La limitación se confirma en:

- [Debate de VOGONS sobre la suite 80286](https://www.vogons.org/viewtopic.php?t=107481)
- [Debate de EmuDev sobre las pruebas 80286](https://www.reddit.com/r/EmuDev/comments/1m5ndt5/an_emulator_test_suite_for_the_80286/)

Por tanto, no se ha encontrado una prueba pública de un 80286 físico que mida directamente este caso:

1. preparar un TSS entrante con `NT=1`;
2. ejecutar un `JMP` al TSS o a un task gate;
3. ejecutar `PUSHF`/`POP AX` en la nueva tarea;
4. observar el bit 14 de los flags.

La suite hardware disponible es una base excelente para futuras pruebas, pero actualmente no cierra esta cuestión del modo protegido.

## 4. Evaluación de la evidencia

| Fuente | Resultado para `NT` tras `JMP` | Peso para un 80286 |
|---|---:|---:|
| Manual Intel 80286, tabla 8-2 | Borra | Muy alto |
| Manual Intel 80286, texto procedimental | Ambiguo | Alto, pero incompleto |
| Guía Intel de sistemas operativos | Solo explicita `CALL`/`INT` | Alto, pero incompleto |
| Manual Intel 80386 | Borra | Medio; generación posterior |
| PCem | Borra | Medio; implementación de emulador |
| 86Box | Borra | Medio; implementación de emulador |
| Bochs | Conserva | Alto para 386+, incierto para 286 |
| PCjs | Conserva | Bajo/medio; implementación de emulador |
| SingleStepTests/80286 | Sin cobertura PM relevante aún | No concluyente |

## 5. Decisión actual para SPK286

Para fidelidad documental estricta, la tabla 8-2 y 86Box/PCem siguen
describiendo:

```text
task switch via JMP  -> incoming NT = 0
task switch via CALL -> incoming NT = 1
task switch via INT  -> incoming NT = 1
IRET                  -> incoming NT restored from TSS
```

Sin embargo, el objetivo operativo de SPK286 incluye ejecutar la secuencia
original de Supersoft/Landmark. Por ello, la política implementada se ha cambiado
deliberadamente a:

```text
task switch via JMP  -> incoming NT preserved from target TSS
task switch via CALL -> incoming NT = 1
task switch via INT  -> incoming NT = 1
IRET                  -> incoming NT restored from TSS
```

La evidencia que motiva esta elección es reproducible: la imagen PMROM de la
prueba falla en el IRET final cuando `JMP` fuerza `NT=0`, y pasa completamente
cuando conserva `NT`; Bochs y PCjs siguen la segunda interpretación. Esto es una
decisión de compatibilidad con la ROM, no una afirmación de que la tabla Intel
sea errónea. La divergencia queda explícita para poder revisarla si aparece
evidencia física específica del 80286.

## 6. Prueba definitiva recomendada

Para cerrar la cuestión experimentalmente en un 80286 real, habría que construir una prueba protegida mínima con dos TSS:

1. cargar un TSS inicial y un TSS destino cuyo campo `FLAGS` tenga `NT=1`;
2. ejecutar un `JMP` al TSS destino;
3. en la tarea destino ejecutar `PUSHF` y `POP AX`;
4. almacenar `AX` en una dirección de memoria observable;
5. evitar `IRET`, para que el propio valor de `NT` no altere la ruta de retorno;
6. repetirlo con `NT=0` y mediante `CALL`/`INT` como controles.

El resultado de esa prueba debería contrastarse con el comportamiento de SPK286, PCem, 86Box y Bochs, manteniendo separados el resultado funcional y el timing histórico.

## Estado del repositorio

Esta investigación conserva las referencias y la discrepancia documental. La
RTL actual aplica la política de compatibilidad indicada arriba y está cubierta
por la prueba focalizada del servicio TSS y por `PMROM.BIN`.
