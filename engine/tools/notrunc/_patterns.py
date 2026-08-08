#!/usr/bin/env python3
"""Truncation-marker pattern data for the no-truncation checker.

Kept in its own module so the patterns can be reviewed, tested, and reasoned
about independently of the checking logic. Each entry pairs a regex with a set
of cheap keyword GATES: the regex is only ever run against a text if every gate
group has at least one member present (case-insensitively). The gates are a
pure performance optimisation and must never change which texts match -- the
test suite asserts gate/regex consistency over random inputs.
"""
import re

# (regex_source, [gate_group, ...]) where a text is a candidate only if every
# gate_group has >=1 member appearing in text.lower(). A group of [""] always
# passes (no gate). Keep gates strictly weaker than the regex they guard.
_UNITS = ["rows", "items", "entries", "lines", "records", "sections", "functions",
          "code", "data", "columns", "fields", "inserts", "statements", "blocks"]

PLACEHOLDER_RULES = [
    (r"\.\.\.\s*(rest|remaining|continue[ds]?|more|etc)\b",
     [[".."], ["rest", "remain", "continu", "more", "etc"]]),
    (r"\b(rest|remainder) of (the )?\w+ (remains?|is|stays?|are) (the same|unchanged|as (before|above|previous))",
     [["rest", "remainder"]]),
    (r"\bremains? (the same|unchanged) (as (before|above)|below)?",
     [["remain"]]),
    (r"\[\s*(remaining|additional|more|other|continued|truncated|omitted|snip|\d+\s+(more|rows|items|lines|entries|records))[^\]]*\]",
     [["["], ["remaining", "additional", "more", "other", "continu", "trunc",
              "omit", "snip", "rows", "items", "lines", "entries", "records"]]),
    (r"\(\s*(remaining|additional|\d+\s+more|truncated|omitted|continued|and so on)[^)]*\)",
     [["("], ["remaining", "additional", "more", "trunc", "omit", "continu", "and so on"]]),
    (r"^\s*(//|#|--|;)\s*\.\.\.\s*$", [[".."]]),
    (r"^\s*\.\.\.\s*$", [[".."]]),
    (r"^\s*[.]{2,}\s*$", [[".."]]),
    (r"^\s*…\s*$", [["…"]]),
    (r"<!--\s*(\.\.\.|omitted|truncated|continued|rest|remaining|snip)",
     [["<!--"], ["..", "omit", "trunc", "continu", "rest", "remain", "snip"]]),
    (r"/\*\s*(\.\.\.|omitted|truncated|continued|rest|remaining|snip)",
     [["/*"], ["..", "omit", "trunc", "continu", "rest", "remain", "snip"]]),
    (r"\b(omitted|truncated|abbreviated|shortened|trimmed|elided|excluded|skipped)\b.{0,30}\b(brevity|space|length|simplicity|readability)\b",
     [["omit", "trunc", "abbrev", "shorten", "trimmed", "elided", "exclude", "skip"],
      ["brevity", "space", "length", "simplicity", "readability"]]),
    (r"\bfor brevity\b", [["brevity"]]),
    (r"\b(and so on|and so forth|et cetera)\b[.!]?\s*$", [["so on", "so forth", "cetera"]]),
    (r"\(continued\)|\bto be continued\b|\bcontinued (below|elsewhere|in part)\b", [["continu"]]),
    (r"\bsimilar (entries|rows|items|sections|code|functions|blocks|records|lines) (follow|continue|below|here)\b",
     [["similar"]]),
    (r"\b(follows?|continues?) (the )?same (pattern|format|structure)\b", [["same"]]),
    (r"\bfollow(s|ing)? (a |the )?similar (pattern|format|structure)\b", [["similar"]]),
    (r"\b(rest|remaining|other) (of the )?(rows|items|entries|lines|records|sections|functions|code|data|columns|fields)\b.{0,40}\b(same|similar|analogous|identical|pattern|above|unchanged|not shown|left out)\b",
     [["rest", "remaining", "other"], _UNITS,
      ["same", "similar", "analogous", "identical", "pattern", "above", "unchanged", "not shown", "left out"]]),
    (r"\b(\d+|many|several|additional|more) (more )?(rows|items|entries|lines|records|inserts|statements|functions)\b.{0,30}\b(omitted|skipped|not shown|left out|here|follow|below)\b",
     [_UNITS, ["omit", "skip", "not shown", "left out", "here", "follow", "below"]]),
    (r"\byou (can|could|would) (add|insert|continue|fill in|generate)\b.{0,40}\b(rest|remaining|more|similar)\b",
     [["you"], ["rest", "remaining", "more", "similar"]]),
    (r"\b(add|insert|place|put) (the )?(rest|remaining|missing|additional) \w+ here\b",
     [["here"], ["rest", "remaining", "missing", "additional"]]),
    (r"\bsnipp?ed\b|\[\s*\.\.\.\s*\]|\(\s*\.\.\.\s*\)", [["snip", ".."]]),
    (r"\bsame as (above|before|previous|the (previous|preceding))\b", [["same as"]]),
    (r"\b(etc\.?|…)\s*$", [["etc", "…"]]),
    (r"\bTODO:?\s*(finish|complete|fill|add (the )?rest|continue)\b", [["todo"]]),
    (r"\b(I('|’)?ll|I will|let me) (stop|pause|continue|truncate)\b",
     [["stop", "pause", "continu", "trunc"]]),
    (r"\b(output|response|content|file) (was |is |has been )?(truncated|cut off|clipped)\b",
     [["trunc", "cut off", "clipped"]]),
]

# Compiled (regex, gates) pairs.
COMPILED_PLACEHOLDERS = [
    (re.compile(src, re.IGNORECASE | re.MULTILINE), gates)
    for src, gates in PLACEHOLDER_RULES
]

# A trailing token that means the line was very likely cut mid-thought.
# ';' and '.' are statement/sentence terminators -- intentionally excluded.
ABRUPT_END_RE = re.compile(
    r"([,:\-+*/=&|]|\b(and|or|the|a|an|to|of|in|with|for|but|by|from|into|onto|"
    r"via|as|at|is|are|was|were|that|which|while|if|then|else))$",
    re.IGNORECASE,
)

# Strip string literals / line comments before counting brackets, so brackets
# inside strings or comments don't create phantom imbalances.
STRING_STRIP_RE = re.compile(
    r"('''.*?'''|\"\"\".*?\"\"\"|'(?:\\.|[^'\\\n])*'|\"(?:\\.|[^\"\\\n])*\")", re.S
)
COMMENT_LINE_RE = re.compile(r"^\s*(#|//|--).*$", re.M)
