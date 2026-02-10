import os
import re
import glob
from pathlib import Path

# Configuration
cargs = {
    "root_dir": "/Users/rico/Dev/sports-models",
    "backup_patterns": [r".*\.bak$", r".*\.backup$", r".*~", r".*_backup\.py$"],
    "log_patterns": [r".*\.log$"],
    "temp_patterns": [r"^debug_.*\.py$", r"^check_.*\.py$", r"^test_.*\.py$"],
    "large_file_threshold": 5 * 1024 * 1024, # 5MB
    "ignore_dirs": [".git", ".venv", "__pycache__", ".agent", ".claude", "node_modules", ".DS_Store", "chrome_profile", "images", ".cache"]
}

def get_all_files(root):
    all_files = []
    for dirpath, dirnames, filenames in os.walk(root):
        # Filter directories
        dirnames[:] = [d for d in dirnames if d not in cargs["ignore_dirs"]]
        
        for f in filenames:
            if f == ".DS_Store": continue
            full_path = Path(dirpath) / f
            all_files.append(full_path)
    return all_files

def check_references(target_file, all_files, root):
    """Check if target_file is referenced in any other file."""
    name = target_file.name
    stem = target_file.stem
    
    # We look for the filename or the module name (for python)
    search_terms = {name}
    if target_file.suffix == '.py':
        search_terms.add(stem)
    
    ref_count = 0
    referenced_by = []
    
    for f in all_files:
        if f == target_file:
            continue
        
        # Skip binary files for text search if possible, or handle errors
        try:
            content = f.read_text(errors='ignore')
            for term in search_terms:
                # Simple check: term appears in content
                # For python imports, we might want to be more specific, but this is a broad sweep
                # "import term" or "from term" or "python term.py" or "bash term.sh"
                if term in content:
                    ref_count += 1
                    referenced_by.append(f.relative_to(root))
                    break 
        except Exception:
            pass
            
    return ref_count, referenced_by

def main():
    root = Path(cargs["root_dir"]).resolve()
    print(f"Analyzing codebase at: {root}\n")
    
    all_files = get_all_files(root)
    
    backups = []
    logs = []
    temp_scripts = []
    large_files = []
    
    # scan for patterns
    for f in all_files:
        name = f.name
        size = f.stat().st_size
        
        # Large files
        if size > cargs["large_file_threshold"]:
            large_files.append((f, size))
            
        # Backups
        for pat in cargs["backup_patterns"]:
            if re.match(pat, name):
                backups.append(f)
                break
                
        # Logs
        for pat in cargs["log_patterns"]:
            if re.match(pat, name):
                logs.append(f)
                break
                
        # Temp/Debug
        for pat in cargs["temp_patterns"]:
            if re.match(pat, name):
                temp_scripts.append(f)
                break

    print("--- 1. High Confidence Cleanup Candidates (Backups/Logs) ---")
    for f in backups:
        print(f"[BACKUP] {f.relative_to(root)} ({f.stat().st_size / 1024:.1f} KB)")
    for f in logs:
        print(f"[LOG]    {f.relative_to(root)} ({f.stat().st_size / 1024 / 1024:.1f} MB)")
        
    print("\n--- 2. Potential Cleanup Candidates (Debug/Test Scripts) ---")
    print("(Verify these are not currently needed)")
    for f in temp_scripts:
        print(f"[SCRIPT] {f.relative_to(root)}")

    print("\n--- 3. Large Files (> 5MB) ---")
    for f, size in large_files:
        print(f"[LARGE]  {f.relative_to(root)} ({size / 1024 / 1024:.1f} MB)")

    print("\n--- 4. Unreferenced Python Files (Orphans) ---")
    print("(Scanning for python files not imported or mentioned in other files...)")
    
    py_files = [f for f in all_files if f.suffix == '.py']
    orphans = []
    
    for f in py_files:
        # Skip if already identified as debug/test/backup
        if f in backups or f in temp_scripts:
            continue
            
        count, refs = check_references(f, all_files, root)
        if count == 0:
            orphans.append(f)
            
    for f in orphans:
        print(f"[ORPHAN] {f.relative_to(root)}")

if __name__ == "__main__":
    main()
