"""pinouts.py -- extract CONNECTOR PINOUTS + WIRE COLORS from schematic / wiring text (brief-req: wiring).
A mechanic checking continuity needs to know which pin carries what and the wire colour to trace. TMs give
these as pin tables ('Pin A  WHT/BLK  GROUND') and connector callouts ('Connector J5'). This pulls them into
a structured pinout so the app can show 'J5 pin A = ground, white/black wire' and back it to the page.

Pure regex extraction; unit-testable. Read-only, offline."""

from __future__ import annotations
import re

# standard MIL/automotive wire-colour abbreviations (+ slash tracers, e.g. WHT/BLK)
_COLORS = {"WHT": "white", "BLK": "black", "RED": "red", "GRN": "green", "BLU": "blue", "YEL": "yellow",
           "ORN": "orange", "ORG": "orange", "BRN": "brown", "VIO": "violet", "PUR": "purple", "GRY": "gray",
           "GRA": "gray", "PNK": "pink", "TAN": "tan", "WH�": "white"}
_COLOR_TOK = r"(?:%s)(?:/(?:%s))?" % ("|".join(_COLORS), "|".join(_COLORS))
_CONN = re.compile(r"\b(?:connector|conn\.?|receptacle|plug)\s+([JPX]\d{1,3}[A-Z]?)\b|\b([JPX]\d{1,3})\b(?=\s*(?:pin|-|,|:))", re.I)
# a pin row: <pin id>  <color?>  <signal text>   (pin id = a number or a single letter)
_PINROW = re.compile(r"^\s*(?:pin\s*)?([0-9]{1,3}|[A-Za-z])\b[\s:.\-]+(?:(" + _COLOR_TOK + r")\b[\s:.\-]+)?(.{2,60}?)\s*$", re.I)


def wire_color(tok):
    """'WHT/BLK' -> 'white/black'."""
    if not tok:
        return ""
    parts = tok.upper().split("/")
    return "/".join(_COLORS.get(p, p.lower()) for p in parts)


def extract_pinouts(text, cap=60):
    """-> [{connector, pins:[{pin, wire, wire_color, signal}]}]. Groups pin rows under the nearest connector."""
    if not text:
        return []
    lines = text.split("\n")
    conns, cur = [], None
    for ln in lines:
        cm = _CONN.search(ln)
        if cm:
            cid = (cm.group(1) or cm.group(2) or "").upper()
            if cur is None or cur["connector"] != cid:
                cur = {"connector": cid, "pins": []}
                conns.append(cur)
        m = _PINROW.match(ln)
        if m and cur is not None:
            pin, color, signal = m.group(1), m.group(2), (m.group(3) or "").strip(" .:-")
            # reject obvious prose lines (signal must look like a signal, not a sentence fragment with no caps/codes)
            if not signal or len(signal.split()) > 8:
                continue
            cur["pins"].append({"pin": pin.upper(), "wire": (color or "").upper(),
                                "wire_color": wire_color(color), "signal": signal})
        if len(conns) >= cap:
            break
    # keep only connectors that actually gathered pins
    return [c for c in conns if c["pins"]][:cap]


# --------------------------------------------------------------------------- #
# self-test: `python pinouts.py`                                              #
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    assert wire_color("WHT/BLK") == "white/black", wire_color("WHT/BLK")
    assert wire_color("RED") == "red"
    print("wire_color OK")

    text = ("Connector J5 pinout:\n"
            "Pin A  RED   +24 VDC\n"
            "Pin B  WHT/BLK  GROUND\n"
            "Pin C  GRN   START SIGNAL\n"
            "Connector J7\n"
            "1  BLU  SENSOR RETURN\n"
            "2  YEL  SENSOR SIGNAL\n")
    conns = extract_pinouts(text)
    assert len(conns) == 2, conns
    j5 = conns[0]
    assert j5["connector"] == "J5" and len(j5["pins"]) == 3, j5
    pb = [p for p in j5["pins"] if p["pin"] == "B"][0]
    assert pb["wire_color"] == "white/black" and "GROUND" in pb["signal"].upper(), pb
    j7 = conns[1]
    assert j7["connector"] == "J7" and len(j7["pins"]) == 2, j7
    print("extract_pinouts OK -> %s(%d pins), %s(%d pins)" %
          (j5["connector"], len(j5["pins"]), j7["connector"], len(j7["pins"])))
    print("   J5-B:", pb["pin"], pb["wire_color"], "->", pb["signal"])
    assert extract_pinouts("Just some prose with no pinout here at all.") == []
    print("no-pinout graceful OK")
    print("pinouts self-test PASS")

# END OF FILE
