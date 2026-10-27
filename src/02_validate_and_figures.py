#!/usr/bin/env python3
"""Validate model outputs and generate diagnostic figures."""
from pathlib import Path
import json,numpy as np,pandas as pd,geopandas as gpd,matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.stats import spearmanr
ROOT=Path(__file__).resolve().parents[1]
T=ROOT/'outputs/tables';F=ROOT/'outputs/figures/all_figures_png';F.mkdir(parents=True,exist_ok=True)
Q=ROOT/'data/qa'

def validate():
 snap=pd.read_csv(Q/'facility_connector_distances_full.csv')
 supp=pd.read_csv(T/'supply_verified.csv')
 cov=pd.read_csv(T/'observed_accessibility.csv')
 gain=pd.read_csv(T/'candidate_marginal_gain.csv')
 dec=pd.read_csv(T/'decision_regret.csv')
 cand=pd.read_csv(ROOT/'data/processed/hypothetical_candidate_nodes.csv')
 assert len(snap)==83
 assert supp.shape[0]==36 and cov.shape[0]==108
 assert all(supp.groupby('service').size()==12)
 assert np.isfinite(snap.snap_distance_m).all() and (snap.snap_distance_m>=0).all()
 assert (cov.network_coverage_share>=-1e-12).all() and (cov.network_coverage_share<=1+1e-12).all()
 assert (gain.district_gain_m>=-1e-7).all()
 assert (dec.decision_regret_m>=-1e-7).all()
 assert dec.groupby(['service','threshold_min']).size().eq(3).all()
 for (s,zone),d in cov.groupby(['service','subdistrict']):
  d=d.sort_values('threshold_min')
  assert (np.diff(d.network_coverage_share)>=-1e-8).all(),(s,zone)
 count60=int((snap.snap_distance_m<=60).sum());n=len(snap)
 d={'facilities_all_83_connector_cost_retained':True,'n_facilities':n,'snap_distance_median_m':round(float(snap.snap_distance_m.median()),2),
  'snap_distance_p90_m':round(float(snap.snap_distance_m.quantile(.9)),2),
  'snap_distance_p95_m':round(float(snap.snap_distance_m.quantile(.95)),2),
  'empirical_count_within_60m_posthoc':count60,'empirical_count_outside_60m_posthoc':n-count60,
  'sixty_meter_recommendation':'No empirical elbow/causal standard established; retained only as a descriptive sensitivity reference, never a base filter.',
  'n_hypothetical_sites':len(cand),'n_facility_service_cells':len(supp),
  'n_service_threshold_cells':len(cov),'n_policy_comparisons':len(dec),'accessibility_range':list(map(float,[cov.network_coverage_share.min(),cov.network_coverage_share.max()])),
  'tests':['source count agreement','monotonic time budgets','no negative gains','coverage 0..1','regret >=0','facilities no 60 m cap']}
 (Q/'validation_report.json').write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf8')
 return snap,supp,cov,dec,cand,gain,d

def summarize_grids():
 files={180:ROOT/'outputs/sensitivity/grid_180m/decision_regret.csv',240:T/'decision_regret.csv',320:ROOT/'outputs/sensitivity/grid_320m/decision_regret.csv'}
 dfs=[]
 for m,file in files.items():
  if not file.exists():continue
  d=pd.read_csv(file);d['grid_m']=m;dfs.append(d)
 if dfs:
  all_=pd.concat(dfs,ignore_index=True);all_.to_csv(T/'grid_robustness_all.csv',index=False)
  aggregate=all_.groupby(['service','threshold_min','proxy'],as_index=False).agg(
   n_grid_scales=('grid_m','nunique'),regret_fraction_min=('regret_fraction','min'),regret_fraction_max=('regret_fraction','max'),
   mean=('regret_fraction','mean'),unique_selected_subdistricts=('selected_subdistrict','nunique'))
  aggregate.to_csv(T/'grid_robustness_summary.csv',index=False)
  return all_
 return None

