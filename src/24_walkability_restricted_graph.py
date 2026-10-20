#!/usr/bin/env python3
"""Publication-strength refinement of v0.3: real facility access vertices, exact boundary partition,
and exhaustive hypothetical one-site marginal gains on a common undirected OSM graph.

Uses the SHA-pinned v0.3 OSM-derived segment layer. Run `01_rebuild_and_experiment.py`
first if the raw PBF or upstream source is replaced. No 60-m facility filter.

Candidates remain *hypothetical street vertices*, not certified land parcels.
"""
from __future__ import annotations
import argparse, json, hashlib, math, time
from collections import defaultdict
from pathlib import Path
import geopandas as gpd
import pandas as pd
import numpy as np
import shapely
from shapely.geometry import Point, LineString
from shapely.strtree import STRtree
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import dijkstra

ROOT=Path(__file__).resolve().parents[1]
GPKG=ROOT/'data/processed/p06_rebuilt_network.gpkg'
DATA=ROOT/'data/qa/facility_connector_distances_full.csv'
THRESHOLDS=(5,10,15)
RADII=(360.,720.,1080.)
SERVICES=('healthcare','elderly_care','culture')
PROXIES=('facilities_per_10k','facilities_per_km2','facilities_per_100km_network')


def vertex_boundary_intervals(line, border):
    """Border intersection positions on a straight OSM segment (including boundary overlaps)."""
    inter=line.intersection(border)
    pos=[]
    def visit(g):
        if g.is_empty:return
        if g.geom_type=='Point':pos.append(line.project(g))
        elif g.geom_type in ('LineString','LinearRing'):
            coords=list(g.coords);pos.append(line.project(Point(coords[0])));pos.append(line.project(Point(coords[-1])))
        elif hasattr(g,'geoms'):
            for sub in g.geoms:visit(sub)
    visit(inter)
    return pos


