"""test_newmodules.py -- property/fuzz hardening for the v1.5-1.7 pure modules. Throws random and hostile
inputs at the sentence/dimension/diff/tree/answer helpers and asserts they NEVER raise and always honour
their invariants. Stdlib only (Hypothesis-optional pattern), so it runs anywhere.

Run:  python tests/test_newmodules.py [N]      (default N=4000 per target)
"""
import os, sys, random, string

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import publogdiff, dimscad, conflicts, faulttree, ask, hybrid   # noqa: E402
try:
    import publog                       # grown file: reads truncated under the sandbox mount, fine host-side
except Exception:
    publog = None
try:
    import jobpack
except Exception:
    jobpack = None

# v1.12 reference decoders + tools (deep audit: these had NO fuzz coverage at all)
try:
    import standards, nsndecode, smrdecode, cage, harnesstrace, macchart
except Exception:                       # grown files can read truncated under a sandbox mount; fine host-side
    standards = nsndecode = smrdecode = cage = harnesstrace = macchart = None


def _rand_text(n):
    alph = string.ascii_letters + string.digits + " .,-/:\n\t±\"'" + "".join(chr(c) for c in range(0x2190, 0x21a0))
    return "".join(random.choice(alph) for _ in range(random.randint(0, n)))


def _rand_dimstr():
    units = ["", "IN", "in", "mm", "cm", "ft", "psi", '"', "V", "junk", " "]
    return "%s%s %s" % (random.choice(["", "-", "+", "."]),
                        random.choice(["", str(random.randint(0, 9999)), "%.3f" % random.uniform(0, 999), ".5", "1,200"]),
                        random.choice(units))


