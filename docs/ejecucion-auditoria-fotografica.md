# Cómo ejecutar la auditoría fotográfica

Desde la raíz del repositorio:

```bash
python3 scripts/audit_catalog_images.py
```

Se generan:
- `docs/photo-catalog-audit.json`: datos por producto y resumen.
- `docs/photo-catalog-audit.md`: informe legible.

La auditoría es de referencias y metadatos declarados. **No certifica la fotografía**, no abre imágenes remotas, no verifica licencias en sus páginas originales y no sustituye la inspección visual.

## Flujo obligatorio para aprobar una fotografía

1. Descargar el archivo original desde la fuente documentada.
2. Revisar visualmente el archivo completo, no solo la miniatura.
3. Confirmar producto y variante exactos (con/sin sal, piel/repelado, frito/tostado, cobertura, formato).
4. Rechazar envases, marcas, etiquetas, publicidad, fondos sucios, composiciones con productos ajenos o fotos de variantes ambiguas.
5. Registrar autor, fuente, licencia y condiciones de atribución.
6. Copiar el binario a `assets/products/` con nombre estable.
7. Actualizar el producto del catálogo con ruta local y metadatos.
8. Comprobar la imagen en la web desplegada y guardar evidencia de la revisión.

Una fotografía candidata, una URL o un metadato de Commons **no** cuentan como incorporación ni aprobación.
