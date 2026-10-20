#!/usr/bin/env python3
"""Recompute 240m network candidate gains under three inferred-89 site scenarios.
Primary v0.4 policy output is *not* overwritten; these runs test how incomplete
site coordinates can distort decision regret. Candidate local search uses same
hypothetical 1,132 OSM at-grade network nodes, identical across scenarios.
"""
from __future__ import annotations
import sys,importlib.util,json,time,math
from pathlib import Path
import numpy as np,pandas as pd,geopandas as gpd
from scipy.sparse.csgraph import dijkstra
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs/osm_inference';QA=ROOT/'data/qa/osm_inference';OUT.mkdir(exist_ok=True)
modfile=ROOT/'src/06_exact_network_refinement.py'
spec=importlib.util.spec_from_file_location('p06_refinement_13',modfile)
r=importlib.util.module_from_spec(spec);sys.modules[spec.name]=r;spec.loader.exec_module(r)

def main():
    started=time.time()
    graph=ROOT/'data/processed/p06_rebuilt_network.gpkg'
    edges=gpd.read_file(graph,layer='osm_node_identity_edges')
    bounds=gpd.read_file(graph,layer='study_subdistricts').drop_duplicates('subdistrict_name').reset_index(drop=True)
    snaps=pd.read_csv(ROOT/'data/qa/facility_connector_distances_full.csv')
    matrix,arr,facility_verts,qa=r.construct_refined_graph(edges,bounds,snaps)
    nodemap=dict(zip(edges.u_id.astype(int),edges.u_index.astype(int)));nodemap.update(zip(edges.v_id.astype(int),edges.v_index.astype(int)))
    names=list(bounds.subdistrict_name)
    cand=pd.read_csv(ROOT/'outputs/refined_model/grid_240m/hypothetical_candidate_nodes_validated.csv')
    assert len(cand)==1132
    assert cand.candidate_node.isin(nodemap).all()
    cand['orig_graph_index']=cand.candidate_node.map(nodemap).astype(int)
    registry=pd.read_csv(ROOT/'data/curated/official_facility_registry_89_address_audited.csv',encoding='utf-8-sig')
    missing=registry[~registry.inherited_spatial_point_present]
    options=pd.read_csv(OUT/'six_facility_plausible_osm_network_nodes.csv',encoding='utf-8-sig')
    lookup={name:q.sort_values('candidate_rank').reset_index(drop=True) for name,q in options.groupby('facility_name')}
    baseline={s:r.source_distance(matrix,[facility_verts[i] for i in snaps.index[snaps.facility_type.eq(s)]]) for s in r.SERVICES}
    zoneL=np.bincount(arr[3],weights=arr[2]*arr[4],minlength=12)
    supply=pd.read_csv(ROOT/'outputs/address_restoration/full_official_supply_240m_with_partial_accessibility.csv')
    assert supply.count_full_official.sum()==89
    targets=['district_gain_m','gain_equal_street_mean_pp']
    traces=[]; gains_rows=[]
    # Spread five combinations along OSM candidate spaces; not a stochastic CI.
    scenarios=[0,3,7,11,14]
    scenario_bases={}
    for rep in scenarios:
        scenario_id=f'INFERRED_89_{rep+1:02d}'
        selected={}
        for j,name in enumerate(sorted(lookup)):
            q=lookup[name];k=(rep*(2*j+1)+j)%len(q)
            selected[name]=int(nodemap[int(q.iloc[k].osm_network_node_id)])
        ds={}
        for s in ['elderly_care','culture']:
            addition=[selected[x.facility_name] for x in missing.itertuples() if x.facility_type==s]
            da=r.source_distance(matrix,addition)
            ds[s]=np.minimum(baseline[s],da)
        ds['healthcare']=baseline['healthcare']
        scenario_bases[scenario_id]={s:(ds[s],r.measure(ds[s],arr)) for s in r.SERVICES}
    # Validate true old 83 baseline against stored observed table.
    old=pd.read_csv(ROOT/'outputs/refined_model/grid_240m/observed_accessibility.csv')
    for s in r.SERVICES:
        val=r.measure(baseline[s],arr)
        expected=old[old.service==s]
        for ti,t in enumerate(r.THRESHOLDS):
            x=expected[expected.threshold_min==t].set_index('subdistrict').loc[names]
            assert np.max(abs(x.covered_network_m.to_numpy()-val[ti]))<1e-5,'Refined network benchmark mismatch'
    for ci,z in enumerate(cand.itertuples()):
        dc=r.source_distance(matrix,[int(z.orig_graph_index)])
        for sid,si in scenario_bases.items():
            for s in r.SERVICES:
                base_d, base_cov=si[s]
                co=r.measure(np.minimum(base_d,dc),arr)
                gain=co-base_cov
                for ti,t in enumerate(r.THRESHOLDS):
                    gains_rows.append((sid,ci,s,int(t),str(z.subdistrict),float(gain[ti].sum()),
                        float(np.mean(gain[ti]/zoneL)*100)))
        if (ci+1)%250==0: print('candidate',ci+1,'/',len(cand),'elapsed',round(time.time()-started,1),flush=True)
    df=pd.DataFrame(gains_rows,columns=['site_scenario','candidate_id','service','threshold_min','subdistrict','district_gain_m','gain_equal_street_mean_pp'])
    df.to_csv(OUT/'inferred_89_candidate_gains_5_scenarios_240m.csv',index=False)
    rows=[]
    for (sid,svc,t),g in df.groupby(['site_scenario','service','threshold_min']):
        ss=supply[supply.service==svc]
        for objective in targets:
            oracle=float(g[objective].max())
            byzone=g.groupby('subdistrict')[objective].agg(['max','mean'])
            rand_street=float(byzone['mean'].mean())
            for proxy in r.PROXIES:
                mn=ss[proxy].min()
                streets=sorted(ss.loc[np.isclose(ss[proxy],mn,rtol=1e-10,atol=1e-12),'subdistrict'].tolist())
                assert len(streets)>0 and set(streets).issubset(byzone.index)
                chosen_best=float(byzone.loc[streets,'max'].mean())
                chosen_expected=float(byzone.loc[streets,'mean'].mean())
                rows.append(dict(site_scenario=sid,service=svc,threshold_min=t,proxy=proxy,objective=objective,
                    selected_streets='|'.join(streets),oracle_gain=oracle,
                    selected_street_best_gain=chosen_best,selected_street_mean_gain=chosen_expected,
                    street_choice_regret=oracle-chosen_best,
                    within_street_expected_regret=chosen_best-chosen_expected,
                    total_expected_regret=oracle-chosen_expected,
                    relative_street_choice_regret=(oracle-chosen_best)/oracle if oracle>0 else np.nan,
                    random_street_expected_gain=rand_street,
                    is_street_choice_better_than_random=(chosen_expected>rand_street)))
    policy=pd.DataFrame(rows)
    policy.to_csv(OUT/'inferred_89_policy_regret_5_scenarios_240m.csv',index=False)
    out={
      'scenarios':5,'candidate_count':len(cand),'site_count_under_scenario':89,
      'street_priority_uses_full_89_official_inventory':True,
      'coverage_includes_6_OSM_inferred_access_nodes':True,
      'unverified_site_entrances_assumed_zero_m_to_graph':True,
      'hypothetical_planning_candidates_not_certified_buildable':True,
      'scenario_policy_rows':len(policy),
      'relative_street_choice_regret_min':float(policy.relative_street_choice_regret.min()),
      'relative_street_choice_regret_max':float(policy.relative_street_choice_regret.max()),
      'culture_scenario_regret_range':{
          p:[round(float(d.relative_street_choice_regret.min()),4),round(float(d.relative_street_choice_regret.max()),4)]
          for p,d in policy.query("service=='culture' and objective=='district_gain_m'").groupby('proxy')},
      'observed_network_baseline_validation':'PASS_exact_v04_83',
      'elapsed_seconds':round(time.time()-started,1),
      'interpretation':'deterministic inferred-site scenario results, not confirmed observed 89-site result'
    }
    (QA/'v06_policy_inferred_89_scenario_qa.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
    print(json.dumps(out,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
