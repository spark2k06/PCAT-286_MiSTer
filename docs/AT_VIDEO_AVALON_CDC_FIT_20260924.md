# Resultado del fit CDC — 24/09/2026

## Conclusión

**Las cuatro familias CDC intervenidas cumplen sus restricciones en las cuatro
esquinas. El proyecto completo todavía no cumple setup.** La peor ruta global
ahora es otro cruce de vídeo, `sync_v|pol → vs_r`, con −6,356 ns.

La compilación del usuario terminó correctamente; síntesis 5:56, Fitter 16:16,
ensamblado 0:28 y TimeQuest 1:42: total **24:22**. Estos tiempos proceden del
informe del flujo original. La revisión posterior ejecutó únicamente TimeQuest.

Se verificó que los hashes de `SYSTEM.sdc`, `sys/ascal.vhd` y el adaptador de
vídeo coinciden con el manifiesto preparado antes de compilar. La netlist
contiene los nuevos registros y los extremos requeridos por las restricciones.
Los antiguos `avl_i_offset0/1` y `avl_o_offset0/1` ya no existen.

## Rutas corregidas

Los valores anteriores son los peores de las familias originales. Los nuevos
son los peores de sus rutas sustitutas entre las cuatro esquinas, con setup y
hold normales entre etapas síncronas y max-delay en los buses retenidos.

| Familia anterior | Antes | Ruta activa que la sustituye | Después |
|---|---:|---|---:|
| Banco de escritura 0 | −6,908 ns | Snapshot de bancos / comando de escritura | +6,949 / +1,657 ns |
| Banco de escritura 1 | −6,948 ns | Snapshot de bancos / comando de escritura | +6,949 / +1,657 ns |
| Dirección de lectura | −6,849 ns | Payload dirección+base retenido | +1,849 ns |
| Selección VGA | −6,893 ns | Decode registrado / primera→segunda etapa | +31,326 / +18,666 ns |

Otras rutas activas del protocolo:

| Ruta | Peor setup | Peor hold |
|---|---:|---:|
| Dirección/base local → dirección Avalon de lectura | +4,829 ns | +0,304 ns |
| Dirección/base local → dirección Avalon de escritura | +8,118 ns | +0,225 ns |
| Sincronizador de petición de lectura | +8,908 ns | +0,246 ns |
| Sincronizador de petición de escritura | +8,810 ns | +0,299 ns |
| Sincronizador de acuse de lectura | +5,458 ns | +0,275 ns |
| Sincronizador de acuse de datos | +5,362 ns | +0,247 ns |
| Sincronizadores de fin de cuadro de entrada | +5,540 ns | +0,227 ns |
| Sincronizador de fin de cuadro de salida | +8,990 ns | +0,227 ns |
| Selección VGA: primera→segunda etapa | +18,666 ns | +0,233 ns |

El historial de campos cumple su max-delay con +2,553 ns, y el snapshot de
configuración del framebuffer con +9,077 ns. Todos sus sincronizadores también
cumplen setup y hold. Los mayores retardos de datos entre las rutas reportadas
de los comandos son 2,270 ns en lectura y 2,629 ns en escritura, frente a una
captura digital observada no anterior a 30,070 ns. El análisis mantiene el
presupuesto max-delay de 10 ns, incluyendo las latencias de reloj de Quartus 17.

No se interpreta como éxito la mera desaparición de las rutas antiguas:
`focused/path_counts.txt` demuestra que hay rutas activas en todas las familias
nuevas. Las exclusiones de hold en payloads y de llegada a primera etapa están
justificadas por los protocolos descritos en `AT_VIDEO_AVALON_CDC.md`.

## Estado global

| Métrica | Antes | Después |
|---|---:|---:|
| Peor setup | −6,948 ns | **−6,356 ns** |
| Peor hold | +0,067 ns | **+0,026 ns** |
| Peor recovery | +3,866 ns | +3,797 ns |
| Peor removal | +0,343 ns | +0,371 ns |
| Peor ancho mínimo de pulso | +0,793 ns | +0,793 ns |
| TNS setup, Slow 1100 mV / 100 °C | −7.476,799 ns | **−8.209,493 ns** |

El peor setup mejora 0,592 ns; el TNS de esa esquina empeora 732,694 ns. Por
tanto, el resultado acredita la corrección de estos CDC, pero no una mejora
uniforme del timing ni el cierre general. El hold positivo de 0,026 ns deja
poco margen en su ruta más ajustada.

### FMax por dominio

Mínimo de los informes de las cuatro esquinas. FMax sólo considera rutas dentro
del mismo reloj: no sustituye al análisis de cruces entre relojes.

