#!/usr/bin/env python3
"""THE VIEWER -- map the SCAN's 3-D descriptions (colour + material + finish) onto the 3-D models.

The scans/FLIS state a part's COLOR, MATERIAL and SURFACE TREATMENT/FINISH. This parses those words into a
renderable material spec: a base colour AND a procedural finish (metallic / matte / rubber / plated) the WebGL
viewer applies -- so a steel bolt looks metallic, a rubber hose matte-black, a brass fitting warm and glossy,
a zinc-plated screw silvery, an olive-drab painted bracket flat green.

Honest scope: the scans give material WORDS, not surface photographs -- so "texture" here is a procedural
finish (colour + metalness + roughness/shininess), not a photographic image map. Authoritative source: FLIS
characteristics (ref_nsn). Read-only (R1/R6). `core` injected by viewer_app.
"""
import re

core = None

# colour name -> hex (incl. military)
COLORS = {
    "BLACK": "#2a2a2a", "GRAY": "#8a9099", "GREY": "#8a9099", "WHITE": "#dcdcdc", "SILVER": "#c0c4c8",
    "RED": "#8a2f2f", "BLUE": "#33506e", "GREEN": "#3b5a3b", "YELLOW": "#c2a83a", "ORANGE": "#c2702a",
    "BROWN": "#5a4632", "TAN": "#b79b6e", "SAND": "#c2b280", "GOLD": "#c9a24a", "CLEAR": None, "NATURAL": None,
    "OLIVE": "#5a5a32", "OD": "#3b3b22",
}
MULTI_COLORS = [("OLIVE DRAB", "#3b3b22"), ("FOREST GREEN", "#2e4a2e"), ("GLOSS BLACK", "#1c1c1c"),
                ("FLAT BLACK", "#262626"), ("CARC GREEN", "#4b5320"), ("DESERT SAND", "#c9b08a"),
                ("DESERT TAN", "#c2a878"), ("FIELD DRAB", "#6c5d3f"), ("AIRCRAFT GRAY", "#9aa0a6")]

# material class -> (metal, rough, sheen, default colour, label)
MATERIALS = [
    (r"STAINLESS|CRES\b|CORROSION RESIST", (0.95, 0.25, 0.7, "#b4b8bd", "stainless steel")),
    (r"\bSTEEL|\bIRON\b|CARBON STEEL|ALLOY STEEL", (0.9, 0.4, 0.6, "#9aa0a6", "steel")),
    (r"ALUMIN", (0.8, 0.45, 0.5, "#b8bcc2", "aluminium")),
    (r"TITAN", (0.85, 0.45, 0.5, "#9a9ea3", "titanium")),
    (r"BRASS", (0.9, 0.35, 0.65, "#b5933f", "brass")),
    (r"BRONZE|COPPER", (0.9, 0.35, 0.6, "#b0703f", "bronze/copper")),
    (r"RUBBER|ELASTOMER|NEOPRENE|SILICONE", (0.0, 0.95, 0.1, "#2c2c2c", "rubber")),
    (r"NYLON|PLASTIC|POLY|PVC|PHENOLIC|ACETAL|DELRIN", (0.0, 0.6, 0.3, "#3a3a3a", "plastic")),
    (r"GLASS", (0.15, 0.12, 0.8, "#b8c4cc", "glass")),
    (r"\bWOOD|PLYWOOD|OAK|BIRCH", (0.0, 0.8, 0.2, "#6a4f32", "wood")),
]
# surface treatment / finish -> (override colour or None, metal, rough, sheen, label)
FINISHES = [
    (r"CHROM", ("#cfd3d8", 0.98, 0.15, 0.85, "chrome")),
    (r"ZINC|GALVANIZ", ("#c8ccd0", 0.85, 0.4, 0.6, "zinc plated")),
    (r"CADMIUM", ("#c8b06a", 0.8, 0.4, 0.6, "cadmium plated")),
    (r"NICKEL", ("#cdd0d2", 0.9, 0.3, 0.7, "nickel plated")),
    (r"PHOSPHAT|PARKERIZ|MANGANESE", ("#3a3d40", 0.3, 0.75, 0.25, "phosphate")),
    (r"BLACK OXIDE|OXIDE|BLACKEN", ("#1e1e1e", 0.4, 0.55, 0.3, "black oxide")),
    (r"ANODIZ", (None, 0.5, 0.4, 0.5, "anodized")),
    (r"\bPAINT|ENAMEL|PRIMER|\bCARC\b|POWDER COAT", (None, 0.0, 0.85, 0.1, "painted")),
]


