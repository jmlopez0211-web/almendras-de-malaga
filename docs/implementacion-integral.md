# Implementación integral — Almendras de Málaga

**Repositorio:** `jmlopez0211-web/almendras-de-malaga`  
**Rama:** `main`  
**Publicación:** GitHub Pages  
**Versión revisada:** 23 de noviembre de 2026

## 1. Arquitectura y límites de la aplicación

La tienda publicada en GitHub Pages es un frontend estático. Descarga HTML, CSS, JavaScript, catálogo y configuración comercial. El asistente inteligente puede comunicarse con un servicio Node.js externo desplegado en Render; ese servicio es independiente del hosting estático. La disponibilidad del backend debe comprobarse mediante su endpoint de salud y no se deduce de que exista una URL configurada.

- `index.html`: estructura semántica, navegación, catálogo, fichas, carrito, contacto, asistente, QR y metadatos.
- `styles.css`: identidad visual, disposición adaptable, componentes y estados de foco.
- `data/catalog.js`: catálogo JavaScript, expuesto mediante `window.PRODUCTS`.
- `js/commercial-config.js`: carga, valida y publica una única configuración comercial compartida; expone `window.COMMERCIAL_CONFIG` y `window.COMMERCIAL_CONFIG_READY`.
- `js/storeAssistantTools.js`: herramientas deterministas para catálogo, formatos, envío, carrito, resumen, WhatsApp e interpretación local del lenguaje natural.
- `js/app.js`: clasificación, búsqueda, filtros, imágenes, fichas, precios, carrito, WhatsApp, compartir, QR, asistente e idioma.
- Páginas HTML de especialidad: contenido SEO para las cinco consultas principales del negocio.
- `scripts/validate_site.py`: comprobaciones estáticas de publicación.
- `tests/test_site.py`: pruebas de regresión con la biblioteca estándar de Python.
- `.github/workflows/site-validation.yml`: ejecución automática de validación en GitHub Actions.

La tienda no dispone de base de datos de pedidos, cuentas de cliente, panel privado, inventario en tiempo real ni pago electrónico. El carrito se conserva en localStorage. El servicio externo del asistente usa memoria de proceso para sesiones y límites temporales; no equivale a una base de datos persistente. La integración de WhatsApp Business, si se configura, depende de credenciales externas y debe probarse en el entorno desplegado. El carrito se conserva en el almacenamiento local del navegador. El cliente revisa el resumen y decide enviarlo por WhatsApp. El comercio confirma disponibilidad, precio final y entrega o recogida.

## 2. Catálogo

El catálogo operativo contiene **151 productos**. Cada ficha usa una clave identificadora y campos de nombre, descripción, etiqueta, categoría, precio y, cuando procede, imagen y sus metadatos.

La validación exige para todas las fichas:
- nombre, descripción y categoría no vacíos;
- precio numérico mayor que cero;
- conservación del recuento esperado;
- comprobación de la existencia de los archivos de imagen locales referenciados.

Los nombres, descripciones, precios y categorías no se traducen ni modifican automáticamente. Su actualización requiere una tarifa o información del proveedor contrastada.

### Clasificación

- `catalogGroup(product)`: asigna las cuatro familias principales —frutos secos, frutas deshidratadas, caramelos/golosinas y aperitivos/variados— usando la categoría y la denominación del producto.
- `productFamily(product)`: determina la subfamilia para refinar el catálogo.
- `renderSubfamilies(active)`: genera los filtros de subfamilia.
- `renderFamilyTiles()`: construye los accesos visuales a las familias.
- `renderProducts()`: aplica categoría, subfamilia y búsqueda; mantiene todas las fichas y prioriza las que tienen una fotografía admitida, específica y única.

### Búsqueda

`normalizeCatalogText(value)` convierte el texto a minúsculas, elimina diacríticos y normaliza espacios. `catalogSearchWords(value)` aplica equivalencias de plural y variantes habituales —por ejemplo, almendras/almendra o pistachos/pistacho—. Todos los términos significativos introducidos deben aparecer en los campos consultables para que la ficha coincida.

Un resultado vacío muestra un mensaje; no modifica ni elimina productos.

## 3. Fotografías y atribución

`productImage(id, product)` solo devuelve imágenes:
- marcadas como verificadas;
- con ruta local bajo `assets/products/` o en los orígenes HTTPS admitidos;
- sin duplicidad con otra ficha que también tenga la imagen verificada.

Las rutas locales deben permanecer dentro de `assets/products/`; se rechazan segmentos de ruta `..`. Los orígenes remotos permitidos están limitados a los proveedores configurados en el código.

`renderProducts()` sustituye una imagen que falla por un marcador de imagen pendiente, sin ocultar la ficha. Las imágenes de las tarjetas familiares también se retiran si no cargan. La ficha de detalle crea un elemento `img` real con texto alternativo y presenta un marcador si la carga falla.

