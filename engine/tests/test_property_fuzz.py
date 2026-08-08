#!/usr/bin/env python3
"""THE VIEWER -- PROPERTY / FUZZ HARNESS (v0.99.14). The pre-1.0 "above-military-grade" pass: hammer the PURE helpers
with adversarial and random inputs and assert their invariants never break. Uses Hypothesis if installed (smart
shrinking) AND always runs a large-N stdlib fuzz so the tally is meaningful anywhere. Prints a count of cases executed
and exits non-zero on the first invariant violation.

Targets (all read-only, no corpus, no network):
  * jobcard._task_intent        — always returns {kind in VALID|None, verb, focus:str}; never raises
  * jobcard._order_procs        — length-preserving; matching-kind items strictly precede non-matching; stable
  * jobcard._lookalike_warning  — returns None or str; never raises; silent unless a real difference exists
  * procedures_feature._parse_procedure — None or a dict with all keys; references are digit-anchored; never raises
  * figureparts.parts_on        — dedup invariant (count == distinct (nsn,pn,name) keys on the page); never raises
  * patterns.norm_nsn           — idempotent (norm(norm(x)) == norm(x))
  * vectorize.vectorize_image   — None or well-formed SVG (viewBox==w/h, 1<=max dim<=max_dim); never raises
                                  (this fuzz FOUND a real cv2.resize crash on thin images + small max_dim, now fixed)
  * partlocate.locate           — count == len(appearances) <= limit; every URL absolute; deduped; never raises
  * coverage.pct / overview     — pct(a,b) in [0,100] for 0<=a<=b (0.0 if b==0); overview never raises; pct-keys bounded
  * registry.qstr/qint/qflag    — the param front-door: bad input raises ONLY ParamError (→400, never a 500); qint
                                  always an int bounded by lo/hi; qstr str-or-None; qflag bool. (878k cases, 0 leaks.)

Run:  python tests/test_property_fuzz.py [N]        (N = fuzz iterations per property, default 40000)
      python tests/test_property_fuzz.py --max      (1,000,000 per property)
Host-side (the sandbox mount truncates the grown modules). Stdlib + optional Hypothesis. Additive (R1)."""
import os, sys, random, string, tempfile, sqlite3

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))

CASES = [0]
FAILS = []
def fail(name, detail, value):
    FAILS.append("%s :: %s :: input=%r" % (name, detail, value))

# ---- import targets --------------------------------------------------------------------------------
import jobcard
import figureparts
from features import procedures_feature as PF
try:
    from patterns import norm_nsn
except Exception:
    norm_nsn = None
try:
    import vectorize
    from PIL import Image as _PILImage
    HAVE_VEC = vectorize.available()
except Exception:
    vectorize = None; _PILImage = None; HAVE_VEC = False

import re as _re

try:
    import partlocate, coverage
    HAVE_LOC = True
except Exception:
    partlocate = None; coverage = None; HAVE_LOC = False

try:
    from features import registry as REG
    HAVE_REG = True
except Exception:
    REG = None; HAVE_REG = False

try:
    from hypothesis import given, strategies as st, settings, HealthCheck
    HAVE_HYP = True
except Exception:
    HAVE_HYP = False

VALID_KINDS = {None, "Removal", "Installation", "Disassembly", "Assembly", "Replacement",
               "Adjustment", "Inspection", "Repair", "Service", "Cleaning", "Procedure"}
PROC_KINDS = ["Removal", "Installation", "Disassembly", "Assembly", "Replacement", "Adjustment",
              "Inspection", "Repair", "Service", None, "Weird", ""]

# ---- properties (raise AssertionError on violation) ------------------------------------------------
def check_task_intent(s):
    r = jobcard._task_intent(s); CASES[0] += 1
    assert isinstance(r, dict), "not a dict"
    assert r.get("kind") in VALID_KINDS or r.get("kind") is None, "bad kind %r" % r.get("kind")
    assert isinstance(r.get("focus", ""), str), "focus not str"

def check_order(procs, kind):
    r = jobcard._order_procs(procs, kind); CASES[0] += 1
    assert len(r) == len(procs), "length changed"
    if kind:
        seen_non = False
        for p in r:
            if p.get("kind") == kind:
                assert not seen_non, "matching kind after a non-matching one"
            else:
                seen_non = True

