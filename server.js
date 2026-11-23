import http from "node:http";
import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";

const PORT=Number(process.env.PORT||3000);
const OPENAI_API_KEY=process.env.OPENAI_API_KEY;
const OPENAI_MODEL=process.env.OPENAI_MODEL||"gpt-4.1-mini";
const WA_TOKEN=process.env.WHATSAPP_ACCESS_TOKEN;
const WA_PHONE_ID=process.env.WHATSAPP_PHONE_NUMBER_ID;
const WA_VERIFY=process.env.WHATSAPP_VERIFY_TOKEN;
const WA_APP_SECRET=process.env.WHATSAPP_APP_SECRET;
const WA_API_VERSION=process.env.WHATSAPP_API_VERSION;
const SITE_ORIGIN="https://jmlopez0211-web.github.io";
const CATALOG_PATH=path.join(process.cwd(),"data","catalog.js");
const catalogSource=fs.readFileSync(CATALOG_PATH,"utf8");
const catalogMatch=catalogSource.match(/window\.PRODUCTS\s*=\s*(\{[\s\S]*\})\s*;?\s*$/);
if(!catalogMatch)throw new Error("No se pudo leer data/catalog.js");
const PRODUCTS=JSON.parse(catalogMatch[1]);
const COMMERCIAL=JSON.parse(fs.readFileSync(path.join(process.cwd(),"data","commercial.json"),"utf8"));

const sessions=new Map();
const rateLimits=new Map();
const processedWebhookIds=new Set();
function saveSession(key,history){
 sessions.set(key,history);
 if(sessions.size>MAX_SESSIONS)sessions.delete(sessions.keys().next().value);
}
const MAX_HISTORY=12;
const MAX_SESSIONS=5000;
const RATE_LIMIT=30;
const RATE_WINDOW_MS=60*60*1000;
const MAX_RATE_LIMIT_KEYS=10000;
const MAX_WEBHOOK_IDS=10000;
const ALLOWED_PACK_FORMATS=[100,250,500,1000,5000,10000,20000];
const MAX_ORDER_WEIGHT_GRAMS=500000;

