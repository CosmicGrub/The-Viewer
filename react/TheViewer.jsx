import { useState, useEffect, useRef, useMemo } from "react";
import { Search, Box, RotateCw, Image as ImageIcon, FileText, Wrench, User, ChevronRight, Layers, Zap } from "lucide-react";

/* THE VIEWER — React/JSX rendition of the signature UI.
   The real app is vanilla HTML/JS (ES5-safe for the legacy/RPS tier); this is a single-file React
   demonstration of the same interface: search + side chooser + the CAD-first 3-D library with live
   rotating CAD / 3-D tabs (a 2-D canvas renderer that mirrors cad_render.py / gl3d.js conceptually). */

const PARTS = [
  { nsn: "3110-00-100-0001", name: "BEARING, BALL", fam: "bearing", color: "#9aa6b2", klass: "metal",
    chars: "OUTSIDE DIAMETER 52 MM; INSIDE DIAMETER 25 MM; WIDTH 15 MM", side: "Mechanic",
    vehicles: ["M1151", "M1165"], maker: "CAGEC 1ABC1", tm: "TM 9-2320-387-24P, Fig 142" },
  { nsn: "5305-00-100-0002", name: "BOLT, MACHINE", fam: "bolt", color: "#6b7280", klass: "metal",
    chars: "THREAD 0.50 IN; LENGTH 3.0 IN; HEX HEAD", side: "Mechanic",
    vehicles: ["M1151", "M1097", "M998"], maker: "CAGEC 96906", tm: "TM 9-2320-280-24P, Fig 18" },
  { nsn: "3020-00-100-0003", name: "GEAR, SPUR", fam: "gear", color: "#8b94a0", klass: "metal",
    chars: "OUTSIDE DIAMETER 4.0 IN; FACE WIDTH 0.75 IN; 24 TEETH", side: "Mechanic",
    vehicles: ["M1151"], maker: "CAGEC 19207", tm: "TM 9-2520-272-34P, Fig 7" },
  { nsn: "5340-00-100-0010", name: "BRACKET, MOUNTING", fam: "bracket", color: "#5f6b3a", klass: "painted",
    chars: "LENGTH 5.0 IN; WIDTH 3.0 IN; HEIGHT 1.0 IN; COLOR OLIVE DRAB", side: "Mechanic",
    vehicles: ["M1151", "M1165"], maker: "CAGEC 81337", tm: "TM 9-2320-387-24P, Fig 91" },
  { nsn: "5330-00-100-0004", name: "GASKET", fam: "gasket", color: "#2f2f33", klass: "rubber",
    chars: "OUTSIDE DIAMETER 3.0 IN; INSIDE DIAMETER 2.2 IN; THICKNESS 0.10 IN; RUBBER", side: "Operator",
    vehicles: ["M1097"], maker: "CAGEC 24617", tm: "TM 9-2320-280-10, Fig 4" },
  { nsn: "3120-00-100-0005", name: "BUSHING, SLEEVE", fam: "bushing", color: "#aeb6c0", klass: "metal",
    chars: "OUTSIDE DIAMETER 1.5 IN; INSIDE DIAMETER 1.0 IN; LENGTH 2.0 IN", side: "Mechanic",
    vehicles: ["M998", "M1097"], maker: "CAGEC 1ABC1", tm: "TM 9-2320-280-24P, Fig 33" },
];

const TABS = [
  { id: "cad", label: "CAD image", icon: ImageIcon },
  { id: "spin", label: "Rotate CAD", icon: RotateCw },
  { id: "3d", label: "Interactive 3-D", icon: Box },
  { id: "fig", label: "Manual illustration", icon: FileText },
];

