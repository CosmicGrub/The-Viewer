#!/usr/bin/env python3
"""Pillar tests for THE VIEWER — exercises the load-bearing logic against a deterministic
fixture index. Importable module under test = core_pillars (verbatim mirror of viewer_app
lines 1-523) so the SAME code can also be mutation-tested. Pure-stdlib runner (no pytest needed).

Pillars covered:
  P1 NSN parsing/routing      P2 keyword FTS search        P3 last-4 + full-NSN search
  P4 parts lookup (cited)     P5 reference enrichment      P6 tech-status (PMCS + history)
  P7 coverage meter           P8 correlations sidecar      P9 104th sheet PDF generation
Set MUT_TARGET to point the runner at a mutated copy of core_pillars (used by the mutation runner)."""
import os, sys, importlib, tempfile, json

HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE = os.path.dirname(HERE)
sys.path.insert(0, ENGINE); sys.path.insert(0, HERE)
import fixture

def load_module():
    name = os.environ.get("PILLAR_MODULE", "core_pillars")
    if name in sys.modules: del sys.modules[name]
    return importlib.import_module(name)

TESTS = []
def test(fn): TESTS.append(fn); return fn

def setup(M, d):
    M.DB_PATH = os.path.join(d, "viewer.db")
    M._POP_CACHE["t"] = 0.0; M._POP_CACHE["s"] = set()   # reset learned-ranking cache
    M._VOCAB_READY = False

# ---------- P1: NSN parsing / routing ----------
@test
def t_norm_nsn(M):
    assert M.norm_nsn("5305-01-674-1467") == "5305-01-674-1467"
    assert M.norm_nsn("5305016741467") == "5305-01-674-1467"          # 13 contiguous digits
    assert M.norm_nsn("part 5305-01-674-1467 ref") == "5305-01-674-1467"  # embedded, dashed
    assert M.norm_nsn("no nsn here") is None
    assert M.norm_nsn("5305 01 674 1467") is None                     # contract: space-separated NOT parsed

@test
def t_nsn_kind(M):
    assert M.nsn_kind("2320-01-272-5029") == "vehicle"   # FSC 2320 = truck
    assert M.nsn_kind("5305-01-674-1467") == "part"       # FSC 5305 = bolt

@test
def t_doc_type(M):
    assert M.doc_type("TM 9-2320-363-24P", "RPSTL.pdf") == "Parts (RPSTL)"
    assert M.doc_type("TM 9-2320-363-10", "Operator.pdf") == "Operator (-10)"
    assert M.doc_type("", "Wiring schematic.pdf") == "Schematics / wiring"

@test
def t_within1(M):
    assert M._within1("brake", "brake")
    assert M._within1("brake", "brakes")     # one insert
    assert M._within1("brake", "broke")      # one substitute
    assert not M._within1("brake", "blade")  # two+ edits

# ---------- P2/P3: search ----------
@test
def t_search_keyword(M):
    rows = M.search("brake", 25)
    assert any("brake" in (r.get("snip") or "").lower() for r in rows), "keyword search must find brake pages"

@test
def t_search_empty(M):
    assert M.search("") == [], "empty query must return no results"
    assert M.search("   ") == [], "whitespace query must return no results"

@test
def t_search_prefix(M):
    # predictive prefix: typing 'brak' must still find 'brake' (last token is a prefix match)
    rows = M.search("brak", 25)
    assert len(rows) >= 1, "prefix of the last token must predictively match"

@test
def t_search_fuzzy_typo(M):
    rows = M.search("braake", 25, use_fuzzy=True)   # 1-insert typo of brake (edit distance 1)
    assert len(rows) >= 1, "fuzzy search should tolerate a 1-edit typo"

@test
def t_search_and_precision(M):
    # "brake chamber" (AND) must require BOTH terms: page 3 has both; the operator pages have
    # only "brake". With AND-join the brake-only pages must NOT dominate as exclusive matches.
    both = M.search("brake chamber", 25)
    assert any(("brake" in (r.get("snip") or "").lower() and r.get("page_number") == 12) for r in both), \
        "AND search must find the page containing both 'brake' and 'chamber'"
    # a two-term query for terms that never co-occur on one page must return nothing under AND
    none_rows = M.search("chamber forklift", 25)   # 'chamber' only on M915 pg, 'forklift' not in text
    assert len(none_rows) == 0, "AND search must exclude pages missing one of the required terms"

@test
def t_nomenclature_helper(M):
    v = M.normalize_nomenclature("BOLT, MACHINE")
    assert any(x.lower() == "machine bolt" for x in v), "comma-inverted variant"
    assert "gasket" in M.normalize_nomenclature("gskt"), "abbr expansion"
    assert M.normalize_nomenclature("") == []

@test
def t_search_nomenclature_widen(M):
    # 'gskt' is not a prefix of 'gasket'; recall comes from abbreviation expansion widening
    rows = M.search("gskt", 25)
    assert any("gasket" in (r.get("snip") or "").lower() for r in rows), "abbr-expanded query must find 'gasket'"

