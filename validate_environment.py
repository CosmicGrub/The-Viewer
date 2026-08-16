import sys
import subprocess
import os
from pathlib import Path

def check_python_modules():
    """Check all required Python packages"""
    modules = [
        'pdfplumber', 'pytesseract', 'python_docx', 'PIL',
        'cv2', 'meilisearch', 'fastapi', 'uvicorn', 'pydantic',
        'pytest', 'black', 'flake8', 'tqdm', 'requests'
    ]
    
    missing = []
    for module in modules:
        try:
            __import__(module)
            print(f"✓ {module}")
        except ImportError:
            missing.append(module)
            print(f"✗ {module} - MISSING")
    
    return missing

def check_external_tools():
    """Check external tools are in PATH"""
    tools = ['tesseract', 'git', 'node', 'npm']
    missing = []
    
    for tool in tools:
        try:
            subprocess.run([tool, '--version'], capture_output=True, check=True, timeout=5)
            print(f"✓ {tool}")
        except:
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