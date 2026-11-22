import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import {execFileSync} from "node:child_process";
import {fileURLToPath} from "node:url";
const generator=fileURLToPath(new URL("../scripts/generate-seo-pages.js",import.meta.url));
test("generador SEO produce páginas diferenciadas, enlaces de familia, Schema sin precios y conserva sitemap",()=>{
 const temp=fs.mkdtempSync(path.join(os.tmpdir(),"almendras-seo-"));
 try{
  fs.mkdirSync(path.join(temp,"data"),{recursive:true});
  const catalog={almendraCruda:{name:"Almendra cruda con piel",desc:"Almendra sin tostar, presentada con su piel.",tag:"Frutos secos",category:"frutos",price:13.2},pistacho:{name:"Pistacho tostado",desc:"Pistacho tostado.",tag:"Frutos secos",category:"frutos",price:29.8},mango:{name:"Mango deshidratado",desc:"Mango deshidratado.",tag:"Fruta deshidratada",category:"fruta",price:19.8}};
  fs.writeFileSync(path.join(temp,"data","catalog.js"),"window.PRODUCTS = "+JSON.stringify(catalog)+";\n");
  const home="https://jmlopez0211-web.github.io/almendras-de-malaga/";
  const landing=home+"frutos-secos-centro-malaga.html";
  fs.writeFileSync(path.join(temp,"sitemap.xml"),'<?xml version="1.0"?><urlset><url><loc>'+home+'</loc></url><url><loc>'+landing+'</loc></url></urlset>');
  const output=execFileSync(process.execPath,[generator],{cwd:temp,encoding:"utf8"});
  const productFiles=fs.readdirSync(path.join(temp,"productos"));
  const categoryFiles=fs.readdirSync(path.join(temp,"categorias"));
  assert.equal(productFiles.length,3);assert.equal(categoryFiles.length,2);
  assert.match(output,/Páginas de producto generadas: 3/);assert.match(output,/Páginas de categoría generadas: 2/);
  const almendraFile=productFiles.find(file=>file.includes("almendra-cruda"));
  const html=fs.readFileSync(path.join(temp,"productos",almendraFile),"utf8");
  assert.match(html,/<title>.*Almendra cruda.*Málaga.*<\/title>/);
  assert.match(html,/rel="canonical"/);assert.match(html,/BreadcrumbList/);
  assert.match(html,/Pistacho tostado/);assert.match(html,/productos de la misma familia/i);
  assert.match(html,/Consultar por WhatsApp/);assert.doesNotMatch(html,/13,20|13\.2|Offer/);
  const schemaBlocks=[...html.matchAll(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/g)].map(m=>JSON.parse(m[1]));
  const schema=schemaBlocks.find(s=>s["@type"]==="Product");
  assert.equal(schema.name,"Almendra cruda con piel");assert.equal("offers" in schema,false);
  const sitemap=fs.readFileSync(path.join(temp,"sitemap.xml"),"utf8");
  assert.ok(sitemap.includes(home));assert.ok(sitemap.includes(landing));assert.equal((sitemap.match(/<loc>/g)||[]).length,7);
 }finally{fs.rmSync(temp,{recursive:true,force:true});}
});
