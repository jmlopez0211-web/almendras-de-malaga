# SEO y captación de tráfico — Almendras de Málaga

## Implementado en el repositorio
- Canonical y meta robots en portada.
- Open Graph y Twitter Card.
- Datos estructurados Store con dirección, teléfono, mapa y contacto.
- FAQPage estructurada para ubicación, formatos, consultas y atención profesional.
- robots.txt con sitemap declarado.
- Sitemap XML con las páginas estáticas de captación.
- Auditoría automática: archivos incluidos en sitemap, titles, descriptions, canonical, robots, Open Graph y Schema.
- Comando `npm run seo:check` y auditoría integrada en `npm test`.

## Revisión manual obligatoria después de publicar
1. Abrir Google Search Console y seleccionar la propiedad URL-prefix:
   `https://jmlopez0211-web.github.io/almendras-de-malaga/`
2. Verificar propiedad (el token ya presente en index.html debe corresponder a la cuenta que la verifica).
3. En Sitemaps, enviar:
   `https://jmlopez0211-web.github.io/almendras-de-malaga/sitemap.xml`
4. Usar Inspección de URL para la portada y las cinco páginas de captación del sitemap; solicitar indexación cuando proceda.
5. Revisar cobertura/indexación, páginas excluidas, canonical elegida por Google y errores.
6. En Rich Results Test / Schema Markup Validator, validar Store y FAQPage.
7. Comprobar la ficha de Google Business Profile: nombre, dirección, teléfono, horarios, categoría, fotos, URL y mapa. No publicar datos que no estén confirmados.
8. Conseguir reseñas auténticas de clientes; no comprarlas ni inventarlas.
9. Añadir enlaces desde redes sociales y perfiles comerciales hacia páginas relevantes.
10. Medir visitas, clics a WhatsApp y acciones del carrito. No afirmar conversiones sin instrumentación y consentimiento aplicable.

## Limitación técnica actual
El catálogo se genera con JavaScript desde `data/catalog.js`. Los motores que no ejecuten o no procesen JavaScript pueden no descubrir individualmente las 151 fichas como páginas indexables. La siguiente fase SEO de mayor impacto consiste en crear páginas HTML estáticas de categorías/productos prioritarios con contenido propio, canonical, title, description, imágenes verificadas y datos estructurados Product cuando haya datos fiables. No generar páginas de baja calidad automáticamente ni inventar disponibilidad, stock, ingredientes o precios finales.

## Criterios de contenido
- Mantener los precios como orientativos cuando corresponda.
- Confirmar disponibilidad y condiciones con el negocio.
- No afirmar ausencia de alérgenos ni trazas.
- No añadir datos comerciales, horarios o entregas sin confirmación.
- Fotografías: usar solo imágenes verificadas, con fuente y licencia documentadas.
