"""
Usage:
  python tools\add_bg_from_path.py "C:\full\path\to\your\image.jpg"

This script copies the image at the provided path into the project's static folder
as `repairs/static/repairs/bg.jpg`. Run it from the project root.
"""
import sys
import os
import shutil

def main():
    if len(sys.argv) < 2:
        print("Usage: python tools\\add_bg_from_path.py C:\\path\\to\\image.jpg")
        return
    src = sys.argv[1]
    if not os.path.isfile(src):
        print(f"Source file does not exist: {src}")
        return
    proj_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    dest_dir = os.path.join(proj_root, 'repairs', 'static', 'repairs')
    os.makedirs(dest_dir, exist_ok=True)
    dest = os.path.join(dest_dir, 'bg.jpg')
    try:
        shutil.copy2(src, dest)
        print(f"Copied {src} -> {dest}")
    except Exception as e:
        print("Failed to copy:", e)

if __name__ == '__main__':
    main()
