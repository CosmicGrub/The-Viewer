#!/usr/bin/env python3
"""109: v0.98.0 — nav consolidation (R2/R3 dark + PDF).

Left: the old 16-item header. Right: the new 7-item header with the Tools menu expanded and
Collections shown as the gateway to the Schematics + 3D libraries.
Run:  python _make_109_nav.py
"""
from _common import *

W, H = 1180, 640
P = [svg_open(W, H), box(0, 0, W, H, BG, BG, 0),
     '<defs><marker id="a" markerWidth="9" markerHeight="9" refX="7" refY="3" orient="auto">'
     '<path d="M0,0 L7,3 L0,6 z" fill="%s"/></marker></defs>' % SUB]

P.append(t(40, 44, "v0.98.0 — NAV CONSOLIDATION: 16 header items → 7", 19, TXT, 700))
P.append(t(40, 66, "libraries live in Collections · mechanic + admin tools live in ONE Tools menu · every old route still works (R1)", 11.5, SUB))

# BEFORE
P.append(box(40, 92, 545, 200, PANEL, RED, 12))
P.append(t(56, 116, "BEFORE — 16 top-level buttons", 12, RED, 700))
old = ["Schematics", "3D Library", "Collections", "Solve it", "Part dossier", "How to do it",
       "Look-Alike", "Circuit Lab", "Add docs", "Ops", "OCR status", "Help", "Settings",
       "Part# review", "Side", "Parts session"]
for i, b in enumerate(old):
    cx = 56 + (i % 4) * 130; cy = 130 + (i // 4) * 36
    P.append(box(cx, cy, 120, 26, P2, LINE, 7))
    P.append(t(cx + 60, cy + 17, b, 8.8, SUB, 400, "middle"))
P.append(t(56, 284, "two+ rows even after the wrap fix; libraries and tools compete with core actions", 8.8, SUB))

P.append('<path d="M593,192 L633,192" stroke="%s" stroke-width="2" fill="none" marker-end="url(#a)"/>' % SUB)

# AFTER
P.append(box(641, 92, 499, 200, PANEL, GRN, 12))
P.append(t(657, 116, "AFTER — 7 top-level items", 12, GRN, 700))
new = [("Browse chip", LINE), ("Collections", ACC), ("Tools ▾", AMB), ("Help", LINE),
       ("Settings", LINE), ("Side", LINE), ("Parts session", LINE)]
cx = 657; cy = 132
for b, col in new:
    bw = 48 + len(b) * 5
    if cx + bw > 1124: cx = 657; cy += 34          # wrap inside the panel (mirrors the real header)
    P.append(box(cx, cy, bw, 26, P2, col, 7))
    P.append(t(cx + bw / 2, cy + 17, b, 9.2, TXT if col != LINE else SUB, 600 if col != LINE else 400, "middle"))
    cx += bw + 8
P.append(t(657, 206, "fits ONE row on most screens — finishes the v0.97 E39 layout fix", 8.8, SUB))
P.append(t(657, 226, "accessible: aria-haspopup/expanded · Esc + outside-click close", 8.8, SUB))
P.append(t(657, 244, "Part# review keeps its id — the existing JS binding just works", 8.8, SUB))
P.append(t(657, 268, "routes /schematics /3d /dossier /procedure … all still live (R1)", 9.2, GRN, 600))

# Collections gateway
y2 = 330
P.append(t(40, y2, "COLLECTIONS = THE GATEWAY", 12, ACC, 700))
P.append(box(40, y2 + 14, 545, 240, PANEL, ACC, 12))
P.append(t(56, y2 + 38, "🗂 Collections page", 12, TXT, 700))
P.append(t(56, y2 + 56, "LIBRARIES", 9.5, ACC, 700))
P.append(box(56, y2 + 64, 250, 64, P2, LINE, 9))
P.append(t(70, y2 + 84, "📐 Schematics & wiring", 10.5, TXT, 700))
P.append(t(70, y2 + 100, "every schematic/wiring doc · viewer + overlays", 8.2, SUB))
P.append(box(318, y2 + 64, 250, 64, P2, LINE, 9))
P.append(t(332, y2 + 84, "🧊 3D Library", 10.5, TXT, 700))
P.append(t(332, y2 + 100, "cited figures · CAD turntable · local models", 8.2, SUB))
P.append(t(56, y2 + 150, "SMART COLLECTIONS", 9.5, ACC, 700))
P.append(box(56, y2 + 158, 512, 64, P2, LINE, 9))
P.append(t(70, y2 + 178, "warnings · torque tables · lube charts · your saved searches …", 9.5, SUB))
P.append(t(70, y2 + 196, "living groups — auto-fill as OCR adds pages (unchanged)", 8.4, SUB))

# Tools menu
P.append(t(641, y2, "🧰 TOOLS MENU (expanded)", 12, AMB, 700))
P.append(box(641, y2 + 14, 240, 240, PANEL, AMB, 12))
items = ["🛠 Solve it", "📋 Part dossier", "🔧 How to do it", "🔍 Look-Alike Parts", "⚡ Circuit Lab"]
admin = ["➕ Add documents", "📊 Ops", "🔤 OCR status", "🔧 Part# review"]
yy = y2 + 34
for it in items:
    P.append(t(657, yy, it, 10.5, TXT)); yy += 21
P.append('<line x1="657" y1="%d" x2="865" y2="%d" stroke="%s"/>' % (yy - 8, yy - 8, LINE))
yy += 8
for it in admin:
    P.append(t(657, yy, it, 10.5, SUB)); yy += 21
P.append(box(899, y2 + 14, 241, 240, PANEL, LINE, 12))
P.append(t(915, y2 + 38, "Why this split", 11, TXT, 700))
s, _ = wrap(915, y2 + 58, "Top level keeps only what a mechanic touches every session: search (always on screen), browse, Collections, Tools, Help, Settings, Side, the parts session. Everything else is one click deeper, grouped by intent — fix-it tools first, admin below the line.", 42, 9.2, SUB, 13)
P.append(s)

P.append(t(40, H - 14, "Verified: 10/10 acceptance + 7 suites green + RPS GATE PASS · rollback: backups/pre-v0.98-nav (R1) · R2/R3/R4/R5/R7 shipped", 9.3, "#6b7280"))

if __name__ == "__main__":
    print(render("\n".join(P) + "</svg>", BASE_DIR + "/109-nav-consolidation"))
