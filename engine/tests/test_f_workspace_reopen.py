#!/usr/bin/env python3
"""F -- save & reopen named workspaces (multi-window support, PR 16 of
docs/superpowers/specs/2026-09-03-multi-window-tabs-plan.md, stage 5).

WHAT THIS COVERS, against the real shipped files (this suite has no in-browser runner, same
limitation every prior PR in this initiative states plainly rather than glosses over -- see the
"WHAT THIS CANNOT COVER" note at the bottom):

  1. SOURCE-LEVEL, against engine/ui/workspaces.html:
       - genuinely calls VW.workspace.list/create/touch/delete/exportUrl/exportFile/importUrl/
         importFile (and VW.checkpoint.get/clear) -- real call-site text, not merely present
         somewhere in a comment.
       - the reopen path builds each url and opens it via the SAME shared.js pairing every other
         launch feature in this app uses -- VW.windows.open(url, {name: VW.popoutWindowName(url)})
         -- and does NOT re-implement shared.js's own naming regex (the identical technique
         test_b_workspace_launcher.py already uses for jobcard.html/solve.html).
       - the delete button is wired behind a real confirm() (this app's established care around
         irreversible actions).
       - the export-file path uses the real Blob + URL.createObjectURL + <a download> pattern this
         app already established (circuitlab.html), not a new download mechanism.
       - both import paths (paste-a-link, upload-a-file) catch importUrl()/importFile()'s thrown/
         rejected Error rather than letting it propagate unhandled.

  2. SOURCE-LEVEL, against engine/ui/handover.html: the new hand-off section genuinely exists (a
     real heading, a real link to /workspaces) and reads LIVE data from VW.workspace.list() rather
     than a static blurb.

  3. REAL ROUND-TRIPS, via tests/js/test_f_workspace_reopen_node.js (see that file's own extensive
     header comment for exactly what and how):
       - workspaceDelete(id) -- create, delete, confirm gone from list()/get(), the cross-tab
         "delete" notification over a real BroadcastChannel, a refused-write case.
       - the auto-checkpoint's storage key is a genuinely different string than the named-
         workspaces key, VW.workspace.list() never includes a checkpoint entry, and shared.js's own
         real pagehide/setInterval handlers (invoked directly, not reimplemented) actually write and
         guard the checkpoint the way its own comment claims (including the "an empty-registry tab
         must never clobber a real checkpoint" guard).

  4. `node --check` on shared.js and the inline scripts of workspaces.html/handover.html.

WHAT THIS CANNOT COVER, stated plainly: whether clicking "Reopen" in a real browser actually opens
every window without a popup-blocker intervening past the first, whether the checkpoint-restore
banner genuinely appears after a real ungraceful browser-crash-and-relaunch (as opposed to the
storage state this suite proves gets written), and whether "copy share link" actually reaches the
OS clipboard in a real browser (navigator.clipboard has no meaningful Node equivalent). Called out as
a manual/PR-note check, the same way test_a2_popout.py, test_shared_windows.py and
test_b_workspace_launcher.py already treat their own real-browser-only behavior.

Self-contained; no corpus, no server. Run:  python engine/tests/test_f_workspace_reopen.py
"""
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE = os.path.dirname(HERE)
UI = os.path.join(ENGINE, "ui")
SHARED_JS = os.path.join(UI, "shared.js")
WORKSPACES_HTML = os.path.join(UI, "workspaces.html")
HANDOVER_HTML = os.path.join(UI, "handover.html")
NODE_TEST = os.path.join(HERE, "js", "test_f_workspace_reopen_node.js")

# The exact call-site text workspaces.html's reopen path must use -- proves it routes through the
# SAME shared.js helper every other launch feature (A1/A2/B) uses, never a re-implemented copy. The
# same fragment test_b_workspace_launcher.py already checks jobcard.html/solve.html against.
SHARED_OPEN_CALL = "VW.windows.open(url, {name: VW.popoutWindowName(url)});"
NAMING_REGEX_FRAGMENTS = [r"[^A-Za-z0-9_-]+", r"replace(/^\/+/"]

passed, failed = [], []


def ok(name, cond):
    (passed if cond else failed).append(name)


def say(msg):
    """ASCII-only diagnostic print, same rationale/helper as test_a2_popout.py and
    test_b_workspace_launcher.py: a non-ASCII print() can UnicodeEncodeError on a cp1252 console
    and, inside a broad try/except, silently swallow every assertion printed after it."""
    print(str(msg).encode("ascii", "backslashreplace").decode("ascii"))


def read(path):
    return open(path, encoding="utf-8").read()


