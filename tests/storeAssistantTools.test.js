import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";
const catalog={
 almond:{name:"Almendra cruda",desc:"Para repostería",tag:"Frutos secos",category:"frutos",price:20},
 pistachio:{name:"Pistacho tostado",desc:"Snack",tag:"Frutos secos",category:"frutos",price:30}
};
const storage=new Map();
const listeners={};
const window={PRODUCTS:catalog,dispatchEvent:e=>{(listeners[e.type]||[]).forEach(fn=>fn(e))},addEventListener:(t,fn)=>(listeners[t]??=[]).push(fn)};
const localStorage={getItem:k=>storage.get(k)||null,setItem:(k,v)=>storage.set(k,v)};
const context={window,localStorage,CustomEvent:class{constructor(type,opts){this.type=type;this.detail=opts?.detail}},console};
vm.runInNewContext(fs.readFileSync(new URL("../js/storeAssistantTools.js",import.meta.url),"utf8"),context);
const tools=window.storeAssistantTools;

test("search by product name and family",()=>{assert.equal(tools.searchProducts("almendras")[0].id,"almond");assert.equal(tools.searchProducts("reposteria")[0].id,"almond")});
test("format pricing is exact and quantity-scaled",()=>{const p=tools.packPrice("almond",250,2);assert.equal(p.unitPrice,5);assert.equal(p.subtotal,10);assert.equal(p.weightGrams,500)});
test("shipping thresholds including over 20kg",()=>{assert.equal(tools.calculateShipping(100).price,2.5);assert.equal(tools.calculateShipping(250).price,3.5);assert.equal(tools.calculateShipping(500).price,4.5);assert.equal(tools.calculateShipping(1000).price,5.5);assert.equal(tools.calculateShipping(5000).price,7.5);assert.equal(tools.calculateShipping(10000).price,9.5);assert.equal(tools.calculateShipping(20000).price,12.5);assert.equal(tools.calculateShipping(20001).price,15)});
test("cart add, modify and summary",()=>{tools.clearCart();tools.addToCart("almond",500,2);tools.setCartItem("almond",500,3);const s=tools.cartSummary();assert.equal(s.weightGrams,1500);assert.equal(s.subtotal,30);assert.equal(s.shipping.price,7.5);assert.equal(s.total,37.5);tools.removeCartItem("almond",500);assert.equal(tools.readCart().length,0)});
test("order summary targets WhatsApp primary and excludes DNI/CIF",()=>{tools.clearCart();tools.addToCart("pistachio",1000,1);const m=tools.orderMessage();assert.match(m,/Pistacho tostado/);assert.match(m,/PESO TOTAL/);assert.match(m,/TOTAL/);assert.doesNotMatch(m,/DNI|CIF/);assert.match(tools.whatsappUrl(),/wa\.me\/34666068765/)});

test("natural language multi-item order adds products and calculates shipping",()=>{tools.clearCart();const result=tools.interpretLocal("Quiero medio kilo de almendras crudas y un cuarto de pistachos");assert.equal(result.handled,true);assert.match(result.reply,/Almendra cruda/);assert.match(result.reply,/Pistacho tostado/);const s=tools.cartSummary();assert.equal(s.items.length,2);assert.equal(s.weightGrams,750);assert.equal(s.subtotal,17.5);assert.equal(s.shipping.price,5.5);assert.equal(s.total,23);});

test("partial natural-language order adds specified weight and asks bag format",()=>{tools.clearCart();const result=tools.interpretLocal("Añade un kilo de almendras y dos bolsas de pistachos");assert.equal(result.handled,true);assert.match(result.reply,/Almendra cruda/);assert.match(result.reply,/indique el formato|indiqu|formato de cada bolsa/i);const s=tools.cartSummary();assert.equal(s.items.length,1);assert.equal(s.items[0].id,"almond");assert.equal(s.weightGrams,1000);});
