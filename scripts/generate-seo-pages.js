import fs from "node:fs";
import path from "node:path";
import { buildProductContent, productTitle as seoProductTitle, productMetaDescription } from "./product-content-seo.js";

const BASE = "https://jmlopez0211-web.github.io/almendras-de-malaga/";
const CATALOG_PATH = path.join(process.cwd(), "data", "catalog.js");
if (!fs.existsSync(CATALOG_PATH)) throw new Error("No existe data/catalog.js. Ejecuta el comando desde la raíz del repositorio.");
const catalogSource = fs.readFileSync(CATALOG_PATH, "utf8");

function extractProducts(source) {
  const marker = source.indexOf("window.PRODUCTS");
  if (marker < 0) throw new Error("No se encontró window.PRODUCTS en data/catalog.js");
  const equals = source.indexOf("=", marker + "window.PRODUCTS".length);
  const start = source.indexOf("{", equals + 1);
  if (equals < 0 || start < 0) throw new Error("Asignación window.PRODUCTS inválida");
  let depth = 0, quote = null, escaped = false, end = -1;
  for (let i = start; i < source.length; i++) {
    const ch = source[i];
    if (quote) {
      if (escaped) escaped = false;
      else if (ch === "\\") escaped = true;
      else if (ch === quote) quote = null;
      continue;
    }
    if (ch === '"' || ch === "'") { quote = ch; continue; }
    if (ch === "{") depth++;
    else if (ch === "}" && --depth === 0) { end = i + 1; break; }
  }
  if (end < 0) throw new Error("Objeto window.PRODUCTS sin cierre");
  return JSON.parse(source.slice(start, end));
}

const products = extractProducts(catalogSource);
const entries = Object.entries(products);
if (!entries.length) throw new Error("El catálogo no contiene productos");
const escapeHtml = value => String(value ?? "").replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;").replaceAll('"',"&quot;").replaceAll("'","&#39;");
const slug = value => String(value ?? "").normalize("NFD").replace(/[\u0300-\u036f]/g,"").toLowerCase().replace(/ñ/g,"n").replace(/[^a-z0-9]+/g,"-").replace(/^-|-$/g,"");
const cleanText = value => String(value ?? "").replace(/\s+/g," ").trim();
const truncate = (value,max) => {
  const text=cleanText(value);
  if(text.length<=max)return text;
  const cut=text.slice(0,max-1).replace(/\s+\S*$/,"").trim();
  return cut+"…";
};
const today = new Date().toISOString().slice(0,10);
const productDir = path.join(process.cwd(),"productos");
const categoryDir = path.join(process.cwd(),"categorias");
// Keep the previous generated HTML so sitemap lastmod changes only when page content changes.
const previousGeneratedPages = new Map();
for (const [directory, prefix] of [[productDir,"productos"],[categoryDir,"categorias"]]) {
  if (!fs.existsSync(directory)) continue;
  for (const name of fs.readdirSync(directory)) {
    if (!name.endsWith(".html")) continue;
    const file = path.join(directory,name);
    if (fs.statSync(file).isFile()) previousGeneratedPages.set(prefix+"/"+name,fs.readFileSync(file,"utf8"));
  }
}
fs.rmSync(productDir,{recursive:true,force:true});
fs.rmSync(categoryDir,{recursive:true,force:true});
fs.mkdirSync(productDir,{recursive:true});
fs.mkdirSync(categoryDir,{recursive:true});

const generatedUrls=[];
const families=new Map();
const productFiles=new Map();
const usedProductFiles=new Set();
for(const [id,product] of entries){
  if(!product || !cleanText(product.name)) throw new Error("Producto sin nombre: "+id);
  const category=cleanText(product.tag||product.category||"Otros");
  let file=slug(id)+"-"+slug(product.name)+".html";
  if(usedProductFiles.has(file))file=slug(id)+".html";
  if(usedProductFiles.has(file))throw new Error("Colisión de URL: "+id);
  usedProductFiles.add(file);
  productFiles.set(id,file);
  if(!families.has(category))families.set(category,[]);
  families.get(category).push({id,product,file});
}

