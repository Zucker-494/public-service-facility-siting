#!/usr/bin/env python3
"""Simulate sequential facility additions on the restricted road network."""
from __future__ import annotations
import argparse
import importlib.util
import json
import hashlib
import sys
import time
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from numba import njit
from scipy.sparse.csgraph import dijkstra

ROOT=Path(__file__).resolve().parents[1]
DEST=ROOT/'outputs'/'walkability_strict_scenario'
DEST.mkdir(exist_ok=True,parents=True)
spec=importlib.util.spec_from_file_location('p06_graph_refinement',ROOT/'src/24_walkability_restricted_graph.py')
ref=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=ref
spec.loader.exec_module(ref)

SERVICE_ORDER=('healthcare','elderly_care','culture')
OBJ_NAMES=('district_gain_m','gain_equal_street_mean_pp')
PROXY_KEYS=('facilities_per_10k','facilities_per_km2','facilities_per_100km_network')
SCENARIO_INDEX=(0,3,7,11,14)

@njit(cache=True)
def all_marginal_gains(ptr,segs,du,dv,eu,ev,length,zone,weight,current,zone_length,available):
    """Exact marginal coverage improvement for each available NEW facility node.

    Result shape N_candidates x 2 objectives x 3 walking thresholds.
    Each edge contribution is clipped to its full length; graph distances include
    all currently selected facilities. Only edges within 1080m of candidate matter.
    """
    n=available.shape[0]
    result=np.zeros((n,2,3),dtype=np.float64)
    radii=(360.0,720.0,1080.0)
    for i in range(n):
        if not available[i]:
            continue
        for j in range(ptr[i],ptr[i+1]):
            e=segs[j]
            L=length[e]
            a=current[eu[e]]; b=current[ev[e]]
            aa=du[j]; bb=dv[j]
            z=zone[e]
            w=weight[e]
            for ti in range(3):
                R=radii[ti]
                l0=min(L,max(0.0,R-a));r0=min(L,max(0.0,R-b));bef=min(L,l0+r0)
                l1=min(L,max(0.0,R-min(a,aa)));r1=min(L,max(0.0,R-min(b,bb)))
                aft=min(L,l1+r1)
                delta=(aft-bef)*w
                if delta>0:
                    result[i,0,ti]+=delta
                    result[i,1,ti]+=delta/zone_length[z]*(100.0/12.0)
    return result


def make_sparse_cache(matrix,arr,candidates,batch=16):
    u,v,L,z,w=arr
    nvert=matrix.shape[0]
    # Lookup of all evaluated edge IDs incident to each graph vertex.
    incidence=[[] for _ in range(nvert)]
    for ei,(a,b) in enumerate(zip(u,v)):
        incidence[int(a)].append(ei)
        incidence[int(b)].append(ei)
    # Numba sees a single compact sparse index of candidates' reachable edges.
    row_ptr=[0]; segs=[]; dua=[];dva=[];rch_ptr=[0];rch_vert=[];rch_dist=[]
    ix=candidates.candidate_index.astype(int).to_numpy()
    for start in range(0,len(ix),batch):
        dist_batch=dijkstra(matrix,directed=False,indices=ix[start:start+batch],limit=1080.)
        if dist_batch.ndim==1: dist_batch=dist_batch[None,:]
        for dist in dist_batch:
            reach=np.flatnonzero(np.isfinite(dist)).astype(np.int32)
            local_edges=sorted(set(e for node in reach for e in incidence[int(node)]))
            # edges with at least one reachable endpoint. Graph vertex dists to others = inf.
            local_edges=np.asarray(local_edges,dtype=np.int32)
            segs.extend(local_edges.tolist());dua.extend(dist[u[local_edges]].astype(np.float32).tolist());dva.extend(dist[v[local_edges]].astype(np.float32).tolist());
            row_ptr.append(len(segs))
            rch_vert.extend(reach.tolist());rch_dist.extend(dist[reach].astype(np.float32).tolist());rch_ptr.append(len(rch_vert))
        if (start+batch)%160==0 or start+batch>=len(ix):
            print('candidate-distance cache',min(len(ix),start+batch),'/',len(ix),flush=True)
    return tuple(np.asarray(p,dtype=d) for p,d in ((row_ptr,np.int64),(segs,np.int32),(dua,np.float32),(dva,np.float32),(rch_ptr,np.int64),(rch_vert,np.int32),(rch_dist,np.float32)))


