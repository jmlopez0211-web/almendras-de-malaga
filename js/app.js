// Tarifas compartidas: js/commercial-config.js es la fuente única de configuración.
const DEFAULT_SHIPPING_TIERS = [
 {maxGrams:100,label:"Hasta 100 g",price:2.50},
 {maxGrams:250,label:"101–250 g",price:3.50},
 {maxGrams:500,label:"251–500 g",price:4.50},
 {maxGrams:1000,label:"501 g–1 kg",price:5.50},
 {maxGrams:5000,label:"1,001–5 kg",price:7.50},
 {maxGrams:10000,label:"5,001–10 kg",price:9.50},
 {maxGrams:20000,label:"10,001–20 kg",price:12.50},
 {maxGrams:Infinity,label:"Más de 20 kg",price:15.00}
];
let SHIPPING_TIERS = DEFAULT_SHIPPING_TIERS.map(tier=>({...tier}));
function applyCommercialConfig(config){
 const tiers=config?.shipping?.tiers;
 if(!Array.isArray(tiers)||tiers.length!==DEFAULT_SHIPPING_TIERS.length)return false;
 const normalized=tiers.map((tier,index)=>({
  maxGrams:index===tiers.length-1?Infinity:Number(tier.maxGrams),
  label:String(tier.label||"").trim(),
  price:Number(tier.price)
 }));
 if(normalized.some((tier,index)=>!tier.label||!Number.isFinite(tier.price)||tier.price<0||(index<normalized.length-1&&(!Number.isFinite(tier.maxGrams)||tier.maxGrams<=0))||(index>0&&index<normalized.length-1&&tier.maxGrams<=normalized[index-1].maxGrams)))return false;
 SHIPPING_TIERS=normalized;
 window.dispatchEvent(new Event("almendras:shipping-updated"));
 return true;
}
if(window.COMMERCIAL_CONFIG)applyCommercialConfig(window.COMMERCIAL_CONFIG);
window.addEventListener("almendras:commercial-config-updated",()=>applyCommercialConfig(window.COMMERCIAL_CONFIG));
function calculateShipping(totalGrams){
 const grams=Math.max(0,Number(totalGrams)||0);
 if(grams===0)return {maxGrams:0,label:"Sin productos",price:0};
 return SHIPPING_TIERS.find(tier=>grams<=tier.maxGrams)||SHIPPING_TIERS[SHIPPING_TIERS.length-1];
}
function getCartWeightGrams(items){return items.reduce((sum,item)=>sum+Math.max(0,Number(item.grams)||0)*Math.max(0,Number(item.quantity)||0),0);}

const products = window.PRODUCTS;
if (!products || typeof products !== 'object') {
  throw new Error('No se ha cargado data/catalog.js: catálogo no disponible.');
}

