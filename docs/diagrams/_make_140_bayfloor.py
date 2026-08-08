#!/usr/bin/env python3
"""v1.4.0 — Bay-floor batch data-flow: kiosk mode · offline QR · spec-sheet+coverage · confidence · ops. Dark (R2/R3)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import *

W, H = 1240, 940
P = [svg_open(W, H), box(0, 0, W, H, BG, BG, 0)]
def hr(y): P.append('<line x1="40" y1="%d" x2="%d" y2="%d" stroke="%s"/>' % (y, W-40, y, LINE))
def arrow(x1, y1, x2, y2, col=SUB):
    P.append('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" stroke-width="1.6" marker-end="url(#ah)"/>' % (x1, y1, x2, y2, col))

P.append('<defs><marker id="ah" markerWidth="9" markerHeight="9" refX="7" refY="3" orient="auto">'
         '<path d="M0,0 L7,3 L0,6 Z" fill="%s"/></marker></defs>' % SUB)

P.append(t(40, 50, "THE VIEWER v1.4.0 — Bay-floor batch  (data flow)", 20, TXT, 700))
P.append(t(40, 76, "Four lanes shipped together: kiosk mode · offline QR · Masterfile spec-sheet + coverage · per-dimension confidence · ops polish. "
                   "All additive & rollbackable (R1); corpus read-only (R6).", 11.5, SUB, 400))
hr(92)

# ---- LANE 1: offline QR ----
P.append(t(40, 120, "1  OFFLINE QR  —  part/NSN  ->  scannable deep-link to the dossier ON THIS LAN", 13, ACC, 700))
P.append(box(40, 132, 250, 74, PANEL, LINE, 10, 1)); P.append(t(56, 158, "part / NSN", 11, TXT, 700))
P.append(t(56, 178, "packet header <img> or", 9, SUB)); P.append(t(56, 192, "/api/qr?q=…", 9, SUB))
arrow(290, 169, 340, 169, ACC)
P.append(box(340, 132, 250, 74, PANEL, ACC, 10, 1)); P.append(t(356, 158, "qrgen.py", 11, ACC, 700))
P.append(t(356, 178, "segno (SVG) -> qrcode+PIL", 9, SUB)); P.append(t(356, 192, "-> degrade (503, app OK)", 9, SUB))
arrow(590, 169, 640, 169, ACC)
P.append(box(640, 132, 260, 74, PANEL, GRN, 10, 1)); P.append(t(656, 158, "QR image", 11, GRN, 700))
P.append(t(656, 178, "encodes http://<Host>/dossier", 9, SUB)); P.append(t(656, 192, "?q=NSN  (same-LAN jump)", 9, SUB))
arrow(900, 169, 950, 169, GRN)
P.append(box(950, 132, 250, 74, PANEL, LINE, 10, 1)); P.append(t(966, 158, "phone / 2nd tablet", 11, TXT, 700))
P.append(t(966, 178, "camera scan -> opens the", 9, SUB)); P.append(t(966, 192, "same part, no retyping", 9, SUB))
hr(222)

# ---- LANE 2: spec-sheet + coverage ----
P.append(t(40, 250, "2  MASTERFILE SPEC-SHEET + COVERAGE  —  the linkless Masterfile becomes printable & auditable", 13, TEAL, 700))
P.append(box(40, 262, 250, 74, PANEL, LINE, 10, 1)); P.append(t(56, 288, "masterfile.db", 11, TXT, 700))
P.append(t(56, 308, "consolidated dims", 9, SUB)); P.append(t(56, 322, "(corpus + external, no links)", 9, SUB))
arrow(290, 285, 340, 285, TEAL)
P.append(box(340, 262, 260, 40, PANEL, TEAL, 10, 1)); P.append(t(356, 287, "specsheet.for_subject -> PDF", 10, TEAL, 700))
P.append(box(340, 306, 260, 30, PANEL, TEAL, 10, 1)); P.append(t(356, 326, "/api/master_coverage", 10, TEAL, 700))
arrow(600, 282, 650, 282, TEAL)
P.append(box(650, 262, 250, 40, PANEL, GRN, 10, 1)); P.append(t(666, 287, "/api/specsheet  (1-page PDF)", 10, GRN, 700))
arrow(600, 321, 650, 321, TEAL)
P.append(box(650, 306, 250, 30, PANEL, GRN, 10, 1)); P.append(t(666, 326, "/mastercov  (gaps dashboard)", 10, GRN, 700))
P.append(box(950, 262, 250, 74, PANEL, LINE, 10, 1)); P.append(t(966, 288, "on /master", 11, TXT, 700))
P.append(t(966, 308, "'Spec sheet PDF' button +", 9, SUB)); P.append(t(966, 322, "'Coverage' link + palette", 9, SUB))
arrow(900, 285, 950, 285, GRN); arrow(900, 321, 950, 321, GRN)
hr(352)

# ---- LANE 3: confidence ----
P.append(t(40, 380, "3  CONFIDENCE  —  a per-dimension trust score, surfaced where the value is read", 13, AMB, 700))
P.append(box(40, 392, 300, 66, PANEL, LINE, 10, 1)); P.append(t(56, 416, "masterfile.for_subject", 11, TXT, 700))
P.append(t(56, 436, "each filtered row: authoritative?", 9, SUB)); P.append(t(56, 449, "n samples · spread(wide?)", 9, SUB))
arrow(340, 425, 390, 425, AMB)
P.append(box(390, 392, 300, 66, PANEL, AMB, 10, 1)); P.append(t(406, 416, "_confidence(f)", 11, AMB, 700))
P.append(t(406, 436, "high / medium / review / low", 9, SUB)); P.append(t(406, 449, "(no per-method tracking needed)", 9, SUB))
arrow(690, 425, 740, 425, AMB)
P.append(box(740, 392, 460, 66, PANEL, GRN, 10, 1)); P.append(t(756, 416, "/master — colored badge + legend", 11, GRN, 700))
P.append(t(756, 436, "high=cited & corroborated · medium=single cite · review=wide spread · low=external", 8.6, SUB))
P.append(t(40, 476, "Deferred follow-ups (need index builds): hybrid keyword+semantic ranking · fold the acronym glossary into search.", 9.5, "#7f8a99", 400))
hr(492)

# ---- LANE 4: kiosk + ops ----
P.append(t(40, 520, "4  BAY-FLOOR KIOSK MODE  &  OPS POLISH", 13, PUR, 700))
P.append(box(40, 532, 570, 118, PANEL, PUR, 12, 1)); P.append(t(58, 556, "Kiosk / glove mode", 12.5, PUR, 700))
s,_ = wrap(58, 578, "palette.js command 'Toggle kiosk mode' -> toggles body.kiosk-mode + saves to localStorage; applied app-wide "
                    "on load across all 29 palette pages. base.css: bigger text, >=44px touch targets, higher-contrast subtext. "
                    "Pure CSS, no dependency, instantly reversible.", 116, 9.6, SUB, 13); P.append(s)
P.append(box(630, 532, 570, 118, PANEL, ACC, 12, 1)); P.append(t(648, 556, "Ops polish", 12.5, ACC, 700))
s,_ = wrap(648, 578, "VIEWER-MENU.bat — one menu launcher for INSTALL/DOCTOR/RUN/VERIFY/RESUME-OCR/BUILD-*. "
                     "verify_ui.py ASCII console guard: FAILs on any print() with a cp1252-incompatible char (no more "
                     "Windows-console UnicodeEncodeError crashes). VERIFY-099.bat now self-tests qrgen + specsheet.", 116, 9.6, SUB, 13); P.append(s)
hr(668)

# ---- graceful-degrade + safety notes ----
P.append(t(40, 696, "GRACEFUL DEGRADE & SAFETY (unchanged doctrine)", 13, GRN, 700))
notes = [
 ("QR", ACC, "No QR backend installed? available()=False, /api/qr returns a friendly 503, the packet QR self-hides. The app never breaks."),
 ("Spec sheet", TEAL, "No reportlab? 503. No consolidated dims for the subject yet? 404 telling you to build the Masterfile first."),
 ("Confidence", AMB, "Falls back to authoritative->medium / external->low if the field is ever absent; the value display is never blocked."),
 ("Rollback (R1)", PUR, "Delete qrgen.py/specsheet.py + their routes, or the kiosk CSS/palette lines — each removes cleanly with zero impact."),
]
ny, nx0, ncw, nch = 710, 40, 575, 74
for i,(ti,col,de) in enumerate(notes):
    cx = nx0 + (i%2)*(ncw+10); cy = ny + (i//2)*(nch+10)
    P.append(box(cx, cy, ncw, nch, PANEL, col, 12, 1)); P.append(t(cx+16, cy+24, ti, 12, col, 700))
    s,_ = wrap(cx+16, cy+44, de, 150, 9.4, SUB, 12); P.append(s)

P.append(box(40, 874, 1160, 40, PANEL, GRN, 12, 1))
P.append(t(58, 899, "R1 additive/rollbackable · R2 this diagram · R3 dark+PDF · R4 CHANGELOG [1.4.0] · R5 changelog-visual · R6 append-only/corpus RO · R7 legacy [1.4.0-legacy] · "
                    "R9 tail sentinel + VERIFY-099 completeness · VERSION=1.4.0.", 9.2, SUB, 400))
P.append(t(40, H-8, "Dark (R3). 2026-07-02 · qrgen.py · specsheet.py · /api/qr · /api/specsheet · /mastercov · masterfile._confidence · palette kiosk · verify_ui ASCII guard · VIEWER-MENU.bat.", 9, "#6b7280", 400))
P.append("</svg>")
print("wrote", render("\n".join(P), os.path.join(BASE_DIR, "140-bayfloor-batch")), "bytes")
