"""nsndecode.py -- decode the STRUCTURE of a NATO Stock Number (roadmap Vol.2 #51/#52). Every NSN is
13 digits: a 4-digit Federal Supply Classification (FSC) + a 9-digit National Item Identification Number
(NIIN). The FSC splits into a 2-digit Federal Supply Group (FSG) + 2-digit class; the NIIN begins with a
2-digit National Codification Bureau (NCB) code that says which country codified the item, then 7 serial
digits. This decoder is DETERMINISTIC -- the split and the group/country names come from the published
FSG list and NATO NCB-code list, never inferred.

R13 discipline: the FSG is named from the standard 2-digit group list (complete), the NCB is named from a
CURATED set of well-established country codes; for a group or NCB we don't carry we return the code with a
null name (never a fabricated country/name). We do NOT claim what the specific item is -- that is PUBLOG's
job (see publog.py). decode() and is_valid_nsn() are pure and unit-testable."""

from __future__ import annotations
import re

# Federal Supply Groups (2-digit) -- the published FSG list (complete for assigned groups).
_FSG = {
    "10": "Weapons", "11": "Nuclear ordnance", "12": "Fire control equipment",
    "13": "Ammunition and explosives", "14": "Guided missiles",
    "15": "Aerospace craft and structural components", "16": "Aircraft components and accessories",
    "17": "Aircraft launching, landing, and ground handling equipment", "18": "Space vehicles",
    "19": "Ships, small craft, pontoons, and floating docks", "20": "Ship and marine equipment",
    "22": "Railway equipment", "23": "Ground effect vehicles, motor vehicles, trailers, and cycles",
    "24": "Tractors", "25": "Vehicular equipment components", "26": "Tires and tubes",
    "28": "Engines, turbines, and components", "29": "Engine accessories",
    "30": "Mechanical power transmission equipment", "31": "Bearings",
    "32": "Woodworking machinery and equipment", "34": "Metalworking machinery",
    "35": "Service and trade equipment", "36": "Special industry machinery",
    "37": "Agricultural machinery and equipment",
    "38": "Construction, mining, excavating, and highway maintenance equipment",
    "39": "Materials handling equipment", "40": "Rope, cable, chain, and fittings",
    "41": "Refrigeration, air conditioning, and air circulating equipment",
    "42": "Firefighting, rescue, and safety equipment", "43": "Pumps and compressors",
    "44": "Furnace, steam plant, and drying equipment; nuclear reactors",
    "45": "Plumbing, heating, and sanitation equipment",
    "46": "Water purification and sewage treatment equipment", "47": "Pipe, tubing, hose, and fittings",
    "48": "Valves", "49": "Maintenance and repair shop equipment", "51": "Hand tools",
    "52": "Measuring tools", "53": "Hardware and abrasives",
    "54": "Prefabricated structures and scaffolding", "55": "Lumber, millwork, plywood, and veneer",
    "56": "Construction and building materials",
    "58": "Communications, detection, and coherent radiation equipment",
    "59": "Electrical and electronic equipment components",
    "60": "Fiber optics materials, components, assemblies, and accessories",
    "61": "Electric wire, and power and distribution equipment", "62": "Lighting fixtures and lamps",
    "63": "Alarm, signal, and security detection systems",
    "65": "Medical, dental, and veterinary equipment and supplies",
    "66": "Instruments and laboratory equipment", "67": "Photographic equipment",
    "68": "Chemicals and chemical products", "69": "Training aids and devices",
    "70": "General purpose information technology equipment (incl. firmware, software, supplies)",
    "71": "Furniture", "72": "Household and commercial furnishings and appliances",
    "73": "Food preparation and serving equipment",
    "74": "Office machines, text processing systems, and visible record equipment",
    "75": "Office supplies and devices", "76": "Books, maps, and other publications",
    "77": "Musical instruments, phonographs, and home-type radios",
    "78": "Recreational and athletic equipment", "79": "Cleaning equipment and supplies",
    "80": "Brushes, paints, sealers, and adhesives",
    "81": "Containers, packaging, and packing supplies",
    "83": "Textiles, leather, furs, apparel and shoe findings, tents, and flags",
    "84": "Clothing, individual equipment, and insignia", "85": "Toiletries",
    "87": "Agricultural supplies", "88": "Live animals", "89": "Subsistence (food)",
    "91": "Fuels, lubricants, oils, and waxes", "93": "Nonmetallic fabricated materials",
    "94": "Nonmetallic crude materials", "95": "Metal bars, sheets, and shapes",
    "96": "Ores, minerals, and their primary products", "99": "Miscellaneous",
}

