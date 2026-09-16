# Landmark 5170: SKIP_PM V2 y checksums por ROM

12 de septiembre de 2026. Hardware anterior confirmado: commit `0f915cd`.

## Estado y causa del bloqueo

La captura del usuario confirma **16K CRITICAL MEMORY REGION PASSED** y
**MEMORY REFRESH PASSED** en el AT. Esto valida físicamente la corrección de
máscaras SDRAM de la entrega anterior. El siguiente encabezado queda en
**PROTECTED MODE CPU**; tanto la ROM original como la V1 llegan a ese test.

La V1 sólo cambiaba F000:94D8 -> 971A. Esa entrada pertenece al bloque posterior
de memoria en modo protegido. El primer test de CPU usa otra ruta:

```text
8E62: configurar pila RAM
8E6D: imprimir PROTECTED MODE CPU
8E70: JMP A3B3                 <-- V1 no modificaba este salto
A3B3: preparar estado CMOS; pruebas de tablas de descriptores
A418: CALL A571
A596: LMSW AX con PE=1
A599: salto a CS=0018
```

El bloque posterior entra en 94D8, activa PE en 94F6 y examina memoria mediante
descriptores, incluyendo su prueba de refresco lento. El salto de V1 a 971A
escribía CMOS shutdown=3 y solicitaba reset para continuar en 972D. No podía
resolver el bloqueo anterior en PROTECTED MODE CPU. La simulación con V1
confirma admisión de una instrucción real en A3B3, no sólo prefetch.

No se ha deducido de la foto el IP exacto de detención dentro del test original.
Sí queda comprobado que el parche previo no omitía ese test, y que requiere
funciones de modo protegido que el proyecto aún no pretende certificar.

## ROM de esta entrega

`SW/ROMs/test/Supersoft_Landmark_1.2.0_AT_5170_SKIP_PM_V2_64K.BIN`

SHA-256:
`46E99247C58766B162413E34480B63490AA8F610702D8AA1E98E15B2D921DEC6`

Tiene 65.536 bytes y dos mitades idénticas. La original y la V1 permanecen
con sus contenidos anteriores. El script genera V2 exclusivamente a partir
de la ROM original con SHA-256
`A8310F83DE0F3E6B71E4A3FF82A01FFE3C3B5A957677AED2FAD17B96BCE2E577`.

| Entrada | Acción V2 | Continuación original |
|---|---|---|
| 8E70, PROTECTED MODE CPU | JMP B100: pila 0000:0800, estado SKIPPED | 8E8F: limpiar CMOS shutdown; siguiente test U114 8259 |
| 94D8, memoria mediante modo protegido | JMP B120: pila 0000:0800, estado SKIPPED | 972D: SYSTEM BIOS |

Los stubs llaman a 9CC0, el renderizador común de estado, con el texto
**SKIPPED**. No llaman a la entrada que selecciona PASSED, no incrementan
contadores de errores y no activan PE ni solicitan reset. El bloque de memoria
que se omite incluye la prueba de refresco lento bajo modo protegido; no debe
confundirse con MEMORY REFRESH en modo real, que el hardware ya ha pasado.

Las entradas y los stubs se duplican en ambas mitades. Se usan únicamente
cavidades comprobadas como cero, B100..B114, B120..B134 y B160..B167, más sus
espejos inferiores. B0F0/B0F1 y sus espejos compensan los checksums.
El vector `EA 65 80 00 F0` se conserva. Las instrucciones de RAM de 16K,
MEMORY REFRESH, los checksums y el resto de diagnósticos permanecen idénticas.
El listado completo de 108 bytes distintos está en el manifiesto de evidencia.

## Checksums corregidos

La V1 conservaba la suma global de 64 KiB, pero esa condición no coincide con
las dos pruebas originales. En 89D4 y 89FF, Landmark lee F800:0000/0001,
acumula 0x4000 bytes y avanza de dos en dos: U27 (pares) y U47 (impares).

| ROM | Suma superior par | Suma superior impar |
|---|---|---|
| Original | 00 | 00 |
| SKIP_PM V1 | 29 | D7 |
| SKIP_PM V2 | 00 | 00 |

