"""Non-negotiable statutory planning evidence gates; no invented parcel matching."""
from pathlib import Path
import json
import unittest
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]

class TestPlanningParcelAudit(unittest.TestCase):
    def test_all_candidates_remain_unverified(self):
        d=pd.read_csv(ROOT/'data/qa/planning/all1132_parcel_readiness.csv')
        self.assertEqual(len(d),1132)
        self.assertEqual(d.candidate_node.nunique(),1132)
        self.assertEqual(set(d.official_parcel_match_status),{'UNMATCHED'})
        self.assertEqual(set(d.legal_site_eligible),{'UNKNOWN'})
        self.assertEqual(d.official_parcel_record_id.notna().sum(),0)

    def test_manual_priority_and_provenance(self):
        d=pd.read_csv(ROOT/'data/qa/planning/priority40_official_parcel_matching_audit.csv')
        self.assertEqual(len(d),40)
        self.assertEqual(d.candidate_id.nunique(),40)
        self.assertTrue(d.latitude_wgs84.between(30,32).all())
        self.assertTrue(d.longitude_wgs84.between(120,123).all())
        self.assertEqual(d.official_parcel_use_verified.sum(),0)
        self.assertEqual(d.official_parcel_dynamic_verified.sum(),0)

    def test_context_only_exclusion_stress(self):
        summary=json.loads((ROOT/'data/qa/planning/v07_parcel_audit_summary.json').read_text())
        d=pd.read_csv(ROOT/'outputs/planning_audit/osm_context_screen_45_optima_comparison.csv')
        self.assertEqual(summary['candidate_excluded_osm_context_stress'],62)
        self.assertEqual(len(d),45)
        self.assertFalse(d.site_choice_changed.any())
        self.assertTrue((d.network_gain_difference_m.abs()<1e-8).all())

if __name__=='__main__': unittest.main()
