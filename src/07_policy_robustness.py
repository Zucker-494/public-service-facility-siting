#!/usr/bin/env python3
"""Evaluate facility priority rankings across candidate grid resolutions."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
from scipy.stats import spearmanr,rankdata
ROOT=Path(__file__).resolve().parents[1]
OUTPUT=ROOT/'outputs/refined_model'
GRIDS=(180,240,320)
PROXIES=('facilities_per_10k','facilities_per_km2','facilities_per_100km_network')

def run_grid(grid):
    folder=OUTPUT/f'grid_{grid}m'
    gains=pd.read_csv(folder/'candidate_marginal_gain.csv')
    supply=pd.read_csv(folder/'supply_verified.csv')
    assert gains.candidate_id.nunique()==len(pd.read_csv(folder/'hypothetical_candidate_nodes_validated.csv'))
    assert len(supply)==36
    rows=[];ranking=[];sample_distributions=[]
    for (service,t),gt in gains.groupby(['service','threshold_min'],sort=True):
        oracle=max(gt.district_gain_m)
        assert oracle>0
        oracle_site=gt.loc[gt.district_gain_m.idxmax()]
        zones=gt.groupby('subdistrict').district_gain_m.agg(['mean','max','min','count']).reset_index()
        zone_index=zones.set_index('subdistrict')
        random_candidate_gain=float(gt.district_gain_m.mean())
        random_zone_gain=float(zones['mean'].mean())
        ss=supply[supply.service.eq(service)].copy()
        assert len(ss)==12 and set(ss.subdistrict)==set(zones.subdistrict)
        for proxy in PROXIES:
            mn=float(ss[proxy].min())
            selected=ss.loc[np.isclose(ss[proxy],mn,rtol=1e-10,atol=1e-12),'subdistrict'].tolist()
            assert len(selected)>=1
            selected=np.sort(np.array(selected,dtype=str)).tolist()
            selected_z=zone_index.loc[selected]
            expected=float(selected_z['mean'].mean())
            best_within=float(selected_z['max'].mean())
            # Exact distribution: first choose a tied minimum-rate street uniformly,
            # then a uniformly random candidate within it. Streets have equal mass.
            subframe=gt[gt.subdistrict.isin(selected)]
            weighted=[]
            for z in selected:
                g=subframe[subframe.subdistrict==z]
                weighted.extend([(float(v),1./len(selected)/len(g)) for v in g.district_gain_m.to_numpy()])
            vals=np.array([x[0] for x in weighted]);probs=np.array([x[1] for x in weighted])
            assert np.isclose(probs.sum(),1.)
            order=np.argsort(vals,kind='stable'); xv=vals[order]; pr=probs[order];cp=np.cumsum(pr)
            def weighted_quantile(q):return float(xv[min(int(np.searchsorted(cp,q,side='left')),len(xv)-1)])
            street_regret=oracle-best_within
            siting_regret=best_within-expected
            assert np.isclose((street_regret+siting_regret),oracle-expected,atol=1e-5)
            if len(selected)==1:
                chosen=selected[0]
            else:
                chosen=' | '.join(selected)
            rows.append(dict(grid_m=grid,service=service,threshold_min=t,proxy=proxy,
                selection_tie_count=len(selected),selected_subdistricts=chosen,
                sites_in_selected_streets=int(len(subframe)),oracle_gain_m=oracle,
                oracle_subdistrict=oracle_site.subdistrict,oracle_candidate_id=int(oracle_site.candidate_id),
                expected_policy_gain_m=expected,policy_gain_p10_m=weighted_quantile(.1),policy_gain_p50_m=weighted_quantile(.5),
                policy_gain_p90_m=weighted_quantile(.9),
                random_candidate_gain_m=random_candidate_gain,random_street_gain_m=random_zone_gain,
                street_choice_regret_m=street_regret,within_street_siting_regret_m=siting_regret,
                total_regret_m=oracle-expected,regret_fraction=(oracle-expected)/oracle,
                street_choice_regret_fraction=street_regret/oracle,within_street_siting_regret_fraction=siting_regret/oracle,
                expected_gain_minus_random_street_m=expected-random_zone_gain,
                proxy_worse_than_uniform_random_street=bool(expected<random_zone_gain),
                estimand='one added hypothetical network-node site; total network-length gain'))
            # Independent descriptive association between ordering of each proxy and
            # expected benefit from adding a site into each street.
            corr=ss[['subdistrict',proxy]].merge(zones,on='subdistrict',validate='one_to_one')
            sp=spearmanr(-corr[proxy],corr['mean'])
            # Gain ratio for the proxy's top-3 ranked zones against top-3 by network gain.
            ranked=corr.sort_values([proxy,'subdistrict'],ascending=[True,True])
            best3=corr.nlargest(3,'mean')
            proxy3=ranked.head(3)
            ranking.append(dict(grid_m=grid,service=service,threshold_min=t,proxy=proxy,
              spearman_proxy_priority_vs_average_gain=float(sp.statistic),
              best_three_average_gain_m=float(best3['mean'].sum()/3),
              proxy_three_average_gain_m=float(proxy3['mean'].sum()/3),
              top_three_efficiency=float(proxy3['mean'].sum()/best3['mean'].sum()) if best3['mean'].sum()>0 else np.nan,
              selected_best_street_by_mean=bool(set(selected)&set(zones[zones['mean']==zones['mean'].max()].subdistrict)),
              note='descriptive 12 streets; repeated three service categories and thresholds are not independent samples'))
            for z in selected:
                for r in subframe[subframe.subdistrict==z].itertuples():
                    sample_distributions.append(dict(grid_m=grid,service=service,threshold_min=t,proxy=proxy,
                      candidate_id=int(r.candidate_id),subdistrict=z,uniform_tie_policy_weight=1./len(selected)/int(zone_index.at[z,'count']),
                      district_gain_m=float(r.district_gain_m)))
    d=pd.DataFrame(rows);rn=pd.DataFrame(ranking);dist=pd.DataFrame(sample_distributions)
    assert len(d)==27 and len(rn)==27
    d.to_csv(folder/'policy_regret_tie_aware.csv',index=False)
    rn.to_csv(folder/'proxy_priority_ranking_validity.csv',index=False)
    dist.to_csv(folder/'policy_candidate_gain_distribution.csv',index=False)
    return d,rn

def main():
    all_dec=[];all_rank=[]
    for grid in GRIDS:
        d,rn=run_grid(grid);all_dec.append(d);all_rank.append(rn)
    all_dec=pd.concat(all_dec,ignore_index=True);all_rank=pd.concat(all_rank,ignore_index=True)
    all_dec.to_csv(OUTPUT/'policy_robustness_all_grids.csv',index=False)
    all_rank.to_csv(OUTPUT/'proxy_ranking_validity_all_grids.csv',index=False)
    base=all_dec[all_dec.grid_m.eq(240)].copy()
    q={
      'grids':list(GRIDS),
      'decisions_per_grid':27,
      'main_policy_regret_range':list(np.round([base.regret_fraction.min(),base.regret_fraction.max()],6)),
      'chosen_street_distinct_per_service':{s:int(g.groupby('proxy').selected_subdistricts.first().nunique()) for s,g in base.groupby('service')},
      'tie_cells_by_service':{s:int(g.selection_tie_count.gt(1).sum()) for s,g in base.groupby('service')},
      'proxy_worse_than_random_street_main_grid':int(base.proxy_worse_than_uniform_random_street.sum()),
      'main_regret_street_share_median':float((base.street_choice_regret_m/base.total_regret_m).median()),
      'ranking_top3_efficiency_median':float(all_rank[all_rank.grid_m.eq(240)].top_three_efficiency.median()),
      'inferential_warning':'All 27 policy outcomes are finite deterministic comparisons conditional on shared data; no invented independent sample size or p-values. 180/320m checks are alternative spatial discretizations, not sampling replications.',
      'source_limitation':'Only 83 previously accepted geocoded points have validated inherited coordinates, not a survey-certified complete 89-site inventory.'
    }
    (OUTPUT/'policy_robustness_qa.json').write_text(json.dumps(q,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps(q,ensure_ascii=False,indent=2))
    print('MAIN POLICY\n',base[['service','threshold_min','proxy','selected_subdistricts','selection_tie_count','regret_fraction','street_choice_regret_fraction','within_street_siting_regret_fraction','proxy_worse_than_uniform_random_street']].to_string(index=False))

if __name__=='__main__':main()
