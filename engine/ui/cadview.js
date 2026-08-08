/* THE VIEWER -- cadview.js : makes the CAD image INTERACTIVE — rotate (drag), zoom/scale (wheel + pinch), auto-spin.
   It loads a turntable sprite sheet from /cadspin (N shaded CAD frames around 360°, the same renderer that makes the
   static CAD image — so it keeps the shading, colour, texture and dimension callouts) and scrubs frames on drag.
   GPU-free (a canvas + one PNG), ES5-safe so it runs on every RPS tier; legacy just gets fewer frames.
   Use:  var h = CadView.mount(containerEl, nsn, {tier:'modern', autospin:true});  h.destroy(); */
(function(){
  function el(tag, css, html){ var e=document.createElement(tag); if(css) e.style.cssText=css; if(html!=null) e.innerHTML=html; return e; }

  function mount(container, nsn, opts){
    opts=opts||{}; if(!container||!nsn) return {destroy:function(){}};
    container.innerHTML=''; container.style.position='relative'; container.style.background='#f4f6f8'; container.style.overflow='hidden'; container.style.borderRadius='8px';
    var cv=el('canvas','display:block;width:100%;height:100%;cursor:grab;touch-action:none'); container.appendChild(cv);
    var ctx=cv.getContext('2d');
    var hint=el('div','position:absolute;left:8px;bottom:8px;color:#46566a;font-size:11px;background:rgba(255,255,255,.78);border:1px solid #d3dae2;border-radius:6px;padding:2px 8px;pointer-events:none','drag to rotate · scroll to zoom');
    container.appendChild(hint);
    // controls
    var bar=el('div','position:absolute;right:8px;top:8px;display:flex;gap:4px;z-index:3');
    function mk(t,title){ return el('button','background:rgba(20,28,38,.82);color:#cfe;border:1px solid #2f4858;border-radius:6px;width:30px;height:26px;cursor:pointer;font-size:13px;line-height:1',t); }
    var bSpin=mk('⟳','auto-rotate'), bZin=mk('+','zoom in'), bZout=mk('−','zoom out'), bRst=mk('⌂','reset view');
    bSpin.title='auto-rotate'; bZin.title='zoom in'; bZout.title='zoom out'; bRst.title='reset view';
    bar.appendChild(bSpin); bar.appendChild(bZin); bar.appendChild(bZout); bar.appendChild(bRst); container.appendChild(bar);
    var load=el('div','position:absolute;inset:0;display:flex;align-items:center;justify-content:center;color:#8a98a8;font-size:13px','rendering rotatable CAD…'); container.appendChild(load);

    var img=null, frames=1, srcFW=1, frameH=1, frame=0, zoom=1, panX=0, panY=0, spin=false, rafId=null, spinAcc=0, dead=false;

    function fit(){ // device-pixel sizing
      var r=container.getBoundingClientRect(); var dpr=window.devicePixelRatio||1;
      cv.width=Math.max(1,Math.round(r.width*dpr)); cv.height=Math.max(1,Math.round(r.height*dpr));
      cv.style.width=r.width+'px'; cv.style.height=r.height+'px'; draw();
    }
    function draw(){
      if(dead||!img) return; var W=cv.width, H=cv.height; ctx.clearRect(0,0,W,H);
      var fi=((Math.round(frame)%frames)+frames)%frames; var sx=fi*srcFW;
      // contain the frame, then apply zoom about the centre
      var s=Math.min(W/srcFW, H/frameH)*zoom; var dw=srcFW*s, dh=frameH*s;
      var dx=(W-dw)/2 + panX, dy=(H-dh)/2 + panY;
      ctx.imageSmoothingEnabled=true; try{ ctx.imageSmoothingQuality='high'; }catch(e){}
      ctx.drawImage(img, sx, 0, srcFW, frameH, dx, dy, dw, dh);
    }
    function clampPan(){ var W=cv.width,H=cv.height; var s=Math.min(W/srcFW,H/frameH)*zoom; var dw=srcFW*s,dh=frameH*s;
      var mx=Math.max(0,(dw-W)/2+40), my=Math.max(0,(dh-H)/2+40);
      panX=Math.max(-mx,Math.min(mx,panX)); panY=Math.max(-my,Math.min(my,panY)); }

    // ----- load the sprite sheet (XHR so we can read frame-count headers; ES5-safe) -----
    var q='/cadspin?nsn='+encodeURIComponent(nsn)+(opts.tier?('&tier='+encodeURIComponent(opts.tier)):'')+(opts.n?('&n='+opts.n):'');
    var x=new XMLHttpRequest(); x.open('GET',q,true); x.responseType='blob';
    x.onreadystatechange=function(){ if(x.readyState!==4) return;
      if(x.status<200||x.status>=300){ load.textContent='CAD turntable unavailable'; return; }
      frames=parseInt(x.getResponseHeader('X-CAD-Frames')||'24',10)||24;
      var url=(window.URL||window.webkitURL).createObjectURL(x.response);
      img=new Image(); img.onload=function(){ srcFW=img.naturalWidth/frames; frameH=img.naturalHeight;
        try{ container.removeChild(load); }catch(e){} fit(); if(opts.autospin) toggleSpin(true);
      }; img.onerror=function(){ load.textContent='CAD turntable failed to load'; }; img.src=url;
    }; x.send();

    // ----- interaction: drag = rotate (and pan when zoomed) -----
    var drag=false, lx=0, ly=0, moved=0;
    function down(cx,cy){ drag=true; lx=cx; ly=cy; moved=0; cv.style.cursor='grabbing'; if(spin) toggleSpin(false); }
    function move(cx,cy){ if(!drag||!img) return; var dx=cx-lx, dy=cy-ly; lx=cx; ly=cy; moved+=Math.abs(dx)+Math.abs(dy);
      // horizontal drag scrubs frames; a full container width ≈ one full turn
      var perFrame=(container.getBoundingClientRect().width||300)/frames;
      frame -= dx/Math.max(6,perFrame);
      if(zoom>1.02){ panX+=dx*(window.devicePixelRatio||1); panY+=dy*(window.devicePixelRatio||1); clampPan(); }
      draw();
    }
    function up(){ drag=false; cv.style.cursor='grab'; }
    cv.addEventListener('mousedown',function(e){ down(e.clientX,e.clientY); e.preventDefault(); });
    window.addEventListener('mousemove',function(e){ move(e.clientX,e.clientY); });
    window.addEventListener('mouseup',up);
    cv.addEventListener('wheel',function(e){ e.preventDefault(); var f=e.deltaY<0?1.12:0.89; setZoom(zoom*f); },{passive:false});
    cv.addEventListener('dblclick',function(){ reset(); });
    // touch: 1 finger rotate, 2 finger pinch-zoom
    var pd=0;
    cv.addEventListener('touchstart',function(e){ if(e.touches.length===1){ down(e.touches[0].clientX,e.touches[0].clientY); }
      else if(e.touches.length===2){ drag=false; pd=dist(e); } e.preventDefault(); },{passive:false});
    cv.addEventListener('touchmove',function(e){ if(e.touches.length===1){ move(e.touches[0].clientX,e.touches[0].clientY); }
      else if(e.touches.length===2){ var d=dist(e); if(pd) setZoom(zoom*(d/pd)); pd=d; } e.preventDefault(); },{passive:false});
    cv.addEventListener('touchend',function(){ up(); pd=0; });
    function dist(e){ var a=e.touches[0],b=e.touches[1]; return Math.sqrt(Math.pow(a.clientX-b.clientX,2)+Math.pow(a.clientY-b.clientY,2)); }

    function setZoom(z){ zoom=Math.max(1,Math.min(6,z)); if(zoom<=1.02){ panX=0; panY=0; } else clampPan(); draw(); }
    function reset(){ zoom=1; panX=0; panY=0; draw(); }
    function toggleSpin(on){ spin=(on==null?!spin:on); bSpin.style.background=spin?'#4f9dff':'rgba(20,28,38,.82)'; bSpin.style.color=spin?'#08111d':'#cfe';
      if(spin && !rafId){ var last=0; (function loop(ts){ if(dead){ return; } if(!spin){ rafId=null; return; }
        if(last){ frame+=(ts-last)/1000* (frames/6); draw(); } last=ts; rafId=requestAnimationFrame(loop); })(0); }
    }
    bSpin.onclick=function(){ toggleSpin(); }; bZin.onclick=function(){ setZoom(zoom*1.25); };
    bZout.onclick=function(){ setZoom(zoom*0.8); }; bRst.onclick=function(){ reset(); };

    var ro=null; if(window.ResizeObserver){ ro=new ResizeObserver(fit); ro.observe(container); } else window.addEventListener('resize',fit);

    return { destroy:function(){ dead=true; spin=false; if(rafId) cancelAnimationFrame(rafId); if(ro) ro.disconnect(); else window.removeEventListener('resize',fit);
        try{ container.innerHTML=''; }catch(e){} }, spin:function(on){ toggleSpin(on); }, reset:reset };
  }
  window.CadView = { mount: mount };
})();