/* ---------- geometry (mirrors the partgeo/cad_render shape families) ---------- */
function buildGeom(fam) {
  const V = [], F = [];
  const TAU = Math.PI * 2;
  const push = (x, y, z) => (V.push([x, y, z]), V.length - 1);
  if (fam === "bracket") {
    const w = 1.2, h = 0.35, d = 0.7;
    const c = [[-w, -h, -d], [w, -h, -d], [w, h, -d], [-w, h, -d], [-w, -h, d], [w, -h, d], [w, h, d], [-w, h, d]];
    c.forEach(p => push(...p));
    F.push([0, 1, 2, 3], [4, 7, 6, 5], [0, 4, 5, 1], [2, 6, 7, 3], [0, 3, 7, 4], [1, 5, 6, 2]);
    return { V, F };
  }
  if (fam === "gear") {
    const n = 14, R = 1.0, td = 0.22, hh = 0.32, y0 = -hh, y1 = hh;
    for (let i = 0; i < n; i++) {
      const a0 = i / n * TAU, a1 = (i + 0.5) / n * TAU, rr = R - td;
      [[a0, rr], [a0 + 0.12 / n * TAU, R], [a1 - 0.12 / n * TAU, R], [a1, rr]].forEach(([a, r]) => {
        push(Math.cos(a) * r, y0, Math.sin(a) * r); push(Math.cos(a) * r, y1, Math.sin(a) * r);
      });
    }
    const ppt = n * 4;
    for (let i = 0; i < ppt; i++) { const j = (i + 1) % ppt; F.push([i * 2, j * 2, j * 2 + 1, i * 2 + 1]); }
    const tc = push(0, y1, 0); for (let i = 0; i < ppt; i++) { const j = (i + 1) % ppt; F.push([tc, i * 2 + 1, j * 2 + 1]); }
    const bc = push(0, y0, 0); for (let i = 0; i < ppt; i++) { const j = (i + 1) % ppt; F.push([bc, j * 2, i * 2]); }
    return { V, F };
  }
  // cylinder-ish: bearing / bushing / bolt
  const seg = 30;
  let rB = 1.0, rT = 1.0, h = 0.6;
  if (fam === "bushing") { rB = rT = 0.7; h = 1.1; }
  if (fam === "bolt") { rB = rT = 0.45; h = 1.5; }
  const y0 = -h, y1 = h;
  for (let i = 0; i < seg; i++) { const a = i / seg * TAU, c = Math.cos(a), s = Math.sin(a); push(c * rB, y0, s * rB); push(c * rT, y1, s * rT); }
  for (let i = 0; i < seg; i++) { const j = (i + 1) % seg; F.push([i * 2, j * 2, j * 2 + 1, i * 2 + 1]); }
  const tc = push(0, y1, 0); for (let i = 0; i < seg; i++) { const j = (i + 1) % seg; F.push([tc, i * 2 + 1, j * 2 + 1]); }
  const bc = push(0, y0, 0); for (let i = 0; i < seg; i++) { const j = (i + 1) % seg; F.push([bc, j * 2, i * 2]); }
  if (fam === "bolt") { // hex head on top
    const hr = 0.8, hy = y1, hy2 = y1 + 0.5, base = V.length;
    for (let i = 0; i < 6; i++) { const a = (i + 0.5) / 6 * TAU, c = Math.cos(a), s = Math.sin(a); push(c * hr, hy, s * hr); push(c * hr, hy2, s * hr); }
    for (let i = 0; i < 6; i++) { const j = (i + 1) % 6; F.push([base + i * 2, base + j * 2, base + j * 2 + 1, base + i * 2 + 1]); }
    const hc = push(0, hy2, 0); for (let i = 0; i < 6; i++) { const j = (i + 1) % 6; F.push([hc, base + i * 2 + 1, base + j * 2 + 1]); }
  }
  return { V, F };
}

function hexToRgb(h) { const n = parseInt(h.slice(1), 16); return [(n >> 16) & 255, (n >> 8) & 255, n & 255]; }

