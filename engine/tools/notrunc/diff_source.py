#!/usr/bin/env python3
"""Prove an output is byte-for-byte faithful to a source (verbatim work).

The checker catches missing content and broken structure, but it cannot catch
sub-line corruption that keeps counts and syntax intact -- e.g. one character
dropped inside a comment or a string. When the task is "reproduce this exactly"
(verbatim copy, rename-everywhere, reformat-only), the only complete proof is a
diff against the source. This is that diff, with an optional transform so an
intended change (like a rename) doesn't show up as noise.

Usage:
  python diff_source.py SOURCE OUTPUT
  python diff_source.py SOURCE OUTPUT --rename OLD=NEW   # ignore an intended rename
  python diff_source.py SOURCE OUTPUT --ignore-blank-lines

Exit code 0 = identical (after any transform), 1 = differs, 2 = usage error.
"""
import argparse
import difflib
import re
import sys
from pathlib import Path


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("source")
    ap.add_argument("output")
    ap.add_argument("--rename", action="append", default=[],
                    help="OLD=NEW intended rename to normalise before diffing (repeatable)")
    ap.add_argument("--ignore-blank-lines", action="store_true")
    ap.add_argument("--max-hunks", type=int, default=40)
    args = ap.parse_args(argv)

    for f in (args.source, args.output):
        if not Path(f).exists():
            print("error: %s not found" % f)
            return 2
    src = Path(args.source).read_text(encoding="utf-8", errors="replace")
    out = Path(args.output).read_text(encoding="utf-8", errors="replace")

    # Normalise intended renames by mapping NEW back to OLD in the output, so a
    # correct rename diffs clean and any *other* change still shows.
    for spec in args.rename:
        if "=" not in spec:
            print("bad --rename spec (need OLD=NEW): %s" % spec)
            return 2
        old, _, new = spec.partition("=")
        out = re.sub(r"\b%s\b" % re.escape(new), old, out)

    s_lines, o_lines = src.splitlines(), out.splitlines()
    if args.ignore_blank_lines:
        s_lines = [l for l in s_lines if l.strip()]
        o_lines = [l for l in o_lines if l.strip()]

    diff = list(difflib.unified_diff(s_lines, o_lines,
                                     fromfile="source", tofile="output", lineterm=""))
    if not diff:
        note = " (after normalising rename/blank-lines)" if (args.rename or args.ignore_blank_lines) else ""
        print("IDENTICAL: output matches source%s -- verbatim reproduction confirmed" % note)
        return 0

    adds = sum(1 for d in diff if d.startswith("+") and not d.startswith("+++"))
    dels = sum(1 for d in diff if d.startswith("-") and not d.startswith("---"))
    print("DIFFERS: %d added, %d removed line(s) beyond the intended transform" % (adds, dels))
    shown = 0
    for d in diff:
        print(d)
        if d.startswith("@@"):
            shown += 1
            if shown >= args.max_hunks:
                print("... (further hunks suppressed)")
                break
    return 1


if __name__ == "__main__":
    sys.exit(main())
