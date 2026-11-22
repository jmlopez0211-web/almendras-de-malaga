# Motor fotográfico v13 — coherencia de sal y mezclas de pasas

## Hallazgos que motivan v13

### Cacahuete tostado repelado sin sal
El catálogo describe este producto como «Cacahuete tostado sin piel y sin sal». El candidato descargado tenía el título «Salt Roasted Peanut.jpg». La regla anterior detectaba «salted», «with salt» y «salty», pero no el término aislado «salt». El resultado era un falso positivo.

La v13 rechaza explícitamente salt, salt roasted, salt-roasted, salado y otras expresiones equivalentes en productos sin sal.

### Revuelto de tres pasas
La descripción real del catálogo es «Mezcla de pasas de tres variedades». El motor v12 lo trataba erróneamente como una mezcla de frutos secos y podía aceptar un trail mix con cacahuetes, nueces, arándanos y otros ingredientes.

La v13:
- Busca tres variedades de pasas, no una mezcla de frutos secos.
- Exige que título o etiquetas identifiquen pasas/raisins.
- Usa «three varieties», «three types», «varieties» y «tres variedades» como indicios adicionales.
- Rechaza trail mix, mezclas de frutos secos y otras frutas/semillas para esta ficha.
- Si la fuente no prueba las tres variedades, deja esa característica como no verificada; no la deduce de los píxeles.

## Informe por ejecución

Cada resultado incorpora engine_version y processed_at. Al terminar cada lote se imprime un resumen separado del informe histórico acumulado para evitar confundir candidatos antiguos con los resultados de la versión actual.

## Seguridad

- No se cambia data/catalog.js.
- No se modifican imágenes existentes.
- No se marca imageVerified.
- Los archivos permanecen como candidatos no aprobados.
- La licencia y la revisión visual siguen siendo obligatorias.
