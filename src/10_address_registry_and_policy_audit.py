#!/usr/bin/env python3
"""Restore authoritative addresses and audit supply-policy missingness.

Reproduction: python src/10_address_registry_and_policy_audit.py
The 89-source inventory is separate from 83 inherited spatial positions.
Archived low-quality address-geocoder responses are PROVISIONAL and excluded from
all final/official network coverage estimates. No OSM POI/name centroid is used.
"""
from __future__ import annotations
import hashlib,json,math
from pathlib import Path
import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import Point

ROOT=Path(__file__).resolve().parents[1]
CUR=ROOT/'data/curated';QA=ROOT/'data/qa/address_restoration';OUT=ROOT/'outputs/address_restoration'
for p in (CUR,QA,OUT):p.mkdir(parents=True,exist_ok=True)
RAW=ROOT/'data/raw/official_inventories'
ORIG=ROOT/'data/raw/p06_yangpu_original.gpkg'
PROC=ROOT/'data/processed/p06_refined_clean.gpkg'
SERVICES=('healthcare','elderly_care','culture')
PROXIES=('facilities_per_10k','facilities_per_km2','facilities_per_100km_network')

# Entries link independently reviewed public evidence to the exact attribute it confirms.
# Empty coordinate in the final row remains intentional until independent address-level
# spatial evidence is obtained. Official activity *venues* are not silently merged into
# the parent community cultural centre's main facility.
EVIDENCE={
 '大桥街道社区文化活动中心':dict(
    address='平凉路1730号',street='大桥街道',status='primary_site_official',
    address_date='2026-07-27',
    url='https://www.shanghai.gov.cn/nw17239/20260727/1b80d1000e3249f8af13f46522e3895e.html',
    other_url='https://www.mct.gov.cn/preview/special/8640/8649/201806/t20180613_833329.htm',
    note='Culture centre named with this address in government programme and Ministry of Culture list. No address-level coordinate in supplied extract.'),
 '延吉新村街道社区文化活动中心':dict(
    address='延吉中路77号',street='延吉新村街道',status='primary_site_official',
    address_date='2025-09-22',
    url='https://www.shanghai.gov.cn/nw17239/20250922/b91728e3a1054f68af5d48aaec87f8ca.html',
    other_url='https://www.shanghai.gov.cn/nw17239/20260831/6a0b320b7ac54c74b2ffdda9bf65c394.html',
    note='77 is primary culture-centre venue. 控江路645弄21号 is documented for off-site activities and should not be substituted for primary site.'),
 '上海信养养老服务有限公司杨浦信澜养老院分公司':dict(
    address='世界路203号',street='长海路街道',status='address_official',address_date='2023-09-15',
    url='https://ybj.sh.gov.cn/gsgg/20230918/e4ca6dfbefb641fea3f6fe0195d32680.html',other_url='',
    note='Official published business address confirmed. Inherited address-geocoder precise=0; no independent accurate doorway coordinate.'),
 '上海市杨浦人和养老院':dict(
    address='市京一村7号',street='长海路街道',status='address_in_original_2024_inventory_not_independently_officially_confirmed',
    address_date='2024-09-30',
    url='https://www.shyp.gov.cn/zhengwu/mzj-gyjsygl/2025/219/9a3687cf8d29a385c1ecea069ba67b0f.html',
    other_url='https://yanglaoku.com/cities/shanghai-3101-page-14.html',
    note='Gov. document confirms existence, not this address; original official inventory and third-party directory give this address. Do not raise to fully verified.'),
 '上海市杨浦区长海路街道敬老院':dict(
    address='翔殷路505弄9号',street='长海路街道',status='address_official',address_date='2024-10-16',
    url='https://www.shyp.gov.cn/shypq/ggfw-bmgg/20241016/465932.html',
    other_url='https://mzj.sh.gov.cn/MZ_zhuzhan23_0-2-8/20230630/94b3d20431e449dbaa7caaef4d86be76.html',
    note='Official address confirmed; geocoder precise=1 but confidence=0, so exact site position unresolved.'),
 '上海杨浦区汇晨长白老年福利院':dict(
    address='春江路815号',street='长白新村街道',status='newer_address_official_historical_discrepancy',
    address_date='2024-12-13',
    url='https://mzj.sh.gov.cn/MZ_zhuzhan34_0-2-6/20241213/8a4cd7a8d26f483e95e8fd98802f40ab.html',
    other_url='https://www.huichenlife.com/Project.aspx?ID=286&cateID=134',
    note='Source 2024-09 inventory reports 民治路15号. Official Dec-2024 and provider report 春江路815号. Archived geocoding for 民治路15号 is stale for current-location modelling.')
}

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def build_registry():
    inventories=[]
    files={
       'healthcare':'yangpu_community_health_centres_official_v0.4.csv',
       'elderly_care':'yangpu_elderlycare_official_2024.csv',
       'culture':'yangpu_community_cultural_centres_official_v0.5.csv'}
    for typ,f in files.items():
        x=pd.read_csv(RAW/f,dtype=str).fillna('')
        x['facility_type']=typ
        inventories.append(x)
    all_source=pd.concat(inventories,ignore_index=True)
    assert len(all_source)==89,len(all_source)
    assert all_source[['facility_type','facility_name']].duplicated().sum()==0
    original=gpd.read_file(PROC,layer='facility_inherited_coordinates').to_crs('EPSG:4326')
    assert len(original)==83
    assert not original[['facility_type','facility_name']].duplicated().any()
    oldgeo=gpd.read_file(ORIG,layer='facility_geocoded_baidu_qa').to_crs('EPSG:4326')
    records=[];provisional=[];geo_pts=[]
    key2point={(r.facility_type,r.facility_name):r.geometry for r in original.itertuples()}
    for r in all_source.itertuples():
       key=(r.facility_type,r.facility_name)
       ev=EVIDENCE.get(r.facility_name)
       source_address=str(getattr(r,'address','')).strip()
       address=(ev['address'] if ev else source_address)
       street=str(getattr(r,'subdistrict_name','')).strip()
       assert (not ev) or (street==ev['street']), (r.facility_name,street,ev['street'])
       geom=key2point.get(key)
       records.append(dict(facility_id=f'{r.facility_type}:{str(getattr(r,"source_record_id",""))}',
         facility_type=r.facility_type,facility_name=r.facility_name,source_record_id=str(getattr(r,'source_record_id','')),
         original_source_address=source_address,canonical_address=address,subdistrict_name=street,
         source_inventory=files[r.facility_type],source_snapshot_2024=str(getattr(r,'source_date','')),
         street_address_status=ev['status'] if ev else 'inherited_source_inventory_unreviewed',
         address_primary_url=ev['url'] if ev else '',
         address_secondary_url=ev['other_url'] if ev else '',
         independent_address_evidence_date=ev['address_date'] if ev else '',
         manual_evidence_note=ev['note'] if ev else '',
         inherited_spatial_point_present=geom is not None,
         geometry_source='inherited_baidu_geocoded_spatial_layer_unverified' if geom is not None else 'coordinate_not_verified',
         wgs84_lon=float(geom.x) if geom is not None else np.nan,
         wgs84_lat=float(geom.y) if geom is not None else np.nan,
         accepted_for_primary_network_model=geom is not None,
         admitted_v0_4=geom is not None))
       geo_pts.append(geom)
       if ev:
          x=oldgeo[(oldgeo.facility_type==r.facility_type)&(oldgeo.facility_name==r.facility_name)]
          # Address keyed: only use geocoder output matching exact, historic source address.
          if len(x)==1 and str(x.iloc[0].official_address).strip()==address and x.iloc[0].geometry is not None:
            xx=x.iloc[0]
            provisional.append(dict(facility_name=r.facility_name,facility_type=r.facility_type,
               canonical_address=address,query_address=xx.query_address,
               coordinate_source='ARCHIVED_BAIDU_ADDRESS_GEOCODER_NOT_OSM_POI',
               archived_request_id=xx.request_id,precise=float(xx.precise),confidence=float(xx.confidence),
               wgs84_lon=float(xx.geometry.x),wgs84_lat=float(xx.geometry.y),
               scenario_only=True,independently_verified_entrance=False,
               accepted_for_primary_network_model=False))
    d=pd.DataFrame(records);assert len(d)==89
    assert d.accepted_for_primary_network_model.sum()==83
    assert sum(~d.inherited_spatial_point_present)==6
    assert d.groupby('facility_type').size().to_dict()=={'culture':12,'elderly_care':65,'healthcare':12}
    d.to_csv(CUR/'official_facility_registry_89_address_audited.csv',index=False,encoding='utf-8-sig')
    allsp=gpd.GeoDataFrame(d.copy(),geometry=geo_pts,crs='EPSG:4326')
    allsp.to_file(CUR/'official_facility_registry_89.gpkg',layer='official_inventory_spatial_status',driver='GPKG')
    q=pd.DataFrame(provisional)
    q.to_csv(QA/'archived_address_geocodes_PROVISIONAL.csv',index=False,encoding='utf-8-sig')
    if len(q):
      gp=gpd.GeoDataFrame(q.copy(),geometry=gpd.points_from_xy(q.wgs84_lon,q.wgs84_lat),crs='EPSG:4326')
      gp.to_file(QA/'archived_address_geocodes_PROVISIONAL.gpkg',layer='address_geocoder_candidates',driver='GPKG')
    # Spatial coordinates of excluded items never assigned from unrelated OSM POI/name.
    if q.empty: assert False,'Archived address geocoder records expected for evidence sensitivity.'
    return d,q

