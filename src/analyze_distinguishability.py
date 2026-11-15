#!/usr/bin/env python3
"""Offline analysis of 227 fixed-snapshot OMB derived rows.

Unit: inventory reporting ROW. Metric: exact equality of the eight coded public status
responses, not equivalence of systems, safeguards, or implementation.
Pairwise probabilities use unordered distinct row pairs, without replacement.
Dependent pairs are descriptive; no independence-based inferential p-values.
"""
from __future__ import annotations
import csv, json, math
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT/'data'/'omb_227_strict_status_matrix.csv'
OUTPUT = ROOT/'results'
FIELDS = ["hi_testing_conducted", "hi_assessment_completed", "hi_independent_review",
          "hi_ongoing_monitoring", "hi_training_established", "hi_failsafe_presence",
          "hi_appeal_process", "hi_public_consultation"]


def load():
    with INPUT.open(newline='', encoding='utf-8-sig') as fp:
        rows=list(csv.DictReader(fp))
    assert len(rows)==227
    assert len({int(r['ordinal_0based']) for r in rows})==227
    assert len({r['agency'] for r in rows})==12
    for r in rows:
        a=r['strict_vector']; b=r['broad_vector']
        assert len(a)==len(b)==8
        assert a == ''.join(r[field] for field in FIELDS)
        assert set(a)<={'E','P','U','N','L','O','M','X'}
    status=Counter(''.join(r['strict_vector'] for r in rows))
    assert status=={'E':267,'P':665,'U':812,'N':38,'L':4,'O':22,'M':3,'X':5}
    assert Counter(r['agency'] for r in rows)['VA']==94
    assert Counter(r['agency'] for r in rows)['DOJ']==73
    return rows


def choose2(n):return n*(n-1)//2


def summary(rows, field):
    n=len(rows); counts=Counter(r[field] for r in rows)
    matches=sum(choose2(v) for v in counts.values()); pairs=choose2(n)
    h=-sum((v/n)*math.log2(v/n) for v in counts.values())
    return {
        'n': n,
        'unique_profiles':len(counts),
        'singleton_profiles':sum(1 for v in counts.values() if v==1),
        'singleton_rows':sum(v for v in counts.values() if v==1),
        'rows_in_repeated_profiles':sum(v for v in counts.values() if v>1),
        'rows_in_repeated_profiles_pct':100*sum(v for v in counts.values() if v>1)/n,
        'modal_profile':counts.most_common(1)[0][0],
        'modal_n':counts.most_common(1)[0][1],
        'modal_pct':100*counts.most_common(1)[0][1]/n,
        'pairs':pairs, 'identical_pairs':matches,
        'pair_collision_pct':100*matches/pairs if pairs else None,
        'shannon_entropy_bits':h,
        'effective_profiles_2_to_H':2**h,
    }


def pair_breakdown(rows,field):
    counts=defaultdict(lambda:[0,0])
    for a,b in combinations(rows,2):
        same_agency=a['agency']==b['agency']
        same_component=same_agency and a['component']==b['component']
        category= ('same_component' if same_component else
                    'different_component_same_agency' if same_agency else
                    'different_agency')
        counts[category][1]+=1
        counts[category][0]+=int(a[field]==b[field])
    out={}
    for name in ['same_component','different_component_same_agency','different_agency']:
        matches,pairs=counts[name]
        out[name]={'identical_pairs':matches,'total_pairs':pairs,
                   'pair_collision_pct':100*matches/pairs if pairs else None}
    assert sum(z['total_pairs'] for z in out.values())==choose2(len(rows))
    assert sum(z['identical_pairs'] for z in out.values())==summary(rows,field)['identical_pairs']
    return out


def write_csv(path,rows):
    assert rows
    with path.open('w',newline='',encoding='utf8') as fp:
        w=csv.DictWriter(fp, fieldnames=list(rows[0].keys()));w.writeheader();w.writerows(rows)


