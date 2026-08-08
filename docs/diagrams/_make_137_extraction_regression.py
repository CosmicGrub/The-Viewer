#!/usr/bin/env python3
"""v1.1.5 — Integrity recovery check + regression guard for the extraction pipeline. Dark (R3)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import *
W, H = 1180, 520
P = [svg_open(W, H), box(0, 0, W, H, BG, BG, 0)]
def hr(y): P.append('<line x1="40" y1="%d" x2="%d" y2="%d" stroke="%s"/>' % (y, W-40, y, LINE))
P.append(t(40, 46, "No code lost — integrity check + regression guard for the extraction pipeline   v1.1.5", 17, TXT, 700))
hr(70)
# left: integrity check
P.append(t(40, 96, "① Recovery / integrity check (authoritative, not the sandbox cache)", 12.5, GRN, 700))
P.append(box(40, 108, 540, 200, PANEL, GRN, 12, 1))
yy = 134
for line in ["Every v1.1 module ends at its # END OF FILE sentinel",
             "at the exact authored line count: enrich 334, masterfile 231,",
             "measures 167, tables 97, builders at theirs",
             "All 14 enrich functions present · routes.py 171 route lines",
             "HTML/JS close properly · zero placeholder/omission markers",
             "Truncation only ever hit the sandbox READ VIEW of grown files;",
             "the real files were always whole (Edit/Write/Read = real files)"]:
    P.append('<circle cx="58" cy="%d" r="2.6" fill="%s"/>' % (yy-3, GRN))
    s, n = wrap(70, yy, line, 76, 10, SUB, 13); P.append(s); yy += n*13 + 6
# right: regression guard
P.append(t(610, 96, "② Regression guard — tests/test_extraction.py", 12.5, ACC, 700))
P.append(box(610, 108, 530, 200, PANEL, ACC, 12, 1))
yy = 134
for line in ["measures: 10 dimension types + ft-lb/in-lb precedence + range/tol",
             "enrich: Wayback parse + HTML-strip + no-snapshot + seed scoping",
             "enrich: corpus-authoritative read filter",
             "masterfile: merge + gap-fill + corpus wins",
             "masterfile: NO links leak · corpus rows keep page cite",
             "tables: spec-table detect (self-skips without PyMuPDF)",
             "Self-contained (temp DBs + fake network) · runs in VERIFY-099"]:
    P.append('<circle cx="628" cy="%d" r="2.6" fill="%s"/>' % (yy-3, ACC))
    s, n = wrap(640, yy, line, 74, 10, SUB, 13); P.append(s); yy += n*13 + 6
hr(332)
P.append(t(40, 358, "Wired into the gate", 13, TXT, 700))
P.append(box(40, 370, 1100, 110, PANEL, LINE, 12, 1))
s, _ = wrap(58, 396, "VERIFY-099.bat now parses + completeness-checks test_extraction.py (tail sentinel, R9) and runs it "
            "alongside the module self-tests. So the whole measures → tables → enrich → masterfile pipeline — including "
            "the corpus-authoritative rule and the no-links-surfaced guarantee of the Masterfile — is protected against "
            "future regressions. Additive & rollbackable (R1); corpus untouched (R6).", 244, 10.5, SUB, 16)
P.append(s)
print("PDF bytes:", render("".join(P) + "</svg>", BASE_DIR + "/137-extraction-regression"))
