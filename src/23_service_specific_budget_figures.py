#!/usr/bin/env python3
"""Publication graphics and transparent diagnostics for 1..40 independent NEW-site budgets.

Reads frozen sequential_addition_trajectories.csv. No interpolation, smoothing,
non-observed points, or stochastic confidence intervals. Existing 89 records (including
6 address-inferred baseline facilities) remain distinct from all newly added sites.
The network-greedy reference is a sequential heuristic and can be beaten at some k.
"""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

ROOT=Path(__file__).resolve().parents[1]
TABLE=ROOT/'outputs/sequential_investment/sequential_addition_trajectories.csv'
OUT=ROOT/'outputs/figures/sequential_v11';OUT.mkdir(parents=True,exist_ok=True)
RES=ROOT/'outputs/sequential_investment';RES.mkdir(parents=True,exist_ok=True)

d=pd.read_csv(TABLE)
required=['scenario','service','threshold_min','objective','rule','new_sites','cumulative_gain','signed_shortfall_vs_greedy','marginal_gain']
assert set(required).issubset(d.columns)
max_budget=int(d.new_sites.max()); assert max_budget>=20
services=['healthcare','elderly_care','culture']
service_name={'healthcare':'Healthcare','elderly_care':'Elderly care','culture':'Culture'}
basecounts={'healthcare':12,'elderly_care':65,'culture':12}
objectives=['district_gain_m','gain_equal_street_mean_pp']
obj_title={'district_gain_m':'A  Total added network coverage','gain_equal_street_mean_pp':'B  Mean coverage increase across 12 streets'}
units={'district_gain_m':'Additional covered network (km)','gain_equal_street_mean_pp':'Average coverage increase (percentage points)'}
short_units={'district_gain_m':'Difference from greedy reference (km)','gain_equal_street_mean_pp':'Difference from greedy reference (pp)'}
keys=['network_greedy','facilities_per_10k','facilities_per_km2','facilities_per_100km_network']
labels={'network_greedy':'Network-greedy reference','facilities_per_10k':'Per 10,000 residents','facilities_per_km2':'Per km²','facilities_per_100km_network':'Per 100 km road'}
# Same scientific color language in every figure; graphic exports are vector-ready.
style={'network_greedy':('#223348','-',2.65,'o'),
       'facilities_per_10k':('#C97830','-',2.0,'s'),
       'facilities_per_km2':('#18877E','--',2.1,'D'),
       'facilities_per_100km_network':('#8D5EAF','-.',2.0,'^')}
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'pdf.fonttype':42,'ps.fonttype':42,
 'axes.linewidth':.9,'axes.titlesize':11,'axes.labelsize':10.2,'legend.fontsize':9,
 'savefig.dpi':280,'xtick.labelsize':9,'ytick.labelsize':9})
idx=['service','objective','rule','threshold_min','new_sites']
count=d.groupby(idx).scenario.nunique()
assert len(count)==3*2*4*3*max_budget
assert (count==5).all(),(count.min(),count.max())
assert (d.groupby(['scenario','service','objective','rule','threshold_min']).new_sites.nunique()==max_budget).all()
assert set(d.new_sites.unique())==set(range(1,max_budget+1))

agg=d.groupby(idx,as_index=False).agg(n_scenarios=('scenario','nunique'),
    gain_min=('cumulative_gain','min'),gain_median=('cumulative_gain','median'),gain_max=('cumulative_gain','max'),
    diff_min=('signed_shortfall_vs_greedy','min'),diff_median=('signed_shortfall_vs_greedy','median'),diff_max=('signed_shortfall_vs_greedy','max'),
    marginal_min=('marginal_gain','min'),marginal_median=('marginal_gain','median'),marginal_max=('marginal_gain','max'))
agg.to_csv(OUT/'figure_data_all_services_all_thresholds.csv',index=False)