| Dominio | Reloj requerido | FMax peor |
|---|---:|---:|
| CPU / `FPGA_CLK2_50` | 50 MHz | **40,14 MHz** |
| HDMI | 148,54 MHz | **108,07 MHz** |
| Avalon HPS | 100 MHz | 148,46 MHz |
| Vídeo base | 28,64 MHz | 33,13 MHz |
| Vídeo ×2 | 57,27 MHz | 85,46 MHz |
| Vídeo de salida +90° | 57,27 MHz | 87,05 MHz |
| `FPGA_CLK1_50` | 50 MHz | 83,12 MHz |
| Audio | 24,58 MHz | 38,74 MHz |

### Siguientes rutas fuera de SPK286

La prioridad siguiente es el contador de cuadros en `sys/sys_top.v`:
`vs_r` recibe `vs_fix` directamente, y `vs_old` se habilita comparando esa
señal asíncrona con `vs_r`. Hace falta sincronizar el nivel VSYNC con dos etapas
y detectar el flanco después de la segunda. Las peores rutas actuales son
`sync_v|pol → vs_r` (−6,356 ns) y `at_video_vs_out_q → vs_r` (−6,208 ns).

Después, los controles de `HDMI_shadowmask`: `hmax[3] → hmax2[3]` alcanza
−6,168 ns y `mask_rotate` hacia la dirección de la LUT, −6,023 ns. Los campos
programados deben llegar juntos y aplicarse en una frontera de cuadro; la
actualización de la LUT necesita preservar su protocolo de escritura.

También permanecen los controles de geometría/LFB y la selección del perfil de
monitor. Estas rutas no se han excluido ni modificado en esta revisión. Las
rutas internas de SPK286 siguen pendientes de su trabajo específico.

| Ruta/grupo pendiente | Peor setup actual |
|---|---:|
| VSYNC → contador de cuadros | −6,356 ns |
| Configuración `HDMI_shadowmask` → reloj HDMI | −6,168 ns |
| Geometría: `HDMI_PR → videow[9]` | −5,826 ns |
| Perfil EGA: `applied[1] → ega_monitor_profile_video_sync1_q[1]` | −5,301 ns |
| SPK286 interno | −4,911 ns |
| BIU → dirección del controlador SDRAM | −1,179 ns |

Las interfaces CPU→bridge y bridge→CPU tienen +0,858 ns y +11,761 ns,
respectivamente. El puerto de memoria tiene +3,550 ns; los pines SDRAM cumplen
con +5,396 ns de setup de entrada y +1,496 ns de salida. Son mínimos entre las
cuatro esquinas; no incluyen una reparación de las rutas de CPU pendientes.

### Cobertura y avisos

`check_timing` mantiene 3.713 elementos sin reloj, como en la referencia; no
detecta bucles ni latches. La cobertura de puertos sigue en 10 entradas y 52
salidas sin restricción, sin aumento frente a la referencia. Los avisos de
max-delay sin min-delay pasan de 13 a 16 por los nuevos payloads cuya exclusión
de hold es explícita. El Fitter conserva el mismo grupo de avisos 15003 de VRAM
con dos relojes y semántica de lectura durante escritura. Nada de ello se
considera resuelto por este cambio CDC.

## Recursos

| Recurso | Antes | Después | Disponible ahora |
|---|---:|---:|---:|
| ALM | 27.139 | 27.150 | 14.760 de 41.910 |
| Registros usados | 33.405 | 33.469 | — |
| LAB ocupados | 3.909 | 3.910 | **281 de 4.191** |
| Bloques RAM | 409 | 409 | 144 de 553 |
| Bits RAM | 3.240.923 | 3.240.923 | 2.421.797 |
| DSP | 39 | 39 | 73 de 112 |
| PLL | 3 | 3 | 3 de 6 |

El cambio cuesta 11 ALM, 64 registros y un LAB. La ocupación de LAB es 93,3 %;
los ALM libres no equivalen a capacidad de colocación contigua disponible.

## RBF e informes

- Binario para pruebas: `output_files/PCAT-286.rbf`.
- Generado el 24/09/2026 a las **19:18:24, Europe/Madrid**; 4.011.692 bytes.
- SHA-256: `8BC84CE4A5F57D5CD012FCA155B24C2B8554799FDC3E4767A6F1F216061560CC`.
- Copia congelada del fit y sus fuentes:
  `build/at-cdc-avalon/20260924-candidate/work/`.
- Análisis específico: `build/at-cdc-avalon/20260924-candidate/focused/`.
- Análisis por dominios: `build/at-cdc-avalon/20260924-candidate/timing/`.
- Referencia: `build/at-cdc-avalon/20260924-reference/`.

`PCAT-286_GFX.RBF` es anterior a este fit; no corresponde al candidato analizado.
La prueba del RBF en placa sigue pendiente. No se ha modificado RTL ni SDC
después de esta compilación; la revisión sólo añade este resultado documental.
