#!/usr/bin/env python3
"""Expanded mutation testing — TWO rounds, many varied mutations, a stranglehold on correctness.

Round 1 mutates the ENGINE LOGIC (core_pillars.py) and runs the 17 pillar tests.
Round 2 mutates the SAFEGUARD (safeguard.py) and runs the truncation/recovery tests — proving the
data-protection layer is itself rigorously pinned down.

A mutant is KILLED if >=1 test fails, SURVIVES if all pass (a coverage gap or an equivalent mutant).
Each mutation is (id, old, new); old must occur exactly once in the source."""
import os, sys, importlib, shutil

HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE = os.path.dirname(HERE)
sys.path.insert(0, HERE); sys.path.insert(0, ENGINE)

# ---- Round 1: engine logic (core_pillars) ----
PILLAR_SRC = os.path.join(ENGINE, "core_pillars.py")
PILLAR_MUTATIONS = [
    ("norm_nsn:swap-23", 'return f"{m.group(1)}-{m.group(2)}-{m.group(3)}-{m.group(4)}" if m else None',
     'return f"{m.group(1)}-{m.group(3)}-{m.group(2)}-{m.group(4)}" if m else None'),
    ("norm_nsn:null->empty", 'return f"{m.group(1)}-{m.group(2)}-{m.group(3)}-{m.group(4)}" if m else None',
     'return f"{m.group(1)}-{m.group(2)}-{m.group(3)}-{m.group(4)}" if m else ""'),
    ("nsn_kind:flip", 'return "vehicle" if nsn[:4] in FSC_VEHICLE else "part"',
     'return "vehicle" if nsn[:4] not in FSC_VEHICLE else "part"'),
    ("nsn_kind:slice", 'return "vehicle" if nsn[:4] in FSC_VEHICLE else "part"',
     'return "vehicle" if nsn[:3] in FSC_VEHICLE else "part"'),
    ("doc_type:rpstl->other", 'if re.search(r"24P|20P|13&P|RPSTL|\\bPARTS\\b|\\b-P\\b", t): return "Parts (RPSTL)"',
     'if re.search(r"24P|20P|13&P|RPSTL|\\bPARTS\\b|\\b-P\\b", t): return "Other"'),
    ("doc_type:operator-swap", 'if re.search(r"-10\\b|OPERATOR", t): return "Operator (-10)"',
     'if re.search(r"-10\\b|OPERATOR", t): return "Maintenance (-20/-24)"'),
    ("within1:break-identity", 'if a == b: return True', 'if a == b: return False'),
    ("within1:break-accum", 'diff += 1\n            if diff > 1: return False',
     'diff += 0\n            if diff > 1: return False'),
    ("within1:early->2", 'if diff > 1: return False', 'if diff > 2: return False'),
    ("build_match:and->or", 'expr = " AND ".join(groups)', 'expr = " OR ".join(groups)'),
    ("build_match:tokcap", 'toks = re.findall(r"[A-Za-z0-9]+", q)[:6]', 'toks = re.findall(r"[A-Za-z0-9]+", q)[:1]'),
    ("alts:drop-prefix", "quoted.append(('\"%s\"*' % a) if (last and i == 0) else ('\"%s\"' % a))",
     "quoted.append(('\"%s\"' % a) if (last and i == 0) else ('\"%s\"' % a))"),
    ("search:last4->3", 'if mode != "text" and re.fullmatch(r"\\d{4}", q):',
     'if mode != "text" and re.fullmatch(r"\\d{3}", q):'),
    ("search:nsn-thresh", 'if nsn and len(re.sub(r"\\D","",q)) >= 11:', 'if nsn and len(re.sub(r"\\D","",q)) >= 99:'),
    ("search:empty-guard", 'if not q: return []', 'if not q: return [1]'),
    ("part_lookup:confidence", '"FROM parts WHERE confidence IS NOT NULL AND nsn=? "',
     '"FROM parts WHERE confidence IS NULL AND nsn=? "'),
    ("part_lookup:found-flip", 'return {"nsn": nsn, "found": bool(refs), "nomenclature": nomen, "refs": refs}',
     'return {"nsn": nsn, "found": not bool(refs), "nomenclature": nomen, "refs": refs}'),
    ("reference:versions>99", 'if v and v[0] > 1: out["versions"] = v[0]', 'if v and v[0] > 99: out["versions"] = v[0]'),
    ("reference:size-prefix", 'WHERE size LIKE ?||\'%\' LIMIT 1', 'WHERE size LIKE \'%\'||? LIMIT 1'),
    ("techstatus:nmcs->fmc", 'suggestion = "NMCS"; basis = "pmcs"', 'suggestion = "FMC"; basis = "pmcs"'),
    ("techstatus:termlen", 'if len(t) >= 4 and t not in _TS_STOP and t not in out: out.append(t)',
     'if len(t) >= 40 and t not in _TS_STOP and t not in out: out.append(t)'),
    ("techstatus:codes-order", 'TECH_CODES = ["FMC", "PMCM", "PMCS", "NMCM", "NMCS"]',
     'TECH_CODES = ["FMC", "PMCS", "PMCM", "NMCM", "NMCS"]'),
    ("coverage:pct+5", '"pct": round(100 * s / tot) if tot else 0', '"pct": round(100 * s / tot) + 5 if tot else 0'),
    ("coverage:searchable-src", "SUM(CASE WHEN p.source IN('text','ocr') THEN 1 ELSE 0 END) searchable ",
     "SUM(CASE WHEN p.source IN('text') THEN 1 ELSE 0 END) searchable "),
    ("correlations:hide", 'if r and (r["n_vehicles"] or 0) > 1:', 'if r and (r["n_vehicles"] or 0) > 99:'),
    ("correlations:niin-slice", 'niin = digits[4:13] if len(digits) >= 13 else digits',
     'niin = digits[4:12] if len(digits) >= 13 else digits'),
]

