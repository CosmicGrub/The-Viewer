/* THE VIEWER -- rps.js : Retroactive Post-Support shim.
   (1) Small, feature-detected ES5 polyfills so the modern UI runs on older browsers (Win 7 / Vista,
       Firefox ESR, IE11). Each is a no-op where the feature already exists.
   (2) Boots the runtime mode from /api/rps and tones the UI down on lite/legacy machines:
       adds a body class (rps-modern|rps-lite|rps-legacy), disables animations/transitions off the
       modern path, and exposes window.RPS = {mode, flags, dpi} for pages to read.
   Pure client-side; loads fast; never blocks rendering. */
(function(){
  "use strict";
  // ---- 1. polyfills (no-ops if already present) ----
  if(!Object.assign){Object.assign=function(t){for(var i=1;i<arguments.length;i++){var s=arguments[i];if(s)for(var k in s)if(Object.prototype.hasOwnProperty.call(s,k))t[k]=s[k];}return t;};}
  if(!Array.from){Array.from=function(a){var o=[],i;for(i=0;i<a.length;i++)o.push(a[i]);return o;};}
  if(!Array.prototype.includes){Array.prototype.includes=function(v){return this.indexOf(v)>=0;};}
  if(!Array.prototype.find){Array.prototype.find=function(f){for(var i=0;i<this.length;i++)if(f(this[i],i,this))return this[i];};}
  if(!String.prototype.includes){String.prototype.includes=function(v){return this.indexOf(v)>=0;};}
  if(!String.prototype.startsWith){String.prototype.startsWith=function(v){return this.lastIndexOf(v,0)===0;};}
  if(typeof window.URLSearchParams==="undefined"){
    window.URLSearchParams=function(q){q=(q||"").replace(/^\?/,"");this._d={};var ps=q?q.split("&"):[];for(var i=0;i<ps.length;i++){var kv=ps[i].split("=");this._d[decodeURIComponent(kv[0])]=decodeURIComponent((kv[1]||"").replace(/\+/g," "));}};
    window.URLSearchParams.prototype.get=function(k){return (k in this._d)?this._d[k]:null;};
  }
  if(typeof window.Promise==="undefined"){          // compact Promise (A+ subset, enough for the app)
    var P=function(ex){var self=this;self._s=0;self._v=null;self._cb=[];
      function res(v){if(self._s)return;if(v&&typeof v.then==="function"){v.then(res,rej);return;}self._s=1;self._v=v;flush();}
      function rej(e){if(self._s)return;self._s=2;self._v=e;flush();}
      function flush(){setTimeout(function(){for(var i=0;i<self._cb.length;i++)self._cb[i]();self._cb=[];},0);}
      self.then=function(onF,onR){return new P(function(rs,rj){function h(){try{if(self._s===1)rs(onF?onF(self._v):self._v);else rj(onR?onR(self._v):self._v);}catch(e){rj(e);}}self._s?flush(self._cb.push(h)):self._cb.push(h);});};
      self["catch"]=function(onR){return self.then(null,onR);};
      try{ex(res,rej);}catch(e){rej(e);}};
    window.Promise=P;
  }
  if(typeof window.fetch==="undefined"){            // XHR-based fetch (GET/POST text+json)
    window.fetch=function(url,opt){opt=opt||{};return new Promise(function(res,rej){var x=new XMLHttpRequest();x.open(opt.method||"GET",url,true);
      if(opt.headers)for(var h in opt.headers)x.setRequestHeader(h,opt.headers[h]);
      x.onreadystatechange=function(){if(x.readyState===4){var body=x.responseText;res({ok:x.status>=200&&x.status<300,status:x.status,text:function(){return Promise.resolve(body);},json:function(){return Promise.resolve(JSON.parse(body||"null"));}});}};
      x.onerror=function(){rej(new Error("network error"));};x.send(opt.body||null);});};
  }

  // ---- 2. mode bootstrap ----
  var RPS={mode:"modern",flags:{},dpi:150};
  window.RPS=RPS;
  function applyMode(m,flags){
    RPS.mode=m||"modern"; RPS.flags=flags||{}; RPS.dpi=(flags&&flags.default_dpi)||150;
    var b=document.body||document.getElementsByTagName("body")[0]; if(!b)return;
    b.className=(b.className||"").replace(/\brps-(modern|lite|legacy)\b/g,"").replace(/\s+$/,"")+" rps-"+RPS.mode;
    if(RPS.mode!=="modern"){
      var st=document.getElementById("rps-lite-style");
      if(!st){st=document.createElement("style");st.id="rps-lite-style";
        st.textContent=".rps-lite *,.rps-legacy *{animation:none!important;transition:none!important;}"+
                       ".rps-lite .fade,.rps-legacy .fade{opacity:1!important;}";
        (document.head||document.getElementsByTagName("head")[0]).appendChild(st);}
    }
    if(typeof window.onRpsMode==="function"){try{window.onRpsMode(RPS);}catch(e){}}
  }
  RPS.MODES=["auto","modern","lite","legacy"];
  function savedOverride(){                       // ?mode= wins for the request; else the user's saved choice
    var qp=null; try{qp=new URLSearchParams(window.location.search).get("mode");}catch(e){}
    if(qp) return qp;
    try{var s=window.localStorage&&localStorage.getItem("rps.mode"); if(s&&s!=="auto") return s;}catch(e){}
    return null;
  }
  function boot(){
    var ov=savedOverride();
    try{
      window.fetch("/api/rps"+(ov?("?mode="+encodeURIComponent(ov)):"")).then(function(r){return r.json();}).then(function(d){
        applyMode(d&&d.mode,d&&d.flags); RPS.serverMode=d&&d.reason;
      })["catch"](function(){applyMode("modern",{default_dpi:150});});
    }catch(e){applyMode("modern",{default_dpi:150});}
  }
  RPS.getOverride=function(){try{return (window.localStorage&&localStorage.getItem("rps.mode"))||"auto";}catch(e){return "auto";}};
  RPS.setMode=function(m){                         // persist the user's choice and re-apply without a reload
    try{ if(window.localStorage){ if(!m||m==="auto") localStorage.removeItem("rps.mode"); else localStorage.setItem("rps.mode", m); } }catch(e){}
    boot();
  };
  if(document.body) boot(); else if(document.addEventListener) document.addEventListener("DOMContentLoaded",boot); else window.onload=boot;
  // load the global Ctrl+K command palette everywhere rps.js is present (once)
  try{ if(!window.__paletteLoaded){ var ps=document.createElement("script"); ps.src="/palette.js"; ps.async=true;
    (document.head||document.documentElement).appendChild(ps); } }catch(e){}
})();
