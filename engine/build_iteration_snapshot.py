#!/usr/bin/env python3
"""THE VIEWER -- ITERATION SNAPSHOT GENERATOR (R10). Derives the comprehensive, visual per-iteration snapshot
DIRECTLY from docs/CHANGELOG.md (+ CHANGELOG-LEGACY.md), so the snapshot MATCHES THE CHANGELOG EXACTLY by construction
(R10: no exceptions). Writes:
  * docs/ITERATION-SNAPSHOTS.md   -- detailed, tagged [FEATURE]/[UPGRADE]/[POLISH]/[FIX] per version
  * docs/ITERATION-DASHBOARD.html -- self-contained dark visual dashboard (cards, tag filters, search, diagram links)

Run (host-side or in-sandbox -- CHANGELOG.md reads fully): python build_iteration_snapshot.py
Read-only on the changelogs; writes only the two snapshot files. Additive (R1)."""
import os, re, json, html, sys

HERE = os.path.dirname(os.path.abspath(__file__))
DOCS = os.path.join(HERE, "..", "docs")
CHANGELOG = os.path.join(DOCS, "CHANGELOG.md")
LEGACY = os.path.join(DOCS, "CHANGELOG-LEGACY.md")
OUT_MD = os.path.join(DOCS, "ITERATION-SNAPSHOTS.md")
OUT_HTML = os.path.join(DOCS, "ITERATION-DASHBOARD.html")

HDR = re.compile(r"^## \[(?P<ver>[0-9.]+)\](?:-legacy)?\s*[—-]\s*(?P<date>[0-9]{4}-[0-9]{2}-[0-9]{2})\s*[—-]\s*(?P<title>.*)$")
DIAG = re.compile(r"(\d{2,3}-[a-z0-9][a-z0-9\-]*\.pdf)", re.I)


def parse_changelog(path):
    """-> list of {ver,date,title,sections:[{label,bullets:[...]}],raw,tags,diagram}"""
    if not os.path.exists(path):
        return []
    lines = open(path, encoding="utf-8").read().splitlines()
    blocks = []
    cur = None
    for ln in lines:
        m = HDR.match(ln)
        if m:
            cur = {"ver": m.group("ver"), "date": m.group("date"), "title": m.group("title").strip(), "body": []}
            blocks.append(cur)
        elif cur is not None:
            cur["body"].append(ln)
    out = []
    for b in blocks:
        sections = []
        label = None; bullets = []
        for ln in b["body"]:
            s = ln.strip()
            hm = re.match(r"^###\s+(.*)$", s)
            if hm:
                if label or bullets:
                    sections.append({"label": label, "bullets": bullets}); bullets = []
                label = re.sub(r"\s+", " ", hm.group(1)).strip()
            elif s.startswith("- ") or s.startswith("* "):
                bullets.append(s[2:].strip())
            elif s.startswith("---") or not s:
                continue
            else:
                # continuation / prose line -> attach to the last bullet or as its own
                if bullets:
                    bullets[-1] = (bullets[-1] + " " + s).strip()
                elif s:
                    bullets.append(s)
        if label or bullets:
            sections.append({"label": label, "bullets": bullets})
        raw = "\n".join(b["body"]).strip()
        diag = None
        dm = DIAG.search(raw)
        if dm:
            diag = dm.group(1)
        tags = derive_tags(b["title"], sections)
        out.append({"ver": b["ver"], "date": b["date"], "title": b["title"],
                    "sections": sections, "tags": tags, "diagram": diag})
    return out


LHDR = re.compile(r"^## \[(?P<ver>[0-9.]+)-legacy\]\s*[—-]\s*(?P<rest>.*)$")

def parse_legacy(path):
    """-> {ver_base: one-line parity summary}. Legacy headers put '-legacy' INSIDE the brackets: [0.99.15-legacy]."""
    res = {}
    if not os.path.exists(path):
        return res
    for ln in open(path, encoding="utf-8").read().splitlines():
        m = LHDR.match(ln)
        if m:
            rest = m.group("rest").strip()
            # drop a leading date if present -> keep the parity summary text
            rest = re.sub(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}\s*[—-]\s*", "", rest)
            res.setdefault(m.group("ver"), rest)
    return res


_POLISH = re.compile(r"\b(polish|qol|quality of life|accessib|discoverab|tidy|clean\s*up|cleanup|dedup|ux|wcag|a11y)\b", re.I)
_UPGRADE = re.compile(r"\b(deeper|deepen|upgrade|boost|pass\b|expand|richer|enhanc|improv|consolidat|refine|faster|speed)\b", re.I)


def derive_tags(title, sections):
    tags = set()
    labels = " ".join((s["label"] or "") for s in sections)
    hay = (title + " " + labels).lower()
    if "fixed" in hay or re.search(r"\bfix\b|\bbug\b|\bcrash\b", hay):
        tags.add("FIX")
    if "added" in hay or re.search(r"\bnew\b|\badd(ed|s)?\b", hay):
        tags.add("FEATURE")
    if "changed" in hay or _UPGRADE.search(hay):
        tags.add("UPGRADE")
    if _POLISH.search(hay):
        tags.add("POLISH")
    if not tags:
        tags.add("FEATURE")
    # order
    order = ["FEATURE", "UPGRADE", "POLISH", "FIX"]
    return [t for t in order if t in tags]


