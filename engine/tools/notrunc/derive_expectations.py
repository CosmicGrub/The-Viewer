#!/usr/bin/env python3
"""Print the completeness expectations for a SOURCE file.

The single most error-prone step in the no-truncation workflow is hand-counting
"how many rows / functions / records should the output have". This does it for
you. Point it at the source (or the thing you're about to reproduce) and it
prints the line count, the final line (your tail sentinel), and the count of the
format's natural unit -- ready to eyeball or to paste straight into
verify_complete.py.

Usage:
  python derive_expectations.py SOURCE [--as-flags] [--json]

  --as-flags  emit a ready-to-run verify_complete.py argument string
  --json      emit machine-readable JSON
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, __file__.rsplit("/", 1)[0] if "/" in __file__ else ".")
from verify_complete import derive_expectations  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("source")
    ap.add_argument("--as-flags", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    p = Path(args.source)
    if not p.exists():
        print("error: %s not found" % p)
        return 2
    text = p.read_text(encoding="utf-8", errors="replace")
    exp = derive_expectations(text, p.suffix.lower())

    if args.json:
        print(json.dumps(exp, indent=1))
        return 0
    if args.as_flags:
        parts = ["--expect-lines %d" % exp["expect_lines"]]
        for pat, n in exp.get("expect_counts", []):
            parts.append('--expect-count "%s=%d"' % (pat, n))
        parts.append('--expect-tail %r' % exp["expect_tail"])
        print(" ".join(parts))
        return 0

    print("Source: %s" % p.name)
    print("  expected lines : %d" % exp["expect_lines"])
    print("  final line     : %r" % exp["expect_tail"])
    for pat, n in exp.get("expect_counts", []):
        print("  unit markers   : %d  (pattern %s)" % (n, pat))
    print("\nVerify the output with:")
    flags = ["--expect-lines %d" % exp["expect_lines"]]
    for pat, n in exp.get("expect_counts", []):
        flags.append('--expect-count "%s=%d"' % (pat, n))
    flags.append('--expect-tail "%s"' % exp["expect_tail"])
    print("  python verify_complete.py OUTPUT %s" % " ".join(flags))
    return 0


if __name__ == "__main__":
    sys.exit(main())
