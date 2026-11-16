# Resultados medidos

Validación local del 16-11-2026. Evidencia principal: [acceptance.json](../reports/acceptance.json), [JUnit](../reports/tests.xml), [capturas y prueba UI](../reports/ui-validation.json). Código del núcleo verificado en commit `40288c44a44e96c234f8ed732d23452a918f2bbe`; hash de código `8cea02f4c59e8c621442c0124a957dd6b9ebaae290c40b7c157ffa85ffab617a`. Los commits posteriores agregan documentación/recursos y auxiliares de distribución, no cambian las reglas de transformación de esa ejecución.

## Datos y calidad observada

Ambas hojas completas: **1.067.371 filas**. Con las reglas declaradas: **1.035.621 ventas elegibles**, **22.951 cancelaciones/correcciones**, **8.799 ajustes**, **0 cuarentenas**. Hay **243.007 filas sin cliente**, aproximadamente 22,77%; por ello la publicación es `provisional`. Cero cuarentenas no significa que todos los datos sean perfectos ni que la regla de catálogo sea una verdad empresarial.

Se reconciliaron **1.798 grupos fecha/clase**, sus conteos, importes conocidos y desconocidos contra un baseline Python que vuelve a leer la fuente. Importe firmado conocido total: **GBP 19.287.250,568**, conservando la precisión de origen; no es caja, utilidad ni ingreso contable. Las medidas por clase están en [activity.csv](../reports/published/retail_uk_reference/activity.csv). El consumidor redondea para mostrar; los controles no usan ese redondeo.

## Ejecuciones de la versión verificada

| Ejecución | Run | Tiempo de pared | Filas / hash |
|---|---|---:|---|
| Rebuild con origen y baseline en caché | `5fc402baea4141778fabfa8419fc3585` | 30,96 s | 1.067.371 / mismo hash |
| Reejecución completa; baseline y origen en caché | `35aa250c28224b6cbb49ad229aa8b9e5` | 29,50 s | 1.067.371 / mismo hash |
| Backfill [2010-12-01, 2010-12-08) | `81ac4b09a2e44ee8826522fa9121e17b` | 20,51 s | 1.067.371 / mismo hash |

SHA-256 canónico de datos, sin metadatos de ejecución:

```text
2cda5344fa929f4a025ee85f6639a1d464eed2fcc4adf3e317263880786a53b6
```

Preparación en la validación final: 0,19 s con archivo/Parquet aprobados ya en caché. **No es el costo de la primera ingesta.** En la medición inicial exploratoria: adaptación completa a Parquet 46,90 s; lectura independiente del baseline 52,59 s; COPY de toda la fuente a PostgreSQL 28,43 s; pipeline inicial 112,11 s. Esta primera medición antecede al congelamiento de código y se conserva separada en [benchmark-initial.json](../reports/benchmark-initial.json). No se mezclan sus condiciones con las del replay final.

Pico de RSS de Python y subprocesos en las tres ejecuciones finales: aproximadamente **633,9 / 677,2 / 709,7 MiB**, por muestreo cada 0,1 s. No incluye el servidor PostgreSQL ni garantiza capturar picos instantáneos. Hardware disponible: 6 núcleos físicos, 12 lógicos y 16.227.487.744 bytes RAM; Windows 11, Python 3.12.14, PostgreSQL 17.12. Versiones y procedencia en [runtime.json](../reports/runtime.json).

Una observación por condición, cachés compartidas y sin aislamiento de carga de todo el equipo. No son percentiles, benchmark universal o garantía de SLA. El hecho de que este backfill sea más rápido no demuestra una mejora general para cualquier intervalo o volumen.

## Pruebas y fallos

**30 pruebas pytest correctas en 82,45 s:** 18 unitarias y 12 de integración/aceptación, con PostgreSQL y dbt reales. Cada build exitoso ejecutó **11 tests dbt**, además de gates Python independientes. Se verificaron:

- Duplicados de contenido conservados con identidades distintas; PK bloquea identidad repetida.
- Esquema incompatible, conversiones inválidas y ausencia de zona horaria inventada.
- Replay y backfill con mismo hash; reanudación de un run ya publicado idempotente.
- Fallos después de staging y antes de publicar, preservando head; posterior recuperación.
- Pérdida de fila y alteración de importe detectadas aunque dbt termine.
- Conflicto de publicación concurrente y rechazo de candidato sin validar.
- Cinco fases operativas del adaptador de orquestación ejecutadas nativamente.
- CLI de validación, exportaciones y parametrización SQL.

La demo final de **10.000 filas sintéticas** conserva la publicación anterior durante un fallo inyectado y produce el mismo hash al recuperar y hacer backfill. Los IDs están en [demo.json](../reports/demo.json). Son pruebas de laboratorio, no incidentes reales ni una tasa empírica de confiabilidad del servicio.

Interfaz: dos reportes en Chromium/Brave, filtros y pestañas correctos, **0 errores JavaScript**, cuatro capturas reales. PBIP: **14 JSON válidos** y referencias de campos/medidas coherentes; Desktop no abierto/refrescado. Lint Ruff, contratos y `pip check` pasaron. El escaneo de secretos tiene alcance limitado a patrones y archivos de entrega; no es una auditoría exhaustiva.

## Límites pendientes reales

- Docker y scheduler Airflow no ejecutados aquí: el host no dispone de Docker/WSL. Hay archivos y CI para esa validación, sin resultado remoto declarado.
- Power BI Desktop: apertura/refresh pendiente; el consumo HTML/CSV/JSON sí fue ejecutado.
- CI remoto no ejecutado: no se subió el repositorio.
- Restauración externa de backup, roles productivos, TLS, monitor 24/7 y alta disponibilidad no acreditados.
- AWS/Spark son extensiones opcionales, no implementadas. No hay proyectos 02–04 en desarrollo.

No se midieron ahorro de horas, ingresos, recuperación de cartera, adopción o decisiones de usuarios reales. La utilidad demostrada es técnica: una cifra se puede reconciliar, explicar y recuperar sin publicar un candidato inválido.
