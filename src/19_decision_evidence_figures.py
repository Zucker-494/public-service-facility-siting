#!/usr/bin/env python3
"""Reproducible decision-evidence figures. Uses the 270 independently checked policy rows.

Inputs are prior computed outputs. No facility/location/network recalculation occurs.
Five deterministic scenarios are ranges, never confidence intervals.
"""
from pathlib import Path
import argparse
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib import ticker
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

SERVICE=['healthcare','elderly_care','culture']
SLABEL={'healthcare':'Healthcare','elderly_care':'Elderly care','culture':'Culture'}
PKEY=['facilities_per_10k','facilities_per_km2','facilities_per_100km_network']
PLABEL=['Facilities / 10,000 residents','Facilities / km²','Facilities / 100 km network']
OBJECTIVES=['district_gain_m','gain_equal_street_mean_pp']
OLABEL=['District-wide network gain','Equal-street coverage gain']
TIME=[5,10,15]
ROMAN={'殷行街道':'Yinhang','新江湾城街道':'Xinjiangwancheng','延吉新村街道':'Yanji Xincun','江浦路街道':'Jiangpu Road','长白新村街道':'Changbai Xincun','长海路街道':'Changhai Road','控江路街道':'Kongjiang Road','五角场街道':'Wujiaochang','定海路街道':'Dinghai Road','大桥街道':'Daqiao','四平路街道':'Siping Road','平凉路街道':'Pingliang Road'}


def roman(s):
    return ROMAN.get(str(s),str(s))


def save(fig,path):
    path.parent.mkdir(parents=True,exist_ok=True)
    fig.savefig(path.with_suffix('.png'),dpi=260,bbox_inches='tight',facecolor='white')
    fig.savefig(path.with_suffix('.pdf'),bbox_inches='tight',facecolor='white')
    plt.close(fig)


def load(root):
    f=root/'outputs/publication_gate/official_89_scenario_policy_independent_recalculation.csv'
    a=pd.read_csv(f,encoding='utf-8-sig')
    assert len(a)==270
    expected=pd.MultiIndex.from_product([a.scenario.unique(),SERVICE,TIME,OBJECTIVES,PKEY],names=['scenario','service','threshold_min','objective','proxy'])
    idx=a.set_index(expected.names).sort_index()
    assert idx.index.is_unique and len(idx)==len(expected) and idx.index.equals(expected.sort_values())
    assert np.allclose(a.total_regret_fraction,a.street_regret_fraction+a.within_street_regret_fraction,atol=1e-9)
    return a


def figure_choices(a,figdir):
    # A selected street is invariant across scenario, time, and objective for each category/metric.
    df=a.groupby(['service','proxy']).selected_streets.agg(lambda v: sorted(v.unique())).reset_index()
    assert df.selected_streets.apply(len).eq(1).all()
    cdict={(r.service,r.proxy):roman(r.selected_streets[0]) for r in df.itertuples(index=False)}
    fig,ax=plt.subplots(figsize=(11.6,4.0),layout='constrained')
    fig.set_facecolor('white')
    ax.set_xlim(-.45,2.55);ax.set_ylim(2.65,-.5)
    ax.set_xticks(range(3),PLABEL,fontsize=11)
    ax.xaxis.tick_top()
    ax.set_yticks(range(3),[SLABEL[s] for s in SERVICE],fontsize=11)
    ax.tick_params(axis='both',length=0,pad=14)
    for sidx,service in enumerate(SERVICE):
        for pidx,proxy in enumerate(PKEY):
            name=cdict[(service,proxy)]
            ax.text(pidx,sidx,name,ha='center',va='center',fontsize=11,weight='semibold' if pidx==2 else 'normal')
            ax.plot([pidx-.42,pidx+.42],[sidx+.43,sidx+.43],lw=.6,alpha=.25)
    # highlight road-based choices where they differ
    for y,service in enumerate(SERVICE):
        if cdict[(service,PKEY[0])]!=cdict[(service,PKEY[2])]:
            ax.plot([1.58,2.42],[y+.27,y+.27],lw=2.0,color='C0',solid_capstyle='round')
    ax.spines[:].set_visible(False)
    ax.set_title('Which street does each supply proxy select?',fontsize=13,pad=36,loc='left')
    fig.text(.5,.01,'Population-rate and area-density rules agree for all services; blue underline marks a different street recommendation.',ha='center',fontsize=9)
    save(fig,figdir/'01_proxy_recommendation_agreement')
    return cdict