@test
def t_search_full_nsn(M):
    rows = M.search("5305-01-674-1467", 25)
    assert len(rows) >= 1 and all(r.get("nsn_query") == "5305-01-674-1467" for r in rows)

@test
def t_search_last4(M):
    rows = M.search("5029", 25)   # cover NSN ends in 5029
    assert any(r.get("nsn") == "2320-01-272-5029" for r in rows), "last-4 should hit the cover NSN"

# ---------- P4: parts lookup ----------
@test
def t_nsn_aliases(M):
    al = M.nsn_aliases("5305-01-674-1467")          # NIIN 016741467 confirmed interchangeable
    assert "5303-01-674-1467" in al and "5305-01-674-1467" in al
    assert M.nsn_aliases("2530-01-367-8888") == ["2530-01-367-8888"]   # unreviewed -> no expansion

@test
def t_search_alias_expand(M):
    rows = M.search("5303-01-674-1467", 25)         # only the 5305 variant appears in pages
    assert len(rows) >= 1, "confirmed-interchangeable alias must surface the equivalent NSN's pages"
    assert any(r.get("aliases") for r in rows), "results should note the alias set"

@test
def t_part_lookup(M):
    r = M.part_lookup("5305-01-674-1467")
    assert r["found"] is True
    assert r["nomenclature"] == "BOLT, MACHINE"
    vehicles = {ref["vehicle"] for ref in r["refs"]}
    assert {"M915 Truck", "Forklift"} <= vehicles, "must cite both platforms"

# ---------- P5: reference enrichment ----------
@test
def t_reference_for(M):
    out = M.reference_for("5305-01-674-1467", "1/4-20")
    assert out["nsn"]["part_no"] == "MS35307-XYZ"
    assert out.get("versions") == 2                 # R6 append-only: prior version retained
    assert out["hardware"]["series"] == "UNC"
    # size lookup is a PREFIX match: '1/4' must find '1/4-20' (kills a suffix-LIKE mutation)
    pre = M.reference_for(None, "1/4")
    assert pre.get("hardware", {}).get("size") == "1/4-20", "hardware size must match by prefix"

# ---------- P6: tech status ----------
@test
def t_techstatus_pmcs(M):
    out = M.tech_status_suggest("M915 Truck", "service brake inoperative air leak")
    assert out["suggestion"] == "NMCS"
    assert out["basis"] == "pmcs"
    assert out["evidence"], "must cite the PMCS criterion page"

@test
def t_techstatus_history(M):
    out = M.tech_status_suggest("Forklift", "air leak somewhere")  # no PMCS on Forklift -> history
    assert out["basis"] in ("history", None)
    if out["basis"] == "history":
        assert out["suggestion"] == "NMCS"

@test
def t_techstatus_codes(M):
    out = M.tech_status_suggest("M915 Truck", "brake")
    assert out["codes"] == ["FMC", "PMCM", "PMCS", "NMCM", "NMCS"]

# ---------- P7: coverage ----------
@test
def t_coverage(M):
    cov = M.coverage("Forklift")   # 1 text/ocr page + 1 blank = 50%
    assert cov["Forklift"]["pct"] == 50

# ---------- P8: correlations sidecar ----------
@test
def t_correlations(M):
    out = M.correlations_for("5305-01-674-1467")
    assert out["interchangeable"]["n_vehicles"] == 2
    assert out["niin_review"]["niin"] == "016741467"
    held = M.correlations_for("1005-01-177-2665")
    assert held["superseded_held"] == ["1005-01-129-5768"]

# ---------- P9: 104th sheet PDF ----------
@test
def t_104th_pdf(M):
    if M.build_request_pdf is None:
        return  # reportlab not present; skip rather than fail
    out = os.path.join(tempfile.mkdtemp(), "sheet.pdf")
    M.build_request_pdf(out, {"mechanic": "SGT Test", "bumper": "A12", "tm": "TM 9-2320", "tech_status": "NMCS"},
                        [{"item_name": "BOLT, MACHINE", "nsn": "5305-01-674-1467", "qty": 2, "fig": "14"}])
    assert os.path.exists(out) and os.path.getsize(out) > 800
    assert open(out, "rb").read(5) == b"%PDF-", "must be a valid PDF"

def run():
    d = tempfile.mkdtemp(); fixture.build(d)
    M = load_module(); setup(M, d)
    passed = []; failed = []
    for fn in TESTS:
        try:
            setup(M, d); fn(M); passed.append(fn.__name__)
        except AssertionError as e:
            failed.append((fn.__name__, "assert: " + str(e)))
        except Exception as e:
            failed.append((fn.__name__, type(e).__name__ + ": " + str(e)))
    return passed, failed

if __name__ == "__main__":
    passed, failed = run()
    for n in passed: print("PASS", n)
    for n, why in failed: print("FAIL", n, "->", why)
    print("\n%d passed, %d failed (of %d pillars)" % (len(passed), len(failed), len(TESTS)))
    sys.exit(1 if failed else 0)
