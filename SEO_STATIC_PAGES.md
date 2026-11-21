# Generación de páginas SEO estáticas

## Generar páginas
Desde la raíz del proyecto:

```bash
npm run seo:build
```

El script lee `data/catalog.js` y genera:
- `productos/`: página HTML individual por producto.
- `categorias/`: página HTML por familia/tag del catálogo.
- `sitemap.xml`: portada, páginas de producto, categorías y landings existentes.

## Verificación

```bash
node --check scripts/generate-seo-pages.js
npm run seo:build
npm run seo:check
npm test
python -m unittest discover -s tests -v
git status --short
```

## Publicar

```bash
git add productos categorias sitemap.xml scripts/generate-seo-pages.js package.json
git commit -m "Genera páginas SEO estáticas de productos y categorías"
git push origin main
```

## Importante
- Los precios son orientativos por kilogramo, según el catálogo.
- Las páginas no afirman que haya stock ni disponibilidad.
- No se incorporan fotografías automáticamente: deben pasar la revisión de imagen, fuente y licencia.
- La generación usa los nombres, descripciones, etiquetas y precios existentes; revisa los resultados antes de publicar.
- GitHub Pages publicará los archivos tras el push. La indexación por Google no es instantánea ni garantizada.


## Datos estructurados de productos
Cada página individual incluye JSON-LD `Product` con una `Offer` y una `UnitPriceSpecification`:
- El precio procede del campo `price` de `data/catalog.js`.
- La moneda es EUR.
- La referencia de unidad es 1 kilogramo (`KGM`), ya que el catálogo publica los precios por kg.
- No se declara disponibilidad, reseñas ni valoraciones porque no existe una fuente fiable para esos datos.
- `npm run seo:check` valida automáticamente el marcado de todas las páginas de producto.
