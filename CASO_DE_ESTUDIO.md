# Faro — Una cifra publicada debe poder explicarse

**Proyecto 01 · Data Engineering · 16-11-2026.** Laboratorio de una empresa ficticia de software para operaciones financieras. No es experiencia laboral atribuida a un cliente real.

## Problema

Un extracto de facturación puede mezclar ventas, cancelaciones y códigos de ajuste. Un total que parece razonable puede perder filas o duplicarse durante reintentos. El responsable financiero necesita saber si una publicación puede usarse, qué excepciones contiene y cómo recuperarla sin sobrescribir la última versión confiable.

La necesidad de calidad y trazabilidad tiene un antecedente reciente en el [informe de supervisión del BCE de 2025](https://www.bankingsupervision.europa.eu/press/other-publications/annual-report/html/ssm.ar2025~6ee989dc7e.en.html). Se toma como evidencia del tipo de problema, no como una estadística sobre este comercio o Colombia.

## Solución construida

Pipeline de archivo a publicación con Python, Parquet, PostgreSQL y dbt. Lee por lotes, conserva cada fila y clasifica actividad comercial, cancelaciones, ajustes y cuarentena. Una implementación independiente en Python/Decimal vuelve a leer el original y contrasta agregados con SQL. Solo después de tests y reconciliación se cambia, en una transacción, el snapshot que ven los consumidores.

El producto incluye CLI, historial y logs, reanudación, backfill, un reporte HTML autónomo con dos vistas, CSV/JSON y un proyecto editable de Power BI. Un adaptador Airflow define cinco tareas con reintentos; las mismas fases se comprobaron con el ejecutor nativo ante la ausencia de un entorno Linux de contenedores.

## Decisiones de ingeniería

- **PostgreSQL real como único motor.** La limitación de Docker del host se resolvió con binarios nativos aislados, sin sustituir SQL por una maqueta.
- **Identidad de origen, no deduplicación por contenido.** Dos líneas iguales pueden ser legítimas; hoja y fila permiten rastrearlas.
- **Dinero en Decimal/NUMERIC.** Los importes no interpretables se conservan como desconocidos, nunca como cero para que el control pase.
- **Snapshot candidato separado.** Se sacrifica disco frente a un diseño más complejo para ganar publicación consistente y recuperación verificable.
- **Backfill sobre la misma versión.** Se reconstruye el intervalo elegido y se conservan las demás filas; una corrección de archivo exige rebuild.
- **Herramientas por responsabilidad.** dbt para modelos/tests, Python para adaptación/oráculo, SQL para persistencia, HTML para revisión portable. Sin broker, Kubernetes o ML sin necesidad.

## Evidencias obtenidas

La fuente pública histórica [UCI Online Retail II](https://archive.ics.uci.edu/dataset/502/online+retail+ii), Chen, [DOI 10.24432/C5CG6D](https://doi.org/10.24432/C5CG6D), se usó con atribución CC BY 4.0 y hashes aprobados. Se procesaron **1.067.371 filas de dos hojas**, sin perder registros. Rebuild, replay y backfill generaron el mismo hash canónico.

La validación final pasó **30 pruebas pytest**, **11 tests dbt por build** y comparación de **1.798 grupos** con el baseline independiente. Rebuild final con fuente ya cargada: 30,96 s; replay: 29,50 s; backfill de una semana: 20,51 s. No son condiciones de ingesta fría ni percentiles; el costo de primera lectura/carga se documenta por separado.

El resultado se publicó como **provisional** por 243.007 filas sin cliente. No se inventaron identificadores para presentar una calidad perfecta. Los fallos de la demo sintética conservaron el head anterior y pudieron recuperarse con el mismo resultado. La interfaz fue probada en un navegador y se guardaron cuatro capturas.

Enlaces para auditar: [aceptación](reports/acceptance.json), [tests](reports/tests.xml), [resultados y condiciones](docs/RESULTADOS.md), [incidente simulado](docs/INCIDENTE_SIMULADO.md), [reporte real guardado](reports/published/retail_uk_reference/index.html), [capturas](assets/web/README.md).

## Utilidad y límites

Se demuestra que un consumidor recibe cifras reconciliadas, puede rastrear una diferencia y mantiene una versión válida durante el fallo de un candidato. No se demuestran horas ahorradas, mayor recaudación o decisiones de usuarios reales. El dataset es británico y antiguo, sin pagos, costos ni vencimientos; sus importes no son caja ni ingreso contable.

Docker/Airflow y apertura/refresh de Power BI Desktop siguen pendientes de validación en un entorno compatible; no se disfrazan como ejecuciones exitosas. La ruta nativa y el HTML cubren la funcionalidad ejecutada. AWS/Spark quedaron fuera como extensiones opcionales. No se publicaron servicios, credenciales o cambios a tu perfil GitHub.

## Aprendizajes

Separar integridad técnica y semántica de negocio evita llamar «ingresos» a una suma de movimientos. Un estado provisional bien explicado aporta más que limpiar filas para obtener un check verde. La recuperación debe probarse junto con el pipeline y el oráculo necesita independencia respecto al SQL evaluado. Finalmente, la evidencia debe declarar cachés, hardware y herramientas no ejecutadas: una configuración correcta no equivale a una operación verificada.