# National Codification Bureau codes (first 2 digits of the NIIN) -- CURATED, well-established set.
_NCB = {
    "00": "United States", "01": "United States", "11": "NATO (NSPA-assigned)",
    "12": "Germany", "13": "Belgium", "14": "France", "15": "Italy", "17": "Netherlands",
    "21": "Canada", "22": "Denmark", "23": "Greece", "24": "Iceland", "25": "Norway",
    "26": "Portugal", "27": "Turkey", "28": "Luxembourg", "66": "Australia",
    "98": "New Zealand", "99": "United Kingdom",
}

_NSN_RX = re.compile(r"\b(\d{4})[-\s]?(\d{2})[-\s]?(\d{3})[-\s]?(\d{4})\b")


def _digits(nsn):
    return re.sub(r"\D", "", nsn or "")


def is_valid_nsn(nsn) -> bool:
    """True iff the token is 13 digits (with optional dashes/spaces in the standard grouping)."""
    return len(_digits(nsn)) == 13


def decode(nsn) -> dict:
    """Decode NSN structure. Returns {nsn, valid, fsc, fsg, fsg_name, class, ncb, ncb_country, niin,
    item_serial}. fsg_name / ncb_country are None when we don't carry that code (never fabricated).
    Returns {'valid': False} for a non-NSN token."""
    d = _digits(nsn)
    if len(d) != 13:
        return {"nsn": nsn, "valid": False}
    fsc, niin = d[:4], d[4:]
    fsg, cls = fsc[:2], fsc[2:]
    ncb = niin[:2]
    return {
        "nsn": "%s-%s-%s-%s" % (d[:4], d[4:6], d[6:9], d[9:]),
        "valid": True,
        "fsc": fsc,
        "fsg": fsg,
        "fsg_name": _FSG.get(fsg),                 # None if unassigned group -> not fabricated
        "class": cls,
        "ncb": ncb,
        "ncb_country": _NCB.get(ncb),              # None if code not in curated set
        "niin": niin,
        "item_serial": niin[2:],
    }


def scan(text, cap=40):
    """Find every NSN-shaped token in text -> list of decode() dicts, deduped."""
    out, seen = [], set()
    for m in _NSN_RX.finditer(text or ""):
        d = _digits(m.group(0))
        if d in seen:
            continue
        seen.add(d)
        out.append(decode(m.group(0)))
        if len(out) >= cap:
            break
    return out


# --------------------------------------------------------------------------- #
# self-test: `python nsndecode.py`                                            #
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    # 2320-01-565-4055 -> FSG 23 (vehicles), US-codified (NCB 01)
    r = decode("2320-01-565-4055")
    assert r["valid"] and r["fsc"] == "2320" and r["fsg"] == "23", r
    assert r["fsg_name"].startswith("Ground effect vehicles"), r
    assert r["ncb"] == "01" and r["ncb_country"] == "United States", r
    assert r["niin"] == "015654055" and r["item_serial"] == "5654055", r
    print("decode 2320-01-565-4055 OK -> FSG %s (%s), NCB %s (%s)"
          % (r["fsg"], r["fsg_name"][:20], r["ncb"], r["ncb_country"]))

    # accepts undashed 13-digit
    r2 = decode("5330014567890")
    assert r2["valid"] and r2["fsg"] == "53" and r2["nsn"] == "5330-01-456-7890", r2
    print("decode undashed OK -> %s (%s)" % (r2["nsn"], r2["fsg_name"][:18]))

    # UK-codified NCB 99
    r3 = decode("1005-99-123-4567")
    assert r3["ncb_country"] == "United Kingdom", r3
    print("decode NCB 99 OK -> %s" % r3["ncb_country"])

    # assigned FSG group named; unassigned group + uncurated NCB -> code returned, name None (never fabricated)
    r4 = decode("2410-01-000-0001")
    assert r4["valid"] and r4["fsg"] == "24" and r4["fsg_name"] == "Tractors", r4
    r4b = decode("2130-01-000-0001")            # FSG 21 is unassigned in the standard list
    assert r4b["valid"] and r4b["fsg"] == "21" and r4b["fsg_name"] is None, r4b
    r5 = decode("9999-88-000-0001")
    assert r5["fsg_name"] == "Miscellaneous", r5
    r6 = decode("1000-45-000-0001")
    assert r6["ncb"] == "45" and r6["ncb_country"] is None, "must not fabricate an NCB country"
    print("R13 OK -> uncurated NCB 45 returns code with country=None (no fabrication)")

    # not an NSN
    assert decode("just words")["valid"] is False
    assert is_valid_nsn("2320-01-565-4055") and not is_valid_nsn("2320-01-565")

    found = scan("Replace pump 4320-01-450-1234 and filter 2940-00-111-2222 per the TM.")
    assert len(found) == 2 and all(x["valid"] for x in found), found
    print("scan OK -> %d NSNs (%s / %s)" % (len(found), found[0]["fsg_name"][:12], found[1]["fsg_name"][:12]))
    print("nsndecode self-test PASS")

# END OF FILE
