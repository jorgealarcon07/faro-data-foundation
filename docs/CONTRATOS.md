# Contratos y coherencia del portafolio

`contracts/v1` es la interfaz implementada 1.0.0; `contracts.lock.json` fija hashes. `scripts/check_contracts.py` detecta cambios sin revisión. El manifiesto se valida contra JSON Schema en cada run. `invoice_line` documenta la exportación tipada; PostgreSQL/dbt comprueban cada fila y sus reglas de dominio sin ejecutar un JSON Schema por millón de filas.

El diseño inicial usó nombres conceptuales `namespace` y `unit_price_decimal`. La interfaz implementada usa `source_namespace` y `unit_price` (NUMERIC en SQL; texto decimal al serializar). `event_local_time` no lleva UTC inventado. `customer_key` siempre existe; su miembro desconocido es explícito. Un dato no interpretable puede quedar nulo en cuarentena y debe conservar su texto de origen.

No hay consumidores de proyectos 02–04 implementados a los que se haya roto una interfaz. Cuando se desarrollen, deberán tomar esta versión o un adaptador explícito, manteniendo namespace, moneda y tipo de procedencia. No deben tratar `invoice_line` como cuentas por cobrar: faltan pagos/vencimientos.

Versiones menores: campos opcionales y documentación que no cambien significado. Versiones mayores: grano, clave, tipo, signos, moneda, reglas que cambien la interpretación contractual. Una actualización requiere revisar productor, fixtures, tests y hashes; un cambio intencional de clasificación debe generar nueva evidencia.
