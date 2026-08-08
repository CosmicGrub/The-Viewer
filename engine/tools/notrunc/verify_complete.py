#!/usr/bin/env python3
"""Completeness checker -- detect truncation in a generated file.

Catches the four truncation failure modes the no-truncation skill targets:
cut-off generation, placeholder/omission markers, summarization drift, and
structural breakage from dropped content.

Two ways to run it:

  # 1. Let it derive expectations from the original source (best for copies,
  #    transforms, and edits -- nothing to hand-count):
  python verify_complete.py OUTPUT --source SOURCE

  # 2. Supply expectations yourself (best for fresh generation, where there is
  #    no source -- you planned the line count, unit count, and final line):
  python verify_complete.py OUTPUT --expect-lines N \
      --expect-count "PATTERN=N" --expect-tail "EXACT FINAL LINE"

  python verify_complete.py --self-test     # check the checker itself
  python verify_complete.py OUTPUT --json   # machine-readable result

Exit code 0 = clean, 1 = problems found, 2 = usage error.

Importable API:
  check_text(text, suffix, *, expect_lines=None, expect_counts=None,
             expect_tail=None, fast=False) -> list[str]   # [] means clean
  derive_expectations(source_text, suffix) -> dict
"""
import argparse
import csv
import io
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _patterns import (  # noqa: E402
    COMPILED_PLACEHOLDERS, ABRUPT_END_RE, STRING_STRIP_RE, COMMENT_LINE_RE,
)

BRACKET_PAIRS = {"{": "}", "[": "]", "(": ")"}
_CODEISH = {".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".c", ".cpp", ".h",
            ".go", ".rs", ".json", ".sql"}

# Per-suffix "unit" marker: the thing you'd count to prove nothing was dropped.
# Used by derive_expectations so the user never has to invent a pattern.
UNIT_PATTERNS = {
    ".csv": r"(?m)^.+$",            # every non-empty line is a record
    ".json": r'"\w+"\s*:',         # key occurrences (stable across objects)
    ".sql": r"(?im)^\s*INSERT\s+INTO",
    ".py": r"(?m)^\s*def\s",
    ".js": r"(?m)^\s*function\s",
    ".ts": r"(?m)^\s*function\s",
    ".md": r"(?m)^#{1,6}\s",       # headings
    ".xml": r"</\w+>",             # closing tags
    ".html": r"</\w+>",
    ".htm": r"</\w+>",
    ".yaml": r"(?m)^\S+:",
    ".yml": r"(?m)^\S+:",
    ".toml": r"(?m)^\s*\[",         # table headers
}


# ---------------------------------------------------------------- primitives

def count_lines(text):
    return text.count("\n") + (0 if (text.endswith("\n") or not text) else 1)


def final_line(text):
    s = text.rstrip()
    return s.splitlines()[-1].strip() if s else ""


# ---------------------------------------------------------------- checks

def check_placeholders(text, problems):
    low = text.lower()
    seen = set()
    for rx, gates in COMPILED_PLACEHOLDERS:
        if not all(any(k in low for k in g) for g in gates):
            continue
        for m in rx.finditer(text):
            ln = text.count("\n", 0, m.start()) + 1
            if ln in seen:
                continue
            seen.add(ln)
            problems.append("line %d: possible placeholder/omission marker: %r"
                            % (ln, m.group(0).strip()[:80]))
            if len(seen) >= 20:
                problems.append("(more placeholder hits suppressed)")
                return


def check_abrupt_ending(text, problems):
    s = text.rstrip()
    if not s:
        problems.append("file is empty or whitespace-only")
        return
    last = s.splitlines()[-1].rstrip()
    if ABRUPT_END_RE.search(last):
        problems.append("abrupt ending -- last line ends mid-thought: %r" % last[-120:])
    for q in ('"', "'"):
        if last.count(q) % 2 == 1 and not last.endswith((";", ",", ")")):
            problems.append("abrupt ending -- unbalanced %s quote on last line: %r"
                            % (q, last[-80:]))
            break


_INLINE_COMMENT = {
    ".py": r"#[^\n]*", ".rb": r"#[^\n]*", ".sh": r"#[^\n]*",
    ".js": r"//[^\n]*", ".ts": r"//[^\n]*", ".jsx": r"//[^\n]*", ".tsx": r"//[^\n]*",
    ".java": r"//[^\n]*", ".c": r"//[^\n]*", ".cpp": r"//[^\n]*", ".h": r"//[^\n]*",
    ".go": r"//[^\n]*", ".rs": r"//[^\n]*", ".sql": r"--[^\n]*",
}


