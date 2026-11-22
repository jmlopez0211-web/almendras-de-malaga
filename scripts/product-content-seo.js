import crypto from "node:crypto";

export const clean = value => String(value ?? "").replace(/\s+/g, " ").trim();
export const slug = value => clean(value).normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().replace(/ñ/g, "n").replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
export const escapeHtml = value => String(value ?? "").replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;").replaceAll("'", "&#39;");
export const truncate = (value, max) => {
  const text = clean(value);
  if (text.length <= max) return text;
  const cut = text.slice(0, max - 1).replace(/\s+\S*$/, "").trim();
  return cut + "…";
};
const variant = (id, count) => parseInt(crypto.createHash("sha256").update(String(id)).digest("hex").slice(0, 8), 16) % count;

function traits(product) {
  const name = clean(product.name);
  const desc = clean(product.desc);
  const all = (name + " " + desc).toLowerCase();
  const preparation = all.includes("cruda") ? "cruda" : all.includes("tostad") ? "tostada" : all.includes("frit") ? "frita" : all.includes("garrapiñ") || all.includes("caramelo") ? "dulce/caramelizada" : all.includes("deshidrat") ? "deshidratada" : "sin preparación especificada";
  const salt = all.includes("sin sal") ? "sin sal según la denominación del catálogo" : all.includes("con sal") || all.includes("salad") ? "con sal según la denominación del catálogo" : "sin información específica sobre sal";
  const shell = all.includes("con cáscara") || all.includes("con cascara") || all.includes("con piel") ? "con piel o cáscara, según el nombre del producto" : all.includes("pelad") || all.includes("repelad") || all.includes("sin piel") ? "sin piel o cáscara, según el nombre del producto" : "presentación que debe confirmarse en la ficha comercial";
  const format = all.includes("harina") ? "molida" : all.includes("filete") || all.includes("lamina") || all.includes("lámina") ? "laminada" : all.includes("granillo") || all.includes("troce") || all.includes("bastón") ? "troceada o cortada" : all.includes("mariposa") ? "en mitades" : "según la presentación indicada";
  const sweet = /garrapiñ|caramel|miel|chocolate|dulce/.test(all);
  const oil = all.includes("aceite de oliva") ? "aceite de oliva, indicado en el nombre o descripción del catálogo" : all.includes("aceite de girasol") ? "aceite de girasol, indicado en el nombre o descripción del catálogo" : "";
  return {name, desc, all, preparation, salt, shell, format, sweet, oil};
}

