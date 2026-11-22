# Finalización de búsqueda fotográfica del catálogo

## Flujo

El workflow **Catalog image candidate search** se ejecuta manualmente desde GitHub Actions. Procesa un lote pequeño de productos sin modificar `data/catalog.js` ni activar `imageVerified`.

1. Buscar en Wikimedia Commons y Openverse con consultas específicas por producto y variante.
2. Filtrar candidatos por ingrediente y preparación cuando estos datos aparecen en el título o tags.
3. Descargar únicamente archivos que superen validación binaria, MIME, formato y resolución.
4. Subir los candidatos como artefacto temporal de GitHub Actions (14 días).
5. Inspección visual individual, comprobación de licencia y atribución.
6. Solo después de aprobación, incorporar el binario y los metadatos a la ficha.

## Batches recomendados

El catálogo tiene 61 productos sin imagen según el último informe. Ejecutar lotes de 8:

- Inicio 0
- Inicio 8
- Inicio 16
- Inicio 24
- Inicio 32
- Inicio 40
- Inicio 48
- Inicio 56

Mantener una pausa de 2,5 segundos entre consultas. Si Commons responde HTTP 429, el motor aplica cooldown/fallback y no debe forzarse la fuente.

## Importante

- Un candidato descargado **no está aprobado**.
- La fotografía debe coincidir con el producto y su variante.
- No aprobar imágenes de envases, etiquetas, marcas, anuncios o productos mezclados que no correspondan.
- No inferir sal, aceite, azúcar o ingredientes invisibles solo a partir de la fotografía.
- Las marcas comerciales (Pictolín, Werther's, etc.) requieren especial cuidado: una foto genérica de un caramelo no representa necesariamente el producto vendido.
- Las mezclas con nombres propios no pueden certificarse mediante una foto genérica de frutos secos.
- El workflow no modifica el catálogo ni despliega imágenes automáticamente.