`productImageCredit(product)` solo construye una atribución cuando existen autor/crédito, fuente y licencia, y la fuente utiliza HTTPS. `renderProductImageCredit(host, product, hasPhoto)` monta el texto y el enlace mediante nodos DOM, no insertando el contenido del catálogo como HTML.

**No se consideran verificadas automáticamente las fotografías solo porque tengan una URL o porque se vean parecidas.** La auditoría documental anterior registró 61 fichas sin URL, 90 con URL, 77 marcadas como verificadas y 13 con URL sin estado verificado. También identificó cuatro imágenes locales con metadatos de atribución incompletos: `almendraGarrapinada`, `bastonAlmendra`, `harinaAlmendra` y `fileteAlmendra`. Estas incidencias siguen requiriendo revisión individual.

## 4. Ficha de producto y cálculo de formatos

`showProduct(id)` valida que la clave sea una propiedad propia del catálogo, carga nombre, etiqueta y descripción, muestra el aviso de alérgenos, monta la fotografía y restablece el formato y cantidad iniciales.

`updatePackPrice()` calcula el importe orientativo mediante:

`precio por kilogramo × gramos del formato ÷ 1.000`

Los formatos disponibles son 100 g, 250 g, 500 g, 1 kg, 5 kg, 10 kg y 20 kg. El importe es proporcional y no añade recargos. No constituye una tarifa comercial confirmada. El comercio confirma el precio final antes de aceptar el pedido.

La información de alérgenos es deliberadamente prudente: puede señalar alérgenos identificables por la denominación de la ficha, pero no sustituye la etiqueta ni la ficha técnica del lote. No se garantiza ausencia de trazas.

## 5. Carrito y solicitud por WhatsApp

El carrito se almacena bajo la clave local `almendrasCart`. Cada elemento conserva identificador de producto, nombre vigente del catálogo, precio vigente del archivo, gramos y cantidad.

Al restaurar el carrito:
- se descartan entradas nulas o malformadas;
- el identificador debe corresponder a una propiedad propia del catálogo;
- el formato debe estar entre 100, 250, 500, 1.000, 5.000, 10.000 y 20.000 gramos;
- la cantidad debe ser un entero entre 1 y 50;
- el precio y el nombre se vuelven a leer del catálogo, no del valor guardado.

Al añadir:
- se valida el formato;
- se valida una cantidad entera entre 1 y 50;
- no se permite acumular más de 50 unidades del mismo producto y formato;
- las operaciones de añadir, quitar y vaciar vuelven a calcular el total y actualizan el contador.

`buildCartOrderMessage()` exige nombre y teléfono, valida entre 9 y 15 dígitos después de eliminar separadores y prepara un mensaje con cliente, teléfono, artículos, cantidades, gramos, subtotales, total orientativo y observaciones. El texto indica que el pedido queda pendiente de confirmación.

El botón del carrito abre WhatsApp mediante `https://wa.me/34666068765` y codifica el resumen con `encodeURIComponent()`. El contacto principal es **+34 666 068 765**. El contacto alternativo es **+34 744 60 28 55**. Los botones secundarios de llamada y WhatsApp permanecen disponibles como alternativas, pero los botones principales de consulta y el carrito usan el 666.

La web no envía un pedido a un servidor ni lo confirma. El usuario revisa el mensaje y lo envía desde WhatsApp.

## 6. Diálogos y accesibilidad

`openModal(id)` conserva el elemento que abrió el diálogo, actualiza `aria-hidden`, abre el panel y lleva el foco al primer control. `closeModal(id)` cierra el panel, restablece el estado accesible y devuelve el foco al elemento anterior.

El controlador global de teclado:
- cierra el diálogo con Escape;
- mantiene la tecla Tab dentro del diálogo abierto;
- devuelve el foco al control de origen al cerrar.

El botón de acceso rápido del asistente actualiza `aria-expanded` y el panel actualiza `aria-hidden`. Escape también cierra el asistente cuando no hay un diálogo modal abierto.

La portada contiene un enlace para saltar al catálogo, estados de foco visibles, nombres accesibles para los controles principales y una región viva para el total del carrito. La hoja de estilos respeta `prefers-reduced-motion`.

## 7. Compartir y código QR

`copyTextSafely(value)` prueba la API Clipboard y ofrece un mecanismo alternativo cuando el navegador lo permite. El botón Compartir utiliza `navigator.share` y recurre a copiar el enlace cuando la función no está disponible.

`makeQR(id)` crea el código QR con la biblioteca QRCode cargada desde CDN. `qrCanvas()` prepara el PNG de mayor resolución y el logotipo central. Si la biblioteca externa no está disponible, el sistema no puede fabricar un QR descargable; se muestra la URL como alternativa y el botón de descarga informa del error.

El botón se denomina «Descargar QR del catálogo». No existe un área privada ni autenticación de propietario.

## 8. Asistente local y backend inteligente