def check_brackets(text, suffix, problems):
    body = text
    if suffix in _CODEISH:
        # Remove string literals first, then inline AND full-line comments, so
        # brackets living in strings or comments can't fake an imbalance.
        body = STRING_STRIP_RE.sub("", body)
        ic = _INLINE_COMMENT.get(suffix)
        if ic:
            body = re.sub(ic, "", body)
        body = COMMENT_LINE_RE.sub("", body)
    counts = {}
    for ch in body:
        if ch in "{}[]()":
            counts[ch] = counts.get(ch, 0) + 1
    for o, c in BRACKET_PAIRS.items():
        d = counts.get(o, 0) - counts.get(c, 0)
        if d != 0:
            problems.append("bracket imbalance: '%s%s' differ by %+d (possible cut-off)"
                            % (o, c, d))


def _check_xmlish(text, problems):
    try:
        import xml.etree.ElementTree as ET
        ET.fromstring(text)
    except Exception as e:
        problems.append("invalid XML/HTML (likely truncated): %s" % e)


def check_structure(suffix, text, problems):
    if suffix == ".json":
        try:
            json.loads(text)
        except Exception as e:
            problems.append("invalid JSON (likely truncated): %s" % e)
    elif suffix in (".xml", ".svg"):
        _check_xmlish(text, problems)
    elif suffix in (".html", ".htm"):
        # HTML is often not well-formed XML; only flag an obviously open tag set.
        s = text.rstrip().lower()
        if "<html" in s and "</html>" not in s:
            problems.append("HTML <html> opened but never closed (likely truncated)")
        if "<table" in s and s.count("<table") > s.count("</table>"):
            problems.append("HTML has more <table> than </table> (likely truncated)")
    elif suffix == ".csv":
        try:
            rows = [r for r in csv.reader(io.StringIO(text)) if r]
            if rows:
                from collections import Counter
                widths = Counter(len(r) for r in rows)
                modal = widths.most_common(1)[0][0]
                bad = sum(n for w, n in widths.items() if w != modal)
                if bad:
                    problems.append("%d CSV row(s) deviate from modal column count %d "
                                    "-- possible cut-off/merged row" % (bad, modal))
        except Exception as e:
            problems.append("CSV parse problem: %s" % e)
    elif suffix == ".py":
        try:
            compile(text, "<output>", "exec")
        except SyntaxError as e:
            problems.append("Python does not compile (likely truncated): %s" % e)
        except ValueError as e:
            problems.append("Python source invalid (e.g. null byte): %s" % e)
    elif suffix in (".md", ".txt", ".rst"):
        last = final_line(text)
        if last and not (
            last.endswith((".", "!", "?", ":", ";", ")", '"', "'", "`", "|", "---", "***"))
            or last.startswith(("#", "```", "|", "- ", "* ", "> ", "![", "["))
        ):
            problems.append("prose ends without terminal punctuation -- possible "
                            "mid-sentence cut: %r" % last[-80:])
    elif suffix in (".js", ".ts", ".jsx", ".tsx"):
        last = final_line(text)
        if last and not (last.endswith((";", "}", ")", "{"))
                         or last.startswith(("//", "/*", "*"))):
            problems.append("last JS/TS line does not end a statement (';','}') "
                            "-- possible cut-off: %r" % last[-80:])
    elif suffix == ".sql":
        last = final_line(text)
        if last and not last.startswith("--") and not last.endswith(";"):
            problems.append("last SQL statement not terminated with ';': %r" % last[-80:])
    elif suffix in (".yaml", ".yml"):
        last = final_line(text)
        if last.endswith(":") or last.endswith("- "):
            problems.append("YAML ends on a key/list-item with no value -- possible cut-off: %r" % last)


# ---------------------------------------------------------------- public API

def derive_expectations(source_text, suffix):
    """From a complete SOURCE, produce the expectations a faithful OUTPUT must meet."""
    exp = {"expect_lines": count_lines(source_text), "expect_tail": final_line(source_text)}
    pat = UNIT_PATTERNS.get(suffix)
    if pat:
        exp["expect_counts"] = [(pat, len(re.findall(pat, source_text)))]
    return exp


