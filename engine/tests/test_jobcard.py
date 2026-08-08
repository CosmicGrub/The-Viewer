#!/usr/bin/env python3
"""Regression tests for the v0.99.8–0.99.10 work-order stack: figureparts dedup, jobcard task-intent /
ordering / look-alike warning / preview, and the enriched procedure parser (materials + referenced manuals).
Self-contained; builds a tiny synthetic index — no corpus. Run host-side (VERIFY-099.bat): python tests/test_jobcard.py"""
import os, sys, sqlite3, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))

passed, failed = [], []
def ok(n, c): (passed if c else failed).append(n if c else n)
def check(n, c):
    (passed if c else failed).append(n)


def _mkdb():
    d = tempfile.mkdtemp(prefix="jobcard_"); db = os.path.join(d, "v.db")
    c = sqlite3.connect(db)
    c.execute("CREATE TABLE documents(id INTEGER PRIMARY KEY, path TEXT, vehicle TEXT, tm_number TEXT, title TEXT)")
    c.execute("CREATE TABLE parts(id INTEGER PRIMARY KEY, document_id INT, page INT, nsn TEXT, part_number TEXT, "
              "name TEXT, nomenclature TEXT, cagec TEXT, smr TEXT, uoc TEXT, fig_no TEXT, fig_title TEXT)")
    c.execute("INSERT INTO documents(id,path,vehicle,tm_number,title) VALUES(1,'/x/a.pdf','HMMWV M998','TM 9-2320-280-24P','MAINT')")
    rows = [
        (1, 12, '5305-01-111-1111', 'B1', 'BOLT', '19207', 'PAOZZ', 'FIG 5', 'ELECTRICAL'),
        (1, 12, '5310-01-222-2222', 'N1', 'NUT', '19207', 'PAOZZ', 'FIG 5', 'ELECTRICAL'),
        (1, 12, '5305-01-111-1111', 'B1', 'BOLT', '19207', 'PAOZZ', 'FIG 5', 'ELECTRICAL'),   # dup
        (1, 44, '2920-01-333-3333', 'A1', 'ALTERNATOR', '19207', 'PAOZZ', 'FIG 12', 'WIRING'),
    ]
    c.executemany("INSERT INTO parts(document_id,page,nsn,part_number,name,cagec,smr,fig_no,fig_title) "
                  "VALUES(?,?,?,?,?,?,?,?,?)", rows)
    c.commit(); c.close(); return db


# ---- figureparts: dedup + figure metadata --------------------------------------------------------
try:
    import figureparts
    db = _mkdb()
    r = figureparts.parts_on(db, 1, 12)
    check("figureparts_dedup", r["count"] == 2)                       # BOLT twice -> once
    check("figureparts_fig_meta", r["fig_no"] == "FIG 5")
    check("figureparts_nsn_first", (r["parts"][0]["nsn"] or "") != "")
    check("figureparts_urls", r["parts"][0]["dossier_url"].startswith("/dossier?q="))
    r0 = figureparts.parts_on(db, 1, 999)
    check("figureparts_empty_page", r0["count"] == 0)
    rbad = figureparts.parts_on(db, "x", "y")
    check("figureparts_bad_input", rbad["count"] == 0 and "error" in rbad)
except Exception as e:
    failed.append("figureparts(%s)" % e)