function send(res,status,data,headers={}){
 const body=typeof data==="string"?data:JSON.stringify(data);
 res.writeHead(status,{"Content-Type":typeof data==="string"?"text/plain; charset=utf-8":"application/json; charset=utf-8","Cache-Control":"no-store",...headers});
 res.end(body);
}
function readBody(req,max=100000){
 return new Promise((resolve,reject)=>{
  let size=0,chunks=[],tooLarge=false,settled=false;
  const fail=(message,statusCode)=>{if(settled)return;settled=true;const error=new Error(message);error.statusCode=statusCode;reject(error)};
  req.on("data",chunk=>{size+=chunk.length;if(size>max){tooLarge=true;chunks=[];return;}if(!tooLarge)chunks.push(chunk)});
  req.on("end",()=>{if(tooLarge)return fail("Body demasiado grande",413);if(!settled){settled=true;resolve(Buffer.concat(chunks).toString("utf8"))}});
  req.on("aborted",()=>fail("Solicitud interrumpida",400));
  req.on("error",error=>fail(error.message,400));
 });
}
function parseJson(raw){try{return JSON.parse(raw)}catch{const error=new Error("JSON inválido");error.statusCode=400;throw error}}
function getClientKey(req){
 const forwarded=String(req.headers["x-forwarded-for"]||"").split(",").map(value=>value.trim()).filter(Boolean);
 return (forwarded.length?forwarded[forwarded.length-1]:String(req.socket.remoteAddress||"unknown")).slice(0,64);
}
function normalise(s){return String(s||"").toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g,"").replace(/[^a-z0-9]+/g," ").trim()}
function productContext(query){
 const words=normalise(query).split(/\s+/).filter(w=>w.length>2&&!["precio","precios","quiero","busco","necesito","cuanto","cuesta","formato","gramos","kilos","producto","productos"].includes(w));
 const scored=Object.entries(PRODUCTS).map(([id,p])=>{
  const hay=normalise([id,p.name,p.desc,p.tag,p.category].join(" "));
  const score=words.reduce((n,w)=>n+(hay.includes(w)?2:0),0);
  return {id,p,score};
 }).sort((a,b)=>b.score-a.score);
 const selected=scored.filter(x=>x.score>0).slice(0,20);
 const list=(selected.length?selected:scored.slice(0,40)).map(({id,p})=>({id,name:p.name,category:p.category,description:p.desc,pricePerKg:Number(p.price),image:p.imageVerified===true?p.image:null}));
 return JSON.stringify({products:list,commercial:COMMERCIAL});
}
const SYSTEM="Eres el asistente comercial oficial de Almendras de Málaga. Atiendes tanto la web como WhatsApp con el mismo criterio, catálogo y reglas. Tu misión es recomendar, informar y ayudar a preparar pedidos de frutos secos, almendras, aperitivos, semillas, frutas deshidratadas, caramelos y productos relacionados. Habla en español salvo que el cliente escriba en otro idioma. Usa únicamente los datos del catálogo y la información comercial JSON proporcionados en cada consulta. Los precios son orientativos por kilogramo; calcula formatos proporcionalmente y redondea a 2 decimales. Respeta los formatos y tarifas de envío que aparecen en el contexto; si las tarifas figuran como provisionales, comunícalo claramente y no las presentes como confirmadas. No inventes stock, ingredientes, certificaciones, alérgenos, origen, descuentos, tarifas, plazos ni fechas de entrega. Para alérgenos, remite a etiqueta o ficha técnica del lote; nunca garantices ausencia de trazas. Puedes recomendar productos para recetas, aperitivos, repostería, regalos, hostelería y compras al por mayor. Pregunta solo lo necesario para avanzar. Cuando quieran comprar, confirma productos, formatos y cantidades, y ofrece preparar un resumen de pedido. No solicites DNI ni CIF, no pidas datos de pago y no afirmes que has realizado pedidos, reservado stock o cobrado. Contacto: "+COMMERCIAL.contact.primaryPhone+". Web: "+COMMERCIAL.contact.web+". Si necesitas información que no tienes, dilo claramente y ofrece contacto humano.";function rateLimit(key){
 const now=Date.now();let data=rateLimits.get(key);
 if(data&&now-data.start>=RATE_WINDOW_MS){rateLimits.delete(key);data=null}
 if(!data){if(rateLimits.size>=MAX_RATE_LIMIT_KEYS){const oldest=rateLimits.keys().next().value;if(oldest!==undefined)rateLimits.delete(oldest)}data={count:0,start:now}}
 data.count++;rateLimits.set(key,data);return data.count<=RATE_LIMIT;
}
const AI_TOOLS=[
 {type:"function",name:"search_products",description:"Busca productos reales en el catálogo. Usa antes de añadir productos.",parameters:{type:"object",properties:{query:{type:"string"}},required:["query"],additionalProperties:false}},
 {type:"function",name:"price_pack",description:"Calcula el precio exacto orientativo de un formato a partir del precio/kg del catálogo.",parameters:{type:"object",properties:{product_id:{type:"string"},grams:{type:"integer",enum:[100,250,500,1000,5000,10000,20000]},quantity:{type:"integer",minimum:1,maximum:50}},required:["product_id","grams","quantity"],additionalProperties:false}},
 {type:"function",name:"calculate_shipping",description:"Calcula envío por peso usando las tarifas configuradas, marcadas provisionales.",parameters:{type:"object",properties:{weight_grams:{type:"integer",minimum:0}},required:["weight_grams"],additionalProperties:false}},
 {type:"function",name:"add_to_cart",description:"Solicita añadir una referencia real al carrito del navegador. No confirma compra.",parameters:{type:"object",properties:{product_id:{type:"string"},grams:{type:"integer",enum:[100,250,500,1000,5000,10000,20000]},quantity:{type:"integer",minimum:1,maximum:50}},required:["product_id","grams","quantity"],additionalProperties:false}}
];
function runStoreTool(name,args){
 if(!args||typeof args!=="object"||Array.isArray(args))return {error:"Argumentos inválidos"};
 if(name==="search_products"){
  if(typeof args.query!=="string"||!args.query.trim()||args.query.length>160)return {error:"Consulta de búsqueda inválida"};
  const q=normalise(args.query);const aliases={almendras:"almendra",pistachos:"pistacho",cacahuetes:"cacahuete",anacardos:"anacardo",nueces:"nuez",avellanas:"avellana"};
  const words=q.split(/\s+/).map(w=>aliases[w]||w).filter(w=>w.length>2&&!["quiero","busco","necesito","precio","precios"].includes(w));
  return Object.entries(PRODUCTS).map(([id,p])=>({id,name:p.name,category:p.category,description:p.desc,pricePerKg:Number(p.price),score:words.reduce((s,w)=>s+(normalise([id,p.name,p.desc,p.tag,p.category].join(" ")).includes(w)?1:0),0)})).filter(p=>p.score>0).sort((a,b)=>b.score-a.score).slice(0,12);
 }
 if(name==="price_pack"){
  const p=PRODUCTS[args.product_id];if(!p)return {error:"Producto no encontrado"};
  const grams=Number(args.grams),quantity=Number(args.quantity),price=Number(p.price);
  if(!ALLOWED_PACK_FORMATS.includes(grams)||!Number.isInteger(quantity)||quantity<1||quantity>50||!Number.isFinite(price)||price<=0)return {error:"Formato, cantidad o precio inválido"};
  return {productId:args.product_id,name:p.name,grams,quantity,unitPrice:Number((price*grams/1000).toFixed(2)),subtotal:Number((price*grams/1000*quantity).toFixed(2)),weightGrams:grams*quantity,pricePerKg:price,availability:"No conectada; confirmar con el comercio"};
 }
 if(name==="calculate_shipping"){
  const grams=Number(args.weight_grams),tiers=COMMERCIAL.shipping.tiers||[];
  if(!Number.isInteger(grams)||grams<0||grams>MAX_ORDER_WEIGHT_GRAMS)return {error:"Peso inválido"};
  const tier=tiers.find(t=>t.maxGrams===null||grams<=t.maxGrams)||tiers[tiers.length-1];
  return {weightGrams:grams,label:tier?.label||"Pendiente de confirmar",price:Number(tier?.price||0),status:COMMERCIAL.shipping.status||"provisional",note:COMMERCIAL.shipping.note||"Tarifa pendiente de confirmar"};
 }
 if(name==="add_to_cart"){
  const p=PRODUCTS[args.product_id];if(!p)return {error:"Producto no encontrado",action:null};
  const grams=Number(args.grams),quantity=Number(args.quantity);
  if(!ALLOWED_PACK_FORMATS.includes(grams)||!Number.isInteger(quantity)||quantity<1||quantity>50||!Number.isFinite(Number(p.price))||Number(p.price)<=0)return {error:"Formato, cantidad o precio no válido",action:null};
  return {action:{type:"add_to_cart",productId:args.product_id,grams,quantity,name:p.name},message:"Añadido al carrito del navegador; aún no es un pedido confirmado."};
 }
 return {error:"Herramienta desconocida"};
}
async function aiReply(history,message,channel="web"){
 if(!OPENAI_API_KEY)throw new Error("IA no configurada");
 const context=productContext(message);
 let input=[...history.slice(-MAX_HISTORY),{role:"user",content:"Consulta del cliente: "+message+"\n\nCatálogo y reglas comerciales (JSON): "+context}];
 const availableTools=channel==="whatsapp"?AI_TOOLS.filter(tool=>tool.name!=="add_to_cart"):AI_TOOLS;
 const explicitCartIntent=channel==="web"&&/\b(quiero|anade|agrega|mete|pon|ponme|comprar|compra|pedido|dame|agregame|meteme|sumame)\b/.test(normalise(message));
 let actions=[];
 const deadline=Date.now()+22000;
 for(let turn=0;turn<5;turn++){
  if(Date.now()>=deadline)throw new Error("Tiempo máximo de respuesta del asistente agotado");
  const r=await fetch("https://api.openai.com/v1/responses",{method:"POST",headers:{"Authorization":"Bearer "+OPENAI_API_KEY,"Content-Type":"application/json"},signal:AbortSignal.timeout(Math.max(1000,deadline-Date.now())),body:JSON.stringify({model:OPENAI_MODEL,instructions:SYSTEM+"\n\nPuedes usar herramientas para buscar productos, calcular formatos y calcular envío. Para pedidos, busca primero el producto exacto, calcula cada formato y el peso total, y consulta el envío. "+(channel==="whatsapp"?"En WhatsApp no existe un carrito web: no afirmes haber añadido productos a un carrito ni que el pedido está registrado; ofrece un resumen para que el cliente confirme con el comercio.":"Puedes solicitar acciones de carrito para la web, pero nunca confirmes una compra. No afirmes que el carrito está actualizado hasta que el cliente reciba la confirmación de la web.")+" No inventes IDs: utiliza IDs devueltos por search_products. Si hay ambigüedad, pregunta.",input,tools:availableTools,max_output_tokens:700})});
  const data=await r.json();if(!r.ok)throw new Error(data.error?.message||"Error en OpenAI API");
  const calls=(data.output||[]).filter(o=>o.type==="function_call");
  if(!calls.length){const text=(data.output||[]).flatMap(o=>o.content||[]).filter(c=>c.type==="output_text").map(c=>c.text).join("\n").trim();if(!text)throw new Error("Respuesta vacía de la IA");const safeReply=channel==="whatsapp"&&/(añadid[oa]s? al carrito|carrito actualizado|pedido registrado|pedido confirmado|compra confirmada)/i.test(text)?text+"\n\nNota: este chat no modifica el carrito de la web ni registra una compra. El pedido debe confirmarse con la tienda.":text;return {reply:safeReply,actions}}
  input=[...input,...data.output];
  for(const call of calls){
   let args;try{args=JSON.parse(call.arguments||"{}")}catch{args={}}
   let result=runStoreTool(call.name,args);
   if(call.name==="add_to_cart"&&!explicitCartIntent)result={error:"Para modificar el carrito, el cliente debe solicitarlo expresamente",action:null};
   if(call.name==="add_to_cart"&&result.action){
    const already=actions.filter(action=>action.productId===result.action.productId&&action.grams===result.action.grams).reduce((sum,action)=>sum+action.quantity,0);
    if(already+result.action.quantity>50)result={error:"El máximo acumulado es de 50 unidades por producto y formato",action:null};
    else actions.push(result.action);
   }
   input.push({type:"function_call_output",call_id:call.call_id,output:JSON.stringify(result)});
  }
 }
 throw new Error("La IA ha excedido el límite de herramientas");
}
async function handleChat(req,res){
 const origin=req.headers.origin||"";
 if(origin&&origin!==SITE_ORIGIN&&origin!=="http://localhost:8080"&&origin!=="http://127.0.0.1:8080")return send(res,403,{error:"Origen no permitido"});
 res.setHeader("Access-Control-Allow-Origin",origin||SITE_ORIGIN);res.setHeader("Vary","Origin");
 if(req.method==="OPTIONS"){res.writeHead(204,{"Access-Control-Allow-Methods":"POST, OPTIONS","Access-Control-Allow-Headers":"Content-Type"});return res.end()}
 if(!String(req.headers["content-type"]||"").toLowerCase().startsWith("application/json"))return send(res,415,{error:"Content-Type debe ser application/json"});
 if(!rateLimit(getClientKey(req)))return send(res,429,{error:"Has enviado demasiadas consultas. Inténtalo más tarde."});
 let body;try{body=parseJson(await readBody(req,16000))}catch(error){return send(res,error.statusCode||400,{error:error.statusCode===413?"Solicitud demasiado grande":"JSON inválido"})}
 if(!body||typeof body!=="object"||Array.isArray(body))return send(res,400,{error:"El cuerpo debe ser un objeto JSON"});
 const message=typeof body.message==="string"?body.message.trim():"";
 const sessionId=typeof body.session_id==="string"?body.session_id.trim():"";
 if(!message||message.length>2000||! /^[\w-]{16,100}$/.test(sessionId)||Object.keys(body).some(key=>!["message","session_id"].includes(key)))return send(res,400,{error:"Cuerpo inválido: message, session_id y ningún otro campo son admitidos"});
 let history=sessions.get("web:"+sessionId)||[];
 try{
  const result=await aiReply(history,message);const answer=result.reply;
  history=[...history,{role:"user",content:message},{role:"assistant",content:answer}].slice(-MAX_HISTORY);
  saveSession("web:"+sessionId,history);
  return send(res,200,{reply:answer,mode:"ai",actions:result.actions||[]});
 }catch(error){
  console.error("Chat error:",error.message);
  return send(res,503,{error:"El asistente inteligente no está disponible ahora. Puedes consultar el catálogo o contactar por WhatsApp.",mode:"fallback"});
 }
}
function verifyWhatsAppSignature(raw,signature){
 if(!WA_APP_SECRET||!signature?.startsWith("sha256="))return false;
 const expected="sha256="+crypto.createHmac("sha256",WA_APP_SECRET).update(raw).digest("hex");
 try{return crypto.timingSafeEqual(Buffer.from(expected),Buffer.from(signature))}catch{return false}
}
async function sendWhatsApp(to,text){
 if(!WA_TOKEN||!WA_PHONE_ID||!WA_API_VERSION)throw new Error("WhatsApp no configurado");
 const url="https://graph.facebook.com/"+WA_API_VERSION+"/"+WA_PHONE_ID+"/messages";
 if(!/^\d{8,15}$/.test(String(to)))throw new Error("Número de WhatsApp de destino inválido");
 const response=await fetch(url,{method:"POST",signal:AbortSignal.timeout(15000),headers:{"Authorization":"Bearer "+WA_TOKEN,"Content-Type":"application/json"},body:JSON.stringify({messaging_product:"whatsapp",recipient_type:"individual",to,type:"text",text:{preview_url:false,body:text.slice(0,4096)}})});
 const data=await response.json();
 if(!response.ok)throw new Error(data.error?.message||"WhatsApp API error");
 return data;
}
async function processWhatsApp(payload){
 for(const entry of payload.entry||[])for(const change of entry.changes||[])for(const msg of change.value?.messages||[]){
  if(!msg.id||processedWebhookIds.has(msg.id))continue;
  processedWebhookIds.add(msg.id);if(processedWebhookIds.size>MAX_WEBHOOK_IDS)processedWebhookIds.delete(processedWebhookIds.values().next().value);
  if(msg.type!=="text"||!msg.from||!/^\d{8,15}$/.test(String(msg.from))||!msg.text?.body)continue;
  const from=String(msg.from),message=String(msg.text.body).trim().slice(0,2000),key="wa:"+from;if(!message)continue;
  const history=sessions.get(key)||[];
  try{
   const answer=await aiReply(history,message,"whatsapp");
   saveSession(key,[...history,{role:"user",content:message},{role:"assistant",content:answer}].slice(-MAX_HISTORY));
   await sendWhatsApp(from,answer);
  }catch(error){
   console.error("WhatsApp reply error:",error.message);
   try{await sendWhatsApp(from,"Ahora mismo no puedo consultar el asistente. Puedes ver el catálogo en https://jmlopez0211-web.github.io/almendras-de-malaga/ o escribirnos de nuevo más tarde.");}
   catch(deliveryError){processedWebhookIds.delete(msg.id);throw deliveryError}
  }
 }
}
async function handleRequest(req,res){
 const url=new URL(req.url,"http://localhost");
 if(req.method==="GET"&&url.pathname==="/health")return send(res,200,{ok:true,service:"almendras-assistant",aiConfigured:Boolean(OPENAI_API_KEY),whatsappConfigured:Boolean(WA_TOKEN&&WA_PHONE_ID&&WA_VERIFY&&WA_APP_SECRET&&WA_API_VERSION)});
 if(url.pathname==="/api/chat"&&(req.method==="POST"||req.method==="OPTIONS"))return handleChat(req,res);
 if(url.pathname==="/webhook/whatsapp"&&req.method==="GET"){
  const mode=url.searchParams.get("hub.mode"),token=url.searchParams.get("hub.verify_token"),challenge=url.searchParams.get("hub.challenge");
  if(mode==="subscribe"&&WA_VERIFY&&token===WA_VERIFY)return send(res,200,challenge||"");
  return send(res,403,"Forbidden");
 }
 if(url.pathname==="/webhook/whatsapp"&&req.method==="POST"){
  try{
   const raw=await readBody(req,1024*1024);
   if(!verifyWhatsAppSignature(raw,req.headers["x-hub-signature-256"]))return send(res,401,{error:"Firma inválida"});
   const payload=parseJson(raw);
   if(!payload||typeof payload!=="object"||!Array.isArray(payload.entry))return send(res,400,{error:"Webhook inválido"});
   send(res,200,{received:true});processWhatsApp(payload).catch(e=>console.error("Webhook processing:",e.message));return;
  }catch(e){return send(res,e.statusCode||400,{error:"Webhook inválido"})}
 }
 return send(res,404,{error:"Not found"});
}
const server=http.createServer((req,res)=>{
 handleRequest(req,res).catch(error=>{
  console.error("Request error:",error.message);
  if(!res.headersSent)send(res,error.statusCode||500,{error:error.statusCode===413?"Solicitud demasiado grande":"Error interno del servidor"});
  else if(!res.writableEnded)res.end();
 });
});
server.requestTimeout=15000;
server.headersTimeout=10000;
server.keepAliveTimeout=5000;
server.maxRequestsPerSocket=100;
server.listen(PORT,"0.0.0.0",()=>console.log("Almendras Assistant listening on "+PORT));
