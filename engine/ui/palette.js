/* THE VIEWER — palette.js : a global Ctrl+K command palette. Self-contained, ES5-safe (runs on legacy
   browsers via the rps.js polyfills). Injects its own overlay + styles; jumps to any feature, or looks up
   a part/vehicle via /api/suggest. Include with <script src="/palette.js"></script>. */
(function(){
  "use strict";
  if(window.__paletteLoaded) return; window.__paletteLoaded=true;

  // ---- Kiosk / glove mode (bay-floor tablet): body.kiosk-mode class, persisted, applied app-wide. ----
  // Applied as early as possible so pages don't flash the normal-size layout first.
  function applyKiosk(on){ try{ var b=document.body||document.documentElement;
      if(on) b.classList.add("kiosk-mode"); else b.classList.remove("kiosk-mode"); }catch(e){} }
  function kioskOn(){ try{ return window.localStorage.getItem("viewer_kiosk")==="1"; }catch(e){ return false; } }
  function toggleKiosk(){ var on=!kioskOn(); try{ window.localStorage.setItem("viewer_kiosk", on?"1":"0"); }catch(e){}
      applyKiosk(on); if(typeof window.toast==="function") window.toast(on?"Kiosk mode ON — big touch targets":"Kiosk mode off"); return on; }
  window.viewerToggleKiosk=toggleKiosk;
  // Review finding: cadview.js/deepzoom.js/threed.html each independently reimplemented this exact
  // read (one inconsistently). Export it so they can share one implementation instead. Guarded so
  // whichever of shared.js/palette.js happens to load first on a given page wins -- most pages load
  // both, but circuitlab.html/scan.html load only palette.js, so this can't only live in shared.js.
  if(window.viewerKioskOn===undefined) window.viewerKioskOn=kioskOn;
  (function(){ var apply=function(){ applyKiosk(kioskOn()); };
    if(document.body) apply(); else document.addEventListener("DOMContentLoaded",apply); })();

  var COMMANDS=[
    {ic:"🔎",label:"Search the manuals",hint:"home",url:"/"},
    {ic:"💬",label:"Ask a question (cited)",hint:"offline Q&A over the manuals",url:"/ask"},
    {ic:"🛠",label:"Solve it (symptom → fix)",hint:"workflow hub",url:"/solve"},
    {ic:"🌳",label:"Guided troubleshooting",hint:"symptom → checks → corrective action (fault tree)",url:"/troubleshoot"},
    {ic:"🔧",label:"How to do it (procedure)",hint:"steps · tools · cautions",url:"/procedure"},
    {ic:"🎞",label:"Visual steps",hint:"follow-along flow",url:"/stepflow"},
    {ic:"🖨",label:"Job packet",hint:"printable take-to-the-bay sheet",url:"/packet"},
    {ic:"📋",label:"Part dossier",hint:"everything about one part",url:"/dossier"},
    {ic:"🧾",label:"Work Order",hint:"procedures + torque + parts + figures",url:"/jobcard"},
    {ic:"🔄",label:"Shift handover",hint:"pending sign-offs + recent field notes, shop-wide",url:"/handover"},
    {ic:"🧭",label:"Find a part",hint:"every figure & page that calls it out",url:"/locate"},
    {ic:"🔩",label:"Torque quick-reference",hint:"cited values + ft-lb/in-lb/N·m converter",url:"/torque"},
    {ic:"🔣",label:"Decode a code (NSN/SMR/CAGE/MS)",hint:"paste any code off a page — says what it means",url:"/decode"},
    {ic:"📐",label:"Measurements & dimensions",hint:"every measured value for a part/vehicle, cited",url:"/measures"},
    {ic:"🗂",label:"Masterfile",hint:"consolidated dimensional data: authoritative + external",url:"/master"},
    {ic:"📑",label:"Masterfile coverage",hint:"dimension gaps by subject; spec-sheet PDFs",url:"/mastercov"},
    {ic:"🗄",label:"Federal catalog (PUBLOG)",hint:"authoritative NSN/part# · characteristics · CAGE",url:"/publog"},
    {ic:"📷",label:"Scan a part",hint:"hand scanner or camera → NSN/part# lookup",url:"/scan"},
    {ic:"🧩",label:"Exploded / assembly view",hint:"figure hotspots + step-through assembly order",url:"/exploded"},
    {ic:"📦",label:"Bin / shelf audit",hint:"scan NSNs → flag look-alikes & superseded",url:"/binaudit"},
    {ic:"🪪",label:"Part page (everything)",hint:"one authoritative pane + complete job-package PDF",url:"/part"},
    {ic:"📜",label:"Provenance audit",hint:"internal: external sources + Wayback links",url:"/audit"},
    {ic:"🪛",label:"Fastener reference",hint:"thread sizes: dia, TPI/pitch",url:"/fastener"},
    {ic:"🗓",label:"PMCS finder",hint:"maintenance-check tables by vehicle",url:"/pmcs"},
    {ic:"🛢",label:"Readiness (fluids · intervals)",hint:"fluids matrix + service intervals by vehicle",url:"/readiness"},
    {ic:"🧠",label:"Semantic search",hint:"search by meaning, not keywords",url:"/semantic"},
    {ic:"🔗",label:"Related parts & assemblies",hint:"what a part sits inside / ships with",url:"/related"},
    {ic:"🖼",label:"Visual part search",hint:"photo → closest figure crops",url:"/visual"},
    {ic:"🔍",label:"Look-Alike Parts",hint:"tell apart same-name parts",url:"/partdiff"},
    {ic:"📈",label:"Coverage",hint:"OCR · CAD · vectorized · netlists",url:"/coverage"},
    {ic:"⚡",label:"Circuit Lab",hint:"overlay editor + simulator",url:"/circuitlab"},
    {ic:"🧊",label:"3-D Library",hint:"representative 3-D parts",url:"/3d"},
    {ic:"🔌",label:"Schematics Library",hint:"wiring & schematic sheets",url:"/schematics"},
    {ic:"🏷",label:"Smart Collections",hint:"living groups that auto-fill from OCR",url:"/collections"},
    {ic:"🔖",label:"Keywords & synonyms",hint:"teach the search your slang, nicknames & abbreviations",url:"/keywords"},
    {ic:"🕸",label:"Knowledge graph",hint:"everything one hop from a part, figure, vehicle, procedure, or spec",url:"/kg"},
    {ic:"➕",label:"Add documents",hint:"scan, index & OCR new TMs / PDFs",url:"/ingest"},
    {ic:"📊",label:"Ops dashboard",hint:"health · cache · runs · audit",url:"/ops"},
    {ic:"🛰",label:"Command center",hint:"are-we-complete: OCR% · coverage · PUBLOG · gaps",url:"/command"},
    {ic:"✅",label:"Verification cockpit",hint:"proof state: tests · last verify · sidecars",url:"/verify"},
    {ic:"🖊",label:"Review & sign-off",hint:"SME approve low-confidence values (audit trail)",url:"/review"},
    {ic:"🔤",label:"OCR status",hint:"searchable progress",url:"/status"},
    {ic:"★",label:"My Bench",hint:"your pinned parts / pages",url:"/bench"},
    {ic:"🎓",label:"Learn / quiz mode",hint:"cited multiple-choice from the manuals",url:"/learn"},
    {ic:"❔",label:"Help & feature guide",hint:"what can this do?",url:"/help"},
    {ic:"🖥",label:"Toggle kiosk mode",hint:"big-touch · high-contrast for the bay floor",act:function(){toggleKiosk();}}
  ];

  var css=""
    + ".cmdk-ov{position:fixed;inset:0;background:rgba(6,10,16,.62);z-index:9999;display:none;align-items:flex-start;justify-content:center}"
    + ".cmdk-ov.on{display:flex}"
    + ".cmdk{width:560px;max-width:92vw;margin-top:11vh;background:#171d26;border:1px solid #2b333f;border-radius:14px;box-shadow:0 24px 60px rgba(0,0,0,.5);overflow:hidden;font:14px/1.5 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;color:#e6e9ee}"
    + ".cmdk input{width:100%;border:none;outline:none;background:transparent;color:#e6e9ee;font-size:16px;padding:15px 17px;border-bottom:1px solid #2b333f}"
    + ".cmdk-list{max-height:54vh;overflow:auto;padding:6px}"
    + ".cmdk-it{display:flex;align-items:center;gap:11px;padding:9px 12px;border-radius:9px;cursor:pointer}"
    + ".cmdk-it.sel,.cmdk-it:hover{background:#1c2430}"
    + ".cmdk-it .ic{width:20px;text-align:center}"
    + ".cmdk-it .lb{flex:1}.cmdk-it .lb small{color:#9aa6b6;margin-left:8px;font-size:12px}"
    + ".cmdk-it .kd{font-size:10px;color:#9aa6b6;border:1px solid #2b333f;border-radius:20px;padding:1px 7px}"
    + ".cmdk-sec{font-size:10px;letter-spacing:.6px;text-transform:uppercase;color:#9aa6b6;padding:8px 12px 3px;font-weight:700}"
    + ".cmdk-ft{border-top:1px solid #2b333f;padding:7px 14px;font-size:11px;color:#9aa6b6;display:flex;gap:14px}";
  var st=document.createElement("style"); st.textContent=css; (document.head||document.documentElement).appendChild(st);

  var ov=document.createElement("div"); ov.className="cmdk-ov";
  ov.innerHTML='<div class="cmdk" role="dialog" aria-modal="true" aria-label="Command palette">'
    + '<input id="cmdkq" placeholder="Jump to a feature, or look up a part / vehicle…" autocomplete="off" role="combobox" aria-expanded="true" aria-controls="cmdkl" aria-activedescendant="">'
    + '<div class="cmdk-list" id="cmdkl" role="listbox" aria-label="Commands and results"></div>'
    + '<div class="cmdk-ft"><span>↑↓ move</span><span>↵ open</span><span>esc close</span></div></div>';
  function add(){ (document.body||document.documentElement).appendChild(ov); }
  if(document.body) add(); else document.addEventListener("DOMContentLoaded",add);

  var items=[], sel=0, sugTimer=null, lastSug="";
  function esc(s){return (s==null?"":String(s)).replace(/[&<>"]/g,function(c){return {"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;"}[c];});}
  function go(url){ close(); window.location.href=url; }

  // ---- QoL: "Recent" — jump back to what you were just looking at (localStorage, ES5-safe) ----
  function getRecent(){ try{ return JSON.parse(window.localStorage.getItem("viewer_recent")||"[]"); }catch(e){ return []; } }
  function putRecent(list){ try{ window.localStorage.setItem("viewer_recent", JSON.stringify(list.slice(0,8))); }catch(e){} }
  function recordCurrent(){
    try{
      var path=location.pathname; if(path==="/"||path==="/index.html"||path==="") return;
      var q=""; try{ q=new URLSearchParams(location.search).get("q")||""; }catch(_){ var m=location.search.match(/[?&]q=([^&]*)/); q=m?decodeURIComponent(m[1].replace(/\+/g," ")):""; }
      var title=(document.title||path).replace(/\s*[—–-]\s*THE VIEWER.*$/i,"").trim()||path;
      var url=path+(q?("?q="+encodeURIComponent(q)):"");
      var list=getRecent().filter(function(r){ return r&&r.url!==url; });
      list.unshift({url:url,title:title,q:q,ts:(+new Date())}); putRecent(list);
      // fire-and-forget local usage beacon (offline, local-only analytics)
      try{
        var kind=(path.indexOf("/dossier")>=0||path.indexOf("/partdiff")>=0)?"part":(path.indexOf("/torque")>=0?"torque":(path.indexOf("/pmcs")>=0?"pmcs":"tool"));
        window.fetch("/api/analytics_log",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({kind:kind,key:(q||path),doc:null})});
      }catch(_){}
    }catch(e){}
  }
  function renderRecent(){
    var list=getRecent(); if(!list.length) return "";
    var sub=list.slice(0,5);
    sub.forEach(function(r){ items.push({ic:"🕘",label:r.title,hint:r.q?("“"+r.q+"”"):"",act:(function(u){return function(){go(u);};})(r.url)}); });
    return '<div class="cmdk-sec">Recent</div>'+rowsHtml(sub.map(function(r){return {ic:"🕘",label:r.title,hint:r.q?("“"+r.q+"”"):""};}),0);
  }
  // ---- QoL: "My Bench" — pin the current page for later ----
  function getBench(){ try{ return JSON.parse(window.localStorage.getItem("viewer_bench")||"[]"); }catch(e){ return []; } }
  function putBench(l){ try{ window.localStorage.setItem("viewer_bench", JSON.stringify(l.slice(0,100))); }catch(e){} }
  function pinCurrent(){
    try{
      var path=location.pathname; if(path==="/bench") return false;
      var q=""; try{ q=new URLSearchParams(location.search).get("q")||""; }catch(_){}
      var title=(document.title||path).replace(/\s*[—–-]\s*THE VIEWER.*$/i,"").trim()||path;
      var url=path+location.search;
      var l=getBench().filter(function(r){ return r&&r.url!==url; });
      l.unshift({url:url,title:title,q:q,ts:(+new Date())}); putBench(l); return true;
    }catch(e){ return false; }
  }

  function build(q){
    q=(q||"").trim(); var ql=q.toLowerCase(); items=[];
    var html="";
    if(!q){ html+=renderRecent(); }
    if(q){
      var qe=encodeURIComponent(q);
      items.push({ic:"🔎",label:"Search “"+q+"”",hint:"in the manuals",act:function(){go("/?q="+qe);}});
      items.push({ic:"📋",label:"Open dossier for “"+q+"”",hint:"aggregate part view",act:function(){go("/dossier?q="+qe);}});
      items.push({ic:"🧾",label:"Work Order for “"+q+"”",hint:"procedures + torque + parts",act:function(){go("/jobcard?q="+qe);}});
      items.push({ic:"🧭",label:"Locate “"+q+"”",hint:"every figure it appears on",act:function(){go("/locate?q="+qe);}});
      html+='<div class="cmdk-sec">Actions</div>';
      html+=rowsHtml(items,0);
    }
    var feats=COMMANDS.filter(function(c){ return !ql || c.label.toLowerCase().indexOf(ql)>=0 || c.hint.toLowerCase().indexOf(ql)>=0; });
    var base=items.length;
    feats.forEach(function(c){ items.push({ic:c.ic,label:c.label,hint:c.hint,act:c.act||(function(u){return function(){go(u);};})(c.url)}); });
    html+='<div class="cmdk-sec">Go to</div>'+rowsHtml(feats.map(function(c){return {ic:c.ic,label:c.label,hint:c.hint};}),base);
    document.getElementById("cmdkl").innerHTML=html+'<div id="cmdk-sug"></div>';
    sel=0; paint();
    if(q.length>=2) suggest(q);
  }
  function rowsHtml(arr,offset){
    var h=""; for(var i=0;i<arr.length;i++){ var it=arr[i];
      h+='<div class="cmdk-it" id="cmdk-opt-'+(offset+i)+'" data-i="'+(offset+i)+'" role="option" aria-selected="false"><span class="ic" aria-hidden="true">'+esc(it.ic)+'</span><span class="lb">'+esc(it.label)+(it.hint?' <small>'+esc(it.hint)+'</small>':'')+'</span></div>'; }
    return h;
  }
  function suggest(q){
    if(q===lastSug) return; clearTimeout(sugTimer);
    sugTimer=setTimeout(function(){ lastSug=q;
      window.fetch("/api/suggest?q="+encodeURIComponent(q)).then(function(r){return r.json();}).then(function(d){
        var sg=(d&&d.suggestions)||[]; if(!sg.length) return;
        var box=document.getElementById("cmdk-sug"); if(!box) return;
        var base=items.length; var h='<div class="cmdk-sec">Parts &amp; vehicles</div>';
        sg.forEach(function(s){ var ic=s.kind==="vehicle"?"🚛":s.kind==="part"?"🔩":"🔎";
          items.push({ic:ic,label:s.text,hint:s.kind,act:(function(t){return function(){go("/dossier?q="+encodeURIComponent(t));};})(s.text)});
        });
        h+=rowsHtml(sg.map(function(s){return {ic:s.kind==="vehicle"?"🚛":s.kind==="part"?"🔩":"🔎",label:s.text,hint:s.kind};}),base);
        box.innerHTML=h; paint();
      })["catch"](function(){});
    },120);
  }
  function paint(){ var els=document.getElementById("cmdkl").querySelectorAll(".cmdk-it");
    for(var i=0;i<els.length;i++){ els[i].className="cmdk-it"+(i===sel?" sel":"");
      els[i].setAttribute("aria-selected", i===sel?"true":"false");
      els[i].onmousedown=(function(idx){return function(e){e.preventDefault(); if(items[idx]&&items[idx].act) items[idx].act();};})(i);
      els[i].onmouseenter=(function(idx){return function(){sel=idx; var ee=document.getElementById("cmdkl").querySelectorAll(".cmdk-it"); for(var k=0;k<ee.length;k++){ee[k].className="cmdk-it"+(k===sel?" sel":"");ee[k].setAttribute("aria-selected",k===sel?"true":"false");} var qq=document.getElementById("cmdkq"); if(qq)qq.setAttribute("aria-activedescendant","cmdk-opt-"+sel);};})(i);
    }
    var q=document.getElementById("cmdkq"); if(q)q.setAttribute("aria-activedescendant", els.length?("cmdk-opt-"+sel):"");
  }
  function move(d){ if(!items.length)return; sel=(sel+d+items.length)%items.length; paint();
    var el=document.getElementById("cmdkl").querySelectorAll(".cmdk-it")[sel]; if(el&&el.scrollIntoView)el.scrollIntoView({block:"nearest"}); }
  var _prevFocus=null;
  function open(){ _prevFocus=document.activeElement; ov.className="cmdk-ov on"; var q=document.getElementById("cmdkq"); q.value=""; build(""); q.focus(); }
  function close(){ ov.className="cmdk-ov"; try{ if(_prevFocus&&_prevFocus.focus) _prevFocus.focus(); }catch(e){} }
  window.cmdkOpen=open;

  document.addEventListener("keydown",function(e){
    if((e.ctrlKey||e.metaKey)&&(e.key==="k"||e.key==="K")){ e.preventDefault(); ov.className.indexOf("on")>=0?close():open(); return; }
    if(ov.className.indexOf("on")<0) return;
    if(e.key==="Escape"){ e.preventDefault(); close(); }
    else if(e.key==="ArrowDown"){ e.preventDefault(); move(1); }
    else if(e.key==="ArrowUp"){ e.preventDefault(); move(-1); }
    else if(e.key==="Enter"){ e.preventDefault(); if(items[sel]&&items[sel].act) items[sel].act(); }
    else if(e.key==="Tab"){
      // minimal focus trap (aria-modal): while the palette is open, Tab cycles inside the dialog.
      var box=ov.querySelector(".cmdk"); if(!box) return;
      var cand=box.querySelectorAll('a[href],button,input,select,textarea,[tabindex]');
      var foc=[]; for(var fi=0; fi<cand.length; fi++){
        if(!cand[fi].disabled && cand[fi].getAttribute("tabindex")!=="-1") foc.push(cand[fi]);
      }
      if(!foc.length){ e.preventDefault(); return; }
      var first=foc[0], last=foc[foc.length-1], act=document.activeElement;
      if(e.shiftKey){ if(act===first || !box.contains(act)){ e.preventDefault(); last.focus(); } }
      else { if(act===last || !box.contains(act)){ e.preventDefault(); first.focus(); } }
    }
  });
  ov.addEventListener("mousedown",function(e){ if(e.target===ov) close(); });
  document.addEventListener("input",function(e){ if(e.target&&e.target.id==="cmdkq") build(e.target.value); });

  // Home ?q= deep-link: a /?q=<query> URL (from the palette or any tool) should prefill + run the search.
  try{
    var pq=null; try{ pq=new URLSearchParams(window.location.search).get("q"); }catch(_){ var m=window.location.search.match(/[?&]q=([^&]*)/); pq=m?decodeURIComponent(m[1].replace(/\+/g," ")):null; }
    if(pq && window.location.pathname==="/"){
      var run=function(){ var qb=document.getElementById("q"); if(qb){ qb.value=pq; } if(typeof window.runSearch==="function"){ window.runSearch(pq,true); } };
      if(document.readyState==="complete"||document.readyState==="interactive") setTimeout(run,80);
      else document.addEventListener("DOMContentLoaded",function(){ setTimeout(run,80); });
    }
  }catch(e){}

  // ---- QoL: record this page for the Recent list + a discoverability pill on every page ----
  if(document.readyState==="loading") document.addEventListener("DOMContentLoaded",recordCurrent); else recordCurrent();
  try{
    // Recommendations annex #9 (palette-discoverability): "⌘K jump" read as a keyboard-shortcut
    // reminder for an audience with no reason to know that convention, and was unusable on a touch
    // tablet with no physical keyboard anyway -- the ONLY entry point there was this pill, at
    // 11px/opacity .7, competing with the equally tiny bench-pill next to it, sized BELOW the
    // 44px touch target base.css's own kiosk-mode/pointer:coarse rules use everywhere else. Relabel
    // to a verb-first description of what it DOES, and size for touch unconditionally -- not gated
    // behind kiosk mode, which a first-touch tablet user has no way to have already discovered.
    var pcss="#cmdk-pill,#bench-pill{position:fixed;bottom:12px;z-index:9998;background:#171d26;color:#9aa6b6;border:1px solid #2b333f;border-radius:20px;padding:10px 16px;font:13px/1 -apple-system,Segoe UI,Arial,sans-serif;cursor:pointer;opacity:.85;user-select:none;box-shadow:0 4px 14px rgba(0,0,0,.35);min-height:44px;display:flex;align-items:center;box-sizing:border-box}#cmdk-pill{right:12px}#bench-pill{right:150px}#cmdk-pill:hover,#bench-pill:hover{opacity:1;color:#e6e9ee}@media print{#cmdk-pill,#bench-pill{display:none}}";
    var ps=document.createElement("style"); ps.textContent=pcss; (document.head||document.documentElement).appendChild(ps);
    var pill=document.createElement("div"); pill.id="cmdk-pill"; pill.textContent="🔍 Jump to anything"; pill.title="Search everything — any tool, part, or procedure (or press Ctrl/Cmd+K)";
    pill.setAttribute("role","button"); pill.setAttribute("tabindex","0"); pill.setAttribute("aria-label","Search everything — any tool, part, or procedure");
    pill.onclick=function(){ open(); };
    pill.onkeydown=function(e){ if(e.key==="Enter"||e.key===" "){ e.preventDefault(); open(); } };
    var bpill=null;
    if(location.pathname!=="/"&&location.pathname!=="/bench"){
      bpill=document.createElement("div"); bpill.id="bench-pill"; bpill.textContent="☆ pin"; bpill.title="Pin this page to My Bench";
      bpill.setAttribute("role","button"); bpill.setAttribute("tabindex","0"); bpill.setAttribute("aria-label","Pin this page to My Bench");
      var doPin=function(){ if(pinCurrent()){ bpill.textContent="★ pinned"; setTimeout(function(){ bpill.textContent="☆ pin"; },1400); } };
      bpill.onclick=doPin;
      bpill.onkeydown=function(e){ if(e.key==="Enter"||e.key===" "){ e.preventDefault(); doPin(); } };
    }
    function mountPill(){ var root=(document.body||document.documentElement); root.appendChild(pill); if(bpill) root.appendChild(bpill); }
    if(document.body) mountPill(); else document.addEventListener("DOMContentLoaded",mountPill);
  }catch(e){}

  // ---- app-wide hand-scanner (keyboard-wedge) support: load scanner.js once on every palette page ----
  try{
    if(!window.__scannerLoaded && !document.getElementById("vw-scanner-js")){
      var sc=document.createElement("script"); sc.id="vw-scanner-js"; sc.src="/scanner.js"; sc.async=true;
      (document.head||document.documentElement).appendChild(sc);
    }
  }catch(e){}

  // ---- app-wide read-aloud (offline TTS) + voice input: load readaloud.js once on every palette page ----
  try{
    if(!window.__readaloudLoaded && !document.getElementById("vw-readaloud-js")){
      var ra=document.createElement("script"); ra.id="vw-readaloud-js"; ra.src="/readaloud.js"; ra.async=true;
      (document.head||document.documentElement).appendChild(ra);
    }
  }catch(e){}
})();
