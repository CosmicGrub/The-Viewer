# Dataset congruency audit, correlations, and pillar/mutation tests (v0.28.0)

Run date: 2026-06-02. Everything here is **read-only over the live index** plus one **additive,
deletable sidecar** — the 3.6 GB `index/viewer.db` is never modified (R1), nothing is removed (R6).

## 1. Congruency audit (read-only)

`engine/tools/congruency_probe.py` loaded the small key-sets into memory and cross-checked them.

| Check | Result | Reading |
|---|---|---|
| documents / parts rows / ref_nsn | 39,683 / 227,908 / 41,701 | corpus intact |
| distinct part NSNs | 45,068 | |
| part NSNs **with** FLIS enrichment | 41,282 | 91.6% of part NSNs are enriched |
| part NSNs **without** enrichment | 3,786 | future-fill candidates (not errors) |
| ref_nsn rows **not** used by any part | 419 | cover / superseded / spare references |
| part NSN bad format | **0** | NSN formatting is clean |
| ref NSN bad format | **0** | |
| ref missing item_name / characteristics / part_no | 5,141 / 10,209 / 322 | known FLIS sparsity |
| ref with supersession / vintage date | 9,412 / 40,046 | |

No orphans, no malformed NSNs. The index is internally consistent.

## 2. Correlations connected (new, additive)

These links were **implied** by the flat tables but never surfaced. They now live in a sidecar
`index/correlations.db` (3.6 MB), built by `engine/tools/build_correlations.py`. Delete the file to
roll back; re-run to rebuild. The server reads it **only if present** (`/api/correlations?nsn=`).

- **Cross-platform interchangeability — 19,511 NSNs span more than one vehicle.** The most shared
  part (bolt `5305-01-674-1467`) appears across **33 platforms / 396 documents**. A mechanic who
  finds a part on one vehicle now sees every other platform it fits.
- **NIIN format-drift — 884 review groups** where one NIIN is written as two different NSN strings.
  Some are benign; some flag a likely extraction error worth a look (e.g. NIIN `016741467` carries
  two FSCs, `5303` vs `5305` — surfaced for review, **not** auto-merged).
- **Supersession held both ways — 311 pairs** where an old NSN's *current* replacement is also in our
  index, so a deadlined old number can point straight to the part we actually hold.

## 3. Pillar tests + mutation testing

`engine/tests/` exercises the load-bearing logic against a deterministic fixture index
(`fixture.py`) — no live corpus needed — through `core_pillars.py`, a verbatim mirror of
`viewer_app.py`'s logic so the same code can be both tested and mutated.

**17 / 17 pillar tests pass:** NSN parsing/routing, keyword FTS, fuzzy typo tolerance, AND-precision,
full-NSN + last-4 routing, parts lookup, reference enrichment (incl. R6 version retention),
tech-status (PMCS-cited + history + codes), coverage meter, correlations sidecar, and the 104th-sheet
PDF (valid `%PDF`).

**Mutation testing — 100% kill rate (15 / 15).** `mutation_runner.py` injects realistic faults one at
a time (flip the FSC vehicle test, AND→OR in search, last-4→last-3, disable the NSN path, flip
`confidence IS NOT NULL`, wrong tech-status code, offset the coverage %, hide interchangeability, …)
and confirms the suite catches every one. Two earlier candidates were identified as **equivalent
mutants** (loosening `within1`'s final `<=1` bound, which the `abs(len)` guard + early `diff>1` exit
make unreachable) and were replaced with genuinely-killable mutations.

## Why not pytest (medium finding #43)

`engine/tests/` is deliberately a stdlib-script + subprocess-per-file model
(`engine/tests/verify_all.py` glob-discovers every `test_*.py` and runs each as its own
`subprocess.run([PY, path], ...)`, checking the real process exit code), not pytest. This was a
choice, not neglect:

- **Hard process isolation between test files.** Several tests patch `sys.argv` to dispatch a CLI
  subcommand end-to-end (e.g. `test_prune.py` drives `viewer_ingest.main()` this way) — inside one
  shared pytest process those mutations could leak between test files; a fresh subprocess per file
  can't.
- **Glob-based auto-discovery already solves the actual historical failure mode.** `verify_all.py`'s
  own docstring documents why: a hand-maintained tuple of test filenames once silently omitted
  `test_procedure.py` (and 9 other real suites) from the "authoritative" gate, and its bug shipped
  undetected. `glob.glob("test_*.py")` guarantees every test file added to the directory runs
  automatically — the actual problem pytest's collection would also solve, already solved here.
- **`mutation_runner.py`/`mutation_xl.py` import test modules directly** (`importlib.import_module`
  + reload) and depend on their current plain-script shape to re-run pillar checks after each
  injected fault.

A full migration would touch all ~20 test files (3,000+ lines), reconcile two different execution
models (subprocess-per-file exit-code checks in CI/`verify_all.py` vs. pytest's in-process
collection), and rework the mutation harness's importlib-based reuse — for a style/tooling
preference with no functional bug behind it. Not pursued.

## How to reproduce

```
python engine/tools/congruency_probe.py --db index/viewer.db --json probe.json
python engine/tools/build_correlations.py --db index/viewer.db --out index/correlations.db
engine/run_tests.bat        (or: cd engine/tests && python test_pillars.py && python mutation_runner.py)
```

Rollback the correlations layer: delete `index/correlations.db` (the app falls back silently).
