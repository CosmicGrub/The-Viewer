#!/usr/bin/env python3
"""v1.2.3 — Acronyms, header/footer cleanup, borderless + cross-page tables. Dark (R3)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import *
W, H = 1160, 460
P = [svg_open(W, H), box(0, 0, W, H, BG, BG, 0)]
def hr(y): P.append('<line x1="40" y1="%d" x2="%d" y2="%d" stroke="%s"/>' % (y, W-40, y, LINE))
P.append(t(40, 46, "Acronyms · header/footer cleanup · borderless + cross-page tables   v1.2.3", 17, TXT, 700))
hr(72)
P.append(panel(40, 92, 350, 168, "🔤", "acronyms.py  §3.10", ACC,
               ["Parse the TM's abbreviations list", "→ per-manual glossary", "expand CTIS, GVWR, PMCS in body",
                "/api/acronyms"], "JARGON → MEANING"))
P.append(panel(405, 92, 350, 168, "🧹", "pagetrim.py  §2.6", TEAL,
               ["Find lines recurring across the", "top/bottom band of many pages", "strip running header/footer",
                "clean text for every extractor"], "DE-NOISE"))
P.append(panel(770, 92, 350, 168, "▦", "tables_plus.py  §2.2 / §2.3", AMB,
               ["Borderless tables (pdfplumber)", "the un-ruled specs find_tables misses", "cross-page stitch (dedup header)",
                "/api/tables_plus"], "TABLE RECOVERY"))
hr(282)
P.append(t(40, 308, "R12 progress", 13, TXT, 700))
P.append(box(40, 320, 1080, 112, PANEL, GRN, 12, 1))
s, _ = wrap(58, 344, "Catalog now ✅ through: §2.2/2.3/2.6 (tables + cleanup) · §3.2/3.6/3.7/3.8/3.9/3.10 (units, "
            "leading-particulars, threads/MIL-SPEC, safety, acronyms) · §5.1-5.5/5.8 (PDF-native). Borderless + "
            "cross-page tables were a standing R11 gap — now closed, feeding the same measures → Masterfile pipeline. "
            "Remaining: IETM/S1000D XML (§6.2), knowledge graph (§3.11/7.4), and the heavy vision ceiling "
            "(§2.4/4.6/10.1). All additive, sidecar-only, corpus authoritative.", 250, 10.5, SUB, 16); P.append(s)
print("PDF bytes:", render("".join(P) + "</svg>", BASE_DIR + "/142-tables-cleanup"))
