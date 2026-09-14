# P07 — Camino EGA byte-preservado

Estado: propuesta condicionada de arquitectura y timing. Base: `4a05f97`,
2026-09-14. Aplican los [requisitos comunes](README.md).

## 1. Objetivo

Evaluar si el camino interno de acceso a la VRAM EGA puede consumir menos
ciclos o tener una ruta crítica más corta, conservando exactamente el modelo
de hardware original: una tarjeta EGA ISA de 8 bits.

La EGA original no se convierte en una tarjeta de 16 bits por instalarse en un
PC AT. Sus registros, la apertura de memoria y la lógica de lectura/escritura
por planos se deben tratar como accesos byte a byte. P07 sólo permite optimizar
la implementación interna cuando el resultado observable siga siendo el de
dos operaciones de byte independientes y ordenadas.

P07 no promete una mejora de CheckIt CPU/MATH. Su beneficio directo, si existe,
se espera en cargas que escriban o lean mucha VRAM EGA. Sólo se considerará una
mejora de timing global si el STA identifica una ruta del frontend EGA como
limitante; no se atribuirá a P07 una mejora de otra ruta.

## 2. Alcance y no objetivos

| Dentro de P07 | Fuera de P07 |
| --- | --- |
| Reducir espera del frontend CPU–VRAM | Cambiar la interfaz externa de EGA a 16 bits |
| Agrupar dos accesos consecutivos compatibles | Habilitar indiscriminadamente `word_capable` para A0000–BFFFF |
| Compartir o registrar mejor la selección de planos | Alterar el reloj del CRTC, raster o SDRAM |
| Acortar muxes y fanout de la ruta de vídeo | Cambiar registros EGA, modos, máscaras o alias del mapa |
| Medir la mejora en una configuración opcional | Tratar clones VGA/EGA de 16 bits como hardware original |

La política inicial DEBE mantener el acceso byte-wide actual. Una variante
experimental puede aceptar internamente un par, pero sólo tras demostrar que
ambos bytes pertenecen a una secuencia legal y que cada byte conserva sus
efectos de plano y de lectura modificada.

## 3. Punto de partida del core

La integración actual expone al frontend EGA `cpu_din` y `cpu_dout` de 8 bits.
`spk286_at_video_adapter` selecciona el byte bajo o alto según la lane de la
petición y retiene una sola operación de memoria. El frontend
`ega_vram_bram_frontend` entrega asimismo una interfaz CPU de 8 bits y usa una
máquina de estados de espera/finalización sobre la VRAM planar compartida con
el raster.

Antes de cambiar RTL se DEBE registrar, para el mismo commit y RBF:

- ciclos desde aceptación CPU hasta `memory_ready`;
- frecuencia y duración de accesos a A0000–BFFFF;
- proporción de byte bajo, byte alto, palabras divididas y accesos no alineados;
- estado de `odd_even_mode`, `chain2`, `read_mode`, `write_mode` y máscaras;
- rutas STA que atraviesen el adaptador, frontend, planos o CDC de vídeo.

## 4. Candidatos permitidos

### P07-A — Agrupación conservadora de bytes

Detectar dos peticiones de byte consecutivas que estén ya retenidas, sean del
mismo propietario y estén en direcciones adyacentes. Mantener la primera
respuesta bloqueada hasta que el segundo byte haya sido procesado. El backend
puede usar dos lanes internas si eso no altera el orden ni las operaciones
plane-specific.

No agrupar si hay cambio de modo, cruce de límite relevante, acceso no alineado,
lectura con efectos, operación pendiente de raster, `HOLD`, `LOCK`, reset,
cancelación o cualquier contención que cambie la secuencia observable.

### P07-B — Frontend registrado de menor profundidad

Separar predecodificación de dirección, selección de mapa y selección de plano,
registrando los resultados donde la ruta crítica lo necesite. Puede reducir
setup y fanout aun manteniendo un byte por operación. La latencia añadida por
un registro sólo es aceptable si el rendimiento útil no empeora.

### P07-C — Acceso interno de dos lanes

Evaluar dos operaciones de byte en paralelo dentro del frontend únicamente
como variante posterior. Las dos lanes DEBEN aplicar las mismas reglas que dos
llamadas secuenciales, incluyendo la lectura previa de los cuatro planos, la
rotación, set/reset, ROP, bit mask, write mask y selección de mapa.