def apply_candidate(cur,ci,cache):
    p,s,d=cache[4:]
    nxt=cur.copy()
    a,b=p[ci],p[ci+1]
    verts=s[a:b]
    nxt[verts]=np.minimum(nxt[verts],d[a:b])
    return nxt


def select_scenario_sources(snaps,facility_verts,registry,options,node_map,scenario_rep):
    existing={s:[int(facility_verts[i]) for i in snaps.index[snaps.facility_type.eq(s)]] for s in SERVICE_ORDER}
    missing=registry.loc[~registry.inherited_spatial_point_present]
    look={name:q.sort_values('candidate_rank').reset_index(drop=True) for name,q in options.groupby('facility_name')}
    added={s:[] for s in SERVICE_ORDER};evidence=[]
    for j,name in enumerate(sorted(look)):
        q=look[name]
        k=(scenario_rep*(2*j+1)+j)%len(q)
        row=q.iloc[k]
        match=missing.loc[missing.facility_name.eq(name)]
        assert len(match)==1,(name,len(match))
        service=match.iloc[0].facility_type
        node=int(row.osm_network_node_id)
        added[service].append(int(node_map[node]))
        evidence.append(dict(scenario=f'INFERRED_89_{scenario_rep+1:02d}',existing_facility_name=name,service=service,imputed_osm_node_id=node,is_new_added_site=False))
    assert sum(map(len,added.values()))==6
    for s in SERVICE_ORDER: existing[s].extend(added[s])
    return existing,evidence


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--max-sites',type=int,default=10)
    ap.add_argument('--scenario',type=str,default='all',help='all or scenario index 1..5')
    ap.add_argument('--benchmark-sample-check',type=int,default=15)
    args=ap.parse_args()
    assert 1<=args.max_sites<=40
    begin=time.time()
    edges=gpd.read_file(ROOT/'data/processed/p06_refined_clean.gpkg',layer='osm_node_identity_edges')
    bounds=gpd.read_file(ROOT/'data/processed/p06_refined_clean.gpkg',layer='study_subdistricts')
    snaps=pd.read_csv(ROOT/'data/qa/facility_connector_distances_full.csv')
    candidates=pd.read_csv(ROOT/'outputs/refined_model/grid_240m/hypothetical_candidate_nodes_validated.csv')
    registry=pd.read_csv(ROOT/'data/curated/official_facility_registry_89_address_audited.csv',encoding='utf-8-sig')
    options=pd.read_csv(ROOT/'outputs/osm_inference/six_facility_plausible_osm_network_nodes.csv',encoding='utf-8-sig')
    supply=pd.read_csv(ROOT/'outputs/address_restoration/full_official_supply_240m_with_partial_accessibility.csv')
    assert len(registry)==89 and registry.inherited_spatial_point_present.sum()==83
    assert len(candidates)==1132 and candidates.candidate_node.is_unique
    assert len(snaps)==83
    assert (supply.count_full_official.sum()==89)
    names=list(bounds.subdistrict_name)
    assert set(supply.subdistrict)==set(names)
    street_id={n:i for i,n in enumerate(names)}
    assert candidates.subdistrict.map(street_id).notna().all()
    c_zone=candidates.subdistrict.map(street_id).astype(int).to_numpy()
    matrix,arr,facility_verts,quality=ref.construct_refined_graph(edges,bounds,snaps)
    u,v,L,z,w=arr
    zone_length=np.bincount(z,weights=L*w,minlength=12)
    assert (zone_length>0).all()
    node_map=dict(zip(edges.u_id.astype(int),edges.u_index.astype(int)))
    node_map.update(zip(edges.v_id.astype(int),edges.v_index.astype(int)))
    assert (candidates.candidate_node.map(node_map).astype(int)==candidates.candidate_index).all()
    cache=make_sparse_cache(matrix,arr,candidates)
    (ptr,segs,du,dv,_,_,_)=cache
    print('cache segments',len(segs),'mean per candidate',len(segs)/len(candidates),'elapsed',round(time.time()-begin,1),flush=True)
    # Validate cache against direct source distances for a diverse sample and all radii/weightings.
    sample=np.linspace(0,len(candidates)-1,args.benchmark_sample_check,dtype=int)
    baseline_83={s:ref.source_distance(matrix,[facility_verts[i] for i in snaps.index[snaps.facility_type.eq(s)]]) for s in SERVICE_ORDER}
    for ci in sample:
        zc=ref.source_distance(matrix,[int(candidates.candidate_index.iloc[ci])])
        c0=baseline_83['healthcare']
        true=ref.measure(np.minimum(c0,zc),arr)-ref.measure(c0,arr)
        pred=all_marginal_gains(ptr,segs,du,dv,u,v,L,z,w,c0,zone_length,np.arange(len(candidates))==ci)[ci]
        np.testing.assert_allclose(pred[0],true.sum(axis=1),rtol=1e-5,atol=0.025)
        np.testing.assert_allclose(pred[1],(true/zone_length).mean(axis=1)*100,rtol=1e-5,atol=0.001)
    print('direct Dijkstra comparison PASSED',len(sample),'samples',flush=True)
    fixed_89=supply.set_index(['service','subdistrict'])
    records=[]; added=[];baselines=[]
    scenarios=list(SCENARIO_INDEX)
    if args.scenario!='all':scenarios=[SCENARIO_INDEX[int(args.scenario)-1]]
    bys=(c_zone[:,None]==np.arange(12)[None,:]);ncan=len(candidates)
    for rep in scenarios:
        sid=f'INFERRED_89_{rep+1:02d}'
        src,evidence=select_scenario_sources(snaps,facility_verts,registry,options,node_map,rep)
        baselines.extend(evidence)
        for service in SERVICE_ORDER:
            basedist=ref.source_distance(matrix,src[service])
            basecov=ref.measure(basedist,arr)
            s=fixed_89.loc[service].loc[names]
            base_count=s['count_full_official'].astype(int).to_numpy()
            assert sum(base_count)==len(src[service])
            pop=s.population_census2020.to_numpy()
            area=s.area_km2.to_numpy()
            road=s.network_km.to_numpy()
            denom=np.column_stack((pop/10000.,area,road/100.))
            assert np.all(denom>0)
            for oi,obj in enumerate(OBJ_NAMES):
                all_strategies=('network_greedy',)+PROXY_KEYS
                for rule in all_strategies:
                    # run each threshold as an independent sequence, avoiding cross-threshold site contamination.
                    for ti,minutes in enumerate(ref.THRESHOLDS):
                        current=basedist.copy()
                        selected=np.zeros(ncan,dtype=np.bool_)
                        unit_counts=base_count.copy()
                        for budget in range(1,args.max_sites+1):
                            gains=all_marginal_gains(ptr,segs,du,dv,u,v,L,z,w,current,zone_length,~selected)
                            sc=gains[:,oi,ti]
                            allowed=(~selected)
                            tied=[]
                            if rule!='network_greedy':
                                pi=PROXY_KEYS.index(rule)
                                ratio=unit_counts/denom[:,pi]
                                m=ratio.min()
                                tied=np.flatnonzero(np.isclose(ratio,m,rtol=1e-11,atol=1e-12)).tolist()
                                allowed=allowed & np.isin(c_zone,tied)
                            choices=np.flatnonzero(allowed)
                            assert len(choices)>0,(sid,service,obj,rule,minutes,budget)
                            val=sc[choices]
                            # candidate IDs are sorted and this chooses lowest index in numerical ties.
                            ci=int(choices[int(np.argmax(val))])
                            delta=float(sc[ci]);
                            assert delta>=-1e-5
                            current=apply_candidate(current,ci,cache)
                            selected[ci]=True
                            unit_counts[c_zone[ci]]+=1
                            actual_coverage=ref.measure(current,arr)
                            cumulative_dist=float(actual_coverage[ti].sum()-basecov[ti].sum())
                            cumulative_equal=float(((actual_coverage[ti]-basecov[ti])/zone_length).mean()*100)
                            cumulative_gain=cumulative_dist if oi==0 else cumulative_equal
                            if abs(cumulative_gain-sum([row['marginal_gain'] for row in records if row['scenario']==sid and row['service']==service and row['objective']==obj and row['rule']==rule and row['threshold_min']==int(minutes)])-delta)>0.10:
                                raise AssertionError('Sequential cumulative gain mismatch')
                            row=dict(scenario=sid,existing_facilities=89,baseline_inherited_geocodes=83,baseline_address_imputations=6,
                              new_sites=budget,service=service,threshold_min=int(minutes),objective=obj,rule=rule,
                              candidate_id=ci,added_candidate_node=int(candidates.candidate_node.iloc[ci]),added_candidate_subdistrict=names[c_zone[ci]],
                              marginal_gain=delta,cumulative_gain=cumulative_gain,district_length_gain_m=cumulative_dist,equal_street_mean_gain_pp=cumulative_equal,
                              remaining_candidates=int((~selected).sum()),street_tie_count=len(tied) if tied else 0,
                              policy_uses_network_to_select_site_within_street=True,
                              all_facility_count=89+budget,service_facility_count=int(sum(base_count)+budget),buildability_verified=False)
                            records.append(row)
                            added.append(dict(scenario=sid,service=service,objective=obj,rule=rule,threshold_min=int(minutes),step=budget,
                              candidate_id=ci,osm_node_id=int(candidates.candidate_node.iloc[ci]),
                              subdistrict=names[c_zone[ci]],is_new_added_site=True))
                print('finished',sid,service,obj,'elapsed',round(time.time()-begin,1),flush=True)
    result=pd.DataFrame(records)
    result.to_csv(DEST/'sequential_addition_trajectories.csv',index=False)
    pd.DataFrame(added).to_csv(DEST/'new_added_site_sequence.csv',index=False)
    pd.DataFrame(baselines).to_csv(DEST/'existing_six_imputation_provenance.csv',index=False)
    # Exact comparison to within-scenario greedy reference; greedy itself is not an exact k-site optimum.
    idx=['scenario','service','objective','threshold_min','new_sites']
    greedy=result[result.rule.eq('network_greedy')].set_index(idx)['cumulative_gain']
    result['greedy_reference_gain']=result.set_index(idx).index.map(greedy)
    result['gain_relative_to_greedy']=result.cumulative_gain/result.greedy_reference_gain
    result['signed_shortfall_vs_greedy']=result.greedy_reference_gain-result.cumulative_gain
    assert np.all(np.isfinite(result.gain_relative_to_greedy))
    result.to_csv(DEST/'sequential_addition_trajectories.csv',index=False)
    # No comparison with a single-site benchmark computed from a different road graph.
    # The old one-site oracle belongs to the original road graph and does not apply to a filtered graph.
    frozen=None
    nchecked=0
    for key,d in result.iloc[:0].groupby(['scenario','service','objective','threshold_min']):
        sid,svc,obj,t=key
        expected=frozen[(frozen.site_scenario==sid)&(frozen.service==svc)&(frozen.threshold_min==t)][obj].max()
        assert abs(d.cumulative_gain.iloc[0]-expected)<0.06,(key,d.cumulative_gain.iloc[0],expected)
        nchecked+=1
    qa={'validation_direct_network_distance_samples':int(len(sample)),
        'one_site_independent_oracle_check_rows':0,
        'official_existing_records':89,'existing_inherited_coordinates':83,'existing_address_imputations':6,
        'separate_hypothetical_new_candidate_locations':int(len(candidates)),
        'new_site_budgets':int(args.max_sites),
        'scenario_variants':len(scenarios),'algorithm':'greedy_marginal_coverage_per_step_with_exact_edge_coverage',
        'global_multiple_site_optimality':'NOT_CLAIMED',
        'local_siting_for_proxy':'BEST_NETWORK_MARGINAL_GAIN_AMONG_MIN_SUPPLY_STREETS',
        'baseline_missing_points_not_new_sites':True,
        'scenario_estimates_are_confidence_intervals':False,
        'decision_results_contain_actual_buildability_validation':False,
        'maximum_abs_marginal_addition_discrepancy':float(np.max(np.abs(result.groupby(['scenario','service','objective','rule','threshold_min']).apply(lambda x:x.cumulative_gain.iloc[-1]-x.marginal_gain.sum(),include_groups=False)))),
        'elapsed_sec':round(time.time()-begin,1),'result_rows':len(result)}
    (DEST/'sequential_quality_gate.json').write_text(json.dumps(qa,ensure_ascii=False,indent=2),encoding='utf8')
    print('QA',json.dumps(qa,ensure_ascii=False,indent=2),flush=True)

if __name__=='__main__':main()