def _color_from(blob):
    for name, hx in MULTI_COLORS:
        if name in blob: return hx, name.title()
    m = re.search(r"COLOR[^:]*:\s*([A-Z][A-Z ]{2,})", blob)
    if m:
        words = m.group(1).strip()
        for name, hx in MULTI_COLORS:
            if name in words: return hx, name.title()
        first = words.split()[0]
        if first in COLORS: return COLORS[first], first.title()
    # bare colour words anywhere
    for c in ("OLIVE DRAB", "BLACK", "OLIVE", "GREEN", "RED", "GRAY", "GREY", "TAN", "SAND", "BROWN", "WHITE", "YELLOW"):
        if re.search(r"\b" + c + r"\b", blob): return (COLORS.get(c.split()[0]) or "#3b3b22"), c.title()
    return None, None


def material_for(characteristics, name=""):
    """Parse a material spec from FLIS characteristics (+ name). Returns the colour + procedural finish."""
    blob = ((characteristics or "") + " " + (name or "")).upper()
    color, color_label = _color_from(blob)
    metal = rough = sheen = None; mat_label = None; base_color = None
    mm = re.search(r"MATERIAL[^:]*:\s*([A-Z][A-Z 0-9,/.\-]{2,})", blob)
    mtext = mm.group(1) if mm else blob
    for pat, (me, ro, sh, col, lab) in MATERIALS:
        if re.search(pat, mtext):
            metal, rough, sheen, base_color, mat_label = me, ro, sh, col, lab; break
    fin_label = None
    for pat, (col, me, ro, sh, lab) in FINISHES:
        if re.search(pat, blob):
            fin_label = lab
            if col: base_color = col          # plating/oxide overrides the colour
            metal = me if metal is None else max(metal, 0) if False else me
            rough = ro; sheen = sh
            break
    if metal is None:                          # nothing recognised -> representative metal-ish
        metal, rough, sheen = 0.4, 0.5, 0.4
    fill = color or base_color or "#8a9099"
    found = bool(color_label or mat_label or fin_label)
    # GL material: [specStrength, shininess(power), metallic]
    shininess = round(8 + (1 - rough) * 88)
    spec = round(0.15 + max(metal, sheen or 0) * 0.65, 2)
    label_bits = [b for b in (color_label, mat_label, fin_label) if b]
    return {"found": found, "color": fill, "color_label": color_label, "material": mat_label,
            "finish": fin_label, "metal": round(metal, 2), "rough": round(rough, 2),
            "sheen": round(sheen or 0, 2), "gl": [spec, shininess, round(metal, 2)],
            "label": " · ".join(label_bits) if label_bits else "representative finish"}


def part_material(nsn, characteristics="", name=""):
    """Resolve an NSN's material from FLIS characteristics (ref_nsn) when not passed in."""
    ch = characteristics or ""; nm = name or ""
    if core is not None and (nsn and not ch):
        con = core.db()
        try:
            r = con.execute("SELECT characteristics, item_name FROM ref_nsn WHERE nsn=? LIMIT 1", (nsn,)).fetchone()
            if r:
                ch = r["characteristics"] or ""; nm = nm or (r["item_name"] or "")
        except Exception:
            pass
        finally:
            try: con.close()
            except Exception: pass
    out = material_for(ch, nm); out["nsn"] = nsn; return out
