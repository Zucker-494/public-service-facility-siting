#!/usr/bin/env python3
"""Original OSM PBF ways -> attributes audit, avoids invented walking permissions.

Flags uncertain higher-order routes in graph without assigning any pass/fail to real-world walkability.
"""
from pathlib import Path
import sys,json
import pandas as pd
import geopandas as gpd
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from pbf_reader import read_osm
pbf=ROOT/'data/raw/shanghai-260929.osm.pbf'
net=gpd.read_file(ROOT/'data/processed/p06_refined_clean.gpkg',layer='osm_node_identity_edges',ignore_geometry=True)
sub=net[net.zone>=0].copy()
needed=set(net.osm_way_id.dropna().astype(int))
look={}
for row in read_osm(pbf):
 if row[0]=='way' and row[1] in needed:
  tags=row[3]
  look[int(row[1])]={k:tags.get(k,'') for k in ['highway','foot','access','sidewalk','sidewalk:left','sidewalk:right','bicycle','motor_vehicle','motorcar','oneway','footway','bridge','tunnel','layer']}
assert len(look)>=int(.99*len(needed)),(len(look),len(needed))
rows=[]
for way,grp in sub.groupby('osm_way_id'):
 if pd.isna(way):continue
 wid=int(way); tags=look.get(wid,{})
 highway=str(tags.get('highway',''))
 length=float(grp.length_m.sum())
 explicit_foot=str(tags.get('foot','')).lower() in ('yes','designated','permissive','official')
 sidewalk_tags=[str(tags.get(z,'')).lower() for z in ['sidewalk','sidewalk:left','sidewalk:right']]
 sidewalk_present=any(z in ('yes','both','left','right','separate','shared','designated') for z in sidewalk_tags)
 sidewalk_absent=any(z in ('no','none') for z in sidewalk_tags)
 prohibited=str(tags.get('foot','')).lower() in ('no','private') or str(tags.get('access','')).lower() in ('no','private')
 high_order=highway in ('primary','primary_link','secondary','secondary_link','tertiary','tertiary_link')
 if prohibited: status='check_inconsistent_prohibited_still_modelled'
 elif high_order and (explicit_foot or sidewalk_present):status='higher_order_with_foot_or_sidewalk_evidence'
 elif high_order and sidewalk_absent:status='higher_order_sidewalk_tag_no_manual_review'
 elif high_order:status='higher_order_pedestrian_tags_not_explicit'
 elif highway in ('footway','path','pedestrian','steps','living_street'):status='pedestrian_designated_class'
 else:status='included_nonpedestrian_class_individual_access_unverified'
 rows.append(dict(osm_way_id=wid,highway=highway,district_midpoint_length_m=length,district_edges=len(grp),foot_tag=tags.get('foot',''),access_tag=tags.get('access',''),sidewalk_tag=tags.get('sidewalk',''),sidewalk_left=tags.get('sidewalk:left',''),sidewalk_right=tags.get('sidewalk:right',''),explicit_foot=explicit_foot,sidewalk_evidence=sidewalk_present,sidewalk_no=sidewalk_absent,review_class=status))
df=pd.DataFrame(rows); assert abs(df.district_midpoint_length_m.sum()-sub.length_m.sum())<.001
out=ROOT/'outputs/publication_gate';out.mkdir(exist_ok=True)
df.sort_values('district_midpoint_length_m',ascending=False).to_csv(out/'osm_source_way_pedestrian_access_evidence.csv',index=False)
agg=df.groupby('review_class',as_index=False).agg(study_length_m=('district_midpoint_length_m','sum'),way_count=('osm_way_id','size'),edge_count=('district_edges','sum'))
agg['pct_length']=agg.study_length_m/df.district_midpoint_length_m.sum()*100
agg.sort_values('study_length_m',ascending=False).to_csv(out/'pedestrian_access_source_tag_quality_by_class.csv',index=False)
res={'source_osm_way_tags_read':len(look),'study_unique_osm_ways':len(df),'pedestrian_network_approx_km':round(float(df.district_midpoint_length_m.sum()/1000),3),'way_tags_incomplete_for_survey_grade_access':True,'distribution':{str(r.review_class):{'length_km':round(r.study_length_m/1000,3),'pct_network_length':round(r.pct_length,2)} for r in agg.itertuples()}}
(out/'pedestrian_access_source_tag_qa.json').write_text(json.dumps(res,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(res,ensure_ascii=False,indent=2))
