/* THE VIEWER - readaloud.js : hands-free help for the bay floor. Two native, OFFLINE browser features:
   (1) READ ALOUD - a floating button reads the page's main content with SpeechSynthesis, so a mechanic
       with greasy hands can listen to a procedure instead of reading it.
   (2) VOICE INPUT - if SpeechRecognition is available, a mic button on the search box dictates the query.
   Both degrade silently when the browser lacks the API. Self-contained, ES5-safe, no deps. */
(function(){
  "use strict";
  if(window.__readaloudLoaded) return; window.__readaloudLoaded=true;

  var synth = window.speechSynthesis || null;
  var speaking = false;

  function mainText(){
    // prefer the primary content container; fall back to the body
    var sel = ["#out", "#results", "#result", "#cur", "#list", "main", ".wrap"];
    for(var i=0;i<sel.length;i++){ var el=document.querySelector(sel[i]); if(el && (el.innerText||"").trim().length>40) return el.innerText; }
    return (document.body ? document.body.innerText : "") || "";
  }
  function clean(t){ return (t||"").replace(/\s+/g," ").replace(/[→⇥◄⤷⬆]/g," ").trim().slice(0, 8000); }

  function speak(text){
    if(!synth){ toast("Read-aloud isn't supported in this browser."); return; }
    stop();
    var msg = clean(text || mainText());
    if(!msg){ toast("Nothing to read on this page."); return; }
    var u = new SpeechSynthesisUtterance(msg);
    u.rate = 0.98; u.pitch = 1.0;
    u.onend = function(){ speaking=false; paint(); };
    u.onerror = function(){ speaking=false; paint(); };
    synth.speak(u); speaking=true; paint();
  }
  function stop(){ try{ if(synth) synth.cancel(); }catch(e){} speaking=false; paint(); }
  window.viewerSpeak = speak; window.viewerStopSpeak = stop;

  function toast(m){ try{ if(typeof window.toast==="function"){ window.toast(m); return; } }catch(e){}
    var el=document.getElementById("vw-ra-toast");
    if(!el){ el=document.createElement("div"); el.id="vw-ra-toast";
      el.style.cssText="position:fixed;left:50%;bottom:60px;transform:translateX(-50%);background:#171d26;color:#e6e9ee;border:1px solid #2b333f;border-radius:8px;padding:8px 16px;font:13px Segoe UI,Arial,sans-serif;z-index:10000";
      (document.body||document.documentElement).appendChild(el); }
    el.textContent=m; el.style.opacity="1"; clearTimeout(el._t); el._t=setTimeout(function(){el.style.opacity="0";},2200);
  }

  // ---- floating read-aloud button ----
  function mountBtn(){
    if(!synth || document.getElementById("vw-read-btn")) return;
    var css="#vw-read-btn{position:fixed;bottom:12px;right:196px;z-index:9998;background:#171d26;color:#9aa6b6;border:1px solid #2b333f;border-radius:20px;padding:6px 12px;font:11px Segoe UI,Arial,sans-serif;cursor:pointer;opacity:.75;user-select:none;box-shadow:0 4px 14px rgba(0,0,0,.35)}#vw-read-btn:hover{opacity:1;color:#e6e9ee}#vw-read-btn.on{color:#7fd6a0;border-color:#1d9e75}@media print{#vw-read-btn{display:none}}";
    var st=document.createElement("style"); st.textContent=css; (document.head||document.documentElement).appendChild(st);
    var b=document.createElement("div"); b.id="vw-read-btn"; b.textContent="🔊 read"; b.title="Read this page aloud (offline)";
    b.setAttribute("role","button"); b.setAttribute("tabindex","0");
    b.onclick=function(){ if(speaking) stop(); else speak(); };
    b.onkeydown=function(e){ if(e.key==="Enter"||e.key===" "){ e.preventDefault(); b.onclick(); } };
    (document.body||document.documentElement).appendChild(b);
  }
  function paint(){ var b=document.getElementById("vw-read-btn"); if(b){ b.className=speaking?"on":""; b.textContent=speaking?"⏹ stop":"🔊 read"; } }
  window.addEventListener("beforeunload", stop);

  // ---- voice input on the search box (best-effort; some browsers need a network for recognition) ----
  function mountMic(){
    var SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    var q = document.getElementById("q");
    if(!SR || !q || document.getElementById("vw-mic-btn")) return;
    var mic=document.createElement("button"); mic.id="vw-mic-btn"; mic.type="button"; mic.textContent="🎤";
    mic.title="Dictate your search"; mic.setAttribute("aria-label","Dictate your search");
    mic.style.cssText="margin-left:6px;background:#1b2735;color:#cfe;border:1px solid #2f4858;border-radius:8px;padding:8px 11px;cursor:pointer;font-size:15px";
    var rec=null, on=false;
    mic.onclick=function(){
      if(on && rec){ try{ rec.stop(); }catch(e){} return; }
      try{ rec=new SR(); }catch(e){ toast("Voice input unavailable."); return; }
      rec.lang="en-US"; rec.interimResults=false; rec.maxAlternatives=1;
      rec.onresult=function(ev){ var txt=(ev.results[0][0].transcript||"").trim(); if(txt){ q.value=txt;
        var evk=new KeyboardEvent("keydown",{key:"Enter"}); q.dispatchEvent(evk);
        if(typeof window.runSearch==="function") window.runSearch(txt,false); } };
      rec.onstart=function(){ on=true; mic.style.color="#7fd6a0"; };
      rec.onend=function(){ on=false; mic.style.color="#cfe"; };
      rec.onerror=function(){ on=false; mic.style.color="#cfe"; toast("Didn't catch that."); };
      try{ rec.start(); }catch(e){ toast("Voice input needs microphone permission."); }
    };
    if(q.parentNode) q.parentNode.insertBefore(mic, q.nextSibling);
  }

  function init(){ mountBtn(); mountMic(); }
  if(document.body) init(); else document.addEventListener("DOMContentLoaded", init);
})();
