# PyInstaller spec for THE VIEWER (v0.99.32) -- builds a standalone folder/exe so the app runs on a shop PC
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
    hookspath=[], runtime_hooks=[], excludes=[],
    win_no_prefer_redirects=False, win_private_assemblies=False, cipher=block_cipher, noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="THE_VIEWER",
          debug=False, bootloader_ignore_signals=False, strip=False, upx=True, console=True)
coll = COLLECT(exe, a.binaries, a.zipfiles, a.datas, strip=False, upx=True, name="THE_VIEWER")
# -- END OF FILE --