def construct_refined_graph(edges,bounds,snaps,connect_atgrade=False):
    start=time.time()
    n_original=int(max(edges.u_index.max(),edges.v_index.max()))+1
    lines=list(edges.geometry)
    border=shapely.union_all(list(bounds.geometry.boundary))
    candidates=STRtree(lines).query(border,predicate='intersects')
    boundary_idxs=set(map(int,candidates))
    facility_extra_splits=defaultdict(list)
    if connect_atgrade:
        left=edges.index[(edges.osm_way_id==225995002)&(edges.zone>=0)]
        right=edges.index[(edges.osm_way_id==1324895009)&(edges.zone>=0)]
        possibilities=[(int(i),int(j)) for i in left for j in right if lines[i].crosses(lines[j])]
        assert len(possibilities)==1,possibilities
        ei,ej=possibilities[0];pos=lines[ei].intersection(lines[ej])
        facility_extra_splits[ei].append(float(lines[ei].project(pos)))
        facility_extra_splits[ej].append(float(lines[ej].project(pos)))
    facilities_on_edge=defaultdict(list)
    for ix,r in snaps.iterrows():
        facilities_on_edge[int(r.edge_index)].append((ix,float(r.projected_fraction),float(r.snap_distance_m)))
    affected=boundary_idxs | set(facilities_on_edge) | set(facility_extra_splits)
    # Deterministic polygon ordering is inherited from the original GPKG.
    polys=list(bounds.geometry)
    n_counter=n_original
    rec_u=[];rec_v=[];rec_L=[];rec_zone=[];eval_weight=[]
    graph_u=[];graph_v=[];graph_w=[]
    facility_vertex={}; facility_connect_cost={}
    refined_segments=0; shared_boundaries=0; crossing_edges=0
    extra_cross_vertices=[]
    for ei,row in enumerate(edges.itertuples()):
        blocked = str(row.highway) not in {"footway","pedestrian","path","steps","living_street","residential","service","unclassified","track"}
        u,v=int(row.u_index),int(row.v_index)
        L=float(row.length_m)
        if ei not in affected:
            if not blocked: graph_u.append(u);graph_v.append(v);graph_w.append(L)
            if not blocked and int(row.zone)>=0:
                rec_u.append(u);rec_v.append(v);rec_L.append(L);rec_zone.append(int(row.zone));eval_weight.append(1.)
            continue
        line=lines[ei]
        splits=[(0.,u),(L,v)]
        if ei in boundary_idxs:
            crossing_edges+=1
            for t in vertex_boundary_intervals(line,border):
                if 1.e-7<t<L-1.e-7:splits.append((t,None))
        for t in facility_extra_splits.get(ei,[]):
            if 1.e-7<t<L-1.e-7:splits.append((t,None))
        this_sites=[]
        for site_id,fraction,off in facilities_on_edge.get(ei,[]):
            t=float(np.clip(fraction*L,0.,L))
            if 1.e-7<t<L-1.e-7:splits.append((t,None))
            this_sites.append((site_id,t,off))
        splits.sort(key=lambda t:t[0])
        final=[]
        for t,n in splits:
            if final and abs(final[-1][0]-t)<1.e-6:
                if n is not None:final[-1]=(final[-1][0],n)
            else:final.append((t,n))
        allocated=[]
        for t,n in final:
            if n is None:n=n_counter;n_counter+=1
            allocated.append((t,n))
        for (t0,n0),(t1,n1) in zip(allocated[:-1],allocated[1:]):
            size=t1-t0
            if size<1.e-8:continue
            refined_segments+=1
            if not blocked: graph_u.append(n0);graph_v.append(n1);graph_w.append(size)
            if ei not in boundary_idxs:
                matched=[int(row.zone)] if int(row.zone)>=0 else []
            else:
                p=line.interpolate((t0+t1)/2)
                matched=[z for z,geom in enumerate(polys) if geom.covers(p)]
                if len(matched)>1:shared_boundaries+=1
                if not matched:
                    # Positional floating point behavior only: fallback via midpoint's nearest polygon.
                    nearest=[(geom.distance(p),z) for z,geom in enumerate(polys)]
                    if min(nearest)[0]<1.e-6:matched=[min(nearest)[1]]
            for z in matched if not blocked else []:
                rec_u.append(n0);rec_v.append(n1);rec_L.append(size);rec_zone.append(z);eval_weight.append(1./len(matched))
        for t in facility_extra_splits.get(ei,[]):
            match=min(allocated,key=lambda x:abs(x[0]-t))
            assert abs(match[0]-t)<1e-6
            extra_cross_vertices.append(match[1])
        for site_id,t,off in this_sites:
            nearest=min(allocated,key=lambda x:abs(x[0]-t))
            assert abs(nearest[0]-t)<1.e-6,(site_id,ei,t,nearest)
            facility_vertex[site_id]=n_counter;n_counter+=1
            facility_connect_cost[site_id]=off
            graph_u.append(facility_vertex[site_id]);graph_v.append(nearest[1]);graph_w.append(off)
    if connect_atgrade:
        assert len(extra_cross_vertices)==2
        graph_u.append(extra_cross_vertices[0]);graph_v.append(extra_cross_vertices[1]);graph_w.append(1.e-6)
    N=n_counter
    g_u=np.asarray(graph_u,dtype=np.int32);g_v=np.asarray(graph_v,dtype=np.int32)
    g_w=np.asarray(graph_w,dtype=float)
    matrix=coo_matrix((np.r_[g_w,g_w],(np.r_[g_u,g_v],np.r_[g_v,g_u])),shape=(N,N)).tocsr()
    # no facility connector cutoff. Duplicate edges should be absent by construction.
    eval_arrays=tuple(np.asarray(x,dtype=dt) for x,dt in [(rec_u,np.int32),(rec_v,np.int32),(rec_L,float),(rec_zone,np.int16),(eval_weight,float)])
    qa=dict(original_vertices=n_original,refined_vertices=N,facility_sources=len(facility_vertex), original_edges=len(edges),graph_edges=len(graph_u),
            measured_zone_segments=len(rec_u),boundary_contact_edge_count=len(boundary_idxs),boundary_splits=refined_segments,
            shared_boundary_segment_allocations=shared_boundaries, seconds_build=round(time.time()-start,2),
            segment_length_sum=float(np.dot(eval_arrays[2],eval_arrays[4])),topology_audit_cross_connected=bool(connect_atgrade))
    return matrix,eval_arrays,facility_vertex,qa


def measure(distance, eval_arr):
    u,v,L,z,w=eval_arr
    a=distance[u];b=distance[v]
    out=np.zeros((3,12),dtype=np.float64)
    for t,R in enumerate(RADII):
        covered=np.minimum(L,np.minimum(L,np.maximum(0,R-a))+np.minimum(L,np.maximum(0,R-b)))
        out[t]=np.bincount(z,weights=covered*w,minlength=12)
    return out


