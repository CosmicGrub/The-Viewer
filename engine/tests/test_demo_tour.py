#!/usr/bin/env python3
"""THE VIEWER -- regression coverage for engine/ui/demo.html (the guided demo/onboarding tour). No prior
test touched this file at all -- it's a real, substantial piece of hand-rolled UI (a full spotlight-tour
engine: scrim/ring/tooltip/arrow-draw, dot progress, autoplay, keyboard nav, operator/mechanic branching)
with nothing verifying its internal consistency. This is a pure static/structural check on the source
text -- no server, no browser -- so it can't catch a runtime layout bug, but it CAN catch the two classes
of drift that are cheap to introduce and easy to miss by eye: a SCRIPT entry pointing at an element id
that doesn't exist (a silently-broken spotlight), and an icon that's drifted out of sync with
palette.js's canonical assignment (this file is deliberately excluded from the app-wide icon-consistency
audit pass, so nothing else catches this for it).
Self-contained; reads the real source files, no server. Run:  python tests/test_demo_tour.py"""
import os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE = os.path.dirname(HERE)
UI = os.path.join(ENGINE, "ui")

passed, failed = [], []
def ok(name, cond):
    (passed if cond else failed).append(name)

try:
    demo_src = open(os.path.join(UI, "demo.html"), encoding="utf-8").read()
    palette_src = open(os.path.join(UI, "palette.js"), encoding="utf-8").read()

    # ---- SCRIPT array: every {scr:'...', sel:'...', side:'...', ...} entry's scr/sel must resolve to a
    # real element id somewhere in the same file (a spotlight step pointing at a typo'd/removed id
    # silently fails at runtime -- place() just returns early with no visible error, per demo.html's own
    # `var el=$(st.sel); if(!el) return;` guard).
    entries = re.findall(r"\{scr:'([^']+)',\s*sel:'([^']+)',\s*side:'([^']+)'", demo_src)
    ok("script_has_entries", len(entries) > 0)
    all_ids = set(re.findall(r'id="([^"]+)"', demo_src))
    missing_scr = [e for e in entries if e[0] not in all_ids]
    missing_sel = [e for e in entries if e[1] not in all_ids]
    ok("every_script_scr_id_exists", not missing_scr)
    ok("every_script_sel_id_exists", not missing_sel)
    if missing_scr: failed.append("missing scr ids: %s" % missing_scr)
    if missing_sel: failed.append("missing sel ids: %s" % missing_sel)

    # ---- every scr: value must actually be a <section class="screen" id="...">, not some other element
    # (a step whose scr points at a non-screen id would call showScreen() with an id that never gets the
    # 'active' class, leaving the tour on the WRONG screen while pointing the ring at a hidden element).
    screen_ids = set(re.findall(r'<section class="screen" id="([^"]+)"', demo_src))
    ok("every_script_scr_is_a_real_screen", all(e[0] in screen_ids for e in entries))

    # ---- step-count regression pins (this session trimmed the mechanic path 20->18 by merging two
    # step-pairs that spotlighted adjacent/overlapping content on the same screen; operator path is
    # untouched at 9). A future edit changing these should be a deliberate choice, not silent drift.
    mech_steps = [e for e in entries if e[2] in ("both", "mech")]
    op_steps = [e for e in entries if e[2] in ("both", "op")]
    ok("mechanic_path_step_count", len(mech_steps) == 18)
    ok("operator_path_step_count", len(op_steps) == 9)

    # ---- icon consistency with palette.js's canonical per-feature assignment (this file is the one
    # deliberately excluded from the app-wide icon-consistency workflow pass -- nothing else checks it).
    def canonical_icon(label_substr):
        m = re.search(r'\{ic:"([^"]+)",label:"[^"]*' + re.escape(label_substr) + r'[^"]*"', palette_src)
        return m.group(1) if m else None

    troubleshoot_ic = canonical_icon("Guided troubleshooting")
    exploded_ic = canonical_icon("Exploded")
    collections_ic = canonical_icon("Smart Collections")
    circuitlab_ic = canonical_icon("Circuit Lab")
    ok("palette_icons_resolved", all([troubleshoot_ic, exploded_ic, collections_ic, circuitlab_ic]))

    tile_block = demo_src.split('id="v-tiles"')[1].split("</section>")[0] if 'id="v-tiles"' in demo_src else ""
    ok("solve_hub_symptom_tile_matches_troubleshoot_icon",
       troubleshoot_ic and ('<div class="ic">%s</div><div class="ti">Symptom' % troubleshoot_ic) in tile_block)
    ok("solve_hub_partbreakdown_tile_matches_exploded_icon",
       exploded_ic and ('<div class="ic">%s</div><div class="ti">Part' % exploded_ic) in tile_block)
    ok("solve_hub_circuitlab_tile_matches_canonical_icon",
       circuitlab_ic and ('<div class="ic">%s</div><div class="ti">Circuit Lab' % circuitlab_ic) in tile_block)
    ok("solve_hub_collections_tile_matches_canonical_icon",
       collections_ic and ('<div class="ic">%s</div><div class="ti">Smart Collections' % collections_ic) in tile_block)

    # ---- shared-infra wiring: rps.js (kiosk-mode sizing + RPS mode/premium body class) IS loaded;
    # palette.js/shared.js are deliberately NOT (their injected bottom-corner pills would collide with
    # this page's own full-width bottom control bar) -- pin both halves of that decision.
    ok("loads_rps_js", '<script src="/rps.js">' in demo_src)
    ok("does_not_load_palette_js", '"/palette.js"' not in demo_src)
    ok("does_not_load_shared_js", '"/shared.js"' not in demo_src)

    # ---- base.css is still linked (tokens + kiosk-mode), matching every other page's convention
    ok("loads_base_css", '<link rel="stylesheet" href="/base.css">' in demo_src)

except Exception as e:
    failed.append("demo_tour_structure(%s)" % e)

for n in passed: print("PASS", n)
for n in failed: print("FAIL", n)
print("\n%d passed, %d failed (of %d checks for demo.html's guided-tour structure)" %
      (len(passed), len(failed), len(passed) + len(failed)))
sys.exit(1 if failed else 0)

# END OF FILE
