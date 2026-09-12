# Evidencia AT: PIT, puerto 61h y reset RTC

El informe y la prueba física siguiente están en
[`AT_LANDMARK_PIT_PARITY_HANDOFF.md`](../../docs/AT_LANDMARK_PIT_PARITY_HANDOFF.md).
Esta carpeta no contiene un RBF nuevo. `latest-user-fit.sta.*` pertenece al fit
anterior del usuario, preservado en el checkpoint DMA `785231e`.

## Reproducciones negativas

- `rtc-before-cold.log`: salida X tras reset, Icarus de cuatro estados.
- `rtc-before-warm.log`: salida 1 después de inyectar lane incorrecta y reset.
- `rtc-before-yosys.log`/`rtc-after-yosys.log`: síntesis lógica aislada de ese
  módulo con Yosys, no síntesis del FPGA. El puerto protocol_error queda como
  constante 1 antes y como registro con reset después.
- `landmark-parity-before.log`: FF en 61h y fetch del manejador FAILED 0F9B68h.
- `landmark-memory-before.log`: primer byte coincide, lectura FF en 61h y
  salida por paridad 0F9E93h. Esta captura es anterior al oráculo adicional
  que comprueba direcciones/lanes/patrones de la prueba final.
- `pit-before.log`: el módulo anterior devuelve 3333h al leer el contador
  después de cargar 1234h y aplicar un tick. `pit-baseline-test-wrapper.sv`
  sólo añade la nueva entrada GATE2 a su declaración para poder elaborar el
  mismo banco; el RTL antiguo no la utiliza. No se cambia su comportamiento.

Los archivos `.before.sv` conservan los módulos del checkpoint inicial.
El test de reset puede reproducirse con Icarus usando el RTC anterior y
`sim/spk286_integration/spk286_at_rtc_reset_tb.sv`; `+WARM_ONLY` selecciona la
prueba que también falla cuando el simulador inicializa a cero.

## Pruebas positivas

Desde la raíz del repositorio, en WSL:

```sh
bash scripts/test_at_pit_ports.sh
bash scripts/test_at_landmark_peripherals.sh
bash scripts/test_at_landmark_dma.sh
bash scripts/test_at_bios_first_fetch.sh
bash scripts/test_a4_dma_refresh_pit.sh
bash scripts/test_at_machine_boundary.sh
bash scripts/test_a5_at_devices.sh
bash scripts/test_at_fault_trace.sh
bash scripts/test_debug_overlay.sh
bash scripts/test_at_profile_elab.sh
```

Los logs `*-after.log` son resultados de simulación, no observaciones de placa.
`overlay-after.log` conserva las líneas PASS de los cuatro escenarios del
script, omitiendo la salida de compilación. La ROM no se modifica. Los casos
originales se ejecutan con el backend físico KFSDRAM y el modelo de pines
existente; las pruebas de memoria no sustituyen ni relajan ese modelo.

`source-manifest.sha256` identifica fuentes tal como estaban en el workspace
(bytes, incluyendo terminadores de línea); `rom.sha256` identifica la ROM.
No se afirma un POST completo ni cierre de timing.
