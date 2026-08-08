"""faulttree.py -- turn a manual's TROUBLESHOOTING content into an interactive fault tree. Army-style TMs
lay troubleshooting out as MALFUNCTION -> (STEP n) TEST OR INSPECTION -> CORRECTIVE ACTION. This module
parses that structure out of the OCR text so the app can present it as a guided decision walk: pick the
symptom, step through the checks, and land on the corrective action (which links onward to the part and
the procedure). Cited to the manual page throughout.

parse(text) is pure and unit-testable; find_for_query() runs it over FTS-matched troubleshooting pages.
Read-only, offline. v1.13.0: retrieval moved to features.corpus -- no direct sqlite here anymore."""

from __future__ import annotations
import re

_MALF = re.compile(r"^\s*MALFUNCTION\b[\s:.\-]*(.*)$", re.I)
_SYMPTOM = re.compile(r"^\s*SYMPTOM\b[\s:.\-]*(.*)$", re.I)
_STEP = re.compile(r"^\s*STEP\s*(\d+)\b[\s:.\-]*(.*)$", re.I)
_CORR = re.compile(r"^\s*(?:CORRECTIVE\s+ACTION|ACTION)\b[\s:.\-]*(.*)$", re.I)
_NOISE = re.compile(r"^\s*(TEST OR INSPECTION|TROUBLESHOOTING|TABLE\s|WARNING|CAUTION|NOTE)\b", re.I)


def _clean(s):
    return re.sub(r"\s+", " ", (s or "")).strip(" .-:\t")


def parse(text, cap=40):
    """Extract fault-tree entries from troubleshooting text.
    -> [{symptom, steps:[{n, test, action}]}]. Robust to OCR noise; best-effort."""
    if not text:
        return []
    lines = text.split("\n")
    entries, cur, pending_step = [], None, None

    def close_step():
        nonlocal pending_step
        if cur is not None and pending_step is not None and (pending_step.get("test") or pending_step.get("action")):
            cur["steps"].append(pending_step)
        pending_step = None

    def close_entry():
        nonlocal cur
        close_step()
        if cur is not None and (cur["symptom"] or cur["steps"]):
            entries.append(cur)
        cur = None

    for i, ln in enumerate(lines):
        mm = _MALF.match(ln)
        ms = _SYMPTOM.match(ln)
        if mm or ms:
            close_entry()
            sym = _clean((mm.group(1) if mm else ms.group(1)))
            if not sym:                         # symptom on the following line(s)
                for j in range(i + 1, min(i + 3, len(lines))):
                    nxt = _clean(lines[j])
                    if nxt and not _STEP.match(lines[j]) and not _NOISE.match(lines[j]):
                        sym = nxt; break
            cur = {"symptom": sym, "steps": []}
            continue
        st = _STEP.match(ln)
        if st and cur is not None:
            close_step()
            pending_step = {"n": int(st.group(1)), "test": _clean(st.group(2)), "action": ""}
            continue
        cr = _CORR.match(ln)
        if cr is not None and pending_step is not None:
            pending_step["action"] = _clean(cr.group(1))
            continue
        # continuation text -> attach to the open step (action if the test is set), else to symptom
        txt = _clean(ln)
        if not txt or _NOISE.match(ln):
            continue
        if pending_step is not None:
            if pending_step["test"] and not pending_step["action"]:
                pending_step["action"] = txt
            elif not pending_step["test"]:
                pending_step["test"] = txt
        elif cur is not None and not cur["symptom"]:
            cur["symptom"] = txt
        if len(entries) >= cap:
            break
    close_entry()
    return [e for e in entries if e["symptom"]][:cap]


def find_for_query(db_path, q, limit=25):
    """FTS-match troubleshooting pages for `q`, parse fault trees, cite each. Returns {query, count, trees}."""
    q = (q or "").strip()
    if len(q) < 2:
        return {"query": q, "count": 0, "trees": []}
    terms = [t for t in re.findall(r"[A-Za-z0-9]+", q) if len(t) > 1]
    match = "(" + " OR ".join(terms) + ")" + ' AND (MALFUNCTION OR "CORRECTIVE ACTION" OR troubleshooting)' if terms else q
    trees = []
    try:                                              # v1.13: shared corpus retrieval (leak-proof)
        from features import corpus as _corpus
        rows = _corpus.fts_pages(match, limit=limit, with_body=True, db_path=db_path)
    except Exception as e:
        return {"query": q, "count": 0, "trees": [], "error": str(e)}
    for r in rows:
        for e in parse(r["body_text"] or ""):
            if not e["steps"] and not e["symptom"]:
                continue
            e["doc"] = r["doc_id"]; e["tm"] = r["tm_number"]; e["vehicle"] = r["vehicle"]; e["page"] = r["page_number"]
            e["page_url"] = "/deepzoom?doc=%s&page=%s" % (r["doc_id"], r["page_number"])
            trees.append(e)
    return {"query": q, "count": len(trees), "trees": trees[:limit]}


# --------------------------------------------------------------------------- #
# self-test: `python faulttree.py`                                            #
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    sample = (
        "TROUBLESHOOTING\n"
        "MALFUNCTION\n"
        "ENGINE WILL NOT CRANK\n"
        "STEP 1. Check that the battery cables are tight and free of corrosion.\n"
        "If loose or corroded, clean and tighten the cables.\n"
        "STEP 2. Check battery state of charge with a voltmeter.\n"
        "CORRECTIVE ACTION. If below 12.4 V, recharge or replace the battery.\n"
        "MALFUNCTION\n"
        "ENGINE CRANKS BUT WILL NOT START\n"
        "STEP 1. Check the fuel level.\n"
        "If empty, refuel and prime the system.\n")
    trees = parse(sample)
    assert len(trees) == 2, trees
    assert trees[0]["symptom"].startswith("ENGINE WILL NOT CRANK"), trees[0]
    assert len(trees[0]["steps"]) == 2, trees[0]["steps"]
    assert "battery cables" in trees[0]["steps"][0]["test"].lower(), trees[0]["steps"][0]
    assert "clean and tighten" in trees[0]["steps"][0]["action"].lower(), trees[0]["steps"][0]
    assert "recharge or replace" in trees[0]["steps"][1]["action"].lower(), trees[0]["steps"][1]
    assert trees[1]["symptom"].startswith("ENGINE CRANKS"), trees[1]
    print("faulttree parse OK -> %d symptoms; first has %d checks" % (len(trees), len(trees[0]["steps"])))
    for s in trees[0]["steps"]:
        print("   STEP %d: %s -> %s" % (s["n"], s["test"][:40], s["action"][:40]))
    print("faulttree self-test PASS")

# END OF FILE
