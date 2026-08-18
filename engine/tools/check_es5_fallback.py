#!/usr/bin/env python3
"""THE VIEWER -- ES5 fallback gate (UX finding #1, priority 5).

engine/ui/index.html is intentionally MODERN_BY_DESIGN (rps_lint.py exempts the whole file from the
ES5-required gate), so a plain rps_lint.py run does not protect the small ES5-only fallback shell
(#legacyHome + its two <script> blocks) that a true ES5 engine actually depends on -- rps_lint.py would
happily let ES6 syntax creep back into just that fallback without ever failing.

This scans ONLY the fallback span (between the "ES5-only capability probe" marker comment and the
"v0.98.0: Tools menu" marker that starts the file's normal modern script) and flags any of the same
non-polyfillable ES6 syntax patterns rps_lint.py checks for. Exit 1 if any is found, or if the markers
themselves are missing (the fallback was deleted/renamed without updating this gate).

  python check_es5_fallback.py
"""
import os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
INDEX_HTML = os.path.join(os.path.dirname(HERE), "ui", "index.html")

START_MARKER = "ES5-only capability probe"
END_MARKER = "v0.98.0: Tools menu"

# Same non-polyfillable ES6 syntax patterns as engine/tests/rps_lint.py -- kept in sync by hand since
# rps_lint.py's own PATTERNS list scans whole files, not a sub-span, and importing it would couple this
# single-purpose gate to that module's internals for no benefit.
PATTERNS = [
    ("arrow function", re.compile(r"=>")),
    ("const declaration", re.compile(r"(?<![\w.])const\s")),
    ("let declaration", re.compile(r"(?<![\w.])let\s")),
    ("template literal", re.compile(r"`")),
    ("for...of", re.compile(r"\bfor\s*\([^)]*\bof\b")),
    ("spread/rest", re.compile(r"\.\.\.")),
    ("class declaration", re.compile(r"(?<![\w.])class\s+[A-Za-z_$]")),
    ("async function", re.compile(r"(?<![\w.])async\s")),
    ("await", re.compile(r"(?<![\w.])await\s")),
]


def extract_fallback_span(html_text):
    """Return the substring between START_MARKER and END_MARKER, or None if either is missing."""
    si = html_text.find(START_MARKER)
    if si < 0:
        return None
    # Review finding (self-caught while fixing another finding): START_MARKER's text lives INSIDE the
    # probe's own explanatory /* ... */ comment, so a span starting exactly there begins mid-comment --
    # missing the opening "/*" left the rest of that same comment's prose (which legitimately mentions
    # words like "await" while explaining the fix) unrecognized as a comment by _blank_comments(),
    # causing false-positive ES6 hits on prose, not code. Back up to the comment's real opening so the
    # whole thing is included and correctly blanked.
    comment_start = html_text.rfind("/*", 0, si)
    if comment_start >= 0:
        si = comment_start
    ei = html_text.find(END_MARKER, si)
    if ei < 0:
        return None
    return html_text[si:ei]


_QUOTED_STRING = re.compile(r'"(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\'')
_BLOCK_COMMENT = re.compile(r"/\*.*?\*/", re.S)
_LINE_COMMENT = re.compile(r"//[^\n]*")


def _blank_quoted_strings(line):
    """Replace the CONTENTS of "..."/'...' string literals with spaces (same length, quotes kept).
    A feature-detection probe legitimately builds ES6 syntax as a STRING and hands it to Function(...)
    to compile at runtime inside a try/catch -- e.g. Function("(a)=>a") -- and that string's contents
    are opaque to the outer engine's parser (never treated as code by IT), so they must not trip this
    scanner. Backtick template literals are template SYNTAX, not string contents, and are intentionally
    left untouched -- a bare backtick in outer code is still real ES6 syntax regardless of context."""
    return _QUOTED_STRING.sub(lambda m: m.group(0)[0] + (" " * (len(m.group(0)) - 2)) + m.group(0)[0], line)


def _blank_comments(text):
    """Replace /* ... */ and // ... comment CONTENTS with spaces (block comments keep their internal
    newlines, so line numbers in reported hits stay accurate). Review finding: explanatory prose in this
    very file's own comments (the word "await", or "..." as an ellipsis) was tripping the scanner --
    comments are never code, a real JS parser ignores them entirely, and this should too.
    Approximate (regex, not a real tokenizer): a string literal containing a literal "/*" or "//" would
    be misblanked, but that's an acceptable tradeoff for a small, human-authored, self-scanned span."""
    text = _BLOCK_COMMENT.sub(lambda m: re.sub(r"[^\n]", " ", m.group(0)), text)
    text = _LINE_COMMENT.sub(lambda m: " " * len(m.group(0)), text)
    return text


def check_span(span_text):
    """Return a list of (pattern_name, line_no, line_text) for every ES6 hit in span_text."""
    hits = []
    code_text = _blank_comments(span_text)
    orig_lines = span_text.splitlines()
    for i, line in enumerate(code_text.splitlines(), 1):
        code_only = _blank_quoted_strings(line)
        for name, pat in PATTERNS:
            if pat.search(code_only):
                hits.append((name, i, orig_lines[i - 1].strip()[:100]))
    return hits


def main():
    if not os.path.exists(INDEX_HTML):
        print("check_es5_fallback: %s not found" % INDEX_HTML)
        return 1
    text = open(INDEX_HTML, "r", encoding="utf-8").read()
    span = extract_fallback_span(text)
    if span is None:
        print("check_es5_fallback: FAIL -- could not locate the fallback span "
              "(marker %r or %r missing from index.html -- was the ES5 fallback removed or renamed "
              "without updating this gate?)" % (START_MARKER, END_MARKER))
        return 1
    hits = check_span(span)
    if hits:
        print("check_es5_fallback: FAIL -- %d ES6 construct(s) found inside the ES5-only fallback span:"
              % len(hits))
        for name, ln, txt in hits:
            print("  [%s] line ~%d: %s" % (name, ln, txt))
        return 1
    print("check_es5_fallback: OK -- fallback span is ES5-clean (%d lines scanned)" % len(span.splitlines()))
    return 0


if __name__ == "__main__":
    sys.exit(main())

# END OF FILE
