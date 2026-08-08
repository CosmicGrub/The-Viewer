#!/usr/bin/env python3
"""v1.1.6 — Masterfile surfaces where the work happens (Work Order / builder / dossier). Dark (R3)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import *
W, H = 1180, 520
P = [svg_open(W, H), box(0, 0, W, H, BG, BG, 0)]
def hr(y): P.append('<line x1="40" y1="%d" x2="%d" y2="%d" stroke="%s"/>' % (y, W-40, y, LINE))
P.append(t(40, 46, "Masterfile where the work happens — Work Order · builder · dossier   v1.1.6", 17, TXT, 700))
P.append(t(40, 64, "The consolidated dimensions now appear inline in the mechanic's views — corpus authoritative, no links (R11)", 11, AMB, 400))
hr(80)
P.append('<defs><marker id="a" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">'
         '<path d="M0 0 L6 3 L0 6 z" fill="%s"/></marker></defs>' % SUB)
# source
P.append(panel(40, 108, 300, 150, "🗂", "masterfile.db (the Masterfile)", PUR,
               ["filtered: canonical per dimension", "authoritative (corpus) + external", "no links carried"],
               "SOURCE"))
P.append(panel(40, 280, 300, 96, "🔌", "jobcard._master_dims()", TEAL,
               ["for_subject(subject) → filtered", "fail-soft → []"], "READER"))
P.append('<path d="M190 258 L190 280" stroke="%s" stroke-width="2" marker-end="url(#a)"/>' % SUB)
# three surfaces
P.append(panel(400, 108, 240, 268, "🧾", "Work Order PDF", ACC,
               ["New 'Key dimensions & specs'", "section after Torque", "authoritative vs ext · ranges",
                "listed in cover contents", "builds even if only dims"], "/api/jobcard"))
P.append(panel(660, 108, 240, 268, "🛠", "Job Card builder", GRN,
               ["'Key dimensions' preview card", "from preview() dimensions_sample", "counted in readiness total",
                "authoritative vs ext tag"], "/jobcard"))
P.append(panel(920, 108, 240, 268, "📇", "Part dossier", AMB,
               ["Lazy 'Key dimensions & specs'", "card fetches /api/master", "manual vs ext · unconfirmed",
                "no links · empty-state prompt"], "/dossier"))
for x in (400, 660, 920):
    P.append('<path d="M340 300 L%d 240" stroke="%s" stroke-width="2" marker-end="url(#a)"/>' % (x, SUB))
hr(400)
P.append(t(40, 426, "Why it matters", 13, TXT, 700))
P.append(box(40, 438, 1120, 62, PANEL, GRN, 12, 1))
s, _ = wrap(58, 460, "The dimensional data recovered across the whole wave — measured from the manuals, gap-filled from the "
            "Wayback-archived web, consolidated in the Masterfile — now lands directly on the bay-ready Work Order and the "
            "part dossier, where a mechanic actually needs a clearance, capacity, or torque. Manuals stay the source of "
            "truth; external values are labelled and unlinked.", 250, 10.4, SUB, 15); P.append(s)
print("PDF bytes:", render("".join(P) + "</svg>", BASE_DIR + "/138-masterfile-integration"))
