# THE VIEWER — v1.1 Roadmap

> **historical — superseded, describes the v1.0.0/v1.1.0-era roadmap only.** Every item below (real semantic
> search, the visual index, hybrid ranking, and the rest) shipped long ago — see `docs/MASTER-RECONCILIATION.md`'s
> feature inventory. The codebase has since moved through 13+ more versions to **v1.14.0** (2026-08-18, the
> 50-finding 4-tier audit + UX pass + CI + doc reconciliation). For what's actually shipped and what's still
> open, read `docs/CHANGELOG.md` (newest entry first) instead of this file. Kept as-is below for historical
> record — not maintained.

v1.0.0 is cut and verify-green. This is the prioritized next lap: **[UPGRADE]** = new capability, **[EFFICIENCY]** =
speed/resource win, **[DEBT]** = cleanup that pays down risk. Effort: **S** ≤ half-day · **M** 1–2 days · **L** multi-day.

---

## NOW — finish what 1.0 started (highest leverage)

1. **[EFFICIENCY] Complete OCR to 100%, then re-index.** The single biggest value gap: ~56% of scanned pages still
   aren't text-searchable (stuck at 43.8%). Run `RESUME-OCR.bat`; when it finishes, run `engine/optimize_index.py`
   (FTS optimize + rebuild `suggest_terms` + `VACUUM`/`ANALYZE`) so search stays fast on the fuller index. **[you-run + M]**

2. **[UPGRADE] Turn on *real* semantic search.** `embed.py` already ships with the model path + a hash fallback.
   `pip install sentence-transformers` (one-time), then `BUILD-EMBEDDINGS.bat` (GPU). Prioritize the pages `hot_docs()`
   flags first so the most-used docs get vectors first. **[you-run + S]**

3. **[UPGRADE] Build the visual index.** `BUILD-VISUAL-INDEX.bat` over `index/figcache` → `/visual` goes live.
   Then a **v1.1 quality pass**: hash multiple crops per figure and add rotation buckets so a tilted phone photo still
   matches. **[you-run now + M for the quality pass]**

4. **[EFFICIENCY] Covering indexes for the new query paths.** The full-table `GROUP BY ocr_status` and per-status counts
   are slow on the 3.65 GB DB. Add covering indexes for the coverage/analytics/pmcs queries and cache `/api/coverage`
   like the page-render LRU already does. **[M]**

---

## NEXT — v1.1 features + wins

