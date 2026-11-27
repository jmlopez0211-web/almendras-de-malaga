# Motor de búsqueda fotográfica v15.1 — reparación de reentrada y reanudación

## Fallo de robustez corregido
La v15 guardaba el progreso al terminar cada producto, pero no persistía cuál estaba en curso. Si Termux/Python se interrumpía mientras buscaba y un lanzador externo volvía a iniciar `--resume`, el producto incompleto podía volver a ocupar el primer puesto y repetirse. Tampoco existía un bloqueo de proceso para impedir dos ejecuciones simultáneas del mismo motor.

## Cambios v15.1
- Bloqueo exclusivo del proceso mediante `fcntl.flock`; una segunda ejecución simultánea termina con código 2 y muestra el PID propietario, sin iniciar nuevas consultas. El sistema operativo libera el bloqueo cuando el proceso termina o se interrumpe.
- Checkpoint atómico `in_progress` escrito antes de cada producto.
- Si el proceso anterior se interrumpió, el siguiente arranque registra ese producto como `INTERRUPTED` y lo excluye de la reanudación normal para evitar repetirlo indefinidamente.
- La repetición deliberada requiere `--force-retry`; se conserva el resto de estados, filtros de identidad/variante y el bloqueo de aprobación humana/licencias.
- Se incrementa `ENGINE_VERSION` a 15.1 para separar las marcas de reintento de la versión anterior.

## Verificación
- `python -m py_compile scripts/catalog_candidate_batch.py`
- `python -m unittest discover -s tests -v`
- Prueba manual de reentrada: el proceso padre adquiere el bloqueo y el proceso hijo debe salir con código 2 antes de iniciar búsquedas.
- Prueba de reanudación: los productos interrumpidos se omiten por defecto y solo vuelven a cola con `--force-retry`.

El motor sigue siendo un buscador de candidatas: no modifica `data/catalog.js`, no aprueba fotografías y no publica imágenes automáticamente.

## Fuente local de Descargas

La v15.1 incorpora un modo de inventario local, independiente de las búsquedas remotas:

```bash
python3 scripts/catalog_candidate_batch.py --index-local-photos
```

La opción `--local-root RUTA` permite indicar otra carpeta de Descargas. El inventario recoge las colecciones locales de Almendras de Málaga, calcula SHA-256, registra dimensiones, formato, duplicados y metadatos de los manifiestos disponibles. El resultado se guarda en `docs/local_photo_inventory.json` (archivo local ignorado por Git, porque contiene rutas absolutas del dispositivo).

Este modo no copia ni publica archivos, no asigna fotografías a fichas y no considera que una sugerencia del manifiesto demuestre la variante. Todas las entradas quedan pendientes de revisión visual, variante comercial y derechos. Las fotografías aportadas por el propietario conservan la referencia de autorización indicada en sus manifiestos; los archivos sin documentación mantienen `NO_DOCUMENTADO`.
