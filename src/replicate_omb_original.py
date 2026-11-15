#!/usr/bin/env python3
"""Audit-grade OMB CSV parser and 8-field disclosure-profile comparison.

Python stdlib only. No LLM-based classification. Input must be the official
fixed-commit CSV; absent that file, --fixture can verify the narrow archived
row-level profile computations but CANNOT reproduce original raw-field parsing.
"""
import argparse, ast, csv, hashlib, json, math
from collections import Counter, defaultdict
from pathlib import Path

COMMIT = '3c225ba8438e48306ace7698c8c7feb9486cbc69'
URL = ('https://raw.githubusercontent.com/ombegov/2025-Federal-Agency-AI-Use-Case-Inventory/'
       + COMMIT + '/Data/2025_individually_reported_AI_use_cases.csv')
FIELDS = ['hi_testing_conducted','hi_assessment_completed','hi_independent_review',
          'hi_ongoing_monitoring','hi_training_established','hi_failsafe_presence',
          'hi_appeal_process','hi_public_consultation']

# The broad profile proxy is reproduced separately because a syntactically
# affirmative 'Other' does not prove a substantive control was implemented.
def broad_category(value):
    x=(value or '').strip()
    if x in ('', '[]'):return 'U'
    if 'Not Applicable' in x or 'Precluded by Law' in x:return 'N'
    if 'in-progress' in x.lower() or 'in-progess' in x.lower():return 'P'
    if (x.startswith(('Yes','CAIO Review','Internal Independent Review','Oversight Board Review',
                      'Training Established','Appeal Process Established',"['"))):return 'E'
    return 'X'

def classify_strict(field, value):
    """Recognize question-appropriate published response; reject column swaps.

    Codes: U unstated, P in progress, E claimed established/completed,
    N inapplicable, L legal preclusion, O unelaborated Other,
    W CAIO waiver, X unexpected / wrong-question response.
    These codes describe PUBLIC TEXT only, never ground truth safeguards.
    """
    t=(value or '').strip()
    if t=='' or t=='[]':return 'U'
    if field=='hi_public_consultation':
        try:
            xs=ast.literal_eval(t)
            if not isinstance(xs,list) or not all(isinstance(x,str) for x in xs):return 'X'
        except (SyntaxError,ValueError):return 'X'
        # A multiselect with mixed states is not collapsed into one status.
        allowed={'Other':'O','Usability Testing':'E','Public Feedback Solicitations':'E',
                 'Public Hearings':'E','In-progress':'P','CAIO Waived':'W',
                 'a) Direct usability testing':'E',
                 'b) General solicitations of feedback and comments from the public':'E',
                 'c) Public hearings or meetings':'E', 'd) Other':'O',
                 'e) In-progress':'P'}
        states={allowed.get(x,'X') for x in xs}
        if 'X' in states:return 'X'
        if not states:return 'U'
        if len(states)>1:
            return 'M'  # multiple selections; preserve for item-level audit
        return next(iter(states))
    if field=='hi_training_established':
        return {'Training Established':'E','Training In-progress':'P','CAIO Waived':'W'}.get(t,'X')
    if field=='hi_appeal_process':
        return {'Appeal Process Established':'E','Appeal Process In-progress':'P',
                'Not Applicable':'N','Appeal Precluded by Law':'L','CAIO Waived':'W'}.get(t,'X')
    if field=='hi_independent_review':
        return {'CAIO Review':'E','Internal Independent Review':'E',
                'Oversight Board Review':'E','In-progress':'P','CAIO Waived':'W'}.get(t,'X')
    if field=='hi_ongoing_monitoring':
        return {'Yes - Monitoring Established':'E','In-progress':'P','CAIO Waived':'W'}.get(t,'X')
    if field=='hi_failsafe_presence':
        return {'Yes':'E','In-progress':'P','Not Applicable':'N','CAIO Waived':'W'}.get(t,'X')
    if field in ('hi_testing_conducted','hi_assessment_completed'):
        return {'Yes':'E','In-progress':'P','CAIO Waived':'W'}.get(t,'X')
    raise KeyError(field)

def read_official(path):
    raw=Path(path).read_bytes()
    digest=hashlib.sha256(raw).hexdigest()
    with Path(path).open('r',encoding='utf-8-sig',newline='') as f:
        allrows=list(csv.DictReader(f))
    need=['agency','id','agency_bureau','development_stage','is_high_impact']+FIELDS
    if not allrows or any(c not in allrows[0] for c in need):
        raise ValueError('Unexpected CSV header; refusing silent column guesses')
    selected=[]
    for i,row in enumerate(allrows):
        if row['development_stage']=='Deployed' and row['is_high_impact']=='High-impact':
            selected.append({
                'row_ordinal':i,'agency':row['agency'],'component':row['agency_bureau'].strip(),
                'source_id':row['id'],'name':row['use_case_name'],
                'topic':row['topic_area'],'contracting':row['contracting_usage'],
                'pii':row['has_pii'],'ato':row['have_ato'],'vendor':row['vendor_name'],
                'vector_proxy':''.join(broad_category(row[f]) for f in FIELDS),
                'vector_strict':''.join(classify_strict(f,row[f]) for f in FIELDS),
                'source_fields':{f:row[f] for f in FIELDS}
            })
    return selected, {'all_records':len(allrows),'csv_sha256':digest,'bytes':len(raw),
                      'source':URL,'selection':'is_high_impact == High-impact AND development_stage == Deployed'}