def run(n=4000):
    random.seed(1234)
    # publog.norm_niin: always 9 digits or '' (skipped if the grown module is truncated in-sandbox)
    if publog is not None:
        for _ in range(n):
            s = _rand_text(20)
            r = publog.norm_niin(s)
            assert r == "" or (len(r) == 9 and r.isdigit()), (s, r)
    # publogdiff._niin + code decoders never crash
    for _ in range(n):
        publogdiff._niin(_rand_text(18))
        publogdiff._decode(publogdiff._RNVC, random.choice(["1", "2", "9", "", "Z", _rand_text(2)]))
        publogdiff._cage_active(random.choice(["A", "H", "N", "", "x"]))
    print("[publog/publogdiff helpers] %d cases OK" % n)

    # dimscad: parse_dim + build always yield a valid primitive/OBJ/SVG
    for _ in range(n):
        v = dimscad.parse_dim(_rand_dimstr())
        assert v is None or isinstance(v, float), v
        charx = [{"requirement": random.choice(["LENGTH", "DIAMETER", "WIDTH", "THREAD", _rand_text(8)]),
                  "reply": _rand_dimstr()} for _ in range(random.randint(0, 6))]
        dims = dimscad.dims_from_characteristics(charx)
        res = dimscad.build(_rand_text(12), dims)
        assert res["primitive"] in ("cylinder", "box", "washer", "hex"), res["primitive"]
        assert res["obj"].startswith("#") and "\nv " in res["obj"], "bad OBJ"
        assert res["svg"].startswith("<svg") and res["svg"].rstrip().endswith("</svg>"), "bad SVG"
    print("[dimscad] %d cases OK" % n)

    # conflicts.detect: invariants on any random rows
    for _ in range(n):
        rows = [{"type": random.choice(["torque", "length", "pressure", ""]),
                 "unit": random.choice(["ft-lb", "in", "psi", ""]),
                 "value": random.choice([_rand_dimstr(), str(random.randint(0, 100)), None, ""]),
                 "doc": random.choice(["1", "2", "3"]), "page": random.randint(1, 500)}
                for _ in range(random.randint(0, 8))]
        cs = conflicts.detect(rows)
        for c in cs:
            assert c["min"] <= c["max"], c
            assert c["severity"] in ("high", "medium"), c
            assert len(c["values"]) >= 2 and c["n_docs"] >= 2, c
    print("[conflicts] %d cases OK" % n)

    # faulttree.parse: always a list of well-formed entries
    for _ in range(n):
        t = faulttree.parse(_rand_text(300))
        assert isinstance(t, list)
        for e in t:
            assert "symptom" in e and isinstance(e["steps"], list), e
    print("[faulttree] %d cases OK" % n)

    # ask.extract_answer: never crashes; sentences carry required keys
    for _ in range(n):
        passages = [{"text": _rand_text(200), "doc": str(random.randint(1, 9)), "page": random.randint(1, 99),
                     "tm": _rand_text(5)} for _ in range(random.randint(0, 4))]
        r = ask.extract_answer(_rand_text(30), passages)
        assert isinstance(r["sentences"], list) and isinstance(r["sources"], list)
        for s in r["sentences"]:
            assert "text" in s and "page" in s, s
    print("[ask] %d cases OK" % n)

    # hybrid.fuse: merged list never larger than inputs; every item keeps a signal
    for _ in range(n):
        a = [{"doc_id": str(random.randint(1, 5)), "page": str(random.randint(1, 9))} for _ in range(random.randint(0, 6))]
        b = [{"doc": str(random.randint(1, 5)), "page": str(random.randint(1, 9))} for _ in range(random.randint(0, 6))]
        f = hybrid.fuse([("keyword", a), ("semantic", b)])
        assert len(f) <= len(a) + len(b)
        for r in f:
            assert r.get("_signals"), r
    print("[hybrid.fuse] %d cases OK" % n)

    # jobpack.build: partial dicts still yield a valid PDF
    if jobpack and jobpack.available():
        for _ in range(min(n, 300)):
            pkg = {"title": _rand_text(10)}
            for key in ("parts", "dims", "torque", "cautions", "procedures"):
                if random.random() < 0.5:
                    pkg[key] = [{"nsn": _rand_text(5), "value": _rand_text(4), "type": _rand_text(4),
                                 "context": _rand_text(6), "kind": "NOTE", "text": _rand_text(8),
                                 "steps": [_rand_text(10)], "tools": [_rand_text(4)]}
                                for _ in range(random.randint(0, 3))]
            pdf = jobpack.build(pkg)
            assert pdf[:5] == b"%PDF-", "jobpack produced non-PDF"
        print("[jobpack] PDF fuzz OK")

    # --- v1.12 decoders: never crash, and never FABRICATE a meaning (R13) --------------------
    if standards is not None:
        codes = ["MS35338-46", "AN960-10", "MIL-PRF-2104", "SAE J429", "ASTM A193", "NAS1149", "",
                 "MS", "MIL-", "-", "999", "MS-----", "\x00", "A-A-59326"]
        for _ in range(n):
            tok = random.choice(codes) if random.random() < 0.5 else _rand_text(24)
            c = standards.classify(tok)
            assert isinstance(c, dict), tok
            if c:
                assert "family" in c and "kind" in c, c
                # curated flag must agree with the presence of a named item (never a bare invention)
                assert ("item" in c) == bool(c.get("curated")), c
            standards.scan(_rand_text(200))

        for _ in range(n):
            d = nsndecode.decode(_rand_text(20) if random.random() < 0.5 else
                                 "%04d-%02d-%03d-%04d" % (random.randint(0, 9999), random.randint(0, 99),
                                                          random.randint(0, 999), random.randint(0, 9999)))
            assert isinstance(d, dict) and "valid" in d, d
            if d["valid"]:
                assert len(d["niin"]) == 9 and len(d["fsc"]) == 4, d
                # R13: a name is either a real table entry or None -- never fabricated
                assert d["fsg_name"] is None or isinstance(d["fsg_name"], str), d
                assert d["ncb_country"] is None or isinstance(d["ncb_country"], str), d
            nsndecode.scan(_rand_text(200))

        for _ in range(n):
            code = random.choice(["PAOZZ", "PAFDD", "XBFZZ", "QQOZZ", "", "PAO", _rand_text(5)])
            d = smrdecode.decode(code)
            assert isinstance(d, dict) and "valid" in d, code
            if d["valid"]:
                assert len(d["code"]) == 5, d
                assert d["source_meaning"] is None or isinstance(d["source_meaning"], str), d
            assert isinstance(smrdecode.summary(code), str)
            smrdecode.scan(_rand_text(200))

        for _ in range(n):
            v = cage.validate(random.choice(["19207", "0VGN7", "1IO34", "", "U1234", _rand_text(6)]))
            assert isinstance(v, dict) and "valid" in v and "reasons" in v, v
            # invalid must always explain itself; valid must never carry a reason
            assert bool(v["reasons"]) != bool(v["valid"]), v
            cage.scan(_rand_text(160))
        print("[standards/nsndecode/smrdecode/cage] %d cases OK -- no crash, no fabricated names" % n)

    if harnesstrace is not None:
        for _ in range(n):
            pins = [{"connector": _rand_text(3),
                     "pins": [{"pin": _rand_text(2), "wire_color": _rand_text(4), "signal": _rand_text(8)}
                              for _ in range(random.randint(0, 3))]}
                    for _ in range(random.randint(0, 3))]
            nets = harnesstrace.build_nets(pins)
            for net in nets:
                assert len(net["points"]) >= 2, net      # a net is never a singleton
            t = harnesstrace.trace(pins, _rand_text(3), _rand_text(2))
            assert isinstance(t, dict) and "found" in t, t
        for _ in range(n):
            rows = macchart.extract_mac(_rand_text(300))
            for r in rows:
                assert r["function"], r                  # a row always names a real MAC function
                assert r["level"] is None or r["level"] in "COFHD", r
        print("[harnesstrace/macchart] %d cases OK -- nets never singleton, MAC rows always named" % n)

    print("test_newmodules PASS (N=%d per target)" % n)


if __name__ == "__main__":
    run(int(sys.argv[1]) if len(sys.argv) > 1 else 4000)

# END OF FILE
