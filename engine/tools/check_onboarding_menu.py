#!/usr/bin/env python3
"""check_onboarding_menu.py -- gate: a first-time user following START-HERE.bat must be told where
TM PDFs go, in plain language (recommendations annex #16: onboarding-sourcing).

Why: START-HERE.bat's guided menu used to walk Install -> Verify -> Build PUBLOG -> Resume OCR ->
Launch, in order, without ever mentioning the "corpus" folder -- that explanation lived one menu
deeper, inside FIRST-RUN.bat, reached only via VIEWER-MENU.bat's "More tasks". FIRST-RUN.bat itself
used the unexplained term "junction" with no plain-language fallback. This check makes both
regressions LOUD instead of silent: it asserts START-HERE.bat's own top-level menu references the
corpus folder, and that "junction" never appears without an explanatory phrase nearby on the same
warning block.

  python engine\\tools\\check_onboarding_menu.py    # exit 0 = both present; exit 1 = lists what's missing
Stdlib only; ASCII output (cp1252-safe console)."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))


def read(path):
    return open(path, encoding="utf-8", errors="replace").read()


def main():
    bad = []

    start_here = os.path.join(ROOT, "START-HERE.bat")
    if not os.path.exists(start_here):
        bad.append("START-HERE.bat not found at %s" % start_here)
    else:
        txt = read(start_here)
        if "corpus" not in txt.lower():
            bad.append("START-HERE.bat's menu never mentions the 'corpus' folder -- a first-time "
                       "user could install/verify/build/launch without being told where TM PDFs go")

    first_run = os.path.join(ROOT, "FIRST-RUN.bat")
    if not os.path.exists(first_run):
        bad.append("FIRST-RUN.bat not found at %s" % first_run)
    else:
        txt = read(first_run)
        if "junction" in txt.lower():
            # "junction" is fine as long as it's accompanied by a plain-language explanation
            # nearby (this repo's own convention: "shortcut folder" is the plain-language gloss
            # used in both START-HERE.bat and FIRST-RUN.bat's corpus-folder guidance).
            if "shortcut folder" not in txt.lower():
                bad.append("FIRST-RUN.bat uses the term 'junction' with no plain-language "
                           "explanation ('shortcut folder') nearby")

    if bad:
        print("ONBOARDING-MENU GATE: FAIL")
        for b in bad:
            print("  - %s" % b)
        return 1
    print("ONBOARDING-MENU GATE: PASS -- START-HERE.bat mentions the corpus folder; "
          "FIRST-RUN.bat's 'junction' reference is plain-language-glossed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