function metaDescription(product,id){ return productMetaDescription(product,id); }
function productTitle(product,id){ return seoProductTitle(product,id); }

function schemaForProduct(product,url,category){
  return {
    "@context":"https://schema.org",
    "@type":"Product",
    "name":cleanText(product.name),
    "description":cleanText(product.desc||product.name),
    "category":category,
    "url":url
  };
}
function breadcrumbSchema(items){
  return {"@context":"https://schema.org","@type":"BreadcrumbList","itemListElement":items.map((item,index)=>({"@type":"ListItem","position":index+1,"name":item.name,"item":item.url}))};
}
function jsonLd(value){return JSON.stringify(value).replaceAll("<","\\u003c");}
function navLinks(categoryUrl){
  return '<nav aria-label="Navegación principal"><a href="../index.html">Inicio</a> · <a href="../index.html#catalogo">Catálogo</a> · <a href="'+categoryUrl+'">Familia de productos</a></nav>';
}
function productPage(entry,category,categoryFile,related){
  const {id,product,file}=entry;
  const url=BASE+"productos/"+file;
  const categoryUrl=BASE+"categorias/"+categoryFile;
  const title=productTitle(product,id);
  const description=metaDescription(product,id);
  const content=buildProductContent(product,id,category,related);
  const desc=cleanText(product.desc||"Consulta la ficha de este producto en el catálogo.");
  const relatedHtml='<section aria-labelledby="related-title"><h2 id="related-title">Productos relacionados para comparar · productos de la misma familia</h2><p>'+escapeHtml(content.comparison)+'</p>'+(related.length?'<ul>'+related.map(item=>'<li><a href="'+item.file+'">'+escapeHtml(item.product.name)+'</a><span> — '+escapeHtml(cleanText(item.product.desc||"Consulta su ficha"))+'</span></li>').join("")+'</ul>':'<p>Consulta la categoría para explorar otras referencias.</p>')+'</section>';
  const otherFamilies=[...families.keys()].filter(name=>name!==category).sort((a,b)=>a.localeCompare(b,"es"));
  const familyLinks=otherFamilies.map(name=>'<li><a href="../categorias/'+categoryFiles.get(name)+'">'+escapeHtml(name)+'</a></li>').join("");
  const schemaProduct=schemaForProduct(product,url,category);
  const schemaBreadcrumb=breadcrumbSchema([{name:"Inicio",url:BASE},{name:"Catálogo",url:BASE+"index.html#catalogo"},{name:category,url:categoryUrl},{name:product.name,url}]);
  const schemaFaq={"@context":"https://schema.org","@type":"FAQPage","mainEntity":content.faq.map(item=>({"@type":"Question","name":item.q,"acceptedAnswer":{"@type":"Answer","text":item.a}}))};
  const whatsapp="https://wa.me/34666068765?text="+encodeURIComponent("Hola, quisiera consultar información, formatos y disponibilidad de "+product.name+".");
  const faqHtml='<section class="seo-faq" aria-labelledby="faq-title"><h2 id="faq-title">Preguntas frecuentes sobre '+escapeHtml(product.name)+'</h2>'+content.faq.map((item,index)=>'<details'+(index===0?' open':'')+'><summary>'+escapeHtml(item.q)+'</summary><p>'+escapeHtml(item.a)+'</p></details>').join("")+'</section>';
  const contentHtml='<section aria-labelledby="about-title"><h2 id="about-title">Conoce esta referencia</h2><p>'+escapeHtml(content.intro)+'</p></section><section aria-labelledby="family-title"><h2 id="family-title">Diferencias dentro de su familia</h2><p>'+escapeHtml(content.family)+'</p></section><section aria-labelledby="choose-title"><h2 id="choose-title">Cómo identificar y elegir esta presentación</h2><p>'+escapeHtml(content.selection)+'</p></section><section aria-labelledby="uses-title"><h2 id="uses-title">Ideas de uso</h2><p>'+escapeHtml(content.use)+'</p></section>';
  return '<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="index,follow"><meta name="description" content="'+escapeHtml(description)+'"><title>'+escapeHtml(title)+'</title><link rel="canonical" href="'+url+'"><meta property="og:type" content="product"><meta property="og:title" content="'+escapeHtml(title)+'"><meta property="og:description" content="'+escapeHtml(description)+'"><meta property="og:url" content="'+url+'"><meta name="twitter:card" content="summary"><meta name="twitter:title" content="'+escapeHtml(title)+'"><meta name="twitter:description" content="'+escapeHtml(description)+'"><script type="application/ld+json">'+jsonLd(schemaProduct)+'</script><script type="application/ld+json">'+jsonLd(schemaBreadcrumb)+'</script><script type="application/ld+json">'+jsonLd(schemaFaq)+'</script><link rel="stylesheet" href="../styles.css"><style>body{margin:0;background:#f7f3e9;color:#243b2e;font-family:Arial,sans-serif}.seo-card{max-width:900px;margin:28px auto;padding:clamp(20px,5vw,46px);background:#fffdf7;border:1px solid #e5d7b8;border-radius:22px}.seo-card h1{font-family:Georgia,serif;font-size:clamp(2rem,6vw,3.4rem);line-height:1.08}.seo-card h2{font-family:Georgia,serif;margin-top:2rem}.seo-card p,.seo-card li{line-height:1.7}.seo-actions{display:flex;gap:12px;flex-wrap:wrap;margin:24px 0}.seo-actions a{padding:13px 19px;border-radius:999px;background:#193f2e;color:white;text-decoration:none;font-weight:700}.seo-actions a.alt{background:#eadbb9;color:#243b2e}.seo-note{color:#6b705f;font-size:.9rem}.seo-card nav{margin-bottom:24px}.seo-card nav a{color:#24583b}.seo-faq details{border-top:1px solid #e5d7b8;padding:14px 0}.seo-faq summary{font-weight:700;cursor:pointer}.seo-card .product-description{font-size:1.15rem}.seo-card .eyebrow{letter-spacing:.08em;text-transform:uppercase;font-size:.8rem;color:#8a7549}</style></head><body><main class="seo-card"><header>'+navLinks('../categorias/'+categoryFile)+'</header><article><p class="eyebrow">Catálogo · '+escapeHtml(category)+'</p><h1>'+escapeHtml(product.name)+'</h1><p class="product-description">'+escapeHtml(desc)+'</p>'+contentHtml+'<div class="seo-actions"><a href="'+whatsapp+'" target="_blank" rel="noopener noreferrer">Consultar por WhatsApp</a><a class="alt" href="../index.html#catalogo">Ver catálogo completo</a></div><section aria-labelledby="details-title"><h2 id="details-title">Información confirmada en el catálogo</h2><p><strong>Familia:</strong> <a href="../categorias/'+categoryFile+'">'+escapeHtml(category)+'</a></p><p>'+escapeHtml(desc)+'</p><p>La ficha no añade precios, existencias, ingredientes, certificaciones, origen, valores nutricionales ni formatos que no estén confirmados específicamente para esta referencia.</p></section>'+relatedHtml+'<section aria-labelledby="purchase-title"><h2 id="purchase-title">Consulta y pedido</h2><p>Contacta con Almendras de Málaga para confirmar disponibilidad, cantidad, formatos y precio vigente antes de realizar el pedido.</p><p>Atención en Calle Santa María, 29, junto a la Catedral de Málaga.</p><div class="seo-actions"><a href="'+whatsapp+'" target="_blank" rel="noopener noreferrer">Consultar este producto</a><a class="alt" href="https://maps.app.goo.gl/a9Xq3G31MJhvYgRA8" target="_blank" rel="noopener noreferrer">Cómo llegar</a></div></section>'+faqHtml+'<section aria-labelledby="browse-title"><h2 id="browse-title">Explorar otras familias</h2><ul>'+familyLinks+'</ul></section><p class="seo-note">Información basada en la descripción disponible del catálogo. La ficha no confirma existencias ni condiciones comerciales.</p></article><footer><p><a href="../index.html">Volver a Almendras de Málaga</a></p></footer></main></body></html>';
}
function similarity(a,b){
  const nameA=cleanText(a.product.name).toLowerCase().split(/[^a-záéíóúñ]+/).filter(x=>x.length>3);
  const nameB=cleanText(b.product.name).toLowerCase().split(/[^a-záéíóúñ]+/).filter(x=>x.length>3);
  const common=nameA.filter(x=>nameB.includes(x)).length;
  const prepA=/cruda|tostada|frita|garrapiñada|pelada|cáscara|piel|sin sal|con sal/.exec(nameA.join(" "));
  const prepB=/cruda|tostada|frita|garrapiñada|pelada|cáscara|piel|sin sal|con sal/.exec(nameB.join(" "));
  const sameCategory=a.product.tag&&b.product.tag&&a.product.tag===b.product.tag?6:0;
  return common*10+sameCategory+(prepA&&prepB&&prepA[0]!==prepB[0]?2:0);
}
function selectRelated(entry,items){
  const sameFamily=items.filter(item=>item.id!==entry.id&&
    cleanText(item.product.tag||item.product.category||"Otros")===cleanText(entry.product.tag||entry.product.category||"Otros"));
  return sameFamily.sort((a,b)=>similarity(entry,b)-similarity(entry,a)||a.product.name.localeCompare(b.product.name,"es")).slice(0,8);
}
const categoryFiles=new Map();
const usedCategoryFiles=new Set();
for(const category of families.keys()){
  let file=slug(category)+".html";
  if(usedCategoryFiles.has(file))file=slug(category)+"-"+usedCategoryFiles.size+".html";
  usedCategoryFiles.add(file);categoryFiles.set(category,file);
}
for(const [category,items] of families){
  const categoryFile=categoryFiles.get(category);
  const categoryUrl=BASE+"categorias/"+categoryFile;
  const title=truncate("Comprar "+category+" en Málaga | Almendras de Málaga",65);
  const description=truncate("Explora "+category.toLowerCase()+" en el catálogo de Almendras de Málaga. Consulta cada ficha y confirma formatos, disponibilidad y precio por WhatsApp.",158);
  const links=items.map(item=>'<li><a href="../productos/'+item.file+'">'+escapeHtml(item.product.name)+'</a><p>'+escapeHtml(cleanText(item.product.desc||"Consulta la información de este producto."))+'</p></li>').join("");
  const listSchema={"@context":"https://schema.org","@type":"ItemList","name":category+" de Almendras de Málaga","itemListElement":items.map((item,index)=>({"@type":"ListItem","position":index+1,"url":BASE+"productos/"+item.file,"name":item.product.name}))};
  const html='<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="index,follow"><meta name="description" content="'+escapeHtml(description)+'"><title>'+escapeHtml(title)+'</title><link rel="canonical" href="'+categoryUrl+'"><meta property="og:title" content="'+escapeHtml(title)+'"><meta property="og:description" content="'+escapeHtml(description)+'"><meta property="og:url" content="'+categoryUrl+'"><meta name="twitter:card" content="summary"><meta name="twitter:title" content="'+escapeHtml(title)+'"><meta name="twitter:description" content="'+escapeHtml(description)+'"><script type="application/ld+json">'+jsonLd(listSchema)+'</script><link rel="stylesheet" href="../styles.css"><style>body{margin:0;background:#f7f3e9;color:#243b2e;font-family:Arial,sans-serif}.seo-card{max-width:900px;margin:28px auto;padding:clamp(20px,5vw,42px);background:#fffdf7;border:1px solid #e5d7b8;border-radius:22px}.seo-card h1{font-family:Georgia,serif;font-size:clamp(2rem,6vw,3.4rem)}.seo-card li{margin:14px 0}.seo-card a{color:#24583b}.seo-card p{line-height:1.6}</style></head><body><main class="seo-card"><nav aria-label="Navegación principal"><a href="../index.html">Inicio</a> · <a href="../index.html#catalogo">Catálogo</a></nav><header><p>Catálogo de Almendras de Málaga</p><h1>'+escapeHtml(category)+' en Málaga</h1><p>'+escapeHtml(description)+'</p><p>Selecciona una ficha para consultar la información disponible. Los datos comerciales y las condiciones se confirman directamente con el establecimiento.</p></header><section aria-labelledby="products-title"><h2 id="products-title">Productos de esta familia</h2><ul>'+links+'</ul></section><section><h2>Consulta y pedido</h2><p>Pregunta por disponibilidad, cantidades, formatos y precio vigente antes de confirmar tu compra.</p><p><a href="https://wa.me/34666068765?text='+encodeURIComponent("Hola, quisiera consultar productos de "+category+".")+'">Consultar por WhatsApp</a></p><p>Almendras de Málaga · Calle Santa María, 29, junto a la Catedral.</p></section><footer><p><a href="../index.html#catalogo">Volver al catálogo completo</a></p></footer></main></body></html>';
  fs.writeFileSync(path.join(categoryDir,categoryFile),html);
  generatedUrls.push(categoryUrl);
  for(const entry of items){
    const siblings=selectRelated(entry,entries.map(([id,product])=>({id,product,file:productFiles.get(id)})));
    const productUrl=BASE+"productos/"+entry.file;
    fs.writeFileSync(path.join(productDir,entry.file),productPage(entry,category,categoryFile,siblings));
    generatedUrls.push(productUrl);
  }
}
const sitemapPath=path.join(process.cwd(),"sitemap.xml");
const oldSitemap=fs.existsSync(sitemapPath)?fs.readFileSync(sitemapPath,"utf8"):"";
const oldUrlMetadata=new Map();
for (const match of oldSitemap.matchAll(/<url\b[^>]*>([\s\S]*?)<\/url>/g)) {
  const loc=match[1].match(/<loc>\s*([^<]+)\s*<\/loc>/);
  if (!loc) continue;
  const lastmod=match[1].match(/<lastmod>\s*([^<]+)\s*<\/lastmod>/);
  oldUrlMetadata.set(loc[1].trim(),lastmod?.[1].trim()||null);
}
const oldUrls=[...oldUrlMetadata.keys()];
const retainedUrls=oldUrls.filter(url=>url.startsWith(BASE)&&!url.startsWith(BASE+"productos/")&&!url.startsWith(BASE+"categorias/"));
const allUrls=[...new Set([...retainedUrls,...generatedUrls])];
function lastmodForUrl(url) {
  const oldLastmod=oldUrlMetadata.get(url);
  const isGenerated=url.startsWith(BASE+"productos/")||url.startsWith(BASE+"categorias/");
  if (!isGenerated) return oldLastmod||null;
  if (!oldLastmod) return today;
  const relativePath=url.slice(BASE.length);
  const oldHtml=previousGeneratedPages.get(relativePath);
  const currentPath=path.join(process.cwd(),...relativePath.split("/"));
  const currentHtml=fs.existsSync(currentPath)?fs.readFileSync(currentPath,"utf8"):null;
  return oldHtml!==undefined&&oldHtml===currentHtml ? oldLastmod : today;
}
const sitemapXml='<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'+allUrls.map(url=>{
  const lastmod=lastmodForUrl(url);
  return "  <url><loc>"+url+"</loc>"+(lastmod?"<lastmod>"+lastmod+"</lastmod>":"")+"</url>";
}).join("\n")+"\n</urlset>\n";
fs.writeFileSync(sitemapPath,sitemapXml);
console.log("Páginas de producto generadas: "+entries.length);
console.log("Páginas de categoría generadas: "+families.size);
console.log("URLs del sitemap: "+allUrls.length+" (conserva las landings existentes)");
