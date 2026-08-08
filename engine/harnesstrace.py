"""harnesstrace.py -- infer wiring CONTINUITY across connectors from extracted pinouts (roadmap Vol.2 #55).
Given the structured pinouts that pinouts.py pulls from a wiring diagram, this groups pins that belong to the
same electrical net so a mechanic can answer 'if I have voltage on J5-A, where else should it appear?' and
trace a wire end to end. Two pins are treated as continuous when they name the SAME signal in the pin tables;
whether their wire colours also agree is reported as a confidence signal.

R13 discipline: continuity here is INFERRED from what the pin tables say, not asserted as measured truth. We
group only on an explicit shared signal name (never on wire colour alone, which is far too common), we label
every net with the inference method + a confidence, and a pin with no partner is reported as 'no continuity
partner found' rather than force-joined to anything. Nothing is fabricated; if the tables are silent we say so.
build_nets() and trace() are pure and unit-testable."""

from __future__ import annotations
import re

_ALIAS = {"GND": "GROUND", "GRD": "GROUND", "RTN": "RETURN", "RET": "RETURN",
          "PWR": "POWER", "POS": "POSITIVE", "NEG": "NEGATIVE", "SIG": "SIGNAL"}


def _norm_sig(s):
    """Normalize a signal name for grouping: upper, collapse whitespace/punctuation, apply common aliases."""
    t = re.sub(r"[^A-Z0-9+ ]", " ", (s or "").upper())
    t = re.sub(r"\s+", " ", t).strip()
    return " ".join(_ALIAS.get(w, w) for w in t.split())


def _points(pinouts):
    """Flatten a list of {connector, pins: list} into flat point dicts {connector,pin,wire_color,signal,_sig}."""
    pts = []
    for c in pinouts or []:
        conn = (c.get("connector") or "").upper()
        for p in c.get("pins") or []:
            sig = (p.get("signal") or "").strip()
            pts.append({"connector": conn, "pin": (p.get("pin") or "").upper(),
                        "wire_color": p.get("wire_color") or "", "signal": sig, "_sig": _norm_sig(sig)})
    return pts


def build_nets(pinouts):
    """Group pins into electrical nets by shared (normalized) signal name. Each net is a dict with keys
    signal, points (each connector/pin/wire_color/signal), wire_colors, method, and confidence.
    Only nets with >=2 points are returned (a net needs at least two endpoints to mean continuity)."""
    groups = {}
    for pt in _points(pinouts):
        if not pt["_sig"]:
            continue                                       # unnamed pin: can't be grouped honestly
        groups.setdefault(pt["_sig"], []).append(pt)
    nets = []
    for sig, pts in groups.items():
        if len(pts) < 2:
            continue
        colors = sorted({p["wire_color"] for p in pts if p["wire_color"]})
        # confidence: colors agree (or unspecified) -> high; colors conflict -> medium (verify)
        conf = "high" if len(colors) <= 1 else "medium"
        nets.append({
            "signal": pts[0]["signal"],
            "points": [{"connector": p["connector"], "pin": p["pin"],
                        "wire_color": p["wire_color"], "signal": p["signal"]} for p in pts],
            "wire_colors": colors,
            "method": "shared-signal",
            "confidence": conf + ("" if conf == "high" else " (wire colours differ across the net — verify)"),
        })
    nets.sort(key=lambda n: (-len(n["points"]), n["signal"]))
    return nets


def trace(pinouts, connector, pin):
    """Trace continuity from one connector/pin. Returns {found, start, signal, wire_color, endpoints, method,
    confidence, note}. endpoints are the OTHER pins on the same net (may be empty)."""
    conn, pn = (connector or "").upper(), (pin or "").upper()
    start = None
    for pt in _points(pinouts):
        if pt["connector"] == conn and pt["pin"] == pn:
            start = pt
            break
    if start is None:
        return {"found": False, "note": "connector/pin %s-%s not found in the available pinout tables" % (conn, pn)}
    if not start["_sig"]:
        return {"found": True, "start": {"connector": conn, "pin": pn}, "signal": start["signal"],
                "wire_color": start["wire_color"], "endpoints": [], "method": "shared-signal",
                "confidence": "n/a", "note": "this pin has no named signal in the tables — cannot infer continuity"}
    for net in build_nets(pinouts):
        pts = net["points"]
        if any(p["connector"] == conn and p["pin"] == pn for p in pts):
            others = [p for p in pts if not (p["connector"] == conn and p["pin"] == pn)]
            return {"found": True, "start": {"connector": conn, "pin": pn}, "signal": start["signal"],
                    "wire_color": start["wire_color"], "endpoints": others, "method": net["method"],
                    "confidence": net["confidence"],
                    "note": "continuity inferred from the pinout tables (shared signal), not measured"}
    return {"found": True, "start": {"connector": conn, "pin": pn}, "signal": start["signal"],
            "wire_color": start["wire_color"], "endpoints": [], "method": "shared-signal", "confidence": "n/a",
            "note": "no continuity partner found for this signal in the available pinout tables"}


# --------------------------------------------------------------------------- #
# self-test: `python harnesstrace.py`                                         #
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    pinouts = [
        {"connector": "J5", "pins": [
            {"pin": "A", "wire_color": "red", "signal": "+24 VDC"},
            {"pin": "B", "wire_color": "white/black", "signal": "GROUND"},
            {"pin": "C", "wire_color": "green", "signal": "START SIGNAL"}]},
        {"connector": "J7", "pins": [
            {"pin": "1", "wire_color": "red", "signal": "+24 VDC"},
            {"pin": "2", "wire_color": "white/black", "signal": "GND"},          # alias of GROUND
            {"pin": "3", "wire_color": "blue", "signal": "SENSOR RETURN"}]},
    ]
    nets = build_nets(pinouts)
    # +24 VDC (J5-A, J7-1) and GROUND/GND (J5-B, J7-2) form two 2-point nets; START/SENSOR are singletons
    signals = {n["signal"] for n in nets}
    assert any("24" in s for s in signals) and any("GROUND" in s.upper() for s in signals), signals
    assert all(len(n["points"]) == 2 for n in nets), nets
    print("build_nets OK -> %d nets: %s" % (len(nets), ", ".join(sorted(signals))))

    t = trace(pinouts, "J5", "A")
    assert t["found"] and len(t["endpoints"]) == 1 and t["endpoints"][0]["connector"] == "J7", t
    assert t["endpoints"][0]["pin"] == "1" and t["confidence"].startswith("high"), t
    print("trace J5-A OK -> continuous to %s-%s (%s), confidence=%s"
          % (t["endpoints"][0]["connector"], t["endpoints"][0]["pin"], t["wire_color"], t["confidence"]))

    # GND alias groups with GROUND
    tg = trace(pinouts, "J7", "2")
    assert tg["found"] and any(e["connector"] == "J5" and e["pin"] == "B" for e in tg["endpoints"]), tg
    print("trace J7-2 (GND) OK -> joins GROUND net at J5-B via alias")

    # a singleton signal -> no partner, honestly reported (not force-joined)
    ts = trace(pinouts, "J5", "C")
    assert ts["found"] and ts["endpoints"] == [] and "no continuity partner" in ts["note"], ts
    print("trace J5-C OK -> no partner reported (not fabricated)")

    # missing pin -> found False
    tm = trace(pinouts, "J9", "Z")
    assert tm["found"] is False and "not found" in tm["note"], tm
    print("trace missing OK ->", tm["note"][:48])
    print("harnesstrace self-test PASS")

# END OF FILE
