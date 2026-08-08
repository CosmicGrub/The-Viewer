#!/usr/bin/env python3
"""Shared helpers for THE VIEWER diagram generators (dark theme, rule R3).

Import this instead of re-declaring the palette + box/text/wrap/panel in every _make_*.py:

    from _common import *
    P = [svg_open(1180, 560), box(0,0,1180,560,BG,BG,0), t(40,46,"Title",19,TXT,700), ...]
    print(render("\\n".join(P) + "</svg>", BASE_DIR + "/79-foo"))
"""
import html, os, sys

# ---- palette (R3 dark) — canonical tokens now live in engine/theme.py (A4, v0.96.0). ----
# Same names/values as before so every existing _make_*.py keeps working; a hardcoded
# fallback keeps this file standalone if engine/ is unreachable.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_ENGINE = os.path.abspath(os.path.join(BASE_DIR, "..", "..", "engine"))
try:
    if _ENGINE not in sys.path: sys.path.insert(0, _ENGINE)
    from theme import PALETTE as _P
    BG=_P["bg"]; PANEL=_P["panel"]; P2=_P["p2"]; LINE=_P["line"]; TXT=_P["txt"]; SUB=_P["sub"]
    ACC=_P["acc"]; GRN=_P["grn"]; AMB=_P["amb"]; TEAL=_P["teal"]; PUR=_P["pur"]; RED=_P["red"]
except Exception:
    BG="#0f1419"; PANEL="#171d26"; P2="#1c2430"; LINE="#2b333f"; TXT="#e6e9ee"; SUB="#9aa6b6"
    ACC="#4f9dff"; GRN="#2f7d4f"; AMB="#caa24a"; TEAL="#1d9e75"; PUR="#7f77dd"; RED="#e0564f"

def esc(s): return html.escape(str(s))

def svg_open(w, h):
    return ('<svg viewBox="0 0 %d %d" xmlns="http://www.w3.org/2000/svg" '
            'font-family="-apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif">' % (w, h))

def box(x, y, w, h, fill=P2, stroke=LINE, rx=9, sw=1):
    return ('<rect x="%s" y="%s" width="%s" height="%s" rx="%s" fill="%s" stroke="%s" stroke-width="%s"/>'
            % (x, y, w, h, rx, fill, stroke, sw))

def t(x, y, s, size=12, fill=TXT, w=400, anchor="start"):
    return ('<text x="%s" y="%s" font-size="%s" font-weight="%s" fill="%s" text-anchor="%s">%s</text>'
            % (x, y, size, w, fill, anchor, esc(s)))

def wrap(x, y, s, width, size, fill, dy=13, wt=400):
    out = []; words = str(s).split(); c = ""; l = 0
    for wd in words:
        if len(c) + len(wd) + 1 > width:
            out.append(t(x, y + l * dy, c, size, fill, wt)); c = wd; l += 1
        else:
            c = (c + " " + wd).strip()
    if c: out.append(t(x, y + l * dy, c, size, fill, wt))
    return "".join(out), l + 1

def panel(x, y, w, h, ic, title, color, rows, metric):
    out = [box(x, y, w, h, PANEL, LINE, 12), '<rect x="%s" y="%s" width="6" height="%s" rx="3" fill="%s"/>' % (x, y, h, color)]
    out.append(t(x + 20, y + 24, ic + "  " + title, 12.5, TXT, 700)); yy = y + 44
    for r in rows:
        out.append('<circle cx="%s" cy="%s" r="3" fill="%s"/>' % (x + 24, yy - 3, color))
        s, n = wrap(x + 36, yy, r, int((w - 58) / 5.2), 8.7, SUB, 11); out.append(s); yy += 3 + n * 11
    out.append(box(x + 16, y + h - 30, w - 32, 22, P2, color, 6, 1))
    out.append(t(x + 26, y + h - 15, metric, 8.8, color, 700))
    return "".join(out)

def render(svg, base):
    """Write base.svg + base.pdf + base_preview.png. Returns the PDF byte size."""
    import cairosvg
    open(base + ".svg", "w", encoding="utf-8").write(svg)
    cairosvg.svg2pdf(bytestring=svg.encode("utf-8"), write_to=base + ".pdf")
    cairosvg.svg2png(bytestring=svg.encode("utf-8"), write_to=base + "_preview.png", output_width=1180)
    return os.path.getsize(base + ".pdf")
