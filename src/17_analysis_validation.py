#!/usr/bin/env python3
"""Check facility records, network attributes and derived analysis results."""
from pathlib import Path
import json, math
import numpy as np
import pandas as pd
import geopandas as gpd
ROOT=Path(__file__).resolve().parents[1]
DEST=ROOT/'outputs/validation';DEST.mkdir(parents=True,exist_ok=True)
R=ROOT/'data/curated/official_facility_registry_89_address_audited.csv'
reg=pd.read_csv(R,encoding='utf-8-sig')
assert len(reg)==89
assert len(reg[['facility_type','facility_name']].drop_duplicates())==89
assert set(reg.facility_type)=={'healthcare','elderly_care','culture'}
assert reg.inherited_spatial_point_present.sum()==83
assert (reg.loc[reg.inherited_spatial_point_present,['wgs84_lon','wgs84_lat']].notna().all(axis=1)).all()
assert reg.loc[~reg.inherited_spatial_point_present,['wgs84_lon','wgs84_lat']].isna().all(axis=1).all()
reg['official_url_record_level']=reg.address_primary_url.fillna('').str.startswith('https://')
reg['coordinate_independently_verified']=False # Model validation does not alter coordinate verification status.
reg['missing_spatial_point']=~reg.inherited_spatial_point_present
reg['coordinate_shared_with_other_in_same_service']=reg.duplicated(['facility_type','wgs84_lon','wgs84_lat'],keep=False) & reg.inherited_spatial_point_present
reg['record_review_priority']=np.select([reg.missing_spatial_point,reg.coordinate_shared_with_other_in_same_service],["P0_missing_coordinate","P1_shared_coordinate"],default="P1_inherited_unverified")
reg[['facility_id','facility_type','facility_name','subdistrict_name','original_source_address','canonical_address','official_url_record_level','inherited_spatial_point_present','coordinate_independently_verified','coordinate_shared_with_other_in_same_service','record_review_priority']].to_csv(DEST/'facility_record_evidence_gate.csv',index=False,encoding='utf-8-sig')
# Summarise source network access attributes separately from field verification.
spatial=ROOT/'data/processed/p06_refined_clean.gpkg'
net=gpd.read_file(spatial,layer='osm_node_identity_edges',ignore_geometry=True)
assert len(net)==106698
required={'highway','length_m','zone','bridge','tunnel','layer'}
assert required.issubset(net.columns),net.columns.tolist()
study=net.loc[net.zone>=0].copy()
study['highway']=study.highway.fillna('').astype(str)
study['observed_access_evidence']=study.highway.isin(['footway','pedestrian','path','steps','living_street'])
study['higher_order_vehicle_road']=study.highway.isin(['primary','primary_link','secondary','secondary_link','tertiary','tertiary_link'])
study['motorised_or_ambiguous']=study.highway.isin(['residential','service','unclassified','track','road','cycleway']) | study.higher_order_vehicle_road
road=study.groupby('highway').agg(edge_count=('highway','size'),edge_length_m=('length_m','sum')).reset_index()
road['share_in_midpoint_district_length']=road.edge_length_m/road.edge_length_m.sum()
road['default_routing_status']='included_by_v0_7_whitelist'
road['independent_pedestrian_permission_verified']=False
road.sort_values('edge_length_m',ascending=False).to_csv(DEST/'network_highway_access_evidence_audit.csv',index=False)
# Keep official supply counts separate from the geocoded subset used in spatial analysis.
supply=pd.read_csv(ROOT/'outputs/address_restoration/full_official_supply_240m_with_partial_accessibility.csv')
assert len(supply)==36 and supply.count_full_official.sum()==89 and supply.count_spatial_inherited_83.sum()==83
assert (supply.count_full_official-supply.count_spatial_inherited_83==supply.missing_points_by_subdistrict).all()
policy=pd.read_csv(ROOT/'outputs/osm_inference/inferred_89_policy_regret_5_scenarios_240m.csv')
gains=pd.read_csv(ROOT/'outputs/osm_inference/inferred_89_candidate_gains_5_scenarios_240m.csv')
assert len(policy)==270
assert len(gains)==5*1132*3*3
# Recompute expectations and regret measures from the complete candidate results.
proxies=['facilities_per_10k','facilities_per_km2','facilities_per_100km_network']
rows=[];errors=[]
for item in policy.itertuples(index=False):
 g=gains.query('site_scenario == @item.site_scenario and service == @item.service and threshold_min == @item.threshold_min')
 assert len(g)==1132
 ss=supply[supply.service==item.service]
 mn=ss[item.proxy].min()
 chosen=set(ss.loc[np.isclose(ss[item.proxy],mn,rtol=1e-10,atol=1e-12),'subdistrict'])
 chosen_stored=set(item.selected_streets.split('|'))
 assert chosen==chosen_stored,(chosen,chosen_stored)
 bystreet=g.groupby('subdistrict')[item.objective].agg(['mean','max'])
 assert len(bystreet)==12
 calc_oracle=g[item.objective].max()
 calc_best=bystreet.loc[list(chosen),'max'].mean()
 calc_mean=bystreet.loc[list(chosen),'mean'].mean()
 assert np.isclose(calc_oracle,item.oracle_gain,rtol=1e-7,atol=1e-5)
 assert np.isclose(calc_best,item.selected_street_best_gain,rtol=1e-7,atol=1e-5)
 assert np.isclose(calc_mean,item.selected_street_mean_gain,rtol=1e-7,atol=1e-5)
 assert np.isclose(calc_oracle-calc_best,item.street_choice_regret,rtol=1e-7,atol=1e-5)
 assert np.isclose(calc_best-calc_mean,item.within_street_expected_regret,rtol=1e-7,atol=1e-5)
 assert calc_oracle>=calc_best-1e-5>=calc_mean-1e-5
 rows.append(dict(scenario=item.site_scenario,service=item.service,threshold_min=item.threshold_min,objective=item.objective,proxy=item.proxy,selected_streets='|'.join(sorted(chosen)),selected_street_count=len(chosen),street_regret_fraction=(calc_oracle-calc_best)/calc_oracle if calc_oracle else np.nan,within_street_regret_fraction=(calc_best-calc_mean)/calc_oracle if calc_oracle else np.nan,total_regret_fraction=(calc_oracle-calc_mean)/calc_oracle if calc_oracle else np.nan,beats_random_street_stage=bool(calc_best>bystreet['max'].mean()),beats_random_street_full=bool(calc_mean>bystreet['mean'].mean())))
