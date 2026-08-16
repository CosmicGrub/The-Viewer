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
    required_dirs = [
        'backend/tests', 'frontend/src', 'frontend/public',
        'data/extracted', 'data/meilisearch', 'docs', 'venv'
    ]
    
    missing = []
    for dir_path in required_dirs:
        if Path(dir_path).exists():
            print(f"✓ {dir_path}/")
        else:
            missing.append(dir_path)
            print(f"✗ {dir_path}/ - MISSING")
    
    return missing

def check_files():
    """Check required project files"""
    required_files = [
        'requirements.txt', '.gitignore', 'README.md',
        '.git/config', '.env' if Path('.env').exists() else None
    ]
    
    missing = []
    for file_path in required_files:
        if file_path and Path(file_path).exists():
            print(f"✓ {file_path}")
        elif file_path:
            missing.append(file_path)
            print(f"✗ {file_path} - MISSING")
    
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