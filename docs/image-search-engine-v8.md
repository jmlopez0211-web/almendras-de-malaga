# Motor de búsqueda de imágenes v8 — descargas resilientes

## Cambios
- Reintentos limitados de descarga para fallos de red, HTTP 429 y HTTP 5xx.
- Respeta Retry-After cuando es válido y aplica espera progresiva.
- Prueba URL original y miniatura por separado.
- Cabeceras de descarga con Accept de imagen, User-Agent y Referer cuando la fuente lo proporciona.
- Rechaza respuestas cuyo Content-Type indique que no son imágenes.
- Verifica el archivo con Pillow, formato permitido y resolución mínima de 900 × 700.
- Limita descargas a 25 MB.
- Escribe candidatos mediante archivo temporal y reemplazo atómico.
- Guarda URL final, errores de URL, dimensiones, formato, Content-Type y SHA-256.
- No aprueba ni incorpora fotografías automáticamente; el catálogo permanece intacto.

## Diagnóstico
```bash
python scripts/catalog_candidate_batch.py --diagnose
```

## Reintentar descargas fallidas
```bash
python scripts/catalog_candidate_batch.py --resume --limit 8 --delay 2
```

## Volver a buscar productos sin candidatos relevantes
```bash
python scripts/catalog_candidate_batch.py --resume --retry-no-candidates --limit 8 --delay 2
```

## Estados
- `DOWNLOADED_UNVERIFIED`: archivo descargado y validado técnicamente; falta revisión visual, licencia y coincidencia exacta.
- `CANDIDATES_FOUND_DOWNLOAD_FAILED`: se encontraron candidatos pero no se pudo descargar ninguno.
- `NO_RESULTS_RELEVANT`: las fuentes respondieron, pero ningún candidato superó los filtros.
- `PARTIAL_SOURCE_FAILURE`: una fuente respondió y otra falló.
- `SOURCE_ERROR`: ninguna fuente respondió correctamente.

La aprobación final sigue siendo manual. No se infiere sal, aceite, azúcar ni una variante invisible de la fotografía.
