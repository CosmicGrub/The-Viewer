#!/usr/bin/env python3
"""v1.31 (gap-sweep item 3): regression coverage for ref_nsn.superseded actually getting written.

THE BUG: migration 0008 (engine/migrations/0008_supersession_date.sql) added ref_nsn.superseded
("cancellation / interchangeable / current-NSN cross-ref") specifically so index.html's cart-panel
enrichment (`if(rn.superseded) parts.push('...')`) could show it -- but viewer_ingest.py's enrich_flis()
already parses exactly this data from V_FLIS_CANCELLED_NIIN.CSV into a local `subs` variable and has,
since that migration shipped, only ever bound it to the OLDER `substitutes` column (which nothing reads
client-side, confirmed by grep), never to `superseded` -- so the column the UI is actually wired to
display has been permanently NULL in production regardless of what FLIS itself reports.

THE FIX: `superseded` added to both INSERT column lists (ref_nsn and ref_nsn_log) and the ON CONFLICT
UPDATE clause, bound to the exact same `subs` value `substitutes` already receives -- purely additive,
`substitutes`'s own write is untouched.

This test builds a real fixture DB (fixture.py, so a real NSN/NIIN relationship is used, not a made-up
one), writes real synthetic FLIS CSVs including a V_FLIS_CANCELLED_NIIN.CSV row, runs the real
enrich_flis(), and asserts ref_nsn.superseded actually contains the cancellation string -- not just
that ingestion "doesn't crash"."""
import os
import re
import sys
import tempfile
import sqlite3

HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE = os.path.dirname(HERE)
sys.path.insert(0, ENGINE); sys.path.insert(0, HERE)
import fixture                                            # noqa: E402

PASS = 0; FAIL = 0


def ok(name, cond):
    global PASS, FAIL
    print(("PASS " if cond else "FAIL ") + name)
    if cond: PASS += 1
    else: FAIL += 1


def main():
    tmp = tempfile.mkdtemp()
    db, _corr = fixture.build(tmp)

    # Derive the real NIIN the exact same way enrich_flis() itself does (digits[4:13] of a 13-digit
    # NSN) from the fixture's own real part NSN, rather than guessing/hardcoding one.
    con = sqlite3.connect(db)
    nsn = con.execute("SELECT nsn FROM parts WHERE nsn IS NOT NULL AND nsn<>'' LIMIT 1").fetchone()[0]
    digits = re.sub(r"\D", "", nsn)
    ok("fixture_has_a_real_13_digit_nsn_to_derive_a_niin_from", len(digits) >= 13)
    niin = digits[4:13]

    flis_dir = os.path.join(tmp, "flis")
    os.makedirs(flis_dir)

    def write_csv(name, rows):
        with open(os.path.join(flis_dir, name), "w", encoding="utf-8", newline="") as f:
            f.write("HEADER_ROW_SKIPPED\n")
            for r in rows:
                f.write(",".join(r) + "\n")

    write_csv("V_FLIS_IDENTIFICATION.CSV", [(niin, "99999")])           # NIIN, INC
    write_csv("P_H6_PICK.CSV", [("99999", "TEST BOLT")])                # INC, item name
    # NIIN, (unused col), repl_niin, status -- matches enrich_flis()'s real len(r)>=4 / r[0]/r[2]/r[3]
    # read (viewer_ingest.py: "cancel[r[0]] = f'status {r[3]}' + (f', repl NIIN {r[2]}' if r[2] else '')").
    write_csv("V_FLIS_CANCELLED_NIIN.CSV", [(niin, "", "098765432", "CANCELLED")])

    import viewer_ingest as VI
    # enrich_flis() unconditionally refreshes the REAL engine/keywords.json on disk when it enriches
    # >=1 NSN (build_keywords.run(db=dbp) with no `out=` override -- confirmed by reading the call
    # site directly) -- a real, git-tracked repo file, not a scratch artifact. Caught live once during
    # this test's own development (a real, unintended `git status` diff on keywords.json from running
    # this exact test) and fixed by disabling the toggle for the call, matching this module's own
    # documented env-var-gated escape hatch rather than monkeypatching build_keywords directly.
    _orig_kw_scan = VI.KEYWORDS_SCAN
    VI.KEYWORDS_SCAN = False
    try:
        n = VI.enrich_flis(con, flis_dir)
    finally:
        VI.KEYWORDS_SCAN = _orig_kw_scan
    ok("enrich_flis_actually_enriched_the_one_real_nsn", n >= 1)

    row = con.execute("SELECT substitutes, superseded FROM ref_nsn WHERE nsn=?", (nsn,)).fetchone()
    ok("ref_nsn_row_exists_after_enrichment", row is not None)
    if row is not None:
        substitutes, superseded = row
        ok("substitutes_still_gets_the_cancellation_string_unchanged_behavior",
           substitutes and "CANCELLED" in substitutes and "098765432" in substitutes)
        ok("superseded_now_ALSO_gets_the_same_cancellation_string_the_actual_bug_fix",
           superseded and "CANCELLED" in superseded and "098765432" in superseded)
        ok("substitutes_and_superseded_hold_the_identical_real_value",
           substitutes == superseded)

    # ref_nsn_log (the append-only history sidecar) must carry the same fix -- confirms the
    # INSERT INTO ref_nsn_log column-list edit didn't silently drop/misalign a placeholder.
    log_row = con.execute("SELECT substitutes, superseded FROM ref_nsn_log WHERE nsn=? ORDER BY id DESC LIMIT 1", (nsn,)).fetchone()
    ok("ref_nsn_log_row_exists", log_row is not None)
    if log_row is not None:
        ok("ref_nsn_log_superseded_also_populated", log_row[1] and "CANCELLED" in log_row[1])

    # Re-run enrich_flis() a second time (simulates a later ingest re-run) to exercise the ON CONFLICT
    # DO UPDATE SET path, not just the initial INSERT -- confirms the UPDATE clause's new
    # `superseded=COALESCE(NULLIF(excluded.superseded,''),superseded)` term is syntactically correct
    # and doesn't blank out a previously-set value.
    VI.KEYWORDS_SCAN = False
    try:
        n2 = VI.enrich_flis(con, flis_dir)
    finally:
        VI.KEYWORDS_SCAN = _orig_kw_scan
    ok("second_enrich_flis_run_still_succeeds_exercising_the_on_conflict_update_path", n2 >= 1)
    row2 = con.execute("SELECT superseded FROM ref_nsn WHERE nsn=?", (nsn,)).fetchone()
    ok("superseded_survives_the_on_conflict_update_path_intact",
       row2 and row2[0] and "CANCELLED" in row2[0])

    con.close()
    return PASS, FAIL


if __name__ == "__main__":
    p, f = main()
    print("\n%d passed, %d failed" % (p, f))
    sys.exit(1 if f else 0)

# END OF FILE