def check_text(text, suffix, *, expect_lines=None, expect_counts=None,
               expect_tail=None, fast=False):
    """Return a list of problem strings. Empty list == no truncation detected."""
    problems = []

    if expect_lines is not None:
        n = count_lines(text)
        if n != expect_lines:
            problems.append("expected %d lines, found %d (%+d)"
                            % (expect_lines, n, n - expect_lines))
            if fast:
                return problems

    if expect_counts:
        for pat, want in expect_counts:
            got = len(re.findall(pat, text, re.MULTILINE))
            if got != want:
                problems.append("pattern %r: expected %d, found %d" % (pat, want, got))
                if fast:
                    return problems

    if expect_tail is not None:
        got = final_line(text)
        if got != expect_tail.strip():
            problems.append("tail sentinel mismatch -- expected final line %r, found %r"
                            % (expect_tail.strip()[:60], got[:60]))
            if fast:
                return problems

    check_abrupt_ending(text, problems)
    if fast and problems:
        return problems
    check_brackets(text, suffix, problems)
    if fast and problems:
        return problems
    check_placeholders(text, problems)
    if fast and problems:
        return problems
    check_structure(suffix, text, problems)
    return problems


def check_file(output_path, source_path=None, expect_lines=None,
               expect_counts=None, expect_tail=None):
    """File-level wrapper: optionally derive expectations from a source file."""
    text = Path(output_path).read_text(encoding="utf-8", errors="replace")
    suffix = Path(output_path).suffix.lower()
    derived = {}
    if source_path:
        src = Path(source_path).read_text(encoding="utf-8", errors="replace")
        derived = derive_expectations(src, suffix)
    el = expect_lines if expect_lines is not None else derived.get("expect_lines")
    ec = expect_counts or derived.get("expect_counts")
    et = expect_tail if expect_tail is not None else derived.get("expect_tail")
    problems = check_text(text, suffix, expect_lines=el, expect_counts=ec, expect_tail=et)
    return problems, count_lines(text), derived


# ---------------------------------------------------------------- self-test

def self_test():
    """Tiny built-in smoke test so the checker can vouch for itself anywhere."""
    cases = [
        ("def f():\n    return 1\n# ... rest of the code remains the same\n", ".py", False),
        ('{"a": [1, 2,', ".json", False),
        ("a,b,c\n1,2,3\n4,5,6\n", ".csv", True),
        ("def f():\n    return 1\n", ".py", True),
        ("Section one is complete.\nSection two follows the same pattern as above.\n", ".md", False),
        ("# Title\n\nAll content present and accounted for.\n", ".md", True),
    ]
    ok = True
    for text, sfx, should_be_clean in cases:
        clean = not check_text(text, sfx)
        status = "PASS" if clean == should_be_clean else "FAIL"
        if status == "FAIL":
            ok = False
        print("  [%s] %s expected_clean=%s" % (status, sfx, should_be_clean))
    print("self-test:", "OK" if ok else "FAILED")
    return 0 if ok else 1


# ---------------------------------------------------------------- CLI

def main(argv=None):
    ap = argparse.ArgumentParser(description="Detect truncation in a generated file.")
    ap.add_argument("output", nargs="?", help="file to verify")
    ap.add_argument("--source", help="original file; expectations are derived from it")
    ap.add_argument("--expect-lines", type=int)
    ap.add_argument("--expect-count", action="append", default=[],
                    help='PATTERN=N (repeatable)')
    ap.add_argument("--expect-tail", help="exact expected final non-empty line")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--self-test", action="store_true", help="test the checker itself")
    args = ap.parse_args(argv)

    if args.self_test:
        return self_test()
    if not args.output:
        ap.error("OUTPUT file is required (or use --self-test)")

    path = Path(args.output)
    if not path.exists():
        print("FAIL: %s does not exist" % path)
        return 2

    expect_counts = []
    for spec in args.expect_count:
        if "=" not in spec:
            ap.error("bad --expect-count spec (need PATTERN=N): %s" % spec)
        pat, _, n = spec.rpartition("=")
        expect_counts.append((pat, int(n)))

    problems, nlines, derived = check_file(
        args.output, args.source, args.expect_lines,
        expect_counts or None, args.expect_tail)

    if args.json:
        print(json.dumps({
            "file": str(path), "lines": nlines, "clean": not problems,
            "problems": problems, "derived_from_source": bool(args.source),
        }, indent=1))
        return 1 if problems else 0

    if args.source and derived:
        print("info: derived from %s -> %d lines, tail=%r%s"
              % (Path(args.source).name, derived["expect_lines"],
                 derived["expect_tail"][:50],
                 (", %d unit markers" % derived["expect_counts"][0][1]) if derived.get("expect_counts") else ""))
    if problems:
        print("FAIL: %d problem(s) in %s:" % (len(problems), path.name))
        for p in problems:
            print("  - %s" % p)
        return 1
    print("OK: %s (%d lines) -- no truncation indicators found" % (path.name, nlines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
