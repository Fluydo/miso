import sys
# Force UTF-8 encoding for all file I/O on Windows
if sys.platform == 'win32':
    sys.stdin.reconfigure(encoding='utf-8', errors='replace')
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
