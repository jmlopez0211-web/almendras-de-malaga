import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const generator = fileURLToPath(new URL("../scripts/generate-seo-pages.js", import.meta.url));

test("SEO generator creates product/category pages and preserves existing landing URLs", () => {
  const temp = fs.mkdtempSync(path.join(os.tmpdir(), "almendras-seo-"));
  try {
    fs.mkdirSync(path.join(temp, "data"), { recursive: true });
    const catalog = {
      almendraCruda: {
        name: "Almendra cruda con piel",
        desc: "Almendra sin tostar, presentada con su piel.",
        tag: "Frutos secos",
        category: "frutos",
        price: 13.2
      },
      pistacho: {
        name: "Pistacho tostado",
        desc: "Pistacho tostado.",
        tag: "Frutos secos",
        category: "frutos",
        price: 29.8
      },
      mango: {
        name: "Mango deshidratado",
        desc: "Mango deshidratado.",
        tag: "Fruta deshidratada",
        category: "fruta",
        price: 19.8
      }
    };
    fs.writeFileSync(path.join(temp, "data", "catalog.js"), "window.PRODUCTS = " + JSON.stringify(catalog, null, 2) + ";\n");
    const home = "https://jmlopez0211-web.github.io/almendras-de-malaga/";
    const landing = home + "frutos-secos-centro-malaga.html";
    fs.writeFileSync(path.join(temp, "sitemap.xml"), '<?xml version="1.0"?><urlset><url><loc>' + home + '</loc></url><url><loc>' + landing + '</loc></url></urlset>');

    const output = execFileSync(process.execPath, [generator], { cwd: temp, encoding: "utf8" });
    const productFiles = fs.readdirSync(path.join(temp, "productos"));
    const categoryFiles = fs.readdirSync(path.join(temp, "categorias"));
    assert.equal(productFiles.length, 3);
    assert.equal(categoryFiles.length, 2);
    assert.match(output, /Páginas de producto generadas: 3/);
    assert.match(output, /Páginas de categoría generadas: 2/);

    const almendraFile = productFiles.find(file => file.includes("almendra-cruda"));
    assert.ok(almendraFile, "Debe existir la página de almendra");
    const productHtml = fs.readFileSync(path.join(temp, "productos", almendraFile), "utf8");
    assert.ok(productHtml.includes("<title>Almendra cruda con piel | Almendras de Málaga</title>"));
    assert.match(productHtml, /rel="canonical"/);
    assert.ok(productHtml.includes("application/ld+json"));
    assert.match(productHtml, /precio orientativo/i);

    const sitemap = fs.readFileSync(path.join(temp, "sitemap.xml"), "utf8");
    assert.ok(sitemap.includes(home));
    assert.ok(sitemap.includes(landing), "No debe borrar landings SEO existentes");
    assert.equal((sitemap.match(/<loc>/g) || []).length, 7);
    assert.ok(sitemap.includes("/productos/"));
    assert.ok(sitemap.includes("/categorias/"));
  } finally {
    fs.rmSync(temp, { recursive: true, force: true });
  }
});
