# Almendras de Málaga

Catálogo digital de frutos secos, almendras, aperitivos, frutas deshidratadas y golosinas en el centro histórico de Málaga.

**Web pública:** https://jmlopez0211-web.github.io/almendras-de-malaga/

## Características
- Catálogo de 151 productos alimentado desde `data/catalog.js`.
- Búsqueda tolerante a tildes, filtros por familias y subfamilias.
- Fichas de producto y cálculo orientativo por formato (100 g, 250 g, 500 g y 1 kg).
- Carrito local persistente en el navegador.
- Solicitud de pedido por WhatsApp con productos, cantidades, importe orientativo y datos de contacto.
- WhatsApp principal de pedidos: **+34 666 068 765**.
- Contacto alternativo: **+34 744 60 28 55**.
- Catálogo compartible y código QR.
- Diseño adaptable a móvil y escritorio.
- Diálogos con gestión de foco y cierre mediante Escape.
- Escape de contenido dinámico del catálogo y validación de URLs de imagen.
- Protección de los límites de cantidad al restaurar y modificar el carrito.
- Validación automatizada de las cinco páginas SEO y sus teléfonos.
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
