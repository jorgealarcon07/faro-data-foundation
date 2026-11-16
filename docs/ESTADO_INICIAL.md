# Revisión previa al desarrollo

16-11-2026, antes de escribir código del proyecto. Se leyeron la investigación, el plan y PROYECTO_01; se consultó de nuevo la [API pública de GitHub](https://api.github.com/users/jorgealarcon07/repos?per_page=100).

La API devolvió `jorgealarcon07`, `QuantFinanceResearch` y el fork `roadmap-retos-programacion`, sin repositorio Faro público. Los dos primeros conservaban `updated_at` de octubre de 2024; no se interpreta esa marca como fecha exacta de toda actividad personal. No se modificó ninguno de esos repositorios.

En el workspace solo estaban las especificaciones y archivos de investigación/validación. La búsqueda de proyectos en Documents/Codex no encontró una implementación Faro; encontró un repositorio de otra tarea, que se dejó intacto. No había estándares de ingeniería ni repositorio Git para este proyecto. No se inspeccionaron ni modificaron fuentes privadas fuera del alcance.

Se creó ESTANDARES_INGENIERIA.md antes del primer código y se registró como primer commit local `ab8f6b4`. El nuevo repo está aislado en `outputs/faro-data-foundation`, sin remoto ni push. Solo se implementó el proyecto 01. La narrativa, namespaces, stack y distinción de fuentes siguen el plan; los nombres definitivos de los contratos están documentados en CONTRATOS.md.

Entorno: Windows 11, Python 3.12; sin Docker ejecutable o WSL instalado. La validación Appx de Power BI no pudo realizarse por permisos y no se contó con una instancia Desktop para abrir/refrescar el reporte. Se eligió una alternativa nativa con PostgreSQL real y consumidor HTML, conservando adaptadores Docker/Airflow y PBIP editables con límites declarados.
