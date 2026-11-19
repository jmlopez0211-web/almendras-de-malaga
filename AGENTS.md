# AGENTS.md — Almendras de Málaga

## Proyecto y arquitectura
- Sitio estático publicado con GitHub Pages. No añadir servidores, backend, bases de datos, paneles de administración, funciones serverless ni pasarelas de pago.
- Mantener el flujo de compra existente: catálogo en el navegador, carrito local y envío del resumen por WhatsApp.
- Estructura prevista:
  - `index.html`: estructura y contenido semántico.
  - `styles.css`: estilos y diseño adaptable.
  - `data/catalog.js`: datos del catálogo; expone `window.PRODUCTS`.
  - `js/app.js`: renderizado, filtros, búsqueda, formatos, carrito y WhatsApp.
  - `js/chatbot.js`: asistente de catálogo, separado de la cuadrícula.
  - `img/frutos-secos/`: fotografías locales verificadas de la Fase 1.
  - `assets/products/`: imágenes existentes; no moverlas hasta comprobar cada ruta y actualizar sus referencias.
- Usar rutas relativas compatibles con el subdirectorio de GitHub Pages. Los scripts clásicos se cargan en orden: catálogo antes que aplicación.

## Integridad del catálogo
- No eliminar, renombrar ni ocultar productos para resolver un problema visual.
- Conservar nombres, descripciones, categorías, precios y formatos salvo que exista una corrección respaldada por la tarifa original y se solicite aplicarla.
- El catálogo actual contiene 152 fichas. Toda modificación debe informar de cualquier variación del recuento.
- La falta de fotografía nunca debe impedir que una ficha aparezca en la cuadrícula.

## Fotografías: regla estricta
- Una imagen solo se asigna cuando representa el producto y su preparación concretos.
- Prohibido reutilizar una fotografía en dos productos distintos o usar una imagen aproximada para rellenar un hueco.
- No inferir por una fotografía el aceite utilizado, la presencia de sal, el origen ni otros atributos que la imagen no pueda demostrar.
- Priorizar archivos locales dentro de `img/frutos-secos/`; optimizar imágenes para web y usar nombres descriptivos.
- Para imágenes de terceros, comprobar licencia comercial, autor y fuente originales. Guardar la atribución y mostrarla cuando la licencia lo exija. No enlazar directamente imágenes externas cuando sea posible alojar una copia autorizada local.
- Si no hay una imagen fiel y con licencia válida, conservar un marcador limpio y registrar el producto como pendiente.
- No sustituir las imágenes existentes ni cambiar su estado de verificación sin inspeccionar el archivo y su fuente.

## Diseño y compra móvil
- Conservar la identidad visual existente: crema, verde oscuro/oliva, acentos cálidos y tipografía editorial.
- Mantener tarjetas legibles en móvil, títulos breves, fotografías con proporción coherente y precio por kilo visible.
- Mantener los formatos disponibles de 100 g, 250 g, 500 g y 1 kg cuando correspondan al producto y el cálculo proporcional existente.
- No cambiar la cuadrícula, el modal de producto, los filtros ni los botones de compra al trabajar solo con imágenes o datos.
- Mantener accesibles búsqueda, carrito, contacto, ubicación y WhatsApp.

## WhatsApp
- El teléfono principal de pedidos es `34744602855`; construir enlaces como `https://wa.me/34744602855?text=` usando `encodeURIComponent()`.
- No borrar ni modificar contactos alternativos que ya estén presentes sin autorización.
- El mensaje debe incluir los artículos, cantidades, peso/formato, precios orientativos y datos del comprador que solicita el formulario.
- No presentar el pedido como confirmado hasta que el comercio lo confirme.

## Cambios y verificación obligatoria
- Leer los archivos implicados y sus dependencias antes de editar.
- Hacer cambios pequeños, localizados y reversibles. Para fotografías, trabajar en micro-lotes de 6 a 8 productos como máximo.
- Antes de cada commit:
  1. Comprobar sintaxis de todo JavaScript modificado.
  2. Comprobar que `window.PRODUCTS` se carga antes de `js/app.js`.
  3. Contar las fichas y comparar con el recuento anterior.
  4. Detectar URLs/archivos de imagen repetidos en productos distintos.
  5. Comprobar que las referencias de imagen existen y que las fichas sin foto siguen visibles.
  6. Revisar que se conservan los selectores y elementos DOM usados por el renderizador.
  7. Revisar el diff y confirmar que no hay cambios ajenos a la tarea.
- No dar por válida una modificación solo porque el commit se haya creado. Distinguir entre validación estática, prueba en navegador y publicación efectiva de GitHub Pages.
- Si una modificación rompe `renderProducts()`, la cuadrícula, los filtros o el carrito, revertir o corregir antes de continuar. Documentar brevemente la causa y la solución.
- No pasar a otra categoría hasta que la Fase 1 (Frutos secos) esté revisada y validada.