# ---- Round 2: safeguard (data protection) ----
SG_SRC = os.path.join(ENGINE, "safeguard.py")
SG_MUTATIONS = [
    ("classify:missing-blind", 'if not os.path.exists(cur_path): return "MISSING", "file is gone"',
     'if not os.path.exists(cur_path): return "OK", "file is gone"'),
    ("classify:empty-blind", 'if cs == 0 and e["size"] > 0: return "EMPTY", "0 bytes (was %d)" % e["size"]',
     'if cs == 0 and e["size"] > 0: return "OK", "0 bytes (was %d)" % e["size"]'),
    ("classify:hash-skip", 'if cur_sha == e["sha256"]: return "OK", ""', 'if cur_sha != e["sha256"]: return "OK", ""'),
    ("classify:trunc->ok", 'return "TRUNCATED", "lost %d of %d bytes (clean prefix)" % (e["size"] - cs, e["size"])',
     'return "OK", "lost %d of %d bytes (clean prefix)" % (e["size"] - cs, e["size"])'),
    ("classify:prefix-cmp", 'if head == cur:', 'if head != cur:'),
    ("classify:corrupt->ok", 'return "CORRUPTED", "same size, content changed (byte-flip?)"',
     'return "OK", "same size, content changed (byte-flip?)"'),
    ("classify:size-cmp", 'if cs < e["size"]:', 'if cs > e["size"]:'),
    ("recover:skip-write", 'atomic_copy(src, dst)\n        ok = sha256_file(dst) == e["sha256"]',
     'ok = sha256_file(dst) == e["sha256"] if os.path.exists(dst) else False'),
    ("recover:hash-blind", 'ok = sha256_file(dst) == e["sha256"]', 'ok = True'),
    ("snapshot:skip-verify", 'if sha256_file(dst) != e["sha256"]:\n            raise RuntimeError("snapshot copy mismatch for %s" % e["rel"])',
     'if False:\n            raise RuntimeError("snapshot copy mismatch for %s" % e["rel"])'),
    ("atomic_write:no-encode", 'if isinstance(data, str): data = data.encode("utf-8")',
     'if isinstance(data, bytes): data = data.encode("utf-8")'),
    ("dbcheck:always-ok", 'r = c.execute("PRAGMA quick_check").fetchone()[0]', 'r = "ok"'),
]

def run_pillars(modname):
    for m in ("test_pillars", modname): sys.modules.pop(m, None)
    os.environ["PILLAR_MODULE"] = modname
    return importlib.import_module("test_pillars").run()

def run_trunc(modname):
    for m in ("test_truncation", modname): sys.modules.pop(m, None)
    os.environ["SAFEGUARD_MODULE"] = modname
    return importlib.import_module("test_truncation").run()

def round_(name, src_path, mutations, runner):
    base = open(src_path, encoding="utf-8").read()
    bp, bf = runner(os.path.splitext(os.path.basename(src_path))[0])
    print("\n### %s  (baseline: %d pass / %d fail)" % (name, bp if isinstance(bp,int) else len(bp), bf if isinstance(bf,int) else len(bf)))
    bf_n = bf if isinstance(bf, int) else len(bf)
    if bf_n: print("  ABORT: baseline not green"); return 0, 0, []
    killed = survived = 0; survivors = []; invalid = 0
    for i, (mid, old, new) in enumerate(mutations):
        if base.count(old) != 1:
            print("  INVALID  %-26s (old x%d)" % (mid, base.count(old))); invalid += 1; continue
        modname = "_xl_%s_%d" % (name[:3], i)
        path = os.path.join(os.path.dirname(src_path), modname + ".py")
        open(path, "w", encoding="utf-8").write(base.replace(old, new))
        try:
            p, f = runner(modname)
            fn = f if isinstance(f, int) else len(f)
            if fn > 0: killed += 1
            else: survived += 1; survivors.append(mid)
            print("  %-8s %-26s -> %d fail" % ("KILLED" if fn else "SURVIVED", mid, fn))
        except Exception as ex:
            killed += 1; print("  %-8s %-26s -> raised %s" % ("KILLED", mid, type(ex).__name__))
        finally:
            try: os.remove(path)
            except OSError: pass
    tot = killed + survived
    print("  -> %d mutants, %d killed, %d survived, score %.0f%%%s" %
          (tot, killed, survived, 100*killed/tot if tot else 0, (" (invalid %d)" % invalid) if invalid else ""))
    return killed, survived, survivors

def main():
    print("=== EXPANDED MUTATION TESTING — 2 ROUNDS ===")
    k1, s1, sv1 = round_("ROUND 1 — engine logic (core_pillars)", PILLAR_SRC, PILLAR_MUTATIONS, run_pillars)
    k2, s2, sv2 = round_("ROUND 2 — safeguard (data protection)", SG_SRC, SG_MUTATIONS, run_trunc)
    tot = k1 + s1 + k2 + s2
    print("\n=== GRAND TOTAL ===")
    print("mutants: %d  killed: %d  survived: %d  overall score: %.0f%%" %
          (tot, k1 + k2, s1 + s2, 100 * (k1 + k2) / tot if tot else 0))
    if sv1 or sv2:
        print("survivors:", ", ".join(sv1 + sv2))
    return 0

if __name__ == "__main__":
    sys.exit(main())
