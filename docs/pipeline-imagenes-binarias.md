# Descarga, inspección y sincronización de fotografías

## Dependencias

Desde la raíz del repositorio:

```bash
python3 -m pip install requests Pillow
```

Recomendado: ejecutar en un entorno virtual.

## 1. Descargar candidatos binarios

El manifest `photo_candidates.json` acepta:
- `product_key`
- `commons_title` (Wikimedia Commons, resuelto mediante API)
- o `url` (URL directa de imagen), opcionalmente `metadata`

```bash
python3 scripts/image_pipeline.py download --manifest photo_candidates.json --directory assets/images
```

Reintentos, timeouts, MIME, firma real del archivo, límite de tamaño, decodificación y dimensiones mínimas se validan. Los archivos se guardan como candidatos.

## 2. Inspeccionar archivos y duplicados

```bash
python3 scripts/image_pipeline.py inspect --directory assets/images
```

La inspección comprueba decodificación, resolución, formato, relación de aspecto y SHA-256. Los duplicados exactos se agrupan por hash. No detecta similitud visual.

## 3. Sincronizar mediante Git local (recomendado)

En una copia local del repositorio:

```bash
python3 scripts/image_pipeline.py sync-git --directory assets/images
```

Esto hace `git add` y `git commit` de los binarios candidatos. Para hacer push explícito:

```bash
python3 scripts/image_pipeline.py sync-git --directory assets/images --push
```

No uses `--push` hasta revisar el listado de archivos que se van a incluir.

## 4. Sincronizar por GitHub API

```bash
export GITHUB_TOKEN=TU_TOKEN
python3 scripts/image_pipeline.py sync-api --owner jmlopez0211 --repo almendras-de-malaga --branch main --directory assets/images --base-path assets/images
```

El token debe tener permiso de Contents: Read and write para el repositorio. No guardes el token en el script, manifest ni commit. La API de Contents crea un commit por archivo; para grandes lotes, Git local es preferible.

## 5. Informe

Se genera `docs/image-pipeline-report.json` con descargas, resultados de inspección, hashes y errores.

## Seguridad y aprobación

- Descarga solo HTTP/HTTPS.
- MIME permitido: JPEG, PNG, WebP; la firma del archivo también debe coincidir.
- Máximo por archivo: 25 MB.
- Reintentos y timeout configurados.
- Se rechazan archivos demasiado pequeños o corruptos.
- SHA-256 identifica duplicados byte a byte.
- Ninguna función actualiza `imageVerified`, `imageSource`, `imageLicense` ni marca producto aprobado.
- Los archivos descargados y sincronizados permanecen **UNAPPROVED / CANDIDATE** hasta revisión humana exacta del producto, imagen, licencia, atribución y visualización en tienda.

## Integración con scripts anteriores

`scripts/download_commons_candidates.py` puede sustituirse por una llamada al pipeline común:

```bash
python3 scripts/image_pipeline.py download --manifest photo_candidates.json --directory assets/products/candidates
```

`scripts/audit_catalog_images.py` sigue siendo una auditoría independiente del catálogo: ejecuta después de integrar archivos, pero no aprueba las imágenes ni altera el catálogo.
