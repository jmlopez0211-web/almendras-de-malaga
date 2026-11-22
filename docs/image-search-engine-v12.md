# Motor de búsqueda de imágenes v12 — identidad estricta del producto

## Hallazgos reales del lote v11

Los informes de Termux mostraron falsos positivos descargados:
- Cacahuete tostado repelado sin sal → cacahuete con cáscara y sal.
- Nuez caramelizada → pain au chocolat con nuez y caramelo.
- Revuelto especial → Comida espacial.
- Revuelto dulce M.ª Carmen → guiso de porotos con chorizo.
- Revuelto Delicias Virginia → barrita Nature Valley.
- Melón deshidratado → melón amargo.
- Nuez con chocolate con leche → arroz con leche y chocolate.
- Avellana con chocolate negro → tableta/barra de chocolate sin evidencia de avellana.

## Cambios de v12

1. La identidad del producto debe aparecer en el título de la imagen o en sus etiquetas. La descripción larga ya no puede demostrar por sí sola que el alimento esté presente.
2. Se utilizan coincidencias por palabras completas y frases; ya no se aceptan subcadenas accidentales.
3. Las mezclas exigen evidencia de una mezcla real (mixed nuts, nut mix, trail mix, etc.), no basta con que aparezca una palabra como nuts.
4. Las mezclas comerciales con composición no documentada reciben `blend_composition_unverified`; siguen siendo candidatas visuales, no fotografías aprobadas.
5. El «Revuelto dulce M.ª Carmen» se busca como mezcla dulce, siguiendo la denominación y descripción actuales del catálogo; no se presupone que sea un revuelto de frutos secos.
6. Se rechazan explícitamente:
   - cacahuetes con cáscara o sal para la ficha repelada sin sal;
   - variantes de sal contradictorias;
   - productos de aceite distinto al especificado cuando la fuente lo indica;
   - melón amargo para melón deshidratado;
   - pastelería con nueces como sustituto de nuez caramelizada;
   - guisos, barritas de cereales, comida espacial y platos preparados;
   - arroz con leche como nuez cubierta de chocolate;
   - barras de chocolate sin evidencia del fruto seco correspondiente.
7. Las variantes no demostrables visualmente siguen marcadas como pendientes de confirmación; no se infieren a partir de la fotografía.

## Seguridad

- No modifica `data/catalog.js`.
- No modifica URLs de imágenes existentes.
- No activa `imageVerified`.
- No aprueba ni publica candidatos.
- Mantiene la validación de licencia, autor, fuente, formato, resolución, tamaño y SHA-256.
- Cada candidato requiere inspección visual y revisión de licencia antes de incorporar.

## Pruebas

Se amplía `tests/test_catalog_candidate_precision.py` con regresiones basadas en falsos positivos observados en los lotes reales y con casos de aceptación para candidatos cuya variante (sal/aceite/preparación) no puede probarse mediante metadatos, pero cuyo alimento principal sí coincide.
