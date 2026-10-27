#!/usr/bin/env python3
"""Prepare candidate site summaries for planning verification."""
from pathlib import Path
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs/osm_inference';QA=ROOT/'data/qa/osm_inference'
G=pd.read_csv(OUT/'inferred_89_candidate_gains_5_scenarios_240m.csv')
C=pd.read_csv(ROOT/'outputs/refined_model/grid_240m/hypothetical_candidate_nodes_validated.csv')
C['candidate_id']=range(len(C))
P=pd.read_csv(OUT/'candidate_osm_landuse_context_planning_pending.csv',encoding='utf-8-sig')
# Each scenario, category, duration and planning objective: top three potential
# network sites. They remain hypothetical until the official map is checked.
records=[]
for (scenario,service,t),g in G.groupby(['site_scenario','service','threshold_min']):
    for obj in ('district_gain_m','gain_equal_street_mean_pp'):
        top=g.nlargest(3,[obj,'candidate_id'])
        for rank,a in enumerate(top.itertuples(),1):
            records.append(dict(scenario=scenario,service=service,threshold_min=t,
                       objective=obj,rank_in_scenario=rank,
                       candidate_id=int(a.candidate_id),gain=float(getattr(a,obj))))
R=pd.DataFrame(records)
M=R.groupby('candidate_id').agg(top3_occurrences=('candidate_id','size'),
         service_scenarios=('service',lambda x:'|'.join(sorted(set(x))))).reset_index()
M=M.merge(C[['candidate_node','candidate_id','zone','subdistrict','x','y']],on='candidate_id',validate='one_to_one')
M=M.merge(P[['candidate_node','osm_landuse_categories','osm_landuse_osm_ids',
               'planning_portal_source','approved_legal_buildability','trial_portal_property_class']],on='candidate_node',validate='one_to_one')
M['planning_parcel_id']='';M['planning_map_search_address']=''
M['planning_dynamic']='not_collected_from_trial_map'
M['statutory_land_use_code']='not_collected_from_trial_map'
M['ownership_availability']='unknown'
M['development_fees_permits']='unknown'
M['site_is_certified_buildable']=False
M=M.sort_values(['top3_occurrences','candidate_id'],ascending=[False,True])
M.to_csv(OUT/'top_planning_verification_candidates_240m.csv',index=False,encoding='utf-8-sig')

# Compare metric definition (street choice only) on 83 vs inferred 89 for the
# district-length objective. This is a descriptive comparison of assumptions.
old=pd.read_csv(ROOT/'outputs/refined_model/grid_240m/policy_regret_tie_aware.csv')
new=pd.read_csv(OUT/'inferred_89_policy_regret_5_scenarios_240m.csv')
x=old[['service','threshold_min','proxy','selected_subdistricts','street_choice_regret_fraction']]
y=new[new.objective=='district_gain_m']
m=y.merge(x,on=['service','threshold_min','proxy'],validate='many_to_one')
m['street_choice_regret_fraction_difference']=m.relative_street_choice_regret-m.street_choice_regret_fraction
m['street_priority_changed']=(m.selected_streets.str.replace('|',' | ',regex=False)!=m.selected_subdistricts)
m.to_csv(OUT/'inferred_89_vs_inherited_83_street_choice_regret.csv',index=False,encoding='utf-8-sig')
res=dict(site_scenarios=5,top_three_candidate_records=len(R),distinct_site_candidates_prioritized=len(M),
      legal_buildability_of_shortlist_confirmed=0,
      comparisons=len(m),priority_changes=int(m.street_priority_changed.sum()),
      culture_comparisons=len(m.query("service=='culture'")),
      culture_priority_changes=int(m.query("service=='culture'").street_priority_changed.sum()),
      caution='Old 83-source analysis uses supply from 83 sites, inferred scenarios use all 89 supply but hypothesized road-access locations; differences mix supply-restoration and location uncertainty')
(QA/'v06_planning_and_comparison_qa.json').write_text(__import__('json').dumps(res,ensure_ascii=False,indent=2))
print(res)