const categoryNames={"frutos":"Frutos secos","variantes":"Almendra y derivados","cacahuetes":"Cacahuetes","dulces":"Garrapiñados y dulces","revueltos":"Revueltos","fruta":"Fruta deshidratada","semillas":"Pipas y semillas","aperitivos":"Aperitivos","chocolates":"Chocolates","caramelos":"Caramelos y confitería"};
const euro=n=>n.toLocaleString('es-ES',{style:'currency',currency:'EUR'});
const escapeHTML=value=>String(value??'').replace(/[&<>"']/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
const hasProductId=id=>Object.prototype.hasOwnProperty.call(products,String(id));
function catalogGroup(p){
 const name=p.name.toLocaleLowerCase('es');
 if(p.category==='chocolates'||p.category==='caramelos'||/chocolate|chocobola|lacasitos|sugus|toffee|toffino|gummys|gominola|picot|pictol[ií]n|carachoco|caramelo|confiter[ií]a|werther|café dry|gajos santos|relleno de fruta|relleno miel|taco de miel|dulce de leche/.test(name))return 'chuches';
 if(p.category==='fruta'||/pasa|orej[oó]n|higo|d[aá]til|deshidratad|ciruela|cereza|mel[oó]n|manzana|papaya|pl[aá]tano|mango|piña|pomelo|hibisco|kiwi|fresa|ar[aá]ndano/.test(name))return 'fruta';
 if(/garrapiñad|caramelizad|con miel|revuelto|mix|pipa|semilla|kiko|garbanzo|haba|aperitivo|chufa/.test(name))return 'variados';
 if(/almendra|cacahuete|anacardo|macadamia|avellana|nuez|pistacho|piñ[oó]n|castaña|coquito|fruto seco/.test(name))return 'frutos';
 return 'variados';
}
function productImage(id,p){
 if(!p||p.imageVerified!==true||typeof p.image!=='string')return '';
 const url=p.image.trim();
 const localAsset=/^assets\/products\/[A-Za-z0-9._/-]+$/.test(url)&&!url.split('/').includes('..');
 let parsed;
 try{parsed=new URL(url,location.href)}catch(e){return ''}
 const remoteHosts=new Set(['commons.wikimedia.org','upload.wikimedia.org','thumb.wikimedia.org','cdn.pixabay.com']);
 const allowed=(localAsset&&parsed.origin===location.origin)||(parsed.protocol==='https:'&&remoteHosts.has(parsed.hostname));
 if(!allowed)return '';
 const owners=Object.entries(products).filter(([otherId,other])=>otherId!==id&&other.imageVerified===true&&other.image===url);
 return owners.length?'':url;
}
function productImageCredit(p){
 if(!p||!p.imageCredit||!p.imageSource||!p.imageLicense)return null;
 let source;
 try{source=new URL(p.imageSource,location.href)}catch(e){return null}
 if(source.protocol!=='https:')return null;
 return {credit:String(p.imageCredit),source:source.href,license:String(p.imageLicense)};
}
function renderProductImageCredit(host,p,hasPhoto){
 host.replaceChildren();
 if(!hasPhoto){host.textContent='No se muestra una imagen genérica para evitar confusiones.';host.hidden=false;return}
 const credit=productImageCredit(p);
 if(!credit){host.textContent='Crédito, fuente o licencia de la fotografía pendiente de documentar';host.hidden=false;return}
 host.append(document.createTextNode('Foto: '+credit.credit+' · '));
 const link=document.createElement('a');
 link.href=credit.source;
 link.target='_blank';
 link.rel='noopener noreferrer';
 link.textContent=credit.license;
 host.append(link);
 host.hidden=false;
}
function hasUniqueProductImage(id){return Boolean(productImage(id,products[id]));}
function hasSpecificProductImage(id){return Boolean(productImage(id,products[id]));}


function productIllustration(p){
 const group=catalogGroup(p);
 const palette=group==='frutos'?['#8b5b31','#d9b47a','#5c3921']:group==='fruta'?['#a75a3c','#d98b4b','#7a3e2b']:group==='chuches'?['#d96b91','#e6b94f','#6da58a']:['#c58a45','#8c5930','#d9b47a'];
 const shapes=group==='frutos'?'<ellipse cx="118" cy="95" rx="25" ry="46" transform="rotate(-35 118 95)" fill="'+palette[0]+'"/><ellipse cx="170" cy="108" rx="25" ry="46" transform="rotate(32 170 108)" fill="'+palette[1]+'"/><ellipse cx="145" cy="145" rx="24" ry="43" transform="rotate(-10 145 145)" fill="'+palette[2]+'"/><ellipse cx="93" cy="150" rx="24" ry="43" transform="rotate(25 93 150)" fill="'+palette[1]+'"/><ellipse cx="195" cy="155" rx="23" ry="42" transform="rotate(-28 195 155)" fill="'+palette[0]+'"/>' : group==='fruta'?'<circle cx="100" cy="110" r="38" fill="'+palette[0]+'"/><circle cx="155" cy="92" r="34" fill="'+palette[1]+'"/><circle cx="185" cy="145" r="42" fill="'+palette[2]+'"/><circle cx="125" cy="160" r="32" fill="'+palette[1]+'"/><circle cx="78" cy="170" r="25" fill="'+palette[2]+'"/>' : group==='chuches'?'<rect x="72" y="72" width="65" height="38" rx="19" fill="'+palette[0]+'" transform="rotate(-25 104 91)"/><rect x="142" y="105" width="70" height="42" rx="21" fill="'+palette[1]+'" transform="rotate(18 177 126)"/><circle cx="110" cy="160" r="29" fill="'+palette[2]+'"/><rect x="145" y="155" width="55" height="35" rx="17" fill="'+palette[0]+'" transform="rotate(-15 172 172)"/>' :'<ellipse cx="90" cy="100" rx="29" ry="17" fill="'+palette[0]+'" transform="rotate(20 90 100)"/><ellipse cx="145" cy="88" rx="30" ry="18" fill="'+palette[1]+'" transform="rotate(-20 145 88)"/><ellipse cx="190" cy="125" rx="29" ry="17" fill="'+palette[2]+'" transform="rotate(15 190 125)"/><ellipse cx="120" cy="155" rx="29" ry="17" fill="'+palette[2]+'" transform="rotate(-25 120 155)"/><ellipse cx="175" cy="175" rx="30" ry="18" fill="'+palette[0]+'" transform="rotate(25 175 175)"/>';
 return '<svg class="product-illustration" viewBox="0 0 280 240" aria-hidden="true"><rect width="280" height="240" rx="16" fill="#f0e4d0"/><circle cx="140" cy="120" r="92" fill="#fff8e9" opacity=".45"/><g>'+shapes+'</g><path d="M55 202 Q140 222 225 202" fill="none" stroke="#b99a6d" stroke-width="2" opacity=".5"/><text x="140" y="222" text-anchor="middle" font-size="10" letter-spacing="2" fill="#6e5b42">ILUSTRACIÓN</text></svg>';
}
function productPlaceholder(p){
 const group=catalogGroup(p);
 const category={frutos:'FRUTOS SECOS',fruta:'FRUTA DESHIDRATADA',chuches:'CHOCOLATES Y GOLOSINAS',variados:'SNACKS Y VARIADOS'}[group]||'CATÁLOGO';
 return '<div class="product-placeholder product-illustrated" role="img" aria-label="Ilustración orientativa de '+escapeHTML(p.name)+'"><div class="illustration-art">'+productIllustration(p)+'</div><span class="placeholder-category">'+category+'</span><strong>'+escapeHTML(p.name)+'</strong></div>';
}
function normalizeCatalogText(value){
 return String(value??'').toLocaleLowerCase('es').normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/\s+/g,' ').trim();
}
function catalogSearchWords(value){
 const aliases={almendras:'almendra',nueces:'nuez',cacahuetes:'cacahuete',anacardos:'anacardo',pistachos:'pistacho',avellanas:'avellana',pipas:'pipa',semillas:'semilla',gominolas:'gominola',caramelos:'caramelo',chocolates:'chocolate',fritas:'frita',fritos:'frito',tostadas:'tostada',tostados:'tostado',peladas:'pelada',pelados:'pelado',naturales:'natural',garrapinadas:'garrapinada',garrapinados:'garrapinado',pinones:'pinon',arandanos:'arandano',datiles:'datil',higos:'higo',pasas:'pasa',ciruelas:'ciruela',frutas:'fruta',orejones:'orejon',castanas:'castana'};
 return normalizeCatalogText(value).split(/[^a-z0-9]+/).filter(Boolean).map(word=>aliases[word]||word).filter(word=>word.length>1);
}
function allergenInfo(p){
 const n=normalizeCatalogText([p.name,p.desc].join(' '));
 const rules=[
  [/almendra/,'Almendra (fruto de cáscara)'],
  [/cacahuete|mani/,'Cacahuete'],
  [/avellana/,'Avellana (fruto de cáscara)'],
  [/anacardo/,'Anacardo (fruto de cáscara)'],
  [/pistacho/,'Pistacho (fruto de cáscara)'],
  [/macadamia/,'Macadamia (fruto de cáscara)'],
  [/nuez de brasil/,'Nuez de Brasil (fruto de cáscara)'],
  [/pecana/,'Nuez pecana (fruto de cáscara)'],
  [/nuez|nueces/,'Nuez (fruto de cáscara)']
 ];
 const hasSpecificNutName=/nuez de macadamia|pecana|nuez de brasil/.test(n);
 const found=rules.filter(([re,label])=>re.test(n)&&!(label==='Nuez (fruto de cáscara)'&&hasSpecificNutName)).map(([,label])=>label);
 return {found:[...new Set(found)]};
}
function allergenCardText(p){
 const info=allergenInfo(p);
 if(info.found.length)return 'Alérgeno identificado por denominación: '+info.found.join(', ')+'. Verifica la etiqueta del lote.';
 return 'Alérgenos: consultar etiqueta del lote.';
}
let activeSubfamily='todos';
function productFamily(p){
 const n=normalizeCatalogText(p.name);
 const tests=[
 ['almendras',/almendra/],['cacahuetes',/cacahuete|mani/],['anacardos',/anacardo/],['pistachos',/pistacho/],['macadamias',/macadamia/],['avellanas',/avellana/],['nueces',/nuez|pecana|brasil/],['piñones',/pinon/],['castañas',/castana/],['chufas',/chufa/],
 ['pipas y semillas',/pipa|semilla/],['kikos y maíz',/kiko|maiz frito/],['habas y garbanzos',/haba|garbanzo/],['revueltos y mixes',/revuelto|mix|variado/],['pasas',/pasa/],['mango',/mango/],['plátano',/platano/],['coco',/coco/],['fruta deshidratada',/deshidrat|orejon|datil|higo|ciruela|melon|papaya|piña|kiwi|arandano|fresa|manzana/],['chocolate',/chocolate|chocobola/],['gominolas',/gummy|gummys|gominola/],['caramelos',/caramelo|pictolin|sugus|werther|toffee|toffino|cafe dry|relleno|picota|gajo|dulce de leche|lacasito|carachoco/]
 ];
 for(const [label,re] of tests)if(re.test(n))return label;
 return 'otros';
}
function renderSubfamilies(active){
 const host=document.getElementById('subfamilyFilters');if(!host)return;
 const labels=[...new Set(Object.values(products).filter(p=>active==='todos'||catalogGroup(p)===active).map(productFamily))].sort((a,b)=>a.localeCompare(b,'es'));
 host.innerHTML='<button class="subfilter active" data-subfilter="todos">Todas las variedades</button>'+labels.map(x=>'<button class="subfilter" data-subfilter="'+escapeHTML(x)+'">'+escapeHTML(x[0].toUpperCase()+x.slice(1))+'</button>').join('');
 host.querySelectorAll('[data-subfilter]').forEach(b=>b.onclick=()=>{activeSubfamily=b.dataset.subfilter;host.querySelectorAll('[data-subfilter]').forEach(x=>x.classList.toggle('active',x===b));renderProducts()});
}
function renderFamilyTiles(){
 const host=document.getElementById('familyTiles');if(!host)return;
 const families=[['frutos','Frutos secos','Almendras, cacahuetes, anacardos y más'],['fruta','Frutas deshidratadas','Pasas, mango, orejones y fruta'],['chuches','Caramelos y golosinas','Gominolas, caramelos y chocolates'],['variados','Pipas, aperitivos y mezclas','Pipas, kikos, habas y revueltos']];
 host.innerHTML=families.map(([id,title,desc])=>{const sample=Object.entries(products).find(([pid,p])=>catalogGroup(p)===id&&productImage(pid,p));const photo=sample?'<img class="family-tile-photo" src="'+escapeHTML(productImage(sample[0],sample[1]))+'" alt="" loading="lazy" decoding="async">':'';return '<button class="family-tile" data-family="'+id+'">'+photo+'<span class="family-tile-title">'+title+'</span><span class="family-tile-desc">'+desc+'</span><span class="family-tile-link">Explorar →</span></button>'}).join('');
 host.querySelectorAll('.family-tile-photo').forEach(img=>img.addEventListener('error',()=>img.remove(),{once:true}));
 host.querySelectorAll('[data-family]').forEach(b=>b.onclick=()=>{const f=b.dataset.family;document.querySelectorAll('.filter').forEach(x=>x.classList.toggle('active',x.dataset.filter===f));activeSubfamily='todos';renderSubfamilies(f);renderProducts();document.getElementById('catalogo').scrollIntoView({behavior:'smooth'})});
}
function renderProducts(){
 const grid=document.getElementById('products');if(!grid)return;
 const active=document.querySelector('.filter.active')?.dataset.filter||'todos';
 const words=catalogSearchWords(document.getElementById('productSearch')?.value||'').filter(word=>!['de','del','la','el','los','las','un','una','y','con','sin','por','favor'].includes(word));
 const entries=Object.entries(products).filter(([id,p])=>{
  const haystack=normalizeCatalogText([p.name,p.desc,p.tag,p.category,catalogGroup(p),productFamily(p)].join(' '));
  return (active==='todos'||catalogGroup(p)===active)&&(activeSubfamily==='todos'||productFamily(p)===activeSubfamily)&&words.every(word=>haystack.includes(word));
 });
 entries.sort(([idA],[idB])=>Number(hasUniqueProductImage(idB))-Number(hasUniqueProductImage(idA)));
 const card=([id,p])=>{
  const safeId=escapeHTML(id);
  const safeName=escapeHTML(p.name);
  const src=productImage(id,p);
  const photo=src?'<img class="product-photo" data-image-product="'+safeId+'" src="'+escapeHTML(src)+'" alt="'+safeName+'" loading="lazy" decoding="async">':productPlaceholder(p);
  return '<article class="product">'+photo+'<div class="product-body"><h3>'+safeName+'</h3><p>'+escapeHTML(p.desc)+'</p><span class="price">'+euro(p.price)+' <span class="unit">/ kg</span></span><div class="format-preview" aria-label="Formatos disponibles"><span>100 g</span><span>250 g</span><span>500 g</span><span>1 kg</span><span>5 kg</span><span>10 kg</span><span>20 kg</span><span>+20 kg</span></div><button class="details" data-product="'+safeId+'">Elegir formato y añadir</button></div></article>';
 };
 const grouped=active==='todos'&&activeSubfamily==='todos'&&words.length===0;
 if(grouped){
  const familyOrder=[['frutos','Frutos secos'],['fruta','Frutas deshidratadas'],['variados','Pipas, aperitivos y mezclas'],['chuches','Caramelos y golosinas']];
  const sections=familyOrder.map(([key,title])=>{
   const items=entries.filter(([id,p])=>catalogGroup(p)===key);
   if(!items.length)return '';
   return '<section class="catalog-family-section" data-catalog-family="'+key+'"><div class="catalog-family-heading"><h3>'+title+'</h3><span>'+items.length+' productos</span><button class="family-see-all" data-see-family="'+key+'">Ver familia →</button></div><div class="family-product-grid">'+items.map(card).join('')+'</div></section>';
  }).join('');
  grid.classList.add('catalog-grouped');grid.innerHTML=sections||'<div class="no-products">No hay productos disponibles.</div>';
 }else{
  grid.classList.remove('catalog-grouped');grid.innerHTML=entries.length?entries.map(card).join(''):'<div class="no-products">No hay productos que coincidan. Prueba con otra palabra o categoría.</div>';
 }
 grid.querySelectorAll('[data-image-product]').forEach(img=>img.addEventListener('error',()=>{
  const p=products[img.dataset.imageProduct];if(!p)return;
  const placeholder=document.createElement('div');placeholder.className='product-placeholder';placeholder.setAttribute('role','img');placeholder.setAttribute('aria-label','Imagen no disponible: '+p.name);
  placeholder.innerHTML=productIllustration(p)+'<span class="placeholder-category">'+escapeHTML(({frutos:'FRUTOS SECOS',fruta:'FRUTA DESHIDRATADA',chuches:'CHOCOLATES Y GOLOSINAS',variados:'SNACKS Y VARIADOS'}[catalogGroup(p)]||'CATÁLOGO'))+'</span><strong>'+escapeHTML(p.name)+'</strong>';placeholder.classList.add('product-illustrated');img.replaceWith(placeholder);
 }));
 const count=document.getElementById('catalogResultCount');if(count)count.textContent=entries.length+' productos'+(active==='todos'?' en el catálogo':' en esta categoría');
 grid.querySelectorAll('[data-product]').forEach(btn=>btn.addEventListener('click',()=>showProduct(btn.dataset.product)));
 grid.querySelectorAll('[data-see-family]').forEach(btn=>btn.addEventListener('click',()=>{const f=btn.dataset.seeFamily;document.querySelectorAll('.filter').forEach(x=>x.classList.toggle('active',x.dataset.filter===f));activeSubfamily='todos';renderSubfamilies(f);renderProducts();document.getElementById('catalogo').scrollIntoView({behavior:'smooth'})}));
}
document.querySelectorAll('.filter').forEach(btn=>btn.addEventListener('click',()=>{document.querySelectorAll('.filter').forEach(x=>x.classList.toggle('active',x===btn));activeSubfamily='todos';renderSubfamilies(btn.dataset.filter);renderProducts()}));
document.getElementById('productSearch')?.addEventListener('input',renderProducts);
renderFamilyTiles();renderSubfamilies('todos');renderProducts();
let selected=null;
let selectedId=null;
let modalReturnFocus=null;
const modalFocusSelector='a[href],button:not([disabled]),input:not([disabled]),select:not([disabled]),textarea:not([disabled]),[tabindex]:not([tabindex="-1"])';
function openModal(id){
 const modal=document.getElementById(id);
 if(!modal)return;
 const currentlyOpen=document.querySelector('.modal.open');
 if(!currentlyOpen)modalReturnFocus=document.activeElement;
 if(currentlyOpen&&currentlyOpen!==modal){currentlyOpen.classList.remove('open');currentlyOpen.setAttribute('aria-hidden','true')}
 modal.classList.add('open');
 modal.setAttribute('aria-hidden','false');
 const first=modal.querySelector(modalFocusSelector);
 if(first)first.focus({preventScroll:true});
}
function closeModal(id,restoreFocus=true){
 const modal=typeof id==='string'?document.getElementById(id):id;
 if(!modal)return;
 modal.classList.remove('open');
 modal.setAttribute('aria-hidden','true');
 if(restoreFocus&&!document.querySelector('.modal.open')&&modalReturnFocus&&typeof modalReturnFocus.focus==='function'){
  modalReturnFocus.focus({preventScroll:true});
  modalReturnFocus=null;
 }
}
function updatePackPrice(){if(!selected)return;const grams=Number(document.getElementById('weightSelect').value);document.getElementById('packPrice').textContent=euro(selected.price*grams/1000);document.getElementById('modalNote').textContent='Precio de referencia: '+euro(selected.price)+' por kg. El importe del formato se calcula proporcionalmente y sin recargos; Don Miguel y Fabián confirmarán disponibilidad y precio final antes de aceptar el pedido.'}
function showProduct(id){
 if(!hasProductId(id))return;
 selectedId=id;
 selected=products[id];
 const src=productImage(id,selected);
 const hasPhoto=Boolean(src);
 document.getElementById('modalTitle').textContent=selected.name;
 document.getElementById('modalTag').textContent=selected.tag;
 document.getElementById('modalDesc').textContent=selected.desc;
 const allergen=document.getElementById('modalAllergen');
 const info=allergenInfo(selected);
 allergen.textContent=(info.found.length?'Alérgeno identificado por denominación: '+info.found.join(', ')+'. ':'')+'La ficha del proveedor no detalla todos los ingredientes ni las posibles trazas. Si tienes alergia o intolerancia, confirma la etiqueta del lote con Don Miguel y Fabián antes de comprar.';
 const photo=document.getElementById('modalPhoto');
 const caption=document.querySelector('.modal-image-caption');
 photo.replaceChildren();
 photo.classList.toggle('photo-pending',!hasPhoto);
 if(hasPhoto){
  photo.setAttribute('aria-label','Fotografía ilustrativa de '+selected.name);
  const image=document.createElement('img');
  image.src=src;
  image.alt='Fotografía ilustrativa de '+selected.name;
  image.loading='eager';
  image.decoding='async';
  image.addEventListener('error',()=>{
   photo.replaceChildren();
   photo.classList.add('photo-pending');
   photo.textContent='Fotografía no disponible · '+selected.name;
   renderProductImageCredit(caption,selected,false);
  },{once:true});
  photo.append(image);
 }else{
  photo.setAttribute('aria-label','Fotografía pendiente para '+selected.name);
  photo.textContent='Fotografía pendiente de incorporación · '+selected.name;
 }
 renderProductImageCredit(caption,selected,hasPhoto);
 document.getElementById('weightSelect').value='1000';
 document.getElementById('qtyKg').value='1';
 updatePackPrice();
 openModal('productModal');
}
document.getElementById('weightSelect').addEventListener('change',updatePackPrice);
document.querySelectorAll('[data-close]').forEach(b=>b.addEventListener('click',()=>closeModal(b.dataset.close)));
document.querySelectorAll('.modal').forEach(m=>m.addEventListener('click',e=>{if(e.target===m)closeModal(m)}));
document.addEventListener('keydown',e=>{
 const opened=document.querySelector('.modal.open');
 if(e.key==='Escape'&&opened){e.preventDefault();closeModal(opened);return}
 if(e.key==='Tab'&&opened){
  const focusable=[...opened.querySelectorAll(modalFocusSelector)].filter(el=>el.offsetParent!==null);
  if(!focusable.length){e.preventDefault();return}
  const first=focusable[0],last=focusable[focusable.length-1];
  if(e.shiftKey&&document.activeElement===first){e.preventDefault();last.focus()}
  else if(!e.shiftKey&&document.activeElement===last){e.preventDefault();first.focus()}
 }
 if(e.key==='Escape'&&!opened&&chatPanel?.classList.contains('open'))closeChatPanel();
});
const cart=(()=>{try{const saved=JSON.parse(localStorage.getItem("almendrasCart")||"[]");return Array.isArray(saved)?saved.filter(x=>x&&typeof x==='object'&&hasProductId(x.id)&&[100,250,500,1000,5000,10000,20000].includes(Number(x.grams))&&Number.isInteger(Number(x.quantity))&&Number(x.quantity)>0&&Number(x.quantity)<=50).map(x=>({id:x.id,name:products[x.id].name,price:products[x.id].price,grams:Number(x.grams),quantity:Number(x.quantity)})):[]}catch(e){return []}})();
function renderCart(){try{localStorage.setItem('almendrasCart',JSON.stringify(cart))}catch(e){}const host=document.getElementById('cartItems');host.innerHTML='';let subtotal=0;cart.forEach((item,index)=>{const itemSubtotal=item.price*item.grams/1000*item.quantity;subtotal+=itemSubtotal;const row=document.createElement('div');row.className='cart-line';row.setAttribute('role','listitem');const info=document.createElement('div');const name=document.createElement('strong');name.textContent=item.name;const detail=document.createElement('small');detail.textContent=item.quantity+' × '+item.grams+' g · '+euro(item.price)+' / kg · '+euro(itemSubtotal);info.append(name,detail);const remove=document.createElement('button');remove.type='button';remove.textContent='Quitar';remove.setAttribute('aria-label','Quitar '+item.name+', formato '+item.grams+' gramos');remove.onclick=()=>{cart.splice(index,1);renderCart()};row.append(info,remove);host.append(row)});if(!cart.length)host.innerHTML='<p class="smallprint">Aún no has añadido productos.</p>';const weight=getCartWeightGrams(cart);const tier=calculateShipping(weight);const total=subtotal+tier.price;document.getElementById('cartSubtotal').textContent=euro(subtotal);document.getElementById('cartWeight').textContent=weight.toLocaleString('es-ES')+' g ('+(weight/1000).toLocaleString('es-ES',{maximumFractionDigits:3})+' kg)';document.getElementById('cartShipping').textContent=euro(tier.price)+' · '+tier.label;document.getElementById('cartTotal').textContent=euro(total);document.getElementById('cartCount').textContent=cart.reduce((n,x)=>n+x.quantity,0)}

document.getElementById('addToCart').onclick=()=>{
 if(!selected||!selectedId)return;
 const grams=Number(document.getElementById('weightSelect').value);
 const quantity=Number(document.getElementById('qtyKg').value);
 if(![100,250,500,1000,5000,10000,20000].includes(grams)){alert('Selecciona un formato válido.');return}
 if(!Number.isInteger(quantity)||quantity<1||quantity>50){alert('Indica entre 1 y 50 unidades de este formato.');return}
 const found=cart.find(x=>x.id===selectedId&&x.grams===grams);
 if(found&&found.quantity+quantity>50){alert('El máximo acumulado por producto y formato es de 50 unidades.');return}
 if(found)found.quantity+=quantity;
 else cart.push({id:selectedId,name:selected.name,price:selected.price,grams,quantity});
 renderCart();
 openModal('cartModal');
};
renderCart();
window.addEventListener('almendras:shipping-updated',renderCart);
window.addEventListener('almendras:cart-updated',event=>{
 cart.length=0;
 const incoming=Array.isArray(event.detail)?event.detail:[];
 incoming.forEach(item=>{
  if(item&&hasProductId(item.id)&&[100,250,500,1000,5000,10000,20000].includes(Number(item.grams))&&Number.isInteger(Number(item.quantity))&&Number(item.quantity)>0&&Number(item.quantity)<=50){
   cart.push({id:item.id,name:products[item.id].name,price:products[item.id].price,grams:Number(item.grams),quantity:Number(item.quantity)});
  }
 });
 renderCart();
});
document.getElementById('cartFab').onclick=()=>{renderCart();openModal('cartModal')};
document.getElementById('clearCart').onclick=()=>{cart.length=0;renderCart()};

function buildCartOrderMessage(){
 if(!cart.length){alert('Añade al menos un producto al pedido.');return null}
 const buyer=document.getElementById('cartBuyer').value.trim();
 const phone=document.getElementById('cartPhone').value.trim();
 if(!buyer||!phone){alert('Indica tu nombre y teléfono de contacto.');return null}
 const phoneDigits=phone.replace(/\D/g,'');
 if(phoneDigits.length<9||phoneDigits.length>15){alert('Comprueba el teléfono: debe contener entre 9 y 15 cifras.');return null}
 let subtotalProducts=0;
 const lines=cart.map(item=>{
  const subtotal=item.price*item.grams/1000*item.quantity;
  subtotalProducts+=subtotal;
  return '• '+item.name+'\n  '+item.quantity+' × '+item.grams+' g · '+euro(subtotal);
 });
 const totalGrams=getCartWeightGrams(cart);
 const shippingTier=calculateShipping(totalGrams);
 const finalTotal=subtotalProducts+shippingTier.price;
 const notes=document.getElementById('cartNotes').value.trim();
 return '🛒 *NUEVO PEDIDO · ALMENDRAS DE MÁLAGA*\n\n'
  +'👤 *Cliente:* '+buyer+'\n'
  +'📱 *Teléfono:* '+phone+'\n\n'
  +'📦 *PRODUCTOS*\n'+lines.join('\n\n')+'\n\n'
  +'⚖️ *PESO TOTAL:* '+totalGrams.toLocaleString('es-ES')+' g ('+(totalGrams/1000).toLocaleString('es-ES',{maximumFractionDigits:3})+' kg)\n'
  +'🚚 *ENVÍO:* '+shippingTier.label+' · '+euro(shippingTier.price)+'\n'
  +'🧾 *SUBTOTAL PRODUCTOS:* '+euro(subtotalProducts)+'\n'
  +'💰 *TOTAL ORIENTATIVO:* '+euro(finalTotal)+'\n\n'
  +'📝 *Observaciones:* '+(notes||'Ninguna')+'\n\n'
  +'📍 Pedido realizado desde el catálogo web.\n'
  +'El envío mostrado es provisional. Esta solicitud no confirma pedido, disponibilidad, precio final ni pago; el negocio lo confirmará por WhatsApp.';
}

document.getElementById('sendCartWhatsApp666').onclick=()=>{const message=buildCartOrderMessage();if(message)window.location.href='https://wa.me/34666068765?text='+encodeURIComponent(message)};

async function copyTextSafely(value){try{if(navigator.clipboard&&window.isSecureContext){await navigator.clipboard.writeText(value);return true}}catch(e){}const area=document.createElement('textarea');area.value=value;area.setAttribute('readonly','');area.style.position='fixed';area.style.opacity='0';document.body.appendChild(area);area.select();let copied=false;try{copied=document.execCommand('copy')}catch(e){}area.remove();return copied}
document.getElementById('share').onclick=async()=>{const data={title:'Almendras de Málaga',text:'Catálogo profesional de frutos secos en Málaga',url:location.href};if(navigator.share){try{await navigator.share(data)}catch(e){if(e&&e.name!=='AbortError')console.warn('No se pudo compartir el catálogo',e)}}else if(await copyTextSafely(location.href)){alert('Enlace copiado')}else{alert('No se pudo copiar el enlace. Puedes copiar la dirección desde el navegador.')}};
const almondMark='<svg viewBox="0 0 48 48" xmlns="http://www.w3.org/2000/svg"><path d="M24 4C14 12 9 20 11 29c2 8 8 13 13 13s11-5 13-13C39 20 34 12 24 4Z" fill="#b77a35" stroke="#70451f" stroke-width="1.8"/><path d="M24 9c-5 8-8 14-7 21 1 5 4 8 7 9" fill="none" stroke="#f3d39a" stroke-width="2.2" stroke-linecap="round"/><path d="M19 15c2-2 4-3 6-4" stroke="#f8e4bb" stroke-width="1.6" stroke-linecap="round"/></svg>';
function makeQR(id){const host=document.getElementById(id);host.innerHTML='<div class="qr-shell"><div class="qr-code"></div><div class="qr-logo">'+almondMark+'</div></div>';const el=host.querySelector('.qr-code');if(window.QRCode){new QRCode(el,{text:location.href.split('#')[0],width:210,height:210,colorDark:'#243b2e',colorLight:'#ffffff',correctLevel:QRCode.CorrectLevel.H});}else el.textContent=location.href}
function qrCanvas(){const source=document.querySelector('#ownerqr .qr-code canvas');if(!source)return null;const scale=3,pad=16*scale,side=source.width*scale+pad*2,out=document.createElement('canvas');out.width=side;out.height=side;const c=out.getContext('2d');c.fillStyle='#fff';c.fillRect(0,0,side,side);c.drawImage(source,pad,pad,source.width*scale,source.height*scale);const center=side/2,r=29*scale;c.fillStyle='#fff';c.beginPath();c.roundRect(center-r,center-r,2*r,2*r,12*scale);c.fill();c.strokeStyle='#eee1ce';c.lineWidth=2*scale;c.stroke();c.save();c.translate(center-r+8*scale,center-r+8*scale);c.scale((2*r-16*scale)/48,(2*r-16*scale)/48);const svg=new Blob([almondMark],{type:'image/svg+xml'}),url=URL.createObjectURL(svg),img=new Image();return new Promise(resolve=>{img.onload=()=>{c.drawImage(img,0,0,48,48);URL.revokeObjectURL(url);resolve(out)};img.onerror=()=>{URL.revokeObjectURL(url);resolve(out)};img.src=url})}
window.addEventListener('load',()=>makeQR('qr'));
document.getElementById('owner').onclick=()=>{document.getElementById('publicUrl').value=location.href.split('#')[0];openModal('ownerModal');makeQR('ownerqr')};
document.getElementById('downloadQR').onclick=async()=>{const c=await qrCanvas().catch(()=>null);if(!c){alert('No se pudo generar el QR. Comprueba la conexión y vuelve a intentarlo.');return}try{const a=document.createElement('a');a.download='QR-Almendras-de-Malaga.png';a.href=c.toDataURL('image/png');a.click()}catch(e){alert('No se pudo descargar el QR en este navegador.')}};
document.getElementById('copyURL').onclick=async()=>{const value=document.getElementById('publicUrl').value;if(await copyTextSafely(value)){alert('Enlace copiado')}else{document.getElementById('publicUrl').focus();document.getElementById('publicUrl').select();alert('Selecciona y copia el enlace manualmente.')}};

// Asistente local: responde usando las fichas de products, sin inventar stock.
const chatPanel=document.getElementById('productChat'),chatFab=document.getElementById('chatFab'),chatMessages=document.getElementById('chatMessages');
function chatSay(text,who){const node=document.createElement('div');node.className='chat-msg '+who;node.textContent=String(text).replace(/\\\\n/g,'\n');node.style.whiteSpace='pre-line';chatMessages.appendChild(node);chatMessages.scrollTop=chatMessages.scrollHeight}
function answerProductQuestion(raw){
 const q=normalizeCatalogText(raw);
 const all=Object.entries(products);
 const ignored=['100','250','500','1000','g','gr','kg','precio','precios','cuanto','cuantos','cuanta','cuantas','cuesta','vale','coste','tenei','teneis','tiene','tienen','hay','disponibilidad','disponible','stock','formato','formatos','gramo','gramos','peso','kilo','kilos','quiero','busco','necesito','producto','productos','favor','por','de','del','la','el','los','las','un','una','con','sin','para','que','es','son','me','dime','consulta','consultar'];
 const searchQuery=q.replace(/\b(?:100|250|500|1000|5000|10000|20000)\s*(?:g|gr|gramos)?\b|\b(?:1|5|10|20)\s*(?:kg|kilo|kilos)\b/g,' ');
 const words=catalogSearchWords(searchQuery).filter(w=>!ignored.includes(w));
 const matches=all.filter(([id,p])=>{
  const haystack=normalizeCatalogText([p.name,p.desc,p.tag,p.category,catalogGroup(p)].join(' '));
  return words.length>0&&words.every(w=>haystack.includes(w));
 });
 const euroPrice=value=>new Intl.NumberFormat('es-ES',{style:'currency',currency:'EUR'}).format(value);
 const requestedGrams=(()=>{const gramsMatch=q.match(/\b(100|250|500|1000|5000|10000|20000)\s*(g|gr|gramos)?\b/);if(gramsMatch)return Number(gramsMatch[1]);const kilosMatch=q.match(/\b(1|5|10|20)\s*(kg|kilo|kilos)\b/);if(kilosMatch)return Number(kilosMatch[1])*1000;if(/medio kilo|500 g|500gr/.test(q))return 500;if(/un kilo|1 kilo|1 kg|1000 g/.test(q))return 1000;return null})();
 if(/disponib|stock|hay existencias|teneis|ten[eé]is|queda/.test(q)){
  if(matches.length)return 'En el catálogo aparece: '+matches.slice(0,8).map(([id,p])=>p.name).join(', ')+'. El stock real no está conectado a la web; Don Miguel y Fabián confirman disponibilidad por WhatsApp: +34 666 068 765.';
  return 'La web no consulta inventario en tiempo real. Dime el nombre del producto o pregunta directamente a Don Miguel y Fabián por WhatsApp: +34 666 068 765.';
 }
 if(matches.length&&requestedGrams){
  return matches.slice(0,6).map(([id,p])=>p.name+': '+euroPrice(p.price*requestedGrams/1000)+' por '+requestedGrams+' g ('+euroPrice(p.price)+' / kg orientativo).').join('\\n')+'\\nEl precio final y la disponibilidad deben confirmarse.';
 }
 if(matches.length&&/precio|cu[aá]nto|coste|vale|format|gram|peso|kilo|kg|cantidad/.test(q)){
  return matches.slice(0,6).map(([id,p])=>p.name+': '+euroPrice(p.price)+' / kg orientativo. Formatos: 100 g ('+euroPrice(p.price*.1)+'), 250 g ('+euroPrice(p.price*.25)+'), 500 g ('+euroPrice(p.price*.5)+'), 1 kg ('+euroPrice(p.price)+'), 5 kg ('+euroPrice(p.price*5)+'), 10 kg ('+euroPrice(p.price*10)+') y 20 kg ('+euroPrice(p.price*20)+').').join('\\n')+'\\nEl importe final y la disponibilidad deben confirmarse con Don Miguel y Fabián.';
 }
 if(matches.length)return 'He encontrado estas referencias en el catálogo:\\n'+matches.slice(0,8).map(([id,p])=>'• '+p.name+' — '+euroPrice(p.price)+' / kg orientativo').join('\\n')+'\\n\\nFormatos: 100 g, 250 g, 500 g, 1 kg, 5 kg, 10 kg y 20 kg. Disponibilidad y precio final pendientes de confirmación.';
 if(/formato|gram|peso|tamano|tamaño|kilo|kg|cantidad/.test(q))return 'Puedes solicitar los formatos de 100 g, 250 g, 500 g, 1 kg, 5 kg, 10 kg y 20 kg. Para cantidades superiores, consulta con Don Miguel y Fabián.';
 if(/chocolate|golosin|caramel|snack|fruta|nuez|almendra|cacahuete|pistacho|anacardo|avellana|pipa|semilla/.test(q)){
  const group=all.filter(([id,p])=>catalogGroup(p)===(/chocolate|golosin|caramel/.test(q)?'chuches':/fruta/.test(q)?'fruta':/snack|pipa|semilla/.test(q)?'variados':'frutos'));
  return 'En esa familia aparecen, por ejemplo: '+group.slice(0,10).map(([id,p])=>p.name).join(', ')+'. Dime la variedad exacta y te indicaré su precio orientativo.';
 }
 return 'Puedo ayudarte con variedades, precios orientativos y formatos. Prueba con el nombre de un producto, por ejemplo «almendra cruda pelada», «pistacho turco tostado» o «kiwi deshidratado». La disponibilidad real la confirman Don Miguel y Fabián.';
}
chatFab.addEventListener('click',()=>{const open=!chatPanel.classList.contains('open');chatPanel.classList.toggle('open',open);chatPanel.setAttribute('aria-hidden',String(!open));chatFab.setAttribute('aria-expanded',String(open));if(open)document.getElementById('chatInput').focus()});
// Burbuja de bienvenida discreta: no abre el chat ni bloquea la navegación.
(function(){
 if(!chatFab||!chatPanel||sessionStorage.getItem('assistantBubbleSeen'))return;
 const bubble=document.createElement('button');bubble.type='button';bubble.className='assistant-welcome-bubble';bubble.setAttribute('aria-label','Abrir asistente: ¿Buscas algo? Te ayudo a encontrarlo');bubble.textContent='¿Buscas algo? Te ayudo a encontrarlo ✨';
 document.body.appendChild(bubble);
 const timer=setTimeout(()=>{if(!chatPanel.classList.contains('open'))bubble.classList.add('visible')},6500);
 bubble.addEventListener('click',()=>{bubble.remove();sessionStorage.setItem('assistantBubbleSeen','1');chatFab.click()});
 chatFab.addEventListener('click',()=>{bubble.remove();sessionStorage.setItem('assistantBubbleSeen','1');clearTimeout(timer)},{once:false});
})();
function closeChatPanel(){chatPanel.classList.remove('open');chatPanel.setAttribute('aria-hidden','true');chatFab.setAttribute('aria-expanded','false');chatFab.focus()}
document.getElementById('chatClose').addEventListener('click',closeChatPanel);
const chatSessionId=(()=>{try{let id=sessionStorage.getItem('almendrasChatSession');if(!id){id=crypto.randomUUID?crypto.randomUUID():'s-'+Date.now()+'-'+Math.random().toString(36).slice(2);sessionStorage.setItem('almendrasChatSession',id)}return id}catch(e){return 's-'+Date.now()}})();
async function sendAssistantMessage(q){
 const storeTools=window.storeAssistantTools;
 const base=String(window.ALMENDRAS_ASSISTANT_API||'').replace(/\/+$/,'');
 if(storeTools){
  const local=storeTools.interpretLocal(q);
  if(local.handled){chatSay(local.reply,'bot');return}
 }
 if(!base){chatSay(answerProductQuestion(q),'bot');return}
 const typing=document.createElement('div');typing.className='chat-msg bot chat-typing';typing.textContent='Pensando…';chatMessages.appendChild(typing);chatMessages.scrollTop=chatMessages.scrollHeight;
 try{
  const response=await fetch(base+'/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({session_id:chatSessionId,message:q})});
  const data=await response.json();
  typing.remove();
  if(!response.ok||!data.reply)throw new Error(data.error||'No se pudo responder');
  chatSay(data.reply,'bot');
  if(Array.isArray(data.actions)&&data.actions.length&&storeTools){
   try{
    for(const action of data.actions){if(action.type==='add_to_cart')storeTools.addToCart(action.productId,action.grams,action.quantity)}
    const summary=storeTools.cartSummary();
    chatSay('\\n🛒 Carrito actualizado\\n'+summary.items.map(item=>'• '+item.name+' — '+item.quantity+' × '+item.grams+' g = '+item.subtotal.toFixed(2)+' €').join('\\n')+'\\n\\n⚖️ Peso total: '+summary.weightGrams+' g\\n🧾 Subtotal: '+summary.subtotal.toFixed(2)+' €\\n🚚 Envío ('+summary.shipping.label+'): '+summary.shipping.price.toFixed(2)+' €\\n💰 Total: '+summary.total.toFixed(2)+' €\\n\\nTarifas provisionales y pedido pendiente de confirmación.','bot');
   }catch(actionError){chatSay('No he podido actualizar el carrito: '+actionError.message,'bot')}
  }
 }catch(error){typing.remove();chatSay(answerProductQuestion(q)+'\n\nEl asistente inteligente no está disponible ahora.','bot')}
}
document.getElementById('chatForm').addEventListener('submit',e=>{e.preventDefault();const input=document.getElementById('chatInput'),q=input.value.trim();if(!q)return;chatSay(q,'user');input.value='';input.focus();sendAssistantMessage(q)});
document.querySelectorAll('[data-assistant-prompt]').forEach(button=>button.addEventListener('click',()=>{const input=document.getElementById('chatInput');input.value=button.dataset.assistantPrompt;document.getElementById('chatForm').requestSubmit()}));
const translations={
en:{eyebrow:'Artisan selection · Historic centre',heroTitle:'The taste of Málaga,<br>made to be shared.',heroText:'Almonds, nuts and caramelised specialities. Discover our products and request a trade price list for your business.',heroBtn:'Explore catalogue ↓',quality:'Selected products',professionalLabel:'Trade enquiries welcome',locationLabel:'Beside the Cathedral',eyebrow2:'Trade catalogue',catalogTitle:'Our products',catalogText:'Tap a product to view prices per kilo and calculated pack prices.',businessNoteTitle:'Trade prices',businessNote:'Ask us for current prices by kilo and pack size. Availability and delivery are confirmed directly.',specialty:'House speciality',p1:'Caramelised almonds',d1:'Almonds coated in crunchy caramel, packed in bags.',indicative:'per kilo',view:'Check pack sizes and request price →',naturalTag:'Natural selection',p2:'Natural almonds',d2:'Selected almonds for bulk or packed sales.',snack:'Snack',p3:'Sunflower seeds',d3:'Roasted sunflower seeds for snacks and retail.',sweet:'Traditional sweet',p4:'Caramelised peanuts',d4:'Peanuts coated in crunchy caramel.',priceFoot:'Prices and pack availability are confirmed directly with the stall. Photographs are illustrative.',forBusiness:'For your business',businessTitle:'A local supplier for your shop',businessText:'Prepare your request with product, quantity and pack size. We can discuss a trade proposal for shops, cafés, hotels, distributors and other professionals.',contact:'Request information',step1:'Choose products from the catalogue.',step2:'Check pack sizes and prices per kilo.',step3:'Send your request for a quotation.',visit:'Visit us',visitTitle:'In the heart of Málaga',address:'Corner of Calle Molina Lario, next to Málaga Cathedral.',maps:'Get directions',share:'Share catalogue',qrTitle:'Scan and save our catalogue',qrText:'Direct access to the digital catalogue',format:'Pack size',priceHead:'Indicative price',quote:'Request a trade quotation',close:'Close',ownerTitle:'Catalogue QR code',download:'Download QR PNG',copy:'Copy link',ownerNote:'This QR code points to the public catalogue.',languageNotice:'Translation is partial. Original product names and descriptions remain in Spanish.'},
fr:{eyebrow:'Sélection artisanale · Centre historique',heroTitle:'Le goût de Málaga,<br>à partager.',heroText:'Amandes, fruits secs et spécialités caramélisées. Découvrez nos produits et demandez un tarif professionnel.',heroBtn:'Voir le catalogue ↓',quality:'Produits sélectionnés',professionalLabel:'Offres aux professionnels',locationLabel:'Près de la Cathédrale',eyebrow2:'Catalogue professionnel',catalogTitle:'Nos produits',catalogText:'Touchez un produit pour consulter les formats disponibles et demander le prix actuel.',businessNoteTitle:'Tarifs professionnels',businessNote:'Demandez les tarifs actuels au kilo et par format. La disponibilité et la livraison sont à confirmer directement.',specialty:'Spécialité',p1:'Amandes caramélisées',d1:'Amandes enrobées de caramel croquant, en sachets.',indicative:'prix au kilo',view:'Consulter les formats et demander le prix →',naturalTag:'Sélection naturelle',p2:'Amandes naturelles',d2:'Amandes sélectionnées, en vrac ou emballées.',snack:'Apéritif',p3:'Graines de tournesol',d3:'Graines de tournesol grillées pour la vente et l’apéritif.',sweet:'Douceur traditionnelle',p4:'Cacahuètes caramélisées',d4:'Cacahuètes enrobées de caramel croquant.',priceFoot:'Les prix et les formats disponibles sont confirmés directement au stand. Photos illustratives.',forBusiness:'Pour votre commerce',businessTitle:'Un fournisseur de proximité',businessText:'Préparez votre demande avec le produit, la quantité et le format. Contactez-nous pour une proposition professionnelle.',contact:'Demander des informations',step1:'Choisissez les produits du catalogue.',step2:'Consultez les formats et les prix au kilo.',step3:'Envoyez votre demande de devis.',visit:'Nous rendre visite',visitTitle:'Au cœur de Málaga',address:'Angle de la Calle Molina Lario, près de la Cathédrale.',maps:'Itinéraire',share:'Partager le catalogue',qrTitle:'Scannez notre catalogue',qrText:'Accès direct au catalogue numérique',format:'Format',priceHead:'Prix indicatif',quote:'Demander un devis',close:'Fermer',ownerTitle:'Code QR du catalogue',download:'Télécharger QR PNG',copy:'Copier le lien',ownerNote:'Ce QR code ouvre le catalogue public.',languageNotice:'La traduction est partielle. Les noms et descriptions originaux des produits restent en espagnol.'},
de:{eyebrow:'Handwerkliche Auswahl · Historisches Zentrum',heroTitle:'Der Geschmack Málagas,<br>zum Teilen.',heroText:'Mandeln, Nüsse und karamellisierte Spezialitäten. Entdecken Sie unsere Produkte und fragen Sie nach Händlerpreisen.',heroBtn:'Katalog ansehen ↓',quality:'Ausgewählte Produkte',professionalLabel:'Angebote für Gewerbe',locationLabel:'Neben der Kathedrale',eyebrow2:'Händlerkatalog',catalogTitle:'Unsere Produkte',catalogText:'Tippen Sie auf ein Produkt, um verfügbare Packungsgrößen zu prüfen und den aktuellen Preis anzufragen.',businessNoteTitle:'Händlerpreise',businessNote:'Fragen Sie die aktuellen Preise pro Kilo und Packungsgröße an. Verfügbarkeit und Lieferung werden direkt bestätigt.',specialty:'Spezialität',p1:'Gebrannte Mandeln',d1:'Mandeln mit knuspriger Karamellschicht, abgepackt.',indicative:'Preis pro Kilo',view:'Packungsgrößen prüfen und Preis anfragen →',naturalTag:'Naturauswahl',p2:'Naturmandeln',d2:'Ausgewählte Mandeln lose oder verpackt.',snack:'Snack',p3:'Sonnenblumenkerne',d3:'Geröstete Sonnenblumenkerne als Snack.',sweet:'Traditionelle Süßigkeit',p4:'Gebrannte Erdnüsse',d4:'Erdnüsse mit knusprigem Karamellüberzug.',priceFoot:'Preise und verfügbare Packungsgrößen werden direkt am Stand bestätigt. Fotos dienen der Illustration.',forBusiness:'Für Ihr Geschäft',businessTitle:'Ein lokaler Lieferant für Ihr Geschäft',businessText:'Senden Sie Produkt, Menge und Verpackungsgröße für ein individuelles Angebot.',contact:'Informationen anfragen',step1:'Produkte aus dem Katalog auswählen.',step2:'Größen und Preise pro Kilo ansehen.',step3:'Anfrage für ein Angebot senden.',visit:'Besuchen Sie uns',visitTitle:'Im Herzen von Málaga',address:'Ecke Calle Molina Lario, neben der Kathedrale.',maps:'Route anzeigen',share:'Katalog teilen',qrTitle:'Katalog scannen und speichern',qrText:'Direkter Zugang zum digitalen Katalog',format:'Packungsgröße',priceHead:'Preis pro Kilo',quote:'Angebot anfordern',close:'Schließen',ownerTitle:'Katalog-QR-Code',download:'QR PNG herunterladen',copy:'Link kopieren',ownerNote:'Dieser QR-Code führt zum öffentlichen Katalog.',languageNotice:'Die Übersetzung ist teilweise. Originale Produktnamen und Beschreibungen bleiben auf Spanisch.'}
};
document.querySelectorAll('[data-lang]').forEach(b=>b.onclick=()=>{
 const l=b.dataset.lang;
 if(!['es','en','fr','de'].includes(l))return;
 document.documentElement.lang=l;
 document.querySelectorAll('[data-lang]').forEach(x=>{x.classList.toggle('active',x===b);x.setAttribute('aria-pressed',String(x===b))});
 document.querySelectorAll('[data-t]').forEach(el=>{
  const k=el.dataset.t;
  if(!el.dataset.originalHtml)el.dataset.originalHtml=el.innerHTML;
  if(l==='es')el.innerHTML=el.dataset.originalHtml;
  else if(translations[l]&&translations[l][k])el.innerHTML=translations[l][k];
  else el.innerHTML=el.dataset.originalHtml;
 });
 try{localStorage.setItem('almendrasLanguage',l)}catch(e){}
});
try{const savedLanguage=localStorage.getItem('almendrasLanguage');if(savedLanguage&&savedLanguage!=='es')document.querySelector('[data-lang="'+savedLanguage+'"]')?.click()}catch(e){}

