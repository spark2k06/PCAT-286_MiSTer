# AT: corrección de máscaras SDRAM para el test de 16K

> Confirmación posterior del usuario: **16K CRITICAL y MEMORY REFRESH PASSED**
> en hardware. El siguiente bloqueo es PROTECTED MODE CPU. Ver
> [AT_LANDMARK_SKIP_PM_V2.md](AT_LANDMARK_SKIP_PM_V2.md) para la nueva ROM,
> sus checksums y la prueba siguiente con el mismo RBF.

Fecha: 12 de septiembre de 2026. Base anterior: `c581864`.

## Diagnóstico y alcance

Las cuatro páginas de Landmark RAM Trace permiten identificar una escritura
por byte que no preserva el otro byte de la palabra física. El propietario AT
calculaba correctamente BE y las salidas DQMH/DQML, pero dejaba **A12/A11=00**
al emitir WRITE. Los módulos MiSTer XS/XSDS conectan las máscaras del chip a
**A12= DQMH y A11= DQML**. Por tanto, ambos bytes quedaban habilitados aunque
el AT sólo quisiera escribir uno.

Se ha reproducido exactamente el fallo con el RTL anterior y ese cableado:
primera lectura de Landmark, dirección **006E40h**, palabra devuelta **FF00h**.
La corrección pasa la rutina completa de cinco patrones en simulación con la
ROM original. La confirmación del nuevo RBF en la placa queda para el usuario.
No se ha sintetizado ni generado un RBF en esta revisión.

## Evidencia física recibida

Las imágenes originales y la transcripción están en
`analysis/at_dqm_wiring_20260912/hardware-page-0.png` a `hardware-page-3.png` y
`hardware-decoded.json`. Las palabras se conservan en orden visible T0..T3:

| Página | T0 | T1 | T2 | T3 |
|---|---|---|---|---|
| Compare | C1FF0000 | F0009F37 | 40000001 | 008606E4 |
| Read path | F5006E40 | E4006E40 | F0003720 | 0000FF00 |
| SDRAM | FF000600 | 06E4F000 | 00006E40 | 000F0000 |
| Registers | FFFFB800 | 40000000 | 0200AE3F | FF008E03 |

`VALID=1`, `ARMED=1`, `COMPARISONS=0001`. La comparación retirada en
F000:9F37 espera AH=FF, recibe BL=00 y deja ZF=0. DI ya es 0001, ES=06E4 y
su base oculta=006E40: el byte comparado está en 006E40+(DI-1)=006E40.
CPU y backend solicitan ese mismo byte; KF usa la palabra 003720, es decir
006E40 >> 1. KF captura FF00, backend devuelve FF00, la lane baja entrega 00
al CPU. La comparación informa correctamente del error que recibió.

La última escritura capturada es 00AE3F, BE=10, dato FF00, al final del patrón.
La captura no contiene todas las escrituras anteriores ni una medida eléctrica
externa. La reproducción siguiente completa esa parte de la cadena con señales
simuladas de los pines y con el cableado documentado de la placa.

## Cableado comprobado y defecto del modelo anterior

Fuentes primarias revisadas visualmente, primera página de cada esquema:

- [SDRAM XS 2.2, Sorgelig](https://github.com/MiSTer-devel/Hardware_MiSTer/blob/master/releases/sdram_xs_2.2.pdf).
- [SDRAM XSDS 3.0, Sorgelig](https://github.com/MiSTer-devel/Hardware_MiSTer/blob/master/releases/sdram_xsds_3.0.pdf).

En XSDS, U1A/U2A: pin 15 DQML conectado a A11; pin 39 DQMH conectado a A12.
Estas mismas redes son bits de dirección de fila en ACTIVE. Un
[controlador funcional de MiSTer](https://github.com/MiSTer-devel/AliceMC10_MiSTer/blob/master/rtl/sdram.sv)
también coloca las máscaras en A12/A11 al emitir comandos de columna y las
replica en las salidas DQMH/DQML. No se cambia su organización de direcciones
por la de KFSDRAM: sólo se verifica el contrato eléctrico común.

El modelo anterior `spk286_sdram_pin_model.sv` recibía únicamente las salidas
DQM dedicadas. Además, rechazaba cualquier A12/A11 distinto de cero durante
READ/WRITE, aunque no sean bits de columna en la geometría x16 modelada.
Ese modelo verificaba el chip con una conexión de placa diferente y ocultaba
el defecto del AT. El RTL anterior sigue pasando el control con DQM dedicado,
pero falla al conectar las máscaras del modelo a A12/A11.

Ahora el modelo usa `DQM_FROM_ADDRESS=1` por defecto (XS/XSDS); el valor 0
mantiene el cableado dedicado como control. Conserva CL2, BL1, ventana DQ
finita, latencia DQM de lectura 2/escritura 0, ACT previo y dirección completa
sin módulo. A10/AP y A9 siguen comprobados según el subconjunto de geometría
que emite KFSDRAM. No es un modelo de retención ni un cierre temporal de una
placa concreta, ni certifica toda la capacidad de todos los módulos MiSTer.

## Reproducción antes y después

Las ondas Icarus y sus comandos muestreados se guardan como
`before-capture.vcd`, `after-capture-1.vcd`, `before-pins.csv`, `after-pins.csv`.
El test comienza cargando y leyendo el vector de ROM, que ya pasaba antes.
Luego escribe y lee la palabra de la dirección observada en hardware:

| Operación | DQ | BE | DQM dedicado | A12:A11 antes | A12:A11 corregido |
|---|---|---|---|---|---|
| Inicializar palabra 006E40 | 0000 | 11 | 00 | 00 | 00 |
| Escribir byte 006E40 | 00FF | 01 | 10 | 00 | 10 |
| Escribir byte 006E41 | FF00 | 10 | 01 | 00 | 01 |
| Leer palabra 006E40 | — | 11 | 00 | 00 | 00 |
| Resultado leído | | | | **FF00 (FAIL)** | **FFFF (PASS)** |

Sin la máscara, la segunda escritura introduce también su relleno 00 en el
byte bajo. Con la máscara, conserva el FF escrito antes. No hay cambio de
A >> 1, alias del vector, orden de bytes, ready/valid ni latencia.

La reproducción con el CPU y la rutina original de Landmark (caso 11, entrada
8DDD, borrado e impresión de encabezado) falla antes del cambio con:

```text
RAM_READ_ORACLE beat=0 addr=006e40 data=ff00
```

El fallo lo detecta un oráculo independiente del CPU, antes de que éste retire
la comparación. El mismo contexto ES=06E4 de la captura física aparece en el
log. La ROM SKIP_PM se usó en esta reproducción anterior; las validaciones
completas posteriores usan la ROM original. La auditoría anterior demuestra
que los bytes de esta rutina son idénticos en ambas ROM.

## Cambio mínimo y comparación XT/AT

La única modificación funcional de producción está en
`rtl/spk286_integration/spk286_at_mister_sdram_owner.sv`: durante READ/WRITE,
A12/A11 reciben las máscaras existentes; el resto de A y todos los comandos
permanecen iguales. En ACTIVE se conserva la fila completa de 13 bits.
No se modifica KFSDRAM compartido ni el perfil XT.

| Aspecto | XT de referencia | AT |
|---|---|---|
| Almacenamiento de bytes CPU | Un byte útil en la lane baja de cada palabra física | Dos bytes útiles por palabra física |
| Escritura de palabra CPU | Dos beats físicos de byte bajo | Una palabra o las lanes necesarias según el acceso |
| Máscaras | Ambos bytes habilitados; el alto no contiene otro byte CPU útil | La escritura por byte debe preservar la otra lane |
| Efecto de A12/A11=00 en WRITE | Compatible con ese almacenamiento | Destruye el byte vecino cuando se usa una sola lane |
| Carga de ROM AT | No se cambia el cargador XT | HPS carga palabras completas; el defecto no destruye otra lane |
| Solución | Sin cambios | Llevar las máscaras a los pines que usa el módulo MiSTer |

`RAM.sv` de XT confirma los datos `{00, byte}` y DQM=00. Esto explica por qué
ese perfil sí pasa el test sin convertir sus demás resultados en referencia
absoluta para un AT.

## Validación realizada

- `test_at_sdram_capture.sh` y `.ps1`: PASS con ambos cableados; 28 transacciones
  por cableado, 16 escrituras y 12 lecturas. Incluye byte bajo/alto, palabras,
  frontera de fila, vector de reset y filas con las cuatro combinaciones
  A12/A11 (direcciones 000400, 200400, 400400, 600400), comprobando ausencia de alias.
- Control de sensibilidad de reloj: el desplazamiento artificial de +4 ns
  produce la lectura Z esperada; el modelo no retiene datos indefinidamente.
- Control anterior con DQM dedicado: PASS. Con A12/A11: FAIL exacto FF00.
- `test_at_landmark_ram.sh`, **ROM original**, casos 13/14: errores inyectados
  FF -> FE en bytes par/impar detectados correctamente por BIOS y traza.
- Casos 11/12: PASS de FF/01/55/AA/00; cada caso verifica **81.920 escrituras y
  81.920 lecturas**, direcciones y lanes, sin fallos del CPU o protocolo.
  Caso 11: 29.011.397 ciclos; caso 12: 23.791.827 ciclos. Al éxito se exige
  traza armada, VALID=0 y contador saturado FFFF.
- Primer fetch y carga HPS de cuatro ROM: PASS, 32 lecturas de instrucción.
- Propietario SDRAM, frontera de máquina, lint de producción y elaboración
  del perfil AT: PASS. El diff pasa `git diff --check`.

Comandos reproducibles desde la raíz del repositorio, en WSL/Bash:

```bash
bash scripts/test_at_sdram_capture.sh
AT_SYSTEM_ROM="$PWD/SW/ROMs/test/Supersoft_Landmark_1.2.0_AT_5170_64K.BIN" \
  AT_LANDMARK_TIMEOUT=180s bash scripts/test_at_landmark_ram.sh
bash scripts/test_at_bios_first_fetch.sh
bash scripts/test_at_mister_sdram_owner.sh
bash scripts/test_at_machine_boundary.sh
bash scripts/test_at_profile_elab.sh
```

Control negativo reproducible; debe terminar con `expected=ffff actual=ff00`:

```bash
AT_SDRAM_OWNER_SOURCE="$PWD/analysis/at_dqm_wiring_20260912/sdram_owner_before.sv.txt" \
  PCAT_BUILD_DIR="$PWD/build/at-dqm-negative-control" \
  bash scripts/test_at_sdram_capture.sh
```

No se afirma un PASS simulado del POST completo desde reset: la prueba larga
anterior fue inconclusa. Los casos de Landmark seleccionan una entrada en el
buffer del testbench; no alteran ningún archivo BIOS ni omiten sus comparaciones.
Las ondas, logs y hashes de ROM están en `analysis/at_dqm_wiring_20260912/`.

## Timing, configuración y otros problemas

Se leyó el `.sta.summary` del fit aportado por el usuario, sin ejecutar Quartus:
slow 1100mV 100C, setup de FPGA_CLK2_50 **-7,563 ns**, grupo SDRAM_CLK **+1,640 ns**,
hold SDRAM_CLK **+0,256 ns**. El peor setup global listado es VCLK_SDIO **-21,513 ns**.
Son resultados previos a esta corrección. Los grupos no identifican por sí solos
una ruta CPU concreta; el anterior -4,338 ns correspondía a otro fit analizado.
El diseño sigue sin cierre temporal general. Las máscaras incorrectas se
reproducen incluso con lógica ideal y reloj nominal, independientemente de ello.

El fallo documentado aquí es de escritura SDRAM, no un fallo nuevo de reset,
splash o activación de modo protegido. No se han cambiado esos subsistemas.
`BASE 000K` proviene de la configuración CMOS y queda pendiente por separado:
esta rutina toma DX=4000, no ese tamaño configurado. MEMORY REFRESH aún requiere
una prueba AT una vez que la BIOS supere 16K.

## Prueba siguiente en hardware

1. Sintetizar **PCAT-286_AT_FAST** desde el commit de esta entrega. Usar un
   nombre distinto, por ejemplo `PCAT-286_20260912_at_dqm_address_pins_AT_FAST.rbf`.
2. Cargar la misma ROM **original** que ya mostró todos los tests previos PASS:
   `Supersoft_Landmark_1.2.0_AT_5170_64K.BIN`, SHA-256
   `A8310F83DE0F3E6B71E4A3FF82A01FFE3C3B5A957677AED2FAD17B96BCE2E577`.
   Para continuar después con la SKIP_PM ya existente, SHA-256
   `E9A3F0605996FF6802F44AD1744675C01DF9B5832273BB7472C878A6AAD03EC6`.
3. Hacer reset completo del core. Verificar **16K CRITICAL MEMORY REGION PASSED**
   y anotar el resultado de **MEMORY REFRESH** cuando aparezca.
4. Si pasa, capturar el diagnóstico y conservar el timing del nuevo fit.
   En la traza se espera ARMED=1, VALID=0, COMPARISONS=FFFF al completar 16K.
5. Si sigue fallando, enviar las mismas cuatro páginas tras un reset completo.
   Si repite exactamente FF00 pese a sintetizar este cambio, hará falta además
   identificar modelo/revisión del módulo SDRAM y capturar con SignalTap
   A[12:0], DQ, BA, CS/RAS/CAS/WE, DQM dedicado y BE durante las escrituras a
   006E40/006E41. No hace falta una captura adicional antes de probar la corrección.

El hash del RBF previo existente en disco está en `manifest.json`: no es una
lectura de la FPGA ni un hash de un RBF nuevo. El usuario hace síntesis y prueba;
el agente se detiene al entregar fuentes, tests y commit.
