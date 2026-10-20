#!/usr/bin/env python3
"""Separate landscape 3-panel paper-scale figures; full six-panel plate stays on GitHub."""
from pathlib import Path
import pandas as pd, numpy as np
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'outputs/sequential_investment/sequential_addition_trajectories.csv'
OUT=ROOT/'outputs/figures/sequential_v10'
d=pd.read_csv(DATA)
SERVICES=['healthcare','elderly_care','culture']
RULES=['network_greedy','facilities_per_10k','facilities_per_km2','facilities_per_100km_network']
ST={'network_greedy':('#182C43','-',2.6,'o'),'facilities_per_10k':('#D37C30','-',1.8,'s'),
'facilities_per_km2':('#268C87','--',1.9,'D'),'facilities_per_100km_network':('#9265A6',':',2.1,'^')}
LAB={'network_greedy':'Network greedy','facilities_per_10k':'Per 10,000 residents','facilities_per_km2':'Per km²','facilities_per_100km_network':'Per 100 km road'}
for obj,label,unit,factor,key in [
 ('district_gain_m','District-wide benefit','Added covered network (km)',.001,'04_paper_district_cumulative'),
 ('gain_equal_street_mean_pp','Equal-street mean benefit','Mean coverage gain (pp)',1.0,'05_paper_equalstreet_cumulative')]:
 fig,axes=plt.subplots(1,3,figsize=(12.8,4.2),sharex=True,sharey=True)
 for si,service in enumerate(SERVICES):
  ax=axes[si]
  for rule in RULES:
   x=d[(d.service==service)&(d.objective==obj)&(d.rule==rule)&(d.threshold_min==15)]
   ag=x.groupby('new_sites').cumulative_gain.agg(['min','median','max']).reindex(range(1,13))
   ticks=np.arange(13);med=np.r_[0,ag['median'].to_numpy()*factor]
   lo=np.r_[0,ag['min'].to_numpy()*factor];hi=np.r_[0,ag['max'].to_numpy()*factor]
   color,ls,lw,marker=ST[rule]
   if np.max(hi-lo)>1e-5:ax.fill_between(ticks,lo,hi,color=color,alpha=.1,lw=0)
   ax.plot(ticks,med,color=color,linestyle=ls,lw=lw,marker=marker,markersize=3,markerfacecolor='white' if rule!='network_greedy' else color)
  ax.set_title({'healthcare':'Healthcare','elderly_care':'Elderly care','culture':'Culture'}[service],fontsize=11,weight='bold')
  ax.set_xlim(0,12);ax.set_xticks([0,2,4,6,8,10,12]);ax.grid(axis='y',alpha=.2)
  ax.set_xlabel('New facilities added')
 axes[0].set_ylabel(unit)
 h=[Line2D([],[],color=ST[rule][0],ls=ST[rule][1],lw=ST[rule][2],marker=ST[rule][3],markersize=4,label=LAB[rule]) for rule in RULES]
 fig.legend(handles=h,loc='lower center',ncol=4,bbox_to_anchor=(.5,.06),frameon=False,fontsize=9)
 fig.suptitle(label+' · 15-minute walking threshold',fontsize=13,y=.99)
 fig.subplots_adjust(left=.078,right=.99,top=.79,bottom=.28,wspace=.19)
 fig.text(.5,.015,'Five deterministic existing-location scenarios; bands denote the scenario range.',ha='center',fontsize=9,color='#555555')
 for ext in ('png','pdf','svg'):
  fig.savefig(OUT/(key+'.'+ext),dpi=300,bbox_inches='tight')
 plt.close(fig)
print('paper panels ready')
