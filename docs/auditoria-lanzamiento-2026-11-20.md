# Auditoría de preparación para lanzamiento — 20-11-2026

## Alcance y arquitectura

Repositorio: `jmlopez0211-web/almendras-de-malaga`, rama `main`.

La web es un sitio estático publicado con GitHub Pages. De acuerdo con la arquitectura del proyecto, el flujo comercial es: catálogo en el navegador, carrito guardado localmente y envío de una solicitud por WhatsApp. No hay servidor, inventario en tiempo real, registro de pedidos, pasarela de pago ni cobro desde la página. El envío de WhatsApp no confirma por sí solo el pedido; el comercio debe confirmar disponibilidad, precio final y entrega o recogida.

## Estado estructural del catálogo

Comprobación directa de `data/catalog.js`:

| Métrica | Resultado |
|---|---:|
| Fichas operativas | 151 |
| Fichas con precio numérico positivo, nombre, descripción y categoría | 151 |
| Fichas sin URL de imagen | 61 |
| Fichas con URL de imagen | 90 |
| URLs con `imageVerified: true` | 77 |
| URLs sin `imageVerified: true` | 13 |

Estos indicadores describen los datos del catálogo; **no equivalen a una nueva auditoría visual de las 77 imágenes marcadas como verificadas**.

### Incidencias de imágenes

- La misma URL `Almendras_tostadas_sin_piel.jpg` está asignada a «Almendra tostada repelada con sal» y «Almendra tostada repelada sin sal». La aplicación detecta la duplicación y no muestra esa imagen en ninguna de las dos fichas. No se ha asignado una sustituta.
- Hay 13 referencias de imagen sin `imageVerified: true`; el renderizador no las muestra.
- Cuatro imágenes locales marcadas como verificadas carecen de metadatos completos de crédito, fuente y licencia: `almendraGarrapinada`, `bastonAlmendra`, `harinaAlmendra` y `fileteAlmendra`. La ficha ya no presenta un crédito genérico de «fotografía real verificada» cuando falta esa documentación.
- La falta de fotografía no elimina la ficha: se mantiene un marcador de imagen pendiente.

### Discrepancia de recuento

`catalogo-revisado.md` contiene 152 filas. La ficha adicional es «Almendra frita con piel», que no aparece en las 151 fichas de `data/catalog.js`. No se reincorpora sin confirmación del comercio y una tarifa vigente.

## Flujo de solicitud comercial

El código permite:

1. Buscar y filtrar productos.
2. Consultar precio orientativo por kilogramo.
3. Calcular formatos de 100 g, 250 g, 500 g y 1 kg.
4. Añadir, quitar y conservar artículos en el carrito local.
5. Preparar un resumen con productos, cantidades, formato, importes, nombre, teléfono y observaciones.
6. Enviar la solicitud a WhatsApp principal (+34 666 068 765) o al contacto alternativo (+34 744 60 28 55).

No se ha conectado el stock. Los precios del archivo son numéricos y válidos estructuralmente, pero el repositorio no demuestra que coincidan con la tarifa comercial vigente ni si incluyen IVA. Tampoco define tarifas, zonas o plazos de entrega.

## Correcciones técnicas publicadas en esta revisión

- Eliminado un segundo listener global redundante para abrir fichas de producto; el listener dentro del renderizador se conserva.
- Cierre de diálogos con la tecla Escape.
- Copiado del enlace con alternativa cuando la API Clipboard no está disponible.
- El crédito de una imagen sin metadatos ya no afirma que está verificada.
- El WhatsApp de cabecera y el asistente remiten al número principal de pedidos.
- Los diálogos tienen etiqueta accesible mediante `aria-labelledby`.
- Los campos de nombre y teléfono tienen atributos `required` y límites de longitud.
- Los botones especifican que envían una «solicitud» por WhatsApp y el texto aclara que queda pendiente de confirmación.
- Se retiró un crédito fotográfico del hero porque el CSS publicado muestra un fondo degradado y no esa fotografía.

Commits:
- `0a064eab3596a4120bb0720cb89f19b3ce906bd8`
- `06ac2cd1e9c7e5fdafb4cbb83cdad0259fa14f38`

