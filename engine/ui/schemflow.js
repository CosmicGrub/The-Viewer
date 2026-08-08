/* THE VIEWER -- schemflow.js : the "Living Schematic" flow overlay. For a VECTOR schematic page it pulls the
   inferred connectivity graph (netlist) from /api/schemgraph and renders an SVG over the page image where the
   wires ANIMATE in the direction of flow (dashes travel power -> load), clicking a wire ISOLATES its whole net,
   and clicking a component fires a breakdown callback. Dependency-free, ES5-safe so legacy runs it too.
   Tiers (RPS):  modern = requestAnimationFrame dash flow;  lite = SMIL <animate> dash flow (browser-driven);
                 legacy = no loop -- static highlight + a STEP button that advances the flow one hop at a time.
   Use:  SchemFlow.open(stageEl, doc, page, {tier:'modern', onInfo:fn, onComponent:fn});
         SchemFlow.close(stageEl); */
(function(){
  var WIRE="#2f4858", FLOW="#39d0ff", HOT="#ffd24a", DIM=0.12, NODE="#5cf2c4", COMP="#ff7a59", PWR="#ffd24a";
  var PWRRE=/^[+-]?\d{1,3}V$|^B\+$|^PWR$|^VCC$|^VBATT$/, GNDRE=/^GND$|^GROUND$/;
  var raf=null, smil=false, state=null;

  function xget(url, cb){ var x=new XMLHttpRequest(); x.open('GET',url,true);
    x.onreadystatechange=function(){ if(x.readyState===4){ try{ cb(x.status>=200&&x.status<300?JSON.parse(x.responseText):null); }catch(e){ cb(null); } } }; x.send(); }
  function xpost(url, body, cb){ var x=new XMLHttpRequest(); x.open('POST',url,true); x.setRequestHeader('Content-Type','application/json');
    x.onreadystatechange=function(){ if(x.readyState===4){ try{ cb(x.status>=200&&x.status<300?JSON.parse(x.responseText):null); }catch(e){ cb(null); } } }; x.send(JSON.stringify(body||{})); }

  // orient edges so flow runs OUTWARD from power/ground sources (BFS); fall back to highest-degree node.
  function orient(g){
    var N=g.nodes.length, adj=[], i;
    for(i=0;i<N;i++) adj.push([]);
    for(i=0;i<g.edges.length;i++){ var e=g.edges[i]; adj[e.a].push([i,e.b]); adj[e.b].push([i,e.a]); }
    // candidate sources: nodes nearest to a power/ground label
    var seeds=[], used={};
    function nearest(px,py){ var bi=-1,bd=1e9; for(var k=0;k<N;k++){ var dx=g.nodes[k].x-px, dy=g.nodes[k].y-py, d=dx*dx+dy*dy; if(d<bd){bd=d;bi=k;} } return bi; }
    for(i=0;i<g.comps.length;i++){ var c=g.comps[i]; if(PWRRE.test(c.ref)||GNDRE.test(c.ref)){ var ni=nearest(c.x,c.y); if(ni>=0&&!used[ni]){ used[ni]=1; seeds.push(ni); } } }
    if(!seeds.length){ var bi=0; for(i=1;i<N;i++) if(g.nodes[i].d>g.nodes[bi].d) bi=i; if(N) seeds.push(bi); }
    var order=new Array(N), o=0, q=seeds.slice(), seen={}; for(i=0;i<seeds.length;i++) seen[seeds[i]]=1;
    while(q.length){ var u=q.shift(); order[u]=o++; for(i=0;i<adj[u].length;i++){ var pr=adj[u][i], ei=pr[0], v=pr[1]; if(!seen[v]){ seen[v]=1; q.push(v); } } }
    for(i=0;i<N;i++) if(order[i]===undefined) order[i]=o++;   // unreached
    var dir=[];   // for each edge: [sx,sy,ex,ey] oriented start->end (flow direction)
    for(i=0;i<g.edges.length;i++){ var e2=g.edges[i];
      if(order[e2.a]<=order[e2.b]) dir.push([e2.x1,e2.y1,e2.x2,e2.y2,e2.a,e2.b]);
      else dir.push([e2.x2,e2.y2,e2.x1,e2.y1,e2.b,e2.a]); }
    return dir;
  }

  function netOfEdge(g){ var m={}; for(var n=0;n<g.nets.length;n++){ for(var j=0;j<g.nets[n].length;j++) m[g.nets[n][j]]=n; } return m; }

  function build(stage, g, doc, page, opts){
    var W=g.w||1000, H=g.h||773, dir=orient(g), e2net=netOfEdge(g), i;
    var tier=opts.tier||'modern';
    var svg=['<svg id="sfsvg" viewBox="0 0 '+W+' '+H+'" preserveAspectRatio="xMidYMid meet" style="width:100%;height:100%;background:#fff">'];
    svg.push('<image href="/page?doc='+doc+'&page='+page+'&dpi=150" x="0" y="0" width="'+W+'" height="'+H+'" preserveAspectRatio="none" opacity="0.92"/>');
    svg.push('<g id="sfwires">');
    var dash=Math.max(8, Math.round(W*0.012));   // dash period in page px
    for(i=0;i<dir.length;i++){ var d=dir[i], net=e2net[i]||0;
      var x1=d[0]*W,y1=d[1]*H,x2=d[2]*W,y2=d[3]*H;
      svg.push('<line x1="'+x1+'" y1="'+y1+'" x2="'+x2+'" y2="'+y2+'" stroke="'+WIRE+'" stroke-width="6" stroke-opacity="0.55" data-i="'+i+'" data-net="'+net+'" class="sfbase"/>');
      var flow='<line x1="'+x1+'" y1="'+y1+'" x2="'+x2+'" y2="'+y2+'" stroke="'+FLOW+'" stroke-width="3" stroke-linecap="round" stroke-dasharray="'+(dash*0.55)+' '+(dash*0.45)+'" data-i="'+i+'" data-net="'+net+'" class="sfflow"';
      if(tier==='lite'){ flow+=' stroke-dashoffset="0"><animate attributeName="stroke-dashoffset" from="0" to="-'+dash+'" dur="0.9s" repeatCount="indefinite"/></line>'; }
      else { flow+=' stroke-dashoffset="0"/>'; }
      svg.push(flow);
    }
    svg.push('</g>');
    // junction dots (degree>=3)
    svg.push('<g id="sfnodes">');
    for(i=0;i<g.nodes.length;i++){ var nd=g.nodes[i]; if(nd.d>=3) svg.push('<circle cx="'+nd.x*W+'" cy="'+nd.y*H+'" r="5" fill="'+NODE+'" stroke="#06281f" stroke-width="1"/>'); }
    svg.push('</g>');
    // component markers (clickable)
    svg.push('<g id="sfcomps">');
    for(i=0;i<g.comps.length;i++){ var c=g.comps[i], pw=PWRRE.test(c.ref)||GNDRE.test(c.ref), col=pw?PWR:COMP;
      svg.push('<g class="sfcomp" data-ref="'+c.ref+'" style="cursor:pointer">'+
        '<circle cx="'+c.x*W+'" cy="'+c.y*H+'" r="11" fill="'+col+'" fill-opacity="0.18" stroke="'+col+'" stroke-width="2"/>'+
        '<text x="'+c.x*W+'" y="'+(c.y*H+4)+'" text-anchor="middle" font-size="12" font-weight="700" fill="'+col+'">'+c.ref+'</text></g>'); }
    svg.push('</g></svg>');
    stage.innerHTML=svg.join('');
    var node=stage.querySelector('#sfsvg');
    var flows=node.querySelectorAll('.sfflow'), bases=node.querySelectorAll('.sfbase');
    var curNet=-1;

    function setNetOpacity(){
      var k;
      for(k=0;k<flows.length;k++){ var nn=+flows[k].getAttribute('data-net'), on=(curNet<0||nn===curNet);
        flows[k].setAttribute('stroke', on?(curNet<0?FLOW:HOT):FLOW);
        flows[k].setAttribute('stroke-opacity', on?'1':String(DIM)); }
      for(k=0;k<bases.length;k++){ var nb=+bases[k].getAttribute('data-net');
        bases[k].setAttribute('stroke-opacity', (curNet<0||nb===curNet)?'0.55':String(DIM)); }
    }
    function clickNet(ev){ ev.stopPropagation(); var nn=+this.getAttribute('data-net'); curNet=(curNet===nn?-1:nn); setNetOpacity();
      if(opts.onInfo) opts.onInfo({net:curNet, size:curNet<0?0:(g.nets[curNet]||[]).length}); }
    for(i=0;i<bases.length;i++){ bases[i].style.cursor='pointer'; bases[i].addEventListener('click', clickNet); }
    node.addEventListener('click', function(){ if(curNet>=0){ curNet=-1; setNetOpacity(); if(opts.onInfo) opts.onInfo({net:-1,size:0}); } });
    var comps=node.querySelectorAll('.sfcomp');
    for(i=0;i<comps.length;i++){ (function(cc){ cc.addEventListener('click', function(ev){ ev.stopPropagation();
      if(opts.onComponent) opts.onComponent({ref:cc.getAttribute('data-ref'), doc:doc, page:page}); }); })(comps[i]); }
    // wheel zoom (shared with highlighter behaviour)
    var vb={x:0,y:0,w:W,h:H};
    node.addEventListener('wheel', function(e){ e.preventDefault(); var f=e.deltaY<0?0.85:1.18;
      var nw=Math.min(W, Math.max(W*0.15, vb.w*f)), nh=nw*(H/W);
      vb.x=Math.max(0,Math.min(W-nw, vb.x+(vb.w-nw)/2)); vb.y=Math.max(0,Math.min(H-nh, vb.y+(vb.h-nh)/2)); vb.w=nw; vb.h=nh;
      node.setAttribute('viewBox', vb.x+' '+vb.y+' '+vb.w+' '+vb.h); }, {passive:false});

    // ---- animation per tier ----
    state={tier:tier, flows:flows, off:0, dash:dash, raf:null, stepFrontier:null, g:g, dir:dir, W:W, H:H, node:node, e2net:e2net, setNet:function(n){curNet=n;setNetOpacity();}};
    if(tier==='modern'){
      function loop(){ state.off=(state.off-0.9); for(var k=0;k<flows.length;k++) flows[k].setAttribute('stroke-dashoffset', state.off); state.raf=requestAnimationFrame(loop); }
      state.raf=requestAnimationFrame(loop);
    } else if(tier==='legacy'){
      // build per-net adjacency for hop stepping; render a STEP control
      buildStep(stage, g, dir, flows, e2net);
    }
    setNetOpacity();
    buildReview(stage, g, doc, page, node, W, H);
    return {dir:dir.length, nets:g.nets.length, comps:g.comps.length, conf:g.confidence};
  }

  // REVIEW/OVERRIDE (step 2): flag a page good/bad and drop component refs the vectorizer missed
  // (CAD sheets outline their label text -> schemgraph finds wires but 0 comps). Posts to the append-only sidecar.
  function buildReview(stage, g, doc, page, node, W, H){
    var bar=document.createElement('div');
    bar.style.cssText='position:absolute;right:8px;bottom:8px;display:flex;gap:6px;z-index:6;align-items:center';
    var badge=(g.review&&g.review.verdict)?('<span style="font-size:11px;color:#7fdca0;background:rgba(18,53,31,.7);border:1px solid #2f6d47;border-radius:6px;padding:2px 7px">reviewed: '+g.review.verdict+'</span>'):'';
    bar.innerHTML=badge+'<button id="sfrev" style="background:#1b2735;color:#cfe;border:1px solid #2f4858;border-radius:6px;padding:5px 10px;cursor:pointer;font-size:12px">⚑ Correct</button>';
    if(stage.style.position!=='relative'&&stage.style.position!=='absolute') stage.style.position='relative';
    stage.appendChild(bar);
    var added=[], placing=false, panel=null;
    function norm(evt){ try{ var pt=node.createSVGPoint(); pt.x=evt.clientX; pt.y=evt.clientY; var p=pt.matrixTransform(node.getScreenCTM().inverse()); return [p.x/W, p.y/H]; }
      catch(e){ var r=node.getBoundingClientRect(); return [(evt.clientX-r.left)/r.width, (evt.clientY-r.top)/r.height]; } }
    function refresh(){ var el=document.getElementById('sfrevlist'); if(el) el.innerHTML=added.length?added.map(function(a){return a.ref;}).join(', '):'(click the diagram to add missed refs)'; }
    function openPanel(){ if(panel) return;
      panel=document.createElement('div');
      panel.style.cssText='position:absolute;right:8px;bottom:44px;width:214px;background:#10151c;border:1px solid #2f4858;border-radius:8px;padding:10px;z-index:7;font-size:12px;color:#cfe';
      panel.innerHTML='<div style="margin-bottom:6px;color:#9aa6b6">Click the diagram to drop a component the vectorizer missed, then save a verdict.</div>'+
        '<div id="sfrevlist" style="max-height:70px;overflow:auto;margin-bottom:7px;color:#9fb">(click the diagram to add missed refs)</div>'+
        '<div style="display:flex;gap:4px">'+
        '<button data-v="good" class="sfrv" style="flex:1;background:#12351f;color:#7fdca0;border:1px solid #2f6d47;border-radius:6px;padding:5px;cursor:pointer">✓ good</button>'+
        '<button data-v="bad" class="sfrv" style="flex:1;background:#3a1717;color:#ff9a94;border:1px solid #6d2f2f;border-radius:6px;padding:5px;cursor:pointer">✕ bad</button>'+
        '<button data-v="corrected" class="sfrv" style="flex:1.4;background:#2b2140;color:#c9b6ff;border:1px solid #4a3a7a;border-radius:6px;padding:5px;cursor:pointer">save refs</button></div>'+
        '<div id="sfrevmsg" style="margin-top:6px;color:#8a98a8"></div>';
      stage.appendChild(panel);
      var vb=panel.querySelectorAll('.sfrv'); for(var i=0;i<vb.length;i++){ (function(b){ b.onclick=function(ev){ ev.stopPropagation(); save(b.getAttribute('data-v')); }; })(vb[i]); }
    }
    function save(verdict){ var msg=document.getElementById('sfrevmsg'); if(msg) msg.textContent='saving…';
      xpost('/api/schemgraph_review_decision', {doc:doc, page:page, verdict:verdict, labels:added}, function(r){
        if(msg) msg.textContent=(r&&r.ok)?('saved: '+verdict):('failed'+(r&&r.error?': '+r.error:'')); }); }
    node.addEventListener('click', function(evt){ if(!placing) return; evt.stopPropagation();
      var nc=norm(evt), ref=window.prompt('Component ref at this point (e.g. R12, K3):',''); if(!ref) return;
      added.push({ref:String(ref).trim().slice(0,16), x:Math.max(0,Math.min(1,nc[0])), y:Math.max(0,Math.min(1,nc[1]))}); refresh(); });
    document.getElementById('sfrev').onclick=function(e){ e.stopPropagation(); placing=!placing;
      this.style.background=placing?'#4f9dff':'#1b2735'; this.style.color=placing?'#08111d':'#cfe'; if(placing) openPanel(); };
  }

  // LEGACY: no rAF. A STEP button lights wires one BFS hop at a time from the source side.
  function buildStep(stage, g, dir, flows, e2net){
    var bar=document.createElement('div');
    bar.style.cssText='position:absolute;left:8px;bottom:8px;display:flex;gap:6px;z-index:5';
    bar.innerHTML='<button id="sfstep" style="background:#1b2735;color:#cfe;border:1px solid #2f4858;border-radius:6px;padding:5px 12px;cursor:pointer;font-size:12px">▸ STEP flow</button>'+
                  '<button id="sfreset" style="background:#1b2735;color:#9aa6b6;border:1px solid #2f4858;border-radius:6px;padding:5px 10px;cursor:pointer;font-size:12px">reset</button>';
    if(stage.style.position!=='relative'&&stage.style.position!=='absolute') stage.style.position='relative';
    stage.appendChild(bar);
    // start frontier = edges whose start node is a source (order 0): approximate as edges touched least; use endpoint nodes with high degree
    var lit={}, frontierNodes={}; // node id -> reached
    // seed: the "start" endpoint of the first edge of each net
    var seededNet={}, n;
    for(n=0;n<dir.length;n++){ var nt=e2net[n]||0; if(!seededNet[nt]){ seededNet[nt]=1; frontierNodes[dir[n][4]]=1; } }
    function paint(){ for(var k=0;k<flows.length;k++){ flows[k].setAttribute('stroke', lit[k]?HOT:FLOW); flows[k].setAttribute('stroke-opacity', lit[k]?'1':'0.18'); flows[k].setAttribute('stroke-dashoffset','0'); } }
    function step(){ var advanced=false, next={};
      for(var k=0;k<dir.length;k++){ if(lit[k]) continue; var s=dir[k][4]; if(frontierNodes[s]){ lit[k]=1; next[dir[k][5]]=1; advanced=true; } }
      for(var nn in next) frontierNodes[nn]=1; paint(); return advanced; }
    function reset(){ lit={}; frontierNodes={}; for(var m=0;m<dir.length;m++){ var t=e2net[m]||0; if(seededNet[t]&&!_seen(t)){ } }
      seededNet={}; for(m=0;m<dir.length;m++){ var t2=e2net[m]||0; if(!seededNet[t2]){ seededNet[t2]=1; frontierNodes[dir[m][4]]=1; } } paint(); }
    function _seen(){ return false; }
    bar.querySelector('#sfstep').addEventListener('click', function(e){ e.stopPropagation(); if(!step()) this.textContent='▸ (end of flow)'; else this.textContent='▸ STEP flow'; });
    bar.querySelector('#sfreset').addEventListener('click', function(e){ e.stopPropagation(); reset(); bar.querySelector('#sfstep').textContent='▸ STEP flow'; });
    paint();
  }

  function open(stage, doc, page, opts){
    opts=opts||{}; close(stage);
    stage.innerHTML='<div style="color:#9aa6b6;padding:20px">tracing the schematic…</div>';
    xget('/api/schemgraph?doc='+encodeURIComponent(doc)+'&page='+encodeURIComponent(page), function(g){
      if(!g){ stage.innerHTML='<div style="color:#9aa6b6;padding:20px">could not load graph.</div>'; return; }
      if(g.error || !g.has_vector || !(g.edges&&g.edges.length)){
        stage.innerHTML='<div style="color:#9aa6b6;padding:24px;text-align:center;max-width:440px;margin:auto">'+
          'No vector wiring to trace on this sheet'+(g.has_vector?' (too few segments)':' — it is a scanned image')+'.<br>'+
          'Use the <b>callout chips</b> below to jump to parts.</div>';
        if(opts.onInfo) opts.onInfo({mode:'none', confidence:g.confidence||0}); return; }
      var r=build(stage, g, doc, page, opts);
      if(opts.onInfo) opts.onInfo({mode:'flow', confidence:g.confidence, counts:g.counts, nets:r.nets, comps:r.comps});
    });
  }
  function close(stage){ if(state&&state.raf){ cancelAnimationFrame(state.raf); state.raf=null; } state=null; }

  window.SchemFlow = { open: open, close: close };
})();
