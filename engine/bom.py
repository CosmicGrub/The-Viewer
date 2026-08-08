"""bom.py -- complete KIT / bill-of-materials builder for a job (brief-req: logistics). A mechanic walking to
the bay needs EVERYTHING in one list: the parts (with NSNs + quantities), the consumables the job always eats
(gaskets, seals, O-rings, cotter pins, lubricants, sealant), and the tools. This aggregates those from the
part list + the procedure text into one deduplicated, categorized kit that drops into the job package.

build_kit() is pure and unit-testable; the route feeds it figureparts + procedure data. Read-only."""

from __future__ import annotations
import re

# consumables a job typically requires -- flagged from procedure text so they aren't forgotten
_CONSUMABLE = re.compile(
    r"\b(gasket|seal|o-?ring|cotter\s*pin|lock\s*washer|split\s*pin|retaining\s*ring|snap\s*ring|"
    r"grease|lubricant|oil|sealant|thread\s*locker|loctite|anti-?seize|rtv|packing|shim|"
    r"lock\s*nut|self-?locking\s*nut|safety\s*wire|tie\s*wrap)\b", re.I)


def _norm(s):
    return " ".join((s or "").strip().lower().split())


def find_consumables(text, cap=20):
    """Pull the consumables a procedure mentions -> deduped list of {item, note}."""
    out, seen = [], set()
    for m in _CONSUMABLE.finditer(text or ""):
        item = m.group(1).lower().replace("  ", " ")
        item = re.sub(r"\s+", " ", item)
        key = item.replace("-", "")
        if key in seen:
            continue
        seen.add(key)
        s = max(0, m.start() - 20)
        out.append({"item": item, "note": (text[s:m.end() + 20].strip() if text else "")})
        if len(out) >= cap:
            break
    return out


def build_kit(parts=None, tools=None, consumables=None, warnings=None):
    """Aggregate into one categorized, deduped kit.
      parts: [{nsn, part_number, name, qty?}]  tools: [str]  consumables: [{item,note} | str]
      warnings: v1.13 (#41/#42) -- one-time-use / torque-to-yield fastener flags from oneuse.py
                ([{kind, sentence, doc_id, tm, page, ...}]); passed through deduped by
                (kind, sentence) so the kit itself says which fasteners MUST be replaced,
                each with its cited sentence (R13: extractive, never inferred here).
    -> a dict with parts, tools, consumables, warnings, and counts."""
    # parts: dedup by (nsn or name), accumulate qty
    pmap = {}
    for p in parts or []:
        key = (p.get("nsn") or p.get("part_number") or _norm(p.get("name")) or "").upper()
        if not key:
            continue
        if key not in pmap:
            pmap[key] = {"nsn": p.get("nsn"), "part_number": p.get("part_number"),
                         "name": p.get("name") or p.get("nomenclature") or "", "qty": 0}
        pmap[key]["qty"] += int(p.get("qty") or 1)
    # tools: dedup, keep order
    tset, tools_out = set(), []
    for t in tools or []:
        k = _norm(t)
        if k and k not in tset:
            tset.add(k); tools_out.append(t.strip())
    # consumables: dedup by item text
    cset, cons_out = set(), []
    for c in consumables or []:
        item = c["item"] if isinstance(c, dict) else c
        note = c.get("note", "") if isinstance(c, dict) else ""
        k = _norm(item).replace("-", "")
        if k and k not in cset:
            cset.add(k); cons_out.append({"item": item, "note": note})
    # warnings: dedup by (kind, sentence); keep order (cited safety flags, pass-through)
    wseen, warns_out = set(), []
    for w in warnings or []:
        if not isinstance(w, dict):
            continue
        k = (w.get("kind") or "", (w.get("sentence") or "").strip())
        if not k[1] or k in wseen:
            continue
        wseen.add(k); warns_out.append(w)
    parts_out = sorted(pmap.values(), key=lambda x: (x["name"] or ""))
    return {"parts": parts_out, "tools": tools_out, "consumables": cons_out, "warnings": warns_out,
            "counts": {"parts": len(parts_out), "tools": len(tools_out), "consumables": len(cons_out),
                       "warnings": len(warns_out), "total_pieces": sum(p["qty"] for p in parts_out)}}


# --------------------------------------------------------------------------- #
# self-test: `python bom.py`                                                  #
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    cons = find_consumables("Remove and discard the gasket. Coat the new O-ring with grease. Install a new "
                            "cotter pin. Apply thread locker to the bolt. Replace the gasket seal.")
    kinds = {c["item"] for c in cons}
    assert "gasket" in kinds and "o-ring" in kinds and "cotter pin" in kinds and "thread locker" in kinds, kinds
    print("find_consumables OK ->", sorted(kinds))

    parts = [{"nsn": "5310-01-000-0001", "name": "WASHER", "qty": 4},
             {"nsn": "5310-01-000-0001", "name": "WASHER", "qty": 2},   # dup -> qty accumulates
             {"nsn": "2920-01-000-0002", "name": "ALTERNATOR"}]
    kit = build_kit(parts, tools=["1/2in socket", "torque wrench", "1/2in socket"], consumables=cons)
    washer = [p for p in kit["parts"] if p["name"] == "WASHER"][0]
    assert washer["qty"] == 6, washer                       # 4+2
    assert kit["counts"]["parts"] == 2, kit["counts"]       # deduped
    assert kit["counts"]["tools"] == 2, kit["counts"]       # socket deduped
    assert kit["counts"]["total_pieces"] == 7, kit["counts"]
    print("build_kit OK -> %d parts (%d pieces), %d tools, %d consumables"
          % (kit["counts"]["parts"], kit["counts"]["total_pieces"], kit["counts"]["tools"], kit["counts"]["consumables"]))

    # v1.13 (#41/#42): oneuse warnings pass through deduped, cited sentence intact
    w = [{"kind": "one_time_use", "sentence": "Head bolts must not be reused.", "tm": "TM-X", "page": 88},
         {"kind": "one_time_use", "sentence": "Head bolts must not be reused.", "tm": "TM-X", "page": 88},  # dup
         {"kind": "torque_to_yield", "sentence": "Torque-to-yield; install new bolts.", "tm": "TM-X", "page": 88}]
    kit2 = build_kit(parts, warnings=w)
    assert kit2["counts"]["warnings"] == 2 and len(kit2["warnings"]) == 2, kit2["warnings"]
    assert kit2["warnings"][0]["sentence"] == "Head bolts must not be reused.", kit2["warnings"]
    assert build_kit(parts)["warnings"] == [], "no warnings -> empty list (back-compat)"
    print("build_kit warnings OK -> deduped %d cited flag(s)" % kit2["counts"]["warnings"])
    print("bom self-test PASS")

# END OF FILE
