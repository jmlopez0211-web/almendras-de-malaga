# Motor de búsqueda fotográfica v15.2 — control estricto de variante, derechos y WebP

## Correcciones
- Corregida una duplicación de claves en `CORE_TERMS`: algunas claves de almendra se sobrescribían con términos de contradicción (aceite/sal), anulando la identidad real del producto.
- Una candidata solo pasa al grupo descargable si el título o las etiquetas documentan la variante completa mediante `MATCH_GROUPS` y `STRICT_MATCH_GROUPS`.
- Los resultados con variante no especificada o contradictoria se registran como descartes; no se descargan para asignación.
- La descarga requiere licencia compatible con uso comercial, URL de licencia, autor/creador y página fuente. Se excluyen licencias no comerciales y sin obras derivadas.
- Las imágenes descargadas se normalizan con orientación EXIF, se limitan a 1800 px y se convierten a WebP calidad 84. Se registran hash y tamaño de origen, dimensiones y tamaño optimizado, licencia, autor y fuente.
- El manifiesto conserva la procedencia y el estado `DOWNLOADED_UNVERIFIED`; la conversión no implica aprobación visual ni comercial.
- Incrementada `ENGINE_VERSION` a 15.2 para invalidar marcas de reintento antiguas.

## Criterio de aprobación
La descarga automática solo produce una candidata. La aprobación final sigue requiriendo revisión visual humana y metadatos de derechos completos mediante `approval_passes_gates`. Ninguna modificación automática de `data/catalog.js` ni publicación está habilitada.

## Verificación
- `python3 -m py_compile scripts/catalog_candidate_batch.py`
- `python3 -m unittest discover -s tests -v` — 80 pruebas OK.
- Prueba de puerta estricta: variante no documentada, licencia no comercial, autor ausente o fuente ausente bloquean la descarga.
- Prueba de diccionario: `CORE_TERMS` no contiene claves duplicadas.
