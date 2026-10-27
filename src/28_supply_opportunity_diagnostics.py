from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.stats import spearmanr

PROXY = {
    'per_10k': ('facilities_per_10k', 'Per 10,000 residents'),
    'per_km2': ('facilities_per_km2', 'Per km$^2$'),
    'per_100km': ('facilities_per_100km_network', 'Per 100 km roads'),
}
SERVICES = {'healthcare': 'Healthcare', 'elderly_care': 'Elderly care', 'culture': 'Culture'}

def build(repo: Path):
    out = repo / 'outputs' / 'sequential_investment'
    figs = repo / 'outputs' / 'figures' / 'all_figures_png'
    out.mkdir(parents=True, exist_ok=True); figs.mkdir(parents=True, exist_ok=True)
    cand = pd.read_csv(repo / 'outputs/osm_inference/inferred_89_candidate_gains_5_scenarios_240m.csv')
    supply = pd.read_csv(repo / 'outputs/address_restoration/full_official_supply_240m_with_partial_accessibility.csv')
    traj = pd.read_csv(repo / 'outputs/sequential_investment/sequential_addition_trajectories.csv')
    assert len(cand)==50940 and len(supply)==36 and len(traj)==14400
    t0=traj[traj.new_sites==1].merge(cand,
        left_on=['scenario','service','threshold_min','candidate_id'],
        right_on=['site_scenario','service','threshold_min','candidate_id'],
        how='left',validate='many_to_one')
    assert len(t0)==360 and t0.site_scenario.notna().all()
    direct=np.where(t0.objective=='district_gain_m', t0.district_gain_m,
                    t0.gain_equal_street_mean_pp)
    assert float(np.max(np.abs(direct-t0.marginal_gain))) < 0.01
    assert supply.count_full_official.sum()==89
    supply['facilities_per_10k'] = supply.count_full_official/(supply.population_census2020/1e4)
    supply['facilities_per_km2'] = supply.count_full_official/supply.area_km2
    supply['facilities_per_100km_network'] = supply.count_full_official/(supply.network_km/100)
    street = (cand.groupby(['site_scenario','service','threshold_min','subdistrict'],as_index=False)
              .agg(max_district=('district_gain_m','max'),max_equal=('gain_equal_street_mean_pp','max'),n_candidates=('candidate_id','size')))
    street = street.merge(supply,on=['service','subdistrict'],validate='many_to_one')
    assert len(street)==540 and street.groupby(['site_scenario','service','threshold_min']).size().eq(12).all()
    street.to_csv(out/'street_opportunity_540.csv',index=False)

    correlations=[]; decisions=[]; structure=[]
    for (scenario,service,t), d in street.groupby(['site_scenario','service','threshold_min']):
        for objective, col in [('district','max_district'),('equal','max_equal')]:
            max_gain = d[col].max()
            for proxy, (field,_) in PROXY.items():
                rho=float(spearmanr(-d[field],d[col]).statistic)
                correlations.append(dict(scenario=scenario,service=service,threshold_min=t,
                                         objective=objective,proxy=proxy,spearman_rho=rho))
                mask=np.isclose(d[field],d[field].min(),atol=1e-12,rtol=1e-11)
                chosen_best=d.loc[mask,col].max()
                decisions.append(dict(scenario=scenario,service=service,threshold_min=t,
                                      objective=objective,proxy=proxy,chosen_max_gain=chosen_best,
                                      all_streets_mean_best=d[col].mean(),global_best_gain=max_gain,
                                      fraction_of_global_best=chosen_best/max_gain,
                                      above_equal_street_mean=bool(chosen_best>d[col].mean()),
                                      tied_priority_streets=int(mask.sum())))
            for metric in ['network_km','n_candidates','population_census2020']:
                rho=float(spearmanr(d[metric],d[col]).statistic)
                structure.append(dict(scenario=scenario,service=service,threshold_min=t,
                                      objective=objective,metric=metric,spearman_rho=rho))

    corr=pd.DataFrame(correlations); dec=pd.DataFrame(decisions); st=pd.DataFrame(structure)
    assert len(corr)==270 and len(dec)==270 and len(st)==270
    corr.to_csv(out/'supply_opportunity_rank_correlations.csv',index=False)
    dec.to_csv(out/'supply_priority_opportunity_audit.csv',index=False)
    st.to_csv(out/'spatial_structure_correlations.csv',index=False)
    paired=corr.pivot_table(index=['scenario','service','threshold_min','proxy'], columns='objective',values='spearman_rho')
    paired['district_minus_equal']=paired['district']-paired['equal']
    paired.reset_index().to_csv(out/'paired_objective_correlations.csv',index=False)
    fig, ax = plt.subplots(1,2,figsize=(9.4,3.8), layout='constrained')
    for a,(objective,label) in zip(ax,[('district','A. District-wide added road length'),('equal','B. Equal-subdistrict coverage gain')]):
        sub=corr[corr.objective==objective]
        mat=np.array([[sub[(sub.service==srv)&(sub.proxy==p)].spearman_rho.median() for p in PROXY] for srv in SERVICES])
        im=a.imshow(mat, cmap='RdBu',vmin=-1,vmax=1)
        a.set_xticks(range(3),['Per 10k', 'Per km$^2$', 'Per 100km'],fontsize=10)
        a.set_yticks(range(3),list(SERVICES.values()),fontsize=10)
        for i in range(3):
            for j in range(3):
                a.text(j,i,f'{mat[i,j]:+.2f}',ha='center',va='center',fontsize=11,
                       color='white' if abs(mat[i,j])>0.57 else 'black',weight='semibold')
        a.set_title(label,fontsize=11)
    cb=fig.colorbar(im,ax=ax,shrink=.86,pad=.02)
    cb.set_label('Median Spearman rank correlation',fontsize=10)
    fig.suptitle('Does lower administrative supply predict greater modelled coverage opportunity?',fontsize=13)
    fig.savefig(figs/'supply_opportunity_rank_validity.png',dpi=300,bbox_inches='tight')
    plt.close(fig)
    fig,axs=plt.subplots(1,2,figsize=(9.6,4.0),layout='constrained')
    labels=['Population','Area','Road length']
    xx=np.arange(3); width=.36
    for a,measure,label in zip(axs,['fraction_of_global_best','above_equal_street_mean'],
                               ['A. Share of objective-specific best candidate gain (%)','B. Cases above mean of 12 street maxima (%)']):
        for k, objective in enumerate(['district','equal']):
            vals=[]
            for proxy in PROXY:
                v=dec[(dec.proxy==proxy)&(dec.objective==objective)][measure]
                vals.append(100*float(v.median() if measure=='fraction_of_global_best' else v.mean()))
            bars=a.bar(xx+(k-.5)*width,vals,width=width,
                       label=('District-length objective' if k==0 else 'Equal-subdistrict objective'))
            for bar,val in zip(bars,vals):
                a.text(bar.get_x()+bar.get_width()/2,bar.get_height()+1,f'{val:.1f}',ha='center',fontsize=8)
        a.set_xticks(xx,labels)
        a.set_ylim(0,108)
        a.set_ylabel('Percent (%)')
        a.set_title(label,fontsize=10)
        a.grid(axis='y',alpha=.20)
        a.set_axisbelow(True)
    handles, labels_ = axs[0].get_legend_handles_labels()
    fig.legend(handles, labels_, frameon=False, fontsize=9, loc='upper center',
               bbox_to_anchor=(0.5, 0.02), ncol=2)
    fig.suptitle('Maximum modelled opportunity within lowest-supply priority streets',fontsize=12.5)
    fig.savefig(figs/'supply_priority_opportunity.png',dpi=300,bbox_inches='tight')
    plt.close(fig)
    trial=traj[traj.rule!='network_greedy'].copy()
    trial['relative_shortfall_pct']=(1-trial.gain_relative_to_greedy)*100
    ag=(trial.groupby(['objective','new_sites'],as_index=False).agg(
          relative_pct=('relative_shortfall_pct','median'),
          absolute=('signed_shortfall_vs_greedy','median')))
    ag.to_csv(out/'sequential_median_shortfalls.csv',index=False)
    fig,axs=plt.subplots(1,3,figsize=(10.7,3.9),layout='constrained')
    x1=ag[ag.objective=='district_gain_m'];x2=ag[ag.objective=='gain_equal_street_mean_pp']
    for a in axs:a.set_xlabel('Number of added facilities');a.grid(alpha=.25)
    axs[0].plot(x1.new_sites,x1.relative_pct,label='District length',lw=2)
    axs[0].plot(x2.new_sites,x2.relative_pct,label='Equal subdistricts',lw=2)
    axs[0].set_title('A. Relative shortfall');axs[0].set_ylabel('Median loss versus greedy (%)')
    axs[0].legend(frameon=False,fontsize=8)
    axs[1].plot(x1.new_sites,x1.absolute/1000,lw=2)
    axs[1].set_title('B. Absolute district-length shortfall');axs[1].set_ylabel('Median cumulative difference (km)')
    axs[2].plot(x2.new_sites,x2.absolute,lw=2)
    axs[2].set_title('C. Absolute equal-subdistrict shortfall');axs[2].set_ylabel('Median cumulative difference (pp)')
    fig.suptitle('Sequential opportunity costs of supply-priority allocation',fontsize=13)
    fig.savefig(figs/'sequential_opportunity_costs.png',dpi=300,bbox_inches='tight')
    plt.close(fig)

if __name__ == '__main__':
    build(Path(__file__).resolve().parents[1])
