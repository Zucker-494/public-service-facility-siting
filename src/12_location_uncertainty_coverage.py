#!/usr/bin/env python3
"""Network-length coverage scenario envelope for six address-inferred facilities.

No random 'confidence interval': rotates deterministic OSM plausible access vertices
around six address-defined candidate corridors; 83 inherited sites unchanged.
Output values are conditional scenarios, not reconstructed observed truth.
Missing-site walking connectors are set to zero from network vertices, hence
an optimistic network-access assumption explicitly tracked in the QA report.
"""
from __future__ import annotations
import importlib.util,sys,json,time
from pathlib import Path
import geopandas as gpd
import pandas as pd
import numpy as np
from scipy.sparse.csgraph import dijkstra
ROOT=Path(__file__).resolve().parents[1]
Q=ROOT/'data/qa/osm_inference';OUT=ROOT/'outputs/osm_inference';OUT.mkdir(exist_ok=True,parents=True)
M=ROOT/'src/06_exact_network_refinement.py'
spec=importlib.util.spec_from_file_location('p06_network_refinement',M)
ref=importlib.util.module_from_spec(spec);sys.modules[spec.name]=ref;spec.loader.exec_module(ref)

def main():
    started=time.time()
    net=ROOT/'data/processed/p06_rebuilt_network.gpkg'
    edges=gpd.read_file(net,layer='osm_node_identity_edges')
    bounds=gpd.read_file(net,layer='study_subdistricts')
    bounds=bounds.drop_duplicates('subdistrict_name').reset_index(drop=True)
    original_snaps=pd.read_csv(ROOT/'data/qa/facility_connector_distances_full.csv')
    assert len(original_snaps)==83
    matrix,evals,facility_vertices,qa=ref.construct_refined_graph(edges,bounds,original_snaps)
    n=matrix.shape[0]
    node_to_index=dict(zip(edges.u_id.astype(int),edges.u_index.astype(int)))
    node_to_index.update(dict(zip(edges.v_id.astype(int),edges.v_index.astype(int))))
    c=pd.read_csv(OUT/'six_facility_plausible_osm_network_nodes.csv',encoding='utf-8-sig')
    registry=pd.read_csv(ROOT/'data/curated/official_facility_registry_89_address_audited.csv',encoding='utf-8-sig')
    absent=registry[~registry.inherited_spatial_point_present]
    assert len(absent)==6
    assert set(c.facility_name)==set(absent.facility_name)
    c['graph_index']=c.osm_network_node_id.map(node_to_index)
    assert c.graph_index.notna().all()
    names=bounds.subdistrict_name.tolist()
    totals=ref.measure(np.zeros(n),evals)[0] # at R=360 zero distances all graph means all network covered
    # safer direct denominator from eval arrays
    zone_lengths=np.bincount(evals[3],weights=evals[2]*evals[4],minlength=12)
    sources={s:[facility_vertices[i] for i in original_snaps.index[original_snaps.facility_type.eq(s)]] for s in ref.SERVICES}
    base={s:ref.source_distance(matrix,lst) for s,lst in sources.items()}
    # 15 spread network-node combinations, no probabilistic sampling claim.
    lookup={name:x.sort_values('candidate_rank') for name,x in c.groupby('facility_name')}
    scenarios=[]
    for rep in range(15):
        selected={}
        for j,facility in enumerate(sorted(lookup)):
            subset=lookup[facility]
            k=(rep*(2*j+1)+j)%len(subset)
            chosen=subset.iloc[k]
            selected[facility]=int(chosen.graph_index)
        rec={'scenario':'ADDRESS_INFERENCE_'+str(rep+1).zfill(2),'selected_nodes':selected}
        scenarios.append(rec)
    rows=[]
    # inherited observed 83 network model benchmark
    for s,d in base.items():
        baseline=ref.measure(d,evals)
        for ti,t in enumerate(ref.THRESHOLDS):
            for zi,zname in enumerate(names):
                rows.append(dict(scenario='INHERITED_83_BASELINE',facility_universe='inherited_83',service=s,
                                 threshold_min=t,subdistrict=zname,network_coverage_share=float(baseline[ti,zi]/zone_lengths[zi]),
                                 inferred_sites_count=0,optimistic_zero_connector_for_new_site=False))
    for p,scenario in enumerate(scenarios,1):
        for s in ref.SERVICES:
            added_names=[a.facility_name for a in absent.itertuples() if a.facility_type==s]
            if not added_names:continue
            added_nodes=[scenario['selected_nodes'][name] for name in added_names]
            extra=ref.source_distance(matrix,added_nodes)
            with_new=ref.measure(np.minimum(base[s],extra),evals)
            for ti,t in enumerate(ref.THRESHOLDS):
                for zi,zname in enumerate(names):
                    rows.append(dict(scenario=scenario['scenario'],facility_universe='inferred_89_sensitivity',service=s,
                        threshold_min=t,subdistrict=zname,network_coverage_share=float(with_new[ti,zi]/zone_lengths[zi]),
                        inferred_sites_count=len(added_nodes),optimistic_zero_connector_for_new_site=True))
        print('inference scenario',p,'/',len(scenarios),'elapsed',round(time.time()-started,1),flush=True)
    out=pd.DataFrame(rows)
    out.to_csv(OUT/'street_network_coverage_missing_site_scenarios.csv',index=False,encoding='utf-8-sig')
    summaries=[]
    b=out.query('facility_universe == "inherited_83"').set_index(['service','subdistrict','threshold_min']).network_coverage_share
    for (s,zone,t),g in out.query('facility_universe == "inferred_89_sensitivity"').groupby(['service','subdistrict','threshold_min']):
        bs=float(b.loc[(s,zone,t)]);lo=float(g.network_coverage_share.min());hi=float(g.network_coverage_share.max())
        assert lo>=bs-1e-8
        summaries.append(dict(service=s,subdistrict=zone,threshold_min=t,baseline_83_coverage_share=bs,
            inferred_89_min_share=lo,inferred_89_max_share=hi,
            min_increment_percentage_points=(lo-bs)*100,max_increment_percentage_points=(hi-bs)*100,
            interval_kind='DETERMINISTIC_PLAUSIBLE_NODE_SCENARIO_RANGE_NOT_STATISTICAL_CI',
            site_doorway_located=False,new_site_connector_cost_m='ASSUMED_0_UPPER_ACCESSIBILITY',
            acceptable_for_final_realworld_claim=False))
    table=pd.DataFrame(summaries)
    table.to_csv(OUT/'street_coverage_scenario_range.csv',index=False,encoding='utf-8-sig')
    summary=dict(scenarios=len(scenarios),inherited_sites=83,address_inferred_scenario_sites=6,
        services_with_scenario=['elderly_care','culture'],main_observed_coverage_still_83=True,
        scenario_conditional_on_plausible_OSM_network_access_location=True,
        baseline_network_graph_vertices=n,baseline_routing_graph_sources=len(facility_vertices),
        new_entrance_connector_cost='assumed_zero_for_sensitivity_only',
        max_coverage_change_pp=float(table.max_increment_percentage_points.max()),
        mean_coverage_change_pp=float(table.max_increment_percentage_points.mean()),
        scenario_not_proof_of_true_locations=True,
        next_step='Repeat one-facility decision-regret simulations if official parcel polygons and address-level entrance evidence are obtainable.')
    (Q/'v06_location_uncertainty_qa.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2))
    (OUT/'scenario_selected_osm_node_ids.json').write_text(json.dumps([
        dict(scenario=p['scenario'],selected_graph_node_indices=p['selected_nodes']) for p in scenarios
        ],ensure_ascii=False,indent=2))
    print(json.dumps(summary,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
