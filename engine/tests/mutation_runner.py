#!/usr/bin/env python3
"""Mutation testing for THE VIEWER's pillars.

Injects small, realistic faults into core_pillars.py (one at a time), re-runs the pillar
test suite against each mutant, and reports which mutants the tests KILL vs let SURVIVE.
A surviving mutant = a behaviour change no test noticed = a coverage gap. High kill rate =
the tests genuinely pin down the load-bearing behaviour.

Each mutation is (id, old_substring, new_substring); old must occur exactly once in the source."""
import os, sys, importlib, shutil, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.dirname(HERE))
SRC = os.path.join(HERE, "core_pillars.py")

MUTATIONS = [
    ("norm_nsn:swap-groups",
     'return f"{m.group(1)}-{m.group(2)}-{m.group(3)}-{m.group(4)}" if m else None',
     'return f"{m.group(1)}-{m.group(3)}-{m.group(2)}-{m.group(4)}" if m else None'),
    ("nsn_kind:flip-class",
     'return "vehicle" if nsn[:4] in FSC_VEHICLE else "part"',
     'return "vehicle" if nsn[:4] not in FSC_VEHICLE else "part"'),
    ("doc_type:break-rpstl",
     'if re.search(r"24P|20P|13&P|RPSTL|\\bPARTS\\b|\\b-P\\b", t): return "Parts (RPSTL)"',
     'if re.search(r"24P|20P|13&P|RPSTL|\\bPARTS\\b|\\b-P\\b", t): return "Other"'),
    ("within1:break-identity",
     'if a == b: return True',
     'if a == b: return False'),
    ("within1:break-accumulator",
     'diff += 1\n            if diff > 1: return False',
     'diff += 0\n            if diff > 1: return False'),
    ("build_match:and->or",
     'expr = " AND ".join(groups)',
     'expr = " OR ".join(groups)'),
    ("search:last4->last3",
     'if mode != "text" and re.fullmatch(r"\\d{4}", q):',
     'if mode != "text" and re.fullmatch(r"\\d{3}", q):'),
    ("search:disable-nsn-path",
     'if nsn and len(re.sub(r"\\D","",q)) >= 11:',
     'if nsn and len(re.sub(r"\\D","",q)) >= 99:'),
    ("part_lookup:flip-confidence",
     '"FROM parts WHERE confidence IS NOT NULL AND nsn=? "',
     '"FROM parts WHERE confidence IS NULL AND nsn=? "'),
    ("reference_for:break-versions",
     'if v and v[0] > 1: out["versions"] = v[0]',
     'if v and v[0] > 99: out["versions"] = v[0]'),
    ("techstatus:wrong-code",
     'if evidence:\n            suggestion = "NMCS"; basis = "pmcs"',
     'if evidence:\n            suggestion = "FMC"; basis = "pmcs"'),
    ("techstatus:break-termlen",
     'if len(t) >= 4 and t not in _TS_STOP and t not in out: out.append(t)',
     'if len(t) >= 40 and t not in _TS_STOP and t not in out: out.append(t)'),
    ("coverage:offset-pct",
     'out[r["vehicle"]] = {"total": tot, "searchable": s, "pct": round(100 * s / tot) if tot else 0}',
     'out[r["vehicle"]] = {"total": tot, "searchable": s, "pct": round(100 * s / tot) + 5 if tot else 0}'),
    ("correlations:hide-interchange",
     'if r and (r["n_vehicles"] or 0) > 1:',
     'if r and (r["n_vehicles"] or 0) > 99:'),
    ("techstatus:codes-order",
     'TECH_CODES = ["FMC", "PMCM", "PMCS", "NMCM", "NMCS"]',
     'TECH_CODES = ["FMC", "PMCS", "PMCM", "NMCM", "NMCS"]'),
]

def run_suite(module_name):
    for m in ("test_pillars", module_name):
        sys.modules.pop(m, None)
    os.environ["PILLAR_MODULE"] = module_name
    tp = importlib.import_module("test_pillars")
    passed, failed = tp.run()
    return len(passed), len(failed)

def main():
    base = open(SRC, encoding="utf-8").read()
    # sanity: the unmutated suite must be all-green first
    open(os.path.join(HERE, "core_pillars_baseline.py"), "w", encoding="utf-8").write(base)
    bp, bf = run_suite("core_pillars_baseline")
    print("baseline: %d passed, %d failed" % (bp, bf))
    if bf:
        print("ABORT: baseline is not green; fix tests before mutation testing."); return 2

    killed = []; survived = []; invalid = []
    for i, (mid, old, new) in enumerate(MUTATIONS):
        if base.count(old) != 1:
            invalid.append((mid, "old occurs %d times (need 1)" % base.count(old))); continue
        mut = base.replace(old, new)
        modname = "_mut_%d" % i
        path = os.path.join(HERE, modname + ".py")
        open(path, "w", encoding="utf-8").write(mut)
        try:
            p, f = run_suite(modname)
            (killed if f > 0 else survived).append((mid, p, f))
            print(("KILLED  " if f > 0 else "SURVIVED") + "  %-28s -> %d pass / %d fail" % (mid, p, f))
        except Exception as e:
            killed.append((mid, 0, -1)); print("KILLED  %-28s -> raised %s" % (mid, type(e).__name__))
        finally:
            try: os.remove(path)
            except OSError: pass
    try: os.remove(os.path.join(HERE, "core_pillars_baseline.py"))
    except OSError: pass

    total = len(killed) + len(survived)
    print("\n=== MUTATION SUMMARY ===")
    print("mutants: %d   killed: %d   survived: %d   score: %.0f%%" %
          (total, len(killed), len(survived), 100 * len(killed) / total if total else 0))
    if invalid:
        print("invalid (skipped):")
        for mid, why in invalid: print("   ", mid, why)
    if survived:
        print("SURVIVORS (coverage gaps to review):")
        for mid, p, f in survived: print("   ", mid)
    return 0

if __name__ == "__main__":
    sys.exit(main())