def source_distance(matrix,source_list):
    return dijkstra(matrix,directed=False,indices=source_list,min_only=True,limit=1080.)


def run(grid,connect_atgrade=False):
    t0=time.time()
    outputs=ROOT/'outputs/refined_model'/(f'grid_{grid}m_atgrade_connected' if connect_atgrade else f'grid_{grid}m')
    outputs.mkdir(parents=True,exist_ok=True)
    edges=gpd.read_file(GPKG,layer='osm_node_identity_edges')
    bounds=gpd.read_file(GPKG,layer='study_subdistricts')
    n_boundary_repeats=len(bounds)//12
    assert len(bounds)%12==0 and n_boundary_repeats>=1
    unique_bounds=bounds.iloc[:12].reset_index(drop=True)
    for k in range(1,n_boundary_repeats):
        bb=bounds.iloc[k*12:(k+1)*12].reset_index(drop=True)
        assert (unique_bounds.subdistrict_name.values==bb.subdistrict_name.values).all()
        assert unique_bounds.geometry.geom_equals_exact(bb.geometry,1e-6).all()
    bounds=unique_bounds
    snaps=pd.read_csv(DATA)
    candidates=pd.read_csv(ROOT/('data/processed/hypothetical_candidate_nodes.csv' if grid==240 else f'outputs/sensitivity/grid_{grid}m/hypothetical_candidate_nodes.csv'))
    matrix,arr,facility_verts,qa=construct_refined_graph(edges,bounds,snaps,connect_atgrade=connect_atgrade)
    names=bounds.subdistrict_name.to_list()
    # Original selection assigned network vertices by adjacent EDGE midpoint. Shared vertices
    # could consequently appear in multiple streets. Assign by actual vertex coordinate.
    candidates_original_rows=len(candidates)
    candidates_original_unique=candidates.candidate_node.nunique()
    candidates=candidates.drop_duplicates('candidate_node').copy()
    newzones=[]
    for r in candidates.itertuples():
        pt=Point(float(r.x),float(r.y))
        found=[z for z,p in enumerate(bounds.geometry) if p.contains(pt)]
        newzones.append(found[0] if len(found)==1 else -1)
    candidates['zone']=newzones
    candidates=candidates[candidates.zone>=0].copy()
    candidates['subdistrict']=candidates.zone.map(dict(enumerate(names)))
    candidates['candidate_basis']=f'at_grade_unique_osm_vertex_lattice_{grid}m'
    candidates=candidates.sort_values(['zone','candidate_node']).reset_index(drop=True)
    node_map=dict(zip(edges.u_id.astype(int),edges.u_index.astype(int)))
    node_map.update(dict(zip(edges.v_id.astype(int),edges.v_index.astype(int))))
    assert candidates.candidate_node.isin(node_map).all()
    candidates['candidate_index']=candidates.candidate_node.map(node_map).astype(int)
    candidates.to_csv(outputs/'hypothetical_candidate_nodes_validated.csv',index=False)
    qa.update(candidate_rows_before_validation=candidates_original_rows, candidate_unique_node_ids_before_validation=int(candidates_original_unique),
              candidate_nodes_after_polygon_validation=len(candidates), candidate_duplicates_removed=candidates_original_rows-candidates_original_unique,
              candidate_polygon_edge_ambiguities_removed=int(candidates_original_unique-len(candidates)))
    zone_lengths=np.bincount(arr[3],weights=arr[2]*arr[4],minlength=12)
    assert (zone_lengths>0).all()
    denom_previous=pd.read_csv(ROOT/'outputs/tables/supply_verified.csv').query("service=='healthcare'").set_index('subdistrict').loc[names]
    population=denom_previous.population_census2020.to_numpy()
    area=denom_previous.area_km2.to_numpy()
    # Direct geometries supplied for 83 facilities; street assigned using legacy accepted geometry.
    coords=gpd.read_file(GPKG,layer='verified_facilities')
    # v0.3 GPKG was appended three times by Fiona/pyogrio 'a' mode; audit and deduplicate.
    repeated_batches=len(coords)//len(snaps)
    assert len(coords)%len(snaps)==0 and repeated_batches>=1
    original=coords.iloc[:len(snaps)].reset_index(drop=True)
    for k in range(1,repeated_batches):
        block=coords.iloc[k*len(snaps):(k+1)*len(snaps)].reset_index(drop=True)
        assert (original[['facility_type','facility_name','zone']].values==block[['facility_type','facility_name','zone']].values).all()
        assert original.geometry.geom_equals_exact(block.geometry,1e-6).all()
    coords=original
    qa['duplicated_spatial_facility_batches_in_legacy_gpkg']=repeated_batches
    qa['duplicated_boundary_batches_in_legacy_gpkg']=n_boundary_repeats
    qa['legacy_facility_layer_rows']=len(snaps)*repeated_batches
    assert (coords.facility_name.to_numpy()==snaps.facility_name.to_numpy()).all()
    facility_zone=coords.zone.astype(int).to_numpy()
    base={};base_coverage={};supply=[];cover=[]
    for service in SERVICES:
        ids=snaps.index[snaps.facility_type.eq(service)].tolist()
        sources=[facility_verts[i] for i in ids]
        d=source_distance(matrix,sources)
        base[service]=d
        base_coverage[service]=measure(d,arr)
        counts=np.bincount(facility_zone[ids],minlength=12)
        for j,name in enumerate(names):
            supply.append(dict(service=service,subdistrict=name,count_verified=int(counts[j]),population_census2020=int(population[j]),
                area_km2=float(area[j]),network_km=float(zone_lengths[j]/1000),facilities_per_10k=float(counts[j]/population[j]*10000),
                facilities_per_km2=float(counts[j]/area[j]),facilities_per_100km_network=float(counts[j]/zone_lengths[j]*100000)))
            for ti,t in enumerate(THRESHOLDS):
                cover.append(dict(service=service,subdistrict=name,threshold_min=t,covered_network_m=float(base_coverage[service][ti,j]),
                    total_network_m=float(zone_lengths[j]),network_coverage_share=float(base_coverage[service][ti,j]/zone_lengths[j])))
    supply=pd.DataFrame(supply);coverage=pd.DataFrame(cover)
    supply.to_csv(outputs/'supply_verified.csv',index=False)
    coverage.to_csv(outputs/'observed_accessibility.csv',index=False)
    zone_names=candidates.subdistrict.tolist()
    gains=[]
    for ci,r in enumerate(candidates.itertuples()):
        dc=source_distance(matrix,[int(r.candidate_index)])
        for service in SERVICES:
            res=measure(np.minimum(dc,base[service]),arr)
            gain=res-base_coverage[service]
            for ti,t in enumerate(THRESHOLDS):
                gains.append((ci,service,r.zone,r.subdistrict,t,float(gain[ti].sum()),float(gain[ti,r.zone]),float(gain[ti].sum()/zone_lengths.sum()*100),
                              float(np.mean(gain[ti]/zone_lengths)*100),float(gain[ti,r.zone]/zone_lengths[r.zone]*100)))
        if (ci+1)%250==0:print(grid,'refined',ci+1,'/',len(candidates),round(time.time()-t0,1),'sec',flush=True)
    gain=pd.DataFrame(gains,columns=['candidate_id','service','zone','subdistrict','threshold_min','district_gain_m','target_subdistrict_gain_m','gain_percent_of_district_network','gain_equal_street_mean_pp','gain_target_street_pp'])
    gain.to_csv(outputs/'candidate_marginal_gain.csv',index=False)
    qa.update(dict(input_network_sha256=hashlib.sha256(GPKG.read_bytes()).hexdigest(),candidate_grid_m=grid,candidate_count=len(candidates),
                   site_snap_distance_max_m=float(snaps.snap_distance_m.max()),no_site_cutoff=True,district_length_km=float(zone_lengths.sum()/1000),
                   original_midpoint_length_km=float(denom_previous.network_km.sum()),elapsed_sec=round(time.time()-t0,2)))
    (outputs/'refinement_qa.json').write_text(json.dumps(qa,indent=2,ensure_ascii=False),encoding='utf8')
    print(grid,'DONE',round(time.time()-t0,1),'sec', flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--grid',type=int,default=240,choices=(180,240,320));p.add_argument('--connect-audit-atgrade',action='store_true');args=p.parse_args()
    run(args.grid,args.connect_audit_atgrade)