recalced=pd.DataFrame(rows)
recalced.to_csv(DEST/'official_89_scenario_policy_independent_recalculation.csv',index=False)
# Compare whether the three supply measures select different priority subdistricts.
comp=recalced.pivot_table(index=['scenario','service','threshold_min','objective'],columns='proxy',values='selected_streets',aggfunc='first').reset_index()
comp['distinct_proxy_street_sets']=comp[proxies].nunique(axis=1)
comp['proxies_disagree']=comp.distinct_proxy_street_sets>1
comp.to_csv(DEST/'proxy_decision_divergence_by_scenario.csv',index=False)
# Summarise the range across the five deterministic location scenarios.
summary=recalced.groupby(['service','threshold_min','objective','proxy'],as_index=False).agg(scenario_min_street_regret=('street_regret_fraction','min'),scenario_max_street_regret=('street_regret_fraction','max'),scenario_min_total_regret=('total_regret_fraction','min'),scenario_max_total_regret=('total_regret_fraction','max'),scenario_count=('scenario','nunique'))
summary.to_csv(DEST/'five_scenario_regret_ranges_not_confidence_intervals.csv',index=False)
# The service-threshold-proxy combinations share underlying spatial inputs.
# OSM land-use classification and planning permission are separate concepts.
planning=pd.read_csv(ROOT/'data/qa/planning/all1132_parcel_readiness.csv')
assert len(planning)==1132
print('PLANNING_COLUMNS',planning.columns.tolist())
# Store a machine-readable summary of the validation checks.
record_level_sources=int(reg.official_url_record_level.sum())
road_suspect_share=float(study.loc[study.motorised_or_ambiguous,'length_m'].sum()/study.length_m.sum())
road_higher_share=float(study.loc[study.higher_order_vehicle_road,'length_m'].sum()/study.length_m.sum())
qa={'research_data':'2026-10-16_v0.7_frozen_inputs','official_facilities':89,'inherited_coords':83,'missing_coords':6,'independently_verified_current_entrances':0,'facility_same_service_shared_coordinate_rows':int(reg.coordinate_shared_with_other_in_same_service.sum()),'official_record_level_url_available':record_level_sources,'official_record_level_url_missing':89-record_level_sources,'network_total_edges':len(net),'district_midpoint_eligible_network_km':float(study.length_m.sum()/1000),'modelled_higher_order_vehicle_road_length_pct':round(100*road_higher_share,3),'modelled_motorized_or_ambiguous_road_length_pct':round(100*road_suspect_share,3),'walking_permission_explicitly_verified_by_road_type':False,'recomputed_policy_rows':len(rows),'scenario_policy_source_rows':len(policy),'scenarios':int(recalced.scenario.nunique()),'scenario_proxy_comparisons':len(comp),'scenario_proxy_comparisons_disagree':int(comp.proxies_disagree.sum()),'culture_proxy_comparisons_disagree':int(comp[comp.service=='culture'].proxies_disagree.sum()),'facility_location_status':'unverified','network_walkability_status':'not_independently_validated','statutory_site_feasibility':'not_evaluated_for_hypothetical_sites','computational_arithmetic_check':'pass_270_rows','can_claim_observed_89_site_regret':False,'uncertainty_interpretation':'Five deterministic scenario values'}
(DEST/'publication_gate_summary.json').write_text(json.dumps(qa,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(qa,ensure_ascii=False,indent=2))
