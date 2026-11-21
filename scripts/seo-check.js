import fs from "node:fs";
import path from "node:path";
import assert from "node:assert/strict";
const root=process.cwd();
const baseUrl="https://jmlopez0211-web.github.io/almendras-de-malaga/";
const sitemap=fs.readFileSync("sitemap.xml","utf8");
const robots=fs.readFileSync("robots.txt","utf8");
const index=fs.readFileSync("index.html","utf8");
const urls=[...sitemap.matchAll(/<loc>\s*([^<]+)\s*<\/loc>/g)].map(m=>m[1].trim());
function canonical(html){return html.match(/<link\s+rel=["']canonical["']\s+href=["']([^"']+)["']/i)?.[1]||null;}
assert.ok(urls.length>=6,"Sitemap: se esperan al menos seis URL");
assert.ok(robots.includes("Sitemap: "+baseUrl+"sitemap.xml"),"robots.txt declara sitemap");
assert.ok(index.includes('name="robots"'),"Meta robots portada");
assert.ok(index.includes('property="og:title"')&&index.includes('property="og:description"')&&index.includes('property="og:url"'),"Open Graph portada");
assert.ok(index.includes('name="twitter:card"'),"Twitter Card portada");
assert.ok(index.includes('"@type":"Store"'),"Schema Store");
assert.ok(index.includes('"@type":"FAQPage"'),"Schema FAQ");
assert.equal(canonical(index),baseUrl,"Canonical portada");
for(const url of urls){
 assert.ok(url.startsWith(baseUrl),"URL externa o base incorrecta: "+url);
 const rel=url.slice(baseUrl.length); const file=rel.endsWith("/")?rel+"index.html":(rel||"index.html");
 assert.ok(fs.existsSync(path.join(root,file)),"Archivo no existe: "+file);
 const html=fs.readFileSync(path.join(root,file),"utf8");
 assert.ok(/<title>[^<]{10,}<\/title>/i.test(html),"Title ausente: "+file);
 assert.ok(/<meta\s+name=["']description["']\s+content=["'][^"']{40,}["']/i.test(html),"Description ausente: "+file);
 assert.equal(canonical(html),url,"Canonical no coincide: "+file);
 if(rel.startsWith("productos/")){
  const marker='<script type="application/ld+json">';
  const jsonLdStart=html.indexOf(marker);
  assert.notEqual(jsonLdStart,-1,"JSON-LD ausente: "+file);
  const jsonLdEnd=html.indexOf("</script>",jsonLdStart+marker.length);
  assert.notEqual(jsonLdEnd,-1,"JSON-LD sin cierre: "+file);
  const jsonLd=html.slice(jsonLdStart+marker.length,jsonLdEnd);
  assert.ok(jsonLd,"JSON-LD ausente: "+file);
  const schema=JSON.parse(jsonLd);
  assert.equal(schema["@type"],"Product","Schema Product incorrecto: "+file);
  assert.equal(schema.url,url,"URL del producto no coincide: "+file);
  assert.equal(schema.offers?.["@type"],"Offer","Offer ausente: "+file);
  assert.equal(schema.offers?.url,url,"URL de Offer no coincide: "+file);
  assert.ok(Number.isFinite(Number(schema.offers?.price)) && Number(schema.offers.price)>=0,"Precio directo Offer ausente o inválido: "+file);
  assert.equal(schema.offers?.priceCurrency,"EUR","Moneda directa Offer incorrecta: "+file);
  const spec=schema.offers?.priceSpecification;
  assert.equal(spec?.["@type"],"UnitPriceSpecification","Precio unitario ausente: "+file);
  assert.ok(Number.isFinite(Number(spec?.price)) && Number(spec.price)>=0,"Precio no válido: "+file);
  assert.equal(spec?.priceCurrency,"EUR","Moneda incorrecta: "+file);
  assert.equal(spec?.referenceQuantity?.["@type"],"QuantitativeValue","Referencia de cantidad ausente: "+file);
  assert.equal(Number(spec.referenceQuantity.value),1,"La referencia debe ser un kilogramo: "+file);
  assert.equal(spec.referenceQuantity.unitCode,"KGM","La unidad debe ser kilogramo: "+file);
 }
}
for(const url of urls.filter(u=>u.includes("/blog/"))){
 const rel=url.slice(baseUrl.length);
 const html=fs.readFileSync(path.join(root,rel),"utf8");
 assert.ok(html.includes("BlogPosting")||html.includes('"@type":"Blog"'),"Schema Blog/BlogPosting ausente: "+rel);
 assert.ok(html.includes('property="og:type"'),"Open Graph type ausente: "+rel);
}

// Blog internal-link audit: every local href must resolve, and each article must link to a real product page.
const blogFiles=fs.readdirSync("blog").filter(f=>f.endsWith(".html"));
for(const file of blogFiles){
 const html=fs.readFileSync(path.join("blog",file),"utf8");
 for(const href of [...html.matchAll(/href=["']([^"']+)["']/g)].map(m=>m[1])){
  if(href.startsWith("https://")||href.startsWith("http://")||href.startsWith("mailto:")||href.startsWith("#")) continue;
  const clean=href.split("#")[0];
  if(!clean) continue;
  const target=path.resolve("blog",clean);
  assert.ok(fs.existsSync(target),"Enlace interno de blog roto: "+file+" -> "+href);
 }
 if(file!=="index.html"){
  assert.ok(html.includes("../productos/"),"Artículo sin enlace a producto real: "+file);
  assert.ok(urls.includes(baseUrl+"blog/"+file),"Artículo no incluido en sitemap: "+file);
 }
}
assert.ok(blogFiles.length>=14,"Blog: se esperan al menos 14 páginas incluyendo índice");

console.log("SEO audit OK | URLs sitemap: "+urls.length+" | robots | canonicals | titles | descriptions | Open Graph | Schema Store/FAQ/Product/Blog");
