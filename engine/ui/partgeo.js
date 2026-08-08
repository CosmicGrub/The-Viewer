/* THE VIEWER — partgeo.js : detailed parametric part geometry from FLIS dimensions + characteristics.
   Replaces the blocky primitives with recognisable part shapes — a bolt has a hex head + threaded shank,
   a gasket is a ring with bolt-holes, a bearing has races + balls, a gear has teeth, a spring is a helix.
   Pure math; returns {V:[[x,y,z]...], F:[[i,j,k,...]...], smooth:bool} consumed by gl3d.js AND the SVG
   fallback. Offline, dependency-free. window.PartGeo.build(family, dims) / window.PartGeo.family(name,chars). */
(function(){
  var TAU = Math.PI * 2;

  function Mesh(){ this.V = []; this.F = []; }
  Mesh.prototype.add = function(g, ox, oy, oz){
    ox = ox||0; oy = oy||0; oz = oz||0;
    var o = this.V.length, i;
    for(i=0;i<g.V.length;i++){ var v=g.V[i]; this.V.push([v[0]+ox, v[1]+oy, v[2]+oz]); }
    for(i=0;i<g.F.length;i++){ var f=g.F[i], nf=[]; for(var k=0;k<f.length;k++) nf.push(f[k]+o); this.F.push(nf); }
    return this;
  };
  Mesh.prototype.get = function(){ return {V:this.V, F:this.F}; };

  // --- primitives (Y is the long axis; outward winding) ---
  // Cylinder/cone: radius rB at bottom, rT at top, height h, centred on origin.
  function cyl(rB, rT, h, seg, capB, capT){
    rT = (rT==null)?rB:rT; seg = seg||28; var V=[], F=[], i, y0=-h/2, y1=h/2;
    for(i=0;i<seg;i++){ var a=i/seg*TAU, c=Math.cos(a), s=Math.sin(a);
      V.push([c*rB, y0, s*rB]); V.push([c*rT, y1, s*rT]); }
    for(i=0;i<seg;i++){ var j=(i+1)%seg; F.push([i*2, j*2, j*2+1, i*2+1]); }
    if(capB!==false && rB>1e-6){ var bc=V.length; V.push([0,y0,0]); for(i=0;i<seg;i++){ var j2=(i+1)%seg; F.push([bc, j2*2, i*2]); } }
    if(capT!==false && rT>1e-6){ var tc=V.length; V.push([0,y1,0]); for(i=0;i<seg;i++){ var j3=(i+1)%seg; F.push([tc, i*2+1, j3*2+1]); } }
    return {V:V, F:F};
  }
  // Regular n-gon prism (hex head / nut), across-flats = 2*r, height h, with a chamfer on each end.
  function prism(r, h, sides, chamfer){
    sides = sides||6; chamfer = (chamfer==null)? r*0.16 : chamfer;
    var V=[], F=[], i, y0=-h/2, y1=h/2, rc=r-chamfer;
    for(i=0;i<sides;i++){ var a=(i+0.5)/sides*TAU, c=Math.cos(a), s=Math.sin(a);
      V.push([c*rc,y0,s*rc]); V.push([c*r,y0+chamfer,s*r]); V.push([c*r,y1-chamfer,s*r]); V.push([c*rc,y1,s*rc]); }
    for(i=0;i<sides;i++){ var j=(i+1)%sides, b=i*4, n=j*4;
      F.push([b,n,n+1,b+1]); F.push([b+1,n+1,n+2,b+2]); F.push([b+2,n+2,n+3,b+3]); }
    var bc=V.length; V.push([0,y0,0]); for(i=0;i<sides;i++){ var j2=(i+1)%sides; F.push([bc, j2*4, i*4]); }
    var tc=V.length; V.push([0,y1,0]); for(i=0;i<sides;i++){ var j3=(i+1)%sides; F.push([tc, i*4+3, j3*4+3]); }
    return {V:V, F:F};
  }
  // Annular tube (washer / race / pipe wall): outer R, inner r, height h. Walls + end rings.
  function tube(R, r, h, seg){
    seg = seg||32; var V=[], F=[], i, y0=-h/2, y1=h/2;
    for(i=0;i<seg;i++){ var a=i/seg*TAU, c=Math.cos(a), s=Math.sin(a);
      V.push([c*R,y0,s*R]); V.push([c*R,y1,s*R]); V.push([c*r,y0,s*r]); V.push([c*r,y1,s*r]); }
    for(i=0;i<seg;i++){ var j=(i+1)%seg, b=i*4, n=j*4;
      F.push([b,n,n+1,b+1]);             // outer wall
      F.push([b+2,b+3,n+3,n+2]);         // inner wall (reversed)
      F.push([b+1,n+1,n+3,b+3]);         // top ring
      F.push([b,b+2,n+2,n]);             // bottom ring
    }
    return {V:V, F:F};
  }
  // Torus (o-ring / seal): tube radius rt around ring radius R.
  function torus(R, rt, su, sv){
    su=su||30; sv=sv||16; var V=[], F=[], i, j;
    for(i=0;i<su;i++){ var a=i/su*TAU, ca=Math.cos(a), sa=Math.sin(a);
      for(j=0;j<sv;j++){ var b=j/sv*TAU, cb=Math.cos(b), sb=Math.sin(b);
        V.push([ (R+rt*cb)*ca, rt*sb, (R+rt*cb)*sa ]); } }
    for(i=0;i<su;i++){ var ni=(i+1)%su; for(j=0;j<sv;j++){ var nj=(j+1)%sv;
      F.push([i*sv+j, ni*sv+j, ni*sv+nj, i*sv+nj]); } }
    return {V:V, F:F};
  }
  function sphere(rr, su, sv){
    su=su||16; sv=sv||12; var V=[], F=[], i, j;
    for(i=0;i<=sv;i++){ var th=i/sv*Math.PI, st=Math.sin(th), ct=Math.cos(th);
      for(j=0;j<su;j++){ var ph=j/su*TAU; V.push([rr*st*Math.cos(ph), rr*ct, rr*st*Math.sin(ph)]); } }
    for(i=0;i<sv;i++){ for(j=0;j<su;j++){ var nj=(j+1)%su;
      F.push([i*su+j, (i+1)*su+j, (i+1)*su+nj, i*su+nj]); } }
    return {V:V, F:F};
  }
  // Helix swept circle (spring): coil radius R, wire radius rw, turns t, height h.
  function helix(R, rw, turns, h, su, sv){
    su=su||Math.max(60, Math.round(turns*24)); sv=sv||8; var V=[], F=[], i, j;
    for(i=0;i<=su;i++){ var u=i/su, a=u*turns*TAU, y=-h/2+u*h;
      var cx=Math.cos(a)*R, cz=Math.sin(a)*R;
      var tx=-Math.sin(a), tz=Math.cos(a);                 // tangent (approx; ignore pitch tilt)
      for(j=0;j<sv;j++){ var b=j/sv*TAU, cb=Math.cos(b), sb=Math.sin(b);
        // ring in plane perpendicular to tangent: radial = (cos a, 0, sin a), up = y
        var rx=Math.cos(a), rz=Math.sin(a);
        V.push([ cx + cb*rw*rx, y + sb*rw, cz + cb*rw*rz ]); } }
    for(i=0;i<su;i++){ for(j=0;j<sv;j++){ var nj=(j+1)%sv;
      F.push([i*sv+j, (i+1)*sv+j, (i+1)*sv+nj, i*sv+nj]); } }
    return {V:V, F:F};
  }
  // Spur gear: toothed disc, pitch radius R, tooth depth td, teeth n, thickness h, bore.
  function gear(R, td, n, h, bore, seg){
    n = Math.max(6, Math.min(40, n||14)); var V=[], F=[], i, y0=-h/2, y1=h/2, per=8;
    for(i=0;i<n;i++){
      var a0=i/n*TAU, a1=(i+0.5)/n*TAU, a2=(i+1)/n*TAU;
      var rr=R-td, ro=R;
      // four rim points: root@a0, tip@a0+, tip@a1-, root@a2  -> a simple trapezoid tooth
      var pts=[[a0,rr],[a0+0.12/n*TAU,ro],[a1-0.12/n*TAU,ro],[a1,rr]];
      for(var k=0;k<4;k++){ var a=pts[k][0], r=pts[k][1], c=Math.cos(a), s=Math.sin(a);
        V.push([c*r,y0,s*r]); V.push([c*r,y1,s*r]); }
    }
    var ppt=n*4; // points per... we pushed 4*2 per tooth
    // outer wall + top/bottom around the toothed outline
    for(i=0;i<ppt;i++){ var j=(i+1)%ppt, b=i*2, m=j*2;
      F.push([b,m,m+1,b+1]); }
    // caps to bore
    if(bore>1e-4){
      var biStart=V.length;
      for(i=0;i<ppt;i++){ var a=i/ppt*TAU, c=Math.cos(a), s=Math.sin(a); V.push([c*bore,y0,s*bore]); V.push([c*bore,y1,s*bore]); }
      for(i=0;i<ppt;i++){ var j=(i+1)%ppt; var o0=i*2, o1=j*2, i0=biStart+i*2, i1=biStart+j*2;
        F.push([o0+1, o1+1, i1+1, i0+1]);   // top
        F.push([o0, i0, i1, o1]);           // bottom
        F.push([i0, i0+1, i1+1, i1]);       // bore wall (reversed-ish)
      }
    } else {
      var tc=V.length; V.push([0,y1,0]); for(i=0;i<ppt;i++){ var j=(i+1)%ppt; F.push([tc, i*2+1, j*2+1]); }
      var bc=V.length; V.push([0,y0,0]); for(i=0;i<ppt;i++){ var j=(i+1)%ppt; F.push([bc, j*2, i*2]); }
    }
    return {V:V, F:F};
  }

  // --- family builders (dims in inches; we scale only relatively) ---
  function f_bolt(p){
    var m=new Mesh(), dia=p.dia||p.W||0.4, L=p.L||1.4, headD=dia*1.7, headH=dia*0.7;
    var thread=cyl(dia*0.5, dia*0.5, L, 24, true, false);
    m.add(thread, 0, -headH*0.5, 0);
    // thread grooves: stacked thin truncated cones along the shank
    var rings=Math.max(5, Math.round(L/(dia*0.32))), tg;
    for(var i=0;i<rings;i++){ tg=cyl(dia*0.5, dia*0.42, dia*0.18, 18, false, false);
      m.add(tg, 0, -L*0.5 - headH*0.5 + dia*0.10 + i*(L/rings), 0); }
    m.add(prism(headD*0.5, headH, 6, headH*0.22), 0, L*0.5 - headH*0.5, 0);  // hex head
    return {V:m.V, F:m.F, smooth:true};
  }
  function f_nut(p){
    var m=new Mesh(), af=(p.dia||p.W||0.5), h=af*0.8, bore=af*0.32;
    m.add(prism(af*0.62, h, 6, h*0.22));
    m.add(tube(af*0.62, bore, h*1.001, 30));   // bore wall
    return {V:m.V, F:m.F, smooth:false};
  }
  function f_washer(p){
    var R=(p.dia||p.W||0.6)*0.5, r=R*0.5, h=(p.H||0.06); h=Math.max(h, R*0.10);
    return mergeSmooth(tube(R, r, h, 36), true);
  }
  function f_gasket(p){
    var R=(p.dia||p.W||1.2)*0.5, r=R*0.62, h=Math.max(p.H||0.05, R*0.05);
    var m=new Mesh(); m.add(tube(R, r, h, 40));
    var holes=Math.max(4, Math.min(12, Math.round(R*8))), hr=R*0.10, ringR=(R+r)/2;
    for(var i=0;i<holes;i++){ var a=i/holes*TAU; m.add(tube(hr, hr*0.55, h*1.02, 12), Math.cos(a)*ringR, 0, Math.sin(a)*ringR); }
    return {V:m.V, F:m.F, smooth:false};
  }
  function f_bearing(p){
    var R=(p.dia||p.W||1.0)*0.5, h=(p.H||R*0.5), bore=R*0.5;
    var m=new Mesh();
    m.add(tube(R, R*0.78, h, 36));                 // outer race
    m.add(tube(bore*1.18, bore, h, 30));           // inner race
    var balls=Math.max(7, Math.round(R*12)), br=(R*0.78 - bore*1.18)*0.5*0.92, ringR=(R*0.78+bore*1.18)/2;
    for(var i=0;i<balls;i++){ var a=i/balls*TAU; m.add(sphere(br,14,10), Math.cos(a)*ringR, 0, Math.sin(a)*ringR); }
    return {V:m.V, F:m.F, smooth:true};
  }
  function f_gear(p){
    var R=(p.dia||p.W||1.0)*0.5, h=(p.H||R*0.4), bore=(p.bore?p.bore*0.5:R*0.28), n=p.teeth||Math.round(R*16);
    n=Math.max(6, Math.min(80, n));
    var g=gear(R, R*0.16, n, h, bore, 0); return {V:g.V, F:g.F, smooth:false};
  }
  function f_spring(p){
    var R=(p.dia||p.W||0.5)*0.5, h=(p.L||p.H||1.6), wire=R*0.20;
    var turns=p.turns||Math.max(4, Math.round(h/(wire*2.6))); turns=Math.max(2, Math.min(40, turns));
    return mergeSmooth(helix(R, wire, turns, h, 0, 8), true);
  }
  function f_tube(p){
    var R=(p.dia||p.W||0.5)*0.5, h=(p.L||1.4), r=R*0.72;
    return mergeSmooth(tube(R, r, h, 32), true);
  }
  function f_oring(p){
    var R=(p.dia||p.W||0.6)*0.5, rt=R*0.22;
    return mergeSmooth(torus(R-rt, rt, 36, 18), true);
  }
  function f_shaft(p){
    var R=(p.dia||p.W||0.3)*0.5, h=(p.L||1.6), m=new Mesh();
    m.add(cyl(R*0.82,R,h*0.06,24,false,true), 0, h*0.5-h*0.03, 0);   // chamfer ends
    m.add(cyl(R,R,h*0.9,24,false,false), 0, 0, 0);
    m.add(cyl(R,R*0.82,h*0.06,24,true,false), 0, -h*0.5+h*0.03, 0);
    return {V:m.V, F:m.F, smooth:true};
  }
  function f_bracket(p){
    var w=(p.W||1.0), h=(p.H||1.0), t=Math.max(p.L||0.12, w*0.10), m=new Mesh();
    m.add(boxG(w, t, w*0.7), 0, -h*0.5+t*0.5, 0);          // base
    m.add(boxG(t, h, w*0.7), -w*0.5+t*0.5, 0, 0);          // upright
    // bolt holes in base
    m.add(tube(w*0.12, w*0.06, t*1.3, 14), w*0.22, -h*0.5+t*0.5, w*0.18);
    m.add(tube(w*0.12, w*0.06, t*1.3, 14), w*0.22, -h*0.5+t*0.5, -w*0.18);
    return {V:m.V, F:m.F, smooth:false};
  }
  function f_battery(p){
    var w=(p.W||1.0), h=(p.H||0.9), d=(p.L||0.7), m=new Mesh();
    m.add(boxG(w, h, d));
    m.add(cyl(w*0.09,w*0.09,h*0.18,16,true,true), -w*0.22, h*0.5+h*0.09, d*0.16);  // + post
    m.add(cyl(w*0.09,w*0.09,h*0.18,16,true,true),  w*0.22, h*0.5+h*0.09, d*0.16);  // - post
    return {V:m.V, F:m.F, smooth:false};
  }
  function f_box(p){ return {V:boxG(p.W||1,p.H||1,p.L||1).V, F:boxG(p.W||1,p.H||1,p.L||1).F, smooth:false}; }

  function boxG(w,h,d){ var x=w/2,y=h/2,z=d/2;
    var V=[[-x,-y,-z],[x,-y,-z],[x,y,-z],[-x,y,-z],[-x,-y,z],[x,-y,z],[x,y,z],[-x,y,z]];
    var F=[[0,3,2,1],[4,5,6,7],[0,1,5,4],[2,3,7,6],[1,2,6,5],[0,4,7,3]];
    return {V:V,F:F};
  }
  function mergeSmooth(g, s){ return {V:g.V, F:g.F, smooth:!!s}; }

  // --- added families (v0.84): plate/cover/pad/link/lever/rivet/switch/cylinder/canister ---
  function f_plate(p){
    var w=(p.W||p.dia||1.2), d=(p.L||w*0.7), t=Math.max(p.H||0.08, w*0.04), m=new Mesh();
    m.add(boxG(w, t, d));
    var hr=Math.min(w,d)*0.08, ox=w*0.5-hr*1.9, oz=d*0.5-hr*1.9;
    m.add(tube(hr, hr*0.5, t*1.3, 12),  ox,0, oz); m.add(tube(hr, hr*0.5, t*1.3, 12), -ox,0, oz);
    m.add(tube(hr, hr*0.5, t*1.3, 12),  ox,0,-oz); m.add(tube(hr, hr*0.5, t*1.3, 12), -ox,0,-oz);
    return {V:m.V, F:m.F, smooth:false};
  }
  function f_cover(p){
    var w=(p.W||p.dia||1.4), d=(p.L||w*0.8), h=Math.max(p.H||w*0.22, w*0.10), t=Math.max(w*0.05,0.04), m=new Mesh();
    m.add(boxG(w, t, d), 0, h*0.5-t*0.5, 0);
    m.add(boxG(t, h, d), -w*0.5+t*0.5, 0, 0); m.add(boxG(t, h, d), w*0.5-t*0.5, 0, 0);
    m.add(boxG(w, h, t), 0, 0, -d*0.5+t*0.5); m.add(boxG(w, h, t), 0, 0, d*0.5-t*0.5);
    return {V:m.V, F:m.F, smooth:false};
  }
  function f_pad(p){
    var w=(p.W||p.dia||1.0), d=(p.L||w*0.7), h=Math.max(p.H||0.25, w*0.12), m=new Mesh();
    m.add(boxG(w, h*0.7, d), 0, -h*0.15, 0);
    m.add(boxG(w*0.86, h*0.5, d*0.86), 0, h*0.30, 0);
    return {V:m.V, F:m.F, smooth:true};
  }
  function f_link(p){
    var L=(p.L||1.6), w=(p.W||L*0.30), t=Math.max(p.H||w*0.5, 0.06), m=new Mesh();
    m.add(boxG(L*0.66, t, w*0.6));
    var er=w*0.5; m.add(tube(er, er*0.45, t, 18), L*0.5-er, 0, 0); m.add(tube(er, er*0.45, t, 18), -L*0.5+er, 0, 0);
    return {V:m.V, F:m.F, smooth:false};
  }
  function f_lever(p){
    var L=(p.L||1.8), w=(p.W||L*0.18), t=Math.max(w*0.5,0.06), m=new Mesh();
    m.add(boxG(L*0.86, t, w));
    var er=w*0.7; m.add(tube(er, er*0.4, t*1.2, 18), -L*0.5+er, 0, 0);
    m.add(sphere(w*0.6, 14, 10), L*0.5, 0, 0);
    return {V:m.V, F:m.F, smooth:false};
  }
  function f_rivet(p){
    var dia=(p.dia||p.W||0.25), L=(p.L||0.7), m=new Mesh();
    m.add(cyl(dia*0.5, dia*0.5, L, 20, true, false), 0, -L*0.5, 0);
    m.add(cyl(dia*0.95, dia*0.55, dia*0.5, 20, true, true), 0, dia*0.18, 0);   // rounded button head
    return {V:m.V, F:m.F, smooth:true};
  }
  function f_switch(p){
    var w=(p.W||0.7), h=(p.H||0.6), d=(p.L||0.6), m=new Mesh();
    m.add(boxG(w, h, d));
    m.add(cyl(w*0.10, w*0.07, h*0.5, 12, true, true), 0, h*0.5+h*0.22, 0);    // toggle
    m.add(sphere(w*0.12, 12, 8), 0, h*0.5+h*0.5, 0);
    m.add(boxG(w*0.10, h*0.3, w*0.06), -w*0.25, -h*0.5-h*0.12, 0);            // terminals
    m.add(boxG(w*0.10, h*0.3, w*0.06),  w*0.25, -h*0.5-h*0.12, 0);
    return {V:m.V, F:m.F, smooth:false};
  }
  function f_cylinder(p){
    var R=(p.dia||p.W||0.8)*0.5, h=(p.L||p.H||1.6), m=new Mesh();
    m.add(cyl(R, R, h, 28, true, true));
    m.add(cyl(R*1.12, R*1.12, h*0.08, 28, true, true), 0,  h*0.5-h*0.04, 0);  // end rims
    m.add(cyl(R*1.12, R*1.12, h*0.08, 28, true, true), 0, -h*0.5+h*0.04, 0);
    m.add(cyl(R*0.18, R*0.18, R*0.7, 14, true, true), R*0.9, h*0.18, 0);      // port stub
    return {V:m.V, F:m.F, smooth:true};
  }
  function f_canister(p){
    var R=(p.dia||p.W||1.0)*0.5, h=(p.L||p.H||1.6), m=new Mesh(), i;
    m.add(cyl(R, R, h*0.8, 28, true, false), 0, -h*0.1, 0);
    var dome=sphere(R, 20, 10), Vd=[];
    for(i=0;i<dome.V.length;i++){ var v=dome.V[i]; Vd.push([v[0], Math.max(0, v[1])*0.6 + h*0.30, v[2]]); }
    m.add({V:Vd, F:dome.F}, 0, 0, 0);
    m.add(cyl(R*1.08, R*1.08, h*0.07, 28, true, true), 0, -h*0.5+h*0.035, 0); // base rim
    m.add(cyl(R*0.16, R*0.16, h*0.2, 12, true, true), 0, h*0.45, 0);          // top spigot
    return {V:m.V, F:m.F, smooth:true};
  }

  function family(name, chars){
    var t=((name||'')+' '+(chars||'')).toUpperCase();
    // fasteners
    if(/\bNUT\b/.test(t)) return 'nut';
    if(/\bRIVET\b/.test(t)) return 'rivet';
    if(/BOLT|SCREW|CAPSCREW|\bSTUD\b|\bSCRW\b/.test(t)) return 'bolt';
    if(/WASHER\b/.test(t)) return 'washer';
    if(/GASKET|\bSHIM\b/.test(t)) return 'gasket';
    if(/O-?RING|\bSEAL\b|PACKING|QUAD RING/.test(t)) return 'oring';
    if(/BEARING/.test(t)) return 'bearing';
    if(/GEAR|SPROCKET|PINION/.test(t)) return 'gear';
    if(/SPRING|\bCOIL\b/.test(t)) return 'spring';
    // links / levers / handles (before generic structural)
    if(/\bLINK\b/.test(t)) return 'link';
    if(/\bLEVER\b|\bHANDLE\b|\bCRANK\b|\bPEDAL\b|CONTROL ARM|\bARM\b/.test(t)) return 'lever';
    // electrical-ish bodies
    if(/SWITCH|\bRELAY\b/.test(t)) return 'switch';
    if(/CIRCUIT CARD|\bCCA\b|PRINTED.*BOARD|\bBOARD\b/.test(t)) return 'plate';
    // cylindrical bodies / canisters
    if(/AIR CLEANER|\bFILTER\b|\bCARTRIDGE\b|\bELEMENT\b|CANISTER|RESERVOIR|\bTANK\b|ACCUMULATOR|DRIER/.test(t)) return 'canister';
    if(/CYLINDER|ACTUATOR|\bMOTOR\b|\bPUMP\b|SOLENOID|COMPRESSOR|\bVALVE\b/.test(t)) return 'cylinder';
    // covers / panels
    if(/COVER|\bDOOR\b|\bPANEL\b|HATCH|\bLID\b|\bGUARD\b|SHIELD|DEFLECTOR|BEZEL/.test(t)) return 'cover';
    // soft goods / pads
    if(/INSULAT|\bPAD\b|CUSHION|\bMAT\b|\bSTRAP\b|WEBBING/.test(t)) return 'pad';
    // tubes / hoses / wiring / connectors
    if(/PIPE|TUBE|TUBING|HOSE|CONDUIT|NIPPLE|COUPLING|ADAPTER|UNION|ELBOW|FITTING|CONNECTOR|CABLE|\bWIRE\b|WIRING|HARNESS|CORD|\bLEAD\b/.test(t)) return 'tube';
    if(/GROMMET|\bBAND\b|\bBELT\b|\bRING\b/.test(t)) return 'oring';
    // shafts / pins / round bar (LAMP/BULB/CAP bounded so they don't catch CLAMP, CAPSCREW, etc.)
    if(/\bPIN\b|DOWEL|\bSHAFT\b|\bROD\b|SPACER|SLEEVE|BUSHING|ROLLER|\bKEY\b|WEDGE|COTTER|\bPLUG\b|\bCAP\b|\bCOCK\b|\bLAMP\b|\bBULB\b|\bFUSE\b|STANDOFF/.test(t)) return 'shaft';
    // brackets / clamps / structural hardware
    if(/BRACKET|MOUNT|\bCLAMP\b|SUPPORT|\bANGLE\b|TERMINAL|\bLUG\b|CONTACT|RETAINER|\bCLIP\b|HINGE|LATCH|STRIKE|\bCATCH\b|\bHASP\b|\bHOOK\b/.test(t)) return 'bracket';
    // flat plates / markers / labels
    if(/PLATE|MARKER|DECAL|LABEL|PLACARD|NAMEPLATE|\bTAG\b|IDENTIFICATION|ARMOR|ARMOUR|\bBUS\b|\bBAR\b/.test(t)) return 'plate';
    if(/BATTERY/.test(t)) return 'battery';
    return 'box';
  }

  // NSN Federal Supply Class (first 4 digits) -> shape, for parts whose NAME is missing/generic/unclassifiable.
  // The NSN is authoritative about the commodity, so it recovers a shape when the nomenclature can't. (v0.84.1)
  var FSC_MAP = {
    '5305':'bolt','5306':'bolt','5307':'bolt','5315':'shaft','5320':'rivet','5310':'nut','5311':'nut',
    '5325':'bracket','5330':'gasket','5331':'oring','5340':'bracket','5342':'bracket','5345':'washer',
    '5355':'shaft','5360':'spring','5365':'shaft','5970':'pad','5975':'box','5999':'plate',
    '3110':'bearing','3120':'bearing','3130':'bearing','3020':'gear','3010':'cylinder','3040':'lever',
    '4710':'tube','4720':'tube','4730':'tube','4820':'cylinder',
    '2910':'cylinder','2915':'cylinder','2920':'cylinder','2930':'canister','2940':'canister','2990':'cover',
    '2510':'cover','2520':'cylinder','2530':'cylinder','2540':'bracket','2541':'bracket','2590':'box','2805':'cylinder',
    '5905':'shaft','5910':'shaft','5915':'shaft','5920':'shaft','5925':'switch','5930':'switch','5935':'tube',
    '5940':'bracket','5945':'switch','5950':'cylinder','5955':'shaft','5960':'shaft','5961':'shaft','5962':'plate',
    '5963':'plate','5985':'cylinder','5995':'tube','6150':'tube',
    '6210':'cover','6220':'cover','6240':'shaft','6250':'shaft','6260':'shaft',
    '4010':'tube','4030':'bracket','9905':'plate','7690':'plate','9390':'pad',
    '2610':'oring','2620':'oring','2640':'oring','4130':'canister','4140':'cylinder','4320':'cylinder','4330':'canister',
    '5120':'shaft','5130':'cylinder','5133':'shaft','5136':'shaft','5210':'shaft','1005':'tube','1010':'tube'
  };
  var FSG_MAP = {'53':'bracket','31':'bearing','30':'gear','47':'tube','48':'cylinder','29':'cylinder',
    '26':'oring','25':'box','28':'box','61':'tube','59':'tube'};
  function familyFromNSN(nsn){
    var m=(nsn||'').match(/\s*(\d{4})/); if(!m) return null;
    var fsc=m[1]; if(FSC_MAP[fsc]) return FSC_MAP[fsc];
    return FSG_MAP[fsc.slice(0,2)] || null;
  }
  // name first; if that yields a plain box, recover from the NSN's supply class.
  function classify(name, chars, nsn){
    var f=family(name, chars);
    if(f==='box' && nsn){ var g=familyFromNSN(nsn); if(g) return g; }
    return f;
  }

  var BUILDERS = {bolt:f_bolt, nut:f_nut, washer:f_washer, gasket:f_gasket, oring:f_oring,
    bearing:f_bearing, gear:f_gear, spring:f_spring, tube:f_tube, shaft:f_shaft,
    bracket:f_bracket, battery:f_battery, box:f_box,
    plate:f_plate, cover:f_cover, pad:f_pad, link:f_link, lever:f_lever, rivet:f_rivet,
    switch:f_switch, cylinder:f_cylinder, canister:f_canister};

  function build(fam, dims){
    try { var g = (BUILDERS[fam] || f_box)(dims || {});
      if(!g || !g.V || !g.V.length) return f_box(dims||{});
      return g;
    } catch(e){ return f_box(dims||{}); }
  }

  window.PartGeo = {build:build, family:family, familyFromNSN:familyFromNSN, classify:classify, BUILDERS:BUILDERS};
})();
