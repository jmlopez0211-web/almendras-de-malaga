import fs from "node:fs";
import path from "node:path";

const sitemapPath = "sitemap.xml";
const base = "https://jmlopez0211-web.github.io/almendras-de-malaga/";
const sitemap = fs.readFileSync(sitemapPath, "utf8");
const urls = [...sitemap.matchAll(/<loc>\\s*([^<]+)\\s*<\\/loc>/g)].map(m => m[1].trim()).filter(u => u.startsWith(base + "productos/"));
let checked = 0, fixed = 0, valid = 0, errors = [];

for (const url of urls) {
  const file = path.join(process.cwd(), url.slice(base.length));
  if (!fs.existsSync(file)) { errors.push("Archivo no existe: " + file); continue; }
  const html = fs.readFileSync(file, "utf8");
  const marker = '<script type="application/ld+json">';
  const start = html.indexOf(marker);
  const end = start < 0 ? -1 : html.indexOf("</script>", start + marker.length);
  if (start < 0 || end < 0) { errors.push("JSON-LD ausente: " + file); continue; }
  let schema;
  try { schema = JSON.parse(html.slice(start + marker.length, end)); }
  catch { errors.push("JSON-LD inválido: " + file); continue; }
  checked++;
  const offer = schema.offers;
  const spec = offer?.priceSpecification;
  if (offer && offer.price == null && Number.isFinite(Number(spec?.price)) && spec?.priceCurrency) {
    offer.price = Number(Number(spec.price).toFixed(2));
    offer.priceCurrency = spec.priceCurrency;
    const json = JSON.stringify(schema).replaceAll("<", "\\u003c");
    const updated = html.slice(0, start + marker.length) + json + html.slice(end);
    fs.writeFileSync(file, updated);
    fixed++;
    console.log("CORREGIDO " + path.relative(process.cwd(), file) + " | " + offer.price + " " + offer.priceCurrency);
  } else if (offer && Number.isFinite(Number(offer.price)) && offer.priceCurrency === "EUR") {
    valid++;
    console.log("VÁLIDO (sin cambios) " + path.relative(process.cwd(), file));
  } else {
    errors.push("No se puede corregir automáticamente sin inventar datos: " + file);
  }
}
console.log("\\nAUDITORÍA: " + checked + " páginas revisadas | " + fixed + " corregidas | " + valid + " ya válidas | " + errors.length + " incidencias.");
if (errors.length) { errors.forEach(e => console.error(e)); process.exitCode = 1; }
