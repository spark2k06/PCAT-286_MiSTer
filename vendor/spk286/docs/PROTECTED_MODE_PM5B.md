# PM5b — resolución transaccional del descriptor TSS

PM5b añade la resolución verificable del descriptor TSS que consume la futura
conmutación de tareas. El servicio `spk286_tss_descriptor_service` es
deliberadamente independiente del movimiento de la imagen TSS de PM5a:

- descompone el selector contra GDT o LDT y comprueba el límite completo de la
  entrada de ocho bytes;
- mantiene la petición de memoria y la dirección estables durante una espera
  `READY`;
- lee los cuatro words del descriptor sin publicar un candidato parcial;
- acepta TSS disponible para entrada y TSS ocupado para retorno por `IRET`;
- valida presencia, forma reservada, límite mínimo fijo `002Bh` y, cuando se
  solicita, DPL frente a CPL/RPL;
- publica `#TS` o `#NP` antes de exponer el candidato, sin escribir estado
  arquitectónico.

La matriz dirigida cubre GDT/LDT, entrada/retorno, espera `READY`, límite
corto, descriptor no presente, tipo no TSS y privilegio insuficiente.

Esto cierra la resolución de la entrada TSS como servicio PM5b. Todavía no
declara implementada la instrucción completa: queda conectar este servicio al
ejecutor de microcódigo, encadenarlo con `spk286_tss_service`, validar los
cuatro descriptores de segmento de la tarea antes del commit y añadir task
gates e `IRET` anidado.
