import fs from "node:fs";
import path from "node:path";

const BASE = "https://jmlopez0211-web.github.io/almendras-de-malaga/";
const CATALOG_PATH = path.join(process.cwd(), "data", "catalog.js");
if (!fs.existsSync(CATALOG_PATH)) throw new Error("No existe data/catalog.js. Ejecuta el comando desde la raíz del repositorio.");
const catalogSource = fs.readFileSync(CATALOG_PATH, "utf8");

function extractProducts(source) {
  const marker = source.indexOf("window.PRODUCTS");
  if (marker < 0) throw new Error("No se encontró la asignación window.PRODUCTS en data/catalog.js");
  const equals = source.indexOf("=", marker + "window.PRODUCTS".length);
  const start = source.indexOf("{", equals + 1);
  if (equals < 0 || start < 0) throw new Error("La asignación window.PRODUCTS no contiene un objeto JSON");
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
    else if (ch === "}") { depth--; if (depth === 0) { end = i + 1; break; } }
  }
  if (end < 0) throw new Error("El objeto window.PRODUCTS tiene llaves sin cerrar");
  let parsed;
  try { parsed = JSON.parse(source.slice(start, end)); }
  catch (error) { throw new Error("El catálogo window.PRODUCTS no es JSON válido: " + error.message); }
  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) throw new Error("window.PRODUCTS debe ser un objeto de productos");
  return parsed;
}

const products = extractProducts(catalogSource);
const productEntries = Object.entries(products);
if (productEntries.length === 0) throw new Error("El catálogo no contiene productos");
const escapeHtml = value => String(value ?? "").replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;").replaceAll("'", "&#39;");
const slug = value => String(value ?? "").normalize("NFD").split("").filter(ch => { const code = ch.charCodeAt(0); return code < 768 || code > 879; }).join("").toLowerCase().replaceAll("ñ", "n").split("").map(ch => /[a-z0-9]/.test(ch) ? ch : "-").join("").replace(/-+/g, "-").replace(/^-|-$/g, "");
const euro = value => Number(value).toLocaleString("es-ES", {minimumFractionDigits:2, maximumFractionDigits:2}) + " €";
const today = new Date().toISOString().slice(0, 10);
const productDir = path.join(process.cwd(), "productos");
const categoryDir = path.join(process.cwd(), "categorias");
fs.rmSync(productDir, {recursive:true, force:true});
fs.rmSync(categoryDir, {recursive:true, force:true});
fs.mkdirSync(productDir, {recursive:true});
fs.mkdirSync(categoryDir, {recursive:true});
const generatedUrls = [];
const categories = new Map();
const usedProductFiles = new Set();

for (const [id, product] of productEntries) {
  if (!product || !product.name || !Number.isFinite(Number(product.price)) || Number(product.price) < 0) {
    throw new Error("Producto con nombre o precio inválido en el catálogo: " + id);
  }
  let filename = slug(id) + "-" + slug(product.name) + ".html";
  if (usedProductFiles.has(filename)) filename = slug(id) + ".html";
  if (usedProductFiles.has(filename)) throw new Error("Colisión de URL para producto: " + id);
  usedProductFiles.add(filename);
  const url = BASE + "productos/" + filename;
  const category = String(product.tag || product.category || "Otros");
  const title = String(product.name) + " | Almendras de Málaga";
  const description = ("Consulta " + product.name + " en Almendras de Málaga. Precio orientativo " + euro(product.price) + " por kilogramo. Formatos y disponibilidad por WhatsApp.").slice(0, 160);
  const whatsapp = "https://wa.me/34666068765?text=" + encodeURIComponent("Hola, quisiera consultar disponibilidad, formatos y precio de " + product.name + ".");
  const schema = {"@context":"https://schema.org","@type":"Product","name":product.name,"description":product.desc || product.name,"category":category,"url":url,"offers":{"@type":"Offer","url":url,"price":Number(Number(product.price).toFixed(2)),"priceCurrency":"EUR","priceSpecification":{"@type":"UnitPriceSpecification","price":Number(Number(product.price).toFixed(2)),"priceCurrency":"EUR","referenceQuantity":{"@type":"QuantitativeValue","value":1,"unitCode":"KGM"}}}};
  const schemaJson = JSON.stringify(schema).replaceAll("<", "\\u003c");
  const html = '<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="index,follow"><meta name="description" content="' + escapeHtml(description) + '"><title>' + escapeHtml(title) + '</title><link rel="canonical" href="' + url + '"><meta property="og:type" content="product"><meta property="og:title" content="' + escapeHtml(title) + '"><meta property="og:description" content="' + escapeHtml(description) + '"><meta property="og:url" content="' + url + '"><script type="application/ld+json">' + schemaJson + '</script><link rel="stylesheet" href="../styles.css"><style>body{margin:0;background:#f7f3e9;color:#243b2e;font-family:Arial,sans-serif}.seo-card{max-width:780px;margin:28px auto;padding:clamp(20px,5vw,46px);background:#fffdf7;border:1px solid #e5d7b8;border-radius:22px}.seo-card h1{font-family:Georgia,serif;font-size:clamp(2rem,6vw,3.4rem);line-height:1.08}.seo-price{font-size:1.5rem;font-weight:700}.seo-actions{display:flex;gap:12px;flex-wrap:wrap;margin:24px 0}.seo-actions a{padding:13px 19px;border-radius:999px;background:#193f2e;color:white;text-decoration:none;font-weight:700}.seo-actions a.alt{background:#eadbb9;color:#243b2e}.seo-note{color:#6b705f;font-size:.9rem}</style></head><body><main class="seo-card"><p><a href="../index.html">Inicio</a> · <a href="../index.html#catalogo">Catálogo</a> · ' + escapeHtml(category) + '</p><h1>' + escapeHtml(product.name) + '</h1><p>' + escapeHtml(product.desc || "Consulta este producto en nuestro catálogo.") + '</p><p class="seo-price">' + euro(product.price) + ' / kg</p><p>Precio orientativo por kilogramo, tomado del catálogo. Consulta el formato, la disponibilidad y el precio final antes de confirmar el pedido.</p><div class="seo-actions"><a href="' + whatsapp + '" target="_blank" rel="noopener">Consultar por WhatsApp</a><a class="alt" href="../index.html#catalogo">Ver catálogo completo</a></div><h2>Formatos y pedidos</h2><p>Consulta formatos de 100 g, 250 g, 500 g, 1 kg, 5 kg, 10 kg y 20 kg, además de pedidos de mayor volumen. Los formatos disponibles y las condiciones se confirman con el negocio.</p><h2>Almendras de Málaga</h2><p>Estamos en Calle Santa María, 29, esquina con calle Molina Lario, junto a la Catedral de Málaga. Contacta con el negocio para confirmar las condiciones de este producto.</p><p class="seo-note">La información procede del catálogo y puede cambiar. Esta página no confirma existencias ni precio final.</p><div class="seo-actions"><a href="https://maps.app.goo.gl/a9Xq3G31MJhvYgRA8" target="_blank" rel="noopener">Cómo llegar</a><a class="alt" href="../index.html">Volver a la tienda</a></div></main></body></html>';
  fs.writeFileSync(path.join(productDir, filename), html);
  generatedUrls.push(url);
  if (!categories.has(category)) categories.set(category, []);
  categories.get(category).push({product, filename});
}

