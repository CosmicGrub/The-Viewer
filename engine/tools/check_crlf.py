#!/usr/bin/env python3
"""check_crlf.py -- gate: every *.bat in the repo must have CRLF line endings (v1.13.0).

Why: the Edit/Write tooling used to build this project saves LF-only files, and an LF-only .bat
"blink-crashes" on Windows -- cmd.exe cannot parse :labels/goto without CR, so the window opens and
closes instantly with no error (documented gotcha; all bats were converted once already and the
problem has quietly regressed since). This check makes the regression LOUD instead of silent.

A .bat is flagged if ANY of its lines ends in a bare LF (no preceding CR). Empty files pass.
backups/ is excluded: those are frozen rollback copies (R1) and must never be rewritten.

  python engine\\tools\\check_crlf.py          # exit 0 = all CRLF; exit 1 = lists every LF-only .bat
Fix any listed file by re-saving it with CRLF endings, e.g. from a POSIX shell:
  sed -i 's/\\r$//;s/$/\\r/' "<file>.bat"
Stdlib only; ASCII output (cp1252-safe console)."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))          # engine/tools
ROOT = os.path.dirname(os.path.dirname(HERE))              # project root (THE VIEWER)
SKIP_DIRS = {"backups", ".git", "__pycache__", "node_modules"}


def is_lf_only(path):
    """True if the file contains at least one LF that is not preceded by CR."""
    try:
        with open(path, "rb") as f:
            data = f.read()
    except OSError as e:
        # unreadable = suspicious; fail loud rather than skip quietly (R13)
        print("  [warn] cannot read %s: %s" % (path, e))
        return True
    if not data:
        return False
    return data.replace(b"\r\n", b"").count(b"\n") > 0


def main():
    bad = []
    total = 0
    for dp, dns, fns in os.walk(ROOT):
        dns[:] = [d for d in dns if d.lower() not in SKIP_DIRS]
        for fn in fns:
            if fn.lower().endswith(".bat"):
                total += 1
                p = os.path.join(dp, fn)
                if is_lf_only(p):
                    bad.append(os.path.relpath(p, ROOT))
    if bad:
        print("CRLF GATE: FAIL -- %d of %d .bat file(s) are LF-only (they will blink-crash on Windows):" % (len(bad), total))
        for rel in sorted(bad):
            print("   %s" % rel)
        print("Fix: re-save each with CRLF endings (see this file's docstring for the sed one-liner).")
        return 1
    print("CRLF GATE: PASS -- all %d .bat files have CRLF line endings." % total)
    return 0


if __name__ == "__main__":
    sys.exit(main())

# END OF FILE
