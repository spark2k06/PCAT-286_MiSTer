# PM5c — construcción atómica de caches de segmento de la tarea

`spk286_task_segment_service` consume los selectores ES/CS/SS/DS del TSS y
construye candidatos de cache oculta sin modificar el estado visible hasta que
los cuatro descriptores han sido leídos y validados.

El servicio cubre:

- resolución independiente por GDT/LDT y retención de dirección durante
  `READY`;
- CS ejecutable y SS de datos escribible con CPL/DPL/RPL coherentes;
- ES/DS de datos o código legible, incluyendo selectores nulos para ES/DS;
- clasificación de selector/tipo inválido como `#TS` y descriptor no presente
  como `#NP`;
- actualización de los bits `accessed` de los cuatro descriptores antes del
  pulso `commit_valid`;
- publicación conjunta de selectores, bases, límites, accesos, clases,
  presencia, DPL, TI y RPL.

Este hito prepara la frontera de validación previa al commit de PM5. Todavía
queda conectar el descriptor TSS, el movimiento de la imagen y este servicio
al ejecutor real, además de implementar busy/backlink, task gates e IRET de
retorno.