def figure_incremental_regret(a,figdir):
    keys=['scenario','service','threshold_min','objective']
    p=a.pivot(index=keys,columns='proxy',values='total_regret_fraction').reset_index()
    assert np.allclose(p[PKEY[0]],p[PKEY[1]],atol=1e-12)  # exact decision equivalence
    p['delta_pp']=(p[PKEY[2]]-p[PKEY[0]])*100
    fig,axes=plt.subplots(3,2,figsize=(11.5,8.2),sharex=True,sharey=True,layout='constrained')
    fig.set_facecolor('white')
    for r,service in enumerate(SERVICE):
        for c,obj in enumerate(OBJECTIVES):
            ax=axes[r,c]
            ss=p[(p.service==service)&(p.objective==obj)]
            xx=[]; yy=[]
            for t in TIME:
                values=ss[ss.threshold_min==t].sort_values('scenario').delta_pp.to_numpy()
                assert len(values)==5
                # Five deterministic values drawn at same threshold with small visual-only horizontal offset
                xx += list(t+np.linspace(-.36,.36,5))
                yy += list(values)
                ax.plot([t,t],[values.min(),values.max()],lw=3,alpha=.65,color='C0')
                ax.scatter([t], [np.median(values)], s=63,marker='D',facecolor='black',edgecolor='white',linewidth=.6,zorder=5)
            ax.scatter(xx,yy,marker='o',s=23,alpha=.72,color='C0',zorder=4)
            ax.axhline(0,lw=1.1,color='.35',linestyle='--')
            ax.set_xticks(TIME)
            ax.set_xlim(3,17)
            ax.set_ylim(-8.2,3.4)
            ax.grid(axis='y',alpha=.18)
            for side in ['top','right']:ax.spines[side].set_visible(False)
            if r==0:ax.set_title(OLABEL[c],fontsize=11)
            if c==0:ax.set_ylabel(SLABEL[service]+'\nChange in regret (pp)',fontsize=10)
            if r==2:ax.set_xlabel('Walking-time threshold (minutes)')
            if service=='elderly_care':
                ax.text(10,-5.5,'Identical priority street\nΔ regret = 0',ha='center',fontsize=9,color='.42')
    fig.suptitle('Network-density rule relative to population/area-density rules',fontsize=14)
    fig.text(.5,-.025,'Δ = regret(network density) − regret(population or area density). Negative = lower loss with network density.\nFive deterministic location scenarios shown as dots; diamonds = medians; bars = min–max. No confidence intervals.',
             ha='center',va='top',fontsize=9)
    save(fig,figdir/'02_incremental_decision_regret')
    return p


def figure_objective_switch(root,figdir):
    df=pd.read_csv(root/'manuscript/objective_changes_five_scenarios.csv')
    assert len(df)==45 and int(df.changed.sum())==40
    fig,axes=plt.subplots(3,3,figsize=(13.0,8.5),sharex=True,sharey=True,layout='constrained')
    fig.set_facecolor('white')
    for r,service in enumerate(SERVICE):
        for c,t in enumerate(TIME):
            ax=axes[r,c];ss=df[(df.service==service)&(df.threshold_min==t)]
            assert len(ss)==5
            dist=ss.best_district_street.value_counts();equal=ss.best_equal_street.value_counts()
            nchange=int(ss.changed.sum())
            def display(vals):
                entries=[f'{roman(st)} ({num}/5)' for st,num in vals.items()]
                return '\n'.join(entries)
            ax.text(.07,.83,'District-wide',transform=ax.transAxes,fontsize=9,color='.4')
            ax.text(.07,.67,display(dist),transform=ax.transAxes,fontsize=10,weight='medium',va='top')
            ax.text(.07,.39,'Equal-street',transform=ax.transAxes,fontsize=9,color='.4')
            ax.text(.07,.23,display(equal),transform=ax.transAxes,fontsize=10,weight='medium',va='top')
            ax.text(.94,.07,f'{nchange}/5 changed',transform=ax.transAxes,ha='right',fontsize=9,
                    fontweight='bold' if nchange else 'normal',color='C0' if nchange else '.40')
            ax.set_xlim(0,1);ax.set_ylim(0,1);ax.set_xticks([]);ax.set_yticks([])
            for spine in ax.spines.values():spine.set_alpha(.17)
            if r==0:ax.set_title(f'{t}-minute',fontsize=11)
            if c==0:ax.set_ylabel(SLABEL[service],fontsize=11,labelpad=9)
    fig.suptitle('Planning objective changes the optimal street in 40 of 45 scenarios',fontsize=14)
    fig.text(.5,-.025,'Counts indicate the number of deterministic missing-site scenarios selecting each street.\nSame network and candidate set; only the planning objective differs.',ha='center',va='top',fontsize=9)
    save(fig,figdir/'03_objective_sensitivity_optimal_street')


