#!/usr/bin/env python3
"""Download pinned OMB data and validate Git blob SHA-1 before saving locally."""
import hashlib, sys, urllib.request
from pathlib import Path
from replicate_omb_original import URL
GIT_BLOB_SHA1='01d67daf88003eab8a0e6c2ddaf694e30c4eae7d'

def verify(raw):
    blob=(f'blob {len(raw)}\0').encode('ascii')+raw
    actual=hashlib.sha1(blob).hexdigest()
    if actual!=GIT_BLOB_SHA1:raise ValueError(f'Git blob mismatch: {actual} expected {GIT_BLOB_SHA1}')
    return hashlib.sha256(raw).hexdigest()

def main():
    dst=Path(sys.argv[1] if len(sys.argv)>1 else 'data/omb_2025_individually_reported_AI_use_cases.csv')
    req=urllib.request.Request(URL,headers={'User-Agent':'JKG-research-reproducer/1.0'})
    with urllib.request.urlopen(req,timeout=45) as resp:raw=resp.read()
    digest=verify(raw)
    dst.parent.mkdir(parents=True,exist_ok=True)
    dst.write_bytes(raw)
    print('Downloaded',len(raw),'bytes; Git blob verified:',GIT_BLOB_SHA1,'SHA256:',digest)
    print('Saved',dst)
if __name__=='__main__':main()
