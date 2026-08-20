#!/usr/bin/env python3
"""Unit tests for engine/procedure_feature.py parse_procedure() -- the deepened Fix/procedure parser.
Pure (no DB): exercises kind detection, tools, classified warnings, numbered steps, sub-steps, and per-step
torque/FIG/NSN/part-number enrichment. Pure stdlib runner; doubles as the mutation-test driver for this module."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import procedure_feature as PF

TEXT = (
    "ALTERNATOR REMOVAL\n"
    "\n"
    "TOOLS REQUIRED\n"
    "Wrench, Torque wrench; Socket set and Pliers\n"
    "\n"
    "WARNING\n"
    "Disconnect the battery\n"
    "before starting.\n"
    "\n"
    "NOTE\n"
    "Some models differ.\n"
    "\n"
    "1. Remove the negative cable, NSN 5305-01-674-1467.\n"
    "   a. Loosen the clamp.\n"
    "   b. Pull the cable.\n"
    "2. Torque the bolt to 35 ft-lb. See FIG 5.\n"
    "3. Install P/N MS35338-44.\n"
)


def run():
    passed, failed = [], []
    def check(name, cond):
        (passed if cond else failed).append(name)

    pr = PF.parse_procedure(TEXT, title="alternator removal")

    # kind detection
    check("kind_removal", pr["kind"] == "removal")
    check("kind_install", PF.parse_procedure("INSTALL the pump\n1. seat it\n")["kind"] == "installation")
    check("kind_adjust", PF.parse_procedure("ADJUST the valve\n1. turn screw\n")["kind"] == "adjustment")
    check("kind_inspect", PF.parse_procedure("INSPECT the line\n1. look\n")["kind"] == "inspection")
    check("kind_default", PF.parse_procedure("Lubricate the hinge\n1. apply grease\n")["kind"] == "procedure")

    # tools (split on ; , and ; header stops at WARNING)
    tl = pr["tools"]
    check("tools_wrench", "Wrench" in tl)
    check("tools_torque_wrench", "Torque wrench" in tl)
    check("tools_socket", "Socket set" in tl)
    check("tools_pliers", "Pliers" in tl)
    check("tools_no_warning_leak", not any("battery" in t.lower() for t in tl))

    # warnings: classified + multi-line body joined
    levels = [w["level"] for w in pr["warnings"]]
    check("warn_two", len(pr["warnings"]) == 2)
    check("warn_levels", "WARNING" in levels and "NOTE" in levels)
    wtext = " ".join(w["text"] for w in pr["warnings"])
    check("warn_multiline_join", "Disconnect the battery before starting." in wtext)

    # steps + sub-steps
    check("steps_three", len(pr["steps"]) == 3)
    s1, s2, s3 = pr["steps"]
    check("step_numbers", (s1["n"], s2["n"], s3["n"]) == (1, 2, 3))
    check("substeps_two", len(s1["subs"]) == 2)
    check("substep_text", s1["subs"][0] == "Loosen the clamp.")

    # per-step enrichment
    check("nsn_on_step1", "5305-01-674-1467" in s1["nsns"])
    check("torque_on_step2", any("35" in t and "ft" in t.lower() for t in s2["torque"]))
    check("fig_on_step2", "5" in s2["figs"])
    check("pn_on_step3", "MS35338-44" in s3["pns"])

    # negative: a bare sentence is not a step
    check("no_phantom_steps", all(isinstance(s["n"], int) for s in pr["steps"]))

    # =================================================================================================
    # Recommendations annex #11 (cautions-single-page): procedure_full()'s adjacent-page WARNING merge.
    # Real, DB-backed -- a synthetic 2-page fixture: page N-1 ends with a WARNING box, page N has the
    # numbered steps and NO warning text of its own.
    # =================================================================================================
    import sqlite3
    import tempfile
    d = tempfile.mkdtemp(prefix="procedure_merge_")
    dbp = os.path.join(d, "viewer.db")
    con = sqlite3.connect(dbp)
    con.executescript("""
        CREATE TABLE documents(id INTEGER PRIMARY KEY, tm_number TEXT, vehicle TEXT);
        CREATE TABLE pages(id INTEGER PRIMARY KEY, document_id INT, page_number INT, body_text TEXT);
        CREATE VIRTUAL TABLE pages_fts USING fts5(body_text, content='pages', content_rowid='id');
    """)
    con.execute("INSERT INTO documents VALUES(1,'TM 9-2320-280-24','HMMWV')")
    page_prev_text = ("SOME UNRELATED HEADER TEXT ABOVE\n\nWARNING\nHigh voltage present -- disconnect "
                       "power before servicing the alternator.\n")
    page_cur_text = ("ALTERNATOR REMOVAL\n\n1. Disconnect the negative battery cable.\n"
                      "2. Remove the two mounting bolts.\n")
    con.execute("INSERT INTO pages(id,document_id,page_number,body_text) VALUES(1,1,11,?)", (page_prev_text,))
    con.execute("INSERT INTO pages(id,document_id,page_number,body_text) VALUES(2,1,12,?)", (page_cur_text,))
    con.execute("INSERT INTO pages_fts(rowid,body_text) SELECT id,body_text FROM pages")
    con.commit(); con.close()

    class _Core:
        def db(self):
            c = sqlite3.connect(dbp); c.row_factory = sqlite3.Row; return c
    PF.core = _Core()

    pf = PF.procedure_full("alternator removal")
    check("procedure_full_found", pf.get("found") is True)
    check("procedure_full_matched_the_step_page", (pf.get("source") or {}).get("page") == 12)
    warn_pages = {w.get("page") for w in pf.get("warnings", [])}
    check("procedure_full_merged_the_previous_page_warning", 11 in warn_pages)
    check("procedure_full_tags_each_warning_with_its_real_source_page",
          all(isinstance(w.get("page"), int) for w in pf.get("warnings", [])))
    merged_text = " ".join(w["text"] for w in pf.get("warnings", []))
    check("procedure_full_merged_warning_text_is_the_real_box_content",
          "High voltage present" in merged_text or "disconnect" in merged_text.lower())
    check("procedure_full_no_warnings_error_on_a_clean_run", "warnings_error" not in pf)

    # a page with NO usable previous-page text (page_number - 1 doesn't exist) must not error --
    # graceful no-op, steps/tools still returned.
    con2 = sqlite3.connect(dbp)
    con2.execute("UPDATE pages SET page_number=1 WHERE id=1")   # page 11 -> 1, so page 12-1=11 no longer exists
    con2.commit(); con2.close()
    pf2 = PF.procedure_full("alternator removal")
    check("procedure_full_missing_previous_page_degrades_cleanly", pf2.get("found") is True and pf2["steps"])
    check("procedure_full_missing_previous_page_no_error", "warnings_error" not in pf2)

    # a failure fetching the adjacent page must surface warnings_error, WITHOUT losing steps/tools --
    # graceful degradation, not an all-or-nothing failure.
    class _CoreFlaky:
        def __init__(self):
            self.n = 0
        def db(self):
            self.n += 1
            if self.n == 1:
                c = sqlite3.connect(dbp); c.row_factory = sqlite3.Row; return c
            raise RuntimeError("simulated DB failure fetching the adjacent page")
    PF.core = _CoreFlaky()
    pf3 = PF.procedure_full("alternator removal")
    check("procedure_full_adjacent_page_failure_sets_warnings_error",
          pf3.get("found") is True and "warnings_error" in pf3)
    check("procedure_full_adjacent_page_failure_still_returns_steps_and_tools",
          bool(pf3.get("steps")))

    return passed, failed


if __name__ == "__main__":
    p, f = run()
    for n in p: print("PASS", n)
    for n in f: print("FAIL", n)
    print("\n%d passed, %d failed" % (len(p), len(f)))
    sys.exit(1 if f else 0)