La sintaxis de `js/app.js` se comprobó antes de publicar los cambios y el contenido de ambos archivos se volvió a leer desde `main`. La publicación efectiva de GitHub Pages y la prueba interactiva en navegador quedan pendientes de verificación.

## Bloqueos antes de anunciar la web como lista para vender

1. **Identidad legal del vendedor:** falta nombre o razón social, NIF/CIF, domicilio legal y correo electrónico de contacto. La página muestra nombre comercial, dirección del puesto y teléfonos, pero eso no completa todos los datos de identificación del prestador que contempla el artículo 10 de la LSSI.
2. **Privacidad:** no hay política de privacidad publicada. El formulario prepara nombre, teléfono y observaciones para enviarlos por WhatsApp; hay que informar de forma clara de quién trata esos datos, finalidades, base jurídica, destinatarios y derechos.
3. **Condiciones de venta:** no hay páginas publicadas de condiciones, entrega/recogida, gastos, cancelaciones, devoluciones y desistimiento cuando corresponda. Deben definirse según el modo real de venta y el tipo de producto.
4. **Precios e impuestos:** confirmar que los precios por kilo son los vigentes y si se muestran con IVA incluido. Definir cómo se comunican los gastos de entrega antes de que el cliente quede vinculado.
5. **Disponibilidad:** el stock no está conectado. La web debe seguir presentando el carrito como una solicitud pendiente, no como compra confirmada.
6. **Fotografías:** quedan 61 fichas sin imagen y 13 referencias no verificadas, además de la duplicación descrita. No se aprobarán imágenes aproximadas ni comerciales para rellenar huecos.
7. **Idiomas:** los selectores ES/EN/FR/DE no traducen todo el contenido, el catálogo y el proceso de pedido; no debe anunciarse una experiencia multilingüe completa hasta terminar esas traducciones.

## Referencias oficiales para la revisión legal

- Ley 34/2002 (LSSI), artículo 10: https://www.boe.es/eli/es/l/2002/07/11/34
- Información de la Administración sobre obligaciones de una web comercial: https://lssi.digital.gob.es/lssi/la-ley/preguntas-frecuentes
- Real Decreto Legislativo 1/2007, artículo 97 (información precontractual): https://www.boe.es/eli/es/rdlg/2007/11/16/1/con/20071130

Esta auditoría es técnica y documental; no sustituye una revisión jurídica de las condiciones comerciales concretas.


## Correcciones posteriores de la revisión integral

- Los cinco artículos SEO secundarios envían sus botones de consulta a WhatsApp principal +34 666 068 765 y conservan el +34 744 60 28 55 como teléfono alternativo.
- El bloque de contacto de la portada identifica expresamente el 666 como principal y el 744 como alternativo.
- Se retiró el horario 10:00–20:00 de la portada al no constar una confirmación verificable en el expediente de lanzamiento; ahora se indica que debe consultarse el horario vigente.
- El botón que abre el QR se denomina «Descargar QR del catálogo»; no existe un área privada ni un sistema de autenticación de propietario.
- Se añadió escape HTML para los campos dinámicos del catálogo, atribución fotográfica construida con nodos DOM y validación de protocolos/orígenes admitidos para imágenes.
- El carrito limita las unidades acumuladas por producto y formato a 50 y descarta entradas malformadas o excesivas al restaurar localStorage.
- Los diálogos actualizan aria-hidden, gestionan Escape y mantienen el foco dentro del modal; se añade aviso de que las traducciones EN/FR/DE son parciales y que el catálogo fuente conserva sus nombres y descripciones en español.
- Se ampliaron los controles automáticos para revisar todas las páginas HTML, enlaces locales, archivos de imagen locales, teléfonos, accesibilidad básica, sitemap y carga ordenada del catálogo.
- Se añadieron pruebas de regresión con la biblioteca estándar de Python y se ejecutan desde GitHub Actions junto con la validación JavaScript.

La validación estática y las pruebas de regresión han pasado en GitHub Actions. El despliegue de GitHub Pages para la revisión integral también ha finalizado correctamente. Sigue pendiente la prueba manual interactiva en varios navegadores/dispositivos y la información legal/comercial indicada en el apartado de bloqueos; por ello no se declara cerrada la preparación legal para venta online.
