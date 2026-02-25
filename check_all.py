import os
import glob

TEMPLATES_DIR = '/home/sureshkumar-s/Documents/ECG-Digitiser/templates'
files = glob.glob(os.path.join(TEMPLATES_DIR, '*.html'))

for fpath in files:
    with open(fpath, 'r') as f:
        lines = f.readlines()
    print(f"File: {fpath}")
    # Print last 15 lines of the script section
    start = max(0, len(lines) - 20)
    for i in range(start, len(lines)):
        print(f"{i+1}: {lines[i].strip()}")
    print("-" * 20)
