import http from "node:http";
import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";

const PORT=Number(process.env.PORT||3000);
const OPENAI_API_KEY=process.env.OPENAI_API_KEY;
const OPENAI_MODEL=process.env.OPENAI_MODEL||"gpt-6.2-sol";
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
  const hay=normalise([p.name,p.desc,p.tag,p.category].join(" "));
  const score=words.reduce((n,w)=>n+(hay.includes(w)?1:0),0);
  return {id,p,score};
 }).sort((a,b)=>b.score-a.score);
 const selected=scored.filter(x=>x.score>0).slice(0,16);
 const list=(selected.length?selected:scored.slice(0,30)).map(({id,p})=>({id,name:p.name,category:p.category,description:p.desc,pricePerKg:Number(p.price),image:p.imageVerified===true?p.image:null}));
 return JSON.stringify({products:list,formats:["100 g","250 g","500 g","1 kg","5 kg","10 kg","20 kg","más de 20 kg"],shipping:"El cálculo de envío de la web usa tramos editables y tarifas provisionales. No inventes el importe: si no se proporciona un cálculo exacto, indica que se confirmará."});
}
const SYSTEM="Eres el asistente comercial oficial de Almendras de Málaga, un negocio de frutos secos, almendras, aperitivos, semillas, frutas deshidratadas, caramelos y productos relacionados situado junto a la Catedral de Málaga. Tu misión es atender, recomendar y ayudar a comprar con una conversación natural, profesional, amable y breve. Habla siempre en español salvo que el cliente escriba en otro idioma. Usa únicamente la información del catálogo y contexto que se te proporciona. Los precios del catálogo son orientativos por kilogramo; calcula formatos multiplicando precio/kg por gramos/1000 y redondea a 2 decimales. No inventes stock, ingredientes, certificaciones, alérgenos, origen, descuentos, tarifas de envío ni fechas de entrega. Formatos habituales: 100 g, 250 g, 500 g, 1 kg, 5 kg, 10 kg, 20 kg y cantidades superiores a 20 kg bajo consulta. Para alérgenos e intolerancias, advierte que la confirmación debe hacerse con la etiqueta/ficha técnica del lote; nunca garantices ausencia de trazas. Puedes recomendar productos para recetas, aperitivos, repostería, regalos, hostelería y compras al por mayor. Pregunta solo lo necesario para avanzar. Cuando el cliente quiera comprar, confirma productos, formatos y cantidades. No solicites DNI ni CIF. No pidas datos de pago. Para cerrar, ofrece generar un resumen para WhatsApp o contactar con el negocio. Contacto: +34 666 068 765. Web: https://jmlopez0211-web.github.io/almendras-de-malaga/ Si una consulta requiere información que no tienes, dilo con claridad y ofrece contacto humano. No afirmes que has realizado pedidos, reservado stock o cobrado.";
function rateLimit(key){
 const now=Date.now();const data=rateLimits.get(key)||{count:0,start:now};
 if(now-data.start>RATE_WINDOW_MS){data.count=0;data.start=now}
 data.count++;rateLimits.set(key,data);
 return data.count<=RATE_LIMIT;
}
async function aiReply(history,message){
 if(!OPENAI_API_KEY)throw new Error("IA no configurada");
 const context=productContext(message);
 const input=[...history.slice(-MAX_HISTORY),{role:"user",content:"Consulta del cliente: "+message+"\n\nCatálogo relevante (JSON): "+context}];
 const r=await fetch("https://api.openai.com/v1/responses",{method:"POST",headers:{"Authorization":"Bearer "+OPENAI_API_KEY,"Content-Type":"application/json"},body:JSON.stringify({model:OPENAI_MODEL,instructions:SYSTEM,input,max_output_tokens:500})});
 const data=await r.json();
 if(!r.ok)throw new Error(data.error?.message||"Error en OpenAI API");
 const text=(data.output||[]).flatMap(o=>o.content||[]).filter(c=>c.type==="output_text").map(c=>c.text).join("\n").trim();
 if(!text)throw new Error("Respuesta vacía de la IA");
 return text;
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
  const answer=await aiReply(history,message);
  history=[...history,{role:"user",content:message},{role:"assistant",content:answer}].slice(-MAX_HISTORY);
  sessions.set("web:"+sessionId,history);
  if(sessions.size>MAX_SESSIONS)sessions.delete(sessions.keys().next().value);
  return send(res,200,{reply:answer,mode:"ai"});
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
