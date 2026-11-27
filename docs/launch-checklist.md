# Release checklist — Almendras de Málaga

## Estado técnico
- [x] Sitio estático compatible con GitHub Pages.
- [x] Catálogo en navegador (151 fichas).
- [x] Búsqueda, familias y filtros.
- [x] Ficha de producto y cálculo proporcional de formatos.
- [x] Carrito local y resumen de solicitud por WhatsApp.
- [x] WhatsApp principal de pedidos: +34 678 21 97 55.
- [x] Contacto secundario: +34 744 60 28 55.
- [x] Pedido expresamente pendiente de confirmación.
- [x] Las cinco páginas SEO envían las consultas a WhatsApp principal 666 y conservan el teléfono alternativo 744.
- [x] El carrito valida formatos y limita a 50 unidades por producto y formato.
- [x] Los diálogos gestionan el foco, Escape y los atributos ARIA.
- [x] Se protegen los campos dinámicos del catálogo frente a inyección HTML.
- [x] Pruebas de regresión automáticas con Python estándar.
- [x] Datos estructurados de negocio, sitemap y robots.
- [x] Comprobación automática de sintaxis JavaScript y estructura del catálogo.
- [x] Validación automática en GitHub Actions para push y pull request a main.

## Validación antes de cada publicación
1. `node --check js/app.js`
2. `python3 scripts/validate_site.py`
3. `python3 -m unittest discover -s tests -v`.
4. Revisar `git diff --check` y el diff completo.
5. Confirmar que el catálogo mantiene 151 fichas y no hay cambios no autorizados de nombres, precios o descripciones.
6. Confirmar que el carrito envía al 666 y que el 744 se mantiene como contacto alternativo.
7. Probar en móvil: búsqueda, filtro, ficha, formatos, añadir, quitar, limpiar carrito, campos obligatorios, WhatsApp, cerrar modales, Escape y compartir.
8. Verificar la web publicada después del despliegue; un commit no equivale a publicación comprobada.

## Pendiente para lanzamiento comercial completo
- Identidad legal del vendedor (nombre/razón social, NIF/CIF y domicilio legal).
- Correo de contacto comercial y de privacidad.
- Política de privacidad adaptada al formulario y al envío de datos a WhatsApp.
- Aviso legal y condiciones de venta/solicitud.
- Confirmar tarifa vigente, impuestos incluidos y gastos/condiciones de entrega o recogida.
- Revisar de forma individual las fotografías, licencias y atribuciones; no sustituir imágenes con aproximaciones.
- Completar o retirar la promesa de traducción completa: actualmente EN/FR/DE solo traducen una parte de la interfaz.
- Prueba interactiva en navegadores móviles y escritorio.

## Limitaciones funcionales declaradas
La web no tiene backend, inventario en tiempo real, cuentas de cliente, pagos ni almacenamiento de pedidos en servidor. El carrito se conserva localmente en el navegador y la solicitud se envía a WhatsApp. El negocio debe confirmar disponibilidad, precio final y entrega/recogida.


## Estado del despliegue
La validación automática y el despliegue de GitHub Pages se han completado correctamente para la revisión integral del 20-11-2026. La publicación técnica no sustituye las pruebas manuales de recorrido completo ni la finalización de los requisitos legales/comerciales.
