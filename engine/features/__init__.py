"""THE VIEWER -- engine/features/: the modularized server (backlog A1/A5/A7, v0.96.0).

viewer_app.py used to be a 2,400-line monolith: domain logic + a Handler with ~90 if/elif route
blocks. It is now a thin shell (config, DB plumbing, RPS init, Handler dispatch, main) and the
domain logic lives here, one module per feature area:

    registry.py      declarative {path: handler} route registry + central param validation (B11)
    search_feature   synonyms/keywords/tags, fuzzy, type-ahead suggest, FTS search, find-in-doc
    parts_feature    NSN lookups, look-alike diff, correlations/NIIN review, references, learning
    browse_feature   vehicle hub, sides, 3D/schematics lists, coverage, status/ops summaries
    procedures_feature  procedure parsing + torque specs
    render_feature   PDF page render pipeline (fitz/Poppler), page cache, words, callouts
    ingest_feature   add-docs preview/start/status
    sessions_feature parts-request sessions
    routes.py        every GET/POST route, registered declaratively

Each module follows the SAME dependency-injection pattern the earlier extractions established
(collections_feature, sides_feature, ...): viewer_app injects itself as `<module>.core` after
import, and modules call core.db() / core.DB_PATH / core.tm_side ... AT CALL TIME -- no import
cycles, and `--db`/RPS-mode changes propagate. The original monolith is preserved at
backups/pre-v0.96-restructure/viewer_app.py (R1: rollback = copy it back).
"""
