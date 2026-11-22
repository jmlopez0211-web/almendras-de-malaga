# Motor de imágenes v14 — recuperación amplia y diagnóstico de descartes

## Problema observado en Termux
La v13 conectaba correctamente con Wikimedia Commons y Openverse, pero el bloque de ocho frutos secos terminaba con 8/8 `NO_RESULTS_RELEVANT`. Las consultas estaban dominadas por frases largas que incluyen simultáneamente preparación, sal y aceite. Los buscadores pueden interpretar esas frases como condiciones AND y devolver cero resultados aunque existan fotografías genéricas del alimento.

## Cambios de búsqueda
- Añade una primera fase de consultas cortas por identidad visual: almonds, almond kernels, blanched peanuts, roasted peanuts, cashew nuts y macadamia nuts.
- Conserva después las consultas específicas por preparación y variante.
- Limita a seis consultas distintas por producto para controlar la carga.
- Amplía Wikimedia Commons de 10 a 30 resultados por consulta.
- Amplía Openverse de 20 a 30 resultados por consulta.
- Sigue aplicando el filtro de identidad, las contradicciones explícitas y los falsos positivos de contexto antes de seleccionar cualquier descarga.
- Intenta reunir hasta cuatro candidatos antes de dejar de consultar una fuente; así no se detiene por un único resultado mediocre.

## Diagnóstico nuevo por producto
El informe de cada producto añade:
- `search_audit.queries`: fuente, término consultado, número bruto de resultados y error.
- `search_audit.raw_candidates`: cantidad de resultados recibidos.
- `search_audit.accepted_candidates`: candidatos que superan el filtro.
- `search_audit.rejection_reasons`: causas concretas de descarte.
- `search_audit.rejected_samples`: títulos y motivos de hasta veinte candidatos rechazados.

Termux imprime un resumen de consultas, candidatos brutos, aceptados y motivos de descarte. Esto permite distinguir:
1. La API no devuelve imágenes para las consultas.
2. La API sí devuelve imágenes, pero los títulos no contienen identidad suficiente.
3. El filtro descarta falsos positivos por variante o contexto.

## Seguridad
- No se reduce el umbral de relevancia.
- No se relajan las contradicciones explícitas, especialmente sal/aceite.
- No se aprueban candidatos automáticamente.
- No se modifica `data/catalog.js`, las URL de imágenes publicadas ni `imageVerified`.
- Toda fotografía continúa pendiente de inspección visual, atribución y licencia.