function familyContext(t) {
  const n=t.all;
  if(n.includes("almendra")) return "En las referencias de almendra, el catálogo reúne distintas formas de presentación: con piel o pelada, cruda, tostada, frita, Marcona y derivados como harina, filete, granillo o bastón. Esta ficha debe compararse con esas variantes según la preparación y el corte que necesites.";
  if(n.includes("cacahuete")||n.includes("maní")||n.includes("mani")) return "Las referencias de cacahuete del catálogo permiten comparar la presentación con o sin piel o cáscara y distintas preparaciones, como crudo, tostado, frito o garrapiñado. La denominación de cada ficha es la guía para distinguirlas.";
  if(n.includes("anacardo")) return "Dentro de las referencias de anacardo se pueden revisar las preparaciones crudas, fritas y tostadas, además de la presencia o ausencia de sal cuando aparece expresamente en el nombre. Consulta las fichas relacionadas para comparar las denominaciones.";
  if(n.includes("macadamia")) return "El catálogo incluye distintas preparaciones de macadamia. Comparar las fichas permite distinguir las referencias crudas, fritas, tostadas o garrapiñadas y las variantes con o sin sal que estén expresamente indicadas.";
  if(n.includes("avellana")) return "Las fichas de avellana permiten comparar referencias crudas y tostadas. La denominación y la descripción disponible son la base para distinguir la preparación de cada producto.";
  if(n.includes("nuez")||n.includes("pecana")) return "La familia de nueces reúne presentaciones diferentes, como nuez con cáscara, mitades, nuez pecana pelada o tostada y otras referencias identificadas por su nombre. Comprueba la ficha concreta para evitar confundir formatos.";
  if(n.includes("pistacho")) return "Las referencias de pistacho pueden diferenciarse por su presentación —con cáscara, pelado o mondado— y por la preparación indicada. Utiliza el nombre de cada ficha para comparar las opciones del catálogo.";
  if(n.includes("pipa")||n.includes("semilla")||n.includes("girasol")||n.includes("calabaza")) return "En las referencias de semillas y pipas, la denominación puede indicar tipo de semilla, preparación y condimento. Compara esos elementos expresamente indicados antes de elegir.";
  if(n.includes("garrapiñ")||n.includes("caramel")||n.includes("miel")||n.includes("chocolate")) return "Las especialidades dulces se agrupan por producto y cobertura o preparación indicada en su denominación. Consulta las referencias relacionadas y confirma ingredientes, alérgenos y detalles de elaboración con el establecimiento.";
  if(n.includes("deshidrat")||n.includes("fruta")) return "Las referencias de fruta deshidratada se distinguen por el tipo de fruta y la presentación recogida en el nombre. Para comparar ingredientes, tratamientos o posibles azúcares añadidos, consulta la etiqueta o al establecimiento.";
  return "La categoría agrupa referencias con nombres y descripciones diferentes. La comparación debe basarse en los datos que aparecen en cada ficha y en la confirmación del establecimiento cuando se necesiten características adicionales.";
}
const introTemplates = [
  t => `La referencia ${t.name} se identifica en el catálogo por su denominación y por la descripción disponible: ${t.desc}. Esta ficha ayuda a localizarla y a distinguirla de otras presentaciones de la misma familia.`,
  t => `Si buscas ${t.name.toLowerCase()}, aquí encontrarás la información que consta en el catálogo. La descripción comercial disponible es: ${t.desc}. Consulta las referencias relacionadas para comparar otras preparaciones o presentaciones.`,
  t => `Esta página está dedicada a ${t.name.toLowerCase()}. El catálogo la describe así: ${t.desc}. La denominación permite distinguir esta referencia de las alternativas que aparecen enlazadas más abajo.`,
  t => `Dentro del catálogo de Almendras de Málaga, ${t.name.toLowerCase()} cuenta con una ficha propia. La información publicada sobre el producto es: ${t.desc}. Para conocer detalles no recogidos aquí, es necesario consultarlos con el establecimiento.`
];
const selectionTemplates = [
  t => `Para elegir esta referencia, fíjate primero en el nombre del producto: indica ${t.preparation} y ${t.shell}. ${t.salt}. Si estás comparando productos, revisa también la descripción específica y pregunta por los detalles que no aparezcan confirmados.`,
  t => `La comparación debe partir de las características que sí están expresadas: preparación ${t.preparation}; presentación ${t.shell}; y ${t.salt}. No se atribuyen aquí ingredientes, procedencia, valores nutricionales ni características de elaboración que no consten en el catálogo.`,
  t => `Esta denominación permite identificar la preparación (${t.preparation}) y la presentación (${t.shell}). ${t.salt}. Antes de comprar, confirma con el negocio cualquier característica adicional que sea importante para tu elección.`
];
const useTemplates = [
  t => `En cocina, los frutos secos y sus derivados pueden utilizarse en aperitivos, recetas, desayunos o elaboraciones de repostería, según su forma y preparación. La presentación ${t.format} puede orientar la manera de incorporarla a una receta; comprueba que el corte o preparación se ajusta a lo que necesitas.`,
  t => `Como idea de uso general, esta referencia puede valorarse para recetas, aperitivos o preparaciones culinarias en las que encaje su presentación. ${t.format === "molida" ? "La forma molida puede resultar práctica en masas y mezclas." : t.format === "laminada" ? "El corte en láminas puede servir para decorar o incorporar a elaboraciones." : t.format === "troceada o cortada" ? "El formato cortado puede facilitar su incorporación a mezclas o recetas." : "El uso dependerá de la preparación concreta y de las preferencias de quien la consuma."} Estas sugerencias son ideas culinarias generales, no características comerciales confirmadas del producto.`,
  t => `La forma de presentación es un criterio útil al planificar una receta o un aperitivo. ${t.format === "molida" ? "Una textura molida se suele emplear en masas, rellenos y mezclas." : t.format === "laminada" ? "Las láminas se pueden utilizar como acabado o como ingrediente." : t.format === "troceada o cortada" ? "Los cortes pequeños pueden distribuirse en mezclas o elaboraciones." : "Puede considerarse para servir, combinar o utilizar en recetas según la preparación."} Adapta la elección a la receta y verifica cualquier detalle de ingredientes o alérgenos en el etiquetado.`
];
const compareTemplates = [
  (t, related) => related.length ? `Dentro de esta familia puedes comparar ${related.slice(0,3).map(x=>x.product.name).join(", ")}. Las diferencias que se pueden afirmar a partir de las denominaciones son las relativas a la preparación, presentación o ingredientes expresamente indicados. Consulta cada ficha y confirma los detalles comerciales antes de decidir.` : `No hay otras referencias de la misma familia enlazadas en esta generación. Puedes volver al catálogo y explorar las categorías para encontrar alternativas.`,
  (t, related) => related.length ? `También puedes revisar ${related.slice(0,3).map(x=>x.product.name).join(", ")}. Comparar los nombres y las descripciones permite localizar diferencias declaradas; no se presupone que sean equivalentes ni que compartan ingredientes o proceso.` : `Para encontrar opciones relacionadas, utiliza la navegación de catálogo y consulta las fichas de la categoría correspondiente.`
];
function faqFor(t, related, id) {
  const faq = [
    {q: `¿Qué es ${t.name.toLowerCase()}?`, a: `El catálogo identifica el producto como ${t.name}. La descripción disponible es: ${t.desc}. Para ampliar información sobre ingredientes, elaboración, procedencia o características concretas, consulta directamente con el establecimiento.`},
    {q: `¿En qué se diferencia de otras referencias?`, a: related.length ? `Puedes compararlo con ${related.slice(0,2).map(x=>x.product.name).join(" y ")}. Las diferencias verificables en esta web son las que figuran en los nombres y descripciones de cada ficha. Si necesitas comparar ingredientes, preparación o formato, solicita confirmación.` : `La ficha recoge la descripción disponible. Consulta el catálogo para localizar otras referencias y confirmar las diferencias específicas.`},
    {q: `¿Cómo puedo utilizarlo?`, a: `Como orientación culinaria general, los frutos secos y sus presentaciones pueden incorporarse a aperitivos, recetas o repostería según el corte y preparación. La ficha no prescribe un uso ni confirma propiedades nutricionales.`},
    {q: `¿Qué formatos, precio y disponibilidad tiene?`, a: `La web no confirma en esta ficha el precio vigente, las existencias ni los formatos específicos. Contacta con Almendras de Málaga para verificar cantidad, presentación, disponibilidad y condiciones antes de realizar el pedido.`}
  ];
  if (t.sweet) faq.splice(2,0,{q:"¿Es una referencia dulce?",a:`La denominación del catálogo indica ${t.name.toLowerCase()}. Para confirmar ingredientes, proporción de cobertura, alérgenos o detalles de elaboración, consulta el etiquetado o al establecimiento.`});
  if (t.oil) faq.splice(2,0,{q:"¿Qué aceite se indica?",a:`La descripción disponible menciona ${t.oil}. No se publican aquí proporciones, ingredientes completos ni información adicional que no esté confirmada.`});
  return faq.slice(0,5);
}
export function buildProductContent(product, id, category, related) {
  const t = traits(product), v = variant(id, 4);
  const intro = introTemplates[v](t);
  const selection = selectionTemplates[v % selectionTemplates.length](t);
  const use = useTemplates[(v + 1) % useTemplates.length](t);
  const comparison = compareTemplates[v % compareTemplates.length](t, related);
  const faq = faqFor(t, related, id);
  return {intro,selection,use,comparison,faq,traits:t};
}
export function productTitle(product,id) {
  const name=clean(product.name);
  const suffixes=[" | Almendras de Málaga"," en Málaga | Almendras de Málaga"," · Málaga | Almendras de Málaga"];
  const v=variant(id,suffixes.length);
  return truncate(name+suffixes[v],65);
}
export function productMetaDescription(product,id) {
  const t=traits(product),v=variant(id,4);
  const templates=[
    `${t.name}: ${t.desc} Consulta información, referencias relacionadas y disponibilidad en Almendras de Málaga.`,
    `Información de ${t.name.toLowerCase()}. ${t.desc} Compara presentaciones del catálogo y consulta el pedido en Málaga.`,
    `Descubre ${t.name.toLowerCase()} en el catálogo de Almendras de Málaga. ${t.desc} Consulta detalles y disponibilidad.`,
    `${t.name} en Málaga. ${t.desc} Revisa productos relacionados y confirma formatos y precio por WhatsApp.`
  ];
  return truncate(templates[v],158);
}