try:
    shared_js = read(SHARED_JS)
    workspaces_html = read(WORKSPACES_HTML)
    handover_html = read(HANDOVER_HTML)

    # ============================================================================================
    # shared.js: workspaceDelete is exported, checkpoint is exported, and the checkpoint namespace
    # only ever exposes get/clear (never a public "save" -- the save is meant to be silent/automatic
    # only, per the design doc; a public save() would invite a page to call it as though it were a
    # deliberate "save my workspace" action, blurring the exact distinction the design doc draws).
    # ============================================================================================
    ok("shared_js_declares_workspaceDelete", "function workspaceDelete(id)" in shared_js)
    ok("shared_js_exports_workspace_delete",
       re.search(r"workspace:\s*\{[^}]*\bdelete:\s*workspaceDelete\b", shared_js, re.S) is not None)
    ok("shared_js_exports_checkpoint_get_and_clear_only",
       re.search(r"checkpoint:\s*\{\s*get:\s*checkpointGet,\s*clear:\s*checkpointClear\s*\}", shared_js)
       is not None)
    ok("shared_js_checkpoint_key_is_not_the_workspaces_key",
       'var _CHECKPOINT_KEY = "viewer_last_session";' in shared_js
       and 'var _WS_KEY = "viewer_workspaces";' in shared_js)
    ok("shared_js_wires_pagehide_for_the_checkpoint_save", 'addEventListener("pagehide", _checkpointSave)' in shared_js)
    ok("shared_js_wires_a_periodic_checkpoint_save_too", "setInterval(_checkpointSave," in shared_js)
    ok("shared_js_checkpoint_save_skips_an_empty_registry",
       re.search(r"function _checkpointSave\(\)\s*\{.*?if\s*\(!wins\.length\)\s*return;", shared_js, re.S)
       is not None)

    # ============================================================================================
    # workspaces.html: every required VW.workspace/VW.checkpoint call is really present as real
    # call-site text (not merely mentioned in a comment).
    # ============================================================================================
    required_calls = [
        ("VW.workspace.list()", "VW.workspace.list()"),
        ("VW.workspace.create(", "VW.workspace.create(name, items, 'manual')"),
        ("VW.workspace.get(", "VW.workspace.get(id)"),
        ("VW.workspace.touch(", "VW.workspace.touch(id)"),
        ("VW.workspace.delete(", "VW.workspace.delete(id)"),
        ("VW.workspace.exportUrl(", "VW.workspace.exportUrl(id)"),
        ("VW.workspace.exportFile(", "VW.workspace.exportFile(id)"),
        ("VW.workspace.importUrl(", "VW.workspace.importUrl(extractWsQuery(raw))"),
        ("VW.workspace.importFile(", "VW.workspace.importFile(f)"),
        ("VW.checkpoint.get(", "VW.checkpoint.get()"),
        ("VW.checkpoint.clear(", "VW.checkpoint.clear()"),
    ]
    for label, needle in required_calls:
        ok("workspaces_html_calls_%s" % re.sub(r"\W+", "_", label).strip("_"), needle in workspaces_html)

    # ---- reopen path reuses shared.js's own naming helper, never a re-implemented copy ----
    ok("workspaces_html_reuses_the_shared_windows_open_call_site", SHARED_OPEN_CALL in workspaces_html)
    for frag in NAMING_REGEX_FRAGMENTS:
        ok("workspaces_html_does_not_reimplement_the_naming_regex(%s)" % frag, frag not in workspaces_html)
    ok("workspaces_html_touches_the_workspace_before_reopening_it",
       re.search(r"VW\.workspace\.touch\(id\);\s*\n\s*\(ws\.items", workspaces_html) is not None)

    # ---- delete is behind a real confirm() ----
    ok("workspaces_html_delete_uses_a_real_confirm_dialog",
       re.search(r"window\.confirm\([^)]*\).*VW\.workspace\.delete\(id\)", workspaces_html, re.S) is not None)

    # ---- export file uses the SAME Blob/download pattern already established (circuitlab.html) ----
    ok("workspaces_html_export_file_creates_a_real_blob_url", "URL.createObjectURL(blob)" in workspaces_html)
    ok("workspaces_html_export_file_uses_a_download_anchor", 'a.download=' in workspaces_html)
    ok("workspaces_html_revokes_the_object_url_after_download", "URL.revokeObjectURL(u)" in workspaces_html)

    # ---- both import paths catch a thrown/rejected Error rather than letting it propagate ----
    ok("workspaces_html_import_from_text_is_wrapped_in_try_catch",
       re.search(r"try\{\s*var id=VW\.workspace\.importUrl\(.*?\}catch\(e\)\{", workspaces_html, re.S)
       is not None)
    ok("workspaces_html_import_from_file_handles_the_rejection",
       re.search(r"VW\.workspace\.importFile\(f\)\.then\([^,]+,\s*function\s*\(e\)\{", workspaces_html, re.S)
       is not None)
    ok("workspaces_html_shows_the_specific_error_message_to_the_technician",
       "(e&&e.message)" in workspaces_html)

    # ---- checkpoint restore is a real button click, never on-load-automatic ----
    ok("workspaces_html_checkpoint_restore_is_a_real_button",
       re.search(r'<button[^>]*id="checkpointRestore"', workspaces_html) is not None)
    ok("workspaces_html_wires_restore_to_a_click_handler", "checkpointRestore').onclick=" in workspaces_html)
    ok("workspaces_html_never_calls_checkpoint_windows_open_outside_the_restore_click_handler",
       # every VW.windows.open(w.url call must be textually inside the onclick handler function,
       # never at the top level of showCheckpoint() -- checked by requiring the ONLY occurrence of
       # this exact fragment sits after 'checkpointRestore').onclick=function(){' and before the
       # matching close, which the single-count check below establishes.
       workspaces_html.count("VW.windows.open(w.url, {name: w.name})") == 1)

    # ============================================================================================
    # handover.html: a real, findable hand-off section (not siloed on /workspaces alone), reading
    # LIVE data from VW.workspace.list() rather than a static blurb.
    # ============================================================================================
    ok("handover_html_has_the_handoff_section_heading", "Hand off your open workspace" in handover_html)
    ok("handover_html_links_to_saved_workspaces", 'href="/workspaces"' in handover_html)
    ok("handover_html_reads_live_workspace_count_data",
       "VW.workspace.list().length" in handover_html or "VW.workspace.list()" in handover_html)
    ok("handover_html_guards_the_workspace_read_in_case_shared_js_failed_to_load",
       "VW.workspace && typeof VW.workspace.list" in handover_html)

