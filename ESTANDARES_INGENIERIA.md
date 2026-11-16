# Estándares de ingeniería — Faro / proyecto 01

Fecha: 16-11-2026. Alcance: `faro-data-foundation`. Debe existir antes del primer código del proyecto. No autoriza implementar proyectos 02–04.

## Reglas y comprobación

| Área | Práctica aplicable | Cómo se comprueba |
|---|---|---|
| Arquitectura | Separar lectura/contratos, acceso a PostgreSQL, transformación dbt, publicación y consumo. Funciones pequeñas y objetos de configuración; interfaces solo cuando sustituyen una dependencia real. SOLID para responsabilidad e inversión de dependencias, sin jerarquías ceremoniales | Revisión de imports, ADR y tests con archivos/base real; la CLI no contiene reglas SQL |
| Código | Paquete `src/`, CLI explícita, SQL versionado, nombres de dominio y errores accionables. Ninguna lógica central solo en notebooks | Importación desde instalación limpia; Ruff y pytest |
| Dependencias | Entorno aislado, versiones fijadas y lock reproducible. No modificar Python global. PostgreSQL real; no SQLite o mocks como sustituto de integración | Registro de versiones, instalación con lock y tests sobre PostgreSQL |
| Configuración | Variables de entorno con defaults locales seguros, rutas del proyecto explícitas; configuración inválida falla antes de escribir | Tests de configuración; `.env.example` sin secretos |
| Secretos | Credenciales solo en entorno/archivo ignorado; no loggear DSN/password, no credenciales reales en ejemplos | Inspección de `git diff --cached`, escaneo de secretos y logs antes de commits |
| Contratos | JSON Schema versionado, hash del contrato, namespace y tipo de datos en toda ejecución. No cambiar grano o semántica silenciosamente | Validación de manifiesto, tests de contratos y lock de hashes |
| Datos y licencias | Fuente oficial, checksum obligatorio, atribución CC BY 4.0 y registro de cambios. Originales inmutables y fuera de Git. Fixture sintético claramente separado | Descarga/verificación de hash, inventario y NOTICE/DATA_SOURCES |
| Calidad | Partición exhaustiva de filas; dinero Decimal/NUMERIC; cliente desconocido explícito. Bloquear pérdida, duplicado de clave origen, esquema roto y descuadre | Oráculo Python independiente de SQL; tests dbt e inyección de fallos |
| Reproducibilidad | Semillas para fixtures, `run_id`, Git SHA, hashes, versiones, configuración e intervalo. Horas originales sin zona inventada | Segunda ejecución y comparación rebuild/backfill; manifiestos guardados |
| Pipeline | Intervalos `[inicio, fin)`, reintentos idempotentes, staging aislado, candidato separado y cambio de publicación en transacción. Fallos preservan versión anterior | Pruebas crash/replay, bloqueo, concurrencia y backfill en base real |
| Pruebas | Unitarias de conversión/reglas; integración PostgreSQL+dbt; E2E CLI sobre fixture y fuente completa para release. No confundir tests sintéticos con validación de negocio real | JUnit/resultados reales y aceptación por caso; no afirmar cobertura no medida |
| CI | Lint, contratos, unitarias, integración sobre servicio PostgreSQL y smoke del DAG en Linux. Mismos comandos que local | Workflow revisable; distinguir ejecución local verificada de CI remoto aún no ejecutado |
| Seguridad | SQL parametrizado/identificadores seguros, extracción ZIP sin traversal, límites y timeouts, HTML escapado, servicios loopback por defecto, usuario no root en imagen | Casos adversos, revisión de configuración, escaneo y permisos de consumo separados |
| Observabilidad | Logs JSON con run/etapa/duración/error sin datos sensibles; estados y métricas de calidad, conteos de descarte y motivos | Logs y reportes de casos buenos/malos; consulta de historial y manifiesto |
| Consumo | Reporte funcional con métricas definidas, origen y limitaciones; exportaciones verificables y dos vistas de actividad/calidad | E2E genera HTML/CSV/JSON; contraste con datos SQL; capturas del resultado real |
| Despliegue | Docker Compose para PostgreSQL/app y perfil Airflow; alternativa nativa reproducible si Docker no está disponible. No publicar servicios externos | Smoke ejecutable y evidencia del entorno utilizado; limitaciones exactas del entorno alternativo |
| Mantenimiento | Migraciones repetibles, runbook para restaurar/reabrir intervalos, limpieza confinada con confirmación explícita para datos | Tests de reejecución y guía de restauración; no borrar recursos ajenos |
| Documentación | README, arquitectura/ADR, diccionario, fuentes, caso de estudio y resultados medidos con comandos/fecha | Checklist de aceptación enlaza cada obligación con evidencia real |
| Git | Repo aislado, commits por cambio coherente, no push sin instrucción, no reset/borrado del trabajo previo | `git status`, historial y revisión de staged files |

## Criterio de cierre

El mínimo requiere datos reales de ambas hojas, Parquet, PostgreSQL, modelos y tests dbt, publicación recuperable, interfaz de consumo y ejecución medida. Airflow se implementa como adaptador de la misma lógica; si el host no soporta ejecutarlo, se intenta un entorno compatible y se documenta la comprobación que realmente pudo hacerse. Power BI debe tener un artefacto editable o una alternativa reproducible justificada si el programa no está disponible. Una configuración escrita no se reporta como ejecución validada.

Las extensiones AWS/Spark de la especificación son opcionales y no justifican retrasar el mínimo. No hay ML en este proyecto; no se añadirán modelos ni métricas predictivas.

El archivo `docs/CUMPLIMIENTO.md` del repositorio registrará al finalizar: requisito, implementación, comando/evidencia, resultado y pendiente real. Los resultados fallidos también se conservan. No se publicarán datos restringidos, credenciales ni resultados estimados como si estuvieran medidos.
