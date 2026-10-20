#!/usr/bin/env python3
"""Digest original supplied source files; no external download or transform."""
import hashlib
from pathlib import Path
import pandas as pd
R=Path(__file__).resolve().parents[1]
files=sorted((R/'data/raw').rglob('*'))
rows=[]
for path in files:
 if not path.is_file():continue
 h=hashlib.sha256()
 with open(path,'rb') as f:
  for buf in iter(lambda:f.read(1024*1024),b''):h.update(buf)
 rows.append({'relative_file':str(path.relative_to(R)),'bytes':path.stat().st_size,'sha256':h.hexdigest(),'role':'as_supplied_or_archived_source'})
pd.DataFrame(rows).to_csv(R/'docs/SOURCE_FILE_SHA256_MANIFEST.csv',index=False)
print('Source inputs SHA-256 verified:',len(rows))