# ---------- Markdown ----------
def render_md(vers, legacy):
    L = []
    L.append("# THE VIEWER — Iteration Snapshots (R10)\n")
    L.append("_Comprehensive, tagged, per-iteration view of **every** change. Generated from `docs/CHANGELOG.md` — it "
             "matches the changelog exactly (R10). Tags: **[FEATURE] [UPGRADE] [POLISH] [FIX]**. Newest first._\n")
    L.append("_Regenerate any time: `python engine/build_iteration_snapshot.py`. Visual version: "
             "`docs/ITERATION-DASHBOARD.html`._\n")
    L.append("| # of iterations | Latest | Legacy-tracked |\n|---|---|---|")
    L.append("| %d | %s — %s | %d |\n" % (len(vers), vers[0]["ver"] if vers else "-",
             vers[0]["title"] if vers else "-", len(legacy)))
    L.append("\n---\n")
    for v in vers:
        badge = " ".join("`%s`" % t for t in v["tags"])
        L.append("## [%s] — %s — %s" % (v["ver"], v["date"], v["title"]))
        L.append("%s%s\n" % (badge, ("  ·  diagram: `%s`" % v["diagram"]) if v["diagram"] else ""))
        for sec in v["sections"]:
            if sec["label"]:
                L.append("**%s**" % sec["label"])
            for b in sec["bullets"]:
                L.append("- %s" % b)
            L.append("")
        lg = legacy.get(v["ver"])
        if lg:
            L.append("_Legacy parity: %s_\n" % lg)
        L.append("---\n")
    L.append("<!-- generated by engine/build_iteration_snapshot.py from CHANGELOG.md -->")
    L.append("# END OF FILE")
    return "\n".join(L) + "\n"


# ---------- HTML dashboard ----------
def render_html(vers, legacy):
    for v in vers:
        v["legacy"] = legacy.get(v["ver"], "")
    data = json.dumps(vers, ensure_ascii=False)
    tmpl = HTML_TMPL.replace("/*__DATA__*/", "window.__ITER__ = " + data + ";")
    tmpl = tmpl.replace("__COUNT__", str(len(vers)))
    tmpl = tmpl.replace("__LATEST__", html.escape((vers[0]["ver"] + " — " + vers[0]["title"]) if vers else "-"))
    return tmpl


