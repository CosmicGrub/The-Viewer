/* THE VIEWER — tagger.js : background, inline part tagging. A small pencil icon marks a part as tag-able;
   clicking opens a tiny popover to add/remove your own words (tags) for THAT part. Tags feed the offline
   search expansion (a tag you put on a part also finds it). Dependency-free, ES5-safe (works on legacy).
   Use:  el.appendChild( Tagger.button({nsn:'<the NSN>', name:'<the name>'}) );
   (v0.96.0: the doc example avoids literal dot-dot-dot so the RPS lint's spread/rest scan stays clean.) */
(function(){
  var pop = null, outsideBound = false;
  function esc(s){ s=(s==null?'':String(s)); return s.replace(/[&<>"]/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]; }); }
  function xget(url,cb){ var x=new XMLHttpRequest(); x.open('GET',url,true);
    x.onreadystatechange=function(){ if(x.readyState===4){ try{ cb(x.status>=200&&x.status<300?JSON.parse(x.responseText):null); }catch(e){ cb(null); } } }; x.send(); }
  function xpost(url,body,cb){ var x=new XMLHttpRequest(); x.open('POST',url,true); x.setRequestHeader('Content-Type','application/json');
    x.onreadystatechange=function(){ if(x.readyState===4){ try{ cb(x.status>=200&&x.status<300?JSON.parse(x.responseText):null); }catch(e){ cb(null); } } }; x.send(JSON.stringify(body)); }
  function close(){ if(pop&&pop.parentNode){ pop.parentNode.removeChild(pop); } pop=null;
    if(outsideBound){ document.removeEventListener('mousedown',outside); outsideBound=false; } }
  function outside(e){ if(pop && !pop.contains(e.target)) close(); }
  function chips(box, part, tags){
    box.innerHTML='';
    if(!tags || !tags.length){ box.innerHTML='<span style="font-size:11px;color:#6b7280">no tags yet</span>'; return; }
    for(var i=0;i<tags.length;i++){ (function(tg){
      var s=document.createElement('span'); s.title='remove';
      s.style.cssText='font-size:11px;border:1px solid rgba(79,157,255,.35);background:rgba(79,157,255,.12);color:#cfe0ff;border-radius:9px;padding:1px 7px;cursor:pointer';
      s.innerHTML=esc(tg)+' &times;';
      s.onclick=function(){ xpost('/api/tags',{action:'delete',nsn:part.nsn||'',name:part.name||'',tag:tg},function(r){ if(r&&r.ok) chips(box,part,r.tags); }); };
      box.appendChild(s); })(tags[i]); }
  }
  function openPop(anchor, part){
    close();
    pop=document.createElement('div');
    pop.style.cssText='position:absolute;z-index:140;min-width:248px;max-width:300px;background:#171d26;border:1px solid #2b333f;border-radius:10px;padding:11px;box-shadow:0 12px 34px rgba(0,0,0,.55);font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;color:#e6e9ee';
    var r=anchor.getBoundingClientRect();
    var sx=window.pageXOffset||document.documentElement.scrollLeft, sy=window.pageYOffset||document.documentElement.scrollTop;
    pop.style.left=Math.max(8, sx+r.left-210)+'px'; pop.style.top=(sy+r.bottom+6)+'px';
    pop.innerHTML='<div style="font-size:12px;color:#9aa6b6;margin-bottom:7px">Tag this part'+(part.nsn?(' &middot; <b style="color:#caa24a">'+esc(part.nsn)+'</b>'):(part.name?(' &middot; '+esc(part.name)):''))+'</div>'+
      '<div id="tgchips" style="display:flex;flex-wrap:wrap;gap:5px;margin-bottom:8px"></div>'+
      '<div style="display:flex;gap:6px"><input id="tginp" placeholder="add your word / slang / tag" style="flex:1;background:#1c2430;color:#e6e9ee;border:1px solid #2b333f;border-radius:7px;padding:6px 9px;font-size:13px"><button id="tgadd" style="background:#4f9dff;border:none;color:#08111d;border-radius:7px;padding:0 11px;cursor:pointer;font-weight:600">Add</button></div>'+
      '<div style="margin-top:7px;font-size:11px;color:#6b7280">A tag also finds this part in search. <a href="/keywords" style="color:#9aa6b6">manage all</a></div>';
    document.body.appendChild(pop);
    var box=pop.querySelector('#tgchips'), inp=pop.querySelector('#tginp');
    xget('/api/tags?nsn='+encodeURIComponent(part.nsn||'')+'&name='+encodeURIComponent(part.name||''), function(j){ chips(box, part, j&&j.tags); });
    function add(){ var v=inp.value.replace(/^\s+|\s+$/g,''); if(!v) return; inp.value='';
      xpost('/api/tags',{action:'save',nsn:part.nsn||'',name:part.name||'',tag:v},function(r){ if(r&&r.ok) chips(box,part,r.tags); }); }
    pop.querySelector('#tgadd').onclick=add;
    inp.addEventListener('keydown',function(e){ if(e.key==='Enter'||e.keyCode===13){ e.preventDefault(); add(); } });
    inp.focus();
    setTimeout(function(){ document.addEventListener('mousedown',outside); outsideBound=true; },0);
  }
  function button(part){
    var b=document.createElement('button'); b.title='Tag this part'; b.setAttribute('aria-label','Tag this part');
    b.innerHTML='&#9998;';   // pencil
    b.style.cssText='border:none;background:transparent;color:#9aa6b6;cursor:pointer;font-size:14px;opacity:.5;padding:2px 6px;border-radius:6px;line-height:1';
    b.onmouseover=function(){ b.style.opacity='1'; b.style.color='#caa24a'; };
    b.onmouseout=function(){ b.style.opacity='.5'; b.style.color='#9aa6b6'; };
    b.onclick=function(ev){ ev.stopPropagation(); ev.preventDefault(); openPop(b, part||{}); };
    return b;
  }
  window.Tagger = { button: button, open: openPop };
})();
