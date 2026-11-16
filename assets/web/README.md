# Recursos para una futura web

Capturas del reporte real ejecutado en Chromium/Brave, no mockups ni imágenes generadas:

- `real-activity.png`: conteos e importes sobre toda la fuente pública histórica.
- `real-quality.png`: razones, calidad y trazabilidad del mismo snapshot.
- `synthetic-activity.png` y `synthetic-quality.png`: fixture e incidentes rotulados.
- `case-study.json`: ficha estructurada de esta entrega, con métricas y límites.

Reproducir: `python scripts/capture_report.py --browser <ruta-exe-Chromium>` o instalar Chromium de Playwright y omitir el parámetro. El script prueba filtro de clasificación y cambio de vista antes de capturar; registra errores JavaScript y evidencia en `reports/ui-validation.json`.

Para publicar imágenes derivadas del dato real, conservar atribución a Chen/UCI, DOI 10.24432/C5CG6D y CC BY 4.0, e indicar agregaciones/normalización. Ver NOTICE y DATA_SOURCES.md. El fixture original es CC0. No publicar una cifra de negocio como impacto conseguido ni describir Faro como empleador real.

No se construyó o publicó una web; estos recursos quedan listos para esa fase posterior.