HTML_TMPL = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>THE VIEWER — Iteration Dashboard</title>
<style>
  :root{--bg:#0c1116;--panel:#141c25;--panel2:#0f151c;--line:#243040;--txt:#e6edf4;--sub:#8a98a8;--acc:#4f9dff}
  *{box-sizing:border-box} html,body{margin:0;background:var(--bg);color:var(--txt);font:14px/1.5 system-ui,Segoe UI,Arial,sans-serif}
  .top{position:sticky;top:0;z-index:5;background:linear-gradient(#0c1116,#0c1116e8);backdrop-filter:blur(4px);border-bottom:1px solid var(--line);padding:16px 22px}
  h1{margin:0 0 4px;font-size:19px} .meta{color:var(--sub);font-size:12.5px}
  .controls{display:flex;gap:8px;flex-wrap:wrap;margin-top:12px;align-items:center}
  .chip{background:#16202b;border:1px solid var(--line);border-radius:999px;padding:5px 13px;font-size:12.5px;color:var(--sub);cursor:pointer;user-select:none}
  .chip.on{color:#06121f;font-weight:700}
  .chip.FEATURE.on{background:#4f9dff;border-color:#4f9dff} .chip.UPGRADE.on{background:#caa24a;border-color:#caa24a}
  .chip.POLISH.on{background:#1d9e75;border-color:#1d9e75} .chip.FIX.on{background:#e0564f;border-color:#e0564f}
  .chip.ALL.on{background:#e6edf4;border-color:#e6edf4}
  input#q{flex:1;min-width:180px;background:var(--panel2);border:1px solid var(--line);border-radius:8px;color:var(--txt);padding:8px 12px;font-size:13px}
  .wrap{max-width:1000px;margin:0 auto;padding:18px 22px 80px}
  .card{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:15px 18px;margin:12px 0}
  .card h2{margin:0;font-size:15px;display:flex;align-items:baseline;gap:10px;flex-wrap:wrap}
  .ver{color:var(--acc);font-weight:700} .date{color:var(--sub);font-size:12px;font-weight:400}
  .title{font-weight:600}
  .tags{margin:8px 0 4px;display:flex;gap:6px;flex-wrap:wrap}
  .tag{font-size:10.5px;font-weight:700;letter-spacing:.04em;border-radius:5px;padding:2px 8px}
  .tag.FEATURE{background:#12314f;color:#8fc0ff} .tag.UPGRADE{background:#3a2f14;color:#e6c878}
  .tag.POLISH{background:#123a2c;color:#7fd8b6} .tag.FIX{background:#3a1512;color:#f2a49c}
  .sec{margin:8px 0 2px} .sec .lbl{color:var(--acc);font-weight:600;font-size:12.5px;margin:6px 0 3px}
  .sec ul{margin:2px 0 6px;padding-left:18px} .sec li{margin:3px 0;color:#cdd8e4;font-size:12.8px}
  .foot{display:flex;gap:14px;flex-wrap:wrap;align-items:center;margin-top:8px;font-size:12px}
  .foot a{color:var(--acc);text-decoration:none;border:1px solid var(--line);border-radius:6px;padding:3px 9px}
  .foot a:hover{border-color:var(--acc)} .legacy{color:var(--sub)}
  .count{color:var(--sub);font-size:12px;margin:6px 0 0}
</style></head><body>
<div class="top">
  <h1>THE VIEWER — Iteration Dashboard</h1>
  <div class="meta">__COUNT__ iterations · latest <b>__LATEST__</b> · generated from CHANGELOG.md (matches it exactly — R10)</div>
  <div class="controls">
    <span class="chip ALL on" data-t="ALL">All</span>
    <span class="chip FEATURE" data-t="FEATURE">Feature</span>
    <span class="chip UPGRADE" data-t="UPGRADE">Upgrade</span>
    <span class="chip POLISH" data-t="POLISH">Polish</span>
    <span class="chip FIX" data-t="FIX">Fix</span>
    <input id="q" placeholder="search versions, titles, changes…">
  </div>
  <div class="count" id="count"></div>
</div>
<div class="wrap" id="list"></div>
<script>/*__DATA__*/</script>
<script>
(function(){
  var DATA=window.__ITER__||[], filt="ALL", q="";
  function esc(s){return String(s==null?"":s).replace(/[&<>"]/g,function(c){return{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c];});}
  function matches(v){
    if(filt!=="ALL" && v.tags.indexOf(filt)<0) return false;
    if(!q) return true;
    var hay=(v.ver+" "+v.title+" "+v.tags.join(" ")+" "+v.sections.map(function(s){return (s.label||"")+" "+s.bullets.join(" ");}).join(" ")).toLowerCase();
    return hay.indexOf(q)>=0;
  }
  function render(){
    var host=document.getElementById("list"); host.innerHTML=""; var n=0;
    DATA.forEach(function(v){
      if(!matches(v)) return; n++;
      var c=document.createElement("div"); c.className="card";
      var h='<h2><span class="ver">'+esc(v.ver)+'</span> <span class="date">'+esc(v.date)+'</span> <span class="title">'+esc(v.title)+'</span></h2>';
      h+='<div class="tags">'+v.tags.map(function(t){return '<span class="tag '+t+'">'+t+'</span>';}).join("")+'</div>';
      v.sections.forEach(function(s){
        h+='<div class="sec">'+(s.label?'<div class="lbl">'+esc(s.label)+'</div>':'');
        if(s.bullets.length){ h+='<ul>'+s.bullets.map(function(b){return '<li>'+esc(b)+'</li>';}).join("")+'</ul>'; }
        h+='</div>';
      });
      var foot='';
      if(v.diagram) foot+='<a href="diagrams/'+esc(v.diagram)+'" target="_blank">📊 diagram</a>';
      if(v.legacy) foot+='<span class="legacy">legacy: '+esc(v.legacy)+'</span>';
      if(foot) h+='<div class="foot">'+foot+'</div>';
      c.innerHTML=h; host.appendChild(c);
    });
    document.getElementById("count").textContent=n+" of "+DATA.length+" iterations shown"+(filt!=="ALL"?(" · "+filt):"")+(q?(" · matching “"+q+"”"):"");
  }
  document.querySelectorAll(".chip[data-t]").forEach(function(ch){ ch.onclick=function(){
    filt=ch.getAttribute("data-t");
    document.querySelectorAll(".chip[data-t]").forEach(function(x){ x.classList.toggle("on", x===ch); });
    render();
  };});
  document.getElementById("q").addEventListener("input",function(e){ q=e.target.value.trim().toLowerCase(); render(); });
  render();
})();
</script>
</body></html>"""


def main():
    vers = parse_changelog(CHANGELOG)
    legacy = parse_legacy(LEGACY)
    if not vers:
        print("no versions parsed from", CHANGELOG); return 1
    open(OUT_MD, "w", encoding="utf-8").write(render_md(vers, legacy))
    open(OUT_HTML, "w", encoding="utf-8").write(render_html(vers, legacy))
    # integrity: every changelog version must appear in the snapshot (R10 -- match exactly)
    md = open(OUT_MD, encoding="utf-8").read()
    missing = [v["ver"] for v in vers if ("[%s]" % v["ver"]) not in md]
    print("iterations: %d | legacy: %d | latest: %s" % (len(vers), len(legacy), vers[0]["ver"]))
    print("wrote", OUT_MD)
    print("wrote", OUT_HTML)
    if missing:
        print("R10 INTEGRITY FAIL -- versions missing from snapshot:", missing); return 1
    print("R10 integrity OK -- all", len(vers), "changelog versions present in the snapshot.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
# END OF FILE
