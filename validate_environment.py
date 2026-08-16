import sys
import shutil
import os
from pathlib import Path

# Windows consoles typically default to a legacy codepage (e.g. cp1252)
# rather than UTF-8, which makes print()-ing the ✓/✗ characters below
# raise UnicodeEncodeError and kill the run. Reconfigure to UTF-8 first.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

def check_python_modules():
    """Check all required Python packages"""
    # (pip package name, the name it's actually imported under) — a
    # package's PyPI name and its import name don't always match, e.g.
    # `python-docx` is installed via pip but imported as `docx`.
    modules = [
        ('pdfplumber', 'pdfplumber'),
        ('pytesseract', 'pytesseract'),
        ('python-docx', 'docx'),
        ('Pillow', 'PIL'),
        ('opencv-python', 'cv2'),
        ('meilisearch', 'meilisearch'),
        ('fastapi', 'fastapi'),
        ('uvicorn', 'uvicorn'),
        ('pydantic', 'pydantic'),
        ('pytest', 'pytest'),
        ('black', 'black'),
        ('flake8', 'flake8'),
        ('tqdm', 'tqdm'),
        ('requests', 'requests'),
    ]

    missing = []
    for package_name, import_name in modules:
        try:
            __import__(import_name)
            print(f"✓ {package_name}")
        except ImportError:
            missing.append(package_name)
            print(f"✗ {package_name} - MISSING")

    return missing

def check_external_tools():
    """Check external tools are in PATH"""
    tools = ['tesseract', 'git', 'node', 'npm']
    missing = []

    for tool in tools:
        # shutil.which() correctly resolves Windows PATHEXT lookups (.exe,
        # .cmd, .bat, ...). subprocess.run([tool, ...]) without shell=True
        # cannot launch .cmd/.bat shims directly (e.g. npm.cmd) even when
        # the tool is genuinely installed and on PATH, which previously
        # made npm a false negative here.
        if shutil.which(tool):
            print(f"✓ {tool}")
        else:
            missing.append(tool)
            print(f"✗ {tool} - NOT FOUND")

    return missing

def check_folder_structure():
    """Check project folder structure"""
    # 'frontend/public' isn't part of this project's actual layout (there's
    # no static-assets folder in the Vite scaffold) — it used to be listed
    # here regardless, so a correctly-scaffolded checkout always failed
    # this check (finding #38).
    required_dirs = [
        'backend/tests', 'frontend/src',
        'data/extracted', 'data/meilisearch', 'docs',
    ]

    missing = []
    for dir_path in required_dirs:
        if Path(dir_path).exists():
            print(f"✓ {dir_path}/")
        else:
            missing.append(dir_path)
            print(f"✗ {dir_path}/ - MISSING")

    # A virtual environment is expected, but not under one specific
    # hardcoded name — `venv/`, `.venv/`, and "currently running inside
    # one" (sys.prefix != sys.base_prefix, true for any activated venv/
    # conda env regardless of its folder name or location) all count.
    # Previously only a literal ./venv folder passed, which spuriously
    # failed anyone using `.venv`, a global env manager, or conda
    # (finding #40).
    in_active_venv = sys.prefix != getattr(sys, "base_prefix", sys.prefix)
    if in_active_venv or Path('venv').exists() or Path('.venv').exists():
        print("✓ virtual environment")
    else:
        missing.append('virtual environment (venv/, .venv/, or an activated env)')
        print("✗ virtual environment - NOT FOUND (expected venv/, .venv/, or an activated env)")

    return missing

def check_files():
    """Check required project files"""
    required_files = ['requirements.txt', '.gitignore', 'README.md', '.git/config']

    missing = []
    for file_path in required_files:
        if Path(file_path).exists():
            print(f"✓ {file_path}")
        else:
            missing.append(file_path)
            print(f"✗ {file_path} - MISSING")

    # .env is expected per the README's Setup instructions but isn't
    # strictly required (TM_SOURCE_DIR/TM_OUTPUT_DIR can be passed as CLI
    # args instead — see config.py) — so its absence is reported but
    # doesn't fail validation on its own. Previously this check could
    # *never* report .env as missing at all (it only checked for it when
    # it already existed), which is the one file most likely to be
    # forgotten on a fresh clone (finding #39).
    if Path('.env').exists():
        print("✓ .env")
    else:
        print("⚠ .env - not found (optional if TM_SOURCE_DIR is set another way — see .env.example)")

    return missing

def main():
    print("=" * 60)
    print("DAY 1 ENVIRONMENT VALIDATION")
    print("=" * 60)
    
    print("\n[1/4] Checking Python Modules...")
    missing_modules = check_python_modules()
    
    print("\n[2/4] Checking External Tools...")
    missing_tools = check_external_tools()
    
    print("\n[3/4] Checking Folder Structure...")
    missing_dirs = check_folder_structure()
    
    print("\n[4/4] Checking Project Files...")
    missing_files = check_files()
    
    print("\n" + "=" * 60)
    print("VALIDATION SUMMARY")
    print("=" * 60)
    
    all_missing = missing_modules + missing_tools + missing_dirs + missing_files
    
    if not all_missing:
        print("✓ ALL CHECKS PASSED - Environment is ready for Day 2!")
        return 0
    else:
        print(f"✗ {len(all_missing)} ISSUE(S) FOUND:")
        for item in all_missing:
            print(f"  - {item}")
        return 1

if __name__ == "__main__":
    sys.exit(main())