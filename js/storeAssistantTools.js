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
function clearCart(){return saveCart([])}
function cartSummary(items=readCart()){
 const lines=items.map(x=>packPrice(x.id,x.grams,x.quantity));
 const weight=lines.reduce((n,x)=>n+x.weightGrams,0),subtotal=Number(lines.reduce((n,x)=>n+x.subtotal,0).toFixed(2)),shipping=calculateShipping(weight),total=Number((subtotal+shipping.price).toFixed(2));
 return {items:lines,weightGrams:weight,subtotal,shipping,total};
}
function orderMessage(items=readCart(),notes=""){
 const s=cartSummary(items);if(!s.items.length)throw new Error("El carrito está vacío");
 return "🛒 *PEDIDO · ALMENDRAS DE MÁLAGA*\n\n"+s.items.map(x=>"• "+x.name+" — "+x.quantity+" × "+x.grams+" g · "+x.subtotal.toFixed(2).replace(".",",")+" €").join("\n")+"\n\n⚖️ *PESO TOTAL:* "+s.weightGrams+" g\n🚚 *ENVÍO:* "+s.shipping.label+" · "+s.shipping.price.toFixed(2).replace(".",",")+" €\n🧾 *SUBTOTAL:* "+s.subtotal.toFixed(2).replace(".",",")+" €\n💰 *TOTAL:* "+s.total.toFixed(2).replace(".",",")+" €\n\n📝 *Observaciones:* "+(notes||"Ninguna")+"\n\nDisponibilidad, precio final y tarifa de envío provisionales pendientes de confirmación. No se solicita DNI ni CIF.";
}
function whatsappUrl(items,notes){return "https://wa.me/"+PHONE+"?text="+encodeURIComponent(orderMessage(items,notes))}
function interpretLocal(text){
 const q=norm(text);
 const gramsMatch=q.match(/\b(100|250|500|1000|5000|10000|20000)\s*(g|gr|gramos)?\b/);
 const kgMatch=q.match(/\b(1|5|10|20)\s*(kg|kilo|kilos)\b/);
 const grams=gramsMatch?Number(gramsMatch[1]):kgMatch?Number(kgMatch[1])*1000:null;
 const quantityMatch=q.match(/\b([1-9][0-9]?)\s*(?:unidades|bolsas|paquetes|formatos)\b/);
 const quantity=quantityMatch?Number(quantityMatch[1]):1;
 if(/vaciar carrito|borra el pedido|elimina todo/.test(q)){clearCart();return {handled:true,reply:"He vaciado el carrito."}}
 if(/resumen|total del pedido|cuanto llevo/.test(q)){const s=cartSummary();return {handled:true,reply:"Resumen: "+s.items.length+" líneas, "+s.weightGrams+" g. Subtotal "+s.subtotal.toFixed(2)+" €, envío "+s.shipping.price.toFixed(2)+" € ("+s.shipping.label+"), total "+s.total.toFixed(2)+" €."}}
 const candidates=searchProducts(text,5);
 const product=candidates[0];
 if(product&&product.score>0&&/(añade|agrega|mete|pon|quiero|pedido|comprar|compra)/.test(q)&&grams){
  try{addToCart(product.id,grams,quantity);const s=cartSummary();return {handled:true,reply:"Añadido: "+product.name+", "+quantity+" × "+grams+" g. El carrito pesa "+s.weightGrams+" g; subtotal "+s.subtotal.toFixed(2)+" €, envío "+s.shipping.price.toFixed(2)+" €, total "+s.total.toFixed(2)+" €."}}catch(e){return {handled:true,reply:e.message}}
 }
 if(product&&product.score>0){return {handled:true,reply:candidates.slice(0,5).map(p=>p.name+" — "+Number(p.price).toLocaleString("es-ES",{style:"currency",currency:"EUR"})+" / kg orientativo").join("\n")+"\nDime formato (100 g, 250 g, 500 g, 1 kg, 5 kg, 10 kg o 20 kg) y cantidad para añadirlo."}}
 return {handled:false};
}
window.storeAssistantTools={searchProducts,getProduct,packPrice,calculateShipping,readCart,addToCart,setCartItem,removeCartItem,clearCart,cartSummary,orderMessage,whatsappUrl,interpretLocal,formats:FORMATS};
})();