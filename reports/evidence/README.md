# Evidencias de ejecución

Los runs de la aceptación vigente están enumerados en `../acceptance.json`; incluyen tres ejecuciones reales y la demo sintética. Cada carpeta preserva manifiesto, eventos y resultados dbt originales. También pueden conservarse validaciones anteriores como historial de desarrollo, con sus propios Git SHA y fechas; no son ejecuciones adicionales independientes para aumentar el conteo de pruebas.

`../benchmark-initial.json` distingue una medición exploratoria anterior al congelamiento del código. `../tests.xml` corresponde a la suite final de 29 pruebas; no sumar los casos repetidos de `integration.xml` como si fueran pruebas nuevas. Los datos crudos, credenciales, cachés de dependencias y cluster PostgreSQL no forman parte de estas evidencias versionadas.
