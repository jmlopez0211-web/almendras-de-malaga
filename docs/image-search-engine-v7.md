# Motor de búsqueda de imágenes v7 — diagnóstico y resiliencia

## Qué cambia

- Reintentos limitados para errores de red, HTTP 5xx y HTTP 429.
- Backoff exponencial y respeto de `Retry-After` cuando es numérico.
- Cabeceras `Accept` y `Accept-Language` además de User-Agent.
- El diagnóstico `--diagnose` muestra fuente, error HTTP o excepción de red completa.
- Cada producto imprime los errores de fuentes en consola; ya no quedan ocultos dentro del JSON.
- Se distingue `SOURCE_ERROR` (ninguna fuente respondió) de `PARTIAL_SOURCE_FAILURE` (una fuente falló y otra sí respondió) y `NO_RESULTS_RELEVANT` (fuentes disponibles, pero sin candidato que supere filtros).
- Una respuesta válida de Commons cuenta como fuente disponible aunque no haya resultados o no se obtengan metadatos de archivo.

## Diagnóstico Termux

Desde la raíz del repo:

```bash
python scripts/catalog_candidate_batch.py --diagnose
```

## Reintentar productos con errores

```bash
python scripts/catalog_candidate_batch.py --resume --retry-no-candidates --limit 8 --delay 2
```

## Interpretación

- `NETWORK_ERROR`: DNS, TLS, timeout, conexión o acceso a internet.
- `SOURCE_BLOCKED`: HTTP 401/403.
- `RATE_LIMITED`: HTTP 429.
- `HTTP_ERROR`: otro HTTP no exitoso.
- `BAD_JSON`: la fuente no devolvió JSON válido.
- `PARTIAL_SOURCE_FAILURE`: el motor pudo consultar una fuente, pero otra falló.
- `NO_RESULTS_RELEVANT`: consulta exitosa sin candidatos que cumplan los filtros.

El motor no aprueba ni incorpora imágenes. El catálogo permanece intacto.
