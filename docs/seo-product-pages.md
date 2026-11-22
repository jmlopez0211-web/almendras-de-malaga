# Implementación SEO de fichas de producto

## Fuente de datos
Las páginas se generan a partir de `data/catalog.js`. El generador no crea afirmaciones comerciales nuevas: utiliza el nombre, descripción y familia que ya existen en el catálogo.

## Metadata
Cada ficha tiene:
- title propio y orientado al producto y Málaga;
- meta description basada en el nombre y descripción real;
- canonical;
- Open Graph;
- Twitter Card.

El auditor comprueba longitud, canonical y duplicados de titles/descriptions de producto.

## Contenido
La ficha contiene:
1. navegación Inicio → Catálogo → Familia;
2. H1 con nombre del producto;
3. descripción del catálogo;
4. explicación de que los datos comerciales deben confirmarse;
5. CTA de consulta por WhatsApp;
6. bloque de información;
7. enlaces a productos de la misma familia;
8. enlace a la página de categoría;
9. navegación a otras familias;
10. contacto y ubicación.

No se inventan ingredientes, alérgenos, formatos, precios, stock, certificaciones ni condiciones comerciales.

## Datos estructurados
- `Product`: name, description, category y URL.
- `BreadcrumbList`: navegación jerárquica.
- `ItemList`: listado de productos en las categorías.

No se incluye `Offer`, `price`, `priceCurrency`, `availability` ni `priceSpecification` mientras no exista una fuente comercial verificada y una política de actualización.

## Enlaces internos
Cada ficha enlaza:
- la categoría/familia actual;
- productos hermanos;
- otras categorías;
- portada y catálogo.

Los enlaces se validan localmente en el SEO checker.

## Sitemap
El generador elimina las URLs antiguas de productos y categorías para reemplazarlas por las URLs actuales, pero conserva las landings, portada y demás páginas del sitemap.

## Validación
`npm run seo:build` regenera páginas.
`npm run seo:check` verifica sitemap, canonical, metadata, Schema, enlaces internos y ausencia de Offer.
`npm test` ejecuta las pruebas y la auditoría SEO.

## Automatización
- El workflow de validación genera las páginas antes de ejecutar pruebas.
- El workflow de build regenera y publica páginas derivadas cuando cambia el catálogo o el generador.
