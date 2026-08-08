#!/usr/bin/env python3
"""Generate docs/diagrams/CHANGELOG-VISUAL.svg + .pdf (rule R5).
Add a tuple to V for each new version, then run:  python _make_changelog_visual.py
Requires cairosvg (pip install cairosvg).
Latest: 0.27.0 schematic legibility viewer."""
import cairosvg, html, os

KIND_FILL = {"feat": ("#16301f", "#2f5a3e"), "fix": ("#3a2f1a", "#6b5526"), "rule": ("#1a2740", "#3a4d6e")}

# (version, title, kind, [flow nodes], explanation)  -- newest appended at the end (chronological)
V = [
 ("0.1.0","Architecture & diagrams","rule",
   ["Corpus (read-only)","Design decisions","Versioned schema","Diagrams (R1/R2)"],
   "Locked: local web app + SQLite/FTS5 + text-first. Established rules R1 (backwards-compatible) and R2 (diagram per addition)."),
 ("0.2.0","Indexing engine + OCR pipeline","feat",
   ["Crawl","Extract text","FTS5 index","OCR queue"],
   "viewer_ingest + migration 0001 (documents/pages/pages_fts/jobs/runs). Text-first, resumable, idempotent; durable OCR job queue."),
 ("0.3.0","Onboarding + 104th parts request","feat",
   ["Onboarding modal","Search","Parts cart","104th PDF"],
   "Migration 0002 (sessions/faults/request_items). Offline app + dark UI; clean PDF replica of the 104th ECC sheet, header from the modal."),
 ("0.4.0","Full-corpus extraction + durability","fix",
   ["Batch crawl","Cheap skip","TRUNCATE journal","Resumable"],
   "Time-boxed resumable batches + cheap skip (size+mtime). Fixed corruption by switching to EXCLUSIVE + on-disk TRUNCATE journal."),
 ("0.5.0","PyMuPDF text backend","feat",
   ["PDF","PyMuPDF get_text","pages text"],
   "Text extraction moved to PyMuPDF (pip) with Poppler fallback - faster and removes the Poppler hard dependency."),
 ("0.6.0","RapidOCR engine; full run","feat",
   ["Scanned page","PyMuPDF render","RapidOCR","FTS5"],
   "OCR engine = RapidOCR (pip, no admin). Full crawl COMPLETED on PC: 40,291 docs, ~1.87M searchable text pages, ~133k queued for OCR."),
 ("0.6.1","OCR detail + example","feat",
   ["Scan","OCR","142 lines @99%"],
   "Detailed OCR diagram + a real before/after example page (recovered part numbers from a scanned parts page)."),
 ("0.7.0","Dark diagram standard (R3)","rule",
   ["Dark SVG","cairosvg","PDF"],
   "Rule R3: all diagrams dark-themed + a PDF version. Converted existing diagrams; viewer.html switched to dark."),
 ("0.8.0","Search GUI: document viewer","feat",
   ["Result","/page render","Viewer pane","Add part"],
   "On-demand page rendering (PyMuPDF) + viewer pane: click a result to see the real manual page, navigate, add the part to the request."),
 ("0.8.1","OCR reliability fixes","fix",
   ["cleanup (drop /tmp rows)","Thread OCR","Live progress","done, failed=0"],
   "Root cause: orphan sandbox-path rows failed instantly. Added cleanup + switched to thread-based OCR. Verified real text, zero failures."),
 ("0.9.0","Forked: GPU + Lite","feat",
   ["Shared core","GPU build (--gpu)","Lite portable","make_portable"],
   "One codebase, two profiles: GPU/production (priority) and Lite/portable (self-contained folder + finished index). Flags --gpu/--dpi."),
 ("0.9.1","Changelog standard (R4)","rule",
   ["Change","CHANGELOG.md entry"],
   "Rule R4: a versioned changelog entry accompanies every change. Retroactive CHANGELOG.md created."),
 ("0.9.2","Visual changelog (R5)","rule",
   ["Change","Changelog entry","Graphical panel","PDF"],
   "Rule R5: every changelog entry also gets a detailed graphical explanation + a functioning diagram PDF (this document)."),
 ("0.9.3","Launcher pip self-upgrade","fix",
   ["Launch .bat","upgrade pip","install deps","run"],
   "All setup/launch files now run pip install --upgrade pip before installing packages, so nothing is missing and the app launches cleanly."),
 ("0.9.4","Nomenclature carries to the sheet","fix",
   ["Search match (snippet)","deriveName","Item name (editable)","104th PDF"],
   "Part nomenclature now auto-fills the cart Item Name from the matched manual line (or search term), so it carries onto the parts request sheet."),
 ("0.10.0","NSN search + Vehicle breakdown hub","feat",
   ["Full NSN","Exact match + classify","Vehicle hub (grouped)","Open real page"],
   "Type a full NSN (part or whole-vehicle); vehicle NSN opens a hub grouping the entire manual set (operator/maint/parts/troubleshooting/schematics), each opening the actual page."),
 ("0.11.0","Express modal + Schematics on every page","feat",
   ["Express field (NSN/part)","Bypass → page/hub","Viewer schematics panel","Always a graphic"],
   "Modal 'What do you need?' jumps straight to the page/hub on exact NSN/part#; the viewer always shows a Schematics & install panel (cited figure → page → vehicle schematic set), verbatim & cited."),
 ("0.12.0","OCR speedup: skip-junk + prioritize","feat",
   ["Pending","Prioritize (parts first)","Blank? skip","OCR real pages"],
   "Skip-the-junk: blank pages skipped with no OCR inference (~0.01s). Prioritized queue OCRs parts catalogs first. Migration 0003 + narrowed FTS trigger (faster requeues)."),
 ("0.13.0","Dynamic front-end UX pass","feat",
   ["Home (browse-by-vehicle)","Smart results (filters+counts)","Viewer zoom/thumbs/highlight","Responsive + large text"],
   "Home screen browses every vehicle + recents (/api/vehicles, /api/sessions). Results gain filters/counts by vehicle/type/source. Viewer adds zoom, a thumbnail strip, and highlight-the-hit (/page?hl via PyMuPDF search_for). Responsive/touch + large-text + simple/advanced toggles. Additive."),
 ("0.14.0","Search upgrades: Last-4 + smart key terms","feat",
   ["Query (one box)","Router by shape","Last-4 / NSN / key-terms","build_match → FTS5"],
   "Type 4 digits for a Last-4 cover/end-item NSN lookup (with a full-text escape hatch). Key-term search gains synonyms (synonyms.json), offline fuzzy typo tolerance (fts5vocab, edit-distance 1), part#/FIG/callout phrase precision, and an All/Any toggle. Additive."),
 ("0.15.0","Modal aligned to the 104th sheet header","feat",
   ["Modal field","SESSION key","104th header block","Live preview + 104th PDF"],
   "Onboarding modal now mirrors the 104th sheet header 1:1 (exact labels & order); header fields always shown (Simple only hides cart FEDLOG); a live paper-style header preview fills in as you type. Field IDs/SESSION keys unchanged -> identical PDF. Additive."),
 ("0.16.0","Self-learning search + calmer UI","feat",
   ["104th sheet generated","request_items (the log)","/api/popular (freq+recency)","Rotating example · quick-picks · ranked"],
   "Surfaces what you already log: GET /api/popular ranks parts that reached a generated sheet by frequency+recency. Drives a single rotating example, a 'commonly requested' quick-pick row, and popularity-ranked results (★ requested). Seed list for cold start; copy trimmed. No migration."),
 ("0.17.0","Tech Status from fault+part (PMCS-cited)","feat",
   ["Fault + parts","GET /api/techstatus","PMCS criteria (cited) / history","Mandatory confirm → 104th"],
   "Suggests equipment status from the fault: searches the vehicle's PMCS 'Not Fully Mission Capable If' criteria (cited, TM+page) -> deadline=NMCS; else prior history; else manual. Mandatory confirm gate at export (server rejects blank). Full codes FMC/PMCM/PMCS/NMCM/NMCS. App proposes & cites, human confirms."),
 ("0.18.0","Switchable layouts behind Settings","feat",
   ["⚙ Settings (preset / fine-tune)","applySettings()","body CSS classes + 2 JS vars","localStorage (per device) · core untouched"],
   "A Settings panel consolidates the toggles + 4 named presets (Simple/Advanced/Shopfloor/Compact), per-device persist + Reset, legacy keys migrated. Presentation only: a layout is just CSS classes + 2 defaults; the dataset, search, and 104th flow are invariant. Client-only, no server/schema change."),
 ("0.19.0","Structured parts index (Phase 1) + coverage","feat",
   ["RPSTL pages","viewer_ingest parts","parts: NSN→figure (cited)","/api/part · cart ref · coverage"],
   "Extracts a cited NSN→figure→page→vehicle index from RPSTL pages (migration 0004; 28,330 records on the sample). Cart shows the cited catalog figure + auto-fills FIG; vehicle hub shows '% searchable'. Multi-sheet 104th + tech-status suggestion capture. Exact part#/variant alignment deferred (OCR-noisy) — honest grounding."),
 ("0.20.0","Online → offline reference enrichment","feat",
   ["Official sources (once)","viewer_ingest enrich","ref_hardware + ref_nsn (cited)","/api/reference · cart label"],
   "One-time online enrichment, offline after: public-domain FED-STD-H28 hardware/thread dims + official GSA NSN extract (filtered to in-index NSNs). Separate cited tables (migration 0005), labeled 'External reference'; torque is general ref (TM governs); third-party scrapers excluded. Fills sheet nomenclature + Tier 2.5 dimensions."),
 ("0.21.0","Append-only NSN enrichment (rule R6)","rule",
   ["GSA extract (re-fetch)","ref_nsn_log (append every version)","ref_nsn current pointer","/api/reference + 'N versions'"],
   "Rule R6: always add, never remove info (even outdated). NSN enrichment is now append-only/versioned (migration 0006, ref_nsn_log) — old + new both kept; current = latest. Space/scope: NSNs are cheap text (tens of MB); whole TMs are heavy (GB + OCR) and a separate sourcing path."),
 ("0.21.1","One-time enrichment reads GSA XLSX","fix",
   ["data.gov GSA extract (.xlsx)","enrich --gsa (streams xlsx/csv)","match in-index NSNs","append (R6)"],
   "enrich now reads the official GSA NSN Extract directly as .xlsx (the actual data.gov format) as well as csv. Engine stays offline; one-shot hand-run filler. Source is public-domain (CC0) but the GSA Advantage subset, dated 2017 — fills commercially-listed NSNs only; kept append-only & cited."),
 ("0.22.0","PUB LOG reference ingest (POC)","feat",
   ["PUB LOG export (CSV/XLSX)","enrich --publog (in-index NSNs)","ref_nsn +part#/CAGE/char/AAC/subs","cart auto-fills part# + AAC"],
   "POC: enrich --publog ingests the authoritative DLA PUB LOG export — fills NSN→item name, part#/CAGE (MCRD), characteristics=size for Tier 2.5 (CHAR), AAC + substitutes (MDI&S). Migration 0007; append-only/cited (R6); cart auto-fills authoritative part# and AAC. Verified on in-index NSNs. Real fill = one-time PUB LOG download on a connected machine."),
 ("0.23.0","PUB LOG via FLIS Reading Room (direct CSVs)","feat",
   ["Reading Room monthly CSVs","enrich --publog-dir","merge per NSN (non-clobbering)","cited offline reference"],
   "Correction: no PUB LOG Windows app needed — the FLIS Reading Room publishes monthly CSVs (Identification/Reference/Characteristics/Management/CAGE/History). enrich --publog-dir reads the folder, keeps in-index NSNs, composes NSN from FSC+NIIN, and merges fields per NSN without clobbering. History.zip keeps inactive NSNs (R6). Verified."),
 ("0.24.0","PUB LOG enrichment RUN on the live index","feat",
   ["16 GB FLIS Reading Room","enrich_flis (NIIN-keyed)","468 NSNs enriched","live in viewer.db (R6)"],
   "Ran the real DLA FLIS catalog into the live index: 468 NSNs got item names (406), part numbers (463), AAC (451), decoded characteristics/dimensions (421), unit prices. enrich_flis() productizes the NIIN-keyed ingest (INC->name via H6, char aggregation) for monthly re-runs. Index verified intact (39,683 docs). Append-only (R6)."),
 ("0.25.0","Overnight: full-catalog enrichment + 2D→3D + rollback","feat",
   ["Parts on full index (45k NSNs)","FLIS enrichment 41,701 NSNs","Supersession/vintage/multi-choice + 2D→3D","Rollback (R1) ready"],
   "On the live index: 227,908 parts records (45,068 NSNs); FLIS enrichment of 41,701 NSNs (names, part#/CAGE, dimensions, AAC, price, vintage date, supersession cross-refs, multiple part choices). New: FLIS year tag + supersession + multiple-choice in the cart; offline rotatable 2D→3D viewer sized to FLIS dims (cited). Search ~45ms. One-click rollback (run_rollback.bat). OCR to 100% remains a GPU job."),
 ("0.26.0","3D viewer: family shapes + material/colour","feat",
   ["FLIS dims (expanded)","Family shape (cyl/hex/disc/box)","Material/colour tint (cited)","Depth-shaded solid"],
   "Representative 3D viewer upgraded: renders family shapes from the item name with depth-sorted filled faces; tints to the FLIS-stated colour (cited) or a material-based representative tint (steel→grey, aluminium→silver, copper→bronze), labelled; expanded dimension parsing; button gated to ~20,869 parts that actually carry a bounding dimension."),
 ("0.27.0","Schematic legibility viewer","feat",
   ["Real page (PyMuPDF)","Clean + contrast (Pillow)","3D tilt (CSS)","Hover loupe 2.6×"],
   "Same drawing, made readable: a Clean toggle + contrast slider re-render the page through a grounded enhancement pipeline (grayscale, auto-contrast, de-speckle, unsharp, optional high-contrast/binarize); a flat-sheet 3D tilt (CSS perspective rotateY) and a cursor-following 2.6× loupe. Off by default, presentation-only — dataset, search and 104th sheet untouched (R1/R6). Nothing invented; cited to its page."),
 # NOTE (backlog #81): entries 0.28.0–0.95.0 are pending backfill — this strip stalled while the
 # program advanced; docs/CHANGELOG.md is the authoritative record of every version.
 ("0.96.0","THE RESTRUCTURE: monolith → features/ package","rule",
   ["2,407-line monolith","Thin shell + 9 feature modules","Route registry + ONE error boundary","Hardening: 400/413/403 + logs"],
   "viewer_app.py split into a ~330-line shell + engine/features/ (search/parts/browse/procedures/render/ingest/sessions + registry/routes), same DI pattern as the earlier extractions; every public name re-exported so tests/scripts are untouched. Shipped with B/J hardening (central param validation → 400, POST body cap 413, same-origin 403, rotating error log, graceful shutdown), the dedup foundation (theme.py + base.css + shared.js + patterns.py adoption), and the RPS lint wired into VERIFY-ALL. 75 regression + 59 route-smoke + 12 hardening tests green; monolith preserved in backups/pre-v0.96-restructure (R1)."),
]