# ---- jobcard: intent, ordering, look-alike warning, preview --------------------------------------
try:
    import jobcard
    i1 = jobcard._task_intent("replace the alternator")
    check("intent_replace", i1["kind"] == "Replacement" and "alternator" in i1["focus"].lower())
    i2 = jobcard._task_intent("adjust the brakes on an M1097")
    check("intent_adjust", i2["kind"] == "Adjustment")
    i3 = jobcard._task_intent("2920-01-333-3333")
    check("intent_none_for_nsn", i3["kind"] is None)

    procs = [{"kind": "Installation", "title": "INSTALL"}, {"kind": "Removal", "title": "REMOVE"}]
    order = jobcard._order_procs(procs, "Removal")
    check("order_floats_matching_kind", order[0]["kind"] == "Removal")
    check("order_noop_without_kind", [p["kind"] for p in jobcard._order_procs(procs, None)] == ["Installation", "Removal"])

    warn = jobcard._lookalike_warning({"found": True, "n_variants": 3, "nomenclature": "VALVE",
            "discriminators": [{"field": "UOC"}, {"field": "NSN"}], "variants": [{"relation": "different variant"}]})
    check("lookalike_warns_on_real_diff", bool(warn) and "LOOK-ALIKE" in warn)
    nowarn = jobcard._lookalike_warning({"found": True, "n_variants": 2,
            "variants": [{"relation": "same item (format drift)"}], "discriminators": []})
    check("lookalike_silent_on_format_drift", nowarn is None)
    check("lookalike_none_when_absent", jobcard._lookalike_warning(None) is None)

    db = _mkdb()
    pv = jobcard.preview(db, "ALTERNATOR", procs, [{"value": "30 ft-lb"}], lookalike=None)
    check("preview_shape", pv["n_procedures"] == 2 and pv["n_torque"] == 1 and "intent" in pv)

    # build_pdf smoke: valid multi-page PDF with the new sections/warning
    pr = [{"kind": "Removal", "title": "REMOVE", "vehicle": "HMMWV", "tm_number": "TM 9", "page": 10,
           "tools": ["Socket"], "materials": ["Lockwasher", "Sealant"], "references": ["TM 9-2320-280-24P"],
           "cautions": [{"kind": "WARNING", "text": "Battery off."}], "steps": ["Do a thing."]}]
    pdf = jobcard.build_pdf({"task": "remove alternator", "label": "ALTERNATOR", "nsn": "2920-01-333-3333",
                             "subtitle": "1 appearance", "intent": jobcard._task_intent("remove alternator")},
                            pr, [{"value": "30 ft-lb", "context": "Tighten.", "vehicle": "HMMWV", "tm_number": "TM 9", "page": 11}],
                            [{"name": "ALTERNATOR", "nsn": "2920-01-333-3333"}], [], warnings=["LOOK-ALIKE: test warning"])
    check("build_pdf_valid", pdf[:5] == b"%PDF-" and len(pdf) > 1500)
except Exception as e:
    failed.append("jobcard(%s)" % e)

# ---- enriched procedure parser: materials + referenced manuals -----------------------------------
try:
    from features import procedures_feature as PF
    txt = ("REMOVAL\n\nTOOLS REQUIRED\nSocket, 9/16 in\n\nMATERIALS/PARTS\nLockwasher\nGasket\n\n"
           "CAUTION: Do not pry.\n\n1. Disconnect the cable. Refer to TM 9-2320-280-24P and WP 0057.\n")
    pr = PF._parse_procedure(txt)
    check("parse_materials", "Lockwasher" in pr["materials"] and "Gasket" in pr["materials"])
    check("parse_refs_digit_anchored", "TM 9-2320-280-24P" in pr["references"] and "WP 0057" in pr["references"])
    check("parse_no_false_ref", not any(x in ("LOCKWASHER", "LOOSEN") for x in pr["references"]))
    check("parse_keeps_tools_steps", pr["tools"] and pr["steps"])
    # regression: steps-only page still parses, new keys empty (not missing)
    pr2 = PF._parse_procedure("1. Do a thing here\n2. Do another thing now")
    check("parse_regression_keys", pr2["materials"] == [] and pr2["references"] == [])
except Exception as e:
    failed.append("procedure_parse(%s)" % e)

for n in passed: print("PASS", n)
for n in failed: print("FAIL", n)
print("\n%d passed, %d failed (of %d job-card checks)" % (len(passed), len(failed), len(passed) + len(failed)))
sys.exit(1 if failed else 0)
