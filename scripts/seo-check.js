import fs from "node:fs";
import path from "node:path";
import assert from "node:assert/strict";

const baseUrl="https://jmlopez0211-web.github.io/almendras-de-malaga/";
const sitemap=fs.readFileSync("sitemap.xml","utf8");
const robots=fs.readFileSync("robots.txt","utf8");
const urls=[...sitemap.matchAll(/<loc>\s*([^<]+)\s*<\/loc>/g)].map(m=>m[1].trim());
assert.ok(urls.length>=6,"Sitemap debe contener páginas de producto y landings");
assert.equal(new Set(urls).size,urls.length,"Sitemap contiene URLs duplicadas");
assert.ok(robots.includes("Sitemap: "+baseUrl+"sitemap.xml"),"robots.txt debe declarar sitemap");

const canonical=html=>html.match(/<link\s+rel=["']canonical["']\s+href=["']([^"']+)["']/i)?.[1]||null;
const getMeta=(html,name)=>html.match(new RegExp('<meta\\s+(?:name|property)=["\\']'+name+'["\\']\\s+content=["\\']([^"\\']+)["\\']','i'))?.[1]||"";
const productTitles=new Set(),productDescriptions=new Set(),contentHashes=new Set();
let products=0,categories=0,shortContent=0,faqCount=0,relatedLinkCount=0;

for(const url of urls){
 assert.ok(url.startsWith(baseUrl),"URL fuera del dominio: "+url);
 const rel=url.slice(baseUrl.length);
 const file=rel.endsWith("/")?rel+"index.html":(rel||"index.html");
 assert.ok(fs.existsSync(file),"Archivo del sitemap no existe: "+file);
 const html=fs.readFileSync(file,"utf8");
 const title=html.match(/<title>([^<]+)<\/title>/i)?.[1]||"";
 const description=html.match(/<meta\s+name=["']description["']\s+content=["']([^"']+)["']/i)?.[1]||"";
 assert.ok(title.length>=10&&title.length<=100,"Title ausente o demasiado largo: "+file);
 assert.ok(description.length>=40&&description.length<=160,"Meta description ausente o fuera de longitud: "+file);
 assert.equal(canonical(html),url,"Canonical incorrecta: "+file);

 if(rel.startsWith("productos/")||rel.startsWith("categorias/")){
  assert.ok(html.includes('property="og:title"')&&html.includes('property="og:description"')&&html.includes('property="og:url"'),"Open Graph incompleto: "+file);
  assert.ok(html.includes('name="twitter:card"'),"Twitter Card ausente: "+file);
 }
 if(rel.startsWith("productos/")){
  products++;
  assert.ok(title.length<=65,"Title de producto supera 65 caracteres: "+title);
  assert.ok(!productTitles.has(title),"Title de producto duplicado: "+title);productTitles.add(title);
  assert.ok(!productDescriptions.has(description),"Meta description de producto duplicada: "+description);productDescriptions.add(description);
  const blocks=[...html.matchAll(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/g)].map(m=>JSON.parse(m[1]));
  const product=blocks.find(x=>x["@type"]==="Product");
  const breadcrumb=blocks.find(x=>x["@type"]==="BreadcrumbList");
  const faq=blocks.find(x=>x["@type"]==="FAQPage");
  assert.ok(product,"Schema Product ausente: "+file);
  assert.equal(product.url,url,"Product URL incorrecta: "+file);
  assert.ok(product.name&&product.description&&product.category,"Product Schema incompleto: "+file);
  assert.ok(!("offers" in product)&&!("price" in product),"No debe publicar Offer/precio no verificado: "+file);
  assert.ok(breadcrumb&&breadcrumb.itemListElement.length>=3,"BreadcrumbList incompleto: "+file);
  assert.ok(faq&&faq.mainEntity.length>=3,"FAQPage Schema ausente o incompleto: "+file);
  assert.ok(html.includes("Productos relacionados para comparar"),"Falta sección de enlaces relacionados: "+file);
  const related=[...html.matchAll(/href=["']([^"']+)["'][^>]*>([^<]+)<\/a>/g)].filter(m=>m[1].endsWith(".html")&&m[1].startsWith("")).length;
  relatedLinkCount+=related;
  const text=html.replace(/<script[\s\S]*?<\/script>/g," ").replace(/<style[\s\S]*?<\/style>/g," ").replace(/<[^>]+>/g," ").replace(/\s+/g," ").trim();
  assert.ok(text.length>=900,"Contenido demasiado corto: "+file+" ("+text.length+" caracteres)");
  assert.ok(html.includes("Diferencias dentro de su familia"),"Falta contenido específico de familia: "+file);
  assert.ok(html.includes("Cómo identificar y elegir esta presentación"),"Falta guía de elección: "+file);
  assert.ok(html.includes("Ideas de uso"),"Falta contenido de usos: "+file);
  assert.ok(html.includes("Preguntas frecuentes sobre"),"FAQ visible ausente: "+file);
  const contentFingerprint=html.match(/<section aria-labelledby="about-title">([\s\S]*?)<\/section>/)?.[1]||"";
  assert.ok(contentFingerprint.length>0,"Intro SEO ausente: "+file);
  assert.ok(!contentHashes.has(contentFingerprint),"Contenido introductorio duplicado: "+file);contentHashes.add(contentFingerprint);
  faqCount+=faq.mainEntity.length;
  const localLinks=[...html.matchAll(/href=["']([^"']+)["']/g)].map(m=>m[1]).filter(h=>!h.startsWith("http")&&!h.startsWith("#")&&!h.startsWith("mailto:"));
  for(const href of localLinks){const target=path.resolve(path.dirname(file),href.split("#")[0]);if(href.split("#")[0])assert.ok(fs.existsSync(target),"Enlace interno roto en "+file+": "+href);}
 }
 if(rel.startsWith("categorias/"))categories++;
}
assert.ok(products>0,"Sitemap sin fichas de producto");
assert.ok(categories>0,"Sitemap sin páginas de categoría");
console.log("SEO CONTENT AUDIT OK | "+products+" productos | "+categories+" categorías | "+productTitles.size+" titles únicos | "+productDescriptions.size+" meta descriptions únicas | "+faqCount+" FAQ | contenido ampliado | Schema sin Offer | canonical | OG | Twitter | enlaces internos");
