#!/usr/bin/env python3
"""v1.2.1 — Internal provenance-audit view. Dark (R3)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import *
W, H = 1160, 470
P = [svg_open(W, H), box(0, 0, W, H, BG, BG, 0)]
def hr(y): P.append('<line x1="40" y1="%d" x2="%d" y2="%d" stroke="%s"/>' % (y, W-40, y, LINE))
P.append(t(40, 46, "Provenance audit — the one place links live, for the operator only   v1.2.1", 17, TXT, 700))
hr(70)
P.append('<defs><marker id="a" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">'
         '<path d="M0 0 L6 3 L0 6 z" fill="%s"/></marker></defs>' % SUB)
P.append(panel(40, 96, 320, 150, "🌐", "enrich.db", AMB,
               ["Every external gap-fill", "with FULL provenance:", "archived Wayback URL · orig URL · ts"],
               "SIDECAR (audit)"))
P.append(panel(420, 96, 300, 150, "🔎", "enrich.provenance_rows()", TEAL,
               ["/api/provenance  · /audit page", "filter by subject or list all", "tolerates pre-1.1.3 sidecars"],
               "OPERATOR-ONLY"))
P.append(panel(780, 96, 340, 150, "🧑‍🔧", "mechanic views", GRN,
               ["Masterfile · dossier · Work Order", "consolidated values only", "NO links surfaced (R11)"],
               "LINK-FREE"))
P.append('<path d="M360 171 L420 171" stroke="%s" stroke-width="2" marker-end="url(#a)"/>' % SUB)
P.append('<path d="M360 210 C 560 300, 620 300, 780 200" stroke="%s" stroke-width="2" fill="none" stroke-dasharray="5 4" marker-end="url(#a)"/>' % SUB)
P.append(t(470, 300, "same data, links stripped", 10, SUB, 400))
hr(270)
P.append(t(40, 296, "Why split them", 13, TXT, 700))
P.append(box(40, 308, 1080, 128, PANEL, LINE, 12, 1))
s, _ = wrap(58, 332, "Chris's rule (R11): mechanics should never see external links — only the raw + filtered data correlated "
            "to the authoritative manuals. But someone still has to be able to VERIFY where an external value came from. "
            "The /audit page keeps that capability in one operator-only place: it shows the archived Wayback snapshot "
            "URL, the original live URL, and the snapshot date for every gap-fill, so a source can be spot-checked — "
            "without ever leaking a link into the mechanic-facing Masterfile, dossier, or Work Order. The manuals stay "
            "authoritative; external values remain labelled unconfirmed everywhere.", 244, 10.5, SUB, 16)
P.append(s)
print("PDF bytes:", render("".join(P) + "</svg>", BASE_DIR + "/140-provenance-audit"))
