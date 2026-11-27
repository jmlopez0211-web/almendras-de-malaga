# Almendras de Málaga

Catálogo digital de frutos secos, almendras, aperitivos, frutas deshidratadas y golosinas en el centro histórico de Málaga.

**Web pública:** https://jmlopez0211-web.github.io/almendras-de-malaga/

La implementación, sus módulos, reglas de negocio, límites y procedimientos de validación están documentados en [docs/implementacion-integral.md](docs/implementacion-integral.md).

## Características
- Catálogo de 151 productos alimentado desde `data/catalog.js`.
- Búsqueda tolerante a tildes, filtros por familias y subfamilias.
- Fichas de producto y cálculo orientativo por formato (100 g, 250 g, 500 g y 1 kg).
- Carrito local persistente en el navegador.
- Solicitud de pedido por WhatsApp con productos, cantidades, importe orientativo y datos de contacto.
- WhatsApp principal de pedidos: **+34 678 21 97 55**.
- Contacto alternativo: **+34 744 60 28 55**.
- Catálogo compartible y código QR.
- Diseño adaptable a móvil y escritorio.
- Diálogos con gestión de foco y cierre mediante Escape.
- Escape de contenido dinámico del catálogo y validación de URLs de imagen.
- Protección de los límites de cantidad al restaurar y modificar el carrito.
- Auditoría SEO automatizada de las fichas de producto y páginas de categoría.
- Titles y meta descriptions diferenciados, enlaces de familia, breadcrumbs y Schema conservador.
- Páginas informativas y metadatos SEO.

## Arquitectura
Proyecto estático; se publica mediante GitHub Pages. No utiliza backend, base de datos, cuentas de cliente, inventario en tiempo real ni pasarela de pago. El carrito se guarda en el navegador y el pedido se envía como una solicitud a WhatsApp. El negocio confirma disponibilidad, precio final y entrega o recogida.

## Desarrollo local
Desde la raíz del repositorio, iniciar un servidor estático:

```bash
python3 -m http.server 8000
```

Abrir http://localhost:8000

## Validación
La comprobación automática del repositorio no requiere dependencias adicionales:

```bash
node --check js/app.js
python3 scripts/validate_site.py
```

El workflow de GitHub Actions ejecuta la comprobación de sintaxis, el validador de publicación y las pruebas de regresión en cada push y pull request hacia `main`.

Si existe el conjunto de pruebas local:

```bash
python3 -m unittest discover -s tests -v
```

## Reglas del catálogo y fotografías
- No cambiar nombres, precios, descripciones ni formatos sin contrastarlos con la tarifa comercial vigente.
- No añadir ni eliminar productos sin autorización y confirmación del negocio.
- Solo mostrar fotografías verificadas, específicas y con licencia/atribución documentada.
- No reutilizar imágenes entre productos distintos.
- Las fichas sin fotografía permanecen visibles con un marcador.

## Pendiente de lanzamiento comercial completo
- Identidad legal del vendedor, NIF/CIF y domicilio legal.
- Correo de contacto y política de privacidad.
- Aviso legal y condiciones de venta/solicitud.
- Confirmación de tarifas, impuestos y condiciones de entrega o recogida.
- Revisión fotográfica y documental de las imágenes pendientes.
- Traducción completa de la experiencia si se anuncian EN, FR o DE como idiomas disponibles.
- Pruebas manuales de compra/solicitud en móvil y escritorio.

## Fichas SEO de productos

Las fichas y categorías se generan desde `data/catalog.js`:

```bash
npm run seo:build
npm run seo:check
npm test
```

La generación:
- crea títulos y descripciones diferenciados por producto y categoría;
- incorpora contenido basado en el nombre y descripción real del catálogo;
- enlaza productos de la misma familia y páginas de categoría;
- incluye navegación semántica y breadcrumbs;
- publica Schema Product sin Offer, precio ni disponibilidad;
- añade ItemList a páginas de categoría;
- conserva las URLs de las landings existentes al regenerar el sitemap.

**Regla de datos comerciales:** las fichas SEO no publican precios, formatos, existencias, ingredientes, alérgenos, certificaciones ni condiciones de entrega si no están confirmados para el producto. La consulta por WhatsApp permite confirmar la información vigente.

El workflow `.github/workflows/seo-product-pages-build.yml` regenera las páginas al cambiar el catálogo o el generador y publica los archivos derivados después de validar las pruebas.
