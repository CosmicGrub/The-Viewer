/* THE VIEWER — loupe.js : a reusable magnifier lens for ANY image (schematics, figures, crops).
   Dependency-free ES5. Loupe.attach(imgEl) -> follows the cursor, magnifies the image under it; mouse-wheel
   changes magnification; leaves on mouse-out. Barring 3-D (attach only to <img>, never the WebGL canvas).
   Re-callable safely (no double-attach). Works on legacy browsers (CSS background magnification, no server). */
(function(){
  function attach(img, opts){
    if(!img || img.nodeName!=='IMG' || img._loupe) return function(){};
    opts = opts || {};
    var size = opts.size || 210;          // lens diameter (px)
    var mag  = opts.mag  || 2.6;          // starting magnification
    img._loupe = true;
    var lens = document.createElement('div');
    lens.className = 'viewer-loupe-lens';
    lens.style.cssText = 'position:fixed;pointer-events:none;display:none;z-index:99999;width:'+size+'px;height:'+size+'px;'
      + 'border-radius:50%;border:2px solid #4f9dff;box-shadow:0 8px 28px rgba(0,0,0,.6),inset 0 0 0 1px rgba(255,255,255,.15);'
      + 'background-repeat:no-repeat;background-color:#0a0e12';
    document.body.appendChild(lens);
    function inside(e, r){ return e.clientX>=r.left && e.clientX<=r.right && e.clientY>=r.top && e.clientY<=r.bottom; }
    function move(e){
      var r = img.getBoundingClientRect();
      if(!r.width || !inside(e, r)){ hide(); return; }
      lens.style.display = 'block'; img.style.cursor = 'none';
      var x = e.clientX - r.left, y = e.clientY - r.top;
      var bw = r.width * mag, bh = r.height * mag;
      lens.style.backgroundImage = "url('" + (img.currentSrc || img.src) + "')";
      lens.style.backgroundSize = bw + 'px ' + bh + 'px';
      lens.style.backgroundPosition = (-(x*mag - size/2)) + 'px ' + (-(y*mag - size/2)) + 'px';
      lens.style.left = (e.clientX - size/2) + 'px';
      lens.style.top  = (e.clientY - size/2) + 'px';
    }
    function hide(){ lens.style.display = 'none'; img.style.cursor = ''; }
    function wheel(e){
      if(lens.style.display === 'none') return;
      e.preventDefault();
      mag += (e.deltaY < 0 ? 0.4 : -0.4); mag = Math.max(1.5, Math.min(8, mag));
      move(e);
    }
    img.addEventListener('mousemove', move);
    img.addEventListener('mouseleave', hide);
    img.addEventListener('wheel', wheel, {passive:false});
    img._loupeDetach = function(){
      img.removeEventListener('mousemove', move); img.removeEventListener('mouseleave', hide);
      img.removeEventListener('wheel', wheel);
      if(lens.parentNode) lens.parentNode.removeChild(lens);
      img._loupe = false; img.style.cursor = '';
    };
    return img._loupeDetach;
  }
  // attach to every <img> matching a selector inside root (idempotent)
  function attachAll(root, selector, opts){
    try{ var imgs=(root||document).querySelectorAll(selector||'img'); for(var i=0;i<imgs.length;i++) attach(imgs[i], opts); }catch(e){}
  }
  window.Loupe = { attach:attach, attachAll:attachAll };
})();
