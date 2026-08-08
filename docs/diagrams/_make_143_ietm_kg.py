#!/usr/bin/env python3
"""v1.3.0 — Structured-source jackpot: IETM/S1000D XML + the knowledge graph. Dark (R3)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import *
W, H = 1160, 470
P = [svg_open(W, H), box(0, 0, W, H, BG, BG, 0)]
def hr(y): P.append('<line x1="40" y1="%d" x2="%d" y2="%d" stroke="%s"/>' % (y, W-40, y, LINE))
P.append(t(40, 46, "Structured-source jackpot — IETM/S1000D XML + the knowledge graph   v1.3.0", 17, TXT, 700))
hr(72)
P.append(panel(40, 92, 520, 168, "🧬", "ietm.py  §6.2", ACC,
               ["S1000D data modules / IETM / MIL-STD-40051 XML", "namespace-agnostic stdlib xml.etree",
                "→ title · warnings · cautions · notes · steps · tables", "+ measurements — richest, cleanest source (no OCR)",
                "/api/ietm"], "ALREADY-TAGGED DATA"))
P.append(panel(580, 92, 540, 168, "🕸", "kg.py + build_kg.py  §3.11 / §7.4", PUR,
               ["part ↔ figure ↔ procedure ↔ spec ↔ NSN ↔ vehicle", "triples from viewer.db + masterfile + figureparts",
                "'everything about X' = one hop", "append-only index/kg.db · /api/kg", "BUILD-KG.bat"],
               "KNOWLEDGE GRAPH"))
hr(282)
P.append(t(40, 308, "R12 progress — the two big structural methods landed", 13, TXT, 700))
P.append(box(40, 320, 1080, 116, PANEL, GRN, 12, 1))
s, _ = wrap(58, 344, "The catalog is now ✅ across §2.2/2.3/2.6 (tables+cleanup), §3.2/3.6/3.7/3.8/3.9/3.10/3.11 (units, "
            "leading-particulars, threads/MIL-SPEC, safety, acronyms, relations), §5.1-5.5/5.8 (PDF-native), §6.2 "
            "(IETM/S1000D), §7.4 (knowledge graph). Remaining are the vision-heavy few: rotation-aware GD&T from "
            "drawings (§4.6), full layout analysis (§2.4), callout-number OCR (§4.5, needs easyocr host-side), and "
            "vision-language page QA (§10.1). Everything additive, sidecar-only, corpus authoritative — the repository "
            "increasingly stands on its own (R12).", 250, 10.5, SUB, 16); P.append(s)
print("PDF bytes:", render("".join(P) + "</svg>", BASE_DIR + "/143-ietm-kg"))
