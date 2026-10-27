"""Summarize parcel information available for hypothetical facility sites."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
from pyproj import Transformer

ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/'outputs/osm_inference'
QA=ROOT/'data/qa/planning'; QA.mkdir(parents=True,exist_ok=True)
OUT=ROOT/'outputs/planning_audit';OUT.mkdir(parents=True,exist_ok=True)
PORTAL='https://shanghai.tianditu.gov.cn/xg/map.html'
allc=pd.read_csv(SRC/'candidate_osm_landuse_context_planning_pending.csv')
top=pd.read_csv(SRC/'top_planning_verification_candidates_240m.csv')
assert len(allc)==1132 and len(top)==40
assert allc.approved_legal_buildability.eq('unverified').all()
assert top.approved_legal_buildability.eq('unverified').all()
assert (top.candidate_id.map(lambda k:int(allc.iloc[int(k)].candidate_node))==top.candidate_node).all()
trans=Transformer.from_crs(32651,4326,always_xy=True)
for frame in (allc,top):
    lon,lat=trans.transform(frame.x.to_numpy(),frame.y.to_numpy())
    frame['longitude_wgs84']=np.round(lon,7)
    frame['latitude_wgs84']=np.round(lat,7)
allc['candidate_id']=np.arange(len(allc),dtype=int)
allc['official_parcel_match_status']='UNMATCHED'
allc['official_parcel_record_id']=''
allc['legal_use_permission']='UNKNOWN'
allc['legal_site_eligible']='UNKNOWN'
allc['osmlanduse_is_official_planning']=False
allc['official_portal_source']=PORTAL
allc.to_csv(QA/'all1132_parcel_readiness.csv',index=False,encoding='utf-8-sig')
top['source_geometry']='hypothetical_original_OSM_network_node'
top['statutory_parcel_lookup']='UNMATCHED_no_georeferenced_official_parcel_id'
top['official_parcel_geometry_available']=False
top['official_parcel_use_verified']=False
top['official_parcel_dynamic_verified']=False
top['legal_buildability_conclusion']='UNKNOWN'
top['field_source']='2026-10-16 public planning portal: field definitions only; no record-specific attributes extracted'
top['next_verification']='identify official parcel boundary and ID, match coordinate; check land-use, planning dynamic, land rights, permit conditions'
top['validation_evidence_url']=''
top['date_checked']='2026-10-16'
top['osm_context_note']=top.osm_landuse_categories.apply(lambda v:'OSM residential area; parcel rights unresolved' if str(v)=='residential' else 'No OSM land-use polygon intersecting this road node')
top.to_csv(QA/'priority40_official_parcel_matching_audit.csv',index=False,encoding='utf-8-sig')
EXCLUDED_TAGS={'military','park','forest','recreation_ground','water','nature_reserve'}
def osm_context_conflict(v):
    return isinstance(v,str) and bool(EXCLUDED_TAGS.intersection(v.split('|')))
allc['osm_context_stress_excluded']=allc.osm_landuse_categories.map(osm_context_conflict)
allc[['candidate_id','candidate_node','subdistrict','osm_landuse_categories','osm_context_stress_excluded','official_parcel_match_status']].to_csv(OUT/'osm_context_exclusion_only_rule.csv',index=False,encoding='utf-8-sig')
blocks=set(allc.loc[allc.osm_context_stress_excluded,'candidate_id'].astype(int))
gains=pd.read_csv(SRC/'inferred_89_candidate_gains_5_scenarios_240m.csv')
rows=[]
for (scenario,service,t),group in gains.groupby(['site_scenario','service','threshold_min']):
    group=group.sort_values(['district_gain_m','candidate_id'],ascending=[False,True])
    orig=group.iloc[0]
    masked=group.loc[~group.candidate_id.isin(blocks)].iloc[0]
    rows.append(dict(site_scenario=scenario,service=service,threshold_min=t,
        unrestricted_best_candidate_id=int(orig.candidate_id),
        osm_screened_best_candidate_id=int(masked.candidate_id),
        site_choice_changed=bool(orig.candidate_id!=masked.candidate_id),
        unrestricted_network_gain_m=float(orig.district_gain_m),
        osm_screened_network_gain_m=float(masked.district_gain_m),
        network_gain_difference_m=float(orig.district_gain_m-masked.district_gain_m),
        note='OSM-only exclusion stress test, NOT statutory parcel validation'))
comparison=pd.DataFrame(rows)
comparison.to_csv(OUT/'osm_context_screen_45_optima_comparison.csv',index=False,encoding='utf-8-sig')
summary=dict(date_checked='2026-10-16',candidate_total=len(allc),priority_candidates=len(top),
  priority_with_osm_residential_context=int(top.osm_landuse_categories.eq('residential').sum()),
  priority_without_osm_landuse=int(top.osm_landuse_categories.isna().sum()),
  official_parcel_id_confirmed=0,official_landuse_confirmed=0,official_buildability_confirmed=0,
  candidate_without_osm_landuse=int(allc.osm_landuse_categories.isna().sum()),
  candidate_excluded_osm_context_stress=len(blocks),
  candidate_remain_osm_context_stress=len(allc)-len(blocks),
  scenario_count=len(comparison),changed_optima_after_osm_context_stress=int(comparison.site_choice_changed.sum()),
  planning_validation='NOT_PASSED',scope='hypothetical pedestrian-network location decisions only',
  source_plan_viewer=PORTAL,
  cannot_infer='legal buildability, land right, zoning or approved site from road node or OSM landuse')
(QA/'v07_parcel_audit_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(summary,ensure_ascii=False,indent=2))
