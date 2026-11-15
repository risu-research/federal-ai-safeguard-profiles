#!/usr/bin/env python3
"""Reproducibility gate. The official raw CSV is mandatory for --csv and
never silently replaced by the derived 227-row fixture.
"""
import argparse,csv,hashlib,json
from collections import Counter
from pathlib import Path
from replicate_omb_original import read_official,FIELDS,report
from analyze_distinguishability import summary, pair_breakdown

ROOT=Path(__file__).resolve().parents[1]
MAN=json.loads((ROOT/'verification'/'source_integrity_manifest.json').read_text())
EXPECTED={
 'strict':{'all':(227,27,7903),'other':(60,27,100),'dhs':(38,17,54)},
 'broad':{'all':(227,17,8266),'other':(60,17,244),'dhs':(38,10,141)}}

def status_matrix():
 with (ROOT/'data'/'omb_227_strict_status_matrix.csv').open(encoding='utf-8-sig',newline='') as f:
  return list(csv.DictReader(f))

def fingerprints(rows):
 return {label:hashlib.sha1(''.join(f"{r['ordinal_0based']},{r['agency']},{r['component']},{r[label]}\n" for r in rows).encode('utf8')).hexdigest() for label in ('strict_vector','broad_vector')}

def check_rows(rows):
 assert len(rows)==227
 assert sum(len(r['strict_vector']) for r in rows)==1816
 assert all(r['strict_vector']==''.join(r[f] for f in FIELDS) for r in rows)
 st=Counter(''.join(r['strict_vector'] for r in rows))
 assert st=={'U':812,'P':665,'E':267,'N':38,'L':4,'O':22,'M':3,'X':5}, st
 assert len({r['agency'] for r in rows})==12
 fp=fingerprints(rows)
 assert fp['strict_vector']==MAN['strict_vector_canonical_sha1'],fp
 assert fp['broad_vector']==MAN['broad_vector_canonical_sha1'],fp
 for mapping,k in [('strict','strict_vector'),('broad','broad_vector')]:
  for group,sub in [('all',rows),('other',[r for r in rows if r['agency'] not in ('VA','DOJ')]),('dhs',[r for r in rows if r['agency']=='DHS'])]:
   ss=summary(sub,k)
   observed=(ss['n'],ss['unique_profiles'],ss['identical_pairs'])
   assert observed==EXPECTED[mapping][group],(mapping,group,observed)
   assert sum(z['identical_pairs'] for z in pair_breakdown(sub,k).values())==ss['identical_pairs']
 return fp

def run(path=None):
 rows=status_matrix(); fp=check_rows(rows)
 result={'fixture_status':'PASS','rows':227,'strict_row_sha1':fp['strict_vector'],'broad_row_sha1':fp['broad_vector'], 'raw_status':'NOT_RUN'}
 if path:
  raw=Path(path).read_bytes(); actual_sha=hashlib.sha256(raw).hexdigest()
  blob_sha=hashlib.sha1((f'blob {len(raw)}\0').encode()+raw).hexdigest()
  assert len(raw)==MAN['original_byte_count'],len(raw)
  assert actual_sha==MAN['sha256_of_original_utf8_bytes'],actual_sha
  assert blob_sha==MAN['git_blob_sha1_official'],blob_sha
  orig,meta=read_official(path)
  assert meta['all_records']==MAN['original_csv_record_count'],meta
  assert len(orig)==227
  for a,b in zip(orig,rows):
   for key,v in [('row_ordinal','ordinal_0based'),('agency','agency'),('component','component'),('vector_strict','strict_vector'),('vector_proxy','broad_vector')]:
    assert str(a[key])==str(b[v]),(key,a[key],b[v])
  assert sum(not x['source_id'].strip() for x in orig)==10
  result.update({'raw_status':'PASS','raw_sha256':actual_sha,'git_blob_sha1':blob_sha,'original_rows':meta['all_records'],'fields':len(FIELDS)})
 else: result['raw_status']='NOT_RUN (requires --csv file; no claim of fresh raw rerun)'
 return result

if __name__=='__main__':
 p=argparse.ArgumentParser()
 p.add_argument('--csv',help='Pin-verified raw official CSV file; omit for derived-matrix checks only')
 p.add_argument('--output',default=None)
 args=p.parse_args()
 result=run(args.csv)
 print(json.dumps(result,indent=2))
 if args.output:Path(args.output).write_text(json.dumps(result,indent=2)+'\n')