def esc(s): return html.escape(s)

def build():
    W=1020; HEAD=120; ROW=132; H=HEAD+ROW*len(V)+30
    P=[f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" role="img" font-family="-apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif">']
    P.append('<defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#9aa5b1"/></marker></defs>')
    P.append(f'<rect x="0" y="0" width="{W}" height="{H}" fill="#0f1419"/>')
    P.append('<text x="40" y="52" font-size="24" font-weight="700" fill="#e6e9ee">THE VIEWER — Visual Changelog</text>')
    P.append('<text x="40" y="78" font-size="12" fill="#9aa6b6">A functioning data-flow panel for every version (chronological). Dark (R3) · PDF (R5) · accompanies docs/CHANGELOG.md (R4).</text>')
    P.append(f'<line x1="40" y1="98" x2="{W-40}" y2="98" stroke="#2a2f37"/>')
    P.append('<rect x="40" y="104" width="12" height="10" rx="2" fill="#16301f" stroke="#2f5a3e"/><text x="58" y="113" font-size="10" fill="#9aa6b6">feature</text>')
    P.append('<rect x="120" y="104" width="12" height="10" rx="2" fill="#3a2f1a" stroke="#6b5526"/><text x="138" y="113" font-size="10" fill="#9aa6b6">fix</text>')
    P.append('<rect x="178" y="104" width="12" height="10" rx="2" fill="#1a2740" stroke="#3a4d6e"/><text x="196" y="113" font-size="10" fill="#9aa6b6">rule/standard</text>')
    for i,(ver,title,kind,flow,expl) in enumerate(V):
        y=HEAD+i*ROW; bf,bs=KIND_FILL[kind]
        P.append(f'<line x1="150" y1="{y}" x2="150" y2="{y+ROW}" stroke="#2a2f37"/>')
        P.append(f'<circle cx="150" cy="{y+34}" r="7" fill="{bf}" stroke="{bs}"/>')
        P.append(f'<rect x="40" y="{y+18}" width="92" height="30" rx="7" fill="{bf}" stroke="{bs}"/>')
        P.append(f'<text x="86" y="{y+38}" text-anchor="middle" font-size="14" font-weight="700" fill="#e6e9ee">{esc(ver)}</text>')
        P.append(f'<text x="172" y="{y+30}" font-size="14.5" font-weight="700" fill="#e6e9ee">{esc(title)}</text>')
        words=expl.split(); lines=[]; cur=""
        for w in words:
            if len(cur)+len(w)+1>112: lines.append(cur); cur=w
            else: cur=(cur+" "+w).strip()
        if cur: lines.append(cur)
        for li,ln in enumerate(lines[:2]):
            P.append(f'<text x="172" y="{y+50+li*15}" font-size="10.5" fill="#9aa6b6">{esc(ln)}</text>')
        fx=172; fy=y+84; bw=160 if len(flow)<=4 else 132; gap=26
        for j,node in enumerate(flow):
            x=fx+j*(bw+gap)
            P.append(f'<rect x="{x}" y="{fy}" width="{bw}" height="36" rx="8" fill="#1c2430" stroke="#38414e"/>')
            if len(node)<=(24 if bw>=160 else 20):
                P.append(f'<text x="{x+bw/2}" y="{fy+23}" text-anchor="middle" font-size="10.5" fill="#e6e9ee">{esc(node)}</text>')
            else:
                half=len(node)//2; sp=node.rfind(" ",0,half+6); sp=sp if sp>0 else half
                P.append(f'<text x="{x+bw/2}" y="{fy+16}" text-anchor="middle" font-size="9.5" fill="#e6e9ee">{esc(node[:sp])}</text>')
                P.append(f'<text x="{x+bw/2}" y="{fy+28}" text-anchor="middle" font-size="9.5" fill="#e6e9ee">{esc(node[sp:].strip())}</text>')
            if j<len(flow)-1:
                ax=x+bw; P.append(f'<path d="M{ax},{fy+18} L{ax+gap},{fy+18}" stroke="#9aa5b1" stroke-width="1.6" fill="none" marker-end="url(#a)"/>')
    P.append(f'<text x="40" y="{H-12}" font-size="10" fill="#6b7280">Rules in effect: R1 backwards-compatible · R2 diagram per addition · R3 dark+PDF · R4 changelog per change · R5 graphical changelog + PDF.</text>')
    P.append('</svg>')
    return "\n".join(P)

if __name__ == "__main__":
    here=os.path.dirname(os.path.abspath(__file__)); base=os.path.join(here,"CHANGELOG-VISUAL")
    svg=build(); open(base+".svg","w",encoding="utf-8").write(svg)
    cairosvg.svg2pdf(bytestring=svg.encode("utf-8"), write_to=base+".pdf")
    print("wrote CHANGELOG-VISUAL.svg + .pdf")
