/* THE VIEWER — circuitsim.js : a tiny dependency-free analog circuit engine (Modified Nodal Analysis).
   No SPICE, no library, fully offline. Solves a netlist for DC operating point and transient response;
   used by the Circuit Lab learning overlay. Backward-Euler companion models for C/L; Newton-Raphson
   for diodes & MOSFETs; behavioral relays; time-varying AC sources; ideal op-amp (high-gain VCVS).
   Works as a browser global (window.CircuitSim) and as a Node module (for unit tests).

   Netlist element: {type, name, n:[...], value, ...}.  Node 0 = ground.
   Types: 'V' (DC volts), 'VAC' (amp,freq,phase volts), 'R' (ohms), 'C' (farads), 'L' (henries),
          'I' (amps), 'D'/'LED' (diode {Is,Vt,Vf}), 'SW' {closed}, 'NMOS' n:[d,g,s] {Vth,K,lambda},
          'OPAMP' n:[inp,inn,out] {gain}, 'RELAY' n:[coilA,coilB,com,no] {Rcoil,pickup,dropout}.
   API: const c=new Circuit(elements); c.dc(); c.step(dt); c.v(node); c.i(name); c.t (sim time). */
(function(global){
  function solve(A, z){            // Gaussian elimination with partial pivoting; returns x for A x = z
    const n = z.length;
    for(let i=0;i<n;i++){
      let p=i; for(let r=i+1;r<n;r++) if(Math.abs(A[r][i])>Math.abs(A[p][i])) p=r;
      if(p!==i){ const t=A[p];A[p]=A[i];A[i]=t; const tz=z[p];z[p]=z[i];z[i]=tz; }
      const piv=A[i][i]; if(Math.abs(piv)<1e-18) continue;
      for(let r=0;r<n;r++){ if(r===i) continue; const f=A[r][i]/piv; if(!f) continue;
        for(let cc=i;cc<n;cc++) A[r][cc]-=f*A[i][cc]; z[r]-=f*z[i]; }
    }
    const x=new Array(n); for(let i=0;i<n;i++) x[i]=Math.abs(A[i][i])<1e-18?0:z[i]/A[i][i]; return x;
  }
  const VSRC=function(e){ return e.type==='V'||e.type==='VAC'||e.type==='L'||e.type==='OPAMP'; };
  function Circuit(elements){
    this.el = elements.map(e=>Object.assign({}, e));
    let maxNode=0; this.el.forEach(e=>e.n.forEach(nd=>{ if(nd>maxNode) maxNode=nd; }));
    this.N = maxNode;
    this.vsrc = this.el.filter(VSRC);
    this.M = this.vsrc.length;
    this.vsrc.forEach((e,i)=>{ e._k = this.N + i; });   // current-unknown row index (0-based incl. nodes)
    this.el.forEach(e=>{ e._iprev=0; e._vprev=0; e._I=0; e._vd=undefined;
      if(e.type==='RELAY') e._closed = !!e.closed0; });
    this.x = new Array(this.N + this.M).fill(0);
    this.t = 0;
  }
  Circuit.prototype.v = function(node){ return node===0?0:(this.x[node-1]||0); };
  Circuit.prototype._g = function(A,a,b,g){
    if(a>0){A[a-1][a-1]+=g;} if(b>0){A[b-1][b-1]+=g;} if(a>0&&b>0){A[a-1][b-1]-=g;A[b-1][a-1]-=g;}
  };
  Circuit.prototype._isrc = function(z,a,b,I){ if(a>0)z[a-1]-=I; if(b>0)z[b-1]+=I; }; // current a->b
  // transconductance gm: current a->b controlled by (cp - cn)
  Circuit.prototype._gm = function(A,a,b,cp,cn,gm){
    if(a>0&&cp>0)A[a-1][cp-1]+=gm; if(a>0&&cn>0)A[a-1][cn-1]-=gm;
    if(b>0&&cp>0)A[b-1][cp-1]-=gm; if(b>0&&cn>0)A[b-1][cn-1]+=gm;
  };
  Circuit.prototype._stampDiode = function(A,z,e){          // linearized companion w/ SPICE-style limiting
    const a=e.n[0], b=e.n[1], Is=e.Is||1e-12, Vt=e.Vt||0.02585, Vf=e.Vf||0;
    let vd=this.v(a)-this.v(b)-Vf;
    const vold=(e._vd===undefined?0:e._vd);
    const vcrit=Vt*Math.log(Vt/(Math.SQRT2*Is));
    if(vd>vcrit && Math.abs(vd-vold)>2*Vt){
      if(vold>0){ const arg=1+(vd-vold)/Vt; vd = arg>0 ? vold+Vt*Math.log(arg) : vcrit; }
      else vd = (vd>0 ? Vt*Math.log(Math.max(vd,1e-12)/Vt) : vd);
    }
    e._vd=vd;
    const ex=Math.exp(Math.min(vd/Vt,80)), Id=Is*(ex-1), Gd=Is/Vt*ex+1e-12, Ieq=Id-Gd*vd;
    this._g(A,a,b,Gd); this._isrc(z,a,b,Ieq); e._I=Id;
  };
  Circuit.prototype._stampNMOS = function(A,z,e){           // square-law level-1 N-channel MOSFET
    const d=e.n[0], g=e.n[1], s=e.n[2], Vth=(e.Vth==null?2:e.Vth), K=(e.K==null?0.02:e.K), lam=e.lambda||0;
    let vgs=this.v(g)-this.v(s), vds=this.v(d)-this.v(s);
    let Ids,gm,gds;
    if(vgs<=Vth){ Ids=0; gm=0; gds=1e-12; }                 // cutoff
    else if(vds < (vgs-Vth)){ const ov=vgs-Vth;             // triode
      Ids=K*(2*ov*vds - vds*vds); gm=2*K*vds; gds=2*K*(ov-vds)+1e-12; }
    else { const ov=vgs-Vth;                                // saturation
      Ids=K*ov*ov*(1+lam*vds); gm=2*K*ov*(1+lam*vds); gds=K*ov*ov*lam+1e-12; }
    const Ieq=Ids - gm*vgs - gds*vds;
    this._g(A,d,s,gds); this._gm(A,d,s,g,s,gm); this._isrc(z,d,s,Ieq); e._I=Ids;
  };
  Circuit.prototype._build = function(dt){
    const n=this.N+this.M, A=[],z=new Array(n).fill(0);
    for(let i=0;i<n;i++){ A.push(new Array(n).fill(0)); }
    const self=this;
    this.el.forEach(function(e){
      const a=e.n[0], b=e.n[1];
      if(e.type==='R'){ self._g(A,a,b,1/(e.value||1e-9)); }
      else if(e.type==='SW'){ self._g(A,a,b, e.closed?1/0.001:1e-9); }
      else if(e.type==='I'){ self._isrc(z,a,b,e.value||0); }
      else if(e.type==='C'){ const g=dt>0?(e.value/dt):0; self._g(A,a,b,g); self._isrc(z,a,b,-g*e._vprev); }
      else if(e.type==='D'||e.type==='LED'){ self._stampDiode(A,z,e); }
      else if(e.type==='NMOS'){ self._stampNMOS(A,z,e); }
      else if(e.type==='V'){ const k=e._k; if(a>0){A[a-1][k]+=1;A[k][a-1]+=1;} if(b>0){A[b-1][k]-=1;A[k][b-1]-=1;} z[k]+=e.value; }
      else if(e.type==='VAC'){ const k=e._k; if(a>0){A[a-1][k]+=1;A[k][a-1]+=1;} if(b>0){A[b-1][k]-=1;A[k][b-1]-=1;}
        z[k]+= (e.value||0)*Math.sin(2*Math.PI*(e.freq||1)*self.t + (e.phase||0)); }
      else if(e.type==='L'){ const k=e._k, Req=dt>0?(e.value/dt):0;
        if(a>0){A[a-1][k]+=1;A[k][a-1]+=1;} if(b>0){A[b-1][k]-=1;A[k][b-1]-=1;} A[k][k]-=Req; z[k]-= Req*e._iprev; }
      else if(e.type==='OPAMP'){ const k=e._k, inp=e.n[0], inn=e.n[1], out=e.n[2], Gain=e.gain||1e5;
        if(out>0){A[out-1][k]+=1;A[k][out-1]+=1;}            // output branch out->gnd carries current i_k
        if(inp>0)A[k][inp-1]-=Gain; if(inn>0)A[k][inn-1]+=Gain; } // v(out) - Gain*(v(inp)-v(inn)) = 0
      else if(e.type==='RELAY'){ const cA=e.n[0], cB=e.n[1], com=e.n[2], no=e.n[3];
        self._g(A,cA,cB, 1/(e.Rcoil||120));                 // coil
        self._g(A,com,no, e._closed?1/0.01:1e-9); }         // contact
    });
    return {A,z};
  };
  Circuit.prototype._updateRelays = function(){             // discrete contact state from coil current
    let changed=false; const self=this;
    this.el.forEach(function(e){ if(e.type!=='RELAY') return;
      const i=Math.abs((self.v(e.n[0])-self.v(e.n[1]))/(e.Rcoil||120));
      const pick=e.pickup||0.02, drop=e.dropout||0.01;
      const ns = e._closed ? (i>drop) : (i>pick);
      if(ns!==e._closed){ e._closed=ns; changed=true; } e._I=i; });
    return changed;
  };
  Circuit.prototype._solveOnce = function(dt){
    const hasNL = this.el.some(e=>e.type==='D'||e.type==='LED'||e.type==='NMOS');
    const hasRelay = this.el.some(e=>e.type==='RELAY');
    let last=this.x.slice();
    const iters = (hasNL||hasRelay)?60:1;
    for(let it=0; it<iters; it++){
      const m=this._build(dt); this.x=solve(m.A,m.z);
      const relayChanged = hasRelay ? this._updateRelays() : false;
      if(!hasNL){ if(!relayChanged) break; else continue; }
      let d=0; for(let i=0;i<this.x.length;i++) d=Math.max(d,Math.abs(this.x[i]-last[i]));
      last=this.x.slice(); if(d<1e-7 && !relayChanged) break;
    }
    const self=this;
    this.el.forEach(function(e){ const a=e.n[0], b=e.n[1];
      if(e.type==='V'||e.type==='VAC'||e.type==='L'||e.type==='OPAMP'){ e._I=self.x[e._k]; }
      else if(e.type==='R'){ e._I=(self.v(a)-self.v(b))/(e.value||1e-9); }
      else if(e.type==='C'){ const g=dt>0?(e.value/dt):0; e._I=g*((self.v(a)-self.v(b))-e._vprev); }
      else if(e.type==='SW'){ e._I=(self.v(a)-self.v(b))/(e.closed?0.001:1e9); }
    });
  };
  Circuit.prototype.dc = function(){ this._solveOnce(0); this._commit(0); return this; };
  Circuit.prototype.step = function(dt){ this.t += dt; this._solveOnce(dt); this._commit(dt); return this; };
  Circuit.prototype._commit = function(dt){ const self=this;
    this.el.forEach(function(e){ if(e.type==='C'){ e._vprev=self.v(e.n[0])-self.v(e.n[1]); }
      else if(e.type==='L'){ e._iprev=e._I; } }); };
  Circuit.prototype.i = function(name){ const e=this.el.find(x=>x.name===name); return e?e._I:0; };
  Circuit.prototype.state = function(name){ const e=this.el.find(x=>x.name===name); return e?{closed:e._closed}:null; };

  const API={Circuit, solve};
  if(typeof module!=='undefined'&&module.exports) module.exports=API;
  if(global) global.CircuitSim=API;
})(typeof window!=='undefined'?window:null);
