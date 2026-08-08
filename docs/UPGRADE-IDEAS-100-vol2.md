# THE VIEWER — 100 More Upgrade Ideas, Vol. 2 (R13-aligned backlog)

Generated 2026-07-02. A second 100, in 10 **new** themes of 10 — distinct from Vol. 1 (which covered
extraction, search, diagrams, wiring, fasteners, fluids, workflow, PUBLOG, trust/QA, security). Same R13
posture. ★ = high leverage · ⚑ = safety-critical · (E) = serves brief-req E "add any file easily".

---

## K. Operator (−10 level) & crew tasks
1. ★ Guided **operator PMCS walk-around** — before / during / after-operation flow with pass/fail logging.
2. **Crew drills** — start, stop, emergency shutdown checklists.
3. ⚑ Operator fault gating — "what can I fix vs what I must report" per the MAC.
4. **Controls & indicators** reference — dash/panel layout with live callouts.
5. **Break-in / new-equipment** procedures aggregation.
6. **Operating-limits quick card** — max grade, fording depth, top speed, GVWR.
7. **Cold / hot start** procedures.
8. **Basic Issue Items (BII)** checklist with shortage annotation.
9. **Load plan / stowage** diagrams.
10. ★ **Operator→mechanic escalation packet** — auto-build a fault report from an operator finding.

## L. Environmental & extreme conditions
11. **Cold-weather ops** kit + procedure aggregation.
12. **Desert / dust** operating adjustments.
13. ⚑ **Fording / deep-water** prep + mandatory after-operation service.
14. **High-altitude** derating notes.
15. ⚑ **CBRN decontamination** procedure linker.
16. **NBC filter** interval tracking.
17. **Long-term storage / preservation** procedures.
18. **Reactivation-from-storage** checklist.
19. **Extreme-temperature** fluid/lube swaps (ties to the fluids matrix).
20. **Sand / mud / snow** recovery adjuncts.

## M. Recovery, towing & rigging
21. **Towing / recovery** procedures with rated capacities.
22. ⚑ **Lift / sling points** diagram + rated loads.
23. **Self-recovery winch** procedures.
24. **Tie-down / air-transport** rigging (e.g. 5-point).
25. **Rail / sea shipment** prep.
26. **Fording recovery**.
27. **Center-of-gravity / weight** data for lifting.
28. **Recovery-asset matching** — which recovery vehicle for which platform.
29. ⚑ **Jack points + safe-support** procedures.
30. ⚑ **Emergency egress / evacuation**.

## N. Armament & sensitive items (where present in the corpus)
31. Weapon-system maintenance linker.
32. **Boresight / zero** procedures.
33. Ammunition compatibility / storage.
34. **Sensitive-item inventory** tracking.
35. Fire-control / optics maintenance.
36. Turret / traverse maintenance.
37. ⚑ **Safety / clearing** procedures.
38. Serial-number **sensitive-item registry**.
39. ⚑ **Misfire / malfunction immediate action**.
40. ⚑ **Pyrotechnic / EOD hazard** flags.

## O. Battle-Damage Assessment & Repair (BDAR)
41. **BDAR expedient-repair** procedure aggregation.
42. **Field-expedient substitute-material** guidance.
43. ★ **Repair-vs-evacuate** decision aid.
44. **Cannibalization** guidance + controls.
45. ⚑ **Expedient bypass** procedures with explicit risk notes.
46. **Field-fabrication drawings** for common parts.
47. **Limp-home / emergency operating** parameters.
48. **Critical vs non-critical component** map.
49. **Time-to-repair** estimates for triage.
50. **BDAR kit** contents + where-used.

## P. Interoperability & standards
51. **STANAG cross-reference** index.
52. **NATO ↔ national stock number** mapping.
53. **Coalition-partner equipment** cross-walk.
54. **Unit-of-issue / unit-of-measure** normalization.
55. **Metric ⇄ imperial dual** everywhere (extend units.py).
56. **Multi-service manual** mapping (Army / USMC / etc.).
57. **COTS commercial-equivalent** cross-reference.
58. **Standard-hardware decoder** (MS / AN / NAS part codes).
59. **MIL-SPEC / MIL-STD resolver** + active/inactive status.
60. **Obsolete-standard supersession** — which spec replaced which.

## Q. OCR & data-quality deepening
61. ★ **Noisy-scan table reconstruction** (deepen tables/tables_plus).
62. **Handwriting / stamp** detection (change markings, unit annotations).
63. **Skew / rotation** auto-correction at corpus scale.
64. **Multi-column reflow** correctness scoring.
65. **Figure/text region segmentation** improvement.
66. **Targeted OCR re-run** on low-confidence pages only.
67. **Dictionary-assisted OCR** correction with a military vocabulary.
68. **Symbol recovery** — ±, °, Ø, fractions, superscripts.
69. **Redaction / blackout** detection.
70. **Duplicate page / edition** detection (deepen dedup.py).

## R. Reporting, forms & compliance
71. ⚑ **DA 2404 / 5988-E** (PMCS results) prefill from logged checks.
72. **DA 2407 / 5990-E** maintenance-request prefill.
73. **DD 1348** parts-request generation.
74. **Deadline (NMC) report** generation.
75. **Historical maintenance record** export per vehicle.
76. **MWO-applied tracking** (which modification work orders are done).
77. **Warranty-claim packet** builder.
78. **Calibration-due** report.
79. **Shortage-annotation (BII/COEI)** report.
80. ★ **Audit-ready export bundle** — every value with its full provenance.

## S. Collaboration & multi-user
81. **Moderated multi-user field notes** (extend fieldnotes.py).
82. **Shared saved-searches / collections** across a shop.
83. ★ **Shift-handover digest** — what's open, what's due, what changed.
84. **SME async question queue** ("office hours").
85. **Comment threads** on a procedure / figure.
86. **Trusted-contributor** signals (endorsement history).
87. **Change-proposal workflow** — suggest a correction → SME sign-off (ties to signoff.py).
88. ⚑ **Safety-bulletin acknowledgment tracking** (read receipts).
89. **Per-crew readiness dashboards**.
90. **Notification center** — new docs, superseded TMs, safety flags.

## T. Platform, packaging & deployment (brief-req E)
91. (E) **Field-laptop single-exe** build (extend the installer).
92. **Ruggedized-tablet layout** profile.
93. **Bay / shelf map** asset locator (GPS-free).
94. **Bin-label barcode printing** (generate + print sheets).
95. **i18n UI shell** — multi-language scaffolding.
96. ★ (E) **Sneakernet delta-sync** between two offline machines.
97. (E) **Master + field-replica** model (central authoring, field read).
98. **Scheduled nightly self-verify** + emailed/printed report.
99. **Local-only usage insights** (no telemetry leaves the box).
100. ⚑ **Disaster-recovery runbook** + one-command restore.

---

### How to use this + Vol. 1
Two hundred ideas total. Tell me a theme (A–T) or a set of line numbers, and I'll turn it into a verified
build wave (pure module + self-test + route + UI + R1–R10 docs), held to R13. Under R13, I build these in
**verified waves, not unverified bulk** — so "build everything" becomes a sequenced program, and each wave
is proven before the next. Recommended next from Vol. 2: **1, 10, 22 ⚑, 43, 71 ⚑, 80, 83, 96**.
