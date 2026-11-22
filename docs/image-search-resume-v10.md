# Reanudación de lotes del motor fotográfico v10

## Problema anterior
El modo `--resume --retry-no-candidates` podía volver a seleccionar los mismos productos sin resultados en cada ejecución. Los fallos de descarga persistentes también podían ocupar repetidamente los primeros puestos del lote e impedir avanzar al resto del catálogo.

## Comportamiento nuevo
- Cada producto pendiente, fallido o sin candidato relevante se reintenta una vez por versión del motor.
- La versión del último reintento queda registrada en `docs/candidate_batch_state.json`.
- Una nueva versión del motor habilita un nuevo intento de productos previos.
- Los candidatos ya descargados siguen fuera del flujo normal; para volver a examinarlos se usa `--recheck-downloaded`.
- `--force-retry` permite forzar otra ejecución de estados fallidos aunque ya se hayan intentado con esa versión.
- Los productos que se quedan sin resultados ya no bloquean la cola al repetir `--resume`.

## Comandos

Actualizar:
```bash
git pull --ff-only origin main
python -m py_compile scripts/catalog_candidate_batch.py
```

Procesar el siguiente bloque de errores y búsquedas vacías una sola vez:
```bash
python scripts/catalog_candidate_batch.py --resume --retry-no-candidates --limit 8 --delay 2.5
```

Revisar también candidatos descargados anteriormente:
```bash
python scripts/catalog_candidate_batch.py --resume --retry-no-candidates --recheck-downloaded --limit 8 --delay 2.5
```

Forzar un nuevo intento tras corregir una fuente o conexión:
```bash
python scripts/catalog_candidate_batch.py --resume --retry-no-candidates --force-retry --limit 8 --delay 2.5
```

El catálogo y las aprobaciones no se modifican por ninguno de estos comandos.
