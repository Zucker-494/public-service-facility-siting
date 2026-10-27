#!/usr/bin/env python3
"""Generate possible network locations for facilities without verified coordinates."""
from __future__ import annotations
import json, math, re, shutil, tempfile, zipfile, hashlib
from pathlib import Path
import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point, LineString, MultiLineString
from shapely.ops import unary_union
from shapely.strtree import STRtree
from scipy.spatial import cKDTree

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'data/processed/p06_refined_clean.gpkg'
REG=ROOT/'data/curated/official_facility_registry_89_address_audited.csv'
QA=ROOT/'data/qa/osm_inference'; OUT=ROOT/'outputs/osm_inference'
QA.mkdir(parents=True,exist_ok=True);OUT.mkdir(parents=True,exist_ok=True)
SOURCE=ROOT/'data/raw/shanghai-260928-free.gpkg.zip'
PROJ=32651
URL='https://shanghai.tianditu.gov.cn/xg/map.html'
# Textual source address evidence reviewed separately in src/10_address_registry_and_policy_audit.py.
# The candidate restriction based on same-road nearby address is a *scenario assumption*.
SPEC=[
 dict(facility_name='大桥街道社区文化活动中心',road='平凉路',compound=None,anchor_address='平凉路1759号',
      anchor_ref='上海杨浦区大桥社区老年公寓',radius_m=250,method='named_street_and_nearby_numbered_address',max_samples=15),
 dict(facility_name='延吉新村街道社区文化活动中心',road='延吉中路',compound=None,anchor_address='',
      anchor_ref='',radius_m=None,method='named_street_within_declared_subdistrict',max_samples=15),
 dict(facility_name='上海信养养老服务有限公司杨浦信澜养老院分公司',road='世界路',compound='世界路151弄',anchor_address='',
      anchor_ref='',radius_m=450,method='named_street_and_nearby_OSM_residential_compound',max_samples=15),
 dict(facility_name='上海市杨浦人和养老院',road=None,compound='市京一村',anchor_address='',
      anchor_ref='',radius_m=None,method='named_OSM_residential_compound_building_number_unresolved',max_samples=15),
 dict(facility_name='上海市杨浦区长海路街道敬老院',road='翔殷路',compound=None,anchor_address='翔殷路505弄3号',
      anchor_ref='长海路街道社区文化活动中心',radius_m=280,method='same_numbered_lane_nearby_building',max_samples=15),
 dict(facility_name='上海杨浦区汇晨长白老年福利院',road='春江路',compound=None,anchor_address='',
      anchor_ref='',radius_m=None,method='named_street_within_declared_subdistrict',max_samples=15),
]


def unique_vertices(edges):
    a=edges[['u_id']].rename(columns={'u_id':'osm_node_id'}).copy()
    a['x']=[g.coords[0][0] for g in edges.geometry]
    a['y']=[g.coords[0][1] for g in edges.geometry]
    b=edges[['v_id']].rename(columns={'v_id':'osm_node_id'}).copy()
    b['x']=[g.coords[-1][0] for g in edges.geometry]
    b['y']=[g.coords[-1][1] for g in edges.geometry]
    x=pd.concat([a,b],ignore_index=True).drop_duplicates('osm_node_id').reset_index(drop=True)
    assert len(x)>90000, len(x)
    return x


