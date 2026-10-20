import unittest,sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from pbf_reader import varint,zig,packed,delta
import pandas as pd,numpy as np

class TestData(unittest.TestCase):
 def test_parser_varints_and_delta(self):
  self.assertEqual(varint(b'\xac\x02',0),(300,2))
  self.assertEqual(zig(1),-1);self.assertEqual(zig(2),1)
  self.assertEqual(list(delta([1,-2,10])),[1,-1,9])
 def test_excluded_six_and_source_universe(self):
  p=ROOT/'data/qa/six_facilities_evidence_and_exclusion.csv'
  e=pd.read_csv(p);self.assertEqual(len(e),6);self.assertEqual(e.facility_name.nunique(),6)
  s=pd.read_csv(ROOT/'outputs/tables/supply_verified.csv');self.assertEqual(int(s.count_verified.sum()),83)
 def test_monotonic_accessibility(self):
  c=pd.read_csv(ROOT/'outputs/tables/observed_accessibility.csv')
  self.assertEqual(len(c),108)
  self.assertTrue(c.network_coverage_share.between(0,1).all())
  for _,g in c.groupby(['service','subdistrict']):
   self.assertTrue((g.sort_values('threshold_min').network_coverage_share.diff().fillna(0)>=-1e-9).all())
 def test_policy_regret_nonnegative(self):
  d=pd.read_csv(ROOT/'outputs/tables/decision_regret.csv')
  self.assertEqual(len(d),27);self.assertTrue((d.decision_regret_m>=-1e-9).all())
  self.assertTrue((d.regret_fraction>=0).all());self.assertTrue((d.regret_fraction<=1).all())
 def test_no_base_60m_cutoff(self):
  s=pd.read_csv(ROOT/'data/qa/facility_connector_distances_full.csv')
  self.assertEqual(len(s),83)
  self.assertGreater((s.snap_distance_m>60).sum(),0)
  self.assertEqual(s.snap_distance_m.isna().sum(),0)
 def test_atgrade_exception_documented(self):
  a=pd.read_csv(ROOT/'data/qa/at_grade_crossing_manual_review.csv')
  self.assertEqual(len(a),1)
  self.assertTrue((a.connection_in_primary_graph==False).all())
 def test_candidate_sensitivity_results(self):
  for m in (180,320):
   d=pd.read_csv(ROOT/f'outputs/sensitivity/grid_{m}m/decision_regret.csv')
   self.assertEqual(len(d),27)

if __name__=='__main__':unittest.main()
