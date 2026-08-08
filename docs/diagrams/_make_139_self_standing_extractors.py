#!/usr/bin/env python3
"""v1.2.0 — Toward a self-standing repository: five new extractors + Masterfile intelligence. Dark (R3)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import *
W, H = 1200, 560
P = [svg_open(W, H), box(0, 0, W, H, BG, BG, 0)]
def hr(y): P.append('<line x1="40" y1="%d" x2="%d" y2="%d" stroke="%s"/>' % (y, W-40, y, LINE))
P.append(t(40, 46, "Toward a self-standing repository — 5 new extractors + Masterfile intelligence   v1.2.0", 17, TXT, 700))
P.append(t(40, 64, "R12: pull ALL the information (catalog §) so the tool stands alone; corpus authoritative, sidecar-only", 11, AMB, 400))
hr(80)
P.append('<defs><marker id="a" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">'
         '<path d="M0 0 L6 3 L0 6 z" fill="%s"/></marker></defs>' % SUB)
P.append(t(40, 104, "New extractors (each self-tested, in VERIFY-099)", 12.5, "#7fbfff", 700))
P.append(panel(40, 116, 222, 150, "📐", "units.py  §3.2", TEAL,
               ["Dual-unit convert/display", "in↔mm · ft-lb↔N-m · °F↔°C", "gal↔L · psi↔kPa · lb↔kg"], "NORMALIZE"))
P.append(panel(272, 116, 222, 150, "🏷", "leadingspecs.py  §3.6", ACC,
               ["'Label: value unit' pairs", "named specs → Masterfile", "in build_measures"], "KEY:VALUE"))
P.append(panel(504, 116, 222, 150, "🔩", "specparse.py  §3.7/3.8", AMB,
               ["thread · fit · Ø±tol", "MIL-SPEC · MS/AN/NAS", "fuel · lubricant", "/api/specs"], "ENGINEERING"))
P.append(panel(736, 116, 210, 150, "📑", "pdfmeta.py  §5", PUR,
               ["outline (chapters)", "metadata · links", "annotations", "/api/pdfmeta"], "PDF-NATIVE"))
P.append(panel(956, 116, 204, 150, "▦", "barcodes.py  §4.9", GRN,
               ["QR / Data-Matrix / 1-D", "OpenCV-QR (pyzbar opt.)", "scrapes NSNs"], "MACHINE-READ"))
hr(286)
P.append(t(40, 312, "Masterfile intelligence", 12.5, GRN, 700))
P.append(panel(40, 324, 360, 120, "🧮", "read-time enrichment (no rebuild)", TEAL,
               ["dual-unit alt on every filtered row", "wide-variance flag (_spread, §9.2)", "system: imperial/metric"],
               "for_subject()"))
P.append(panel(420, 324, 360, 120, "📊", "coverage() gap dashboard", AMB,
               ["per subject: dimensions covered", "which of 13 types still MISSING", "/api/master_coverage"],
               "TARGET ENRICHMENT"))
P.append(panel(800, 324, 360, 120, "📇", "dossier: Specs & standards card", PUR,
               ["threads · MIL-SPEC · fluids", "beside Key dimensions", "cited to the page"], "/dossier · /api/specs"))
hr(464)
P.append(t(40, 490, "Everything flows into the Masterfile", 12.5, TXT, 700))
P.append(box(40, 500, 1120, 44, PANEL, LINE, 12, 1))
s, _ = wrap(58, 520, "native text · OCR · tables · measurements · leading-particulars · threads/MIL-SPEC · PDF outline · "
            "barcodes → consolidated, deduped, dual-unit, variance-flagged, gap-tracked — a repository that answers on "
            "its own, corpus authoritative, no links surfaced (R11/R12).", 258, 10.2, SUB, 14); P.append(s)
print("PDF bytes:", render("".join(P) + "</svg>", BASE_DIR + "/139-self-standing-extractors"))