5. **[UPGRADE] Hybrid ranking (keyword + semantic).** Fuse FTS/BM25 rank with vector cosine (reciprocal-rank fusion) so
   results are both precise (exact NSN/part#) and smart (meaning). The single biggest search-quality jump. **[M]**

6. **[UPGRADE] Finish the PMCS checklist card.** `pmcs.py` already extracts structured items; render them + the interval
   grid into a printable **PMCS card PDF** per vehicle (reuse the `figuresheet`/`jobcard` reportlab pattern). **[M]**

7. **[UPGRADE] Precomputed look-alike index.** Today look-alikes are computed per query. Precompute a `lookalike.db`
   sidecar (same-name → differing NSN/UOC/CAGEC/SMR) so **every** part page can warn instantly and `/partdiff` is O(1).
   Resumable batch like `build_schemgraph`. **[M]**

8. **[UPGRADE] Cross-reference graph view.** `xref.py` returns assemblies/siblings/see-also; add an interactive graph on
   `/related` (reuse the schematic-flow SVG renderer) so a mechanic can *see* the assembly tree. **[M]**

9. **[EFFICIENCY] Cache the read-heavy API endpoints.** Add ETag/304 + a small TTL LRU to `/api/pmcs`, `/api/xref`,
   `/api/torque`, `/api/semantic` (the queries are deterministic per input). Extends the existing `fitz` LRU + ETag work
   from the 0.56 speed pass. **[S]**

10. **[EFFICIENCY] Rotate/compact `analytics.jsonl`.** It's append-only and unbounded. Add monthly rotation + a compacted
    aggregate so `top()`/`hot_docs()` stay O(1) as usage grows. **[S]**

11. **[UPGRADE] Server-side "My Bench" (optional).** Today it's per-browser `localStorage`. For a shared shop machine,
    add an opt-in `bench.db` sidecar so a pinned job survives a browser wipe / follows the mechanic. **[M]**

---

## LATER — bigger bets

12. **[UPGRADE] Tablet / kiosk mode.** Glove-friendly big-touch layout + high-contrast theme for a bay-floor tablet
    (the `:focus-visible`/ARIA a11y work is the foundation). **[L]**

13. **[UPGRADE] Photo annotation layer.** Let a mechanic drop notes/markups on a page or figure (append-only sidecar,
    never touches the corpus — R6). Pairs with My Bench. **[L]**

14. **[UPGRADE] Voice search (offline).** Deferred from the 10 recs; revisit with Vosk for hands-free bay use. **[L]**

15. **[EFFICIENCY] Parts-request → fillable AcroForm PDF.** `partspdf.py` prints + barcodes today; upgrade to a true
    fillable DA-2404/5988-E style form with editable qty fields. **[M]**

---

## EFFICIENCY / TECH-DEBT BACKLOG (do alongside features)

16. **[DEBT] Module consolidation.** Two procedure modules exist (`procedure_feature.py` legacy + `features/
    procedures_feature.py`); the CAD/figure render logic is duplicated across `figuresheet.py`/`jobcard.py`. Merge to
    one source each and delete the `.orig` leftovers. **[M]**

17. **[EFFICIENCY] Lazy-import heavy deps at the route level.** `numpy`/`reportlab`/`fitz`/`cv2` load on first use in most
    modules already; audit the rest so cold startup (and the frozen exe) boots faster. **[S]**

18. **[EFFICIENCY] Tier the test/hardening suites.** `VERIFY-099` (fast, always) vs `RUN-ALL-VERIFY` (adds slow mutation).
    Parallelize `mutate.py` across targets and cap fuzz N in the smoke tier — the full million-case run stays opt-in. **[S]**

19. **[EFFICIENCY] One launcher to rule them.** A `VIEWER-MENU.bat` that lists every .bat (run app, OCR, verify, builds,
    cut) with numbered choices — there are ~15 launchers now; a menu is friendlier on a shop PC. **[S]**

20. **[DEBT] ASCII-safe console output.** The audit/verify logs render `·`/`—`/`⚠` as `?`/`�` in the Windows cp437
    console. Swap to ASCII in the printed lines (keep unicode in the HTML/PDF). Cosmetic but tidies the logs. **[S]**

21. **[EFFICIENCY] Installer size.** ~~The PyInstaller bundle pulls numpy/reportlab/fitz/onnxruntime; add `excludes` for
    unused submodules and UPX so the shop-floor package is lean.~~ **[S]** — **PARTIALLY ADDRESSED** (`viewer.spec`
    now sets `excludes=["sentence_transformers", "torch", "torchvision", "torchaudio"]` — the only route into any of
    those is `engine/embed.py`'s already-optional `sentence_transformers` import, so this is a no-op for the shipped
    server; UPX was already `True` on both `EXE`/`COLLECT`, not actually missing. `onnxruntime`/`onnxruntime-gpu` were
    investigated and deliberately left bundled: `engine/sysprobe.py`'s `gpu_info()` is reached from real server-boot
    code (`viewer_app.main() -> rps_init() -> sysprobe.load_or_build()`), not just OCR-ingest tooling, and feeds the
    RPS modern/lite/legacy mode pick — excluding it would misdetect GPU hardware on boot, not just shrink the build.
    numpy/reportlab/fitz are genuine request-serving dependencies and were left alone. Not build-verified in this pass
    — no PyInstaller run/bundle-size measurement was done, only static import-graph tracing; see `viewer.spec` for the
    full reasoning.)

---

## Suggested v1.1 cut line
Ship **1.1** after **NOW (1–4)** + **NEXT items 5, 6, 9, 10** land and `RUN-ALL-VERIFY` stays green. Everything in
LATER is a 1.2+ theme. Keep R1–R10 discipline: each item = changelog + diagram + snapshot, verify host-side before cut.

<!-- END OF FILE -->
