#!/usr/bin/env python3
"""CHANGELOG-VISUAL-FULL: the COMPLETE visual changelog, auto-generated from docs/CHANGELOG.md
(v0.97.0, backlog #81 — root-cause fix).

The original _make_changelog_visual.py keeps a hand-maintained V list, which stalled at 0.27.0
while the program marched on. This generator instead PARSES the authoritative CHANGELOG.md at
runtime — every `## [x.y.z] — date — title` entry becomes a card (kind inferred, flow nodes from
the ### section headings, summary from the first bullets). Re-run it after any release and the
strip is current by construction; it can never stall again.

  python _make_changelog_visual_full.py            # reads ../CHANGELOG.md
  python _make_changelog_visual_full.py <path>     # explicit changelog path (testing)

Writes CHANGELOG-VISUAL-FULL.svg + .pdf (R3/R5 dark + PDF). The original generator and its
outputs are retained untouched (R6)."""
import html
import os
import re
import sys

from _common import BG, PANEL, P2, LINE, TXT, SUB, ACC, GRN, AMB, BASE_DIR

KIND_FILL = {"feat": ("#16301f", "#2f5a3e"), "fix": ("#3a2f1a", "#6b5526"), "rule": ("#1a2740", "#3a4d6e")}


def esc(s):
    return html.escape(str(s if s is not None else ""))


def parse(path):
    src = open(path, encoding="utf-8").read()
    entries = []
    blocks = re.split(r"(?m)^## \[", src)[1:]
    for b in blocks:
        head = b.split("\n", 1)[0]
        m = re.match(r"([0-9.]+(?:-legacy)?)\]\s+—\s+(\S+)\s+—\s+(.+)", head)
        if not m: continue
        ver, date, title = m.group(1), m.group(2), m.group(3).strip()
        body = b.split("\n", 1)[1] if "\n" in b else ""
        body = re.split(r"(?m)^---\s*$", body)[0]
        secs = re.findall(r"(?m)^### (.+)$", body)
        # kind: rule when standing-rules / restructure / governance; fix when the first section fixes
        tl = (title + " " + " ".join(secs)).lower()
        if "rule" in tl or "restructure" in tl or "standing" in tl: kind = "rule"
        elif secs and secs[0].lower().startswith("fixed"): kind = "fix"
        elif "fix" in title.lower(): kind = "fix"
        else: kind = "feat"
        # flow nodes: section headings (cleaned), else bolded phrases, else generic
        nodes = [re.sub(r"\s*[—(].*$", "", s).replace("**", "").strip()[:34] for s in secs][:4]
        if not nodes:
            nodes = [x.strip()[:34] for x in re.findall(r"\*\*([^*]{3,40})\*\*", body)][:4]
        if not nodes:
            nodes = ["Change shipped"]
        # summary: first bullet lines, markdown stripped
        bullets = re.findall(r"(?m)^- (.+)$", body)
        summ = " ".join(bullets[:2])
        summ = re.sub(r"[`*]|\[(.*?)\]\(.*?\)", r"\1", summ)
        summ = re.sub(r"\s+", " ", summ).strip()[:300]
        entries.append((ver, date, title, kind, nodes, summ))
    entries.reverse()                      # chronological (CHANGELOG.md is newest-first)
    return entries


def wraptext(s, width):
    out, cur = [], ""
    for w in str(s).split():
        if cur and len(cur) + 1 + len(w) > width: out.append(cur); cur = w
        else: cur = (cur + " " + w).strip()
    if cur: out.append(cur)
    return out