for svc in services:
    for mode in ('gain','difference'):
        fig,ax=plt.subplots(2,1,figsize=(9.4,9.2),layout='constrained')
        for j,obj in enumerate(objectives):
            a=ax[j]
            fac=0.001 if obj=='district_gain_m' else 1.
            for rule in keys:
                if mode=='difference' and rule=='network_greedy':continue
                rr=agg[(agg.service==svc)&(agg.objective==obj)&(agg.rule==rule)&(agg.threshold_min==15)].sort_values('new_sites')
                assert len(rr)==max_budget
                x=rr.new_sites.to_numpy()
                pref='gain' if mode=='gain' else 'diff'
                val=np.r_[0.,rr[f'{pref}_median'].to_numpy()*fac]
                lo=np.r_[0.,rr[f'{pref}_min'].to_numpy()*fac]
                hi=np.r_[0.,rr[f'{pref}_max'].to_numpy()*fac]
                x=np.r_[0,x]
                color,linestyle,lw,marker=style[rule]
                if np.any(hi-lo>1e-7):a.fill_between(x,lo,hi,color=color,alpha=.10,lw=0)
                a.plot(x,val,color=color,ls=linestyle,lw=lw,
                       marker=marker,markevery=[0,1,5,10,15,20,25,30,35,40] if max_budget==40 else max(1,max_budget//8),
                       markersize=4,markerfacecolor='white' if rule!='network_greedy' else color,
                       markeredgewidth=.85,label=labels[rule],zorder=5 if rule=='network_greedy' else 4)
            if mode=='difference':a.axhline(0,color='#696969',lw=.95,ls=':')
            a.set_title(obj_title[obj],loc='left',fontweight='semibold',pad=10)
            a.set_xlabel('New facilities added')
            a.set_ylabel(units[obj] if mode=='gain' else short_units[obj])
            a.set_xlim(0,max_budget)
            a.set_xticks(np.arange(0,max_budget+1,5))
            if mode=='gain':a.set_ylim(bottom=0)
            a.grid(axis='y',alpha=.2,lw=.7)
            a.set_axisbelow(True)
        text='Cumulative coverage gain' if mode=='gain' else 'Difference from the sequential greedy reference'
        fig.suptitle(f'{service_name[svc]}  |  {text}',fontsize=14,fontweight='bold')
        shown=[key for key in keys if mode=='gain' or key!='network_greedy']
        legend_handles=[Line2D([0],[0],color=style[k][0],ls=style[k][1],lw=style[k][2],
                                marker=style[k][3],markersize=4,label=labels[k]) for k in shown]
        fig.legend(handles=legend_handles,loc='outside lower center',ncol=len(shown),frameon=False)
        fig.get_layout_engine().set(w_pad=.13,h_pad=.11)
        # No numeric CI interpretation for min/max ranges across five deterministic site scenarios.
        p=OUT/f'{svc}_{"01_cumulative_gain" if mode=="gain" else "02_difference_to_greedy"}'
        for ext in ('png','pdf','svg'):fig.savefig(str(p)+'.'+ext,bbox_inches='tight')
        plt.close(fig)

# Supplemental single-service threshold sensitivity 5/10/15, with domain-specific y scales.
for svc in services:
    fig,axes=plt.subplots(1,3,figsize=(14.5,4.8),sharey=True,layout='constrained')
    for j,t in enumerate([5,10,15]):
        a=axes[j]
        for rule in keys:
            sub=agg[(agg.service==svc)&(agg.objective=='district_gain_m')&(agg.rule==rule)&(agg.threshold_min==t)].sort_values('new_sites')
            xx=np.r_[0,sub.new_sites.to_numpy()]
            yy=np.r_[0,sub.gain_median.to_numpy()/1000]
            color,ls,lw,marker=style[rule]
            a.plot(xx,yy,color=color,linestyle=ls,lw=lw,marker=marker,markevery=max(1,max_budget//8),markersize=3)
        a.set_title(f'{t}-minute walking threshold')
        a.set_xlim(0,max_budget);a.set_ylim(bottom=0)
        a.set_xticks(np.arange(0,max_budget+1,10));a.set_xlabel('New facilities added')
        a.grid(axis='y',alpha=.2)
    axes[0].set_ylabel('Additional covered network (km)')
    fig.suptitle(f'{service_name[svc]} | sensitivity to walking-time threshold',fontsize=13)
    fig.legend(handles=[Line2D([0],[0],color=style[k][0],ls=style[k][1],lw=style[k][2],label=labels[k]) for k in keys],
      loc='outside lower center',ncol=4,frameon=False)
    f=OUT/f'{svc}_03_walking_thresholds'
    for ext in ('png','pdf','svg'):fig.savefig(str(f)+'.'+ext,bbox_inches='tight')
    plt.close(fig)

# Transparent marginal-benefit summaries; incremental values are NOT smoothed.
summary=[]
for svc in services:
    for obj in objectives:
        for rule in keys:
            sub=agg[(agg.service==svc)&(agg.objective==obj)&(agg.rule==rule)&(agg.threshold_min==15)].set_index('new_sites')
            first=float(sub.loc[1,'marginal_median'])
            for k in [1,3,6,12,20,30,40]:
                if k>max_budget:continue
                row=sub.loc[k]
                summary.append(dict(service=svc,initial_service_facilities=basecounts[svc],objective=obj,rule=rule,
                    new_sites=k,added_fraction_of_initial=k/basecounts[svc],
                    gain_scenario_median=row.gain_median,marginal_scenario_median=row.marginal_median,
                    marginal_fraction_of_first=row.marginal_median/first if first>0 else np.nan,
                    five_scenario_min=row.gain_min,five_scenario_max=row.gain_max))
summary=pd.DataFrame(summary)
summary.to_csv(RES/'expanded_budget_marginal_summary.csv',index=False)

qa={'existing_official_facilities':89,'baseline_inherited_coordinates':83,'baseline_address_inferred_existing':6,
  'baseline_facility_counts_by_service':basecounts,'new_sites_are_independent_candidates':True,
  'new_site_budget_range':[1,max_budget],'range_is_administrative_policy_target':False,
  'purpose_of_budget_extension':'Explore diminishing gains across a common controlled computational range; no inferred build target',
  'scenario_variants':5,'scenario_ranges_are_confidence_intervals':False,
  'network_greedy_is_global_multisite_optimum':False,'results_rows':int(len(d)),
  'plot_data_rows':int(len(agg)),'figure_count':9,'full_thresholds_in_supplement':[5,10,15],
  'figure_checks':'all five scenarios present for every combination; source values directly aggregated',
  'source_table':str(TABLE.relative_to(ROOT))}
(RES/'expanded_budget_figure_qa.json').write_text(json.dumps(qa,ensure_ascii=False,indent=2),encoding='utf8')
print('FIGURES OK',json.dumps(qa,ensure_ascii=False),flush=True)
