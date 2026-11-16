# Cumplimiento de ESTANDARES_INGENIERIA.md

Revisión final 16-11-2026. Los estándares se crearon antes del código y fueron el primer commit. Esta tabla distingue ejecución verificada de configuración o trabajo pendiente.

| Práctica | Implementación y comprobación | Estado |
|---|---|---|
| Arquitectura/SOLID útil | Módulos con responsabilidades; configuración inmutable; sin jerarquías vacías. ADR en ARQUITECTURA.md | Revisado |
| Organización/mantenibilidad | Paquete src, CLI, SQL/dbt, tests y scripts. Ruff sobre todo el repo | Verificado |
| Dependencias | Python 3.12 aislado, pyproject + 75 entradas fijadas en lock; `pip check` | Verificado en Windows; instalación Linux pendiente de CI |
| Configuración/secretos | `.env` generado e ignorado; env no evalúa shell; no DSN/password en manifiestos; escaneo de archivos versionados | Verificado dentro del alcance del scanner |
| Contratos | JSON Schema del manifiesto ejecutado por run; hashes en lock; tipado/restricciones y tests para filas | Verificado |
| Permisos de datos | Ficha UCI y CC BY 4.0 revisadas; hashes ZIP/XLSX; NOTICE; derivados con atribución; fixture original CC0 | Verificado |
| Ingesta/almacenamiento | Ambas hojas, Parquet por lotes, COPY PostgreSQL real y PK de identidad | Ejecutado sobre 1.067.371 filas |
| Calidad/modelado | 11 tests dbt/build + baseline independiente por fecha/clase y controles de publicación | Verificado, 1.798 grupos |
| Reproducibilidad | Git/code/contract/source/data hashes, versiones y semillas; rebuild/replay/backfill | Mismo hash real en las tres ejecuciones finales |
| Recuperación | Candidato separado, locks, head guard, transacción, crash/replay y corrupción sembrada | Pruebas correctas |
| Pruebas | 18 unitarias + 12 integración/aceptación, sin sustituir PostgreSQL o dbt | 28 correctas; JUnit guardado |
| CI | Workflow Linux/PostgreSQL y smoke Airflow; mismos comandos de QA | Configurado, remoto no ejecutado |
| Seguridad | SQL parametrizado, nombres validados, ZIP limitado, loopback, escape JSON/DOM, fuentes fuera de Git | Casos y revisión local; no certificación productiva |
| Observabilidad | Eventos JSON, historial SQL, tiempos/filas/RSS, error seguro y manifests | Evidencia guardada; sin monitor 24/7 |
| Consumo | HTML offline, filtro/pestañas, CSV/JSON; cuatro capturas sin errores JS | Verificado |
| Power BI | PBIP/PBIR, M y DAX; 14 JSON y bindings validados | Desktop apertura/refresh pendiente |
| Airflow | Cinco tareas sobre operaciones reales; cinco fases nativas probadas | Scheduler/import Linux pendiente |
| Despliegue local | PostgreSQL nativo sin servicio del sistema, runner acotado y fetch con hash | Verificado |
| Contenedores | Dockerfile, Compose, imagen Airflow y dependencias separadas | No ejecutados en este host |
| Mantenimiento | Runbook, backup/retención/rollback documentados, limpieza no destructiva | Guía completada; restore externo pendiente |
| Documentación | README, arquitectura, fuentes, diccionario, contratos, caso y resultados | Completado |
| Git/alcance | Repo local aislado, commits por responsabilidad, sin push, sin proyecto 02 | Verificado |

Las verificaciones de Docker, scheduler y Desktop no bloquean la funcionalidad local probada, pero impiden afirmar que esos runtimes fueron validados. No hay modelos ML, scoring o pruebas anti-fuga porque este proyecto no contiene ML. No se añadieron herramientas equivalentes para aparentar más cobertura.