def main():
 snap,supp,cov,dec,cand,gain,checks=validate()
 grid=summarize_grids()
 # Figure 1: observed empirical snap distribution; 60 m shown after empirical audit, post-hoc only.
 fig,ax=plt.subplots(figsize=(7.5,4.5));a=np.sort(snap.snap_distance_m.to_numpy());y=np.arange(1,len(a)+1)/len(a)
 ax.step(a,y,where='post',lw=2,label='Empirical connector distances (n=83)')
 ax.axvline(np.median(a),linestyle='--',label=f'Median = {np.median(a):.1f} m')
 ax.axvline(60,linestyle=':',label='60 m post-hoc reference')
 ax.set(xlabel='Facility-to-network connector distance (m)',ylabel='Cumulative share of facilities',ylim=(0,1.03),xlim=(0,max(155,a.max()+10)))
 ax.legend(loc='lower right');ax.grid(alpha=.2)
 fig.tight_layout();fig.savefig(F/'01_connector_distance_empirical_cdf.png',dpi=200);plt.close(fig)
 # Figure 2: observed network coverage, same 0-100% vertical scale throughout
 fig,axes=plt.subplots(1,3,figsize=(13,4.5),sharey=True)
 for ax,(service,group) in zip(axes,cov.groupby('service',sort=True)):
  data=group.pivot(index='subdistrict',columns='threshold_min',values='network_coverage_share')
  for t in [5,10,15]:
   ys=sorted(data[t].values)
   ax.plot(np.arange(1,len(ys)+1),ys,marker='.',label=f'{t} min')
  ax.set(title=service,xlabel='Ranked subdistrict (within each curve)',ylim=(0,1),xticks=[1,4,8,12])
  ax.grid(alpha=.2)
 axes[0].set_ylabel('Pedestrian network-length coverage (share)')
 axes[-1].legend(loc='lower right');fig.suptitle('Recomputed coverage distributions: n=12 subdistricts per service')
 fig.tight_layout();fig.savefig(F/'02_accessibility_coverage_profiles.png',dpi=200);plt.close(fig)
 # Figure 3: three by three small multiples, fixed 0–1 axes and clear scenario separation
 if grid is not None:
  ss=['culture','elderly_care','healthcare'];pp=['facilities_per_10k','facilities_per_km2','facilities_per_100km_network']
  pretty=['Per 10,000 residents','Per km²','Per 100 km network']
  fig,axes=plt.subplots(3,3,figsize=(11.5,10),sharex=True,sharey=True)
  for ri,service in enumerate(ss):
   for ci,proxy in enumerate(pp):
    ax=axes[ri,ci];z=grid[(grid.service==service)&(grid.proxy==proxy)]
    for m,g in z.groupby('grid_m'):
     ax.plot(g.threshold_min,g.regret_fraction,marker='o',lw=1.7,label=f'{m} m grid')
    ax.set(ylim=(0,1),xlim=(4,16),xticks=[5,10,15]);ax.grid(alpha=.2)
    if ri==0:ax.set_title(pretty[ci])
    if ci==0:ax.set_ylabel(service.replace('_',' ')+'\nRegret (0–1)')
    if ri==2:ax.set_xlabel('Walking threshold (min)')
  axes[0,2].legend(loc='lower right',fontsize=8)
  fig.suptitle('Simulated one-site decision regret: supply policies by service, proxy and candidate grid',y=.995)
  fig.tight_layout(rect=[0,0,1,.975]);fig.savefig(F/'03_proxy_decision_regret_grid_robustness.png',dpi=200);plt.close(fig)
 # Figure 4: grade audit map for all unmatched geometric crossings within Yangpu
 edges=gpd.read_file(ROOT/'data/processed/p06_rebuilt_network.gpkg',layer='osm_node_identity_edges')
 bound=gpd.read_file(ROOT/'data/processed/p06_rebuilt_network.gpkg',layer='study_subdistricts')
 audit=pd.read_csv(Q/'unshared_crossings_district.csv')
 fig,ax=plt.subplots(figsize=(7.5,8.5))
 edges[edges.zone>=0].plot(ax=ax,linewidth=.35,alpha=.7)
 bound.boundary.plot(ax=ax,linewidth=.8)
 xy=[]
 district_edges=edges[edges.zone>=0].reset_index(drop=True)
 for row in audit.itertuples():
  p=district_edges.geometry.iloc[row.edge_i].intersection(district_edges.geometry.iloc[row.edge_j])
  if p.geom_type=='Point':xy.append((p.x,p.y,row.tagged_grade_separated))
 if xy:
  x,y,z=zip(*xy)
  ax.scatter([xx for xx,t in zip(x,z) if t],[yy for yy,t in zip(y,z) if t],s=15,marker='x',label='Grade-tagged unshared crossing')
  ax.scatter([xx for xx,t in zip(x,z) if not t],[yy for yy,t in zip(y,z) if not t],s=55,marker='o',facecolors='none',edgecolors='black',label='At-grade unshared crossing: inspect')
 ax.set(title='OSM-node topology crossing QA · Yangpu',xlabel='UTM zone 51N easting (m)',ylabel='UTM zone 51N northing (m)');ax.set_aspect('equal');ax.legend(fontsize=8)
 fig.tight_layout();fig.savefig(F/'04_unshared_crossings_network_qa.png',dpi=180);plt.close(fig)
 print(json.dumps(checks,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
