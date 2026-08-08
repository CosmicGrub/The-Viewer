#!/usr/bin/env python3
"""THE VIEWER -- generic, dependency-free MUTATION TESTER.

Unlike the hand-written mutation lists (mutation_runner.py / mutation_xl.py), this AUTO-GENERATES mutants
for ANY module by walking its tokens and applying small, realistic faults one at a time:
  - comparators:   ==<->!=   <-> >=   > <-> <=
  - arithmetic:    + <-> -   * <-> /   %
  - aug-assign:    += <-> -=  *= <-> /=
  - booleans:      and <-> or,  True <-> False
  - numbers:       n -> n+1  (0 -> 1)
For each mutant it runs your TEST COMMAND; if a test fails (non-zero exit) the mutant is KILLED, if every
test still passes the mutant SURVIVED (a coverage gap), and a hang is a TIMEOUT (counts as killed).

Safety: the target file is mutated IN PLACE but restored from an in-memory original after every run, and a
final SHA-256 check asserts the source is byte-identical to how it started -- it can never be left broken.
Stdlib only (tokenize/subprocess/hashlib); runs on Python 3.6+ (RPS-safe).

  python mutate.py --target ../patterns.py --test "python tests/test_patterns.py" --cwd .. \
                   [--max 200] [--seed 1] [--timeout 60] [--json out.json]
"""
import os, sys, tokenize, subprocess, hashlib, json, random, time, argparse

OP_SWAPS = {"==": "!=", "!=": "==", "<": ">=", ">": "<=", "<=": ">", ">=": "<",
            "+": "-", "-": "+", "*": "/", "/": "*", "%": "*",
            "+=": "-=", "-=": "+=", "*=": "/=", "/=": "*="}
NAME_SWAPS = {"and": "or", "or": "and", "True": "False", "False": "True"}


def _sha(b):
    return hashlib.sha256(b if isinstance(b, bytes) else b.encode("utf-8")).hexdigest()


def candidates(src):
    """Return [(row, col_start, col_end, old, new, kind)] single-token mutation sites."""
    out = []
    try:
        toks = list(tokenize.generate_tokens(iter(src.splitlines(keepends=True)).__next__))
    except Exception:
        return out
    for t in toks:
        s = t.string
        if t.start[0] != t.end[0]:
            continue                                  # only single-line tokens
        if t.type == tokenize.OP and s in OP_SWAPS:
            out.append((t.start[0], t.start[1], t.end[1], s, OP_SWAPS[s], "op"))
        elif t.type == tokenize.NAME and s in NAME_SWAPS:
            out.append((t.start[0], t.start[1], t.end[1], s, NAME_SWAPS[s], "bool"))
        elif t.type == tokenize.NUMBER and s.isdigit():
            out.append((t.start[0], t.start[1], t.end[1], s, str(int(s) + 1), "num"))
    return out


def apply_one(src, site):
    row, c1, c2, old, new, kind = site
    lines = src.splitlines(keepends=True)
    ln = lines[row - 1]
    lines[row - 1] = ln[:c1] + new + ln[c2:]
    return "".join(lines)


def run_test(cmd, cwd, timeout):
    try:
        p = subprocess.run(cmd, cwd=cwd, shell=True, stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, timeout=timeout)
        return p.returncode
    except subprocess.TimeoutExpired:
        return "timeout"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", required=True)
    ap.add_argument("--test", required=True)
    ap.add_argument("--cwd", default=None)
    ap.add_argument("--max", type=int, default=200)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--timeout", type=int, default=60)
    ap.add_argument("--json", default=None)
    a = ap.parse_args()

    target = os.path.abspath(a.target)
    cwd = os.path.abspath(a.cwd) if a.cwd else os.path.dirname(target)
    with open(target, "r", encoding="utf-8") as f:
        original = f.read()
    orig_sha = _sha(original)

    print("=== MUTATION TEST: %s ===" % os.path.basename(target))
    base_rc = run_test(a.test, cwd, a.timeout)
    if base_rc != 0:
        print("ABORT: baseline test is not green (rc=%s). Fix tests before mutating." % base_rc)
        return 2
    print("baseline: green")

    sites = candidates(original)
    total_sites = len(sites)
    if total_sites > a.max:
        random.seed(a.seed)
        sites = random.sample(sites, a.max)
    print("mutation sites: %d (testing %d)\n" % (total_sites, len(sites)))

    # belt-and-suspenders: keep a .orig sidecar so even a hard kill mid-test is recoverable
    bak = target + ".orig"
    with open(bak, "w", encoding="utf-8") as f:
        f.write(original)

    def _restore():
        with open(target, "w", encoding="utf-8") as f:
            f.write(original)

    killed = survived = timeouts = 0
    survivors = []
    try:
        for i, site in enumerate(sites):
            mutant = apply_one(original, site)
            with open(target, "w", encoding="utf-8") as f:
                f.write(mutant)
            rc = run_test(a.test, cwd, a.timeout)
            _restore()                               # <-- file is a mutant only during the test window
            row, c1, c2, old, new, kind = site
            tag = "%s:%d  %s->%s" % (os.path.basename(target), row, old, new)
            if rc == "timeout":
                timeouts += 1; killed += 1
                print("  KILLED(timeout) %s" % tag)
            elif rc != 0:
                killed += 1
                if killed <= 3 or len(sites) <= 40:
                    print("  KILLED          %s" % tag)
            else:
                survived += 1
                survivors.append({"line": row, "old": old, "new": new, "kind": kind})
                print("  SURVIVED        %s   <-- coverage gap" % tag)
    finally:
        _restore()
        restored_sha = _sha(open(target, "r", encoding="utf-8").read())
        if restored_sha != orig_sha:
            print("\n!!! CRITICAL: source not restored cleanly (sha mismatch). Recover from %s NOW." % bak)
            return 3
        try: os.remove(bak)
        except OSError: pass

    tested = killed + survived
    score = (100.0 * killed / tested) if tested else 0.0
    print("\n=== SUMMARY: %s ===" % os.path.basename(target))
    print("sites=%d tested=%d  killed=%d  survived=%d  timeouts=%d  SCORE=%.0f%%"
          % (total_sites, tested, killed, survived, timeouts, score))
    print("source restored ok (sha verified).")
    if a.json:
        with open(a.json, "w", encoding="utf-8") as f:
            json.dump({"target": os.path.basename(target), "sites": total_sites, "tested": tested,
                       "killed": killed, "survived": survived, "timeouts": timeouts,
                       "score": round(score, 1), "survivors": survivors}, f, indent=2)
        print("wrote", a.json)
    return 0


if __name__ == "__main__":
    sys.exit(main())
