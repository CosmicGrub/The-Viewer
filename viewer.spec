# PyInstaller spec for THE VIEWER -- builds a standalone folder/exe so the app runs on a shop PC
# (version comes from engine/viewer_app.py's VERSION constant -- not duplicated here, so this comment
# can't drift out of sync with it the way it did before: last read v0.99.32 while the app was on v1.13.2)
# with NO Python install. Build host-side:  BUILD-INSTALLER.bat  (which runs: pyinstaller viewer.spec)
# The corpus/index are NOT bundled (they're huge + machine-specific) -- FIRST-RUN.bat junctions/points to them.
# -*- mode: python ; coding: utf-8 -*-
import os
block_cipher = None
ENG = os.path.join(os.getcwd(), "engine")

a = Analysis(
    [os.path.join("engine", "viewer_app.py")],
    pathex=[ENG],
    binaries=[],
    datas=[(os.path.join("engine", "ui"), "ui")],   # bundle the UI pages/scripts next to the exe
    hiddenimports=[
        "features.registry", "features.routes", "features.search_feature", "features.parts_feature",
        "features.browse_feature", "features.procedures_feature", "features.render_feature",
        "features.ingest_feature", "features.sessions_feature",
        "jobcard", "figureparts", "partlocate", "figuresheet", "coverage", "doctor", "pmcs",
        "xref", "analytics", "partspdf", "vectorize", "phash", "embed", "schemreview", "localmodel",
    ],
    # Roadmap "Installer size" item: viewer_app.py's route handlers never import these, so PyInstaller's
    # static import-follower has no business bundling them just because they happen to be installed on
    # the build host (e.g. for OCR ingest tooling / dev experimentation).
    #   - sentence_transformers/torch/torchvision/torchaudio: engine/embed.py's _load_model() imports
    #     sentence_transformers inside a try/except and is the ONLY place in the served app that ever
    #     imports it (confirmed by tracing every reachable import from this Analysis entry point --
    #     features/routes.py's /api/semantic and /api/search_hybrid routes both funnel through
    #     embed.search()/embed.embed_text(), which already falls back to a pure-numpy hash vector when
    #     sentence_transformers is absent). Excluding it is a strict no-op for the shipped server.
    #   - onnxruntime/onnxruntime-gpu deliberately NOT excluded: engine/sysprobe.py's gpu_info() (reached
    #     from viewer_app.main() -> rps_init() -> sysprobe.load_or_build() -> build_profile(), i.e. real
    #     server-boot code, not just the separate OCR-ingest subprocess tooling in viewer_ingest.py) does
    #     `import onnxruntime as ort` to detect CUDA availability. That result feeds `tier`, which
    #     `rps.mode_for()` uses to pick modern/lite/legacy at boot -- so on a shop PC with a modest CPU but
    #     a capable GPU, excluding onnxruntime would silently downgrade it from "modern" to "lite" mode
    #     (the import is wrapped in try/except so it wouldn't crash, but it would misdetect real hardware
    #     and pick a worse runtime mode for the request-serving app itself). Left in until that RPS
    #     coupling is decoupled from onnxruntime, or the profile is rebuilt outside the frozen exe.
    excludes=["sentence_transformers", "torch", "torchvision", "torchaudio"],
    win_no_prefer_redirects=False, win_private_assemblies=False, cipher=block_cipher, noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="THE_VIEWER",
          debug=False, bootloader_ignore_signals=False, strip=False, upx=True, console=True)
coll = COLLECT(exe, a.binaries, a.zipfiles, a.datas, strip=False, upx=True, name="THE_VIEWER")
# -- END OF FILE --
