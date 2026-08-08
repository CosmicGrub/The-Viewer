#!/usr/bin/env python3
"""v1.1.2 — External gap-fill enrichment (IA/Wayback). Corpus authoritative. Dark (R3)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import *
W, H = 1180, 600
P = [svg_open(W, H), box(0, 0, W, H, BG, BG, 0)]
def hr(y): P.append('<line x1="40" y1="%d" x2="%d" y2="%d" stroke="%s"/>' % (y, W-40, y, LINE))
P.append(t(40, 46, "External gap-fill — cross-reference the internet to complete blanks   v1.1.2", 19, TXT, 700))
P.append(t(40, 64, "The corpus is ALWAYS authoritative. External data only fills dimension types the manuals are silent on.", 11, AMB, 400))
hr(80)
# top: online (host-run) band
P.append(t(40, 106, "① OPT-IN, ONLINE, HOST-RUN  —  ENRICH.bat → build_enrich.py  (the ONLY networked component)", 12.5, "#7fbfff", 700))
P.append(box(40, 116, 1100, 150, PANEL, "#7fbfff", 12, 1))
P.append(panel(56, 132, 250, 120, "🧩", "find_gaps()", AMB,
               ["Per vehicle: which dimension", "types have NO corpus value", "(uses measures sidecar)"],
               "MISSING TYPES"))
P.append(panel(322, 132, 250, 120, "🌐", "Internet Archive + Wayback", TEAL,
               ["IA full-text search → item text", "Wayback closest snapshot", "API shapes verified live"],
               "CROSS-REFERENCE"))
P.append(panel(588, 132, 240, 120, "📐", "same measures engine", GRN,
               ["Extract measurements from", "the external text — identical", "parser as the corpus path"],
               "EXTRACT"))
P.append(panel(844, 132, 280, 120, "🗄", "record() → enrich.db", PUR,
               ["Keeps ONLY the gap types", "Provenance: source · URL ·", "Wayback ts · fetched ts", "Append-only (R1/R6)"],
               "external-unconfirmed"))
for x1, x2 in [(306, 322), (572, 588), (828, 844)]:
    P.append('<path d="M%d 192 L%d 192" stroke="%s" stroke-width="2" marker-end="url(#a)"/>' % (x1, x2, SUB))
P.append('<defs><marker id="a" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">'
         '<path d="M0 0 L6 3 L0 6 z" fill="%s"/></marker></defs>' % SUB)
hr(286)
# bottom: offline read
P.append(t(40, 312, "② OFFLINE  —  the running app only READS enrich.db (no network ever from the server)", 12.5, GRN, 700))
P.append(box(40, 322, 1100, 150, PANEL, GRN, 12, 1))
P.append(panel(56, 338, 300, 120, "📚", "Corpus measurements", ACC,
               ["/api/measures over FTS", "AUTHORITATIVE — always wins", "Shown first, cited to page"],
               "DEFAULT SOURCE"))
P.append(panel(372, 338, 300, 120, "🚦", "/api/external filter", AMB,
               ["Pass corpus 'have' types", "Any type corpus answers →", "external HIDDEN (corpus wins)"],
               "GAP-ONLY"))
P.append(panel(688, 338, 436, 120, "🖥", "/measures — badged section", PUR,
               ["Separate 'External references — unconfirmed' block", "Each value: source ↗ link + snapshot date",
                "Explicit 'not verified — confirm before use' notice"],
               "CLEAR PROVENANCE"))
for x1, x2 in [(356, 372), (672, 688)]:
    P.append('<path d="M%d 398 L%d 398" stroke="%s" stroke-width="2" marker-end="url(#a)"/>' % (x1, x2, SUB))
hr(492)
# guardrails
P.append(t(40, 518, "Guardrails", 13, TXT, 700))
P.append(box(40, 530, 1100, 52, PANEL, RED, 12, 1))
s, _ = wrap(58, 552, "External values NEVER overwrite or contradict a corpus value · surfaced ONLY where the corpus is silent · "
            "always badged 'external-unconfirmed' with full provenance · app stays 100% offline (network only in the "
            "opt-in host crawler) · corpus untouched, sidecar append-only (R1/R6).", 246, 10.2, SUB, 15)
P.append(s)
print("PDF bytes:", render("".join(P) + "</svg>", BASE_DIR + "/134-external-enrichment"))
