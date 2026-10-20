"""Fast non-circular archive acceptance checks for inferred-site scenarios."""
import unittest
from pathlib import Path
import pandas as pd
import geopandas as gpd
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs/osm_inference'
QA=ROOT/'data/qa/osm_inference'

class TestV06OSMAddressInference(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.register=pd.read_csv(ROOT/'data/curated/official_facility_registry_89_address_audited.csv',encoding='utf-8-sig')
        cls.candidates=pd.read_csv(OUT/'six_facility_plausible_osm_network_nodes.csv',encoding='utf-8-sig')
        cls.coverage=pd.read_csv(OUT/'street_network_coverage_missing_site_scenarios.csv')
        cls.policy=pd.read_csv(OUT/'inferred_89_policy_regret_5_scenarios_240m.csv')
    def test_source_universe(self):
        self.assertEqual(len(self.register),89)
        self.assertEqual(int(self.register.inherited_spatial_point_present.sum()),83)
        self.assertEqual(set(self.register.loc[~self.register.inherited_spatial_point_present,'facility_name']),
                         set(self.candidates.facility_name))
    def test_candidate_provenance(self):
        self.assertEqual(len(self.candidates),83)
        self.assertFalse(self.candidates.address_matched_in_OSM.any())
        self.assertFalse(self.candidates.site_entrance_verified.any())
        self.assertFalse(self.candidates.primary_analysis_approved.any())
        self.assertTrue(self.candidates.scenario_only.all())
        self.assertFalse(self.candidates[['facility_name','osm_network_node_id']].duplicated().any())
        g=gpd.read_file(ROOT/'data/processed/p06_refined_clean.gpkg',layer='study_subdistricts')
        for street,points in self.candidates.groupby('declared_subdistrict'):
            poly=g.loc[g.subdistrict_name==street,'geometry'].iloc[0]
            self.assertTrue(all(poly.buffer(1).covers(p) for p in gpd.points_from_xy(points.x_utm51n,points.y_utm51n)))
    def test_coverage_monotonic_scenarios(self):
        t=self.coverage
        b=t.loc[t.facility_universe=='inherited_83'].set_index(['service','subdistrict','threshold_min'])
        q=t.loc[t.facility_universe=='inferred_89_sensitivity']
        self.assertEqual(q.scenario.nunique(),15)
        self.assertEqual(len(q),15*2*12*3)
        for z in q.itertuples():
            self.assertGreaterEqual(z.network_coverage_share+1e-9,float(b.loc[(z.service,z.subdistrict,z.threshold_min),'network_coverage_share']))
            self.assertTrue(-1e-8<=z.network_coverage_share<=1+1e-8)
    def test_policy_records_and_nonnegative_regret(self):
        p=self.policy
        self.assertEqual(len(p),5*3*3*3*2)
        self.assertEqual(p.site_scenario.nunique(),5)
        self.assertTrue((p.street_choice_regret>=-1e-6).all())
        self.assertTrue((p.total_expected_regret>=-1e-6).all())
        self.assertTrue((p.relative_street_choice_regret.between(-1e-6,1+1e-6)).all())
    def test_no_planning_certification(self):
        p=pd.read_csv(OUT/'candidate_osm_landuse_context_planning_pending.csv')
        self.assertEqual(len(p),1132)
        self.assertEqual(p.candidate_node.nunique(),1132)
        self.assertTrue((p.approved_legal_buildability=='unverified').all())
        self.assertTrue(p.OSM_is_not_planning_permission.all())
        x=pd.read_csv(OUT/'top_planning_verification_candidates_240m.csv')
        self.assertEqual(len(x),40)
        self.assertFalse(x.site_is_certified_buildable.any())
    def test_legacy_base_network_exact_validation(self):
        x=__import__('json').loads((QA/'v06_policy_inferred_89_scenario_qa.json').read_text())
        self.assertEqual(x['observed_network_baseline_validation'],'PASS_exact_v04_83')

if __name__=='__main__':unittest.main()
