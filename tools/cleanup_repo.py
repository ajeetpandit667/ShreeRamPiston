"""
Run from project root to archive developer helper scripts and images and produce a debug-print report.

Usage:
    python tools\cleanup_repo.py

What it does:
 - Creates `tools/archive/scripts` and `tools/archive/images`.
 - Moves common helper files (run_*.py, test_*.py, run_*.bat) from project root into archive.
 - Moves common image files from project root into archive/images.
 - Scans `.py` files under the project for occurrences of `print(`, `TODO`, and `DEBUG` and writes a report to `tools/cleanup_report.txt`.

It does NOT modify source files automatically; it only archives and reports so you can review changes safely.
"""
import os
import shutil

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
ARCHIVE = os.path.join(ROOT, 'tools', 'archive')
SCRIPTS_ARCHIVE = os.path.join(ARCHIVE, 'scripts')
IMAGES_ARCHIVE = os.path.join(ARCHIVE, 'images')

os.makedirs(SCRIPTS_ARCHIVE, exist_ok=True)
os.makedirs(IMAGES_ARCHIVE, exist_ok=True)

# Patterns to move from project root
root = ROOT
move_patterns = [
    'run_*.py', 'test_*.py', 'run_*.bat'
]
moved = []
for pat in move_patterns:
    for fn in os.listdir(root):
        if fn.lower().startswith(pat.split('*')[0]) and fn.lower().endswith(pat.split('*')[-1] or ''):
            src = os.path.join(root, fn)
            if os.path.isfile(src):
                dst = os.path.join(SCRIPTS_ARCHIVE, fn)
                shutil.move(src, dst)
                moved.append(dst)

# Move common image types from project root to images archive
for fn in os.listdir(root):
    if fn.lower().endswith(('.jpg', '.jpeg', '.png', '.gif')):
        src = os.path.join(root, fn)
        if os.path.isfile(src):
            dst = os.path.join(IMAGES_ARCHIVE, fn)
            shutil.move(src, dst)
            moved.append(dst)

# Scan project for debug prints and TODOs
report_lines = []
for dirpath, dirnames, filenames in os.walk(ROOT):
    # skip virtual envs and .git
    if '.git' in dirpath.split(os.sep):
        continue
    for fn in filenames:
        if fn.endswith('.py'):
            path = os.path.join(dirpath, fn)
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    for i, line in enumerate(f, start=1):
                        if 'print(' in line or 'TODO' in line or 'DEBUG' in line:
                            report_lines.append(f"{path}:{i}: {line.strip()}")
            except Exception:
                # binary or unreadable
                pass

report_path = os.path.join(ROOT, 'tools', 'cleanup_report.txt')
with open(report_path, 'w', encoding='utf-8') as r:
    r.write("Archived files:\n")
    for p in moved:
        r.write(p + '\n')
    r.write('\nScan for prints/TODO/DEBUG:\n')
    for l in report_lines:
        r.write(l + '\n')

print('Archived files count:', len(moved))
print('Report written to', report_path)