P07-C no puede exponerse como una palabra AT genérica ni asumir que una escritura
de palabra es una única operación EGA. Si no se puede demostrar equivalencia
para todos los modos, se descarta.

## 5. Requisitos de corrección

P07-R01. El límite visible del dispositivo continúa siendo byte-wide; la CPU
puede seguir dividiendo palabras en las mismas lanes y orden que la base.

P07-R02. Una lectura EGA conserva el valor y el momento de captura de cada byte.
No se adelanta la respuesta de una lane usando datos de la otra.

P07-R03. Las escrituras respetan por separado `plane_write_mask`, `bit_mask`,
`set_reset`, ROP, `odd_even_mode`, `chain2` y cualquier modo de mapa activo.

P07-R04. No se fusionan operaciones que crucen una frontera de 64 KiB, una
ventana de mapa, un cambio de configuración o una condición de contención.

P07-R05. Se conservan READY, backpressure, propietario, `HOLD/HLDA`, `LOCK`,
reset, cancelación, DMA/refresco y arbitraje. Toda petición aceptada termina
una sola vez, aunque P07 la procese internamente en varios beats.

P07-R06. La actividad del raster y las lecturas de texto siguen observando la
VRAM en el orden definido por el frontend actual. No se introduce coherencia
implícita de caché ni se reordena una escritura pendiente.

P07-R07. La implementación debe poder desactivarse con un parámetro o perfil
de elaboración para comparar exactamente la base frente a la variante.

## 6. Timing y recursos

El análisis DEBE distinguir:

1. latencia arquitectónica CPU–EGA;
2. ciclos consumidos por el frontend y la VRAM planar;
3. retraso de lógica y routing de la ruta crítica;
4. tráfico y contención con raster, memoria y otros propietarios.

No se añadirá una excepción multicycle ni un false path para ocultar la ruta.
Se compararán al menos las 20 peores rutas setup/hold del grupo de vídeo y el
peor slack global. También se registrarán ALM, registros, memoria, fanout y
frecuencia máxima del mismo perfil físico.

Una variante sólo será candidata si mantiene o mejora el margen de timing y no
reduce el rendimiento útil de las cargas generales. Una mejora de slack con más
ciclos de CPU no se considerará éxito por sí sola.

## 7. Pruebas mínimas

| ID | Caso | Resultado exigido |
| --- | --- | --- |
| P07-T01 | Lecturas/escrituras de byte en las cuatro lanes | Datos y efectos idénticos a la base |
| P07-T02 | Palabras alineadas y no alineadas | Misma división, orden y READY |
| P07-T03 | Todos los modos de lectura/escritura EGA | Planos, ROP y máscaras idénticos |
| P07-T04 | Odd/even, chain-2 y mapas A0000–BFFFF | Sin alias ni bytes cruzados |
| P07-T05 | Raster concurrente y acceso de texto | Sin tearing funcional ni dato perdido |
| P07-T06 | HOLD, LOCK, DMA, refresco y reset | Arbitraje y drenaje conservados |
| P07-T07 | Escrituras automodificables y lectura posterior | Memoria actual, sin respuesta obsoleta |
| P07-T08 | DOS, BIOS EGA y cargas gráficas | Arranque y compatibilidad conservados |
| P07-T09 | CheckIt y carga CPU/MATH | Sin regresión; beneficio sólo si está medido |
| P07-T10 | Repetición prolongada | Cero divergencias frente a la base |

## 8. Criterio de decisión

P07 se implementa sólo si una traza real muestra coste significativo de EGA o
el STA confirma que su frontend limita el reloj. Se cierra como PASS cuando
la matriz funcional no presenta divergencias, la variante conserva el modelo
EGA de 8 bits, el timing mejora o no empeora dentro del margen acordado y existe
una ganancia medida en una carga de vídeo o una reducción demostrada de ciclos.

Si el beneficio queda limitado a gráficos y no afecta a CheckIt, se documentará
así. Si no hay beneficio o la equivalencia exige excepciones incompatibles con
una EGA original, P07 se descarta sin modificar la base estable.

## 9. Entregables

Manifiesto de la base y la variante, trazas de accesos EGA, tabla de rutas STA,
RTL opcional con parámetro de desactivación, pruebas de equivalencia, recursos,
resultados de timing y una prueba de placa con BIOS, modo de vídeo y RBF
identificados por hash.
