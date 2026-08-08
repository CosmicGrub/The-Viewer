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

    return passed, failed


if __name__ == "__main__":
    p, f = run()
    for n in p: print("PASS", n)
    for n in f: print("FAIL", n)
    print("\n%d passed, %d failed" % (len(p), len(f)))
    sys.exit(1 if f else 0)
