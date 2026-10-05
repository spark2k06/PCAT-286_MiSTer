# PM5d — servicio único de cambio de tarea

`spk286_task_switch_service` compone la prelectura de la imagen TSS, la
validación de las caches ES/CS/SS/DS y el servicio de guardado/carga de PM5a.
Su interfaz es una única transacción serializada para entrada anidada, salto o
retorno de tarea:

1. lee los 15 words de la imagen entrante;
2. valida los cuatro descriptores de segmento y espera READY sin cambiar la
   tarea saliente;
3. ejecuta el guardado, backlink/busy y carga a través de
   `spk286_tss_service`;
4. publica el nuevo estado y las caches solo tras completar la secuencia.

La prueba dirigida cubre orden de guardado/backlink/busy, NT para una entrada
anidada, caches ocultas, espera `READY` e invalidación de CS antes de modificar
el TSS saliente.

Este hito deja preparada la interfaz única que invoca el microcódigo. La
conexión de las transferencias lejanas directas y el commit arquitectónico se
documenta en PM5e; los task gates y la ruta IRET basada en backlink siguen
siendo trabajo posterior.
