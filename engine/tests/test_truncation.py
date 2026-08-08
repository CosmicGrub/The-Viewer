#!/usr/bin/env python3
"""Truncation / corruption protection tests for THE VIEWER's safeguard.

Builds a throwaway project tree, snapshots it into a temp vault, then DELIBERATELY damages each
file at varying severities — light (last line), medium (50%), hard (10 bytes), empty, partial-UTF8,
byte-flip corruption (a mutation), and missing — and asserts that:
  (1) verify() classifies the damage correctly, and
  (2) recover() restores the file byte-for-byte (sha256 == original).
Also corrupts a SQLite DB header and checks integrity detection + recovery. Self-contained: never
touches the real project. Pure stdlib runner."""
import os, sys, tempfile, shutil, sqlite3, importlib, hashlib

HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE = os.path.dirname(HERE)
sys.path.insert(0, ENGINE); sys.path.insert(0, HERE)

# The module under test is configurable (default "safeguard") so the mutation runner can point
# this suite at a mutated copy of the safeguard and confirm the tests KILL the mutant.
def load_sg():
    name = os.environ.get("SAFEGUARD_MODULE", "safeguard")
    if name in sys.modules: del sys.modules[name]
    return importlib.import_module(name)

SG = load_sg()

def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(65536), b""): h.update(c)
    return h.hexdigest()

def make_tree(root):
    os.makedirs(os.path.join(root, "engine", "sub"), exist_ok=True)
    os.makedirs(os.path.join(root, "engine", "ui"), exist_ok=True)
    os.makedirs(os.path.join(root, "index"), exist_ok=True)
    files = {
        "engine/big.py": "\n".join("def f%04d(): return %d  # the quick brown fox %d" % (i, i, i*7) for i in range(1, 801)) + "\n",
        "engine/sub/mod.py": "X = [%s]\n" % ", ".join(str(i) for i in range(300)),
        "engine/ui/index.html": "<html>\n" + ("<div>row %d unicode: café résumé naïve ☃ 日本語</div>\n" % 1) * 50 + "</html>\n",
        "engine/conf.json": "{\n" + ",\n".join('  "k%03d": %d' % (i, i) for i in range(120)) + "\n}\n",
    }
    for rel, txt in files.items():
        p = os.path.join(root, rel)
        with open(p, "w", encoding="utf-8") as f: f.write(txt)
    # a small sqlite db
    db = os.path.join(root, "index", "correlations.db")
    c = sqlite3.connect(db)
    c.execute("CREATE TABLE t(id INTEGER PRIMARY KEY, v TEXT)")
    c.executemany("INSERT INTO t(v) VALUES(?)", [("row %d" % i,) for i in range(500)])
    c.commit(); c.close()
    return list(files.keys()) + ["index/correlations.db"]

def patch_safeguard(root):
    SG.ROOT = root
    SG.VAULT = os.path.join(root, "backups", "vault")
    SG.DB_DEFAULT = os.path.join(root, "index", "correlations.db")
    SG.CRITICAL_GLOBS = ["engine/*.py", "engine/**/*.py", "engine/ui/*.html", "engine/*.json", "index/correlations.db"]

# damage functions operate on the live file in `root`
def dmg_light(p):     # drop last line
    b = open(p, "rb").read(); i = b.rstrip(b"\n").rfind(b"\n")
    open(p, "wb").write(b[:i+1])