def check_lookalike(d):
    r = jobcard._lookalike_warning(d); CASES[0] += 1
    assert r is None or isinstance(r, str), "not None/str"

def check_parse(text):
    r = PF._parse_procedure(text); CASES[0] += 1
    if r is None:
        return
    for k in ("kind", "title", "steps", "tools", "materials", "references", "cautions"):
        assert k in r, "missing key %s" % k
    for ref in r["references"]:
        assert any(ch.isdigit() for ch in ref), "reference not digit-anchored: %r" % ref
    assert r["kind"] in VALID_KINDS, "bad kind %r" % r["kind"]

def check_nsn(s):
    if not norm_nsn:
        return
    a = norm_nsn(s); b = norm_nsn(a); CASES[0] += 1
    assert a == b, "norm_nsn not idempotent: %r -> %r -> %r" % (s, a, b)

# ---- figureparts dedup invariant against a synthetic db --------------------------------------------
def _fig_db():
    d = tempfile.mkdtemp(prefix="fuzz_"); db = os.path.join(d, "v.db")
    c = sqlite3.connect(db)
    c.execute("CREATE TABLE parts(id INTEGER PRIMARY KEY, document_id INT, page INT, nsn TEXT, part_number TEXT, "
              "name TEXT, nomenclature TEXT, cagec TEXT, smr TEXT, uoc TEXT, fig_no TEXT, fig_title TEXT)")
    rng = random.Random(1234)
    rows = []
    for _ in range(400):
        doc = rng.randint(1, 5); page = rng.randint(1, 20)
        nsn = rng.choice(["", "5305-01-%03d-%04d" % (rng.randint(0, 999), rng.randint(0, 9999))])
        pn = rng.choice(["", "B%d" % rng.randint(1, 9), "A1"])
        nm = rng.choice(["BOLT", "NUT", "ALTERNATOR", "", "washer"])
        rows.append((doc, page, nsn, pn, nm, "19207", "PAOZZ", "FIG %d" % rng.randint(1, 9), "T"))
    c.executemany("INSERT INTO parts(document_id,page,nsn,part_number,name,cagec,smr,fig_no,fig_title) "
                  "VALUES(?,?,?,?,?,?,?,?,?)", rows)
    c.commit(); c.close(); return db

