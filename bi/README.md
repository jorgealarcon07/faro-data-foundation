# Consumo Power BI

Se entrega `Faro.pbip`, reporte PBIR de dos páginas, siete visuales y un modelo `model.bim` con seis medidas DAX. Se genera con `python bi/build_powerbi.py --data-dir <directorio-con-activity.csv-y-quality.csv>`.

1. Ejecutar el pipeline y `faro report --namespace retail_uk_reference`.
2. Regenerar PBIP con la ruta real de `reports/latest/retail_uk_reference`.
3. Abrir `bi/Faro.pbip` en Power BI Desktop compatible con PBIP/PBIR. Si hace falta, habilitar estas funciones en las opciones de Desktop.
4. Revisar el parámetro M `DataDirectory` y refrescar las dos tablas.
5. Contrastar filas y medidas con CSV/SQL; los valores visuales se redondean y no sustituyen NUMERIC como referencia monetaria.

Actividad: filas, ventas elegibles, tendencia y clases. Calidad: filas sin cliente, cuarentena y estado diario. No se carga un hecho completo de un millón de filas en el reporte para mostrar solo agregados.

**Comprobado:** 14 archivos JSON validados contra esquemas oficiales Microsoft y referencias de campos/medidas verificadas con `python bi/validate_powerbi.py`; ver `reports/powerbi-validation.json`. **No comprobado:** apertura y refresh en Desktop; la aplicación no estaba disponible para esa validación en el entorno. No hay PBIX exportado. El HTML real ejecutado y las exportaciones cubren el consumo funcional mientras esa prueba de integración de escritorio queda pendiente.

Documentación: [PBIP](https://learn.microsoft.com/en-us/power-bi/developer/projects/projects-overview), [formato de reportes PBIR](https://learn.microsoft.com/en-us/power-bi/developer/projects/projects-report), [esquemas Microsoft](https://github.com/microsoft/json-schemas). El código generado no incluye licencia de Desktop, credenciales, un tenant o un servicio publicado.