def build(entries):
    COLS = 2; CW = 565; CH = 148; GX = 18; GY = 14; PAD = 36
    rows = (len(entries) + COLS - 1) // COLS
    W = PAD * 2 + COLS * CW + (COLS - 1) * GX
    H = 120 + rows * (CH + GY) + 40
    P = ['<svg viewBox="0 0 %d %d" xmlns="http://www.w3.org/2000/svg" font-family="-apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif">' % (W, H),
         '<rect width="%d" height="%d" fill="%s"/>' % (W, H, BG)]
    P.append('<text x="%d" y="52" font-size="24" font-weight="700" fill="%s">THE VIEWER — visual changelog (complete, auto-generated)</text>' % (PAD, TXT))
    P.append('<text x="%d" y="76" font-size="12" fill="%s">%d releases · generated from docs/CHANGELOG.md — rerun _make_changelog_visual_full.py after any release · R3/R5</text>'
             % (PAD, SUB, len(entries)))
    legend = [("feat", "feature", GRN), ("fix", "fix", AMB), ("rule", "rule / structure", ACC)]
    lx = PAD
    for k, lbl, col in legend:
        f, st = KIND_FILL[k]
        P.append('<rect x="%d" y="88" width="14" height="14" rx="4" fill="%s" stroke="%s"/>' % (lx, f, st))
        P.append('<text x="%d" y="100" font-size="11" fill="%s">%s</text>' % (lx + 20, SUB, lbl))
        lx += 130
    for i, (ver, date, title, kind, nodes, summ) in enumerate(entries):
        cx = PAD + (i % COLS) * (CW + GX); cy = 118 + (i // COLS) * (CH + GY)
        f, st = KIND_FILL.get(kind, KIND_FILL["feat"])
        P.append('<rect x="%d" y="%d" width="%d" height="%d" rx="10" fill="%s" stroke="%s"/>' % (cx, cy, CW, CH, PANEL, LINE))
        P.append('<rect x="%d" y="%d" width="6" height="%d" rx="3" fill="%s"/>' % (cx, cy, CH, st))
        P.append('<rect x="%d" y="%d" width="58" height="20" rx="6" fill="%s" stroke="%s"/>' % (cx + 16, cy + 12, f, st))
        P.append('<text x="%d" y="%d" font-size="10.5" font-weight="700" fill="%s">%s</text>' % (cx + 22, cy + 26, TXT, esc(ver[:9])))
        tl = wraptext(title, 54)                       # stays clear of the right-aligned date
        P.append('<text x="%d" y="%d" font-size="12.5" font-weight="600" fill="%s">%s</text>' % (cx + 84, cy + 26, TXT, esc(tl[0][:54])))
        if len(tl) > 1:
            P.append('<text x="%d" y="%d" font-size="11" fill="%s">%s</text>' % (cx + 84, cy + 41, SUB, esc(tl[1][:60] + ("…" if len(tl) > 2 or len(tl[1]) > 60 else ""))))
        P.append('<text x="%d" y="%d" font-size="9.5" fill="%s">%s</text>' % (cx + CW - 78, cy + 26, SUB, esc(date)))
        nx = cx + 16; ny = cy + 52; bw = min(124, int((CW - 40) / max(1, len(nodes))) - 10)
        for j, nd in enumerate(nodes):
            P.append('<rect x="%d" y="%d" width="%d" height="26" rx="6" fill="%s" stroke="%s"/>' % (nx, ny, bw, P2, LINE))
            lab = nd if len(nd) <= int(bw / 5.4) else nd[:int(bw / 5.4) - 1] + "…"
            P.append('<text x="%d" y="%d" font-size="9" fill="%s" text-anchor="middle">%s</text>' % (nx + bw / 2, ny + 17, TXT, esc(lab)))
            if j < len(nodes) - 1:
                P.append('<path d="M%d,%d L%d,%d" stroke="%s" stroke-width="1.3"/>' % (nx + bw, ny + 13, nx + bw + 10, ny + 13, SUB))
            nx += bw + 10
        ly = cy + 96
        for ln in wraptext(summ, 102)[:3]:
            P.append('<text x="%d" y="%d" font-size="9.6" fill="%s">%s</text>' % (cx + 16, ly, SUB, esc(ln)))
            ly += 13
    P.append('<text x="%d" y="%d" font-size="10" fill="#6b7280">Rules: R1 backwards-compatible · R2 diagram · R3 dark+PDF · R4 changelog · R5 visual changelog · R6 append-only · R7 legacy track</text>' % (PAD, H - 14))
    P.append("</svg>")
    return "\n".join(P)


if __name__ == "__main__":
    clog = sys.argv[1] if len(sys.argv) > 1 else os.path.join(BASE_DIR, "..", "CHANGELOG.md")
    entries = parse(clog)
    if not entries:
        sys.exit("no entries parsed from " + clog)
    svg = build(entries)
    base = os.path.join(BASE_DIR, "CHANGELOG-VISUAL-FULL")
    open(base + ".svg", "w", encoding="utf-8").write(svg)
    try:
        import cairosvg
        cairosvg.svg2pdf(bytestring=svg.encode("utf-8"), write_to=base + ".pdf")
        print("wrote CHANGELOG-VISUAL-FULL.svg + .pdf (%d releases)" % len(entries))
    except Exception as e:
        print("wrote CHANGELOG-VISUAL-FULL.svg (%d releases); PDF skipped: %s" % (len(entries), e))
