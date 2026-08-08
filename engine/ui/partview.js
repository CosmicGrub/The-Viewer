/* THE VIEWER — partview.js : embed a part's live parametric 3-D shape into any container.
   Self-contained ES5. Depends on window.PartGeo (partgeo.js) and optionally window.GL3D (gl3d.js).
   PartView.render(el, {name, chars, nsn, color, gl}) -> family. WebGL (auto-spin + drag/zoom) when available,
   else a depth-shaded SVG fallback (Win7/Vista / RPS safe). Mirrors threed.html's dims/build so it always matches. */
(function(){
  function num(ch, labels){
    ch=(ch||'').toUpperCase();
    for(var k=0;k<labels.length;k++){ var lab=labels[k], i=ch.indexOf(lab);
      if(i>=0){ var m=ch.slice(i+lab.length).match(/[-+]?\d*\.?\d+/); if(m){ var v=parseFloat(m[0]); if(v>0) return v; } } }
    return 0;
  }
  function dims(ch){
    var dia=num(ch,['OVERALL DIAMETER:','BODY DIAMETER:','OUTSIDE DIAMETER:','HEAD DIAMETER:','BASE DIAMETER:','THREAD DIAMETER:','DIAMETER:']);
    var bore=num(ch,['HOLE DIAMETER:','INSIDE DIAMETER:','BORE DIAMETER:']);
    var L=num(ch,['OVERALL LENGTH:','BODY LENGTH:','FASTENER LENGTH:','LENGTH:']);
    var W=num(ch,['OVERALL WIDTH:','BODY WIDTH:','WIDTH:'])||dia;
    var H=num(ch,['OVERALL HEIGHT:','BODY HEIGHT:','HEAD HEIGHT:','HEIGHT:','THICKNESS:'])||dia;
    if(dia){ W=dia; H=dia; if(!L) L=dia; }
    return {L:L||1, W:W||1, H:H||1, dia:dia, bore:bore};
  }
  // depth-shaded SVG projection (fixed three-quarter angle) — same look as the card thumbnails
  function svgMesh(geom, fill, w, h){
    var V=geom.V, F=geom.F, rx=-0.5, ry=0.6;
    var cy=Math.cos(ry), sy=Math.sin(ry), cx=Math.cos(rx), sx=Math.sin(rx), i;
    var P=[]; for(i=0;i<V.length;i++){ var x=V[i][0],y=V[i][1],z=V[i][2];
      var x1=x*cy+z*sy, z1=-x*sy+z*cy, y1=y*cx-z1*sx, z2=y*sx+z1*cx; P.push([x1,y1,z2]); }
    var xs=P.map(function(p){return p[0];}), ys=P.map(function(p){return p[1];});
    var minx=Math.min.apply(null,xs),maxx=Math.max.apply(null,xs),miny=Math.min.apply(null,ys),maxy=Math.max.apply(null,ys);
    var span=Math.max(maxx-minx,maxy-miny,.001), sc=Math.min(h*0.42,300)/span;
    var cX=w/2,cY=h/2,mx=(minx+maxx)/2,my=(miny+maxy)/2;
    function sp(p){ return [cX+(p[0]-mx)*sc, cY+(p[1]-my)*sc]; }
    var fa=F.map(function(f){ var zc=0; f.forEach(function(idx){ zc+=P[idx][2]; }); return {f:f,z:zc/f.length}; })
            .sort(function(a,b){ return a.z-b.z; });
    var zmin=fa.length?fa[0].z:0, zmax=fa.length?fa[fa.length-1].z:1, zr=(zmax-zmin)||1;
    var s='<svg width="100%" height="100%" viewBox="0 0 '+w+' '+h+'">';
    fa.forEach(function(o){ var pts=o.f.map(function(idx){ var q=sp(P[idx]); return q[0].toFixed(1)+','+q[1].toFixed(1); }).join(' ');
      var op=(0.5+0.45*((o.z-zmin)/zr)).toFixed(2);
      s+='<polygon points="'+pts+'" fill="'+fill+'" fill-opacity="'+op+'" stroke="#0a0e12" stroke-width="0.6" stroke-linejoin="round"/>'; });
    return s+'</svg>';
  }
  function dispose(el){ try{ if(el&&el._gl&&el._gl.spin) el._gl.spin(false); }catch(e){} if(el) el._gl=null; }
  function render(el, part){
    if(!el) return 'box';
    dispose(el); el.innerHTML='';
    if(!window.PartGeo){ el.innerHTML='<div style="color:#9aa6b6;font-size:12px;padding:10px">3-D engine not loaded.</div>'; return 'box'; }
    var fam = PartGeo.classify ? PartGeo.classify(part.name||'', part.chars||'', part.nsn||'')
                               : PartGeo.family(part.name||'', part.chars||'');
    var g; try{ g=PartGeo.build(fam, dims(part.chars||'')); }catch(e){ g=PartGeo.build('box',{}); }
    var color=part.color||'#9aa0a6', mat=(part.gl&&part.gl.length===3)?part.gl:[0.6,40,0.4];
    var W=el.clientWidth||280, H=el.clientHeight||220;
    var v=null;
    try{ if(window.GL3D && GL3D.supported()){
      var canvas=document.createElement('canvas'); canvas.style.cssText='width:100%;height:100%;display:block;border-radius:8px;background:#0a0e12';
      canvas.width=W; canvas.height=H; el.appendChild(canvas); v=GL3D.create(canvas);
    } }catch(e){ v=null; }
    if(v){ try{ v.load(g, color, g.smooth!==false, mat); el._gl=v; }catch(e){ el.innerHTML=svgMesh(g,color,W,H); } }
    else { el.innerHTML=svgMesh(g, color, W, H); }
    return fam;
  }
  window.PartView = { render:render, dims:dims, num:num, dispose:dispose };
})();