function PartCanvas({ fam, color, klass, mode }) {
  const ref = useRef(null);
  const drag = useRef({ on: false, x: 0, ry: 0.6, rx: -0.5, auto: true });
  const geom = useMemo(() => buildGeom(fam), [fam]);
  useEffect(() => {
    const cv = ref.current; if (!cv) return; const ctx = cv.getContext("2d");
    let raf, t0 = performance.now();
    const base = mode === "spin" ? [154, 166, 178] : hexToRgb(color); // Rotate CAD = neutral machined steel
    const klassId = mode === "spin" ? 0 : ({ metal: 1, rubber: 2, wood: 3, plastic: 4, painted: 5 }[klass] || 0);
    function tex(i) { // procedural material modulation (evokes the gl3d klass texture)
      if (!klassId) return 1;
      if (klassId === 1) return 0.94 + 0.06 * Math.sin(i * 12.9);
      if (klassId === 2) return 0.84 + 0.16 * ((Math.sin(i * 91.3) * 4375) % 1 + 1) % 1;
      if (klassId === 5) return 0.9 + 0.1 * Math.sin(i * 4.0) * Math.sin(i * 2.3);
      return 0.97 + 0.03 * Math.sin(i * 9.0);
    }
    function frame(now) {
      const dt = (now - t0) / 1000; t0 = now;
      const d = drag.current; if (d.auto && !d.on) d.ry += dt * 0.6;
      const W = cv.width, H = cv.height; ctx.clearRect(0, 0, W, H);
      const cy = Math.cos(d.ry), sy = Math.sin(d.ry), cx = Math.cos(d.rx), sx = Math.sin(d.rx);
      const P = geom.V.map(v => { const x = v[0], y = v[1], z = v[2];
        const x1 = x * cy + z * sy, z1 = -x * sy + z * cy, y1 = y * cx - z1 * sx, z2 = y * sx + z1 * cx; return [x1, y1, z2]; });
      let mnx = 1e9, mxx = -1e9, mny = 1e9, mxy = -1e9;
      P.forEach(p => { mnx = Math.min(mnx, p[0]); mxx = Math.max(mxx, p[0]); mny = Math.min(mny, p[1]); mxy = Math.max(mxy, p[1]); });
      const span = Math.max(mxx - mnx, mxy - mny) || 1, sc = Math.min(W, H) * 0.62 / span;
      const sp = p => [W / 2 + (p[0] - (mnx + mxx) / 2) * sc, H * 0.52 + (p[1] - (mny + mxy) / 2) * sc];
      const L = [0.4, 0.82, 0.42], Lf = [-0.55, 0.18, 0.62];
      const faces = geom.F.map((f, fi) => {
        const a = P[f[0]], b = P[f[1]], c = P[f[2]];
        const ux = b[0] - a[0], uy = b[1] - a[1], uz = b[2] - a[2], vx = c[0] - a[0], vy = c[1] - a[1], vz = c[2] - a[2];
        let nx = uy * vz - uz * vy, ny = uz * vx - ux * vz, nz = ux * vy - uy * vx;
        const nl = Math.hypot(nx, ny, nz) || 1; nx /= nl; ny /= nl; nz /= nl;
        const dk = Math.max(0, nx * L[0] + ny * L[1] + nz * L[2]), df = Math.max(0, nx * Lf[0] + ny * Lf[1] + nz * Lf[2]);
        const zc = f.reduce((s, i) => s + P[i][2], 0) / f.length;
        const br = (0.30 + 0.55 * dk + 0.16 * df) * tex(fi);
        return { f, zc, br };
      }).sort((p, q) => p.zc - q.zc);
      faces.forEach(({ f, br }) => {
        const r = Math.min(255, base[0] * br) | 0, g = Math.min(255, base[1] * br) | 0, bl = Math.min(255, base[2] * br) | 0;
        ctx.beginPath(); f.forEach((idx, k) => { const s = sp(P[idx]); k ? ctx.lineTo(s[0], s[1]) : ctx.moveTo(s[0], s[1]); });
        ctx.closePath(); ctx.fillStyle = `rgb(${r},${g},${bl})`;
        ctx.strokeStyle = `rgba(${r * 0.7 | 0},${g * 0.7 | 0},${bl * 0.7 | 0},1)`; ctx.lineWidth = 1; ctx.fill(); ctx.stroke();
      });
      raf = requestAnimationFrame(frame);
    }
    raf = requestAnimationFrame(frame);
    const down = e => { drag.current.on = true; drag.current.x = e.clientX; drag.current.y = e.clientY; };
    const move = e => { const d = drag.current; if (!d.on) return; d.ry += (e.clientX - d.x) * 0.01; d.rx += (e.clientY - d.y) * 0.01; d.x = e.clientX; d.y = e.clientY; };
    const up = () => (drag.current.on = false);
    cv.addEventListener("mousedown", down); window.addEventListener("mousemove", move); window.addEventListener("mouseup", up);
    return () => { cancelAnimationFrame(raf); cv.removeEventListener("mousedown", down); window.removeEventListener("mousemove", move); window.removeEventListener("mouseup", up); };
  }, [geom, color, klass, mode]);
  return <canvas ref={ref} width={360} height={300} className="w-full h-full cursor-grab active:cursor-grabbing" />;
}

