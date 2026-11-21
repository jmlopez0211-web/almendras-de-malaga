# Ejecución SEO local — Almendras de Málaga

## Implementado en esta rama

- Sección HTML estática y rastreable con cinco variedades de almendra en la portada.
- Enlaces directos desde esa sección a cinco fichas de producto existentes en el sitemap.
- Coherencia entre el title, la meta description, Open Graph y Twitter Cards.
- Enlaces contextuales desde cinco artículos hacia el catálogo de la portada.
- Aserciones en la auditoría SEO para evitar regresiones.

No se han modificado dirección, coordenadas, horario, teléfono, identidad ni marcado de negocio local. La ubicación que declara la web debe verificarse con la ficha exacta de Google antes de modificarla. No se han añadido imágenes nuevas ni precios estáticos.

## 1. Google Business Profile — pendiente de identificar la ficha

1. Abrir Google Maps y entrar en la ficha que administra el comercio.
2. Copiar el enlace mediante Compartir.
3. Confirmar que el nombre de la ficha corresponde al negocio y que el pin cae en el puesto real.
4. Verificar con el titular nombre comercial, categoría principal, dirección o área de servicio, teléfono, sitio web, horario semanal, fotografías y acceso a reseñas.
5. No crear una segunda ficha si ya existe una ficha legítima.
6. No publicar horarios que no estén confirmados.
7. No introducir un domicilio postal si el negocio no cumple los requisitos de establecimiento físico de Google.

«Tienda de frutos secos» es una categoría candidata para comprobar, no una categoría ya asignada.

## 2. Fotografías y reseñas

Priorizar fotografías propias y autorizadas:
- puesto reconocible desde la vía pública;
- rótulo comercial, si existe;
- mostrador y exposición real;
- variedades de almendra representadas fielmente.

Solicitar opiniones a clientes reales sin ofrecer incentivos, filtrar opiniones negativas ni redactar reseñas en nombre de clientes.

## 3. Menciones y enlaces locales

Empezar por actualizar las menciones locales que ya existen. Solicitar al editor:
- nombre comercial coherente;
- dirección y teléfono confirmados por el negocio;
- enlace directo a la portada;
- texto de enlace descriptivo y natural.

Registrar directorio, URL de la ficha, enlace de destino, fecha de solicitud y estado. No comprar enlaces ni crear perfiles duplicados.

## 4. Enlaces internos

Los cinco artículos con enlace contextual añadido son:
- `blog/comprar-almendras-malaga.html`
- `blog/comprar-frutos-secos-malaga.html`
- `blog/almendras-al-por-mayor.html`
- `blog/almendras-garrapinadas-caseras.html`
- `blog/almendras-beneficios-y-usos.html`

Las fichas de producto y páginas comerciales mantienen sus enlaces de navegación hacia la portada. Evitar repetir enlaces idénticos de forma artificial.

## 5. Medición orgánica

Conectar en OpenSEO la propiedad URL-prefix exacta de Search Console:
`https://jmlopez0211-web.github.io/almendras-de-malaga/`

Consultar los últimos tres meses con dimensiones consulta y página. Registrar por consulta:
- clics;
- impresiones;
- CTR;
- posición media;
- URL que recibe impresiones.

Consultas prioritarias:
- Almendras de Málaga;
- comprar almendras Málaga;
- tienda de almendras Málaga;
- almendras Málaga centro;
- almendras garrapiñadas Málaga;
- frutos secos Málaga centro.

Separar móvil y escritorio. Cada posición debe acompañarse de fecha, ubicación, dispositivo y profundidad consultada.

## 6. Medición local en Google Maps

No iniciar la cuadrícula hasta identificar la ficha propia y su place ID o CID. Después:
- fijar el centro en las coordenadas verificadas del puesto;
- ejecutar una cuadrícula móvil 3 × 3 con separación inicial de 2 km;
- medir «tienda de frutos secos», «almendras» y «frutos secos» por separado;
- registrar ranking, puntos donde aparece, primer competidor y fecha;
- repetir con la misma configuración para comparar cambios.

Un resultado de un solo punto no representa toda Málaga.

## 7. Analítica web y privacidad

No se ha añadido Google Analytics, Tag Manager ni píxeles. Para medir clics a WhatsApp, llamadas y acciones del carrito hacen falta proveedor, identificador de medición y revisión de consentimiento/cookies. No incluir identificadores ficticios ni activar seguimiento sin configuración válida.

## 8. Validación antes de integrar en main

1. `node --check js/app.js`
2. `npm run seo:check`
3. `npm test`
4. `python3 scripts/validate_site.py`
5. `python3 -m unittest discover -s tests -v`
6. Revisar diff y probar móvil y escritorio.
7. Confirmar que se conservan las 151 fichas originales y que carrito, filtros, buscador y WhatsApp no han cambiado.

## Datos pendientes

- enlace compartido de la ficha exacta de Google Maps;
- pin, coordenadas y dirección pública confirmados;
- categoría y horario confirmados por el titular;
- fotografías reales y reseñas atribuidas a la ficha correcta;
- autorización de Search Console;
- identificador de analítica, si se decide instrumentarla.