def policy_recompute(registry,grid):
    base=ROOT/'outputs/refined_model'/f'grid_{grid}m'
    supply_old=pd.read_csv(base/'supply_verified.csv')
    gains=pd.read_csv(base/'candidate_marginal_gain.csv')
    official=registry.groupby(['facility_type','subdistrict_name']).size()
    supply=supply_old.copy()
    supply['count_full_official']=supply.apply(lambda r:int(official.get((r.service,r.subdistrict),0)),axis=1)
    supply['count_spatial_inherited_83']=supply['count_verified']
    for typ in SERVICES:
      assert sum(supply.loc[supply.service==typ,'count_full_official'])==int((registry.facility_type==typ).sum())
    supply['missing_points_by_subdistrict']=supply.count_full_official-supply.count_spatial_inherited_83
    assert (supply.missing_points_by_subdistrict>=0).all(), 'Official and spatial entity attribution disagree.'
    supply['facilities_per_10k']=supply.count_full_official/supply.population_census2020*10000
    supply['facilities_per_km2']=supply.count_full_official/supply.area_km2
    supply['facilities_per_100km_network']=supply.count_full_official/supply.network_km*100
    supply.to_csv(OUT/f'full_official_supply_{grid}m_with_partial_accessibility.csv',index=False)
    rows=[]
    for (service,t),gt in gains.groupby(['service','threshold_min'],sort=True):
      zone=gt.groupby('subdistrict').district_gain_m.agg(['mean','max','min','count'])
      oracle=float(gt.district_gain_m.max())
      assert oracle>0
      s0=supply_old.query('service == @service')
      s1=supply.query('service == @service')
      for metric in PROXIES:
        mn0=s0[metric].min();mn1=s1[metric].min()
        streets_old=sorted(s0.loc[np.isclose(s0[metric],mn0,rtol=1e-10,atol=1e-12),'subdistrict'].tolist())
        streets_new=sorted(s1.loc[np.isclose(s1[metric],mn1,rtol=1e-10,atol=1e-12),'subdistrict'].tolist())
        assert len(streets_old)>0 and len(streets_new)>0
        best_current=float(zone.loc[streets_old,'max'].mean());best_new=float(zone.loc[streets_new,'max'].mean())
        expected_old=float(zone.loc[streets_old,'mean'].mean());expected_new=float(zone.loc[streets_new,'mean'].mean())
        rows.append(dict(grid_m=grid,service=service,threshold_min=t,proxy=metric,
            old_selected_streets=' | '.join(streets_old),official_selected_streets=' | '.join(streets_new),
            old_tie_count=len(streets_old),official_tie_count=len(streets_new),priority_changed=streets_old!=streets_new,
            official_supply_restored=True,accessibility_reference_still_83=True,
            old_expected_gain_m=expected_old,official_supply_expected_gain_conditional_83m=expected_new,
            old_street_regret_m=oracle-best_current,official_supply_street_regret_conditional_83m=oracle-best_new,
            regret_difference_official_minus_spatial_m=(oracle-best_new)-(oracle-best_current),
            caveat='Outcome and oracle retain 83 point baseline. Not a complete 89-location reanalysis.' ))
    out=pd.DataFrame(rows)
    out.to_csv(OUT/f'priority_missingness_impact_{grid}m.csv',index=False)
    return out,supply

