# Scaler HDMI: dividir el máximo RGB sin cambiar la latencia

## Punto de partida

Fit del 25/09/2026, 10:30, descrito en `AT_NATIVE_OUTPUT_FIT_20260925_1030.md`:

- Ruta `ascal|o_h_lum_pix.g[4] → ascal|o_poly_lum[1]`.
- Setup −0,294 ns en Slow −40 °C; −0,094 ns en Slow 100 °C.
- FMax HDMI mínima: 142,33 MHz, con reloj analizado de 148,54 MHz.

Es lógica síncrona de datos del filtro adaptativo. No es un CDC ni una
señal de configuración mantenida estable, por lo que debe cumplir setup.

## Cambio en `sys/ascal.vhd`

La función anterior calculaba `max(R,G,B)` mediante dos comparaciones
consecutivas antes de `o_poly_lum`. La etapa siguiente sólo copiaba el
resultado en `o_poly_lum1`.

| Etapa existente | Antes | Ahora |
|---|---|---|
| C3 / HC3 / VC4 | Registrar `max(R,G,B)` | Registrar `max(R,G)` y B |
| C4 / HC4 / VC5 | Copiar luminancia | Registrar `max(max_rg_q,b_q)` |
| C5 / HC5 / VC6 | Calcular pesos `256-lum` y `lum` | Igual |

Se mantienen la latencia total, la prioridad del eje vertical, las direcciones
de coeficientes y las etapas posteriores. Si ningún eje adaptativo está
activo, los dos registros de la primera etapa retienen juntos su último
valor. Se añaden ocho bits de registro en RTL; el coste físico se conocerá
con el siguiente fit.

La optimización no añade excepciones SDC. La auditoría de TimeQuest incorpora
las familias `scaler_luminance_capture`, `scaler_luminance_reduce` y
`scaler_luminance_weights`, con comprobación de setup y hold en todas las
condiciones y rechazo de colecciones vacías.

## Verificación previa al fit

`python3 scripts/test_at_scaler_luminance.py` genera dos envoltorios con las
declaraciones, funciones y proceso `PolyFetch` completos: uno del RTL actual
y otro del commit de referencia `a8bc4f12e50317f29bb316367e1bbf477aee262b`.
La referencia queda fijada para que futuros commits no cambien el patrón de
comparación. Además se comprueban luminancia y pesos contra un modelo entero
independiente con sus retardos esperados.

Se usan tablas de coeficientes diferentes entre sí, con valores negativos y
dependientes de la fase, para detectar desalineaciones que filtros identidad
o píxeles grises podrían ocultar. La comparación incluye luminancia, pesos,
dirección adaptativa y los ocho coeficientes finales de los ejes H/V.

Resultado: **PASS, 73.872 ciclos** a periodo de 6,734 ns, con combinaciones
RGB de frontera, 65.536 muestras aleatorias, cambios consecutivos de modo,
fase y habilitación, prioridad V cuando ambos ejes están activos y retención:

- Selección horizontal: 17.901 ciclos.
- Selección vertical: 30.616 ciclos, incluidos 13.058 con ambos ejes activos.
- Retención sin eje activo: 25.355 ciclos.

La compilación GHDL del scaler completo en VHDL-93 también pasa.
Evidencias: `build/at-scaler-luminance/equivalence/`.

Quartus 17.0 **Analysis & Elaboration: PASS, 0 errores y 131 advertencias**,
el mismo número de advertencias que la validación anterior. El comprobador
de asignaciones del proyecto también pasa. Se ejecutó en copia aislada,
sin síntesis de mapeado, Fitter, ensamblado ni generación de RBF.
Evidencias y hashes de entrada: `build/at-scaler-luminance/frontend/`.

Regresión del scaler completo: **6/6 variantes PASS**, junto con sus seis
comprobadores de transacciones Avalon y los dos de coeficientes adaptativos:

| Variante | Lecturas Avalon | Beats escritos | Píxeles válidos |
|---|---:|---:|---:|
| Progresivo | 185 | 3.840 | 26.965 |
| Entrelazado | 202 | 3.840 | 24.661 |
| Configuración local, progresivo | 188 | 4.368 | 27.648 |
| Configuración local, entrelazado | 205 | 4.368 | 25.344 |
| Filtro adaptativo, progresivo | 171 | 4.368 | 24.576 |
| Filtro adaptativo, entrelazado | 172 | 4.368 | 23.040 |

Se verifican backpressure, coherencia de comandos, triple buffering, cambios
de base del framebuffer, cambios de geometría, pausas de reloj y publicación
de coeficientes. En cada prueba adaptativa se comprueban 8.192 escrituras de
coeficientes y la transición H → V → desactivado. Evidencias:
`build/at-scaler-luminance/integration/`.

## Resultado del fit y prueba en hardware

El usuario compiló y confirmó funcionamiento en hardware con el RBF
`PCAT-286_20260925_113743.rbf`. La auditoría posterior de TimeQuest confirma
las tres familias nuevas en las cuatro condiciones: setup mínimo
**+1,305 / +1,976 / +1,749 ns**, con hold positivo.

El dominio HDMI completo pasa de −0,294 a **+0,125 ns** y su FMax mínima
de 142,33 a **151,35 MHz**. El cierre global sigue pendiente en CPU/CLK2
y su interfaz con SDRAM. Véase `AT_SCALER_LUMINANCE_FIT_20260925_1139.md`
para las rutas, condiciones, recursos y la trazabilidad del RBF.
