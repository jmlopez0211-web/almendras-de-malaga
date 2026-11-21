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
const MAX_HISTORY=12;
const MAX_SESSIONS=5000;
const RATE_LIMIT=30;
const RATE_WINDOW_MS=60*60*1000;

function send(res,status,data,headers={}){
 const body=typeof data==="string"?data:JSON.stringify(data);
 res.writeHead(status,{"Content-Type":typeof data==="string"?"text/plain; charset=utf-8":"application/json; charset=utf-8","Cache-Control":"no-store",...headers});
 res.end(body);
}
function readBody(req,max=100000){
 return new Promise((resolve,reject)=>{
  let size=0,chunks=[];
  req.on("data",chunk=>{size+=chunk.length;if(size>max){reject(new Error("Body demasiado grande"));req.destroy();return;}chunks.push(chunk)});
  req.on("end",()=>resolve(Buffer.concat(chunks).toString("utf8")));
  req.on("error",reject);
 });
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
 const now=Date.now();const data=rateLimits.get(key)||{count:0,start:now};
 if(now-data.start>RATE_WINDOW_MS){data.count=0;data.start=now}
 data.count++;rateLimits.set(key,data);
 return data.count<=RATE_LIMIT;
}
const AI_TOOLS=[
 {type:"function",name:"search_products",description:"Busca productos reales en el catálogo. Usa antes de añadir productos.",parameters:{type:"object",properties:{query:{type:"string"}},required:["query"],additionalProperties:false}},
 {type:"function",name:"price_pack",description:"Calcula el precio exacto orientativo de un formato a partir del precio/kg del catálogo.",parameters:{type:"object",properties:{product_id:{type:"string"},grams:{type:"integer",enum:[100,250,500,1000,5000,10000,20000]},quantity:{type:"integer",minimum:1,maximum:50}},required:["product_id","grams","quantity"],additionalProperties:false}},
 {type:"function",name:"calculate_shipping",description:"Calcula envío por peso usando las tarifas configuradas, marcadas provisionales.",parameters:{type:"object",properties:{weight_grams:{type:"integer",minimum:0}},required:["weight_grams"],additionalProperties:false}},
 {type:"function",name:"add_to_cart",description:"Solicita añadir una referencia real al carrito del navegador. No confirma compra.",parameters:{type:"object",properties:{product_id:{type:"string"},grams:{type:"integer",enum:[100,250,500,1000,5000,10000,20000]},quantity:{type:"integer",minimum:1,maximum:50}},required:["product_id","grams","quantity"],additionalProperties:false}}
];
function runStoreTool(name,args){
 if(name==="search_products"){
  const q=normalise(args.query);const aliases={almendras:"almendra",pistachos:"pistacho",cacahuetes:"cacahuete",anacardos:"anacardo",nueces:"nuez",avellanas:"avellana"};
  const words=q.split(/\\s+/).map(w=>aliases[w]||w).filter(w=>w.length>2&&!["quiero","busco","necesito","precio","precios"].includes(w));
  return Object.entries(PRODUCTS).map(([id,p])=>({id,name:p.name,category:p.category,description:p.desc,pricePerKg:Number(p.price),score:words.reduce((s,w)=>s+(normalise([id,p.name,p.desc,p.tag,p.category].join(" ")).includes(w)?1:0),0)})).filter(p=>p.score>0).sort((a,b)=>b.score-a.score).slice(0,12);
 }
 if(name==="price_pack"){
  const p=PRODUCTS[args.product_id];if(!p)return {error:"Producto no encontrado"};
  const grams=Number(args.grams),quantity=Number(args.quantity||1);
  return {productId:args.product_id,name:p.name,grams,quantity,unitPrice:Number((Number(p.price)*grams/1000).toFixed(2)),subtotal:Number((Number(p.price)*grams/1000*quantity).toFixed(2)),weightGrams:grams*quantity,pricePerKg:Number(p.price),availability:"No conectada; confirmar con el comercio"};
 }
 if(name==="calculate_shipping"){
  const grams=Math.max(0,Number(args.weight_grams)||0),tiers=COMMERCIAL.shipping.tiers||[];
  const tier=tiers.find(t=>t.maxGrams===null||grams<=t.maxGrams)||tiers[tiers.length-1];
  return {weightGrams:grams,label:tier?.label||"Pendiente de confirmar",price:Number(tier?.price||0),status:COMMERCIAL.shipping.status||"provisional",note:COMMERCIAL.shipping.note||"Tarifa pendiente de confirmar"};
 }
 if(name==="add_to_cart"){
  const p=PRODUCTS[args.product_id];if(!p)return {error:"Producto no encontrado",action:null};
  const grams=Number(args.grams),quantity=Number(args.quantity||1);
  if(![100,250,500,1000,5000,10000,20000].includes(grams)||quantity<1||quantity>50)return {error:"Formato o cantidad no válida",action:null};
  return {action:{type:"add_to_cart",productId:args.product_id,grams,quantity,name:p.name},message:"Añadido al carrito del navegador; aún no es un pedido confirmado."};
 }
 return {error:"Herramienta desconocida"};
}
async function aiReply(history,message){
 if(!OPENAI_API_KEY)throw new Error("IA no configurada");
 const context=productContext(message);
 let input=[...history.slice(-MAX_HISTORY),{role:"user",content:"Consulta del cliente: "+message+"\\n\\nCatálogo y reglas comerciales (JSON): "+context}];
 let actions=[];
 for(let turn=0;turn<5;turn++){
  const r=await fetch("https://api.openai.com/v1/responses",{method:"POST",headers:{"Authorization":"Bearer "+OPENAI_API_KEY,"Content-Type":"application/json"},body:JSON.stringify({model:OPENAI_MODEL,instructions:SYSTEM+"\\n\\nPuedes usar herramientas para buscar productos, calcular formatos, calcular envío y preparar acciones de carrito. Para pedidos, busca primero el producto exacto, calcula cada formato y el peso total, consulta el envío y solicita añadir al carrito. No afirmes que el carrito está actualizado hasta que el cliente lo reciba en la web. No inventes IDs: utiliza IDs devueltos por search_products. Si hay ambigüedad, pregunta.",input,tools:AI_TOOLS,max_output_tokens:700})});
  const data=await r.json();if(!r.ok)throw new Error(data.error?.message||"Error en OpenAI API");
  const calls=(data.output||[]).filter(o=>o.type==="function_call");
  if(!calls.length){const text=(data.output||[]).flatMap(o=>o.content||[]).filter(c=>c.type==="output_text").map(c=>c.text).join("\\n").trim();if(!text)throw new Error("Respuesta vacía de la IA");return {reply:text,actions};}
  input=[...input,...data.output];
  for(const call of calls){let args;try{args=JSON.parse(call.arguments||"{}")}catch{args={}}const result=runStoreTool(call.name,args);if(call.name==="add_to_cart"&&result.action)actions.push(result.action);input.push({type:"function_call_output",call_id:call.call_id,output:JSON.stringify(result)});}
 }
 throw new Error("La IA ha excedido el límite de herramientas");
}
async function handleChat(req,res){
 const origin=req.headers.origin||"";
 if(origin&&origin!==SITE_ORIGIN&&origin!=="http://localhost:8080"&&origin!=="http://127.0.0.1:8080")return send(res,403,{error:"Origen no permitido"});
 res.setHeader("Access-Control-Allow-Origin",origin||SITE_ORIGIN);
 res.setHeader("Vary","Origin");
 if(req.method==="OPTIONS"){res.writeHead(204,{"Access-Control-Allow-Methods":"POST, OPTIONS","Access-Control-Allow-Headers":"Content-Type"});return res.end()}
 const ip=req.headers["x-forwarded-for"]?.split(",")[0]||req.socket.remoteAddress||"unknown";
 if(!rateLimit(ip))return send(res,429,{error:"Has enviado demasiadas consultas. Inténtalo más tarde."});
 const body=JSON.parse(await readBody(req));
 const message=String(body.message||"").trim().slice(0,2000);
 const sessionId=String(body.session_id||"").slice(0,100);
 if(!message||!sessionId)return send(res,400,{error:"message y session_id son obligatorios"});
 let history=sessions.get("web:"+sessionId)||[];
 try{
  const result=await aiReply(history,message);const answer=result.reply;
  history=[...history,{role:"user",content:message},{role:"assistant",content:answer}].slice(-MAX_HISTORY);
  sessions.set("web:"+sessionId,history);
  if(sessions.size>MAX_SESSIONS)sessions.delete(sessions.keys().next().value);
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
 const response=await fetch(url,{method:"POST",headers:{"Authorization":"Bearer "+WA_TOKEN,"Content-Type":"application/json"},body:JSON.stringify({messaging_product:"whatsapp",recipient_type:"individual",to,type:"text",text:{preview_url:false,body:text.slice(0,4096)}})});
 const data=await response.json();
 if(!response.ok)throw new Error(data.error?.message||"WhatsApp API error");
 return data;
}
async function processWhatsApp(payload){
 for(const entry of payload.entry||[])for(const change of entry.changes||[])for(const msg of change.value?.messages||[]){
  if(!msg.id||processedWebhookIds.has(msg.id))continue;
  processedWebhookIds.add(msg.id);if(processedWebhookIds.size>10000)processedWebhookIds.clear();
  if(msg.type!=="text"||!msg.from||!msg.text?.body)continue;
  const from=msg.from,message=msg.text.body.trim().slice(0,2000),key="wa:"+from;
  const history=sessions.get(key)||[];
  try{
   const answer=await aiReply(history,message);
   sessions.set(key,[...history,{role:"user",content:message},{role:"assistant",content:answer}].slice(-MAX_HISTORY));
   await sendWhatsApp(from,answer);
  }catch(error){
   console.error("WhatsApp reply error:",error.message);
   await sendWhatsApp(from,"Ahora mismo no puedo consultar el asistente. Puedes ver el catálogo en https://jmlopez0211-web.github.io/almendras-de-malaga/ o escribirnos de nuevo más tarde.");
  }
 }
}
const server=http.createServer(async(req,res)=>{
 const url=new URL(req.url,"http://localhost");
 if(req.method==="GET"&&url.pathname==="/health")return send(res,200,{ok:true,service:"almendras-assistant",aiConfigured:Boolean(OPENAI_API_KEY),whatsappConfigured:Boolean(WA_TOKEN&&WA_PHONE_ID&&WA_VERIFY&&WA_APP_SECRET&&WA_API_VERSION)});
 if(url.pathname==="/api/chat"&&(req.method==="POST"||req.method==="OPTIONS"))return handleChat(req,res);
 if(url.pathname==="/webhook/whatsapp"&&req.method==="GET"){
  const mode=url.searchParams.get("hub.mode"),token=url.searchParams.get("hub.verify_token"),challenge=url.searchParams.get("hub.challenge");
  if(mode==="subscribe"&&token&&token===WA_VERIFY)return send(res,200,challenge||"");
  return send(res,403,"Forbidden");
 }
 if(url.pathname==="/webhook/whatsapp"&&req.method==="POST"){
  try{
   const raw=await readBody(req,1024*1024);
   if(!verifyWhatsAppSignature(raw,req.headers["x-hub-signature-256"]))return send(res,401,{error:"Firma inválida"});
   const payload=JSON.parse(raw);
   send(res,200,{received:true});
   processWhatsApp(payload).catch(e=>console.error("Webhook processing:",e.message));
   return;
  }catch(e){return send(res,400,{error:"Webhook inválido"})}
 }
 return send(res,404,{error:"Not found"});
});
server.listen(PORT,"0.0.0.0",()=>console.log("Almendras Assistant listening on "+PORT));
