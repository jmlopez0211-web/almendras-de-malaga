# Clasificación del auditor SEO

El auditor separa hallazgos en tres niveles:

## Errores críticos
- HTTP no-200 para una URL del sitemap.
- Enlaces internos rotos.
- Canonical ausente, duplicado o incorrecto.
- Title o meta description ausentes.
- Sitemap o robots.txt inválidos.
- JSON-LD mal formado o datos estructurados obligatorios ausentes en una página cuyo tipo los requiere.

## Advertencias
- Datos estructurados incompletos.
- Metadatos sociales incompletos.
- Imágenes sin alt cuando corresponde.
- Contenido semántico insuficiente o duplicado.

## Oportunidades
- BreadcrumbList ausente en páginas donde no es requisito para indexación.
- FAQ u otros tipos Schema opcionales.
- Enriquecimiento semántico que no cambia la indexabilidad.

La ausencia de BreadcrumbList no debe bloquear la validación SEO ni presentarse como error de indexación. Si está presente, sí se valida su estructura mínima.

## Política de cambios
- No modificar masivamente fichas de producto que ya validan.
- Añadir Schema solo con datos verificables.
- Evitar Offer, precio o disponibilidad no confirmados.
- Validar cambios en una rama y mediante pruebas antes de fusionar.
