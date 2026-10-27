#!/usr/bin/env python3
"""Validate spatial outputs and generate manuscript figures."""
from pathlib import Path
import argparse
import json
import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'outputs/refined_model';FIG=ROOT/'outputs/figures/all_figures_png';FIG.mkdir(parents=True,exist_ok=True)


def save(name):
 plt.savefig(FIG/(name+'.png'),dpi=200,bbox_inches='tight')
 plt.close()


def clean_gpkg():
 old=ROOT/'data/processed/p06_rebuilt_network.gpkg'
 new=ROOT/'data/processed/p06_refined_clean.gpkg'
 if new.exists():new.unlink()
 edges=gpd.read_file(old,layer='osm_node_identity_edges')
 bounds=gpd.read_file(old,layer='study_subdistricts')
 fac=gpd.read_file(old,layer='verified_facilities')
 # All repetitions must match in sequence AND exact geometry; never silently drop differences.
 def one_batch(layer,size):
  assert len(layer)%size==0
  ref=layer.iloc[:size].reset_index(drop=True)
  for k in range(1,len(layer)//size):
   a=layer.iloc[k*size:(k+1)*size].reset_index(drop=True)
   assert ref.geometry.geom_equals_exact(a.geometry,1e-7).all()
   for field in [col for col in ref.columns if col!='geometry']:
    assert (ref[field].fillna('MISSING').values==a[field].fillna('MISSING').values).all()
  return ref
 bounds=one_batch(bounds,12);fac=one_batch(fac,83)
 candidates=pd.read_csv(BASE/'grid_240m/hypothetical_candidate_nodes_validated.csv')
 assert candidates.candidate_node.nunique()==len(candidates)
 cand=gpd.GeoDataFrame(candidates,geometry=gpd.points_from_xy(candidates.x,candidates.y),crs=edges.crs)
 fac=fac.rename(columns={'zone':'subdistrict_index'})
 fac['coordinate_status']='inherited_geocode_pending_independent_spatial_confirmation'
 # Use writer with new path, then add uniquely named layers. Existing layer never appended.
 edges.to_file(new,layer='osm_node_identity_edges',driver='GPKG')
 bounds.to_file(new,layer='study_subdistricts',driver='GPKG')
 fac.to_file(new,layer='facility_inherited_coordinates',driver='GPKG')
 cand.to_file(new,layer='hypothetical_candidate_nodes_240m',driver='GPKG')
 spec=gpd.list_layers(new)
 assert len(spec)==4,spec
 assert len(gpd.read_file(new,layer='study_subdistricts'))==12
 assert len(gpd.read_file(new,layer='facility_inherited_coordinates'))==83
 assert len(gpd.read_file(new,layer='hypothetical_candidate_nodes_240m'))==len(candidates)
 return {'clean_spatial_db':str(new.relative_to(ROOT)),'layers':[dict(layer=row['name'],count=len(gpd.read_file(new,layer=row['name']))) for _,row in spec.iterrows()]}


def figures():
 all_=pd.read_csv(BASE/'policy_robustness_all_grids.csv')
 main=all_[all_.grid_m.eq(240)]
 services=['healthcare','elderly_care','culture'];times=[5,10,15]
 legend_proxy={'facilities_per_10k':'Population rate','facilities_per_km2':'Area density','facilities_per_100km_network':'Network density'}
 colors=['C0','C1','C2']
 # 05: separate street choice from local site placement, same y-axis across all services.
 fig,ax=plt.subplots(3,1,figsize=(12,9),sharex=True,sharey=True,layout='constrained')
 for i,service in enumerate(services):
  a=ax[i];sub=main[main.service==service]
  for p,proxy in enumerate(legend_proxy):
   tmp=sub[sub.proxy==proxy].set_index('threshold_min').loc[times]
   x=np.arange(3)+(p-1)*.23
   a.bar(x,tmp.street_choice_regret_fraction,width=.21,label='Street choice' if i==0 and p==0 else None,color='C0',edgecolor='white',linewidth=.5)
   a.bar(x,tmp.within_street_siting_regret_fraction,bottom=tmp.street_choice_regret_fraction,width=.21,
         label='Within-street siting' if i==0 and p==0 else None,color='C1',edgecolor='white',linewidth=.5)
  a.set_title(service.replace('_',' ').title(),loc='left',fontsize=10)
  a.set_ylim(0,1);a.set_ylabel('Regret / oracle gain')
  a.grid(axis='y',alpha=.2)
 ax[0].legend(ncol=2,loc='upper right')
 ticks=[j+(p-1)*.23 for j in range(3) for p in range(3)]
 ax[2].set_xticks(ticks,[f'{t}m\n{pr}' for t in times for pr in ['Pop','Area','Road']],fontsize=8)
 fig.suptitle('Policy regret: street choice versus hypothetical local siting (240 m)',fontsize=12)
 save('05_tie_aware_regret_decomposition')
 # 06: criterion sensitivity. Compare same policy under three objective definitions.
 obj=pd.read_csv(BASE/'objective_sensitivity_all.csv');obj=obj[obj.grid_m.eq(240)]
 fig,ax=plt.subplots(3,1,figsize=(12,9),sharey=True,layout='constrained')
 objective_keys=['absolute_network_length','equal_street_percentage_point_gain','target_street_percentage_point_gain']
 lab=['District total length','Equal-street mean coverage','Local street coverage']
 for i,service in enumerate(services):
  a=ax[i];z=obj[obj.service==service]
  xx=np.arange(9)
  for j,o in enumerate(objective_keys):
   vals=[]
   for t in times:
    for proxy in legend_proxy:
     vals.append(float(z[(z.threshold_min==t)&z.proxy.eq(proxy)&z.objective.eq(o)].normalized_regret.iloc[0]))
   a.bar(xx+(j-1)*.25,vals,width=.24,label=lab[j] if i==0 else None)
  a.set_ylim(0,1);a.set_ylabel('Regret / oracle gain');a.grid(axis='y',alpha=.2)
  a.set_title(service.replace('_',' ').title(),loc='left',fontsize=10)
  a.set_xticks(xx,[f'{t}m\n{p}' for t in times for p in ['Pop','Area','Road']],fontsize=8)
 ax[0].legend(ncol=3,loc='upper right',fontsize=9)
 fig.suptitle('Decision-regret sensitivity to the objective function (240 m)',fontsize=12)
 save('06_objective_definition_sensitivity')
 # 07: same estimate across candidate grid sizes (3 scenarios; no CI).
 fig,axs=plt.subplots(3,1,figsize=(10,8),sharex=True,sharey=True,layout='constrained')
 for i,service in enumerate(services):
  a=axs[i];sub=all_[all_.service==service]
  for p,proxy in enumerate(legend_proxy):
   for t in times:
    v=sub[(sub.proxy==proxy)&(sub.threshold_min==t)].sort_values('grid_m')
    a.plot(v.grid_m,v.regret_fraction,marker=['o','s','^'][p],linestyle=['-','--',':'][t//5-1],alpha=.82,
           label=f'{legend_proxy[proxy]}, {t}min' if i==0 else None)
  a.set_ylim(0,1);a.set_ylabel('Regret / oracle gain');a.set_title(service.replace('_',' ').title(),loc='left',fontsize=10)
  a.grid(alpha=.2)
 axs[0].legend(ncol=3,fontsize=7,loc='upper right')
 axs[-1].set_xticks([180,240,320]);axs[-1].set_xlabel('Hypothetical candidate lattice spacing (m)')
 fig.suptitle('Finite-candidate discretization sensitivity (three exact enumerations)',fontsize=12)
 save('07_corrected_candidate_grid_sensitivity')
 # 08: accepted vs official completeness by service: counts as actual values.
 audit=pd.read_csv(ROOT/'data/qa/supply_inventory_vs_spatial_analysis.csv')
 fig,ax=plt.subplots(figsize=(12,5),layout='constrained')
 count=audit.groupby('service')[['source_inventory_count','count_verified']].sum().reindex(services)
 x=np.arange(len(services))
 ax.bar(x-.18,count.source_inventory_count,width=.34,label='Official inventory')
 ax.bar(x+.18,count.count_verified,width=.34,label='Coordinate-included subset')
 ax.set_xticks(x,['Healthcare','Elderly care','Culture']);ax.set_ylabel('Facilities');ax.legend();ax.grid(axis='y',alpha=.2)
 ax.set_title('Official facility inventory and inherited coordinate coverage',loc='left',fontsize=12)
 save('08_facility_coordinate_completeness')
 return sorted(x.name for x in FIG.iterdir())


def main():
 parser=argparse.ArgumentParser(description='Generate publication QA figures from existing analytical outputs.')
 parser.add_argument('--rebuild-spatial-db',action='store_true',help='Explicitly reconstruct the processed GeoPackage before drawing figures.')
 args=parser.parse_args()
 database=clean_gpkg() if args.rebuild_spatial_db else None
 imgs=figures()
 qa={'figures':imgs}
 if database is not None:
  qa['database']=database
  (ROOT/'data/qa/v04_clean_delivery_audit.json').write_text(json.dumps(qa,ensure_ascii=False,indent=2),encoding='utf8')
 print(json.dumps(qa,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