function PartStage({ part, tab }) {
  if (tab === "fig")
    return (
      <div className="w-full h-full flex flex-col items-center justify-center bg-white rounded-lg text-slate-500 text-sm gap-2">
        <FileText size={40} className="text-slate-400" />
        <div className="font-mono text-xs">{part.tm}</div>
        <div className="text-xs">Cited manual illustration (public-domain scan)</div>
      </div>
    );
  if (tab === "cad")
    return (
      <div className="w-full h-full flex flex-col bg-slate-100 rounded-lg overflow-hidden">
        <div className="flex-1 relative"><PartCanvas fam={part.fam} color={part.color} klass={part.klass} mode="cad" /></div>
        <div className="text-slate-600 text-[11px] text-center py-1.5 border-t border-slate-200">
          Representative CAD · {part.fam} · scaled to FLIS dims · auto-CAD v7 (colour + texture)
        </div>
      </div>
    );
  // spin (flat steel) or 3d (coloured + textured) — both live canvas
  return (
    <div className="w-full h-full flex flex-col rounded-lg overflow-hidden" style={{ background: tab === "spin" ? "#dfe6ee" : "#0f1620" }}>
      <div className="flex-1 relative"><PartCanvas fam={part.fam} color={part.color} klass={part.klass} mode={tab === "spin" ? "spin" : "3d"} /></div>
      <div className={`text-[11px] text-center py-1.5 ${tab === "spin" ? "text-slate-600" : "text-slate-300"}`}>
        {tab === "spin" ? "Interactive CAD · flat technical shading (machined steel) · drag to rotate"
          : `Interactive 3-D · ${part.klass} material grafted from the CAD image · drag to rotate, scroll to zoom`}
      </div>
    </div>
  );
}

