#!/usr/bin/env python3
"""LEGACY v1.0 FIGURES: reproduce only the first 12 budget steps from extended v1.1 data.

For current publication figures covering 1..40 use src/23_service_specific_budget_figures.py.

Publication figures using independently recomputed 89-site baseline + 1..12 NEW hypothetical sites.
No smoothing, spline, interpolation, synthetic sampling, or confidence interval claims.
"""
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import json

ROOT=Path(__file__).resolve().parents[1]
IN=ROOT/'outputs'/'sequential_investment'/'sequential_addition_trajectories.csv'
OUT=ROOT/'outputs'/'figures'/'sequential_v10';OUT.mkdir(exist_ok=True,parents=True)
rows=pd.read_csv(IN)
rows=rows.loc[rows.new_sites <= 12].copy()
assert len(rows)==5*3*2*3*4*12

SERVICE=['healthcare','elderly_care','culture']
SNAME={'healthcare':'Healthcare','elderly_care':'Elderly care','culture':'Culture'}
RULES=['network_greedy','facilities_per_10k','facilities_per_km2','facilities_per_100km_network']
RNAMES={'network_greedy':'Network-greedy reference','facilities_per_10k':'Facilities per 10,000 residents','facilities_per_km2':'Facilities per km²','facilities_per_100km_network':'Facilities per 100 km road'}
STYLE={
 'network_greedy':('#182C43','-',2.7,'o'),
 'facilities_per_10k':('#D37C30','-',1.8,'s'),
 'facilities_per_km2':('#268C87','--',1.9,'D'),
 'facilities_per_100km_network':('#9265A6',':',2.1,'^'),
}
OBJECTIVES=['district_gain_m','gain_equal_street_mean_pp']
OTITLE={'district_gain_m':'A   District-wide added network length','gain_equal_street_mean_pp':'B   Equal-street mean coverage gain'}
OUNIT={'district_gain_m':'Additional covered network (km)','gain_equal_street_mean_pp':'Mean coverage increase (pp)'}

plt.rcParams.update({'font.family':'DejaVu Sans','pdf.fonttype':42,'ps.fonttype':42,'axes.linewidth':0.9,'font.size':10,
 'axes.titlesize':11,'axes.labelsize':10,'xtick.labelsize':9,'ytick.labelsize':9})

def generate(what):
    fig,axes=plt.subplots(2,3,figsize=(15.2,8.5),sharex=True,sharey='row',constrained_layout=False)
    axes=np.asarray(axes)
    for ri,obj in enumerate(OBJECTIVES):
        for ci,svc in enumerate(SERVICE):
            ax=axes[ri,ci]
            x=np.arange(0,13)
            vals={}
            for rule in RULES:
                sub=rows[(rows.service==svc)&(rows.objective==obj)&(rows.rule==rule)&(rows.threshold_min==15)]
                g=sub.groupby('new_sites')
                if what=='gain':
                    agg=g.cumulative_gain.agg(['min','median','max']).reindex(range(1,13))
                    factor=0.001 if obj=='district_gain_m' else 1.0
                    y=np.r_[0,agg['median'].to_numpy()*factor]
                    lo=np.r_[0,agg['min'].to_numpy()*factor]
                    hi=np.r_[0,agg['max'].to_numpy()*factor]
                else:
                    agg=g.signed_shortfall_vs_greedy.agg(['min','median','max']).reindex(range(1,13))
                    factor=0.001 if obj=='district_gain_m' else 1.0
                    y=np.r_[0,agg['median'].to_numpy()*factor]
                    lo=np.r_[0,agg['min'].to_numpy()*factor]
                    hi=np.r_[0,agg['max'].to_numpy()*factor]
                color,ls,lw,marker=STYLE[rule]
                vals[rule]=y
                if what=='gap' and rule=='network_greedy':
                    continue
                # In narrow bands, light shading is enough; five scenarios are deterministic.
                if np.max(np.abs(hi-lo))>1e-5:
                    ax.fill_between(x,lo,hi,color=color,alpha=.09,linewidth=0)
                ax.plot(x,y,ls=ls,linewidth=lw,marker=marker,markersize=3.7,
                        markerfacecolor='white' if rule!='network_greedy' else color,
                        markeredgewidth=.9,color=color,zorder=4 if rule=='network_greedy' else 3)
            if what=='gap':
                ax.axhline(0,color='#777777',linewidth=.85,linestyle='-')
            ax.set_title(SNAME[svc],fontweight='bold',pad=9)
            ax.set_xlim(0,12)
            ax.set_xticks([0,2,4,6,8,10,12])
            ax.grid(axis='y',alpha=.18)
            ax.set_axisbelow(True)
            if ci==0:
                ax.set_ylabel((OUNIT[obj] if what=='gain' else ('Gain shortfall vs network greedy (km)' if ri==0 else 'Gain shortfall (pp)')))
            if ri==1:
                ax.set_xlabel('New hypothetical facilities added')
    # enforce shared y ranges by objective row (matplotlib sharey=row auto)
    handles=[]
    for rule in RULES:
        if what=='gap' and rule=='network_greedy':continue
        color,ls,lw,marker=STYLE[rule]
        handles.append(Line2D([],[],color=color,linestyle=ls,lw=lw,marker=marker,markersize=5,label=RNAMES[rule]))
    fig.legend(handles=handles,loc='lower center',ncol=len(handles),bbox_to_anchor=(.5,.064),frameon=False,fontsize=9)
    for ri,obj in enumerate(OBJECTIVES):
        axes[ri,0].text(0.0,1.15,OTITLE[obj],transform=axes[ri,0].transAxes,
                   fontsize=11,fontweight='bold',ha='left',va='bottom')
    fig.subplots_adjust(left=.075,right=.992,top=.89,bottom=.18,wspace=.19,hspace=.38)
    subtitle=('Cumulative gain from 89 existing facilities + sequential additions' if what=='gain' else
       'How much network benefit each supply-led sequence forgoes')
    fig.suptitle(subtitle,x=.5,y=.98,fontsize=15,fontweight='bold')
    fig.text(.5,.030,'15-minute network threshold · 1,132 hypothetical candidate nodes · '
                'five deterministic baseline-location scenarios (median and min–max envelopes)',
            ha='center',fontsize=9,color='#555555')
    name='01_cumulative_gain_curves' if what=='gain' else '02_gain_shortfall_vs_network_greedy'
    for ext in ('png','pdf','svg'):
        fig.savefig(OUT/(name+'.'+ext),dpi=300,bbox_inches='tight')
    plt.close(fig)


