"""Validate refined spatial data, network calculations and allocation results."""
import sys,json,unittest
from pathlib import Path
import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point,LineString,Polygon
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
import importlib.util
spec=importlib.util.spec_from_file_location('network_refine',ROOT/'src/06_exact_network_refinement.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
B=ROOT/'outputs/refined_model'

class TestRefinedQA(unittest.TestCase):
 def test_clean_geometry_layers_unique(self):
  path=ROOT/'data/processed/p06_refined_clean.gpkg'
  layers={r['name'] for _,r in gpd.list_layers(path).iterrows()}
  self.assertEqual(layers,{'osm_node_identity_edges','study_subdistricts','facility_inherited_coordinates','hypothetical_candidate_nodes_240m'})
  self.assertEqual(len(gpd.read_file(path,layer='study_subdistricts')),12)
  self.assertEqual(len(gpd.read_file(path,layer='facility_inherited_coordinates')),83)
  self.assertEqual(len(gpd.read_file(path,layer='hypothetical_candidate_nodes_240m')),1132)
 def test_facility_access_edge_midpoint_exact(self):
  edge=gpd.GeoDataFrame({'u_index':[0],'v_index':[1],'u_id':[10],'v_id':[11],'length_m':[1000.],'zone':[0],
    'osm_way_id':[1],'highway':['residential'],'bridge':[''],'tunnel':[''],'layer':['']},
    geometry=[LineString([(0,0),(1000,0)])])
  poly=gpd.GeoDataFrame({'subdistrict_name':['A']},geometry=[Polygon([(-5,-5),(1005,-5),(1005,5),(-5,5)])])
  snaps=pd.DataFrame([{'edge_index':0,'projected_fraction':.5,'snap_distance_m':0}])
  mat,arr,site,qa=module.construct_refined_graph(edge,poly,snaps)
  measured=module.measure(module.source_distance(mat,[site[0]]),arr)
  self.assertAlmostEqual(float(measured[0,0]),720.,places=5)
  self.assertAlmostEqual(float(measured[1,0]),1000.,places=5)
 def test_border_splitting_exact(self):
  edge=gpd.GeoDataFrame({'u_index':[0],'v_index':[1],'u_id':[10],'v_id':[11],'length_m':[1000.],'zone':[0],
    'osm_way_id':[1],'highway':['residential'],'bridge':[''],'tunnel':[''],'layer':['']},
    geometry=[LineString([(0,0),(1000,0)])])
  bounds=gpd.GeoDataFrame({'subdistrict_name':['A','B']},geometry=[Polygon([(-10,-10),(500,-10),(500,10),(-10,10)]),
    Polygon([(500,-10),(1010,-10),(1010,10),(500,10)])])
  mat,arr,_,qa=module.construct_refined_graph(edge,bounds,pd.DataFrame(columns=['edge_index','projected_fraction','snap_distance_m']))
  l=np.bincount(arr[3],weights=arr[2]*arr[4],minlength=2)
  self.assertTrue(np.allclose(l,[500.,500.],atol=.00001))
  result=module.measure(module.source_distance(mat,[0]),arr)
  self.assertTrue(np.allclose(result[0,:2],[360.,0.],atol=.00001))
 def test_refined_outputs_all_grids(self):
  for grid in (180,240,320):
   d=B/f'grid_{grid}m'
   cand=pd.read_csv(d/'hypothetical_candidate_nodes_validated.csv')
   self.assertTrue(cand.candidate_node.is_unique)
   self.assertEqual(set(cand.zone.unique()),set(range(12)))
   cov=pd.read_csv(d/'observed_accessibility.csv')
   self.assertEqual(len(cov),108)
   self.assertTrue(cov.network_coverage_share.between(0,1).all())
   for _,x in cov.groupby(['service','subdistrict']):
    self.assertTrue((x.sort_values('threshold_min').network_coverage_share.diff().fillna(0)>=-1e-7).all())
   dec=pd.read_csv(d/'policy_regret_tie_aware.csv')
   self.assertEqual(len(dec),27)
   self.assertTrue(np.allclose(dec.total_regret_m,dec.street_choice_regret_m+dec.within_street_siting_regret_m,atol=1e-6))
   self.assertTrue(dec.regret_fraction.between(0,1).all())
   for _,r in dec.iterrows():
    self.assertAlmostEqual(float(r.total_regret_m/r.oracle_gain_m),float(r.regret_fraction),places=8)
   qa=json.loads((d/'refinement_qa.json').read_text())
   self.assertEqual(qa['facility_sources'],83)
   self.assertFalse(qa['topology_audit_cross_connected'])
   self.assertTrue(qa['no_site_cutoff'])
 def test_ambiguous_intersection_scenario(self):
  a=json.loads((B/'grid_320m_atgrade_connected/refinement_qa.json').read_text())
  b=json.loads((B/'grid_320m/refinement_qa.json').read_text())
  self.assertTrue(a['topology_audit_cross_connected'])
  self.assertFalse(b['topology_audit_cross_connected'])
 def test_population_exclusions_persist(self):
  missing=pd.read_csv(ROOT/'data/qa/six_facilities_evidence_and_exclusion.csv')
  self.assertEqual(len(missing),6)
  self.assertEqual(missing.facility_type.value_counts().to_dict(),{'elderly_care':4,'culture':2})
  ranks=pd.read_csv(B/'grid_240m/policy_regret_tie_aware.csv')
  self.assertTrue(ranks[ranks.service=='culture'].selection_tie_count.eq(2).all())
 def test_objective_is_not_the_same_across_scenarios(self):
  d=pd.read_csv(B/'objective_street_comparison.csv')
  self.assertEqual(len(d),81)
  self.assertTrue(d[d.grid_m==240].oracle_street_changed.any())

if __name__=='__main__':unittest.main()

# Additional numerical sensitivity asserted separately so the one disputed road
# crossing is not silently treated as resolved in the source OSM data.
class TestRefinedTopologyStability(unittest.TestCase):
 def test_main_grid_atgrade_regret_sensitivity(self):
  x=pd.read_csv(B/'atgrade_sensitivity_main_and_coarse.csv')
  d=x[x.grid_m==240]
  self.assertEqual(len(d),27)
  self.assertFalse(d.oracle_street_changed.any())
  self.assertLess(d.regret_difference_connected_minus_baseline.abs().max(),.002)
