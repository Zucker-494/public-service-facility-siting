#!/usr/bin/env python3
"""Write a SHA-256 inventory for the source files supplied with the project."""
import hashlib
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'data' / 'raw'
DEST = ROOT / 'data' / 'qa' / 'source_file_sha256_manifest.csv'

rows = []
for path in sorted(p for p in RAW.rglob('*') if p.is_file()):
    digest = hashlib.sha256()
    with path.open('rb') as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(chunk)
    rows.append({
        'relative_file': path.relative_to(ROOT).as_posix(),
        'bytes': path.stat().st_size,
        'sha256': digest.hexdigest(),
        'role': 'source_data',
    })

DEST.parent.mkdir(parents=True, exist_ok=True)
pd.DataFrame(rows, columns=['relative_file', 'bytes', 'sha256', 'role']).to_csv(DEST, index=False)
print(f'Source-file manifest written: {DEST.relative_to(ROOT)} ({len(rows)} files)')
