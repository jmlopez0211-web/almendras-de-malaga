import fs from "node:fs";
const sitemap=fs.readFileSync("sitemap.xml","utf8");
const urls=[...sitemap.matchAll(/<loc>\\s*([^<]+)\\s*<\\/loc>/g)].map(m=>m[1].trim());
const concurrency=8, timeoutMs=15000;
let next=0, ok=0, bad=[];
async function check(url){
 try{
  const controller=new AbortController();const timer=setTimeout(()=>controller.abort(),timeoutMs);
  let response=await fetch(url,{method:"HEAD",redirect:"follow",signal:controller.signal});
  if(response.status===405||response.status===501) response=await fetch(url,{method:"GET",redirect:"follow",signal:controller.signal});
  clearTimeout(timer);
  if(response.status>=200&&response.status<400) ok++;else bad.push({url,status:response.status});
 }catch(e){bad.push({url,error:e.name==="AbortError"?"TIMEOUT":e.message});}
}
async function worker(){while(true){const i=next++;if(i>=urls.length)return;await check(urls[i]);console.log(`[${ok+bad.length}/${urls.length}] ${urls[i]} ${bad.find(x=>x.url===urls[i])?.status||bad.find(x=>x.url===urls[i])?.error||"OK"}`);}}
await Promise.all(Array.from({length:concurrency},worker));
console.log("\\nLIVE URL CHECK");
console.log(`URLs: ${urls.length} | OK: ${ok} | Fallidas: ${bad.length}`);
if(bad.length){console.log(JSON.stringify(bad,null,2));process.exitCode=1;}
