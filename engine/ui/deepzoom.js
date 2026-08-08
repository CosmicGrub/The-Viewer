/* THE VIEWER -- deepzoom.js : OFFLINE deep-zoom for a TM page/figure (no OpenSeadragon, no CDN).
   Renders the page image to a canvas with smooth drag-pan + cursor-centred wheel-zoom, and upgrades the
   source render to a higher DPI as you zoom in (progressive resolution, on-demand via /page?dpi=N). Overlays
   OCR "callout" hotspots (/api/callouts): numbered markers you click to jump to the part (NSN/PN/figure).
   Dependency-free, ES5-safe. Use:  DeepZoom.mount(containerEl, doc, page, {onInfo:fn}); */
(function(){
  function el(tag, css, html){ var e=document.createElement(tag); if(css) e.style.cssText=css; if(html!=null) e.innerHTML=html; return e; }
  function xget(url, cb){ var x=new XMLHttpRequest(); x.open('GET',url,true);
    x.onreadystatechange=function(){ if(x.readyState===4){ try{ cb(x.status>=200&&x.status<300?JSON.parse(x.responseText):null); }catch(e){ cb(null); } } }; x.send(); }

  function mount(container, doc, page, opts){
    opts=opts||{}; if(!container||!doc){ return {destroy:function(){}}; }
    container.innerHTML=''; container.style.position='relative'; container.style.background='#0c1116'; container.style.overflow='hidden';
    var cv=el('canvas','display:block;width:100%;height:100%;cursor:grab;touch-action:none'); container.appendChild(cv);
    var ctx=cv.getContext('2d');
    var hot=el('div','position:absolute;inset:0;pointer-events:none'); container.appendChild(hot);   // hotspot layer
    var bar=el('div','position:absolute;left:8px;top:8px;display:flex;gap:4px;z-index:4');
    function mk(t,ti){ var b=el('button',null,t); b.title=ti||t; b.style.cssText='background:rgba(20,28,38,.85);color:#cfe;border:1px solid #2f4858;border-radius:6px;min-width:30px;height:26px;cursor:pointer;font-size:13px;padding:0 7px'; return b; }
    var bIn=mk('+','zoom in'), bOut=mk('−','zoom out'), bFit=mk('⌂','fit'), bHot=mk('⌖','toggle callouts'), bDpi=mk('','');
    bDpi.style.cursor='default'; bDpi.style.color='#8fb'; bDpi.textContent='150 dpi';
    bar.appendChild(bIn); bar.appendChild(bOut); bar.appendChild(bFit); bar.appendChild(bHot); bar.appendChild(bDpi); container.appendChild(bar);
    var load=el('div','position:absolute;inset:0;display:flex;align-items:center;justify-content:center;color:#8a98a8;font-size:13px','loading page…'); container.appendChild(load);

    var img=null, imgDpi=0, zoom=1, panX=0, panY=0, dead=false, showHot=true, callouts=[], hotOn=true;
    var DPIS=[150,300,600,1000];   // progressive ladder

    function pageUrl(dpi){ return '/page?doc='+encodeURIComponent(doc)+'&page='+encodeURIComponent(page)+'&dpi='+dpi+'&clean=1'; }
    function wantDpi(){ // pick the render dpi so on-screen pixels stay crisp for the current zoom
      var eff=zoom; for(var i=DPIS.length-1;i>=0;i--){ if(DPIS[i]<=150*Math.max(1,eff)) return DPIS[i]; } return DPIS[0]; }
    function fetchDpi(dpi){ if(dpi===imgDpi) return; var im=new Image();
      im.onload=function(){ if(dead) return; img=im; imgDpi=dpi; bDpi.textContent=dpi+' dpi'; try{container.removeChild(load);}catch(e){} draw(); };
      im.onerror=function(){ if(load) load.textContent='could not load page'; }; im.src=pageUrl(dpi); }

    function fit(){ var r=container.getBoundingClientRect(); var dpr=window.devicePixelRatio||1;
      cv.width=Math.max(1,Math.round(r.width*dpr)); cv.height=Math.max(1,Math.round(r.height*dpr)); cv.style.width=r.width+'px'; cv.style.height=r.height+'px'; draw(); }
    function baseScale(){ if(!img) return 1; return Math.min(cv.width/img.naturalWidth, cv.height/img.naturalHeight); }
    function drawGeom(){ var s=baseScale()*zoom; var dw=img.naturalWidth*s, dh=img.naturalHeight*s;
      var dx=(cv.width-dw)/2+panX, dy=(cv.height-dh)/2+panY; return {s:s,dw:dw,dh:dh,dx:dx,dy:dy}; }
    function draw(){ if(dead||!img) return; var W=cv.width,H=cv.height; ctx.clearRect(0,0,W,H);
      var g=drawGeom(); ctx.imageSmoothingEnabled=true; try{ctx.imageSmoothingQuality='high';}catch(e){}
      ctx.drawImage(img,0,0,img.naturalWidth,img.naturalHeight,g.dx,g.dy,g.dw,g.dh); placeHotspots(g); }

    function placeHotspots(g){ hot.innerHTML=''; if(!hotOn||!callouts.length) return;
      var dpr=window.devicePixelRatio||1;
      for(var i=0;i<callouts.length;i++){ var c=callouts[i]; if(!c.box) continue;
        var cx=(c.box[0]+c.box[2])/2, cy=(c.box[1]+c.box[3])/2;          // normalized 0..1 centre
        var px=(g.dx+cx*g.dw)/dpr, py=(g.dy+cy*g.dh)/dpr;
        if(px<-20||py<-20||px>cv.width/dpr+20||py>cv.height/dpr+20) continue;
        (function(cc,x,y){ var m=el('button',null,String(cc._n));
          m.title=cc.label||cc.text; m.style.cssText='position:absolute;transform:translate(-50%,-50%);left:'+x+'px;top:'+y+'px;pointer-events:auto;'+
            'background:rgba(79,157,255,.92);color:#08111d;border:2px solid #fff;border-radius:50%;width:22px;height:22px;font-size:11px;font-weight:700;cursor:pointer;z-index:5';
          m.onclick=function(ev){ ev.stopPropagation(); if(opts.onCallout){ opts.onCallout(cc); } else if(cc.url){ window.open(cc.url,'_blank'); } };
          hot.appendChild(m); })(c,px,py);
      }
    }

    function setZoom(z, cx, cy){ var nz=Math.max(1,Math.min(12, z));
      if(cx!=null&&img){ var g=drawGeom(); var ix=(cx-g.dx)/g.dw, iy=(cy-g.dy)/g.dh;   // image point under cursor
        zoom=nz; var g2=drawGeom(); panX+=(cx-(g2.dx+ix*g2.dw)); panY+=(cy-(g2.dy+iy*g2.dh)); }
      else zoom=nz;
      var wd=wantDpi(); if(wd!==imgDpi && wd>imgDpi) fetchDpi(wd);   // upgrade resolution as we zoom in
      draw();
    }
    function reset(){ zoom=1; panX=0; panY=0; if(imgDpi>150) fetchDpi(150); else draw(); }

    var drag=false,lx=0,ly=0;
    cv.addEventListener('mousedown',function(e){ drag=true; lx=e.clientX; ly=e.clientY; cv.style.cursor='grabbing'; });
    window.addEventListener('mousemove',function(e){ if(!drag) return; var dpr=window.devicePixelRatio||1; panX+=(e.clientX-lx)*dpr; panY+=(e.clientY-ly)*dpr; lx=e.clientX; ly=e.clientY; draw(); });
    window.addEventListener('mouseup',function(){ drag=false; cv.style.cursor='grab'; });
    cv.addEventListener('wheel',function(e){ e.preventDefault(); var dpr=window.devicePixelRatio||1;
      var r=cv.getBoundingClientRect(); var cx=(e.clientX-r.left)*dpr, cy=(e.clientY-r.top)*dpr;
      setZoom(zoom*(e.deltaY<0?1.15:0.87), cx, cy); },{passive:false});
    cv.addEventListener('dblclick',reset);
    // touch: 1-finger pan, 2-finger pinch
    var pd=0; function dist(e){ var a=e.touches[0],b=e.touches[1]; return Math.hypot(a.clientX-b.clientX,a.clientY-b.clientY); }
    cv.addEventListener('touchstart',function(e){ if(e.touches.length===1){ drag=true; lx=e.touches[0].clientX; ly=e.touches[0].clientY; } else if(e.touches.length===2){ drag=false; pd=dist(e); } e.preventDefault(); },{passive:false});
    cv.addEventListener('touchmove',function(e){ var dpr=window.devicePixelRatio||1;
      if(e.touches.length===1&&drag){ panX+=(e.touches[0].clientX-lx)*dpr; panY+=(e.touches[0].clientY-ly)*dpr; lx=e.touches[0].clientX; ly=e.touches[0].clientY; draw(); }
      else if(e.touches.length===2){ var d=dist(e); if(pd) setZoom(zoom*(d/pd)); pd=d; } e.preventDefault(); },{passive:false});
    cv.addEventListener('touchend',function(){ drag=false; pd=0; });

    bIn.onclick=function(){ setZoom(zoom*1.3, cv.width/2, cv.height/2); };
    bOut.onclick=function(){ setZoom(zoom*0.77, cv.width/2, cv.height/2); };
    bFit.onclick=reset;
    bHot.onclick=function(){ hotOn=!hotOn; bHot.style.background=hotOn?'#4f9dff':'rgba(20,28,38,.85)'; bHot.style.color=hotOn?'#08111d':'#cfe'; draw(); };
    bHot.style.background='#4f9dff'; bHot.style.color='#08111d';

    var ro=null; if(window.ResizeObserver){ ro=new ResizeObserver(fit); ro.observe(container); } else window.addEventListener('resize',fit);

    fetchDpi(150);
    xget('/api/callouts?doc='+encodeURIComponent(doc)+'&page='+encodeURIComponent(page), function(d){
      var cs=(d&&d.callouts)||[]; callouts=[]; for(var i=0;i<cs.length;i++){ if(cs[i].box){ cs[i]._n=callouts.length+1; callouts.push(cs[i]); } }
      if(opts.onInfo) opts.onInfo({callouts:callouts.length, anchored:d&&d.anchored});
      draw();
    });

    return { destroy:function(){ dead=true; if(ro) ro.disconnect(); else window.removeEventListener('resize',fit); try{container.innerHTML='';}catch(e){} },
             reset:reset, callouts:function(){ return callouts.length; } };
  }
  window.DeepZoom = { mount: mount };
})();
