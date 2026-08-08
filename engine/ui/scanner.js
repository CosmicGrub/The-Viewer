/* THE VIEWER - scanner.js : global HAND-SCANNER (keyboard-wedge) support. Self-contained, ES5-safe.
   Handheld USB/Bluetooth barcode & QR scanners act as keyboards: they "type" the code very fast and
   send Enter. This listener watches for that fast-burst-then-Enter signature ANYWHERE in the app and,
   when you're not already typing in a field, routes the scanned NSN / NIIN / manufacturer part number
   straight to the federal-catalog lookup (/publog). A page may set window.onScan(code) to intercept a
   scan (e.g. the bin audit collects scans into a list instead of navigating). No deps, fully offline. */
(function(){
  "use strict";
  if(window.__scannerLoaded) return; window.__scannerLoaded=true;

  var BURST_MS=35;      // scanners emit keystrokes faster than a human can type (~<35ms apart)
  var MIN_LEN=4;        // ignore very short bursts
  var buf="", last=0, fastCount=0, total=0;

  function isTyping(){
    var el=document.activeElement; if(!el) return false;
    var t=(el.tagName||"").toUpperCase();
    return t==="INPUT"||t==="TEXTAREA"||t==="SELECT"||el.isContentEditable;
  }
  function looksNSN(s){ var d=s.replace(/[^0-9]/g,""); return d.length===13||d.length===9; }

  function route(code){
    code=code.replace(/[ -]/g,"").trim(); if(code.length<MIN_LEN) return;
    // a page can intercept scans (bin audit collects them into a list instead of navigating)
    if(typeof window.onScan==="function"){
      try{ if(window.onScan(code)!==false){ flash("Scanned: "+code); return; } }catch(e){}
    }
    // NSN/NIIN -> catalog record; otherwise treat as a manufacturer part number (reverse lookup)
    var url = looksNSN(code) ? ("/publog?nsn="+encodeURIComponent(code))
                             : ("/publog?pn="+encodeURIComponent(code));
    flash("Scanned: "+code);
    // fire-and-forget local usage beacon (offline, matches palette.js analytics)
    try{ window.fetch("/api/analytics_log",{method:"POST",headers:{"Content-Type":"application/json"},
      body:JSON.stringify({kind:"scan",key:code,doc:null})}); }catch(e){}
    setTimeout(function(){ window.location.href=url; }, 260);
  }

  document.addEventListener("keydown", function(e){
    // allow the user (and scanners aimed at a field) to type normally into inputs
    if(isTyping()) return;
    var now=(e.timeStamp||Date.now());
    if(e.key==="Enter"){
      // a scan = enough chars, mostly arriving in fast bursts
      if(buf.length>=MIN_LEN && fastCount >= Math.max(2, Math.floor(total*0.6))){
        var code=buf; buf=""; fastCount=0; total=0;
        e.preventDefault(); route(code);
      } else { buf=""; fastCount=0; total=0; }
      return;
    }
    if(e.key && e.key.length===1){
      var gap=now-last; last=now;
      if(gap>250){ buf=e.key; fastCount=0; total=1; }   // new burst
      else { buf+=e.key; total++; if(gap<=BURST_MS) fastCount++; }
      if(buf.length>240) buf=buf.slice(-240);
    }
  }, true);

  // tiny toast (uses shared window.toast if present, else a minimal inline one)
  function flash(msg){
    try{ if(typeof window.toast==="function"){ window.toast(msg); return; } }catch(e){}
    var el=document.getElementById("vw-scan-toast");
    if(!el){ el=document.createElement("div"); el.id="vw-scan-toast";
      el.style.cssText="position:fixed;left:50%;bottom:60px;transform:translateX(-50%);background:#123020;color:#7fd6a0;border:1px solid #1d9e75;border-radius:8px;padding:8px 16px;font:13px -apple-system,Segoe UI,Arial,sans-serif;z-index:10000;box-shadow:0 6px 24px rgba(0,0,0,.45)";
      (document.body||document.documentElement).appendChild(el); }
    el.textContent="> "+msg; el.style.opacity="1";
    clearTimeout(el._t); el._t=setTimeout(function(){ el.style.opacity="0"; }, 2200);
  }
  // expose for manual/testing use
  window.viewerScanRoute=route;
})();