const usedCategoryFiles = new Set();
for (const [category, items] of categories) {
  let filename = slug(category) + ".html";
  if (usedCategoryFiles.has(filename)) filename = slug(category) + "-" + usedCategoryFiles.size + ".html";
  usedCategoryFiles.add(filename);
  const url = BASE + "categorias/" + filename;
  const title = "Comprar " + category + " en Málaga | Almendras de Málaga";
  const description = ("Consulta nuestra selección de " + category.toLowerCase() + " en Almendras de Málaga. Catálogo, precios orientativos y contacto directo.").slice(0,160);
  const itemList = items.map(({product, filename: productFile}) => '<li><a href="../productos/' + productFile + '">' + escapeHtml(product.name) + '</a> — ' + euro(product.price) + ' / kg orientativo</li>').join("");
  const html = '<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="index,follow"><meta name="description" content="' + escapeHtml(description) + '"><title>' + escapeHtml(title) + '</title><link rel="canonical" href="' + url + '"><meta property="og:title" content="' + escapeHtml(title) + '"><meta property="og:description" content="' + escapeHtml(description) + '"><meta property="og:url" content="' + url + '"><link rel="stylesheet" href="../styles.css"><style>body{margin:0;background:#f7f3e9;color:#243b2e;font-family:Arial,sans-serif}.seo-card{max-width:900px;margin:28px auto;padding:clamp(20px,5vw,42px);background:#fffdf7;border:1px solid #e5d7b8;border-radius:22px}.seo-card h1{font-family:Georgia,serif;font-size:clamp(2rem,6vw,3.4rem)}.seo-card li{margin:10px 0}.seo-card a{color:#24583b}</style></head><body><main class="seo-card"><p><a href="../index.html">Inicio</a> · <a href="../index.html#catalogo">Catálogo</a></p><h1>' + escapeHtml(category) + ' en Málaga</h1><p>' + escapeHtml(description) + '</p><p>Consulta los productos de esta familia, sus formatos y las condiciones de compra. Los precios mostrados son orientativos y la disponibilidad debe confirmarse.</p><ul>' + itemList + '</ul><p><a href="https://wa.me/34666068765?text=' + encodeURIComponent("Hola, quisiera consultar productos de " + category + ".") + '">Consultar por WhatsApp</a></p><p>Almendras de Málaga · Calle Santa María, 29, junto a la Catedral.</p><p><a href="../index.html#catalogo">Volver al catálogo completo</a></p></main></body></html>';
  fs.writeFileSync(path.join(categoryDir, filename), html);
  generatedUrls.push(url);
}

const sitemapPath = path.join(process.cwd(), "sitemap.xml");
const oldSitemap = fs.existsSync(sitemapPath) ? fs.readFileSync(sitemapPath, "utf8") : "";
const oldUrls = oldSitemap.split("<loc>").slice(1).map(part => part.split("</loc>")[0].trim()).filter(Boolean);
const retainedUrls = oldUrls.filter(url => url.startsWith(BASE) && !url.startsWith(BASE + "productos/") && !url.startsWith(BASE + "categorias/"));
const allUrls = [...new Set([...retainedUrls, ...generatedUrls])];
const sitemapXml = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + allUrls.map(url => "  <url><loc>" + url + "</loc><lastmod>" + today + "</lastmod></url>").join("\n") + "\n</urlset>\n";
fs.writeFileSync(sitemapPath, sitemapXml);

console.log("Páginas de producto generadas: " + productEntries.length);
console.log("Páginas de categoría generadas: " + categories.size);
console.log("URLs del sitemap: " + allUrls.length + " (incluye portada y landings SEO existentes)");