29+D7 se cancela módulo 256, pero ambos chips fallan individualmente.
V2 compensa cada lane por separado y conserva las mismas compensaciones en
la mitad inferior. Los cuatro residuos (dos mitades por dos lanes) son cero.
No se omite ni se fuerza el resultado de ninguna rutina de checksum.

## Validación y límites

`test_at_landmark_pm_skip.sh` usa el CPU SPK286, el bridge AT, la carga HPS,
KFSDRAM y el modelo de pines con el cableado MiSTer real:

- Caso 16: entrada original 8E62, impresión de SKIPPED confirmada en escrituras
  completadas a vídeo mono y color; continuación en 8EA8, PE=0 y sin reset.
  PASS en 6.513.629 ciclos.
- Caso 17: entrada 94CD con la pila RAM que deja el POST; mismo texto en ambos
  espacios de vídeo; continuación de SYSTEM BIOS en 973E, PE=0 y sin reset.
  PASS en 6.505.186 ciclos.
- Caso 18: ambas rutinas originales de checksum alcanzan sus salidas PASSED
  con el contexto de U27 y U47 correcto. PASS en 16.360.999 ciclos.

Para seleccionar la entrada, el testbench cambia únicamente su buffer privado
de ROM. En el caso 18 neutraliza **sólo el delta de checksum introducido por esa
selección**, preservando los residuos del archivo cargado. No convierte una
ROM defectuosa en una válida. Los controles negativos lo comprueban:

- V1, caso 16: detectada la entrada no omitida en A3B3.
- V1, caso 18: las rutinas de checksum siguen fallando.
- Copia V2 con un bit cambiado en la lane impar: checksum rechazado.

El chequeo independiente Python verifica el conjunto permitido de cambios,
las dos mitades, las lanes, el vector y los destinos reales de CALL/JMP.
El generador se ejecutó dos veces y produjo exactamente el mismo SHA-256.
La V2 sin redirigir su vector también pasa la carga HPS y sus primeros 32
fetches de instrucción, con 16 respuestas CPU verificadas.

Se trata de pruebas de las entradas y continuaciones relevantes, no de un
PASS simulado de todo el POST desde reset. La validación física de V2 y los
resultados de los diagnósticos posteriores quedan para la siguiente prueba.
No hay cambios RTL ni un nuevo fit/RBF en esta entrega.

## Reproducción

Generación en PowerShell, desde la raíz del repositorio:

```powershell
./scripts/patch_supersoft_landmark_skip_pm.ps1
```

Validación en WSL/Bash:

```bash
python3 scripts/test_supersoft_landmark_patch.py \
  SW/ROMs/test/Supersoft_Landmark_1.2.0_AT_5170_64K.BIN \
  SW/ROMs/test/Supersoft_Landmark_1.2.0_AT_5170_SKIP_PM_V2_64K.BIN
bash scripts/test_at_landmark_pm_skip.sh
```

Los casos se seleccionan con `AT_LANDMARK_CASES`, y el archivo con
`AT_SYSTEM_ROM`. Elegir V1 y el caso 16 o 18 debe producir los fallos de control
anteriores. El RBF del usuario sólo se identificó por su hash en disco; no se
leyó directamente la FPGA ni se compiló de nuevo.

## Prueba en MiSTer

1. Mantener el RBF que acaba de pasar 16K y MEMORY REFRESH. **No hace falta sintetizar.**
2. Cargar como BIOS la nueva `...SKIP_PM_V2_64K.BIN` y hacer reset completo del core.
3. Comprobar que U27 y U47 muestran PASSED, y que 16K y MEMORY REFRESH siguen pasando.
4. PROTECTED MODE CPU debe mostrar **SKIPPED** y continuar con U114 8259.
5. Si se alcanza el bloque posterior de memoria mediante modo protegido,
   también mostrará SKIPPED y continuará con SYSTEM BIOS. Estos tests omitidos
   no certifican modo protegido ni memoria extendida.
6. Enviar una captura del siguiente resultado o punto de detención.
