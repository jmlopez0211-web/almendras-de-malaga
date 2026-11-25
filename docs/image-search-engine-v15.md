# Motor de búsqueda fotográfica v15.0

## Cambio de diseño
Se separan tres estados que antes se mezclaban:

- `candidate_identity_is_confirmed`: verifica la familia del producto y la identidad básica a partir del título/etiquetas.
- `candidate_variant_evidence_status`: devuelve `EXACT_VARIANT_EVIDENCE`, `VARIANT_UNSPECIFIED` o `CONTRADICTORY_VARIANT` para atributos como frito/tostado, con/sin sal, aceite y tipo de recubrimiento.
- `approval_passes_gates`: conserva el bloqueo final; exige identidad, documentación completa de derechos, fuente/titular y revisión visual humana.

## Efecto
Una imagen de macadamias sin información de sal puede descargarse para revisión visual como `VARIANT_UNSPECIFIED`; no se declara que sea macadamia frita sin sal. Una imagen que se identifica explícitamente como salada frente a una ficha sin sal se marca como contradicción y no entra en la cola. Los filtros de contexto irrelevante se mantienen.

## Fuentes
Se documentan fabricantes y distribuidores oficiales en `photo-review-20261125/fabricantes-distribuidores.json` y `.md`. Las páginas de producto solo verifican referencias comerciales; no conceden derechos de reutilización.

## Revisión visual
Hoja: `photo-review-20261125/index.html` y `candidatas-contact-sheet.jpg`. Manifiesto con origen, licencia declarada, dimensiones y SHA-256: `candidatas-manifest.json`. Ninguna candidata queda aprobada automáticamente.

No se modificó `data/catalog.js`, precios ni textos comerciales.

## Resultado del lote visual existente
- 22 archivos descargados vinculados a candidatos activos, incluidos en la hoja.
- 2 duplicados binarios exactos detectados por SHA-256.
- 4 archivos heredados quedaron fuera de la hoja principal por no estar vinculados a un manifiesto que acredite producto, fuente y licencia; se enumeran como huérfanos en el manifiesto.
- Cero imágenes aprobadas automáticamente.

## Selección depurada y proveedores
La hoja visual se redujo a 11 candidatos que pueden servir como identidad base y 11 archivos se apartaron por título/identidad errónea o no demostrable. La selección no afirma proceso, sal, aceite ni composición cuando la fuente no lo acredita. Se añadieron fuentes oficiales y una solicitud formal de derechos en `photo-review-20261125/`. Resultado de permisos: cero autorizaciones recibidas. COPAVAL e ITAC/Importaco tienen avisos legales que exigen consentimiento explícito / permiso escrito; el resto queda pendiente de respuesta escrita.
