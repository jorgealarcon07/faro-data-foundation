# Diccionario de datos y métricas

Contrato 1.0.0; hashes en `contracts.lock.json`. Namespace y `data_kind` acompañan las salidas. GBP, sin conversión. `event_local_time` es timestamp sin zona; `business_date` deriva de él, no de la hora de carga.

## Campos

| Campo | Semántica |
|---|---|
| `source_row_id` | SHA-256(checksum XLSX : hoja : fila); grano de origen |
| `invoice_id` | Texto de Invoice; no es único por línea |
| `product_key` | StockCode, puede contener ajustes o estar ausente |
| `customer_key` | Customer ID como texto; `__UNKNOWN__` si falta |
| `quantity` / `unit_price` | NUMERIC, nulos si no interpretables; textos originales en source_rows |
| `signed_amount` | Cantidad × precio si ambos son interpretables, incluso en cuarentena |
| `classification_reason` | Razón única; orden de evaluación debajo |
| `publication_run_id` | Snapshot expuesto por la vista; no forma parte del hash de datos |

Se aceptan decimales finitos de magnitud ≤10^15 y hasta 12 posiciones decimales. Valores fuera de ese contrato se conservan como texto y pasan a desconocidos/cuarentena. No se truncan ni redondean para lograr reconciliación. Cantidades no enteras son cuarentena, pero su importe se conserva si es calculable.

## Clasificación exclusiva y exhaustiva, en este orden

1. `quarantine / invalid_field`: falta factura/código, fecha inválida, cantidad no interpretable/no entera o precio no interpretable.
2. `cancellation / cancellation_or_correction`: prefijo C o cantidad negativa. No se infiere qué venta corrige.
3. `adjustment / non_merchandise_code`: código distinto del patrón conservador de 5 dígitos y sufijo opcional de letra. Regla de laboratorio, no catálogo oficial de mercancías.
4. `adjustment / zero_quantity`: cantidad cero.
5. `adjustment / non_positive_price`: precio cero/negativo; no se interpreta como fraude.
6. `sale / eligible_sale`: resto.

Un código comercial real fuera del patrón podría quedar como ajuste. El reporte conserva su razón y permite revisar la regla en una versión futura. Descripción o país faltante no invalida una línea. La dimensión de producto conserva cantidad de descripciones observadas y una muestra lexicográfica, no una historia temporal inventada.

## Medidas y gates

- Venta elegible: suma firmada filtrada por `sale`; cantidades y precios positivos por construcción.
- Cancelaciones/correcciones: suma firmada de `cancellation`; no asumir que siempre tiene signo negativo si ambos factores son negativos.
- Ajustes: suma conocida de `adjustment`; no sumar a ventas sin justificarlo.
- Cuarentena: número de filas `quarantine`; importe conocido calculable se muestra aparte.
- Desconocidos monetarios: cantidad de filas donde no se puede calcular importe; no entran como cero en una cifra publicada.
- Sin cliente: número de **filas**, no de clientes únicos, con clave desconocida. El porcentaje usa todas las filas de ese día.
- `ready`: reconciliación crítica correcta y sin cuarentena/desconocidos de cliente.
- `provisional`: gates críticos correctos, con excepciones visibles; no implica que puedan reportarse como definitivas.
- Publicación bloqueada: checksum/esquema/clave, discrepancia de conteo/importe, test dbt o conflicto de head. El candidato falla y no desplaza la versión anterior.

Filas entrada = venta + cancelación + ajuste + cuarentena. Importes comparables se reconcilian por fecha/clase con Decimal; los desconocidos también se comparan por conteo. Fecha inválida tiene un bucket nulo explícito, no desaparece del agregado.

El redondeo visual es a dos decimales, con convenciones del consumidor. Los importes exactos de control están en SQL/CSV/manifiesto. Ninguna medida representa saldo vencido, caja, beneficio o estados financieros certificados.
