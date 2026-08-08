/* THE VIEWER -- schemhl.js : schematic Highlighter mode. When ON for a VECTOR schematic page, renders an
   interactive SVG (the page image + the page's real vector geometry from /api/schempaths) where hovering
   outlines an element and clicking highlights the whole CONNECTED group (a net/trace/symbol). Raster scans
   have no geometry -> it tells you to use the callout chips. Dependency-free, ES5-safe (legacy too).
   Use:  SchemHL.open(stageEl, doc, page, onInfo);  SchemHL.close(stageEl, restoreFn); */
(function(){
  var HL = "#ffd24a", HOV = "#4f9dff";
  function xget(url, cb){ var x=new XMLHttpRequest(); x.open('GET',url,true);
    x.onreadystatechange=function(){ if(x.readyState===4){ try{ cb(x.status>=200&&x.status<300?JSON.parse(x.responseText):null); }catch(e){ cb(null); } } }; x.send(); }
  function key(x,y){ return Math.round(x*500)+","+Math.round(y*500); }   // snap endpoints to a grid

  function build(stage, data, doc, page){
    var W=data.w||1000, H=data.h||773, paths=data.paths||[];
    // union-find over paths sharing a snapped endpoint -> connected groups
    var parent=[]; function find(a){ while(parent[a]!==a){ parent[a]=parent[parent[a]]; a=parent[a]; } return a; }
    function uni(a,b){ parent[find(a)]=find(b); }
    var i, ends=[];
    for(i=0;i<paths.length;i++){ parent[i]=i;
      var p=paths[i], e=[];
      if(p.t==='l'){ e=[[p.x1,p.y1],[p.x2,p.y2]]; }
      else if(p.t==='r'){ e=[[p.x,p.y],[p.x+p.w,p.y],[p.x,p.y+p.h],[p.x+p.w,p.y+p.h]]; }
      else if(p.t==='p'&&p.pts&&p.pts.length){ e=[p.pts[0],p.pts[p.pts.length-1]]; }
      ends.push(e);
    }
    var atKey={};
    for(i=0;i<ends.length;i++){ for(var k=0;k<ends[i].length;k++){ var kk=key(ends[i][k][0],ends[i][k][1]);
      if(atKey[kk]!==undefined) uni(i, atKey[kk]); else atKey[kk]=i; } }
    var grp=[]; for(i=0;i<paths.length;i++) grp[i]=find(i);

    var svg=['<svg id="hlsvg" viewBox="0 0 '+W+' '+H+'" preserveAspectRatio="xMidYMid meet" style="width:100%;height:100%;background:#fff">'];
    svg.push('<image href="/page?doc='+doc+'&page='+page+'&dpi=150" x="0" y="0" width="'+W+'" height="'+H+'" preserveAspectRatio="none"/>');
    function el(p){
      if(p.t==='l') return '<line x1="'+p.x1*W+'" y1="'+p.y1*H+'" x2="'+p.x2*W+'" y2="'+p.y2*H+'"/>';
      if(p.t==='r') return '<rect x="'+p.x*W+'" y="'+p.y*H+'" width="'+p.w*W+'" height="'+p.h*H+'" fill="none"/>';
      if(p.t==='p'&&p.pts){ var d=''; for(var j=0;j<p.pts.length;j++){ d+=(j?'L':'M')+(p.pts[j][0]*W)+' '+(p.pts[j][1]*H); } return '<path d="'+d+'" fill="none"/>'; }
      return '';
    }
    // transparent fat hit-targets (catch clicks/hover near thin lines) + thin visible stroke layer
    for(i=0;i<paths.length;i++){
      var g=grp[i], tag=el(paths[i]);
      if(!tag) continue;
      svg.push(tag.replace('<', '<').replace('/>', ' data-i="'+i+'" data-g="'+g+'" stroke="#000" stroke-opacity="0" stroke-width="9" fill="none" class="hit"/>'));
    }
    svg.push('</svg>');
    stage.innerHTML=svg.join('');
    var node=stage.querySelector('#hlsvg');
    var hits=node.querySelectorAll('.hit'), curG=-1;
    function paint(gsel, color, wid){ for(var q=0;q<hits.length;q++){ if(+hits[q].getAttribute('data-g')===gsel){ hits[q].setAttribute('stroke',color); hits[q].setAttribute('stroke-opacity','0.9'); hits[q].setAttribute('stroke-width',wid);} } }
    function clear(gsel){ for(var q=0;q<hits.length;q++){ if(+hits[q].getAttribute('data-g')===gsel && gsel!==curG){ hits[q].setAttribute('stroke-opacity','0'); } } }
    for(i=0;i<hits.length;i++){ (function(h){
      h.style.cursor='pointer';
      h.addEventListener('mouseover',function(){ var g=+h.getAttribute('data-g'); if(g!==curG){ paint(g,HOV,'5'); } });
      h.addEventListener('mouseout',function(){ var g=+h.getAttribute('data-g'); clear(g); });
      h.addEventListener('click',function(ev){ ev.stopPropagation(); var g=+h.getAttribute('data-g');
        if(curG>=0){ var pg=curG; curG=-1; clear(pg); }
        curG=g; paint(g,HL,'6'); });
    })(hits[i]); }
    node.addEventListener('click',function(){ if(curG>=0){ var g=curG; curG=-1; clear(g); } });  // bg click clears
    // wheel zoom via viewBox
    var vb={x:0,y:0,w:W,h:H};
    node.addEventListener('wheel',function(e){ e.preventDefault(); var f=e.deltaY<0?0.85:1.18;
      var nw=Math.min(W, Math.max(W*0.15, vb.w*f)), nh=nw*(H/W);
      vb.x=Math.max(0,Math.min(W-nw, vb.x+(vb.w-nw)/2)); vb.y=Math.max(0,Math.min(H-nh, vb.y+(vb.h-nh)/2)); vb.w=nw; vb.h=nh;
      node.setAttribute('viewBox', vb.x+' '+vb.y+' '+vb.w+' '+vb.h); },{passive:false});
    return paths.length;
  }

  function open(stage, doc, page, onInfo){
    if(!stage) return; stage.innerHTML='<div style="color:#9aa6b6;padding:20px">analysing schematic…</div>';
    xget('/api/schempaths?doc='+encodeURIComponent(doc)+'&page='+encodeURIComponent(page), function(d){
      if(!d){ stage.innerHTML='<div style="color:#9aa6b6;padding:20px">could not load.</div>'; return; }
      if(!d.has_vector){
        stage.innerHTML='<div style="color:#9aa6b6;padding:24px;text-align:center;max-width:420px;margin:auto">'+
          'This sheet is a scanned image — there is no vector geometry to click. '+
          'Use the <b>callout chips</b> below (part #/NSN/figure) to jump to parts.</div>';
        if(onInfo) onInfo({mode:'raster'}); return;
      }
      var n=build(stage, d, doc, page);
      if(onInfo) onInfo({mode:'vector', paths:n});
    });
  }
  window.SchemHL = { open: open };
})();
