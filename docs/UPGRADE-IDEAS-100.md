# THE VIEWER — 100 Upgrade Ideas (R13-aligned backlog)

Generated 2026-07-02. Every item below is **new or a deepening** — none duplicate what's already shipped
(search, PUBLOG, look-alike intelligence, troubleshooting, offline Q&A, validation/integrity/sign-off,
serviceability, kit/BOM, pinouts, training, field notes, etc.). Organized into 10 themes of 10. Governed by
**R13 (above military grade)**: accuracy sacred, fail-loud/degrade-safe, verify like lives depend on it,
completeness a duty. Pick any line or any theme and I'll turn it into a verified build wave.

Legend: ★ = high leverage · ⚑ = safety-critical · ⧗ = previously deferred follow-up ·
✅ = shipped (see `docs/CHANGELOG.md`) · 🔧 = in progress.

Items are unmarked until shipped; annotate inline (going forward) rather than maintaining a
separate tracker — no scheduled re-audit of this list is implied. (Medium finding #42: this list
previously had no completion tracking of any kind across its 100 items; `docs/ITERATION-
SNAPSHOTS.md` independently notes ~190 backlog items remain across both idea files. The two items
below already had verifiable shipped evidence in CHANGELOG.md/module docstrings — the rest are not
individually re-audited here.)

---

## A. Structured extraction & data completeness (deepen R11/R12)
1. ★ Full **RPSTL** structured import — figure ↔ item-number ↔ NSN ↔ qty ↔ UOC, per manual. — ✅ Shipped (see `engine/rpstl.py`, `docs/CHANGELOG.md`).
2. **Maintenance Allocation Chart (MAC)** parse — which task is authorized at which level (C/O/F/H/D).
3. **Lubrication Order (LO)** full parse — every lube point, interval, and lubricant type, structured.
4. ⚑ Expendable/durable **supplies lists** (appendix) → structured consumables per manual.
5. **Special-tool** NSNs + a where-used map (which procedures need which special tool).
6. **Warranty / serial-number applicability** — which serials or lots a change or procedure applies to.
7. **Calibration requirements & intervals** for test/measurement equipment.
8. **Preservation / shipping / storage** instruction extraction per item.
9. **Nomenclature cross-index** — official name ↔ colloquial ↔ NATO term, app-wide.
10. ★ **Change-package differ** — when a TM change arrives, extract exactly which values/steps changed.

## B. Search & retrieval intelligence
11. ★ **Fielded/boolean search** operators — `fsc:`, `tm:`, `nsn:`, `vehicle:`, `level:`.
12. **Saved searches + new-match alerts** when a newly ingested doc satisfies a saved query.
13. **Search-within-results** progressive faceting (vehicle → system → component).
14. **Glossary/synonym admin UI** — curate the acronym & alias tables an SME trusts.
15. **Typo-tolerant full-text** (edit-distance FTS) so a misspelling still finds the page.
16. **Sketch-to-figure** search — draw a rough shape, find the closest figure crop.
17. **Wildcard/partial NSN** search with instant FSC/vehicle faceting.
18. **Recency-aware ranking** — prefer the current TM revision over superseded copies (uses tmrev).
19. ★ **Gap detection** — log zero-result searches to reveal what mechanics can't find.
20. **"Cited answer" mode toggle** on the home search (surface ask.py inline).

## C. Diagrams, assembly & visualization (brief-req C + D)
21. ★ **Animated assembly / disassembly sequence player** driven by the callout order.
22. **Layer-peel exploded view** — a depth slider that removes assemblies one layer at a time.
23. **Cutaway / section-view** generator from a figure.
24. **System-colored overlays** on vehicle diagrams (fuel / electrical / hydraulic / air).
25. **Two-variant figure compare** — overlay look-alike parts' figures with a diff highlight.
26. **Auto simplified line-art** "quick reference" from a dense scanned figure (for young mechanics).
27. ⚑ **Animated torque sequence** — play the star pattern + stages step by step.
28. **Deep-zoom everywhere** — extend loupe/pan-zoom to every figure, not just some.
29. **Extend the 3-D turntable** to far more parts (grow CAD-engine coverage) + measurement overlays.
30. **Printable illustrated work-instruction** (steps with the right figure crop beside each step).

## D. Wiring & electrical depth
31. ⧗ ⚑ **Symptom → circuit fault-isolation tree** on the real schematics (Circuit Lab + living schematic).
32. ⚑ **Expected voltage-drop / continuity values** per net for a go/no-go electrical check.
33. **Connector face-view diagrams** + wire-color legend (builds on pinouts.py).
34. **Ground-point map** per vehicle.
35. **Relay / fuse box locator** + function table.
36. **Signal-trace animation** across multi-page schematics.
37. **Harness routing overlay** on the vehicle outline.
38. **Connector mating & keying** diagrams (which plugs into which).
39. **Breaker/fuse rating vs load** cross-check (flag mismatches).
40. **Diagnostic-connector pinout** + fault-code reader guidance.

