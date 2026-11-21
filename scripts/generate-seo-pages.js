import fs from "node:fs";
import path from "node:path";

const BASE = "https://jmlopez0211-web.github.io/almendras-de-malaga/";
const match = catalogSource.match(/window\.PRODUCTS\s*=\s*(\{[\s\S]*\})\s*;?\s*$/);
const match = catalogSource.match(/window\\.PRODUCTS\\s*=\\s*(\\{[\\s\\S]*\\})\\s*;?\\s*$/);
if (!match) throw new Error("No se pudo extraer window.PRODUCTS de data/catalog.js");
const products = JSON.parse(match[1]);

const esc = value => String(value ?? "").replace(/[&<>"']/g, char => ({
  "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
}[char]));
const slug = value => String(value).normalize("NFD").replace(/[\\u0300-\\u036f]/g, "")
  .toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
const euro = value => Number(value).toLocaleString("es-ES", { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + " €";
const date = new Date().toISOString().slice(0, 10);
const productDir = "productos", categoryDir = "categorias";
fs.mkdirSync(productDir, { recursive: true });
fs.mkdirSync(categoryDir, { recursive: true });
const urls = [BASE], categories = new Map();

for (const [id, product] of Object.entries(products)) {
  const filename = slug(id) + "-" + slug(product.name) + ".html";
  const url = BASE + productDir + "/" + filename;
  const title = product.name + " | Almendras de Málaga";
  const description = ("Consulta " + product.name + " en Almendras de Málaga. Precio orientativo " + euro(product.price) + "/kg. Formatos y disponibilidad por WhatsApp.").slice(0, 160);
  const schema = {
    "@context": "https://schema.org", "@type": "Product", name: product.name,
    description: product.desc || product.name, category: product.tag || product.category,
    url, offers: { "@type": "Offer", price: Number(product.price).toFixed(2), priceCurrency: "EUR", url }
  };
  const wa = "https://wa.me/34666068765?text=" + encodeURIComponent("Hola, quisiera consultar disponibilidad, formatos y precio de " + product.name + ".");
  const html = `<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="description" content="${esc(description)}"><meta name="robots" content="index,follow"><title>${esc(title)}</title><link rel="canonical" href="${url}"><meta property="og:type" content="product"><meta property="og:title" content="${esc(title)}"><meta property="og:description" content="${esc(description)}"><meta property="og:url" content="${url}"><meta name="theme-color" content="#243b2e"><script type="application/ld+json">${JSON.stringify(schema).replace(/</g, "\\u003c")}</script><link rel="stylesheet" href="../styles.css"><style>.seo-product{max-width:780px;margin:32px auto;padding:clamp(20px,5vw,48px);background:#fffdf7;border:1px solid #e7d9ba;border-radius:22px;color:#243b2e}.seo-product h1{font-family:Georgia,serif;font-size:clamp(2rem,6vw,3.5rem);line-height:1.08}.seo-price{font-size:1.5rem;font-weight:700}.seo-actions{display:flex;gap:12px;flex-wrap:wrap;margin:24px 0}.seo-actions a{padding:14px 20px;border-radius:999px;background:#193f2e;color:white;text-decoration:none;font-weight:700}.seo-actions a.alt{background:#eadbb9;color:#243b2e}.seo-note{font-size:.9rem;color:#6b705f}</style></head><body><main class="seo-product"><p><a href="../index.html">Inicio</a> · <a href="../index.html#catalogo">Catálogo</a> · ${esc(product.tag || "Producto")}</p><h1>${esc(product.name)}</h1><p>${esc(product.desc || "Consulta este producto en nuestro catálogo.")}</p><p class="seo-price">${euro(product.price)} / kg</p><p>Precio orientativo por kilogramo. Consulta formato, disponibilidad y precio final antes de confirmar el pedido.</p><div class="seo-actions"><a href="${wa}" target="_blank" rel="noopener">Consultar por WhatsApp</a><a class="alt" href="../index.html#catalogo">Ver catálogo completo</a></div><h2>Formatos de consulta</h2><p>Consulta formatos de 100 g, 250 g, 500 g, 1 kg, 5 kg, 10 kg y 20 kg, así como pedidos de mayor volumen. Formatos y disponibilidad sujetos a confirmación.</p><h2>Almendras de Málaga</h2><p>Calle Santa María, 29, esquina con calle Molina Lario, junto a la Catedral de Málaga. Contacta con Don Miguel y Fabián para confirmar las condiciones del producto.</p><p class="seo-note">La información procede del catálogo y puede cambiar. Esta página no confirma existencias ni precio final.</p><div class="seo-actions"><a href="https://maps.app.goo.gl/a9Xq3G31MJhvYgRA8" target="_blank" rel="noopener">Cómo llegar</a><a class="alt" href="../index.html">Volver a la tienda</a></div></main></body></html>`;
  fs.writeFileSync(path.join(productDir, filename), html);
  urls.push(url);
  const category = product.tag || product.category || "Otros";
  if (!categories.has(category)) categories.set(category, []);
  categories.get(category).push({ product, filename });
}

for (const [category, list] of categories) {
  const filename = slug(category) + ".html", url = BASE + categoryDir + "/" + filename;
  const title = "Comprar " + category + " en Málaga | Almendras de Málaga";
  const description = ("Consulta nuestra selección de " + category.toLowerCase() + ". Catálogo y precios orientativos; disponibilidad por WhatsApp.").slice(0, 160);
  const items = list.map(({ product, filename: productFile }) => '<li><a href="../productos/' + productFile + '">' + esc(product.name) + '</a> — ' + euro(product.price) + '/kg orientativo</li>').join("");
  const html = `<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="description" content="${esc(description)}"><meta name="robots" content="index,follow"><title>${esc(title)}</title><link rel="canonical" href="${url}"><meta property="og:title" content="${esc(title)}"><meta property="og:description" content="${esc(description)}"><meta property="og:url" content="${url}"><link rel="stylesheet" href="../styles.css"></head><body><main class="seo-product" style="max-width:900px;margin:32px auto;padding:28px"><p><a href="../index.html">Inicio</a> · Catálogo</p><h1>${esc(category)} en Málaga</h1><p>${esc(description)}</p><p>Consulta productos, formatos y condiciones. Los precios son orientativos y la disponibilidad debe confirmarse.</p><ul>${items}</ul><p><a href="https://wa.me/34666068765?text=${encodeURIComponent("Hola, quisiera consultar productos de " + category + ".")}">Consultar por WhatsApp</a></p><p>Almendras de Málaga · Calle Santa María, 29, junto a la Catedral.</p><p><a href="../index.html#catalogo">Ver catálogo completo</a></p></main></body></html>`;
  fs.writeFileSync(path.join(categoryDir, filename), html);
  urls.push(url);
}

const sitemap = '<?xml version="1.0" encoding="UTF-8"?>\\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\\n' +
  urls.map(url => '  <url><loc>' + url + '</loc><lastmod>' + date + '</lastmod></url>').join("\\n") +
  '\\n</urlset>\\n';
fs.writeFileSync("sitemap.xml", sitemap);
console.log("Generadas " + Object.keys(products).length + " páginas de producto y " + categories.size + " categorías. Sitemap: " + urls.length + " URLs.");
