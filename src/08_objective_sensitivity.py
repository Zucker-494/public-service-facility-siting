#!/usr/bin/env python3
"""Compare facility placement outcomes under alternative coverage objectives."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'outputs/refined_model'
PROXIES=('facilities_per_10k','facilities_per_km2','facilities_per_100km_network')
FIELDS={'absolute_network_length':'district_gain_m','equal_street_percentage_point_gain':'gain_equal_street_mean_pp',
        'target_street_percentage_point_gain':'gain_target_street_pp'}

def run():
 rows=[];cross=[]
 for grid in (180,240,320):
  folder=BASE/f'grid_{grid}m'
  gain=pd.read_csv(folder/'candidate_marginal_gain.csv')
  supply=pd.read_csv(folder/'supply_verified.csv')
  for (s,t),gg in gain.groupby(['service','threshold_min']):
   ss=supply[supply.service==s]
   for objective,col in FIELDS.items():
    best=gg.loc[gg[col].idxmax()]
    oracle=float(best[col]);assert oracle>0
    zones=gg.groupby('subdistrict')[col].agg(['mean','max','min','count'])
    for proxy in PROXIES:
     mn=ss[proxy].min()
     eligible=ss.loc[np.isclose(ss[proxy],mn,atol=1e-12,rtol=1e-10),'subdistrict'].tolist()
     region=zones.loc[eligible]
     expected=float(region['mean'].mean())
     max_zone_mean=float(region['max'].mean())
     vals=gg[gg.subdistrict.isin(eligible)].groupby('subdistrict')[col]
     rows.append(dict(grid_m=grid,service=s,threshold_min=t,proxy=proxy,objective=objective,
                      decision_minimum_value=mn,selection_tie_count=len(eligible),selected_streets=' | '.join(sorted(eligible)),
                      oracle_street=best.subdistrict,oracle_gain=oracle,expected_policy_gain=expected,
                      normalized_regret=(oracle-expected)/oracle,zone_selection_regret_fraction=(oracle-max_zone_mean)/oracle,
                      within_zone_siting_regret_fraction=(max_zone_mean-expected)/oracle,
                      random_street_expected_gain=float(zones['mean'].mean()),
                      beats_random_street=bool(expected>=zones['mean'].mean()),
                      objective_unit='meters' if objective=='absolute_network_length' else 'percentage points'))
 d=pd.DataFrame(rows)
 d.to_csv(BASE/'objective_sensitivity_all.csv',index=False)
 # Pair fixed configuration rows by objective to see what changes purely from value function.
 a=d[d.objective=='absolute_network_length']
 b=d[d.objective=='equal_street_percentage_point_gain']
 both=a.merge(b,on=['grid_m','service','threshold_min','proxy'],suffixes=('_length','_equal'))
 both['oracle_street_changed']=both.oracle_street_length!=both.oracle_street_equal
 both['normalized_regret_difference_equal_minus_length']=both.normalized_regret_equal-both.normalized_regret_length
 both[['grid_m','service','threshold_min','proxy','oracle_street_length','oracle_street_equal','oracle_street_changed',
       'normalized_regret_length','normalized_regret_equal','normalized_regret_difference_equal_minus_length']].to_csv(BASE/'objective_street_comparison.csv',index=False)
 report={'n_compared_policy_cells':len(both),'oracle_street_changed_all_grids':int(both.oracle_street_changed.sum()),
         'main_grid_oracle_street_changed':int(both[both.grid_m==240].oracle_street_changed.sum()),
         'max_abs_regret_fraction_difference':float(both.normalized_regret_difference_equal_minus_length.abs().max()),
         'equal_street_objective':'Mean of the 12 subdistrict network-coverage improvements in percentage points; every street receives equal evaluation weight.',
         'target_street_objective':'Within the site-selected street, local network-coverage percentage-point improvement; ignores spillover to other streets.'}
 (BASE/'objective_sensitivity_qa.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
 print(json.dumps(report,ensure_ascii=False,indent=2))
 print(d[d.grid_m.eq(240)].pivot_table(index=['service','threshold_min','proxy'],columns='objective',values='normalized_regret').round(3).to_string())

if __name__=='__main__':run()
