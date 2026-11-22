import test from "node:test";
import assert from "node:assert/strict";
import { buildProductContent, productTitle, productMetaDescription } from "../scripts/product-content-seo.js";

const samples=[
  {id:"almendraCrudaPiel",product:{name:"Almendra cruda con piel",desc:"Almendra sin tostar, presentada con su piel."},category:"Frutos secos",related:[{product:{name:"Almendra cruda pelada",desc:"Almendra cruda sin piel."}}]},
  {id:"almendraFritaOliva",product:{name:"Almendra frita con aceite de oliva",desc:"Almendra frita; el catálogo indica aceite de oliva."},category:"Frutos secos",related:[{product:{name:"Almendra frita con aceite de girasol",desc:"Almendra frita; el catálogo indica aceite de girasol."}}]},
  {id:"almendraGarrapinada",product:{name:"Almendra garrapiñada",desc:"Almendra recubierta de caramelo."},category:"Garrapiñados y dulces",related:[{product:{name:"Cacahuete garrapiñado",desc:"Cacahuete recubierto de caramelo."}}]},
  {id:"harinaAlmendra",product:{name:"Harina de almendra",desc:"Almendra molida hasta obtener una textura de harina."},category:"Almendra y derivados",related:[{product:{name:"Filete de almendra",desc:"Almendra cortada en láminas finas."}}]}
];

test("product content is expanded, specific and contains FAQ",()=>{
  for(const sample of samples){
    const c=buildProductContent(sample.product,sample.id,sample.category,sample.related);
    assert.ok(c.intro.includes(sample.product.name));
    assert.ok(c.selection.length>100);
    assert.ok(c.use.length>100);
    assert.ok(c.faq.length>=3);
    assert.ok(c.faq.every(item=>item.q&&item.a));
  }
});
test("titles and meta descriptions remain within SEO bounds",()=>{
  for(const sample of samples){
    const title=productTitle(sample.product,sample.id);
    const description=productMetaDescription(sample.product,sample.id);
    assert.ok(title.length>=10&&title.length<=65);
    assert.ok(description.length>=40&&description.length<=158);
  }
});
test("FAQ does not invent commercial data",()=>{
  const c=buildProductContent(samples[0].product,samples[0].id,samples[0].category,samples[0].related);
  assert.ok(c.faq.some(item=>item.a.includes("no confirma")||item.a.includes("no public")));
  assert.ok(c.faq.some(item=>item.a.includes("no confirma")||item.a.includes("No se publican")||item.a.includes("no se publica")||item.a.includes("no confirma")||item.a.includes("no se")));
});
