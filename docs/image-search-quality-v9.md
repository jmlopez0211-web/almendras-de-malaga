# Precisión del motor fotográfico v9

## Problema que corrige

La auditoría del lote de Termux detectó falsos positivos: una receta con piñones, donuts con miel, manzanas de caramelo, toffees de otra marca, escenas de tienda y fotografías de otros dulces alcanzaban el umbral de relevancia por compartir solo una palabra con el producto.

## Mejoras

- La puntuación ahora incorpora título, descripción y etiquetas de las fuentes.
- Wikimedia Commons aporta `ImageDescription`; Openverse aporta `description` cuando está disponible.
- Se rechazan contextos de recetas, platos salados, restaurantes, tiendas, mercados, envases, etiquetas y marcas ajenas identificadas en la auditoría.
- Las variantes de chocolate exigen evidencia explícita del tipo de cobertura y del ingrediente base.
- Pictolín exige evidencia de marca, sabor y estado de azúcar; las versiones con azúcar rechazan metadatos que las identifiquen como sin azúcar.
- Café Dry sin azúcar requiere indicación explícita de azúcar-free/sin azúcar; una foto genérica de caramelos no pasa.
- Carachoco, Toffino, Toffee nata, Taco de miel y Ligero piñones exigen evidencia de producto y tipo de confitería, no solo una palabra común.
- Las mezclas con chocolate requieren mención de la mezcla y de los componentes; las pipas con chocolate requieren evidencia de cobertura, no basta un trail mix con pepitas de chocolate.
- Los cacahuetes con chocolate negro requieren evidencia de chocolate negro, y no se aceptan cacahuetes cubiertos con pasas u otros ingredientes como equivalentes.

## Pruebas

`tests/test_catalog_candidate_precision.py` verifica falsos positivos observados en la auditoría:
- plato de piñones con anchoa y pimiento;
- donuts con miel;
- manzana de caramelo;
- marca de anís distinta de Pictolín;
- botella de toffee;
- dulces de café no identificados;
- escena de tienda;
- cacahuetes sin evidencia de cobertura negra;
- trail mix;
- toffee de otra marca;
- escena de mercado.

También comprueba coincidencias positivas explícitas para Taco de miel, Pictolín anís sin azúcar y almendras fritas en aceite de girasol.

## Alcance y seguridad

- No modifica imágenes del catálogo ni `imageVerified`.
- No descarga ni publica imágenes automáticamente.
- Los candidatos deben seguir pasando revisión visual, procedencia y licencia.
- Los atributos invisibles (sal, aceite, azúcar) no se deducen de los píxeles; se exige evidencia textual o documental.
- Es preferible no mostrar una foto antes que mostrar una foto de otro producto.