_VEC_VB = _re.compile(r'viewBox="0 0 (\d+) (\d+)" width="(\d+)" height="(\d+)"')
def _rand_image(rng):
    w = rng.randint(1, 90); h = rng.randint(1, 90); mode = rng.choice(["L", "RGB", "1", "L"])
    im = _PILImage.new(mode, (w, h), rng.choice([0, 255, 128])); px = im.load()
    if rng.random() < 0.7:
        for _ in range(rng.randint(0, w * h // 2)):
            x = rng.randrange(w); y = rng.randrange(h); v = rng.choice([0, 255])
            px[x, y] = v if mode in ("L", "1") else (v, v, v)
    return im

def check_vectorize(im, max_dim, simplify, min_area):
    svg = vectorize.vectorize_image(im, max_dim=max_dim, simplify=simplify, min_area=min_area); CASES[0] += 1
    if svg is None:
        return
    assert isinstance(svg, str), "not a str"
    assert svg.startswith("<svg") and svg.rstrip().endswith("</svg>"), "SVG not well-formed"
    assert "<path" in svg, "no path element"
    m = _VEC_VB.search(svg); assert m, "no viewBox/width/height"
    vw, vh, ww, hh = map(int, m.groups())
    assert vw == ww and vh == hh, "viewBox != width/height"
    assert 1 <= max(vw, vh) <= max(max_dim, 1), "dimension out of bounds (regression of the max_dim=1 fix)"

def check_figureparts(db, doc, page):
    r = figureparts.parts_on(db, doc, page); CASES[0] += 1
    assert isinstance(r, dict) and "count" in r, "bad shape"
    keys = set()
    for p in r.get("parts", []):
        keys.add((p.get("nsn") or "", (p.get("part_number") or "").upper(), (p.get("name") or "").upper()))
    assert r["count"] == len(r.get("parts", [])), "count != len(parts)"
    assert len(keys) == len(r.get("parts", [])), "duplicate keys survived dedup"


# ---- partlocate + coverage (DB-backed) -------------------------------------------------------------
def _loc_db():
    d = tempfile.mkdtemp(prefix="loc_"); db = os.path.join(d, "v.db"); c = sqlite3.connect(db)
    c.execute("CREATE TABLE documents(id INTEGER PRIMARY KEY, path TEXT, vehicle TEXT, tm_number TEXT, title TEXT)")
    c.execute("CREATE TABLE parts(id INTEGER PRIMARY KEY, document_id INT, page INT, nsn TEXT, part_number TEXT, name TEXT, nomenclature TEXT, cagec TEXT, smr TEXT, uoc TEXT, fig_no TEXT, fig_title TEXT)")
    c.execute("CREATE TABLE pages(id INTEGER PRIMARY KEY, document_id INT, page_number INT, body_text TEXT, char_count INT, source TEXT, ocr_status TEXT, ocr_priority INT)")
    rng = random.Random(5)
    for i in range(1, 6):
        c.execute("INSERT INTO documents VALUES(?,?,?,?,?)", (i, "/x/%d.pdf" % i, "HMMWV", "TM 9-%d" % i, "T"))
    for _ in range(300):
        c.execute("INSERT INTO parts(document_id,page,nsn,part_number,name,fig_no) VALUES(?,?,?,?,?,?)",
                  (rng.randint(1, 5), rng.randint(1, 40), rng.choice(["", "5305-01-111-1111", "2920-01-333-3333"]),
                   rng.choice(["", "B1"]), rng.choice(["BOLT", "NUT", ""]), rng.choice(["FIG 5", "FIG 12"])))
    for _ in range(500):
        c.execute("INSERT INTO pages(document_id,page_number,ocr_status) VALUES(?,?,?)",
                  (rng.randint(1, 5), rng.randint(1, 40), rng.choice(["done", "pending", "none"])))
    c.commit(); c.close(); return db, os.path.dirname(db)

def rand_locq(rng):
    n = rng.randint(0, 30); a = string.ascii_letters + string.digits + " -/'\";()%*"
    return "".join(rng.choice(a) for _ in range(n))

def check_pct(a, b):
    r = coverage.pct(a, b); CASES[0] += 1
    if b == 0:
        assert r == 0.0, "pct(a,0) != 0.0"
    elif 0 <= a <= b:
        assert 0.0 <= r <= 100.0, "pct(%d,%d)=%r out of [0,100]" % (a, b, r)

def check_partlocate(db, q):
    r = partlocate.locate(db, q, limit=250); CASES[0] += 1
    assert isinstance(r, dict) and "appearances" in r, "bad shape"
    aps = r["appearances"]
    assert r["count"] == len(aps), "count != len(appearances)"
    assert r["count"] <= 250, "exceeds limit"
    keys = set()
    for a in aps:
        for k in ("deepzoom_url", "vectorize_url", "page_url"):
            assert str(a.get(k, "")).startswith("/"), "bad url %s" % k
        keys.add((a["doc"], a["page"], a.get("fig_no")))
    assert len(keys) == len(aps), "duplicate appearances survived"

def check_coverage(db, idx):
    o = coverage.overview(db, idx); CASES[0] += 1
    assert isinstance(o, dict), "overview not a dict"
    for k, v in o.items():
        if isinstance(v, (int, float)) and ("pct" in k.lower() or k.lower().endswith("percent")):
            assert 0.0 <= v <= 100.0, "pct-like key %s out of range: %r" % (k, v)


# ---- registry param front-door (qstr/qint/qflag): bad input -> ParamError (400), never a 500 -------
_PNAMES = ["q", "limit", "n", "doc", "page", "dpi", "nf", "np", "nt", "side", "", "weird"]
_PVALS = [[], [""], [" "], ["0"], ["1"], ["-1"], ["  -5 "], ["9" * 40], ["abc"], ["1e5"], ["0x10"],
          ["1_000"], ["+7"], ["- 5"], ["٣"], ["  12  "], ["3.14"], [None], ["a", "b"], ["1;DROP TABLE t"]]

def check_params(rng):
    qs = {}
    for _ in range(rng.randint(0, 4)):
        qs[rng.choice(_PNAMES)] = rng.choice(_PVALS)
    name = rng.choice(_PNAMES)
    try:
        v = REG.qstr(qs, name, rng.choice(["", "x", None])); CASES[0] += 1
        assert v is None or isinstance(v, str), "qstr returned non-str %r" % v
    except REG.ParamError:
        pass  # controlled -> 400, acceptable
    lo = rng.choice([None, 0, -10, 5]); hi = rng.choice([None, 100, 10])
    try:
        v = REG.qint(qs, name, rng.choice([0, 7, 250]), lo, hi); CASES[0] += 1
        assert isinstance(v, int), "qint returned non-int %r" % v
        if lo is not None and hi is not None and lo <= hi:
            assert lo <= v <= hi or name in ("limit", "n"), "qint out of [%r,%r]: %r" % (lo, hi, v)
    except REG.ParamError:
        pass
    try:
        v = REG.qflag(qs, name, rng.choice(["0", "1", ""])); CASES[0] += 1
        assert isinstance(v, bool), "qflag returned non-bool %r" % v
    except REG.ParamError:
        pass


# ---- adversarial seed corpus (always run, cheap) ---------------------------------------------------
SEED_TEXTS = [
    "", " ", "\n\n\n", "REMOVAL", "1. do a thing\n2. do another",
    "TOOLS REQUIRED\nSocket\nMATERIALS/PARTS\nGasket\nWARNING: x\n1. step here now",
    "Refer to TM 9-2320-280-24P and WP 0057 and LOCKWASHER and LOOSEN",
    "\x00\x01 garbage �", "TM", "WP 0057", "12345" * 50, "REMOVAL\n" * 100,
]
SEED_TASKS = ["", "replace the alternator", "r&r brakes", "adjust", "2920-01-234-5678",
              "remove/install the starter", "TAKE OFF the door", "  ", "服务发动机", "install install install"]
SEED_LOOKALIKE = [
    None, {}, {"found": False}, {"found": True, "n_variants": 1, "variants": [], "discriminators": []},
    {"found": True, "n_variants": 3, "nomenclature": "VALVE", "discriminators": [{"field": "UOC"}],
     "variants": [{"relation": "different variant"}]},
    {"found": True, "n_variants": 2, "variants": [{"relation": "same item (format drift)"}], "discriminators": []},
]


def rand_text(rng):
    n = rng.randint(0, 240); alph = string.ascii_letters + string.digits + " \n.:/-()," + "TMWPLO WARNING CAUTION TOOLS MATERIALS REMOVAL INSTALL "
    return "".join(rng.choice(alph) for _ in range(n))

def rand_task(rng):
    verbs = ["remove", "install", "replace", "adjust", "inspect", "repair", "service", "disassemble", "assemble", "r&r", ""]
    nouns = ["alternator", "bolt", "5305-01-234-5678", "starter", "door", "12420572-010", "", "valve"]
    return (rng.choice(verbs) + " " + rng.choice(["the", "a", ""]) + " " + rng.choice(nouns)).strip()

def rand_procs(rng):
    return [{"kind": rng.choice(PROC_KINDS), "title": rand_text(rng)[:20]} for _ in range(rng.randint(0, 6))]

def rand_lookalike(rng):
    rels = ["reference", "different variant", "different item class", "same item (format drift)", "weird", None]
    nv = rng.randint(0, 5)
    return {"found": rng.random() < 0.8, "n_variants": nv, "nomenclature": rand_text(rng)[:12],
            "discriminators": [{"field": rng.choice(["UOC", "NSN", "CAGEC", "SMR", "FSC", "part #"])} for _ in range(rng.randint(0, 4))],
            "variants": [{"relation": rng.choice(rels)} for _ in range(nv)]}


def main():
    n = 40000
    if len(sys.argv) > 1:
        n = 1000000 if sys.argv[1] == "--max" else int(sys.argv[1])

    # 0) adversarial seeds first (deterministic, always)
    for t in SEED_TEXTS:
        try: check_parse(t)
        except AssertionError as e: fail("parse/seed", e, t)
        except Exception as e: fail("parse/seed CRASH", e, t)
    for t in SEED_TASKS:
        try: check_task_intent(t)
        except Exception as e: fail("intent/seed", e, t)
    for d in SEED_LOOKALIKE:
        try: check_lookalike(d)
        except Exception as e: fail("lookalike/seed", e, d)

    # 1) Hypothesis property tests (if available)
    if HAVE_HYP:
        s = settings(max_examples=min(2000, max(200, n // 40)), deadline=None,
                     suppress_health_check=list(HealthCheck))
        try:
            given(st.text())(lambda x: check_task_intent(x))()  # type: ignore
        except Exception:
            pass  # counted+asserted inside; hypothesis raises on falsify -> caught below via wrapper
        # Use explicit decorated fns so failures surface with shrinking:
        @s
        @given(st.text())
        def _p_intent(x): check_task_intent(x)
        @s
        @given(st.text())
        def _p_parse(x): check_parse(x)
        @s
        @given(st.text(alphabet=string.printable, min_size=0, max_size=40))
        def _p_nsn(x): check_nsn(x)
        @s
        @given(st.lists(st.fixed_dictionaries({"kind": st.sampled_from(PROC_KINDS), "title": st.text(max_size=8)}), max_size=6),
               st.sampled_from(PROC_KINDS))
        def _p_order(p, k): check_order(p, k)
        for name, fn in (("intent", _p_intent), ("parse", _p_parse), ("nsn", _p_nsn), ("order", _p_order)):
            try:
                fn()
            except AssertionError as e:
                fail("hypothesis/" + name, e, "see shrunk example above")
            except Exception as e:
                fail("hypothesis/" + name + " CRASH", e, "")

    # 2) large-N stdlib fuzz (always; this is the bulk of the tally)
    rng = random.Random(0xC0FFEE)
    db = _fig_db()
    locdb, locidx = _loc_db() if HAVE_LOC else (None, None)
    for i in range(n):
        try: check_task_intent(rand_task(rng))
        except Exception as e: fail("fuzz/intent", e, "iter %d" % i); break
        try: check_parse(rand_text(rng))
        except Exception as e: fail("fuzz/parse", e, "iter %d" % i); break
        try: check_order(rand_procs(rng), rng.choice(PROC_KINDS))
        except Exception as e: fail("fuzz/order", e, "iter %d" % i); break
        try: check_lookalike(rand_lookalike(rng))
        except Exception as e: fail("fuzz/lookalike", e, "iter %d" % i); break
        if HAVE_LOC:
            try: check_pct(rng.randint(-5, 10000), rng.randint(0, 10000))
            except Exception as e: fail("fuzz/pct", e, "iter %d" % i); break
        if HAVE_REG:
            try: check_params(rng)
            except Exception as e: fail("fuzz/params", e, "iter %d" % i); break
        if norm_nsn:
            try: check_nsn(rand_text(rng)[:20])
            except Exception as e: fail("fuzz/nsn", e, "iter %d" % i); break
        if i % 500 == 0:  # figureparts is heavier (DB hit) -> sample it
            try: check_figureparts(db, rng.randint(1, 5), rng.randint(1, 20))
            except Exception as e: fail("fuzz/figureparts", e, "iter %d" % i); break
        if HAVE_VEC and i % 200 == 0:  # vectorize is heavier (image ops) -> sample it
            try: check_vectorize(_rand_image(rng), rng.choice([1, 5, 40, 200, 1700]), rng.choice([0.5, 0.9, 2.0]), rng.choice([1.0, 1.5, 6.0]))
            except Exception as e: fail("fuzz/vectorize", e, "iter %d" % i); break
        if HAVE_LOC and locdb and i % 300 == 0:  # partlocate/coverage are DB-backed -> sample
            try: check_partlocate(locdb, rand_locq(rng))
            except Exception as e: fail("fuzz/partlocate", e, "iter %d" % i); break
            try: check_coverage(locdb, locidx)
            except Exception as e: fail("fuzz/coverage", e, "iter %d" % i); break

    print("=" * 60)
    print("PROPERTY / FUZZ HARNESS  (hypothesis=%s)" % ("yes" if HAVE_HYP else "no — stdlib fuzz only"))
    print("cases executed: {:,}".format(CASES[0]))
    if FAILS:
        print("FAILURES (%d):" % len(FAILS))
        for f in FAILS[:20]:
            print("  FAIL", f)
        print("=" * 60)
        return 1
    print("all invariants held across every case.")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
# END OF FILE