generate('gain');generate('gap')
# Supplemental: each walking threshold, district total only; prevents hiding threshold sensitivity.
fig,axs=plt.subplots(3,3,figsize=(13,10),sharex=True,sharey='row')
for r,svc in enumerate(SERVICE):
    for c,t in enumerate((5,10,15)):
        ax=axs[r,c]
        for rule in RULES:
            sub=rows[(rows.service==svc)&(rows.objective=='district_gain_m')&(rows.rule==rule)&(rows.threshold_min==t)]
            med=sub.groupby('new_sites').cumulative_gain.median().reindex(range(1,13)).to_numpy()/1000
            x=np.arange(13);y=np.r_[0,med]
            col,ls,lw,m=STYLE[rule]
            ax.plot(x,y,color=col,linestyle=ls,lw=lw,marker=m,markersize=3)
        ax.set_title(f'{t}-minute threshold' if r==0 else '')
        ax.grid(axis='y',alpha=.2);ax.set_xticks([0,3,6,9,12]);ax.set_xlim(0,12)
        if c==0:ax.set_ylabel(SNAME[svc]+'\nAdded network (km)')
        if r==2:ax.set_xlabel('New facilities added')
fig.legend(handles=[Line2D([],[],color=STYLE[p][0],linestyle=STYLE[p][1],label=RNAMES[p]) for p in RULES],
           ncol=4,loc='lower center',bbox_to_anchor=(.5,-.006),frameon=False)
fig.suptitle('Walking-time sensitivity of sequential allocation (district-length objective)',fontsize=13,y=.995)
fig.tight_layout(rect=(0,.04,1,.97))
for ext in ('png','pdf','svg'):
    fig.savefig(OUT/('03_threshold_sensitivity.'+ext),dpi=300,bbox_inches='tight')
plt.close(fig)

# Figure-to-input audit: exact underlying curve values.
groups=[]
for (svc,obj,rule,t,k),frame in rows.groupby(['service','objective','rule','threshold_min','new_sites']):
 groups.append(dict(service=svc,objective=obj,rule=rule,threshold_min=t,new_sites=k,
   scenario_n=len(frame),median_gain=frame.cumulative_gain.median(),min_gain=frame.cumulative_gain.min(),max_gain=frame.cumulative_gain.max(),
   median_shortfall_vs_greedy=frame.signed_shortfall_vs_greedy.median(),
   min_shortfall=frame.signed_shortfall_vs_greedy.min(),max_shortfall=frame.signed_shortfall_vs_greedy.max()))
pd.DataFrame(groups).to_csv(OUT/'figure_data_5_scenarios.csv',index=False)
print('FIGURES',OUT)
