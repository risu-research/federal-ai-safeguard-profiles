#!/usr/bin/env python3
"""Unit test coding edge cases, structural matrix, observed recodes, and pair counts."""
import sys,unittest,csv,collections
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from replicate_omb_original import classify_strict,broad_category
from audit_reproduction import run

class ReproductionTests(unittest.TestCase):
 def test_coding(self):
  samples=[('hi_appeal_process','Appeal Precluded by Law','L','N'),
    ('hi_appeal_process','Not Applicable','N','N'),
    ('hi_public_consultation',"['Other']",'O','E'),
    ('hi_public_consultation',"['In-progress']",'P','P'),
    ('hi_public_consultation',"['Other', 'Usability Testing']",'M','E'),
    ('hi_public_consultation','[]','U','U'),
    ('hi_training_established','Training In-progress','P','P'),
    ('hi_testing_conducted','Yes','E','E'),
    ('hi_training_established','In-progress','X','P'),
    ('hi_training_established','CAIO Waived','W','X'),
   ]
  for f,t,s,b in samples:
   with self.subTest(field=f,raw=t):
    self.assertEqual(classify_strict(f,t),s)
    self.assertEqual(broad_category(t),b)
 def test_entire_matrix(self):
  self.assertEqual(run()['fixture_status'],'PASS')
 def test_changed_cells(self):
  with (ROOT/'codebook'/'OBSERVED_STRICT_TO_BROAD_CHANGES.csv').open(encoding='utf-8-sig',newline='') as fp: changes=list(csv.DictReader(fp))
  self.assertEqual(len(changes),33)
  self.assertEqual(collections.Counter((x['strict'],x['broad']) for x in changes),{('O','E'):22,('M','E'):3,('L','N'):4,('X','P'):3,('X','E'):1})

if __name__=='__main__':unittest.main(verbosity=2)