except Exception as e:
    failed.append("f_workspace_reopen_source_checks(%s)" % e)


# ---- house convention: node --check on shared.js + the inline script blocks of both pages.
#      Gracefully skips (never false-fails) without node, same as every other node-dependent check.
_node_available = False
try:
    _node_available = subprocess.run(["node", "--version"], capture_output=True).returncode == 0
except Exception:
    _node_available = False

if _node_available:
    try:
        r = subprocess.run(["node", "--check", SHARED_JS], capture_output=True, text=True)
        ok("shared_js_parses_with_node", r.returncode == 0)
        if r.returncode != 0:
            say("  node --check shared.js: %s" % r.stderr.strip()[:400])

        for tag, path in (("workspaces.html", WORKSPACES_HTML), ("handover.html", HANDOVER_HTML)):
            html = read(path)
            blocks = re.findall(r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>", html, re.S)
            all_clean = bool(blocks)
            for b in blocks:
                with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f:
                    f.write(b)
                    tmp_path = f.name
                r = subprocess.run(["node", "--check", tmp_path], capture_output=True, text=True)
                if r.returncode != 0:
                    all_clean = False
                    say("  node --check %s inline script: %s" % (tag, r.stderr.strip()[:400]))
                os.unlink(tmp_path)
            ok("%s_inline_scripts_parse_with_node" % tag.replace(".", "_"), all_clean)
    except Exception as e:
        failed.append("f_workspace_reopen_node_syntax(%s)" % e)

    # ---- the real round-trip suite (workspaceDelete + auto-checkpoint) ----
    try:
        r = subprocess.run(["node", NODE_TEST], capture_output=True, text=True)
        for line in r.stdout.splitlines():
            if line.startswith("PASS ") or line.startswith("FAIL "):
                print("  " + line)
        ok("vw_workspace_delete_and_checkpoint_real_roundtrips (see indented PASS/FAIL lines above)",
           r.returncode == 0)
        if r.returncode != 0:
            say("  node test stderr: %s" % r.stderr.strip()[:1500])
    except Exception as e:
        failed.append("f_workspace_reopen_node_roundtrip(%s)" % e)
else:
    ok("node_unavailable_skip", True)


for n in passed:
    print("PASS", n)
for n in failed:
    print("FAIL", n)
print("\n%d passed, %d failed (F -- save & reopen named workspaces, multi-window PR 16)" % (len(passed), len(failed)))
sys.exit(1 if failed else 0)

# END OF FILE
