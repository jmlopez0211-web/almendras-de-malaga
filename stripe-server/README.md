# Backend de pagos — Almendras de Málaga

Este servicio crea sesiones alojadas de Stripe Checkout. La clave secreta vive únicamente en las variables de entorno del servidor; nunca en GitHub Pages ni en el navegador.

## Antes de activar cobros

1. Crear/usar una cuenta Stripe del negocio y completar la verificación solicitada por Stripe.
2. Confirmar con Fabián todos los precios, formatos, impuestos aplicables, política de entrega/recogida, devoluciones y datos legales del vendedor.
3. Revisar `catalog.json`: los importes se han copiado de los precios orientativos que actualmente aparecen en la web. **No son una validación comercial ni fiscal.**
4. Desplegar este directorio como servicio Node.js en un hosting con variables secretas (por ejemplo Render).
5. Configurar las variables indicadas abajo. Empezar con una clave `sk_test_...` y mantener `PAYMENTS_ENABLED=false` mientras se prueba.

## Variables de entorno

- `STRIPE_SECRET_KEY`: clave secreta de prueba o producción de Stripe.
- `SITE_URL`: URL pública exacta de GitHub Pages.
- `ALLOWED_ORIGIN`: origen de la web, sin ruta: `https://jmlopez0211-web.github.io`.
- `PAYMENTS_ENABLED`: `false` hasta que el negocio haya validado precios y condiciones; solo entonces `true`.
- `PORT`: lo proporciona normalmente el hosting.

## Despliegue

En Render, crear un **Web Service** conectado al repositorio:
- Root Directory: `stripe-server`
- Runtime: Node
- Build Command: `npm install`
- Start Command: `npm start`

Añadir las variables de entorno en el panel privado del servicio. No crear ni subir un archivo `.env` al repositorio.

Después de desplegar, abrir `https://TU-SERVICIO/health`; debe responder `{"ok":true,...}`.

Editar `stripe-config.js` en GitHub y sustituir la cadena vacía por la URL del servicio, por ejemplo:
```js
window.ALMENDRAS_CONFIG = {
  STRIPE_API_BASE: 'https://tu-servicio.onrender.com'
};
```

## Pruebas y activación

- Con clave `sk_test_...`, probar una compra en modo test usando una tarjeta de prueba publicada por Stripe.
- Comprobar importe, formato, teléfono y resultado de cancelación.
- No pasar a clave `sk_live_...` ni poner `PAYMENTS_ENABLED=true` hasta que Fabián haya confirmado precios y el negocio esté listo para vender.
- Para una tienda en producción se recomienda añadir webhooks firmados y un registro persistente de pedidos antes de automatizar preparación o envío. Esta primera versión no almacena pedidos en una base de datos ni confirma entregas.

## Seguridad

El servidor vuelve a calcular cada importe usando su propio `catalog.json`; no confía en precios enviados por el navegador. Limita el tamaño de la petición y el número de intentos. La web conserva WhatsApp como alternativa.
