# Operación, recuperación y mantenimiento

## Configuración

Usar `.env` local o variables `FARO_DB_HOST/PORT/NAME/USER/PASSWORD`, `FARO_HOME` y `FARO_BATCH_SIZE` (100–100.000; default 20.000). Una contraseña vacía se rechaza. `.env.example` no contiene secretos. El script nativo genera una contraseña; no imprimirla, copiarla al README o guardarla en logs. La CLI carga solo claves FARO_/DBT_ y no ejecuta el contenido de `.env` como shell.

La cuenta de laboratorio es propietaria y puede crear esquemas. Producción exige un usuario de ejecución con privilegios controlados y otro de consumo con USAGE en `faro` y SELECT únicamente en `current_*`; no dar acceso a source_rows, candidatos o credenciales del escritor a un servicio público. Este endurecimiento no se presenta como realizado en producción.

## Flujo y observabilidad

Comenzar por `faro init-db`, `faro fixture`/`faro download` y `faro run`. En `reports/runs/<id>/`: logs JSON, log dbt, artefactos dbt y manifiesto. En PostgreSQL: `faro.runs`, `faro.events`, `faro.publications`. No se escribe la contraseña/DSN en los eventos. Las salidas `ready/provisional` son calidad de una publicación válida; `failed` en run significa candidato no publicable, no eliminación de la publicación anterior.

El manifiesto guarda Git SHA, hash del código, contratos, dataset y tabla canónica; versiones de paquetes; conteos; importes; duración y pico aproximado de RSS de Python+subprocesos. El RSS no incluye el servidor PostgreSQL separado. El tiempo de preparación se mide aparte del pipeline. Los benchmarks dependen de cachés, disco, hardware y estado de la base.

No se mide frescura del negocio: el origen no da hora de llegada real. El intervalo es histórico y la publicación tiene hora UTC de laboratorio. El SLO práctico medido es duración de procesamiento tras disponer del archivo, no demora desde una venta de 2011. No etiquetar los datos históricos como un incidente de latencia actual.

## Incidente: falla de staging o dbt

1. Leer el error seguro en events y el log dbt del run. No compartir logs que alguien haya enriquecido con secretos.
2. Comprobar que `faro.publications` todavía señala el run anterior.
3. Corregir disponibilidad/configuración; `faro run --resume <id>` retoma el mismo candidato sin duplicar source_rows.
4. Si otro run publicó, el head guard rechaza la escritura antigua. Crear un nuevo run desde la fuente aprobada.
5. No editar un snapshot publicado para arreglar un reporte. Corregir reglas, probar y publicar un nuevo run.

Para reproducir el fallo acotado: `faro run --input data/fixtures/synthetic.xlsx --failpoint before-publish`. Está rotulado como inyección; no usarlo en una tarea programada normal. La demo ya prueba esta ruta y compara el head antes/después.

## Fuente o calidad incompatible

Checksum distinto: conservar el archivo, revisar proveedor/licencia/esquema y aprobar nueva versión mediante PR; no desactivar la validación. Esquema roto: falla la adaptación antes del warehouse. Parquet corrupto: se reconstruye desde el XLSX aprobado. PK duplicada: la transacción de carga se revierte. Descuadre del baseline o tests: no publicar ni «corregir» a mano el total de referencia.

Clientes desconocidos no se inventan ni descartan: generan publicación provisional y conteo. Cuarentena mantiene importes calculables y cantidades desconocidas; no reemplazar ausencias monetarias por cero. El baseline caché se invalida al cambiar su código o el del adaptador; cambiar reglas requiere revisar ambos implementadores y contratos.

## Backfill y evolución

Pasar `--start YYYY-MM-DD --end YYYY-MM-DD`; seleccionar límites antes de ejecutar. La fuente debe ser la misma que la publicación previa. Cada candidato materializa snapshot completo; se preserva todo lo no incluido en el intervalo. Correcciones de archivo o fechas nulas requieren rebuild. Cambios de grano o contrato deben versionarse; campos de contratos están documentados en `docs/CONTRATOS.md`.

## Backup, rollback y retención

Conservar ZIP aprobado + checksum, contratos, código, manifests y backup PostgreSQL. `pg_dump` debe ejecutarse contra la base configurada con credenciales por entorno, no contraseña en command line. Para restaurar, usar una base nueva, cargar backup, ejecutar `faro validate` y generar un reporte; este procedimiento está documentado pero no se ensayó una restauración externa en esta entrega.

La interfaz no ofrece rollback ciego: volver a procesar una versión aprobada produce una nueva publicación validada. Los snapshots anteriores se retienen para auditoría. No hay limpieza automática de datos en esta versión. `faro clean` no borra fuentes, snapshots o volúmenes. Antes de purgar un esquema retirado, verificar que nunca sea el head, tener backup y revisar la lista concreta; no ejecutar eliminaciones recursivas sobre rutas calculadas.

## Entorno nativo y contenedores

`scripts/verify_native.py` arranca/detiene solo `.runtime/pgdata` del proyecto. El ejecutable PostgreSQL se recibe con `--bin`; no busca ni detiene servicios del sistema. En el sandbox necesita clientes en esa misma invocación. Fuera de él, `native_postgres.py start/stop` sirve para una sesión local persistente.

Docker usa bind mounts `data` y `reports`. En Linux, crear esas carpetas y usar un UID con permisos de escritura para el usuario del contenedor; ajustar `user` de app/Airflow de forma coherente con el propietario y GID 0 para la imagen Airflow. No abrir permisos globales ni ejecutar el pipeline como root por conveniencia. Esta ruta debe validarse en el host Linux antes de declarar despliegue verificado.

Actualizaciones: pin por PR, instalación limpia, `pip check`, pruebas completas, comparación de hashes y nueva medición. No habilitar dependencias emergentes sin una necesidad concreta. La salida actual es local; no hay servicio externo desplegado ni monitor 24/7.