export default function TheViewer() {
  const [side, setSide] = useState("Mechanic");
  const [q, setQ] = useState("");
  const [sel, setSel] = useState(PARTS[0]);
  const [tab, setTab] = useState("cad");
  const [focus, setFocus] = useState(false);

  const results = useMemo(() => {
    const s = q.trim().toLowerCase();
    return PARTS.filter(p => (side === "Both" || p.side === side || p.side === "Operator")
      && (!s || p.name.toLowerCase().includes(s) || p.nsn.includes(s) || p.chars.toLowerCase().includes(s)));
  }, [q, side]);
  const sugg = useMemo(() => {
    const s = q.trim().toLowerCase(); if (!s) return [];
    return PARTS.filter(p => p.name.toLowerCase().includes(s) || p.nsn.includes(s)).slice(0, 5);
  }, [q]);

  useEffect(() => { setTab("cad"); }, [sel]);

  return (
    <div className="w-full min-h-[640px] bg-slate-950 text-slate-200 font-sans flex flex-col rounded-xl overflow-hidden border border-slate-800">
      {/* header */}
      <div className="flex items-center gap-3 px-4 py-3 border-b border-slate-800 bg-slate-900">
        <div className="flex items-center gap-2 text-sky-400 font-bold tracking-wide"><Layers size={20} /> THE VIEWER</div>
        <span className="text-[11px] text-slate-500 hidden sm:inline">offline TM search · 3-D library</span>
        <div className="ml-auto flex items-center gap-1 bg-slate-800 rounded-lg p-0.5 text-xs">
          {["Operator", "Mechanic"].map(s => (
            <button key={s} onClick={() => setSide(s)}
              className={`px-3 py-1 rounded-md flex items-center gap-1 ${side === s ? "bg-sky-500 text-slate-900 font-semibold" : "text-slate-300 hover:text-white"}`}>
              {s === "Operator" ? <User size={13} /> : <Wrench size={13} />}{s}
            </button>
          ))}
        </div>
      </div>

      {/* search */}
      <div className="px-4 py-3 border-b border-slate-800 relative">
        <div className="flex items-center gap-2 bg-slate-900 border border-slate-700 rounded-lg px-3 py-2">
          <Search size={16} className="text-slate-500" />
          <input value={q} onChange={e => setQ(e.target.value)} onFocus={() => setFocus(true)} onBlur={() => setTimeout(() => setFocus(false), 150)}
            placeholder="Search parts, NSN, characteristics…  (offline type-ahead)"
            className="bg-transparent outline-none text-sm w-full placeholder:text-slate-600" />
          <kbd className="text-[10px] text-slate-500 border border-slate-700 rounded px-1.5 py-0.5 hidden sm:block">Ctrl K</kbd>
        </div>
        {focus && sugg.length > 0 && (
          <div className="absolute left-4 right-4 mt-1 bg-slate-900 border border-slate-700 rounded-lg z-10 overflow-hidden shadow-xl">
            {sugg.map(p => (
              <button key={p.nsn} onMouseDown={() => { setSel(p); setQ(""); }} className="w-full text-left px-3 py-2 text-sm hover:bg-slate-800 flex items-center justify-between">
                <span>{p.name}</span><span className="font-mono text-[11px] text-slate-500">{p.nsn}</span>
              </button>
            ))}
          </div>
        )}
      </div>

      <div className="flex flex-1 min-h-0">
        {/* results list */}
        <div className="w-64 border-r border-slate-800 overflow-y-auto shrink-0">
          {results.map(p => (
            <button key={p.nsn} onClick={() => setSel(p)}
              className={`w-full text-left px-3 py-2.5 border-b border-slate-800/60 flex items-center gap-2 ${sel.nsn === p.nsn ? "bg-slate-800" : "hover:bg-slate-900"}`}>
              <span className="w-8 h-8 rounded shrink-0 border border-slate-700" style={{ background: p.color }} />
              <span className="min-w-0">
                <span className="block text-sm truncate">{p.name}</span>
                <span className="block font-mono text-[10px] text-slate-500 truncate">{p.nsn}</span>
              </span>
              <ChevronRight size={14} className="ml-auto text-slate-600 shrink-0" />
            </button>
          ))}
          {results.length === 0 && <div className="p-4 text-sm text-slate-500">No parts match.</div>}
        </div>

        {/* detail */}
        <div className="flex-1 flex flex-col min-w-0">
          <div className="px-4 pt-3 flex items-center gap-2 flex-wrap">
            <span className="font-semibold">{sel.name}</span>
            <span className="font-mono text-xs text-slate-500">{sel.nsn}</span>
            <span className="ml-auto text-[11px] px-2 py-0.5 rounded-full bg-slate-800 text-slate-300 flex items-center gap-1">
              {sel.side === "Operator" ? <User size={11} /> : <Wrench size={11} />}{sel.side}
            </span>
          </div>

          {/* tabs */}
          <div className="px-4 pt-2 flex gap-1 flex-wrap">
            {TABS.map(({ id, label, icon: Icon }) => (
              <button key={id} onClick={() => setTab(id)}
                className={`text-xs px-2.5 py-1.5 rounded-lg border flex items-center gap-1.5 ${tab === id ? "bg-sky-500 text-slate-900 border-sky-500 font-semibold" : "border-slate-700 text-slate-300 hover:bg-slate-800"}`}>
                <Icon size={13} />{label}
              </button>
            ))}
          </div>

          <div className="flex-1 grid grid-cols-1 lg:grid-cols-[1fr_260px] gap-3 p-4 min-h-0">
            <div className="min-h-[280px]"><PartStage part={sel} tab={tab} /></div>
            <div className="text-xs space-y-3 overflow-y-auto">
              <div>
                <div className="text-slate-500 uppercase tracking-wide text-[10px] mb-1">FLIS characteristics</div>
                <div className="text-slate-300 leading-relaxed">{sel.chars.split("; ").map((c, i) => <div key={i}>· {c}</div>)}</div>
              </div>
              <div>
                <div className="text-slate-500 uppercase tracking-wide text-[10px] mb-1">Cross-reference</div>
                <div className="text-slate-300">Maker {sel.maker}</div>
                <div className="text-slate-400 mt-1">Fits: {sel.vehicles.map(v => (
                  <span key={v} className="inline-block bg-slate-800 border border-slate-700 rounded px-1.5 py-0.5 mr-1 mb-1">{v}</span>))}</div>
              </div>
              <div>
                <div className="text-slate-500 uppercase tracking-wide text-[10px] mb-1">Appearance</div>
                <div className="flex items-center gap-2"><span className="w-3 h-3 rounded-sm border border-slate-600" style={{ background: sel.color }} />
                  <span className="text-slate-300">CAD material: {sel.klass}</span></div>
              </div>
              <a className="inline-flex items-center gap-1 text-sky-400 hover:text-sky-300 cursor-pointer"><Zap size={13} /> Find in manuals · {sel.tm}</a>
              <div className="text-[10px] text-slate-600 pt-2 border-t border-slate-800">
                Representative CAD approximation — not a manufacturing drawing. STL / OBJ export available.
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
