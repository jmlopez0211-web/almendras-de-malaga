import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import {execFileSync} from "node:child_process";
import {fileURLToPath} from "node:url";
const generator=fileURLToPath(new URL("../scripts/generate-seo-pages.js",import.meta.url));

test("generador SEO diferencia fichas, conserva el sitemap y mantiene lastmod solo en cambios significativos",()=>{
 const temp=fs.mkdtempSync(path.join(os.tmpdir(),"almendras-seo-"));
 try{
  fs.mkdirSync(path.join(temp,"data"),{recursive:true});
  const catalog={
   almendraCruda:{name:"Almendra cruda con piel",desc:"Almendra sin tostar, presentada con su piel.",tag:"Frutos secos",category:"frutos",price:13.2},
   pistacho:{name:"Pistacho tostado",desc:"Pistacho tostado.",tag:"Frutos secos",category:"frutos",price:29.8},
   mango:{name:"Mango deshidratado",desc:"Mango deshidratado.",tag:"Fruta deshidratada",category:"fruta",price:19.8}
  };
  fs.writeFileSync(path.join(temp,"data","catalog.js"),"window.PRODUCTS = "+JSON.stringify(catalog)+";\n");
  const home="https://jmlopez0211-web.github.io/almendras-de-malaga/";
  const landing=home+"frutos-secos-centro-malaga.html";
  fs.writeFileSync(path.join(temp,"sitemap.xml"),
   '<?xml version="1.0"?><urlset><url><loc>'+home+'</loc><lastmod>2021-02-03</lastmod></url>'+
   '<url><loc>'+landing+'</loc><lastmod>2020-04-05</lastmod></url></urlset>');
  const runGenerator=()=>execFileSync(process.execPath,[generator],{cwd:temp,encoding:"utf8"});
  const lastmodFor=(xml,url)=>{
   const entry=[...xml.matchAll(/<url><loc>([^<]+)<\/loc>(?:<lastmod>([^<]+)<\/lastmod>)?<\/url>/g)].find(match=>match[1]===url);
   return entry?.[2]||null;
  };

  const output=runGenerator();
  const productFiles=fs.readdirSync(path.join(temp,"productos"));
  const categoryFiles=fs.readdirSync(path.join(temp,"categorias"));
  assert.equal(productFiles.length,3);
  assert.equal(categoryFiles.length,2);
  assert.match(output,/Páginas de producto generadas: 3/);
  assert.match(output,/Páginas de categoría generadas: 2/);

  const almendraFile=productFiles.find(file=>file.includes("almendra-cruda"));
  const html=fs.readFileSync(path.join(temp,"productos",almendraFile),"utf8");
  assert.match(html,/<title>.*Almendra cruda.*Málaga.*<\/title>/);
  assert.match(html,/rel="canonical"/);
  assert.match(html,/BreadcrumbList/);
  assert.match(html,/Pistacho tostado/);
  assert.match(html,/productos de la misma familia/i);
  assert.match(html,/Consultar por WhatsApp/);
  assert.doesNotMatch(html,/13,20|13\.2|Offer/);
  const schemaBlocks=[...html.matchAll(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/g)].map(m=>JSON.parse(m[1]));
  const schema=schemaBlocks.find(s=>s["@type"]==="Product");
  assert.equal(schema.name,"Almendra cruda con piel");
  assert.equal("offers" in schema,false);

  let sitemap=fs.readFileSync(path.join(temp,"sitemap.xml"),"utf8");
  assert.ok(sitemap.includes(home));
  assert.ok(sitemap.includes(landing));
  assert.equal((sitemap.match(/<loc>/g)||[]).length,7);
  assert.equal(lastmodFor(sitemap,home),"2021-02-03");
  assert.equal(lastmodFor(sitemap,landing),"2020-04-05");

  // Simulate unchanged generated pages with an older trustworthy modification date.
  sitemap=sitemap.replace(/<url><loc>([^<]+)<\/loc>(?:<lastmod>[^<]+<\/lastmod>)?<\/url>/g,(entry,url)=>{
   return url.startsWith(home+"productos/")||url.startsWith(home+"categorias/")
    ? '<url><loc>'+url+'</loc><lastmod>2020-01-01</lastmod></url>'
    : entry;
  });
  fs.writeFileSync(path.join(temp,"sitemap.xml"),sitemap);
  runGenerator();
  const stableSitemap=fs.readFileSync(path.join(temp,"sitemap.xml"),"utf8");
  const almendraUrl=home+"productos/"+almendraFile;
  const pistachoFile=productFiles.find(file=>file.includes("pistacho"));
  const pistachoUrl=home+"productos/"+pistachoFile;
  const mangoFile=productFiles.find(file=>file.includes("mango"));
  const mangoUrl=home+"productos/"+mangoFile;
  assert.equal(lastmodFor(stableSitemap,almendraUrl),"2020-01-01");
  assert.equal(lastmodFor(stableSitemap,pistachoUrl),"2020-01-01");
  assert.equal(lastmodFor(stableSitemap,mangoUrl),"2020-01-01");
  assert.equal(lastmodFor(stableSitemap,home),"2021-02-03");
  assert.equal(lastmodFor(stableSitemap,landing),"2020-04-05");

  // A source-description edit changes the affected product page, but not unrelated product pages.
  catalog.almendraCruda.desc="Almendra cruda con piel; descripción revisada para la prueba de lastmod.";
  fs.writeFileSync(path.join(temp,"data","catalog.js"),"window.PRODUCTS = "+JSON.stringify(catalog)+";\n");
  runGenerator();
  const changedSitemap=fs.readFileSync(path.join(temp,"sitemap.xml"),"utf8");
  assert.notEqual(lastmodFor(changedSitemap,almendraUrl),"2020-01-01");
  assert.notEqual(lastmodFor(changedSitemap,pistachoUrl),"2020-01-01");
  assert.equal(lastmodFor(changedSitemap,mangoUrl),"2020-01-01");
  assert.equal(lastmodFor(changedSitemap,home),"2021-02-03");
  assert.equal(lastmodFor(changedSitemap,landing),"2020-04-05");
 }finally{
  fs.rmSync(temp,{recursive:true,force:true});
 }
});
