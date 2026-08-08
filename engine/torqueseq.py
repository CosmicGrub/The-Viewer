"""torqueseq.py -- torque SEQUENCE + bolt-pattern diagrams (R13 safety graphic; brief-req D). A TM will say
'torque the bolts in a star pattern, in three stages to 15, 30, then 45 ft-lb' -- in TEXT. Getting the
ORDER or the STAGING wrong warps a head or a flange. This module detects the pattern and the staged values
from the text and renders a clear NUMBERED bolt-pattern diagram showing the tightening order, plus the
stage list. A visual aid, always cited back to the TM.

detect_sequence() and star_order() are pure and unit-testable; render_svg() is deterministic. Offline."""

from __future__ import annotations
import math, re

_NUM = r"[-+]?(?:\d{1,4}(?:\.\d+)?)"
_PATTERNS = [
    (re.compile(r"\bstar[\s-]*pattern\b", re.I), "star"),
    (re.compile(r"\bcris?s?[\s-]*cross\b|\bcross[\s-]*pattern\b|\bdiagonal(?:ly)?\b|\balternately\b|\bopposite\b", re.I), "crisscross"),
    (re.compile(r"\bin\s+sequence\b|\bsequential(?:ly)?\b|\bin\s+order\b|\bconsecutiv", re.I), "sequential"),
    (re.compile(r"\bcircular\s+pattern\b|\bclockwise\b|\baround\b", re.I), "circular"),
]
_NBOLT = re.compile(r"\b(\d{1,2})\s*(?:bolts?|screws?|nuts?|cap\s*screws?|fasteners?)\b", re.I)
_STAGES = re.compile(r"\b(?:to|at)\s+(" + _NUM + r")\s*(?:,\s*(?:then\s+)?|\s+then\s+|\s+and\s+)(" + _NUM +
                     r")(?:\s*(?:,\s*(?:then\s+)?|\s+then\s+|\s+and\s+)(" + _NUM + r"))?", re.I)


def detect_sequence(text):
    """-> {pattern, stages:[float], n_bolts:int|None, note}. pattern in star|crisscross|sequential|circular|None."""
    if not text:
        return {"pattern": None, "stages": [], "n_bolts": None}
    pattern = None
    for rx, name in _PATTERNS:
        if rx.search(text):
            pattern = name
            break
    nb = _NBOLT.search(text)
    n_bolts = int(nb.group(1)) if nb else None
    stages = []
    m = _STAGES.search(text)
    if m:
        stages = [float(g) for g in m.groups() if g]
    else:  # single 'torque to X'
        s = re.search(r"\btorque\b[^.]{0,40}?\b(?:to|at)\s+(" + _NUM + r")", text, re.I)
        if s:
            stages = [float(s.group(1))]
    return {"pattern": pattern, "stages": stages, "n_bolts": n_bolts,
            "note": "representative tightening order -- confirm against the TM figure"}


def star_order(n):
    """A representative star / criss-cross tightening order for n bolts arranged in a circle: jump ~halfway
    each step, nudging to the next free position. Returns 1-based bolt numbers in tightening order."""
    if n <= 0:
        return []
    if n <= 2:
        return list(range(1, n + 1))
    order, used, cur, half = [0], {0}, 0, n // 2
    while len(order) < n:
        nxt = (cur + half) % n
        while nxt in used:
            nxt = (nxt + 1) % n
        order.append(nxt); used.add(nxt); cur = nxt
    return [i + 1 for i in order]


