#!/usr/bin/env python3
"""THE VIEWER -- FEATURE CONGRUENCY (v0.99.15). As new features meld into the project, assert they actually fit
together: every cross-link a feature emits must resolve to a route the app really serves, the new routes/pages are
registered, and the look-alike logic is consistent between the cover warning and the per-part flag. This is the
"do the pieces mesh?" test, complementary to audit_features.py ("is anything dead?").

Runs HOST-side (imports the grown viewer_app/jobcard; the sandbox mount truncates those). Self-contained; a tiny
synthetic index, no corpus. Run: python tests/test_congruency.py"""
import os, re, sys, tempfile, sqlite3
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))

passed, failed = [], []
def ck(n, c): (passed if c else failed).append(n)

import viewer_app  # noqa: F401  triggers registration
from features import routes as R
from features import registry as REG

KNOWN = set(REG.GET) | set(REG.POST) | set(R._SCRIPTS)
for paths, _ in R._PAGES.items():
    for p in paths:
        KNOWN.add(p)

def base(u):
    return (u or "").split("?")[0].split("#")[0].rstrip("/") or "/"

# --- 1. the new routes/pages are all registered -----------------------------------------------------
for r in ["/api/figureparts", "/api/jobcard", "/api/jobcard_preview", "/api/figuresheet",
          "/api/partlocate", "/api/coverage", "/api/partdiff", "/api/suggest"]:
    ck("route registered " + r, r in REG.GET)
for p in ["/jobcard", "/locate", "/coverage", "/deepzoom", "/partdiff", "/dossier", "/procedure", "/ingest"]:
    ck("page reachable " + p, p in KNOWN)

# --- 2. figureparts emits congruent cross-links (→ real routes) -------------------------------------
def _mkdb():
    d = tempfile.mkdtemp(prefix="cong_"); db = os.path.join(d, "v.db"); c = sqlite3.connect(db)
    c.execute("CREATE TABLE documents(id INTEGER PRIMARY KEY, path TEXT, vehicle TEXT, tm_number TEXT, title TEXT)")
    c.execute("CREATE TABLE parts(id INTEGER PRIMARY KEY, document_id INT, page INT, nsn TEXT, part_number TEXT, name TEXT, nomenclature TEXT, cagec TEXT, smr TEXT, uoc TEXT, fig_no TEXT, fig_title TEXT)")
    c.execute("INSERT INTO documents(id,path,vehicle,tm_number,title) VALUES(1,'/x/a.pdf','HMMWV','TM 9','T')")
    c.executemany("INSERT INTO parts(document_id,page,nsn,part_number,name,cagec,smr,fig_no,fig_title) VALUES(?,?,?,?,?,?,?,?,?)", [
        (1, 12, '5305-01-111-1111', 'B1', 'BOLT', '19207', 'PAOZZ', 'FIG 5', 'ELEC'),
        (1, 12, '2920-01-333-3333', 'A1', 'ALTERNATOR', '19207', 'PAOZZ', 'FIG 5', 'ELEC')])
    c.commit(); c.close(); return db

try:
    import figureparts
    db = _mkdb()
    parts = figureparts.parts_on(db, 1, 12).get("parts", [])
    ck("figureparts returns parts", len(parts) == 2)
    for pt in parts:
        for key in ("dossier_url", "locate_url"):
            u = pt.get(key)
            if u:
                ck("figureparts.%s -> known route (%s)" % (key, base(u)), base(u) in KNOWN)
except Exception as e:
    failed.append("figureparts congruency (%s)" % e)

# --- 3. jobcard: per-part look-alike flag is congruent with the cover warning + links to /partdiff --
try:
    import jobcard
    la = {"found": True, "n_variants": 2, "nomenclature": "ALTERNATOR", "discriminators": [{"field": "UOC"}],
          "variants": [{"relation": "different variant", "nsn": "2920-01-999-9999"}, {"relation": "reference", "nsn": "2920-01-333-3333"}]}
    warn = jobcard._lookalike_warning(la)
    flagged = jobcard._flag_lookalikes([{"name": "ALTERNATOR", "nsn": "2920-01-333-3333"}, {"name": "BOLT", "nsn": "5305-01-111-1111"}], la)
    ck("warning + flag agree (both fire on real diff)", bool(warn) and flagged[0].get("lookalike") and not flagged[1].get("lookalike"))
    # format-drift: neither warns nor flags
    la2 = {"found": True, "n_variants": 2, "nomenclature": "NUT", "variants": [{"relation": "same item (format drift)", "nsn": "x"}], "discriminators": []}
    f2 = jobcard._flag_lookalikes([{"name": "NUT", "nsn": "x"}], la2)
    ck("warning + flag agree (both silent on format drift)", jobcard._lookalike_warning(la2) is None and not f2[0].get("lookalike"))
    ck("/partdiff exists for the per-part compare link", "/partdiff" in KNOWN)
except Exception as e:
    failed.append("jobcard congruency (%s)" % e)

# --- 4. palette commands all point to routes the app serves -----------------------------------------
try:
    pal = open(os.path.join(HERE, "..", "ui", "palette.js"), encoding="utf-8").read()
    urls = re.findall(r'url:"(/[^"]*)"', pal) + re.findall(r'go\("(/[^"?]*)', pal)
    ck("palette exposes commands", len(urls) >= 10)
    bad = sorted({base(u) for u in urls if base(u) not in KNOWN and not base(u).startswith("/api/")})
    ck("every palette destination resolves to a real route" + (" (bad: %s)" % bad if bad else ""), not bad)
except Exception as e:
    failed.append("palette congruency (%s)" % e)

for n in passed: print("PASS", n)
for n in failed: print("FAIL", n)
print("\n%d passed, %d failed (of %d congruency checks)" % (len(passed), len(failed), len(passed) + len(failed)))
sys.exit(1 if failed else 0)
# END OF FILE
