# Motor de búsqueda de imágenes v11 — recuperación por coincidencia visual

## Hallazgo de la auditoría
La v9/v10 rechazaba candidatos de alimentos correctos cuando la descripción o etiquetas no documentaban variantes que no pueden verificarse visualmente, como sal, aceite o azúcar. Esto generaba falsos negativos y colas de productos sin resultados.

## Cambio
- El ingrediente/producto principal sigue siendo requisito duro.
- Contextos irrelevantes o comerciales (recetas, platos, mercados, tiendas, envases, etiquetas y marcas ajenas) siguen rechazándose.
- En frutos secos y frutas deshidratadas, preparación y variante se puntúan como evidencia adicional, no como requisito textual absoluto.
- Los metadatos incompletos quedan marcados como `variant_metadata_unverified`.
- Las variantes contradictorias explícitamente detectadas siguen siendo rechazadas mediante `STRICT_FORBIDDEN_TERMS`.
- Las categorías de chocolates y confitería con identidad específica mantienen controles de ingrediente, cobertura, sabor o marca cuando son necesarios para evitar confundir productos.

## Interpretación
Una imagen de almendras puede ser una candidata visual para «almendra frita sin sal» aunque la fuente solo la titule «almonds». La fotografía no demuestra que esté frita ni que no tenga sal. Esas propiedades se mantienen como advertencias y necesitan confirmación del producto, proveedor o ficha documental.

## Seguridad del catálogo
- Los archivos siguen siendo candidatos no aprobados.
- No se modifica `data/catalog.js`.
- No se marca `imageVerified`.
- Se mantiene la revisión visual individual y la verificación de fuente/licencia antes de publicar.

## Pruebas de regresión
Se añaden casos que permiten aceptar una fotografía del alimento principal cuando faltan metadatos de variantes visualmente no verificables, sin relajar los rechazos de falsos positivos conocidos.