def dmg_medium(p):    # truncate to 50%
    b = open(p, "rb").read(); open(p, "wb").write(b[:len(b)//2])
def dmg_hard(p):      # truncate to 10 bytes
    b = open(p, "rb").read(); open(p, "wb").write(b[:10])
def dmg_empty(p):     # zero bytes
    open(p, "wb").write(b"")
def dmg_partial_utf8(p):  # cut 1 byte off the end (likely mid multibyte) -> truncation
    b = open(p, "rb").read(); open(p, "wb").write(b[:len(b)-1])
def dmg_byteflip(p):  # same size, flip bytes in the middle (corruption, not truncation)
    b = bytearray(open(p, "rb").read()); m = len(b)//2
    for k in range(m, m+8): b[k] ^= 0xFF
    open(p, "wb").write(bytes(b))
def dmg_missing(p):   # delete
    os.remove(p)

CASES = [
    ("LIGHT (last line)",   "engine/big.py",        dmg_light,        {"TRUNCATED"}),
    ("MEDIUM (50%)",        "engine/big.py",        dmg_medium,       {"TRUNCATED"}),
    ("HARD (10 bytes)",     "engine/big.py",        dmg_hard,         {"TRUNCATED"}),
    ("EMPTY (0 bytes)",     "engine/conf.json",     dmg_empty,        {"EMPTY"}),
    ("PARTIAL UTF-8",       "engine/ui/index.html", dmg_partial_utf8, {"TRUNCATED"}),
    ("BYTE-FLIP corrupt",   "engine/sub/mod.py",    dmg_byteflip,     {"CORRUPTED"}),
    ("MISSING (deleted)",   "engine/conf.json",     dmg_missing,      {"MISSING"}),
]

def run():
    global SG
    SG = load_sg()
    root = tempfile.mkdtemp(prefix="viewer_safeguard_")
    passed, failed = [], []
    try:
        rels = make_tree(root); patch_safeguard(root)
        originals = {r: sha(os.path.join(root, r)) for r in rels}
        snapid, man = SG.snapshot("test")
        # baseline verify must be all-OK
        sid, res = SG.verify(snapid)
        if any(st != "OK" for _, st, _ in res):
            failed.append(("baseline-clean", "verify not all-OK right after snapshot"));
        else:
            passed.append("baseline-clean")

        for name, rel, fn, expect in CASES:
            p = os.path.join(root, rel)
            fn(p)
            sid, res = SG.verify(snapid)
            got = dict((r, (st, d)) for r, st, d in res)
            st = got.get(rel, ("?", ""))[0]
            detected = st in expect
            # recover and check byte-for-byte
            SG.recover([rel], snapid)
            restored = os.path.exists(p) and sha(p) == originals[rel]
            if detected and restored:
                passed.append("%s -> %s, recovered" % (name, st))
            else:
                failed.append((name, "detected=%s(got %s, want %s) restored=%s" % (detected, st, expect, restored)))

        # multi-damage + recover --all
        dmg_hard(os.path.join(root, "engine/big.py")); dmg_byteflip(os.path.join(root, "engine/sub/mod.py"))
        SG.recover("ALL", snapid)
        all_ok = all(sha(os.path.join(root, r)) == originals[r] for r in rels)
        (passed.append("recover --all restores everything") if all_ok else failed.append(("recover-all", "not all restored")))

        # Vault-corruption guard: if the SNAPSHOT copy itself is damaged, recover must report a
        # hash failure (not a false "RECOVERED"). This pins the post-recovery self-verification.
        snapid3, _ = SG.snapshot("vaultguard")
        vfile = os.path.join(SG.VAULT, snapid3, "files", "engine/big.py")
        with open(vfile, "ab") as f: f.write(b"\x00CORRUPT")     # damage the stored relic
        _, done = SG.recover(["engine/big.py"], snapid3)
        st = dict(done).get("engine/big.py")
        if st == "RECOVER_FAILED_HASH":
            passed.append("vault-corruption caught by post-recovery verify")
        else:
            failed.append(("vault-guard", "recover status was %s, want RECOVER_FAILED_HASH" % st))
        SG.recover(["engine/big.py"], snapid)   # restore from the good snapshot

        # DB integrity: corrupt the SQLite header, detect, recover from a --with-db snapshot
        snapid2, _ = SG.snapshot("withdb", with_db=True)
        db = SG.DB_DEFAULT
        b = bytearray(open(db, "rb").read()); b[0:16] = b"\x00" * 16; open(db, "wb").write(bytes(b))
        bad = SG.db_integrity(db)
        SG.recover(["index/correlations.db"], snapid2)
        good = SG.db_integrity(db)
        if bad != "ok" and good == "ok":
            passed.append("DB corruption detected (%s) + recovered (ok)" % bad)
        else:
            failed.append(("db-integrity", "bad=%s good=%s" % (bad, good)))
    finally:
        shutil.rmtree(root, ignore_errors=True)
    return passed, failed

if __name__ == "__main__":
    p, f = run()
    for n in p: print("PASS", n)
    for n, why in f: print("FAIL", n, "->", why)
    print("\n%d passed, %d failed" % (len(p), len(f)))
    sys.exit(1 if f else 0)
