# Incidente simulado — caída antes de publicar

**Es una inyección de fallo de laboratorio**, no un incidente de una empresa real. Entrada: fixture original CC0, 10.000 filas, semilla 2026, namespace `retail_synthetic`.

## Detección e impacto

`faro demo` publica una primera versión, crea otro candidato, carga/reutiliza staging, ejecuta dbt y reconciliación, y lanza el failpoint `before-publish`. Se registra `failed` en el historial y un evento seguro; no se cambia el puntero. El script consulta el head y comprueba que sigue siendo el primer run.

El impacto demostrado es la indisponibilidad del candidato, con continuidad del snapshot anterior. No se mide disponibilidad 24/7, usuarios afectados o pérdidas económicas. El fallo ocurre antes de la transacción de publicación; los tests también cubren una caída después de staging.

## Recuperación

Se llama `run --resume` con el mismo ID. La ingesta no duplica filas porque source_rows es inmutable y tiene PK; dbt reconstruye el candidato y se vuelven a ejecutar gates. Si nadie publicó entretanto, la transacción cambia el head y vistas. Se compara hash canónico del resultado con el primer rebuild y después con backfill; deben coincidir.

IDs y aserciones medidos se encuentran en `reports/demo.json` y en `reports/acceptance.json`. Los eventos originales están en `reports/evidence/`; un run recuperado vuelve a estado `published`, pero el evento de fallo permanece para auditoría y el reporte conserva su motivo.

## Prevención y límites

Snapshots separados, cambio atómico del head, comprobación optimista de concurrencia y pruebas de replay previenen publicación parcial/doble carga en este contrato. Los tests de pérdida de fila y alteración monetaria demuestran que una cifra incorrecta bloquea la publicación aunque dbt haya terminado.

No se simuló un corte físico de energía o corrupción del disco. PostgreSQL proporciona sus garantías transaccionales; la suite verifica el uso que hace el proyecto de ellas, no certifica el hardware ni reemplaza una estrategia de backup. Una restauración externa de backup sigue siendo una comprobación operativa pendiente antes de producción.