def fixture_rows(path):
    obj=json.loads(Path(path).read_text(encoding='utf8'))
    return [{'agency':r['agency'],'component':r['component'],'vector_proxy':r['vector_proxy'],
             'row_ordinal':r['csv_data_row_0based']} for r in obj['rows']]

def compare_pairs(records,vector='vector_proxy'):
    result={k:{'pairs':0,'exact':0,'sum_hamming':0} for k in ('within_component','same_agency_other_component','cross_agency')}
    for i,a in enumerate(records):
        for b in records[i+1:]:
            if a['agency']==b['agency'] and a['component']==b['component']:
                key='within_component'
            elif a['agency']==b['agency']:
                key='same_agency_other_component'
            else:key='cross_agency'
            x=result[key];v=a[vector];w=b[vector]
            x['pairs']+=1;x['exact']+=int(v==w)
            x['sum_hamming']+=sum(c!=d for c,d in zip(v,w))
    for v in result.values():
        v['rate']=v['exact']/v['pairs'] if v['pairs'] else None
        v['mean_hamming']=v['sum_hamming']/v['pairs'] if v['pairs'] else None
    w=result['within_component'];c=result['same_agency_other_component'];d=result['cross_agency']
    other={'pairs':c['pairs']+d['pairs'],'exact':c['exact']+d['exact']}
    other['rate']=other['exact']/other['pairs'] if other['pairs'] else None
    return {'within_component':w,'same_agency_other_component':c,'cross_agency':d,
            'all_other_components':other,'within_vs_other_ratio':w['rate']/other['rate'] if w['rate'] and other['rate'] else None}

def report(records,provenance, include_strict=False):
    no_va=[x for x in records if x['agency'] not in ('VA','DOJ')]
    dhs=[x for x in records if x['agency']=='DHS']
    out={'provenance':provenance,'population':{'n':len(records),
          'agency_counts':dict(sorted(Counter(x['agency'] for x in records).items())),
          'components':len({(x['agency'],x['component']) for x in records}),
          'proxy_vector_counts':dict(Counter(x['vector_proxy'] for x in records))},
          'broad_proxy':{'full':compare_pairs(records),'no_VA_DOJ':compare_pairs(no_va),
                         'DHS_only':compare_pairs(dhs)}}
    if include_strict:
        anomalies=[{'row_ordinal':x['row_ordinal'],'source_id':x['source_id'],
                    'agency':x['agency'],'field':f,'raw':x['source_fields'][f],
                    'strict_category':cat} for x in records
                    for f,cat in zip(FIELDS,x['vector_strict']) if cat=='X']
        blanks=[{'row_ordinal':x['row_ordinal'],'agency':x['agency'],
                 'component':x['component'],'name':x['name']} for x in records if not x['source_id'].strip()]
        out['strict']={'vector_counts':dict(Counter(x['vector_strict'] for x in records)),
             'full':compare_pairs(records,'vector_strict'),
             'no_VA_DOJ':compare_pairs(no_va,'vector_strict'),
             'DHS_only':compare_pairs(dhs,'vector_strict'),
             'invalid_field_values':anomalies,'missing_source_ids':blanks}
    return out

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    q=ap.add_mutually_exclusive_group(required=True)
    q.add_argument('--csv',help='Original pinned official OMB CSV downloaded separately')
    q.add_argument('--fixture',help='Offline 227-row broad-profile fixture (not a raw CSV rerun)')
    ap.add_argument('--output',default='reproduction_results.json')
    args=ap.parse_args()
    if args.csv: rows,prov=read_official(args.csv); strict=True
    else:rows=fixture_rows(args.fixture);prov={'input':'offline broad-category fixture; NOT full original CSV'};strict=False
    results=report(rows,prov,include_strict=strict)
    if len(rows)!=227:raise AssertionError(f'Selected {len(rows)} records; expected 227. Stop for reconciliation.')
    Path(args.output).write_text(json.dumps(results,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
    print('Wrote',args.output,'n=',len(rows),'within=',results['broad_proxy']['full']['within_component']['exact'],
          '/',results['broad_proxy']['full']['within_component']['pairs'])
if __name__=='__main__':main()