`answerProductQuestion(raw)` consulta las fichas cargadas en el navegador. `storeAssistantTools.interpretLocal(text)` interpreta operaciones deterministas de búsqueda, formatos, adición, modificación, eliminación, resumen y limpieza del carrito. El módulo valida productos, formatos y cantidades antes de guardar cambios.

`assistant-config.js` define la URL del servicio externo. `sendAssistantMessage(q)` intenta resolver primero las operaciones locales y, cuando no corresponde, solicita respuesta a `/api/chat`. El navegador transmite un identificador de sesión y el mensaje; procesa la respuesta y aplica únicamente acciones de carrito con tipo reconocido. Si el servicio no responde, se muestra una alternativa basada en el catálogo local.

El servicio `server.js` utiliza variables de entorno para la clave de OpenAI y las credenciales opcionales de WhatsApp Business. Incluye herramientas de búsqueda de catálogo, cálculo de formatos, cálculo de envío y propuesta de añadir al carrito. La memoria de conversación está en memoria de proceso y puede perderse al reiniciar o escalar instancias. El stock sigue sin estar conectado; ninguna respuesta puede confirmar disponibilidad ni una compra.

## 9. Idiomas

El selector conserva ES, EN, FR y DE. Las cadenas que tienen clave `data-t` se traducen cuando existe una entrada en el diccionario correspondiente. La selección se conserva en el almacenamiento local. Si una cadena no tiene traducción, se restaura su texto original español.

La traducción de interfaz sigue siendo **parcial**. Los nombres, descripciones y datos originales del catálogo permanecen en español; no se deben anunciar EN, FR o DE como traducciones completas hasta incorporar y revisar toda la interfaz y el contenido de producto.

## 10. Contacto, SEO y páginas informativas

- El teléfono estructurado del negocio en JSON-LD es el principal: +34 666 068 765.
- La portada distingue el contacto principal y el secundario.
- Las cinco páginas SEO secundarias usan el WhatsApp principal en sus llamadas a la acción y conservan ambos teléfonos.
- La portada y las páginas informativas contienen enlaces canónicos, descripciones y navegación interna.
- `robots.txt` declara el sitemap público.
- `sitemap.xml` incluye la portada y las cinco páginas SEO.

No se publica horario de apertura mientras no exista confirmación verificable. La portada solicita consultar el horario vigente y disponibilidad directamente.

## 11. Configuración comercial compartida

`data/commercial.json` es la fuente de datos de tarifas de envío. `js/commercial-config.js` carga el JSON antes de los módulos de tienda, valida ocho tramos, etiquetas, precios no negativos y límites crecientes, y publica la configuración mediante `window.COMMERCIAL_CONFIG`. Si el archivo no se puede cargar o no supera la validación, la tienda conserva las tarifas de respaldo marcadas como provisionales. Al completarse la carga, emite `almendras:commercial-config-updated`; tanto el carrito como el asistente leen la misma configuración. `app.js` emite `almendras:shipping-updated` para recalcular el resumen visible.

Las tarifas siguen siendo provisionales hasta confirmación expresa del transportista. No se deben convertir en una promesa de coste de envío.

## 12. Validación automatizada

`scripts/validate_site.py` comprueba:
1. presencia de los archivos principales;
2. lectura de las 151 fichas y campos obligatorios;
3. duplicados de imágenes marcadas como verificadas;
4. existencia de rutas de imágenes locales;
5. IDs duplicados, imágenes sin atributo alt y atributos ARIA de los diálogos;
6. meta viewport y referencias locales;
7. anclas internas de cada página;
8. carga de `data/catalog.js` antes de `js/app.js`;
9. teléfono principal y alternativo;
10. envío del carrito al número principal;
11. destino WhatsApp y teléfonos de las cinco páginas SEO;
12. enlace del sitemap desde robots.txt y validez XML del sitemap;
13. enlace para saltar al catálogo, foco visible, movimiento reducido y medidas de seguridad de renderizado.

`tests/test_site.py` ejecuta siete pruebas de regresión usando únicamente la biblioteca estándar de Python. GitHub Actions realiza:
- `node --check js/app.js`;
- `python3 scripts/validate_site.py`;
- `python3 -m unittest discover -s tests -v`.

El workflow se ejecuta con cada push y pull request a `main`, y también puede iniciarse manualmente.

## 13. Requisitos pendientes para lanzamiento comercial completo

No se deben inventar ni publicar datos en los siguientes apartados:
- identidad legal del vendedor, NIF/CIF y domicilio legal;
- correo de contacto y canal de privacidad;
- aviso legal y política de privacidad específicos;
- condiciones de venta, recogida/entrega, gastos, cancelaciones y devoluciones cuando correspondan;
- confirmación de tarifa vigente, impuestos y precios aplicables;
- auditoría visual y documental de todas las fotografías pendientes;
- traducción completa de la interfaz y del contenido, si se desea ofrecer en otros idiomas;
- prueba manual de todo el flujo en navegadores reales de móvil y escritorio.

El estado técnico de la publicación no equivale a una certificación legal ni a la confirmación de precios, stock o condiciones comerciales.
