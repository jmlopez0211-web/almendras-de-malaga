/* Herramientas deterministas de tienda: catálogo real, carrito local y envío. */
(function(){
"use strict";
const FORMATS=[100,250,500,1000,5000,10000,20000];
const PHONE="34666068765";
const norm=s=>String(s||"").toLocaleLowerCase("es").normalize("NFD").replace(/[\u0300-\u036f]/g,"").replace(/[^a-z0-9]+/g," ").trim();
function catalog(){return window.PRODUCTS||{}}
function searchProducts(query,limit=12){
 const aliases={almendras:"almendra",nueces:"nuez",cacahuetes:"cacahuete",anacardos:"anacardo",pistachos:"pistacho",avellanas:"avellana",pipas:"pipa",semillas:"semilla",pasas:"pasa",frutas:"fruta"}; const q=norm(query), words=q.split(/\s+/).filter(w=>w.length>1).map(w=>aliases[w]||w);
 return Object.entries(catalog()).map(([id,p])=>{
  const hay=norm([id,p.name,p.desc,p.tag,p.category].join(" "));
  const score=words.reduce((n,w)=>n+(hay.includes(w)?2:0),0);
  return {id,...p,score};
 }).filter(p=>!words.length||p.score>0).sort((a,b)=>b.score-a.score).slice(0,limit);
}
function getProduct(id){const p=catalog()[id];return p?{id,...p}:null}
function packPrice(productId,grams,quantity=1){
 const p=getProduct(productId);grams=Number(grams);quantity=Number(quantity);
 if(!p||!FORMATS.includes(grams)||!Number.isInteger(quantity)||quantity<1||quantity>50)throw new Error("Producto, formato o cantidad inválidos");
 return {id:productId,name:p.name,pricePerKg:Number(p.price),grams,quantity,unitPrice:Number((Number(p.price)*grams/1000).toFixed(2)),subtotal:Number((Number(p.price)*grams/1000*quantity).toFixed(2)),weightGrams:grams*quantity};
}
function shippingTiers(){
 const fallback=[{maxGrams:100,label:"Hasta 100 g",price:2.5},{maxGrams:250,label:"101–250 g",price:3.5},{maxGrams:500,label:"251–500 g",price:4.5},{maxGrams:1000,label:"501 g–1 kg",price:5.5},{maxGrams:5000,label:"1,001–5 kg",price:7.5},{maxGrams:10000,label:"5,001–10 kg",price:9.5},{maxGrams:20000,label:"10,001–20 kg",price:12.5},{maxGrams:Infinity,label:"Más de 20 kg",price:15}];
 try{const c=window.COMMERCIAL_CONFIG;if(Array.isArray(c?.shipping?.tiers)&&c.shipping.tiers.length===8)return c.shipping.tiers.map(t=>({...t,maxGrams:t.maxGrams==null?Infinity:Number(t.maxGrams),price:Number(t.price)}))}catch{}
 return fallback;
}
function calculateShipping(weightGrams){const g=Math.max(0,Number(weightGrams)||0);if(!g)return {maxGrams:0,label:"Sin productos",price:0};return shippingTiers().find(t=>g<=t.maxGrams)||shippingTiers().at(-1)}
function readCart(){try{return JSON.parse(localStorage.getItem("almendrasCart")||"[]").filter(x=>getProduct(x.id)&&FORMATS.includes(Number(x.grams))&&Number.isInteger(Number(x.quantity))&&Number(x.quantity)>0).map(x=>({id:x.id,name:getProduct(x.id).name,price:Number(getProduct(x.id).price),grams:Number(x.grams),quantity:Number(x.quantity)}))}catch{return []}}
function saveCart(items){localStorage.setItem("almendrasCart",JSON.stringify(items));window.dispatchEvent(new CustomEvent("almendras:cart-updated",{detail:items}));return items}
function addToCart(id,grams,quantity=1){const item=packPrice(id,grams,quantity),cart=readCart(),found=cart.find(x=>x.id===id&&x.grams===Number(grams));if(found){if(found.quantity+quantity>50)throw new Error("Máximo 50 unidades por producto y formato");found.quantity+=quantity}else cart.push({id,name:item.name,price:item.pricePerKg,grams:Number(grams),quantity:Number(quantity)});saveCart(cart);return cart}
function setCartItem(id,grams,quantity){const cart=readCart(),found=cart.find(x=>x.id===id&&x.grams===Number(grams));if(!found)throw new Error("Artículo no encontrado");if(!Number.isInteger(Number(quantity))||quantity<0||quantity>50)throw new Error("Cantidad inválida");if(quantity===0)return saveCart(cart.filter(x=>x!==found));found.quantity=Number(quantity);return saveCart(cart)}
function removeCartItem(id,grams){return saveCart(readCart().filter(x=>!(x.id===id&&x.grams===Number(grams))))}
function clearCart(){pendingFormats=[];return saveCart([])}
function cartSummary(items=readCart()){
 const lines=items.map(x=>packPrice(x.id,x.grams,x.quantity));
 const weight=lines.reduce((n,x)=>n+x.weightGrams,0),subtotal=Number(lines.reduce((n,x)=>n+x.subtotal,0).toFixed(2)),shipping=calculateShipping(weight),total=Number((subtotal+shipping.price).toFixed(2));
 return {items:lines,weightGrams:weight,subtotal,shipping,total};
}
function orderMessage(items=readCart(),notes=""){
 const s=cartSummary(items);if(!s.items.length)throw new Error("El carrito está vacío");
 return "🛒 *PEDIDO · ALMENDRAS DE MÁLAGA*\n\n"+s.items.map(x=>"• "+x.name+" — "+x.quantity+" × "+x.grams+" g · "+x.subtotal.toFixed(2).replace(".",",")+" €").join("\n")+"\n\n⚖️ *PESO TOTAL:* "+s.weightGrams+" g\n🚚 *ENVÍO:* "+s.shipping.label+" · "+s.shipping.price.toFixed(2).replace(".",",")+" €\n🧾 *SUBTOTAL:* "+s.subtotal.toFixed(2).replace(".",",")+" €\n💰 *TOTAL:* "+s.total.toFixed(2).replace(".",",")+" €\n\n📝 *Observaciones:* "+(notes||"Ninguna")+"\n\nDisponibilidad, precio final y tarifa de envío provisionales pendientes de confirmación.";
}
function whatsappUrl(items,notes){return "https://wa.me/"+PHONE+"?text="+encodeURIComponent(orderMessage(items,notes))}
function splitWeight(totalGrams){
 totalGrams=Number(totalGrams);
 if(!Number.isInteger(totalGrams)||totalGrams<1||totalGrams>500000)throw new Error("Peso total inválido (máximo 500 kg)");
 const packs=[];let remaining=totalGrams;
 for(const format of [...FORMATS].sort((a,b)=>b-a)){
  while(remaining>=format){packs.push(format);remaining-=format;}
 }
 if(remaining)throw new Error("El peso solicitado no puede dividirse en formatos disponibles");
 return packs;
}
function parseWeight(text){
 const q=norm(text);
 if(/medio kilo|media kilo|medio kg|500 gramos|500 g/.test(q))return 500;
 if(/un cuarto|cuarto de kilo|250 gramos|250 g/.test(q))return 250;
 if(/un kilo|1 kilo|1 kg|1000 gramos/.test(q))return 1000;
 if(/dos kilos|2 kilos|2 kg/.test(q))return 2000;
 const m=q.match(/\b(100|250|500|1000|5000|10000|20000)\s*(g|gr|gramos)?\b/);
 if(m)return Number(m[1]);
 const kg=q.match(/\b([1-9][0-9]?)\s*(kg|kilo|kilos)\b/);
 if(kg)return Number(kg[1])*1000;
 return null;
}
function findProductForPhrase(phrase){
 const q=norm(phrase);
 const aliases={almendras:"almendra",pistachos:"pistacho",cacahuetes:"cacahuete",anacardos:"anacardo",nueces:"nuez",avellanas:"avellana",crudas:"cruda",tostadas:"tostada",fritas:"frita"}; const words=q.split(/\s+/).filter(w=>w.length>2&&!["quiero","para","poner","añade","agrega","comprar","pedido","medio","kilo","cuarto","gramos","gramo","bolsa","bolsas","de","del","una","un"].includes(w)).map(w=>aliases[w]||w);
 const scored=Object.entries(catalog()).map(([id,p])=>{
  const hay=norm([id,p.name,p.desc,p.tag,p.category].join(" "));
  let score=words.reduce((n,w)=>n+(hay.includes(w)?3:0),0);
  if(norm(p.name).includes(q))score+=10;
  if(words.some(w=>/almendra|pistacho|cacahuete|anacardo|nuez|avellana|pasas/.test(w))&&words.some(w=>hay.includes(w)))score+=1;
  return {id,p,score,matched:words.filter(w=>hay.includes(w)).length};
 }).sort((a,b)=>b.score-a.score);
 return scored[0]&&scored[0].score>=3?scored[0]:null;
}
let pendingFormats=[];
function interpretLocal(text){
 const q=norm(text);
 if(pendingFormats.length){const grams=parseWeight(text);if(grams){try{const pending=[...pendingFormats];pendingFormats=[];pending.forEach(x=>addToCart(x.id,grams,x.quantity));const s=cartSummary();return {handled:true,reply:"He añadido las bolsas pendientes:\n"+pending.map(x=>"• "+x.name+" — "+x.quantity+" × "+grams+" g").join("\n")+"\n\n"+s.items.map(x=>"• "+x.name+" — "+x.quantity+" × "+x.grams+" g = "+x.subtotal.toFixed(2)+" €").join("\n")+"\n\n⚖️ Peso total: "+s.weightGrams+" g\n🧾 Subtotal: "+s.subtotal.toFixed(2)+" €\n🚚 Envío ("+s.shipping.label+"): "+s.shipping.price.toFixed(2)+" €\n💰 Total: "+s.total.toFixed(2)+" €.\n\nTarifas provisionales; disponibilidad y precio final pendientes de confirmación."}}catch(e){return {handled:true,reply:"No he podido añadir las bolsas: "+e.message}}}}
 if(/vaciar carrito|borra el pedido|elimina todo/.test(q)){clearCart();return {handled:true,reply:"He vaciado el carrito."}}
 // Modificación/eliminación explícita de líneas existentes del carrito.
 const isRemove=/\b(quita|quitar|elimina|eliminar|borra|borrar|saca|retira)\b/.test(q);
 const isModify=/\b(cambia|cambiar|modifica|modificar|ajusta|ajustar|deja|pon|poner|reduce|reducir)\b/.test(q);
 if(isRemove||isModify){
  const product=findProductForPhrase(text);
  if(product){
   const existing=readCart().filter(x=>x.id===product.id);
   if(!existing.length)return {handled:true,reply:"No encuentro "+product.p.name+" en el carrito. Si quieres, puedo añadirlo indicando el formato."};
   if(isRemove){
    existing.forEach(x=>removeCartItem(x.id,x.grams));
    const s=cartSummary();
    return {handled:true,reply:"He eliminado "+product.p.name+" del carrito.\\n\\n"+(s.items.length?s.items.map(x=>"• "+x.name+" — "+x.quantity+" × "+x.grams+" g = "+x.subtotal.toFixed(2)+" €").join("\\n")+"\\n\\n⚖️ Peso total: "+s.weightGrams+" g\\n🧾 Subtotal: "+s.subtotal.toFixed(2)+" €\\n🚚 Envío ("+s.shipping.label+"): "+s.shipping.price.toFixed(2)+" €\\n💰 Total: "+s.total.toFixed(2)+" €.":"El carrito está vacío.")};
   }
   const grams=parseWeight(text);
   if(grams){
    const qtyMatch=q.match(/\b([1-9]|[1-5][0-9])\\s*(?:bolsas|paquetes|unidades)\b/);
    const wordQty=q.match(/\b(una|un|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez)\\s*(?:bolsas|paquetes|unidades)\b/);
    const quantity=qtyMatch?Number(qtyMatch[1]):wordQty?({una:1,un:1,dos:2,tres:3,cuatro:4,cinco:5,seis:6,siete:7,ocho:8,nueve:9,diez:10}[wordQty[1]]):1;
    existing.forEach(x=>removeCartItem(x.id,x.grams));
    try{splitWeight(grams).forEach(pack=>addToCart(product.id,pack,quantity));const s=cartSummary();return {handled:true,reply:"He actualizado "+product.p.name+" a "+quantity+" bolsa(s) de "+grams+" g (divididas en formatos disponibles).\\n\\n"+s.items.map(x=>"• "+x.name+" — "+x.quantity+" × "+x.grams+" g = "+x.subtotal.toFixed(2)+" €").join("\\n")+"\\n\\n⚖️ Peso total: "+s.weightGrams+" g\\n🧾 Subtotal: "+s.subtotal.toFixed(2)+" €\\n🚚 Envío ("+s.shipping.label+"): "+s.shipping.price.toFixed(2)+" €\\n💰 Total: "+s.total.toFixed(2)+" €.\\n\\nTarifas provisionales; disponibilidad y precio final pendientes de confirmación."}}catch(e){return {handled:true,reply:"No he podido modificar el carrito: "+e.message}}
   }
   return {handled:true,reply:"He localizado "+product.p.name+" en el carrito. Indícame el formato nuevo (100 g, 250 g, 500 g, 1 kg, 5 kg, 10 kg o 20 kg)."}
  }
 }
 if(/resumen|total del pedido|cuanto llevo/.test(q)){const s=cartSummary();return {handled:true,reply:"Resumen: "+s.items.length+" líneas, "+s.weightGrams+" g. Subtotal "+s.subtotal.toFixed(2)+" €, envío "+s.shipping.price.toFixed(2)+" € ("+s.shipping.label+"), total "+s.total.toFixed(2)+" €."}}
 const shopping=/\b(quiero|anade|agrega|mete|pon|comprar|compra|pedido|lleva|dame)\b/.test(q);
 if(shopping){
  const chunks=String(text).replace(/[,;]+/g," y ").split(/\s+y\s+/i).map(x=>x.trim()).filter(Boolean);
  const parsed=[],needsFormat=[];
  for(const chunk of chunks){
   const cq=norm(chunk);
   const grams=parseWeight(chunk);
   const qtyMatch=cq.match(/\b([1-9]|[1-5][0-9])\s*(?:bolsas|paquetes|unidades)\b/);
   const wordQty=cq.match(/\b(una|un|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez)\s*(?:bolsas|paquetes|unidades)\b/);
   const quantity=qtyMatch?Number(qtyMatch[1]):wordQty?({una:1,un:1,dos:2,tres:3,cuatro:4,cinco:5,seis:6,siete:7,ocho:8,nueve:9,diez:10}[wordQty[1]]):1;
   const clean=cq.replace(/\b(quiero|anade|agrega|mete|pon|comprar|compra|pedido|lleva|dame|un|una|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|medio|media|cuarto|kilo|kilos|kg|gramos|gramo|g|bolsa|bolsas|paquete|paquetes|unidad|unidades|de|del|la|el|con|y)\b/g," ").replace(/\b\d+\b/g," ").trim();
   const product=findProductForPhrase(clean)||findProductForPhrase(chunk);
   if(!product)continue;
   if(!grams){needsFormat.push({id:product.id,name:product.p.name,quantity});continue}
   parsed.push({id:product.id,name:product.p.name,grams,quantity});
  }
  if(parsed.length||needsFormat.length){
   try{
    parsed.forEach(x=>splitWeight(x.grams).forEach(pack=>addToCart(x.id,pack,x.quantity)));
    const s=cartSummary();
    const added=parsed.map(x=>"• "+x.name+" — "+x.quantity+" × "+x.grams+" g (dividido en formatos disponibles)").join("\n");
    const breakdown=s.items.map(x=>"• "+x.name+" — "+x.quantity+" × "+x.grams+" g = "+x.subtotal.toFixed(2)+" €").join("\n");
    let reply=parsed.length?"He añadido al carrito:\n"+added+"\n\n"+breakdown+"\n\n⚖️ Peso total: "+s.weightGrams+" g\n🧾 Subtotal: "+s.subtotal.toFixed(2)+" €\n🚚 Envío ("+s.shipping.label+"): "+s.shipping.price.toFixed(2)+" €\n💰 Total: "+s.total.toFixed(2)+" €.":"";
    if(needsFormat.length){pendingFormats=needsFormat;reply+=(reply?"\n\n":"")+"Para añadir "+needsFormat.map(x=>x.quantity+" bolsa(s) de "+x.name).join(" y ")+" necesito que me indiques el formato de cada bolsa (100 g, 250 g, 500 g, 1 kg, etc.).";}
    reply+="\n\nTarifas de envío provisionales; disponibilidad y precio final pendientes de confirmación.";
    return {handled:true,reply};
   }catch(e){return {handled:true,reply:"No he podido completar el carrito: "+e.message}}
  }
 }
 const candidates=searchProducts(text,5),product=candidates[0];
 if(product&&product.score>0){
  return {handled:true,reply:candidates.slice(0,5).map(p=>p.name+" — "+Number(p.price).toLocaleString("es-ES",{style:"currency",currency:"EUR"})+" / kg orientativo").join("\n")+"\nDime el formato (100 g, 250 g, 500 g, 1 kg, 5 kg, 10 kg o 20 kg) para añadirlo."}
 }
 return {handled:false};
}
window.storeAssistantTools={searchProducts,getProduct,packPrice,calculateShipping,readCart,addToCart,setCartItem,removeCartItem,clearCart,cartSummary,orderMessage,whatsappUrl,interpretLocal,splitWeight,formats:FORMATS};
})();