def main():
    reg,prov=build_registry()
    outs=[];sup=[]
    for grid in [180,240,320]:
      q,s=policy_recompute(reg,grid);outs.append(q);sup.append(s.assign(grid_m=grid))
    allout=pd.concat(outs,ignore_index=True);allout.to_csv(OUT/'all_grid_priority_missingness_impact.csv',index=False)
    idx=allout.query('grid_m == 240')
    qdict=dict(version='0.5-address-audit',official_inventory_records=len(reg),inherited_spatial_points=int(reg.inherited_spatial_point_present.sum()),
         address_verified_records_among_six=int(reg[~reg.inherited_spatial_point_present].street_address_status.isin(['primary_site_official','address_official','newer_address_official_historical_discrepancy']).sum()),
         missing_positions=6,provisional_address_geocoder_coordinates=len(prov),geocoder_candidates_in_primary=0,
         policy_priority_changes_grid240m=int(idx.priority_changed.sum()),total_comparisons_grid240m=len(idx),
         primary_accessibility_still_from_83=True,
         address_only_Osm_POI_snap_accepted=0,
         input_legacy_gpkg_sha256=sha(ORIG),clean_network_gpkg_sha256=sha(PROC),
         limitations=['six coordinates not independently confirmed','historical population/facilities/OSM year discrepancy','fixed candidate-network feasibility unknown', '83 inherited locations unverified independently'])
    (QA/'v05_address_supply_qa.json').write_text(json.dumps(qdict,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps(qdict,ensure_ascii=False,indent=2))
    print(idx[['service','threshold_min','proxy','old_selected_streets','official_selected_streets','priority_changed']].to_string(index=False))

if __name__=='__main__':main()
