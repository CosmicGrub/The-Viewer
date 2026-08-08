#!/usr/bin/env python3
"""Per-module smoke tests for the v0.96 engine/features/ package + the 0.99 Living-Schematic additions.
Confirms every feature module imports, the registry is populated, the new routes are registered, and the
schemreview sidecar round-trips. Self-contained; no corpus. Run: python tests/test_features_modules.py"""
import os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
import viewer_app as V  # noqa: F401  -> triggers features/routes registration

passed, failed = [], []
def ok(n, c): (passed if c else failed).append(n)

# every feature module imports cleanly
for mod in ("search_feature", "parts_feature", "browse_feature", "procedures_feature",
            "render_feature", "ingest_feature", "sessions_feature", "registry", "routes"):
    try:
        __import__("features." + mod); ok("import features.%s" % mod, True)
    except Exception as e:
        failed.append("import features.%s (%s)" % (mod, e))

# registry populated + the new Living-Schematic routes registered
try:
    from features import registry as REG
    ok("registry_get_populated", len(REG.GET) >= 100)
    ok("registry_post_populated", len(REG.POST) >= 8)
    for p in ("/api/schemgraph", "/api/schemgraph_review", "/api/schemgraph_coverage"):
        ok("GET " + p, p in REG.GET)
    ok("POST /api/schemgraph_review_decision", "/api/schemgraph_review_decision" in REG.POST)
except Exception as e:
    failed.append("registry(%s)" % e)

# schemreview sidecar round-trip + coverage summary
try:
    import schemreview as R
    d = tempfile.mkdtemp(prefix="schemrev_")
    open(os.path.join(d, "schemgraph_coverage.tsv"), "w").write(
        "doc_id\tpage\tsegments\tnodes\tedges\tnets\tcomponents\tconfidence\n"
        "5\t3\t200\t40\t150\t6\t0\t0.82\n5\t4\t180\t44\t160\t7\t12\t0.90\n")
    q = R.queue(d, 200, 0)
    ok("review_queue_flags_no_comp", q["pending"] == 1 and q["items"][0]["page"] == 3)
    ok("review_record", R.record(d, 5, 3, "corrected", labels=[{"ref": "R7", "x": 0.5, "y": 0.4}])["ok"])
    ov = R.overrides_for(d, 5, 3)
    ok("review_override", ov and ov["verdict"] == "corrected" and ov["labels"][0]["ref"] == "R7")
    cs = R.coverage_summary(d)
    ok("coverage_summary", cs["schematic_pages"] == 2 and cs["pages_with_components"] == 1 and cs["pages_reviewed"] == 1)
    ok("review_bad_verdict_rejected", R.record(d, 1, 1, "maybe")["ok"] is False)
except Exception as e:
    failed.append("schemreview(%s)" % e)

for n in passed: print("PASS", n)
for n in failed: print("FAIL", n)
print("\n%d passed, %d failed (of %d module checks)" % (len(passed), len(failed), len(passed) + len(failed)))
sys.exit(1 if failed else 0)
