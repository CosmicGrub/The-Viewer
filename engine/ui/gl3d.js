/* THE VIEWER — gl3d.js : dependency-free WebGL viewer for the representative 3D shapes.
   No Three.js, no CDN — fully offline. Glossy multi-light shading (key + fill + rim/fresnel),
   antialiasing, smooth rounded surfaces for round families, an idle turntable spin, orbit + zoom.
   Same geometry we derive from FLIS dimensions (grounded). Callers fall back to the SVG renderer
   when GL3D.supported() is false (keeps Win7/Vista / RPS working).
   API: GL3D.supported()->bool;  const v=GL3D.create(canvas);
        v.load({V,F}, '#rrggbb', smooth);  v.reset(); v.setColor(hex); v.spin(bool); */
window.GL3D = (function(){
  function compile(gl,type,src){const s=gl.createShader(type);gl.shaderSource(s,src);gl.compileShader(s);if(!gl.getShaderParameter(s,gl.COMPILE_STATUS))throw new Error(gl.getShaderInfoLog(s));return s;}
  function program(gl,vs,fs){const p=gl.createProgram();gl.attachShader(p,compile(gl,gl.VERTEX_SHADER,vs));gl.attachShader(p,compile(gl,gl.FRAGMENT_SHADER,fs));gl.linkProgram(p);if(!gl.getProgramParameter(p,gl.LINK_STATUS))throw new Error(gl.getProgramInfoLog(p));return p;}
  const M={
    mul:(a,b)=>{const o=new Array(16);for(let i=0;i<4;i++)for(let j=0;j<4;j++){let s=0;for(let k=0;k<4;k++)s+=a[k*4+j]*b[i*4+k];o[i*4+j]=s;}return o;},
    persp:(f,a,n,fa)=>{const t=1/Math.tan(f/2);return [t/a,0,0,0,0,t,0,0,0,0,(fa+n)/(n-fa),-1,0,0,2*fa*n/(n-fa),0];},
    rotX:c=>{const s=Math.sin(c),k=Math.cos(c);return [1,0,0,0,0,k,s,0,0,-s,k,0,0,0,0,1];},
    rotY:c=>{const s=Math.sin(c),k=Math.cos(c);return [k,0,-s,0,0,1,0,0,s,0,k,0,0,0,0,1];},
    trans:(x,y,z)=>[1,0,0,0,0,1,0,0,0,0,1,0,x,y,z,1]
  };
  function hexToRgb(h){h=(h||'#8a9099').replace('#','');if(h.length===3)h=h.split('').map(c=>c+c).join('');const n=parseInt(h,16);return [((n>>16)&255)/255,((n>>8)&255)/255,(n&255)/255];}
  function supported(){try{const c=document.createElement('canvas');return !!(window.WebGLRenderingContext&&(c.getContext('webgl')||c.getContext('experimental-webgl')));}catch(e){return false;}}
  function create(canvas){
    let gl;try{const o={antialias:true,alpha:true,premultipliedAlpha:false,depth:true};gl=canvas.getContext('webgl',o)||canvas.getContext('experimental-webgl',o);}catch(e){gl=null;}
    if(!gl) return null;
    const VS='attribute vec3 p;attribute vec3 n;uniform mat4 mvp;uniform mat3 nm;varying vec3 vn;varying vec3 vp;void main(){vn=nm*n;vp=p;gl_Position=mvp*vec4(p,1.0);}';
    // key + fill + rim(fresnel) + glossy spec → metallic "product render" pop
    // mat = [specStrength, shininess(power), metallic] -> material "texture" from the scan's stated material.
    // klass = CAD material class (0 none,1 metal,2 rubber,3 wood,4 plastic,5 painted/CARC,6 brass) ->
    // a procedural surface texture grafted from the CAD renderer so the 3-D model matches the CAD image.
    const FS=[
      'precision mediump float;varying vec3 vn;varying vec3 vp;uniform vec3 col;uniform vec3 mat;uniform float klass;',
      'float hash(vec3 p){return fract(sin(dot(p,vec3(12.9898,78.233,37.719)))*43758.5453);}',
      'float tex(vec3 p){',
      ' if(klass<0.5)return 1.0;',
      ' if(klass<1.5)return 0.94+0.06*sin(p.y*150.0);',                 // metal: fine brushed streaks
      ' if(klass<2.5)return 0.86+0.14*hash(floor(p*55.0));',            // rubber: speckled grain
      ' if(klass<3.5)return 0.84+0.16*sin(length(p.xz)*42.0);',         // wood: growth rings
      ' if(klass<4.5)return 0.96+0.04*sin(p.x*90.0);',                  // plastic: subtle
      ' if(klass<5.5)return 0.91+0.09*sin(p.x*34.0)*sin(p.y*34.0);',    // painted/CARC: orange-peel
      ' return 0.93+0.07*sin(p.y*120.0);',                             // brass: brushed
      '}',
      'void main(){',
      ' vec3 N=normalize(vn);vec3 Vd=vec3(0.0,0.0,1.0);',
      ' vec3 Lk=normalize(vec3(0.45,0.75,0.55));vec3 Lf=normalize(vec3(-0.5,-0.2,0.4));',
      ' float dk=max(dot(N,Lk),0.0);float df=max(dot(N,Lf),0.0)*0.35;',
      ' vec3 Hk=normalize(Lk+Vd);float sp=pow(max(dot(N,Hk),0.0),mat.y)*mat.x;',
      ' float rim=pow(1.0-max(dot(N,Vd),0.0),3.0)*0.5*(1.0-mat.z*0.55);',  // metals: less plastic rim
      ' float amb=0.30;float tx=tex(vp);vec3 alb=col*tx;',  // CAD material texture modulates the albedo
      ' vec3 spec=mix(vec3(sp),col*sp*1.7,mat.z);',  // metals tint the highlight with their own colour
      ' vec3 c=alb*(amb+0.85*dk+df)+spec+vec3(0.45,0.55,0.75)*rim;',
      ' c=c/(c+vec3(0.6))*1.35;', // soft tonemap for a punchy look
      ' gl_FragColor=vec4(c,1.0);',
      '}'
    ].join('');
    let prog;try{prog=program(gl,VS,FS);}catch(e){return null;}
    const a_p=gl.getAttribLocation(prog,'p'),a_n=gl.getAttribLocation(prog,'n');
    const u_mvp=gl.getUniformLocation(prog,'mvp'),u_nm=gl.getUniformLocation(prog,'nm'),u_col=gl.getUniformLocation(prog,'col');
    const u_mat=gl.getUniformLocation(prog,'mat');
    const u_klass=gl.getUniformLocation(prog,'klass');
    const buf=gl.createBuffer();
    let count=0,color=[0.54,0.58,0.62];
    let material=[0.55,48.0,0.0];   // [specStrength, shininess, metallic] — default = the original look
    let klass=0.0;                  // CAD material class for the procedural texture
    const st={rx:-0.5,ry:0.6,dist:3.0};
    let autospin=true, idleT=0, raf=0;
    gl.enable(gl.DEPTH_TEST);

    function load(geom,hex,smooth,mat,kls){
      if(hex)color=hexToRgb(hex);
      if(mat&&mat.length===3)material=[mat[0],mat[1],mat[2]];
      if(kls!==undefined&&kls!==null)klass=+kls||0;
      const V=geom.V,F=geom.F;
      let mn=[1e9,1e9,1e9],mx=[-1e9,-1e9,-1e9];
      V.forEach(v=>{for(let i=0;i<3;i++){if(v[i]<mn[i])mn[i]=v[i];if(v[i]>mx[i])mx[i]=v[i];}});
      const c=[(mn[0]+mx[0])/2,(mn[1]+mx[1])/2,(mn[2]+mx[2])/2];
      const span=Math.max(mx[0]-mn[0],mx[1]-mn[1],mx[2]-mn[2])||1, sc=2.0/span;
      // smooth shading: averaged per-position normals (round families); else flat per-face.
      let vNorm=null;
      if(smooth){
        const key=v=>v[0].toFixed(3)+','+v[1].toFixed(3)+','+v[2].toFixed(3);
        const acc={};
        F.forEach(f=>{if(f.length<3)return;const a=V[f[0]],b=V[f[1]],cc=V[f[2]];
          const ux=b[0]-a[0],uy=b[1]-a[1],uz=b[2]-a[2],wx=cc[0]-a[0],wy=cc[1]-a[1],wz=cc[2]-a[2];
          let nx=uy*wz-uz*wy,ny=uz*wx-ux*wz,nz=ux*wy-uy*wx;const ln=Math.sqrt(nx*nx+ny*ny+nz*nz)||1;nx/=ln;ny/=ln;nz/=ln;
          f.forEach(idx=>{const k=key(V[idx]);(acc[k]=acc[k]||[0,0,0]);acc[k][0]+=nx;acc[k][1]+=ny;acc[k][2]+=nz;});});
        vNorm=idx=>{const n=acc[key(V[idx])];const l=Math.sqrt(n[0]*n[0]+n[1]*n[1]+n[2]*n[2])||1;return [n[0]/l,n[1]/l,n[2]/l];};
      }
      const data=[];
      F.forEach(f=>{
        if(f.length<3)return;
        const a=V[f[0]],b=V[f[1]],cc=V[f[2]];
        const ux=b[0]-a[0],uy=b[1]-a[1],uz=b[2]-a[2],wx=cc[0]-a[0],wy=cc[1]-a[1],wz=cc[2]-a[2];
        let fnx=uy*wz-uz*wy,fny=uz*wx-ux*wz,fnz=ux*wy-uy*wx;const ln=Math.sqrt(fnx*fnx+fny*fny+fnz*fnz)||1;fnx/=ln;fny/=ln;fnz/=ln;
        for(let i=1;i<f.length-1;i++){
          [f[0],f[i],f[i+1]].forEach(idx=>{const v=V[idx];const nrm=vNorm?vNorm(idx):[fnx,fny,fnz];
            data.push((v[0]-c[0])*sc,(v[1]-c[1])*sc,(v[2]-c[2])*sc, nrm[0],nrm[1],nrm[2]);});
        }
      });
      count=data.length/6;
      gl.bindBuffer(gl.ARRAY_BUFFER,buf);gl.bufferData(gl.ARRAY_BUFFER,new Float32Array(data),gl.STATIC_DRAW);
      autospin=true; loop();
    }
    function frame(){
      const dpr=Math.min(window.devicePixelRatio||1,2);
      const w=Math.max(1,Math.round((canvas.clientWidth||300)*dpr)),h=Math.max(1,Math.round((canvas.clientHeight||300)*dpr));
      if(canvas.width!==w||canvas.height!==h){canvas.width=w;canvas.height=h;}
      gl.viewport(0,0,canvas.width,canvas.height);
      gl.clearColor(0,0,0,0);gl.clear(gl.COLOR_BUFFER_BIT|gl.DEPTH_BUFFER_BIT);
      if(!count)return;
      gl.useProgram(prog);
      const model=M.mul(M.rotX(st.rx),M.rotY(st.ry));
      const view=M.trans(0,0,-st.dist);
      const proj=M.persp(0.9,canvas.width/canvas.height,0.1,100);
      const mvp=M.mul(proj,M.mul(view,model));
      const nm=[model[0],model[1],model[2],model[4],model[5],model[6],model[8],model[9],model[10]];
      gl.uniformMatrix4fv(u_mvp,false,new Float32Array(mvp));
      gl.uniformMatrix3fv(u_nm,false,new Float32Array(nm));
      gl.uniform3fv(u_col,new Float32Array(color));
      if(u_mat)gl.uniform3fv(u_mat,new Float32Array(material));
      if(u_klass)gl.uniform1f(u_klass,klass);
      gl.bindBuffer(gl.ARRAY_BUFFER,buf);
      gl.enableVertexAttribArray(a_p);gl.vertexAttribPointer(a_p,3,gl.FLOAT,false,24,0);
      gl.enableVertexAttribArray(a_n);gl.vertexAttribPointer(a_n,3,gl.FLOAT,false,24,12);
      gl.drawArrays(gl.TRIANGLES,0,count);
    }
    function loop(){
      cancelAnimationFrame(raf);
      const step=()=>{ if(autospin){ st.ry+=0.006; } frame();
        if(autospin || performance.now()<idleT){ raf=requestAnimationFrame(step); } };
      raf=requestAnimationFrame(step);
    }
    function kick(){ idleT=performance.now()+250; loop(); } // ensure a frame after interaction
    let drag=false,px=0,py=0,idleTimer=0;
    function pause(){ autospin=false; clearTimeout(idleTimer); }
    function resumeSoon(){ clearTimeout(idleTimer); idleTimer=setTimeout(()=>{ autospin=true; loop(); }, 2600); }
    canvas.addEventListener('mousedown',e=>{drag=true;px=e.clientX;py=e.clientY;canvas.style.cursor='grabbing';pause();});
    window.addEventListener('mousemove',e=>{if(!drag||!canvas.isConnected)return;st.ry+=(e.clientX-px)*0.01;st.rx+=(e.clientY-py)*0.01;px=e.clientX;py=e.clientY;kick();});
    window.addEventListener('mouseup',()=>{if(drag){drag=false;canvas.style.cursor='grab';resumeSoon();}});
    canvas.addEventListener('wheel',e=>{e.preventDefault();st.dist*=(e.deltaY<0?0.9:1.11);st.dist=Math.max(1.4,Math.min(9,st.dist));pause();kick();resumeSoon();},{passive:false});
    canvas.addEventListener('dblclick',()=>reset());
    function reset(){st.rx=-0.5;st.ry=0.6;st.dist=3.0;autospin=true;loop();}
    function setColor(hex){color=hexToRgb(hex);kick();}
    function setMaterial(m){if(m&&m.length===3){material=[m[0],m[1],m[2]];kick();}}
    function setKlass(k){klass=+k||0;kick();}
    function spin(b){autospin=!!b;loop();}
    canvas.style.cursor='grab';
    return {load,reset,setColor,setMaterial,setKlass,spin,draw:kick};
  }
  return {create,supported};
})();