def main():
    reg=pd.read_csv(REG,encoding='utf-8-sig')
    missing=reg[~reg.inherited_spatial_point_present].copy()
    assert len(reg)==89 and len(missing)==6
    bounds=gpd.read_file(BASE,layer='study_subdistricts')
    edges=gpd.read_file(BASE,layer='osm_node_identity_edges')
    assert len(bounds)==12 and len(edges)==106698
    nodes=unique_vertices(edges)
    xys=nodes[['x','y']].to_numpy(float)
    from pyproj import Transformer
    conv=Transformer.from_crs(4326,PROJ,always_xy=True)
    with tempfile.TemporaryDirectory(prefix='p06_osm_source_') as temp:
        with zipfile.ZipFile(SOURCE) as z:
            z.extract('shanghai.gpkg',path=temp)
        gpkg=str(Path(temp)/'shanghai.gpkg')
        # All source layers are original Geofabrik 2026-09-28, not fresh OSM POI queries.
        bb=bounds.to_crs(4326).total_bounds
        bbox=(bb[0]-0.01,bb[1]-0.01,bb[2]+0.01,bb[3]+0.01)
        road=gpd.read_file(gpkg,layer='gis_osm_roads_free',bbox=bbox).to_crs(PROJ)
        land=gpd.read_file(gpkg,layer='gis_osm_landuse_a_free',bbox=bbox).to_crs(PROJ)
    candidates=[];summaries=[];corridors=[]
    street_map={r.subdistrict_name:r.geometry for r in bounds.itertuples()}
    for row in SPEC:
        m=missing.loc[missing.facility_name.eq(row['facility_name'])]
        assert len(m)==1,row
        r=m.iloc[0]
        poly=street_map[r.subdistrict_name]
        relevant=road[road.name.eq(row['road'])].copy() if row['road'] else road.iloc[0:0]
        named=land[land.name.eq(row['compound'])].copy() if row['compound'] else land.iloc[0:0]
        # Prefer official same street's road portion; keep OSM estate polygon if named.
        roadgeoms=[geom.intersection(poly.buffer(1)) for geom in relevant.geometry if geom.intersects(poly.buffer(1))]
        roadgeoms=[g for g in roadgeoms if not g.is_empty and g.length>0]
        roadgeom=unary_union(roadgeoms) if roadgeoms else None
        estate=unary_union([g for g in named.geometry if g.intersects(poly.buffer(120))]) if len(named) else None
        if estate is not None and estate.is_empty:estate=None
        if row['road'] and roadgeom is None:raise ValueError('No OSM street found '+row['facility_name'])
        if row['compound'] and estate is None:raise ValueError('Named OSM compound absent '+row['facility_name'])
        if row['method'].startswith('named_OSM_residential'):
            mask=estate.buffer(80).covers
            corridor=estate.buffer(80).intersection(poly.buffer(80))
        else:
            corridor=roadgeom.buffer(70).intersection(poly)
        anchor_pt=None;anchor_osm_id='';anchor_kind='';anchor_approx=False
        if row['anchor_ref']:
            a=reg.loc[reg.facility_name.eq(row['anchor_ref'])]
            assert len(a)==1 and a.iloc[0].inherited_spatial_point_present
            xx,yy=conv.transform(float(a.iloc[0].wgs84_lon),float(a.iloc[0].wgs84_lat))
            anchor_pt=Point(xx,yy)
            anchor_kind='inherited_other_facility_address_geocode_not_independently_verified'
            anchor_approx=True
        elif estate is not None and row['road']:
            anchor_pt=estate.representative_point()
            anchor_osm_id=';'.join(map(str,named.osm_id.tolist()))
            anchor_kind='osm_named_residential_compound_nearby_number_not_exact_target'
            anchor_approx=True
        if anchor_pt is not None and row['radius_m'] is not None:
            restricted=corridor.intersection(anchor_pt.buffer(float(row['radius_m'])))
            if restricted.is_empty:raise ValueError('Anchor and named OSM road inconsistent '+row['facility_name'])
            corridor=restricted
        possible=nodes[[corridor.distance(Point(x,y))<2 for x,y in xys]].copy() if False else None
        # Fast spatial pre-selection using bounding box, then geometry predicate.
        mnx,mny,mxx,mxy=corridor.bounds
        idx=np.flatnonzero((xys[:,0]>=mnx)&(xys[:,0]<=mxx)&(xys[:,1]>=mny)&(xys[:,1]<=mxy))
        idx=[int(i) for i in idx if corridor.covers(Point(*xys[i]))]
        # Ensure each candidate is on the accepted routing graph, and inside declared street.
        idx=[i for i in idx if poly.buffer(1).covers(Point(*xys[i]))]
        if not idx:
            raise ValueError('No accessible OSM nodes in candidate envelope '+row['facility_name'])
        coords=xys[idx]
        # A deterministic spatially spread sample: min 15 nodes, farthest-point sampling.
        chosen=[]
        if anchor_pt is not None:
            centroid=np.array([anchor_pt.x,anchor_pt.y])
        else:
            p=corridor.representative_point();centroid=np.array([p.x,p.y])
        k=int(np.argmin(np.sum((coords-centroid)**2,axis=1)));chosen.append(k)
        nearest=np.sum((coords-coords[k])**2,axis=1)
        for _ in range(min(int(row['max_samples']),len(coords))-1):
            k=int(np.argmax(nearest));chosen.append(k)
            nearest=np.minimum(nearest,np.sum((coords-coords[k])**2,axis=1))
        # Original OSM node IDs and original road names are preserved for each candidate.
        pt_geoms=[]
        for rank,k in enumerate(chosen,1):
            n=nodes.iloc[idx[k]]; p=Point(float(n.x),float(n.y))
            pt_geoms.append(p)
            candidates.append(dict(facility_name=row['facility_name'],facility_type=r.facility_type,
                canonical_address=r.canonical_address,declared_subdistrict=r.subdistrict_name,
                method=row['method'],osm_network_node_id=int(n.osm_node_id),x_utm51n=float(n.x),y_utm51n=float(n.y),
                candidate_rank=rank,plausible_node_total=len(idx),
                anchor_type=anchor_kind,anchor_is_approximate=anchor_approx,
                source_osm_road_way_ids=';'.join(sorted(map(str,relevant.osm_id.unique()))) if len(relevant) else '',
                source_osm_compound_way_ids=';'.join(sorted(map(str,named.osm_id.unique()))) if len(named) else '',
                address_matched_in_OSM=False,site_entrance_verified=False,
                primary_analysis_approved=False,scenario_only=True,geometry=p))
        dmax=math.hypot(coords[:,0].max()-coords[:,0].min(),coords[:,1].max()-coords[:,1].min())
        summaries.append(dict(facility_name=row['facility_name'],facility_type=r.facility_type,
            official_address=r.canonical_address,official_subdistrict=r.subdistrict_name,
            osm_match_method=row['method'],named_osm_road=row['road'] or '',named_osm_compound=row['compound'] or '',
            osm_road_length_in_subdistrict_m=round(roadgeom.length,1) if roadgeom is not None else np.nan,
            named_compound_area_m2=round(estate.area,1) if estate is not None else np.nan,
            anchor_reference_address=row['anchor_address'],anchor_provenance=anchor_kind,
            assumed_anchor_radius_m=row['radius_m'] if row['radius_m'] else '',
            candidate_original_node_count=len(idx),sampled_candidate_count=len(chosen),
            sampled_bbox_diagonal_m=round(dmax,1),
            exact_house_number_geocoded=False,entrance_confirmed=False,
            primary_admission=False,provisional_for_sensitivity=True,
            main_conclusion='ADDRESS_COVERED; ROUTING_POINT_UNKNOWN',
            geom=corridor))
        corridors.append(corridor)

    cd=pd.DataFrame(candidates).drop(columns='geometry')
    cd.to_csv(OUT/'six_facility_plausible_osm_network_nodes.csv',index=False,encoding='utf-8-sig')
    sd=pd.DataFrame(summaries).drop(columns='geom')
    sd.to_csv(QA/'six_facility_address_osm_trace.csv',index=False,encoding='utf-8-sig')
    sample_geo=gpd.GeoDataFrame(candidates,geometry='geometry',crs=PROJ)
    sample_geo.to_file(OUT/'address_candidate_envelopes.gpkg',layer='sampled_network_access_vertices',driver='GPKG')
    gpd.GeoDataFrame(summaries,geometry='geom',crs=PROJ).to_file(
        OUT/'address_candidate_envelopes.gpkg',layer='plausible_location_corridors',driver='GPKG',mode='a')
    # Enrich **hypothetical network candidates** with OSM landuse context.
    policy=gpd.read_file(BASE,layer='hypothetical_candidate_nodes_240m')
    j=gpd.sjoin(policy[['candidate_node','subdistrict','geometry']],land[['osm_id','fclass','name','geometry']],predicate='intersects',how='left')
    agg=j.groupby('candidate_node',dropna=False).agg(
      osm_landuse_categories=('fclass',lambda z:'|'.join(sorted(set(x for x in z.dropna().astype(str))))),
      osm_landuse_osm_ids=('osm_id',lambda z:'|'.join(sorted(set(x for x in z.dropna().astype(str))))))
    policy=policy.drop(columns='geometry').merge(agg,left_on='candidate_node',right_index=True,how='left',validate='one_to_one')
    policy['planning_portal_source']=URL
    policy['planning_parcel_id']=''
    policy['approved_legal_buildability']='unverified'
    policy['trial_portal_property_class']='not_extracted'
    policy['parcel_missingness_flag']=True
    policy['OSM_is_not_planning_permission']=True
    policy.to_csv(OUT/'candidate_osm_landuse_context_planning_pending.csv',index=False,encoding='utf-8-sig')
    qa=dict(version='0.6-osm-address-sensitivity',official_inventory_records=len(reg),
      missing_facility_sites=len(missing),address_context_matched=6,
      exact_osm_house_number_locations_verified=0,
      network_inference_candidate_facilities=6,
      sampled_osm_network_access_candidates=len(cd),
      total_planning_experimental_candidates=len(policy),
      official_planning_parcel_legal_buildability_confirmed=0,
      official_parcel_vectors_downloaded=False,raw_osm_landuse_only=True,
      existing_83_primary_sites_unchanged=True,
      source_geofabrik_osm_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
      caution='These nodes represent plausible walking-network access locations, not parcel-centroid or surveyed facility positions. Main results remain 83-site until scenario uncertainty reanalysis.')
    (QA/'v06_osm_address_inference_qa.json').write_text(json.dumps(qa,indent=2,ensure_ascii=False),encoding='utf8')
    assert cd.groupby('facility_name').size().to_dict().keys()==set(missing.facility_name)
    assert not cd.primary_analysis_approved.any()
    assert (policy.approved_legal_buildability=='unverified').all()
    print(json.dumps(qa,indent=2,ensure_ascii=False))
    print(sd[['facility_name','osm_match_method','candidate_original_node_count','sampled_bbox_diagonal_m']].to_string(index=False))
if __name__=='__main__':main()