def figure_components(a,figdir):
    fig,axes=plt.subplots(3,2,figsize=(11.5,8.1),sharex=True,sharey=True)
    fig.subplots_adjust(left=.10,right=.985,bottom=.19,top=.905,hspace=.18,wspace=.09)
    fig.set_facecolor('white')
    # Retain two unique decision rules: population/area pooled, network density
    rule=[PKEY[0],PKEY[2]]
    for r,service in enumerate(SERVICE):
        for c,obj in enumerate(OBJECTIVES):
            ax=axes[r,c]
            for tt,t in enumerate(TIME):
                for j,p in enumerate(rule):
                    ss=a[(a.service==service)&(a.objective==obj)&(a.threshold_min==t)&(a.proxy==p)]
                    street=np.median(ss.street_regret_fraction)
                    total=np.median(ss.total_regret_fraction)
                    local=total-street
                    xx=tt+(-.17 if j==0 else .17)
                    ax.bar(xx,street,width=.30,color='C0',edgecolor='white',lw=.4)
                    ax.bar(xx,local,bottom=street,width=.30,color='C1',edgecolor='white',lw=.4)
                    if j==1:
                        # A hatch distinguishes network-rule bars without consuming a third color
                        ax.bar(xx,total,width=.30,color='none',edgecolor='.35',lw=.8,hatch='//')
            ax.set_xticks(range(3),[f'{t} min' for t in TIME]);ax.set_ylim(0,1)
            ax.grid(axis='y',alpha=.17);ax.set_axisbelow(True)
            for spine in ['top','right']:ax.spines[spine].set_visible(False)
            if r==0:ax.set_title(OLABEL[c])
            if c==0:ax.set_ylabel(SLABEL[service]+'\nNormalized regret')
    fig.suptitle('Where does decision regret arise? Two-stage decomposition',fontsize=14,y=.975)
    fig.legend(handles=[Patch(facecolor='C0',label='Street-selection loss'),Patch(facecolor='C1',label='Within-street siting loss'),Patch(facecolor='white',edgecolor='.35',hatch='//',label='Network-density rule; plain = population/area rule')],
               loc='lower center',bbox_to_anchor=(.5,.105),ncol=3,frameon=False,fontsize=9)
    fig.text(.5,.050,'Each bar equals the median total regret; within-street segment = median total − median street loss.',ha='center',fontsize=9)
    save(fig,figdir/'04_regret_decomposition')


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1])
    args=ap.parse_args()
    root=args.root
    figdir=root/'outputs/figures/decision_evidence_v091'
    figdir.mkdir(parents=True,exist_ok=True)
    data=load(root)
    choices=figure_choices(data,figdir)
    delta=figure_incremental_regret(data,figdir)
    figure_objective_switch(root,figdir)
    figure_components(data,figdir)
    print('figures:',figdir)
    print('proxy equivalence: population vs area (90/90)')
    print('road vs population nonzero:',int((delta.delta_pp.abs()>1e-8).sum()),'of',len(delta))

if __name__=='__main__':main()
