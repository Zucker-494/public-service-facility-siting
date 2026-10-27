#!/usr/bin/env python3
"""Plot pedestrian network sensitivity and coverage results."""
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'outputs/figures/all_figures_png'
OUT.mkdir(parents=True, exist_ok=True)
ROBUST = ROOT / 'outputs/walkability_robustness'
TAG = ROOT / 'outputs/publication_gate/pedestrian_access_source_tag_quality_by_class.csv'
SERVICES = ['healthcare', 'elderly_care', 'culture']
SERVICE_NAMES = ['Healthcare', 'Elderly care', 'Culture']
RULES = ['network_greedy','facilities_per_10k','facilities_per_km2','facilities_per_100km_network']
RULE_LABELS = ['Greedy','Per 10k residents','Per km²','Per 100km road']
STYLES = [('tab:blue','-'),('tab:orange','--'),('tab:green','--'),('tab:red',':')]
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.grid':True,'grid.alpha':0.17})


def evidence_figure():
    df = pd.read_csv(TAG)
    lookup = {
        'included_nonpedestrian_class_individual_access_unverified': 'Other road classes: walking permission unverified',
        'higher_order_pedestrian_tags_not_explicit': 'Higher-order roads: no explicit walking tags',
        'pedestrian_designated_class': 'Pedestrian-designated class',
    }
    df['label'] = df.review_class.map(lookup)
    if df.label.isna().any():
        raise ValueError('Unrecognised pedestrian access category: '+str(df.loc[df.label.isna(),'review_class'].tolist()))
    df = df.sort_values('pct_length',ascending=True)
    fig,ax=plt.subplots(figsize=(11.4,4.0))
    bars=ax.barh(df.label,df.pct_length,color='#277ba9',height=.57)
    ax.set_xlim(0,100)
    ax.set_xlabel('Share of modelled district network length (%)')
    ax.grid(axis='y',visible=False)
    for b,v in zip(bars,df.pct_length):
        ax.text(float(v)+1,b.get_y()+b.get_height()/2,f'{v:.1f}%',va='center',fontsize=9)
    fig.tight_layout()
    fig.savefig(OUT/'source_network_walkability_tag_evidence.png',dpi=200,bbox_inches='tight')
    plt.close(fig)


def network_comparison():
    df = pd.read_csv(ROBUST/'walkability_robustness_14400_rows.csv')
    df = df[(df.threshold_min == 15)&(df.objective == 'district_gain_m')]
    fig,axes=plt.subplots(2,3,figsize=(14.2,8.1),sharex=True)
    for row,(network,field) in enumerate([('original','cumulative_gain_original'),('strict','cumulative_gain_strict')]):
        for col,service in enumerate(SERVICES):
            ax=axes[row,col]
            subset=df[df.service == service]
            for rule,(color,linestyle),label in zip(RULES,STYLES,RULE_LABELS):
                d=subset[subset.rule == rule].groupby('new_sites')[field].median().sort_index()
                if len(d)!=40:
                    raise ValueError(f'Expected 40 steps: {service}, {rule}, {network}')
                ax.plot(np.r_[0,d.index.to_numpy()], np.r_[0,d.to_numpy()/1000],
                        color=color,linestyle=linestyle,linewidth=1.8,label=label)
            ax.set_title(f'{SERVICE_NAMES[col]} | {"Original" if row==0 else "Restricted"} network',fontsize=10)
            ax.set_xlim(0,40)
            ax.set_ylim(bottom=0)
            if col==0:ax.set_ylabel('Additional covered network (km)')
            if row==1:ax.set_xlabel('Newly added sites')
    handles,labels=axes[0,0].get_legend_handles_labels()
    fig.legend(handles,labels,ncol=4,loc='lower center',bbox_to_anchor=(.5,-.007),frameon=False)
    fig.tight_layout(rect=(0,.045,1,1))
    fig.savefig(OUT/'walkability_comparison.png',dpi=200,bbox_inches='tight')
    plt.close(fig)


def network_loss():
    # The historical figure compares ORIGINAL versus STRICT at the 12-site budget.
    df = pd.read_csv(ROBUST/'walkability_policy_comparison_summary.csv')
    df = df[(df.objective == 'district_gain_m') & (df.new_sites == 12)]
    rules=RULES[1:]
    fig,axes=plt.subplots(1,3,figsize=(13.6,4.9),sharey=True)
    for ax,service,title in zip(axes,SERVICES,SERVICE_NAMES):
        d=df[(df.service == service) & (df.rule.isin(rules))]
        for idx,rule in enumerate(rules):
            vals=[]
            for network in ('original','strict'):
                sel=d[(d.rule==rule)&(d.network==network)]
                if len(sel)!=1:raise ValueError(f'Missing result: {service}/{rule}/{network}/12')
                vals.append(float(sel.loss_pct_median.iloc[0]))
            color=['tab:blue','tab:orange','tab:green'][idx]
            x=np.array([idx*3,idx*3+0.75])
            ax.plot(x, vals, color=color, linewidth=1.3, zorder=2)
            ax.scatter(x, vals, color=color, marker='o', s=30, zorder=3)
        ax.set_xticks([.375,3.375,6.375],['Per 10k','Per km²','Per road'],rotation=10)
        ax.set_title(title)
        ax.set_xlim(-.5,7.5)
        ax.set_ylim(bottom=0)
        ax.grid(axis='x',visible=False)
    axes[0].set_ylabel('Shortfall vs same-network greedy (%)')
    fig.text(.5,.015,'Within each rule, left = original network and right = restricted network; 12 added facilities, 15-minute threshold',
             ha='center',fontsize=9,color='#4b5563')
    fig.tight_layout(rect=(0,.06,1,1))
    fig.savefig(OUT/'walkability_loss_comparison.png',dpi=200,bbox_inches='tight')
    plt.close(fig)


if __name__ == '__main__':
    evidence_figure()
    network_comparison()
    network_loss()
    print('Created three PNG figures in:', OUT)
