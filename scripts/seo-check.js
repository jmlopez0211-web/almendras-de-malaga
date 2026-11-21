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
 const rel=url.slice(baseUrl.length); const file=rel||"index.html";
 assert.ok(fs.existsSync(path.join(root,file)),"Archivo no existe: "+file);
 const html=fs.readFileSync(path.join(root,file),"utf8");
 assert.ok(/<title>[^<]{10,}<\/title>/i.test(html),"Title ausente: "+file);
 assert.ok(/<meta\s+name=["']description["']\s+content=["'][^"']{40,}["']/i.test(html),"Description ausente: "+file);
 assert.equal(canonical(html),url,"Canonical no coincide: "+file);
}
console.log("SEO audit OK | URLs sitemap: "+urls.length+" | robots | canonicals | titles | descriptions | Open Graph | Schema Store/FAQ");
