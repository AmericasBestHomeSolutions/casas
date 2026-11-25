/* ---------- render (no editar — los datos de las casas viven en homes.js) ---------- */
(function(){
  const $ = id => document.getElementById(id);
  const money = n => "$" + Math.round(Number(n||0)).toLocaleString("en-US");

  // cadena de respaldo de imagen: foto real del vendedor → foto de Google Street
  // View (etiquetada) → tarjeta con degradado. Street View solo se muestra con su
  // etiqueta "Vista de calle · © Google", nunca como si fuera una foto real.
  window.__svFallback = function(img){
    const sv = img.getAttribute("data-sv");
    if (sv && !img.dataset.svTried){
      img.dataset.svTried = 1;
      img.onload = function(){ img.style.opacity = 1; const b = img.parentNode.querySelector(".sv-badge"); if (b) b.hidden = false; };
      img.src = sv;
    } else { img.remove(); }
  };
  const statusEs = s => {
    const k = (s||"").toLowerCase();
    if (k === "pending")  return "Pendiente";
    if (k === "available" || k === "") return "Disponible";
    return s;
  };

  // on-brand gradient palette; each city gets a stable one so the grid has gentle variety
  const FACES = [
    ["#15315e","#2f5c96"],["#15315e","#24508a"],["#1a4675","#3a6bab"],
    ["#1c3f70","#3f6db0"],["#0f2444","#24508a"],["#1c4a7a","#37639f"]
  ];
  const faceFor = s => {
    let h=0; for(const ch of (s||"")) h=(h*31+ch.charCodeAt(0))>>>0;
    return FACES[h % FACES.length];
  };
  // Las vendidas salen de la lista. Pendiente se queda, con una insignia, y no cuenta como disponible.
  const isPending = h => /^pending$/i.test(String((h && h.status) || "").trim());
  const isSold = h => /^sold$/i.test(String((h && h.status) || "").trim());
  const LISTINGS = HOMES.filter(h => !isSold(h));
  const houseMark = `<svg class="fmark" width="150" height="150" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 11.5 12 4l9 7.5"/><path d="M5 10v9h14v-9"/><path d="M10 19v-5h4v5"/></svg>`;
  function isNewHome(h){
    const raw = (typeof LISTED_ON !== "undefined" ? LISTED_ON : (window.LISTED_ON || {}))[h.id];
    const t = Date.parse(raw || "");
    return !!(raw && t && (Date.now() - t) <= 7 * 86400000);
  }

  // Default order. Seller photos come before Street View-only homes. Inside each
  // group: homes near the visitor first, then newest listed (visitor-near.js).
  function realPhoto(h){
    const meta = (window.PHOTO_INDEX || {})[h.id];
    return meta && meta.real ? 1 : 0;
  }
  function completeFirst(a, b){
    return (realPhoto(b) - realPhoto(a)) || ((b.address?1:0) - (a.address?1:0));
  }
  function defaultOrder(){
    const within = window.VisitorNear
      ? VisitorNear.compare((a, b) => (b.address?1:0) - (a.address?1:0))
      : (a, b) => {
          const t = h => Date.parse(((typeof LISTED_ON !== "undefined" ? LISTED_ON : (window.LISTED_ON || {}))[h.id]) || "") || 0;
          return (t(b) - t(a)) || ((b.address?1:0) - (a.address?1:0));
        };
    return (a, b) => (realPhoto(b) - realPhoto(a)) || within(a, b);
  }

  // filter options — built from whatever is in homes.js
  const states = [...new Set(LISTINGS.map(h => h.state).filter(Boolean))].sort();
  $("fState").insertAdjacentHTML("beforeend",
    states.map(s => `<option value="${s}">${s}</option>`).join(""));
  const allCities = [...new Set(LISTINGS.map(h => h.city).filter(Boolean))].sort();
  function fillCities(){
    const st = $("fState").value;
    const keep = $("fCity").value;
    const list = [...new Set(LISTINGS.filter(h => !st || h.state === st).map(h => h.city).filter(Boolean))].sort();
    $("fCity").innerHTML = `<option value="">Todas las ciudades</option>` +
      list.map(c => `<option value="${c}">${c}</option>`).join("");
    $("fCity").value = list.includes(keep) ? keep : "";   // a city from another state is cleared
  }
  fillCities();

  // hero stats — pending stays listed, but the count is homes still available
  const availableCount = LISTINGS.filter(h => !isPending(h)).length;
  $("statHomes").textContent = availableCount;
  $("statCities").textContent = allCities.length;
  $("otHomes").textContent = availableCount;
  $("otCities").textContent = allCities.length;

  function featureTag(h){
    if (isNewHome(h)) return "Nuevo";
    if (h.contractor) return "Para contratistas";
    const order = ["backyard","fenced_yard","basement","garage","central_air","attic","storage_shed","off_street_parking"];
    const labels = {backyard:"Patio", fenced_yard:"Patio cercado", basement:"Sótano", garage:"Garaje", central_air:"Aire central", attic:"Ático", storage_shed:"Cobertizo", off_street_parking:"Estacionamiento"};
    const f = h.features || {};
    const key = order.find(k => f[k] === "yes");
    return key ? labels[key] : "";
  }
  function cardHTML(h, opts){
    const [a,b] = faceFor(h.city + h.state);
    const rec = Number(h.beds);
    const specs = [
      rec ? `${rec} recámara${rec===1?"":"s"}` : "",
      h.baths ? `${h.baths} ba` : "",
      (h.sqft && Number(h.sqft)) ? `${Number(h.sqft).toLocaleString("en-US")} pies²` : ""
    ].filter(Boolean).join(" | ");
    const meta = (window.PHOTO_INDEX || {})[h.id] || {};
    const pending = isPending(h);
    const tag = pending ? "" : ((opts && opts.featured && h.featured) ? "Destacada" : featureTag(h));
    const where = [h.address, h.city, h.state].filter(Boolean).join(", ");
    const eager = opts && opts.eager;
    const photo = meta.card
      ? `<img src="${meta.card}" alt="Casa en ${h.city}, ${h.state}" width="${meta.w}" height="${meta.h}" loading="${eager?"eager":"lazy"}" decoding="async"${eager?' fetchpriority="high"':""}>`
      : "";
    const book = (typeof bookHref === "function")
      ? bookHref(h.id)
      : `https://owner.getownerfinancedhomes.com/book?home=${encodeURIComponent(h.id)}&lang=es`;
    const similar = `/?q=${encodeURIComponent([h.city, h.state].filter(Boolean).join(", "))}`;
    const action = pending
      ? `<a class="card-book" href="${similar}">Visitas cerradas: ver casas parecidas</a>`
      : `<a class="card-book" href="${book}">Agendar una visita</a>`;
    const away = (opts && opts.away != null) ? `<div class="card-away">a unas ${opts.away} millas</div>` : "";
    return `
    <div class="card${h.contractor?" is-cs":""}${pending?" is-pending":""}" data-hid="${h.id}">
      <a class="card-open" href="${encodeURIComponent(h.id)}.html">
      <div class="card-face" style="background:linear-gradient(135deg,${a},${b})">
        ${photo}
        <span class="sv-badge"${meta.sv?"":" hidden"}>Vista de calle · © Google</span>
        ${(h.photos||[]).length>1?`<button type="button" class="pg pv" aria-label="Foto anterior">‹</button><button type="button" class="pg nx" aria-label="Foto siguiente">›</button><span class="pdots">${Array.from({length:Math.min(6,(h.photos||[]).length)},(_,k)=>`<i${k?"":" class=\"on\""}></i>`).join("")}</span>`:""}
        ${pending ? `<span class="status-tag pending">Pendiente</span>` : (tag ? `<span class="z-feat">${tag}</span>` : "")}
        ${window.HomesCart?HomesCart.heart(h):""}
      </div>
      <div class="card-body">
        <div class="card-price"><span class="num">${money(h.monthlyPayment)}</span><span class="per">/mes</span></div>
        <div class="card-specs">${specs}</div>
        <div class="card-where">${where}</div>
        ${h.moveIn ? `<div class="card-down">${money(h.moveIn)} de enganche</div>` : ""}
        <div class="card-avail">${pending ? "Pendiente: visitas cerradas" : "Disponible ahora"}</div>
        ${away}
        ${h._dist!=null?`<div style="font-size:13px;color:var(--ink-soft);margin-top:4px">${h._dist.toFixed(1)} mi</div>`:""}
      </div>
      </a>
      ${action}
    </div>`;
  }

  const PER_PAGE = 12;   // a short, scannable page; the pager does the rest
  let page = 1;

  const hasCS = LISTINGS.some(h => h.contractor);
  if (hasCS) $("fTypeWrap").hidden = false;
  function filtered(){
    const state = $("fState").value;
    const city = $("fCity").value;
    const statusPick = ($("fStatus") && $("fStatus").value) || "";
    const bedsVal = Number($("fBeds").value) || 0;   // exact match; 4 means "4 or more"
    const bathsVal = Number($("fBaths").value) || 0;
    const type = hasCS ? $("fType").value : "all";
    const sort = $("fSort").value;
    const rng = (n, lo, hi) => (!lo || n >= lo) && (!hi || n <= hi);
    const payLo = Number($("fPayMin").value)||0, payHi = Number($("fPayMax").value)||0;
    const prLo = Number($("fPriceMin").value)||0, prHi = Number($("fPriceMax").value)||0;
    const downLo = Number($("fDownMin").value)||0, downHi = Number($("fDown").value)||0;
    // free-text: every word must appear in address/city/state/zip; "contractor"/"fixer" flips on Contractor Specials
    const CSW = /^(contractor|contratista|contratistas|special|specials|especial|especiales|fixer|investor)$/;
    let words = ($("fQ").value||"").toLowerCase().replace(/[.,#]/g," ").split(/\s+/).filter(Boolean);
    const csQ = words.some(w => CSW.test(w));
    words = words.filter(w => !CSW.test(w));
    const list = LISTINGS.filter(h =>
      (!state || h.state === state) &&
      (!city || h.city === city) &&
      (statusPick !== "pending" || isPending(h)) &&
      (statusPick !== "available" || !isPending(h)) &&
      (!bedsVal || (Number(h.beds)||0) >= bedsVal) &&
      (!bathsVal || (Number(h.baths)||0) >= bathsVal) &&
      rng(Number(h.monthlyPayment)||0, payLo, payHi) &&
      rng(Number(h.lockedPrice)||0, prLo, prHi) &&
      (!downLo || (Number(h.moveIn)||0) >= downLo) &&
      (!downHi || (Number(h.moveIn)||0) <= downHi) &&
      (csQ ? !!h.contractor : (words.length || type === "all" || (type === "contractor" ? !!h.contractor : !h.contractor))) &&
      (!words.length || (hay => words.every(w => hay.includes(w)))(((h.address||"")+" "+(h.city||"")+" "+(h.state||"")+" "+(h.zip||"")).toLowerCase().replace(/[.,#]/g," ")))
    );
    const num = (v, fallback=0) => Number(v) || fallback;
    if (sort === "monthly-asc")   list.sort((a,b) => num(a.monthlyPayment,Infinity) - num(b.monthlyPayment,Infinity));
    else if (sort === "down-asc") list.sort((a,b) => num(a.moveIn,Infinity) - num(b.moveIn,Infinity));  // "Pregúntenos" ($0) sorts last
    else if (sort === "price-asc")list.sort((a,b) => num(a.lockedPrice,Infinity) - num(b.lockedPrice,Infinity));
    else list.sort(defaultOrder());  // Destacadas (every home is): near the visitor first, then newest listed first
    return window.HomesMap ? HomesMap.applyGeo(list) : list;
  }

  const DOWN_STEPS = [1000,1500,2000,2500,3000,4000,5000];
  const PAY_STEPS = [500,600,700,800,900,1000,1100,1200,1300,1400,1500,1600,1700,1800];
  let zipTable = null, zipPromise = null, zipFailed = false;
  function normPlace(s){ return String(s||"").toLowerCase().replace(/\./g,"").replace(/\s+/g," ").trim(); }
  function findPlace(q){
    const raw = String(q||"").trim();
    if (/^\d{5}$/.test(raw)) return {kind:"zip", zip:raw};
    const n = normPlace(raw);
    if (!n || n.length < 3) return null;
    const seen = new Map();
    LISTINGS.forEach(h => {
      if (!h.city) return;
      const key = normPlace(h.city) + "|" + (h.state||"");
      if (!seen.has(key)) seen.set(key, {city:h.city, state:h.state});
    });
    const hits = [...seen.values()].filter(c => normPlace(c.city)===n || normPlace(c.city+", "+c.state)===n || normPlace(c.city+" "+c.state)===n);
    return hits.length ? {kind:"city", hits} : null;
  }
  function milesBetween(a, b){
    const R = 3958.7613;
    const p1 = a.lat * Math.PI/180, p2 = b.lat * Math.PI/180;
    const dphi = (b.lat - a.lat) * Math.PI/180, dl = (b.lng - a.lng) * Math.PI/180;
    const x = Math.sin(dphi/2)**2 + Math.cos(p1)*Math.cos(p2)*Math.sin(dl/2)**2;
    return 2 * R * Math.asin(Math.min(1, Math.sqrt(x)));
  }
  function pointOf(h){
    const lat = Number(h.lat), lng = Number(h.lng);
    return (lat && lng) ? {lat, lng} : null;
  }
  function centroid(list){
    const pts = list.map(pointOf).filter(Boolean);
    if (!pts.length) return null;
    return {lat: pts.reduce((s,p)=>s+p.lat,0)/pts.length, lng: pts.reduce((s,p)=>s+p.lng,0)/pts.length};
  }
  function loadZips(){
    if (zipTable || zipFailed || zipPromise) return;
    zipPromise = fetch("data/zip-centroids.json").then(r => r.json()).then(d => {
      zipTable = d.zips || {};
      render(false);
    }).catch(() => { zipFailed = true; });
  }
  function otherFilters(h){
    const state = $("fState").value, city = $("fCity").value;
    const statusPick = ($("fStatus") && $("fStatus").value) || "";
    const bedsVal = Number($("fBeds").value)||0, bathsVal = Number($("fBaths").value)||0;
    const type = hasCS ? $("fType").value : "all";
    const payLo = Number($("fPayMin").value)||0, prLo = Number($("fPriceMin").value)||0, prHi = Number($("fPriceMax").value)||0;
    const downLo = Number($("fDownMin").value)||0;
    if (state && h.state !== state) return false;
    if (city && h.city !== city) return false;
    if (statusPick === "pending" && !isPending(h)) return false;
    if (statusPick === "available" && isPending(h)) return false;
    if (bedsVal && (Number(h.beds)||0) < bedsVal) return false;
    if (bathsVal && (Number(h.baths)||0) < bathsVal) return false;
    const pay = Number(h.monthlyPayment)||0, price = Number(h.lockedPrice)||0, down = Number(h.moveIn)||0;
    if (payLo && pay < payLo) return false;
    if ((prLo && price < prLo) || (prHi && price > prHi)) return false;
    if (downLo && down < downLo) return false;
    if (type === "contractor" && !h.contractor) return false;
    if (type !== "all" && type !== "contractor" && h.contractor) return false;
    return true;
  }
  function fitsBudget(h){
    const downHi = Number($("fDown").value)||0, payHi = Number($("fPayMax").value)||0;
    return (!downHi || (Number(h.moveIn)||0) <= downHi) && (!payHi || (Number(h.monthlyPayment)||0) <= payHi);
  }
  function oneStep(value, cap, steps){
    if (!cap || value <= cap) return false;
    const next = steps.find(s => s > cap);
    return !!next && value <= next;
  }
  function justOver(h){
    if (isPending(h)) return false;
    const downHi = Number($("fDown").value)||0, payHi = Number($("fPayMax").value)||0;
    const down = Number(h.moveIn)||0, pay = Number(h.monthlyPayment)||0;
    const dOver = !!(downHi && down > downHi);
    const pOver = !!(payHi && pay > payHi);
    if (dOver === pOver) return false;
    if (dOver && !oneStep(down, downHi, DOWN_STEPS)) return false;
    if (pOver && !oneStep(pay, payHi, PAY_STEPS)) return false;
    return true;
  }
  function inPlace(h, place, origin){
    if (place.kind === "city") return place.hits.some(c => h.city === c.city && h.state === c.state);
    const zip = String(h.zip||"").replace(/\D/g,"").slice(0,5);
    if (zip && zip === place.zip) return true;
    if (zip) return false;
    const p = pointOf(h);
    return !!(origin && p && milesBetween(origin, p) <= 10);
  }
  function groupedHTML(place){
    let origin = null;
    if (place.kind === "zip"){
      if (!zipTable) loadZips();
      const row = zipTable && zipTable[place.zip];
      if (row) origin = {lat: row[0], lng: row[1]};
    }
    const pool = LISTINGS.filter(otherFilters);
    const here = pool.filter(h => inPlace(h, place, origin));
    if (!origin) origin = centroid(here);
    const match = here.filter(fitsBudget);
    const available = match.filter(h => !isPending(h)).sort(defaultOrder());
    const pending = match.filter(isPending).sort(defaultOrder());
    const parts = [];
    const paint = (list, opts) => list.map((h,i) => cardHTML(h, Object.assign({eager: i===0}, opts||{}))).join("");
    if (match.length) parts.push(available.concat(pending).map((h,i) => cardHTML(h, {eager: i===0})).join(""));
    if (available.length < 3 && origin){
      const near = pool.filter(h => !isPending(h) && fitsBudget(h) && !inPlace(h, place, origin)).map(h => {
        const p = pointOf(h);
        return p ? {h, d: milesBetween(origin, p)} : null;
      }).filter(x => x && x.d <= 50).sort((a,b) => a.d - b.d);
      if (near.length){
        parts.push(`<h2 class="result-group">Casas cercanas dentro de su presupuesto</h2>`);
        parts.push(near.map((x,i) => cardHTML(x.h, {away: Math.round(x.d), eager: !match.length && i===0})).join(""));
      }
    }
    const over = here.filter(h => justOver(h)).sort(defaultOrder());
    if (over.length){
      parts.push(`<h2 class="result-group">Un poco arriba de su presupuesto</h2>`);
      parts.push(paint(over));
    }
    return {html: parts.join(""), count: match.length + (parts.length ? 0 : 0), any: parts.length > 0, shown: available.length + pending.length};
  }

  function render(scroll){
    const place = findPlace($("fQ").value);
    if (place){
      const grouped = groupedHTML(place);
      $("cards").innerHTML = grouped.html;
      $("empty").style.display = grouped.any ? "none" : "block";
      const bits = grouped.html ? (grouped.html.match(/data-hid=/g)||[]).length : 0;
      $("count").textContent = bits ? `${bits} casa${bits===1?"":"s"}` : "";
      $("pager").style.display = "none";
      $("pager").innerHTML = "";
      if (window.HomesMap) HomesMap.update([]);
      if (window.HomesCart) HomesCart.sync();
      chips();
      const head = document.querySelector("body.page-search .topbar");
      if (head) document.documentElement.style.setProperty("--zhead", (head.offsetHeight + 8) + "px");
      if (scroll) document.getElementById("listings").scrollIntoView({block:"start", behavior:"smooth"});
      return;
    }
    const shown = filtered();
    const pages = Math.max(1, Math.ceil(shown.length / PER_PAGE));
    if (page > pages) page = 1;
    const slice = shown.slice((page-1)*PER_PAGE, page*PER_PAGE);
    $("cards").innerHTML = slice.map((h, i) => cardHTML(h, {eager: page===1 && i===0})).join("");
    $("empty").style.display = shown.length ? "none" : "block";
    const start = shown.length ? (page-1)*PER_PAGE+1 : 0;
    const end = Math.min(page*PER_PAGE, shown.length);
    $("count").textContent = shown.length
      ? `Mostrando ${start}–${end} de ${shown.length} casa${shown.length===1?"":"s"}`
      : "";
    renderPager(pages);
    if (window.HomesMap) HomesMap.update(shown);
    if (window.HomesCart) HomesCart.sync();
    chips();
    const head = document.querySelector("body.page-search .topbar");
    if (head) document.documentElement.style.setProperty("--zhead", (head.offsetHeight + 8) + "px");
    if (scroll) document.getElementById("listings").scrollIntoView({block:"start", behavior:"smooth"});
  }

  function renderPager(pages){
    const pager = $("pager");
    if (pages <= 1){ pager.style.display = "none"; pager.innerHTML = ""; return; }
    pager.style.display = "flex";
    const btn = (label, p, opts={}) =>
      `<button class="page-btn${opts.active?" active":""}" ${opts.disabled?"disabled":""} data-p="${p}"
        style="font-family:'DM Mono','DM Mono Fallback',ui-monospace,monospace;font-size:14px;min-width:44px;padding:12px 14px;border-radius:10px;cursor:${opts.disabled?"default":"pointer"};
        border:1px solid ${opts.active?"var(--pine,#15315e)":"var(--line,#dfe4ec)"};
        background:${opts.active?"var(--pine,#15315e)":"#fff"};color:${opts.active?"#fff":"var(--ink,#1c1b17)"};${opts.disabled?"opacity:.4":""}">${label}</button>`;
    let html = btn("‹ Anterior", page-1, {disabled: page===1});
    // compact page numbers: show a window around current page
    const nums = new Set([1, pages, page, page-1, page+1]);
    let last = 0;
    for (let p=1; p<=pages; p++){
      if (!nums.has(p)) continue;
      if (p - last > 1) html += `<span style="color:var(--ink-soft,#8892a0);padding:0 2px">…</span>`;
      html += btn(String(p), p, {active: p===page});
      last = p;
    }
    html += btn("Siguiente ›", page+1, {disabled: page===pages});
    pager.innerHTML = html;
    pager.querySelectorAll("button[data-p]").forEach(b =>
      b.addEventListener("click", () => { const p = Number(b.dataset.p); if (p>=1 && p<=pages){ page = p; render(true); } }));
  }

  // ── enlaces de búsqueda para compartir ────────────────────────────────
  // filtros ⇄ query string, para poder enviar una búsqueda (p. ej. Flint, MI)
  // como un enlace que abre ya filtrado.
  const URL_KEYS = { fState:"state", fCity:"city", fBeds:"beds", fBaths:"baths", fPayMin:"payMin", fPayMax:"payMax", fPriceMin:"priceMin", fPriceMax:"priceMax", fDownMin:"downMin", fDown:"down", fType:"type", fStatus:"status", fSort:"sort", fQ:"q" };
  const FILTER_IDS = ["fCity","fBeds","fBaths","fPayMin","fPayMax","fPriceMin","fPriceMax","fDownMin","fDown","fType","fStatus","fSort","fQ"];
  function applyURL(){
    const p = new URLSearchParams(location.search);
    if (p.get("state")) $("fState").value = p.get("state");
    fillCities();                                  // las ciudades dependen del estado elegido
    const legacy = (k) => { const m = (p.get(k)||"").match(/^(min|max):(\d+)$/); return m ? m : null; };
    const lp = legacy("pay"), ld = legacy("down");
    if (lp && !p.get("payMin") && !p.get("payMax")) p.set(lp[1]==="max"?"payMax":"payMin", lp[2]);
    if (ld && ld[1]==="max" && !/^\d+$/.test(p.get("down")||"")) p.set("down", ld[2]);
    FILTER_IDS.forEach(id => {
      const v = p.get(URL_KEYS[id]);
      if (v != null){ $(id).value = v; if ($(id).value !== v) $(id).value = ""; }  // ignorar valores desconocidos
    });
  }
  function syncURL(){
    const p = new URLSearchParams();
    Object.entries(URL_KEYS).forEach(([id,key]) => { const v = $(id).value; if (v) p.set(key, v); });
    if (window.HomesMap) HomesMap.toURL(p);
    const qs = p.toString();
    history.replaceState(null, "", qs ? "?" + qs : location.pathname);
  }

  ["fState",...FILTER_IDS].forEach(id => $(id).addEventListener("change", () => {
    if (id === "fState") fillCities();
    if (id === "fCity" && $("fCity").value && window.VisitorNear) VisitorNear.rememberCity(HOMES, $("fCity").value, $("fState").value);
    page = 1; render(true); syncURL(); chips();
  }));

  (function(){
    const q = $("fQ"), dl = $("qHints"); let t;
    q.addEventListener("input", () => { clearTimeout(t); t = setTimeout(() => { page = 1; render(false); syncURL(); chips(); }, 160); });
    q.addEventListener("keydown", e => { if (e.key === "Enter"){ q.blur(); render(true); } });
    const cities = [...new Set(LISTINGS.map(h => h.city + ", " + h.state))].sort();
    dl.innerHTML = cities.map(c => `<option value="${c}">`).join("");
  })();

  // swipeable / arrow photo browsing on cards (cover first, then up to 5 more photos)
  (function(){
    const box = $("cards"); if(!box) return;
    const byId = id => LISTINGS.find(h => h.id === id);
    const pics = h => {
      const meta = (window.PHOTO_INDEX || {})[h.id] || {};
      const cover = meta.real ? (h.heroPhoto || `images/${h.id}.jpg`) : "";
      return [cover, ...(h.photos||[])].filter((p, i, all) => p && all.indexOf(p) === i).slice(0, 6);
    };
    // same picture as the cover (re-saved copies differ in bytes): compare 16x16 grayscale thumbnails
    const thumbCache = {};
    function thumb(src){ return thumbCache[src] || (thumbCache[src] = new Promise(res => { const im = new Image(); im.onload = () => { try{ const c = document.createElement("canvas"); c.width = c.height = 16; const x = c.getContext("2d"); x.drawImage(im,0,0,16,16); res(x.getImageData(0,0,16,16).data); }catch(e){ res(null); } }; im.onerror = () => res(null); im.src = src; })); }
    const dups = new Set(), primed = new Set();
    function isCoverDup(img, card, src){ return dups.has(card.dataset.hid + "|" + src); }
    function prime(card){   // on first touch/hover, find photos that repeat the cover so the arrows skip them
      const h = byId(card.dataset.hid); if(!h || primed.has(h.id)) return; primed.add(h.id);
      const list = pics(h); if(list.length < 2) return;
      thumb(list[0]).then(c0 => { if(!c0) return; list.slice(1).forEach(s => thumb(s).then(c => {
        if(!c) return; let d = 0; for(let k=0;k<c.length;k+=4) d += Math.abs(c[k]-c0[k]) + Math.abs(c[k+1]-c0[k+1]) + Math.abs(c[k+2]-c0[k+2]);
        if(d / 256 / 3 < 4) dups.add(h.id + "|" + s); })); });
    }
    ["mouseover","touchstart"].forEach(ev => box.addEventListener(ev, e => { const c = e.target.closest && e.target.closest(".card"); if(c) prime(c); }, {passive:true}));
    function go(card, d){
      const h = byId(card.dataset.hid); if(!h) return; const list = pics(h); if(list.length < 2) return;
      const img = card.querySelector(".card-face img");
      let i = ((Number(card.dataset.pi)||0) + d + list.length) % list.length;
      for(let s=0; s<list.length && i>0 && isCoverDup(img, card, list[i]); s++) i = (i + d + list.length) % list.length;   // skip a photo that is the cover again
      card.dataset.pi = i; img.removeAttribute("data-sv"); img.style.opacity = 1; img.src = list[i];
      card.querySelectorAll(".pdots i").forEach((x,k) => x.classList.toggle("on", k===i));
    }
    box.addEventListener("click", e => { const b = e.target.closest(".pg"); if(!b) return; e.preventDefault(); e.stopPropagation(); go(b.closest(".card"), b.classList.contains("nx") ? 1 : -1); }, true);
    let x0 = null, moved = false;
    box.addEventListener("touchstart", e => { if(e.target.closest(".card-face")){ x0 = e.touches[0].clientX; moved = false; e.target.closest(".card-face").classList.add("touch"); } }, {passive:true});
    box.addEventListener("touchend", e => { if(x0 == null) return; const d = e.changedTouches[0].clientX - x0; x0 = null;
      if(Math.abs(d) > 40){ moved = true; const c = e.target.closest(".card"); if(c) go(c, d < 0 ? 1 : -1); } }, {passive:true});
    box.addEventListener("click", e => { if(moved){ e.preventDefault(); e.stopPropagation(); moved = false; } }, true);
  })();

  // etiquetas de filtros activos (toque una para quitarla)
  function chips(){
    const m = n => "$" + Number(n).toLocaleString("en-US");
    const box = $("chips");
    if (!box) return;
    const bits = [];
    const addRange = (loId, hiId, unit) => {
      const lo = $(loId).value, hi = $(hiId).value;
      if (lo && hi) bits.push({ids:[loId, hiId], label:`${m(lo)}–${m(hi)}${unit}`});
      else if (lo) bits.push({ids:[loId], label:`${m(lo)}+${unit}`});
      else if (hi) bits.push({ids:[hiId], label:`Hasta ${m(hi)}${unit}`});
    };
    addRange("fPayMin", "fPayMax", "/mes");
    addRange("fDownMin", "fDown", " de enganche");
    addRange("fPriceMin", "fPriceMax", "");
    if ($("fBeds").value) bits.push({ids:["fBeds"], label: $("fBeds").value + "+ recámaras"});
    if ($("fBaths").value) bits.push({ids:["fBaths"], label: $("fBaths").value + "+ baños"});
    if ($("fState").value) bits.push({ids:["fState"], label: $("fState").value});
    if ($("fCity").value) bits.push({ids:["fCity"], label: $("fCity").value});
    if ($("fQ").value) bits.push({ids:["fQ"], label: $("fQ").value});
    if ($("fType").value === "contractor") bits.push({ids:["fType"], label: "Proyectos más grandes"});
    else if ($("fType").value === "all") bits.push({ids:["fType"], label: "Todas"});
    if ($("fStatus") && $("fStatus").value === "pending") bits.push({ids:["fStatus"], label: "Pendiente"});
    else if ($("fStatus") && $("fStatus").value === "available") bits.push({ids:["fStatus"], label: "Disponible"});
    if (window.HomesMap && HomesMap.active && HomesMap.active()) {
      const ns = HomesMap.nearState && HomesMap.nearState();
      bits.push({ids:["near"], label: ns ? ("Cerca de " + ns.label) : "Cerca de mí"});
    }
    box.innerHTML = bits.map((b,i) => `<button type="button" data-i="${i}">${b.label} <span aria-hidden="true">×</span></button>`).join("");
    box.querySelectorAll("button").forEach(btn => btn.onclick = () => {
      const b = bits[Number(btn.dataset.i)];
      if (b.ids[0] === "near") {
        const c = document.getElementById("hmClear");
        if (c) c.click();
      } else {
        b.ids.forEach(id => { $(id).value = ""; });
        if (b.ids.includes("fState")) fillCities();
      }
      page = 1; render(false); syncURL();
    });
    const count = bits.filter(b => b.ids[0] !== "fQ").length;
    const badge = $("fCount");
    if (badge) { badge.hidden = !count; badge.textContent = String(count); }
    const clr = $("clearFilters"); if (clr) clr.hidden = !bits.some(b => b.ids[0] !== "near");
  }

  // "Copiar enlace de estos resultados" — busca para un cliente, toca, pega en un mensaje
  (function(){
    const btn = $("copyLink"); if (!btn) return;
    btn.style.display = "inline-block";
    const label = btn.textContent;
    btn.addEventListener("click", async () => {
      syncURL();
      try { await navigator.clipboard.writeText(location.href); }
      catch(e){ const t=document.createElement("textarea"); t.value=location.href; document.body.appendChild(t); t.select(); document.execCommand("copy"); t.remove(); }
      btn.textContent = "✓ Enlace copiado — envíeselo a quien decide con usted";
      setTimeout(() => { btn.textContent = label; }, 2600);
    });
  })();

  applyURL();
  if (window.HomesMap) HomesMap.mount({ rerender: render, sync: syncURL });
  // escritorio: un mapa pequeño arriba de las casas. En el teléfono queda el botón Lista / Mapa.
  (function(){
    const wrap = $("hmWrap"), cards = $("cards");
    if (!wrap || !window.HomesMap) return;
    const split = document.createElement("div"); split.id = "split";
    const left = document.createElement("div"), right = document.createElement("div"); right.id = "splitMap";
    cards.parentNode.insertBefore(split, cards);
    const head = document.querySelector("#listings .listings-head");
    if (head) left.append(head);
    left.append(cards, $("pager"), $("empty")); right.append(wrap); split.append(left, right);
    if (matchMedia("(min-width:861px)").matches) {
      $("hmMap").click();
      setTimeout(() => { if (window.HomesMap && HomesMap.refit) HomesMap.refit(); }, 400);
    }
  })();
  chips();
  (function(){
    const near = $("nearMe");
    if (near) near.addEventListener("click", () => { if (window.HomesMap && HomesMap.locate) HomesMap.locate(); });
    const miles = $("fMiles");
    if (miles) miles.addEventListener("change", () => {
      const hm = $("hmMiles");
      if (hm) { hm.value = miles.value; hm.dispatchEvent(new Event("change")); }
    });
    const qForm = document.querySelector(".hdr-search");
    if (qForm) qForm.addEventListener("submit", (e) => { e.preventDefault(); page = 1; render(false); syncURL(); });
    const filterBtn = $("filterBtn"), sheet = $("filterSheet");
    if (filterBtn && sheet) filterBtn.addEventListener("click", () => {
      const open = sheet.hasAttribute("hidden");
      if (open) sheet.removeAttribute("hidden"); else sheet.setAttribute("hidden", "");
      filterBtn.setAttribute("aria-expanded", open ? "true" : "false");
    });
    const more = $("moreFilters");
    if (more && filterBtn) more.addEventListener("click", () => { filterBtn.click(); more.setAttribute("aria-expanded", filterBtn.getAttribute("aria-expanded")); });
    const clr = $("clearFilters");
    if (clr) clr.addEventListener("click", () => {
      ["fState",...FILTER_IDS].filter(id => id !== "fSort").forEach(id => { const el = $(id); if (el) el.value = ""; });
      fillCities(); page = 1; render(false); syncURL();
    });
    const mapToggle = document.getElementById("mapToggle");
    if (mapToggle) mapToggle.addEventListener("click", () => {
      const on = document.body.classList.toggle("show-map");
      const label = mapToggle.querySelector("span");
      if (label) label.textContent = on ? "Lista" : "Mapa";
      mapToggle.setAttribute("aria-pressed", on ? "true" : "false");
      const btn = $(on ? "hmMap" : "hmList");
      if (btn) btn.click();
    });
  })();
  applyURL();
  chips();
  // ── destacadas + vendidas recientemente (datos de homes.js) ─────────────
  function drawFeatured(){  // every home is featured: near the visitor first, then newest listed
    const feats = LISTINGS.filter(h => !isPending(h)).slice().sort(defaultOrder()).slice(0, 6);
    if (feats.length && !document.body.classList.contains("page-search")){
      $("featuredCards").innerHTML = feats.map(h => cardHTML(h, {featured:true})).join("");
      $("featuredSec").hidden = false;
    }
  }
  (function spotlight(){
    drawFeatured();
    const sold = (typeof RECENTLY_SOLD !== "undefined" && RECENTLY_SOLD) || [];
    if (sold.length){
      const mo = d => { const t = new Date(d + "T12:00:00"); return t.toLocaleDateString("es-US", {month:"long"}) + " " + t.getFullYear(); };
      $("soldStrip").innerHTML = sold.map(x =>
        `<div class="sold-card"><span class="ribbon">Vendida</span><div class="c">${x.city}, ${x.state}</div><div class="d">Vendida ${mo(x.soldOn)}</div></div>`).join("");
      $("soldSec").hidden = false;
    }
    if (window.HomesCart) HomesCart.sync();
  })();
  // The approximate location can arrive a moment after the page draws: reorder only while the visitor is still on
  // the first page of the default order, so nothing jumps under someone who is already browsing.
  if (window.VisitorNear) VisitorNear.onChange(() => {
    drawFeatured();
    if (page === 1 && !$("fSort").value) render(false);
    if (window.HomesCart) HomesCart.sync();
  });

  function revealHash(){
    const id = decodeURIComponent((location.hash || "").replace(/^#/, ""));
    if (!id) return;
    const el = document.getElementById(id);
    if (el) el.scrollIntoView({ block: "start" });
  }
  render();
  revealHash();
  if (window.HomesMap) HomesMap.fromURL(new URLSearchParams(location.search));

  // ¿llega desde un enlace de búsqueda compartido? deja claro que se aplicó el
  // filtro: renombra la sección y salta directo a los resultados (no al hero).
  (function(){
    const params = new URLSearchParams(location.search);
    if (![...params.keys()].some(k => k !== "view")) return;
    const sec = $("listings");
    sec.querySelectorAll(".reveal").forEach(el => el.classList.add("in"));
    sec.classList.add("in");
    const st = $("fState").value, ci = $("fCity").value;
    if (st || ci){
      const h = sec.querySelector(".sec-title");
      if (h) h.textContent = ci ? `Casas en ${ci}, ${st}` : `Casas en ${st}`;
    }
    if (!location.hash) requestAnimationFrame(() => sec.scrollIntoView({ block: "start" }));
  })();

  // scroll reveal (respects reduced-motion via CSS)
  if ("IntersectionObserver" in window){
    const io = new IntersectionObserver((entries)=>{
      entries.forEach(e=>{ if(e.isIntersecting){ e.target.classList.add("in"); io.unobserve(e.target);} });
    },{threshold:0, rootMargin:"0px 0px -10% 0px"});
    document.querySelectorAll(".reveal").forEach(el=>io.observe(el));
  } else {
    document.querySelectorAll(".reveal").forEach(el=>el.classList.add("in"));
  }
})();