## E. Fasteners, torque & mechanical
41. ⚑ **Torque-to-yield / angle-torque** detection and flagging (TTY = one-time-use).
42. ⚑ **One-time-use fastener** list ("replace always" — cotter pins, lock nuts, crush washers).
43. **Torque converter with correction notes** (dry vs lubed, altitude, thread condition).
44. **Bolt-grade / head-marking** identification guide.
45. **Thread-repair** (Heli-Coil/insert) procedure linker when threads are damaged.
46. **Torque-wrench range/calibration** guard — warn if a value is outside the wrench's range.
47. **Fastener reuse rules** by joint/material.
48. **Gasket / sealant compatibility** matrix.
49. **Shim / clearance stack-up** calculator.
50. **Press-fit / interference-fit** spec extraction + assembly-force notes.

## F. Fluids, lubrication & consumables
51. ⧗ ★ **Per-vehicle fluids matrix** — type + capacity + interval for oil/coolant/fuel/grease.
52. **Mil-spec → commercial fluid equivalents** cross-reference.
53. **Cold-weather / desert** fluid substitution guidance.
54. **Fluid capacity calculator** (dry fill vs refill, partial service).
55. **Grease-point checklist** with intervals (from the LO).
56. ⚑ **Hazmat / MSDS linkage** for every consumable.
57. **Fluid contamination / analysis limits** (when a sample condemns the fluid).
58. **Auto-add expendables** to the kit/BOM from the procedure.
59. **Filter cross-reference** — element ↔ NSN ↔ change interval.
60. **Coolant mix-ratio** calculator.

## G. Maintenance workflow & fleet readiness
61. ⧗ ★ **Fleet commonality finder** — which parts are shared across vehicles in the corpus.
62. ⧗ **Service-interval "what's due"** tracker by hours / miles / calendar.
63. **Multi-day job resume** — persist active jobs (beyond localStorage) so work survives a restart.
64. ⚑ **NMC / deadline status** tracker per vehicle.
65. **PMCS results logging** + fault trend over time.
66. **Work-order history** per bumper number.
67. **Parts-on-order** tracking tied to a job.
68. **Technician assignment / handoff** with the audit trail.
69. ★ **Fault-recurrence analytics** — which parts fail most, feeding stockage.
70. **Maintenance forecast** from usage data.

## H. PUBLOG / logistics depth
71. ★ **RPSTL ↔ PUBLOG reconciliation** — flag where a manual's NSN disagrees with FLIS.
72. **Lead-time / management data** surfacing from PUBLOG.
73. **AAC-based procurability advice** — order vs fabricate vs cannibalize vs substitute.
74. **I&S family browser** — walk the interchangeable-and-substitute set.
75. ⚑ **DEMIL code + hazmat** handling surfaced on the part page.
76. **FSC/FSG catalog browser** — drill the full federal supply hierarchy.
77. **CAGE vendor dossier** — every NSN a vendor makes, with status.
78. **Freight / packaging** data for shipping a part.
79. **Cancelled-NIIN migration report** — batch supersession across a stockage list.
80. ★ **Local stock cross-reference** — import a unit's on-hand list, mark what's in stock.

## I. Trust, verification & QA (R13)
81. ⧗ ★ **Cross-method agreement** — measures vs spec-tables vs PUBLOG for the same fact; require concurrence. — ✅ Shipped (see `engine/crossmethod.py`, `docs/CHANGELOG.md`).
82. **Confidence heatmap** per manual — where OCR / extraction is weak and needs a human.
83. **Human-verified %** dashboard — how much data carries an SME sign-off.
84. ⚑ **Golden-record locking** — approved values become immutable + versioned.
85. **Re-ingest extraction diff** — when a doc updates, show exactly what changed.
86. **Expanding accuracy ground-truth** — grow test_accuracy's set every time an SME corrects something.
87. **Citation-completeness audit** — flag any surfaced value that lacks a page cite.
88. ★ **Corpus-wide contradiction sweep** — batch conflicts.py across the whole library.
89. **"Explain this answer"** — a provenance trace UI (source page → extractor → value).
90. **Data-lineage graph** — full path from a scanned page to what a mechanic sees.

## J. Security, resilience & field deployment (military + brief-req E)
91. ⚑ **At-rest encryption** option for the index and sidecars.
92. **Signed, tamper-evident manifest** — cryptographically sign the DB checksums.
93. **Role-based access** — operator / mechanic / SME / admin scopes.
94. **Offline audit log** of all views and exports (who saw / printed what).
95. ★ (brief-req E) **Air-gap update package** — signed delta bundles to add manuals to a disconnected machine.
96. ★ (brief-req E) **Bulk drag-a-folder ingestion** pipeline with an auto-OCR queue and progress.
97. ⚑ **Classification / redaction** handling — mark & filter FOUO / restricted content.
98. **Watchdog auto-restart + encrypted off-disk backup rotation** (extend the stability suite).
99. ⚑ **Fail-closed integrity self-check** on startup — refuse to serve a corrupt DB.
100. **Secure wipe / decommission** mode.

---

### How to use this
Tell me a theme (A–J) or a set of line numbers and I'll turn it into a verified build wave — pure module +
self-test + route + UI + R1–R10 docs, held to R13. Highest-leverage starting points if you want a
recommendation: **1, 10, 19, 31, 51, 61, 81, 88, 95, 96**.
