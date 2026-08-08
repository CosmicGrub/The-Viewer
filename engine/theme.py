#!/usr/bin/env python3
"""THE VIEWER -- single source of truth for the dark-theme design tokens (backlog A4, v0.96.0).

The same palette is re-declared today in ~16 ui/*.html :root blocks and ~90 docs/diagrams/_make_*.py
generators. This module is the canonical copy: the UI mirror lives in ui/base.css (generated to match),
and diagram generators import PALETTE / css_root() from here instead of hardcoding hexes.

Stdlib-only, read-only, RPS-safe (works on any Python 3.x). Purely additive -- existing files keep
working untouched; new/updated code points here.
"""

# Canonical dark theme (verified against the live UI + the diagram corpus, 2026-06-10).
PALETTE = {
    "bg":    "#0f1419",   # page background
    "panel": "#171d26",   # card / panel background
    "p2":    "#1c2430",   # nested panel / input background
    "chip":  "#243042",   # chip / tag background
    "line":  "#2b333f",   # borders / separators
    "txt":   "#e6e9ee",   # primary text
    "sub":   "#9aa6b6",   # secondary text
    "mut":   "#6b7280",   # muted / disabled text
    "acc":   "#4f9dff",   # accent (links, primary action)
    "grn":   "#2f7d4f",   # success / additive
    "amb":   "#caa24a",   # warning / amber
    "red":   "#e0564f",   # danger / error
    "teal":  "#1d9e75",   # info / alt accent
    "pur":   "#7f77dd",   # special / experimental
    "mark":  "#5a4a1e",   # search-hit highlight
}

# Diagram-specific derivations (panel fills with borders, used by _make_*.py generators).
DIAGRAM = {
    "node_fill":   PALETTE["panel"],
    "node_stroke": PALETTE["line"],
    "lane_fill":   PALETTE["p2"],
    "arrow":       PALETTE["sub"],
    "title":       PALETTE["txt"],
    "label":       PALETTE["sub"],
    "feat_fill":   "#16301f", "feat_stroke": "#2f5a3e",   # additive / feature
    "fix_fill":    "#3a2f1a", "fix_stroke":  "#6b5526",   # fix
    "rule_fill":   "#1a2740", "rule_stroke": "#3a4d6e",   # rule / governance
}

FONT_STACK = "-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif"
MONO_STACK = "ui-monospace,Consolas,Menlo,monospace"


def css_root(extra=None):
    """The :root{} CSS block for the canonical tokens (what ui/base.css ships)."""
    toks = dict(PALETTE)
    if extra:
        toks.update(extra)
    body = ";".join("--%s:%s" % (k, v) for k, v in toks.items())
    return ":root{%s;}" % body


def svg_style():
    """Common <style> text for hand-built SVG diagrams (text + panel classes)."""
    p = PALETTE
    return ("text{font-family:%s;fill:%s}"
            ".sub{fill:%s}.mut{fill:%s}"
            ".node{fill:%s;stroke:%s}"
            ".lane{fill:%s;stroke:%s}"
            % (FONT_STACK, p["txt"], p["sub"], p["mut"],
               DIAGRAM["node_fill"], DIAGRAM["node_stroke"],
               DIAGRAM["lane_fill"], DIAGRAM["node_stroke"]))


if __name__ == "__main__":
    print(css_root())
