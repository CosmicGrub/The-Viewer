# react/

`TheViewer.jsx` is a **design/UI reference mockup**, not part of the live application.

It was carried over wholesale in the commit that imported this project's working tree (`8cc9c17`). There is no `package.json`, bundler config, or build step anywhere in this repository for it — it cannot be compiled or run as-is, and nothing in `engine/` imports or serves it.

**The real, live UI is `engine/ui/*.html`** — plain HTML/vanilla JS (ES5-safe for the legacy/RPS tier), served directly off disk by `engine/viewer_app.py` via `engine/features/routes.py`'s static-page registry. `TheViewer.jsx`'s own header comment says as much: *"the real app is vanilla HTML/JS ... this is a single-file React demonstration of the same interface."*

Kept as reference rather than removed: its dark-slate/sky-accent/`Ctrl+K`-search visual language has already been used once as a starting point for a real (separate) frontend build, so it has demonstrated genuine reuse value as a design reference. If you're looking for the application someone can actually run, start at `engine/viewer_app.py` and `engine/ui/`, not here.