def main():
    OUTPUT.mkdir(exist_ok=True)
    rows=load(); agencies=sorted({r['agency'] for r in rows})
    groups={
      'all_227':rows,
      'excluding_VA_DOJ_60':[r for r in rows if r['agency'] not in {'VA','DOJ'}],
      'DHS_only_38':[r for r in rows if r['agency']=='DHS'],
      'excluding_VA_DOJ_NCUA_55':[r for r in rows if r['agency'] not in {'VA','DOJ','NCUA'}]
    }
    sizes={'all_227':227,'excluding_VA_DOJ_60':60,'DHS_only_38':38,'excluding_VA_DOJ_NCUA_55':55}
    assert {k:len(v) for k,v in groups.items()}==sizes
    result={'cohort':{'source':'V4 status-only derived OMB classification, pinned commit 3c225ba8438e48306ace7698c8c7feb9486cbc69',
                      'original_csv_bytes_reproduced_this_round':False,
                      'row_count':227,'field_count':8,'agency_count':12,
                      'unit':'reported inventory row, not independent physical AI deployment'},
            'coding':'strict preserves E,P,U,N,L,O,M,X; broad coarsens some distinct responses',
            'groups':{}}
    flat=[]; pairflat=[]
    for name, subset in groups.items():
        result['groups'][name]={}
        for fld in ['strict_vector','broad_vector']:
            s=summary(subset,fld); p=pair_breakdown(subset,fld)
            result['groups'][name][fld]={'metrics':s,'pair_breakdown':p}
            flat.append({'group':name,'coding':fld,**s})
            for pair_type, vals in p.items():
                pairflat.append({'group':name,'coding':fld,'pair_type':pair_type,**vals})
    counts=Counter(r['strict_vector'] for r in rows)
    assert counts['UUUUUUUU']==101 and counts['PPPPPPPP']==75
    assert result['groups']['all_227']['strict_vector']['metrics']['unique_profiles']==27
    assert result['groups']['excluding_VA_DOJ_60']['strict_vector']['metrics']['unique_profiles']==27
    assert result['groups']['all_227']['strict_vector']['metrics']['identical_pairs']==7903
    assert result['groups']['excluding_VA_DOJ_60']['strict_vector']['metrics']['identical_pairs']==100
    assert result['groups']['all_227']['strict_vector']['metrics']['rows_in_repeated_profiles']==211
    # All 94 VA and 73 DOJ records have all-field uniform profiles: 4,371+2,628 matching pairs.
    dominant_pairs=choose2(94)+choose2(73)
    result['dominant_agency_decomposition']={
      'VA_within_agency_identical_pairs':choose2(94),
      'DOJ_within_agency_identical_pairs':choose2(73),
      'combined_identical_pairs':dominant_pairs,
      'share_of_all_7903_identical_pairs_pct':100*dominant_pairs/7903,
      'share_of_same_agency_identical_pairs_pct':100*dominant_pairs/7068
    }
    agency_rows=[]
    for agency in sorted(agencies,key=lambda x: (-sum(r['agency']==x for r in rows),x)):
        subset=[r for r in rows if r['agency']==agency]
        s=summary(subset,'strict_vector'); b=summary(subset,'broad_vector')
        agency_rows.append({'agency':agency,'reported_rows':len(subset),'strict_unique_patterns':s['unique_profiles'],
           'strict_modal_pattern':s['modal_profile'],'strict_modal_count':s['modal_n'],
           'strict_modal_pct':round(s['modal_pct'],4),
           'strict_matching_pairs':s['identical_pairs'],'within_agency_pairs':s['pairs'],
           'strict_pair_collision_pct':round(s['pair_collision_pct'],4) if s['pair_collision_pct'] is not None else '',
           'strict_entropy_bits':round(s['shannon_entropy_bits'],5),
           'broad_unique_patterns':b['unique_profiles'],
           'broad_pair_collision_pct':round(b['pair_collision_pct'],4) if b['pair_collision_pct'] is not None else ''})
    profile_rows=[]
    for fld in ['strict_vector','broad_vector']:
        c=Counter(r[fld] for r in rows)
        for k,n in c.most_common():
            members=sorted({r['agency'] for r in rows if r[fld]==k})
            profile_rows.append({'coding':fld,'profile':k,'n':n,'pct_of_227':round(n/227*100,4),
              'number_of_agencies':len(members), 'agencies':'|'.join(members)})
    # Cross-check analytic count identity with direct enumeration, separately from pair_breakdown.
    for name,subset in groups.items():
      for fld in ['strict_vector','broad_vector']:
        brute=sum(1 for x,y in combinations(subset,2) if x[fld]==y[fld])
        assert brute==result['groups'][name][fld]['metrics']['identical_pairs']
    write_csv(OUTPUT/'sensitivity_summary.csv',flat)
    write_csv(OUTPUT/'pair_breakdown.csv',pairflat)
    write_csv(OUTPUT/'agency_distinguishability.csv',agency_rows)
    write_csv(OUTPUT/'profile_frequencies.csv',profile_rows)
    with (OUTPUT/'full_results.json').open('w',encoding='utf8') as fp:json.dump(result,fp,ensure_ascii=False,indent=2)
    for key in ('all_227','excluding_VA_DOJ_60','DHS_only_38'):
      ss=result['groups'][key]['strict_vector']
      print(key,ss['metrics']['n'],'unique',ss['metrics']['unique_profiles'],
        'pair collision',round(ss['metrics']['pair_collision_pct'],4),
        'same component',ss['pair_breakdown']['same_component'],
        'diff comp same agency',ss['pair_breakdown']['different_component_same_agency'],
        'cross agency',ss['pair_breakdown']['different_agency'])
    print('SUCCESS: 227 rows, 12 agencies, profiles and pair metrics verified')

if __name__=='__main__':main()