def render_svg(n_bolts, pattern="star", stages=None, w=360, h=360):
    """Numbered bolt-pattern diagram. Bolts sit on a circle; the number IS the tightening order."""
    n = max(1, min(int(n_bolts or 6), 40))
    seq = star_order(n) if pattern in ("star", "crisscross") else list(range(1, n + 1))
    # position index -> order label
    label_at = {}
    for order_idx, bolt_pos in enumerate(seq, start=1):
        label_at[bolt_pos] = order_idx
    cx, cy, r = w / 2.0, h / 2.0 - 6, min(w, h) * 0.36
    P = ['<svg viewBox="0 0 %d %d" xmlns="http://www.w3.org/2000/svg" font-family="Segoe UI,Arial,sans-serif">' % (w, h)]
    P.append('<rect width="%d" height="%d" fill="#0c1116"/>' % (w, h))
    P.append('<circle cx="%.1f" cy="%.1f" r="%.1f" fill="none" stroke="#2f4858" stroke-width="1.4" stroke-dasharray="4 4"/>' % (cx, cy, r))
    # faint order path
    pts = []
    for order_idx in range(1, n + 1):
        pos = seq[order_idx - 1]
        a = -math.pi / 2 + 2 * math.pi * (pos - 1) / n
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    if len(pts) > 1:
        P.append('<polyline points="%s" fill="none" stroke="#1d3a55" stroke-width="1.2"/>' %
                 " ".join("%.1f,%.1f" % p for p in pts))
    for pos in range(1, n + 1):
        a = -math.pi / 2 + 2 * math.pi * (pos - 1) / n
        x, y = cx + r * math.cos(a), cy + r * math.sin(a)
        oi = label_at.get(pos, pos)
        col = "#7fd6a0" if oi == 1 else ("#e8c07a" if oi == n else "#9fd0ff")
        P.append('<circle cx="%.1f" cy="%.1f" r="15" fill="#111823" stroke="%s" stroke-width="2"/>' % (x, y, col))
        P.append('<text x="%.1f" y="%.1f" font-size="13" font-weight="800" fill="%s" text-anchor="middle" dominant-baseline="central">%d</text>' % (x, y, col, oi))
    ptxt = (pattern or "sequence").upper()
    P.append('<text x="12" y="20" font-size="12.5" font-weight="700" fill="#8a98a8">%s tightening order (%d)</text>' % (ptxt, n))
    if stages:
        P.append('<text x="12" y="%d" font-size="11.5" fill="#e8c07a">Stages: %s</text>' %
                 (h - 12, " -> ".join(("%g" % s) for s in stages)))
    P.append("</svg>")
    return "\n".join(P)


def build(text, n_bolts=None):
    d = detect_sequence(text)
    n = n_bolts or d.get("n_bolts") or 6
    return {"pattern": d["pattern"] or "sequential", "stages": d["stages"], "n_bolts": n,
            "order": star_order(n) if (d["pattern"] in ("star", "crisscross")) else list(range(1, n + 1)),
            "svg": render_svg(n, d["pattern"] or "sequential", d["stages"]),
            "enough": bool(d["pattern"] or d["stages"])}


# --------------------------------------------------------------------------- #
# self-test: `python torqueseq.py`                                            #
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    d = detect_sequence("Torque the 8 bolts in a star pattern in three stages to 15, 30, then 45 ft-lb.")
    assert d["pattern"] == "star", d
    assert d["stages"] == [15.0, 30.0, 45.0], d
    assert d["n_bolts"] == 8, d
    print("detect_sequence OK ->", d["pattern"], d["stages"], "n=%d" % d["n_bolts"])

    o = star_order(8)
    assert sorted(o) == list(range(1, 9)) and len(set(o)) == 8, o     # a valid permutation
    assert o[0] == 1, o
    print("star_order(8) OK ->", o)

    r = build("Torque the 6 cap screws criss-cross to 25 ft-lb.", None)
    assert r["n_bolts"] == 6 and r["pattern"] == "crisscross", r
    assert r["svg"].startswith("<svg") and "tightening order" in r["svg"], "bad svg"
    assert r["enough"], r
    print("build OK -> %s, %d bolts, svg %d bytes" % (r["pattern"], r["n_bolts"], len(r["svg"])))

    plain = detect_sequence("Install the panel and secure it.")
    assert plain["pattern"] is None and plain["stages"] == [], plain
    print("no-pattern graceful OK")
    print("torqueseq self-test PASS")

# END OF FILE
