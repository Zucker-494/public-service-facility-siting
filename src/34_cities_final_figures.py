#!/usr/bin/env python3
from pathlib import Path
import json
import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
from matplotlib.lines import Line2D

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'manuscript' / 'cities' / 'figures'
OUT.mkdir(parents=True, exist_ok=True)
SEQ = ROOT / 'outputs' / 'sequential_investment'
ROB = ROOT / 'outputs' / 'walkability_robustness'

COL = {
    'greedy':'#263746',
    'per_10k':'#D98C3F',
    'per_km2':'#2A9D8F',
    'per_100km':'#7B61A8',
    'healthcare':'#3B82A0',
    'elderly_care':'#C26A5A',
    'culture':'#6A8E3A',
    'district':'#2F6B8A',
    'equal':'#B55D4C',
}
plt.rcParams.update({
    'font.family':'DejaVu Sans', 'font.size':9.5, 'axes.titlesize':10.5,
    'axes.labelsize':9.5, 'xtick.labelsize':8.5, 'ytick.labelsize':8.5,
    'legend.fontsize':8.3, 'axes.spines.top':False, 'axes.spines.right':False,
    'axes.linewidth':0.8, 'grid.color':'#D7DBDF', 'grid.alpha':0.55,
    'grid.linewidth':0.6, 'pdf.fonttype':42, 'ps.fonttype':42,
})

PROXY = ['per_10k','per_km2','per_100km']
PROXY_RULE = ['facilities_per_10k','facilities_per_km2','facilities_per_100km_network']
PLAB = {'per_10k':'Per 10,000 residents','per_km2':'Per km²','per_100km':'Per 100 km roads',
        'facilities_per_10k':'Per 10,000 residents','facilities_per_km2':'Per km²','facilities_per_100km_network':'Per 100 km roads'}
SLAB = {'healthcare':'Healthcare','elderly_care':'Elderly care','culture':'Cultural facilities'}
OLAB = {'district':'District-wide coverage','equal':'Equal-subdistrict coverage',
        'district_gain_m':'District-wide coverage','gain_equal_street_mean_pp':'Equal-subdistrict coverage'}

def save(fig, name):
    fig.savefig(OUT/f'{name}.png', dpi=320, bbox_inches='tight', facecolor='white')
    fig.savefig(OUT/f'{name}.pdf', bbox_inches='tight', facecolor='white')
    plt.close(fig)

def panel(ax, s):
    ax.text(-0.10, 1.04, s, transform=ax.transAxes, fontsize=11.5, fontweight='bold', va='bottom')

def attach_zones_to_boundaries(bound, cand):
    """Attach candidate-zone IDs to boundary polygons using candidate points."""
    if 'zone' in bound.columns:
        out=bound.copy()
        out['zone']=out['zone'].astype(int)
        return out
    pts=gpd.GeoDataFrame(cand[['zone']].copy(), geometry=gpd.points_from_xy(cand.x,cand.y), crs=bound.crs)
    bb=bound.reset_index(drop=True).reset_index().rename(columns={'index':'poly_idx'})
    joined=gpd.sjoin(pts, bb[['poly_idx','geometry']], predicate='within', how='left')
    mapped=joined.dropna(subset=['poly_idx']).copy()
    mapping=mapped.groupby('poly_idx').zone.agg(lambda x: int(x.mode().iloc[0]))
    out=bb.set_index('poly_idx').copy()
    out['zone']=out.index.map(mapping)
    expected=int(cand.zone.nunique())
    if out.zone.isna().any() or int(out.zone.nunique()) != expected:
        raise ValueError(f'Could not map all study boundaries to candidate zones: mapped={out.zone.nunique()}, expected={expected}')
    out['zone']=out.zone.astype(int)
    return out.reset_index(drop=True)

def fig1_study_framework():
    gpkg = ROOT/'data/processed/p06_refined_clean.gpkg'
    bound = gpd.read_file(gpkg, layer='study_subdistricts')
    edges = gpd.read_file(gpkg, layer='osm_node_identity_edges')
    edges = edges[edges['zone'] >= 0]
    cand = pd.read_csv(ROOT/'data/processed/hypothetical_candidate_nodes.csv', encoding='utf-8-sig')
    bound = attach_zones_to_boundaries(bound, cand)
    reg = pd.read_csv(ROOT/'data/curated/official_facility_registry_89_address_audited.csv', encoding='utf-8-sig')
    reg = reg[reg.wgs84_lon.notna() & reg.wgs84_lat.notna()].copy()
    fac = gpd.GeoDataFrame(reg, geometry=gpd.points_from_xy(reg.wgs84_lon, reg.wgs84_lat), crs='EPSG:4326').to_crs(edges.crs)
    cg = gpd.GeoDataFrame(cand, geometry=gpd.points_from_xy(cand.x,cand.y), crs=edges.crs)

    fig, axes = plt.subplots(1,2,figsize=(12.2,5.4), layout='constrained')
    ax=axes[0]
    bound.plot(ax=ax, facecolor='#F5F2EA', edgecolor='#666666', linewidth=0.8)
    edges.plot(ax=ax, color='#B8BEC4', linewidth=0.32, alpha=0.75)
    cg.plot(ax=ax, color='#7AA6B8', markersize=2.1, alpha=0.42, label='1,132 candidate sites')
    markers={'healthcare':'o','elderly_care':'^','culture':'s'}
    for svc in ['healthcare','elderly_care','culture']:
        q=fac[fac.facility_type==svc]
        q.plot(ax=ax,color=COL[svc],marker=markers[svc],markersize=23,edgecolor='white',linewidth=.4,label=f'{SLAB[svc]} ({len(q)} mapped)')
    zone_name=cand[['zone','subdistrict_en']].drop_duplicates().set_index('zone').subdistrict_en.to_dict()
    for r in bound.itertuples():
        z=getattr(r,'zone',None)
        if z in zone_name:
            p=r.geometry.representative_point()
            ax.text(p.x,p.y,zone_name[z].replace(' Subdistrict',''),fontsize=6.4,ha='center',va='center',color='#444444')
    ax.set_axis_off()
    ax.set_title('A  Spatial setting', loc='left', fontweight='semibold')
    ax.legend(frameon=False, loc='lower left', fontsize=7.5)

    ax=axes[1]
    ax.set_axis_off()
    ax.set_xlim(0,1)
    ax.set_ylim(0,1)
    ax.set_title('B  Decision-validity experiment', loc='left', fontweight='semibold')
    def box(x,y,w,h,text,fc):
        p=FancyBboxPatch((x,y),w,h,boxstyle='round,pad=0.012,rounding_size=0.018',facecolor=fc,edgecolor='#555555',linewidth=.8)
        ax.add_patch(p)
        ax.text(x+w/2,y+h/2,text,ha='center',va='center',fontsize=8.5)
    def arrow(x1,y1,x2,y2):
        ax.add_patch(FancyArrowPatch((x1,y1),(x2,y2),arrowstyle='-|>',mutation_scale=11,linewidth=.9,color='#666666'))
    box(.05,.73,.38,.14,'Existing provision\n89 facilities + pedestrian network','#EDF2F4')
    box(.57,.73,.38,.14,'Candidate opportunity\n1,132 network sites','#EDF2F4')
    box(.05,.47,.38,.15,'Supply-based priority\nper 10k | per km² | per 100 km roads','#F7E6D2')
    box(.57,.47,.38,.15,'Network-greedy reference\nmaximum marginal gain','#DCEBE8')
    box(.31,.21,.38,.14,'Sequential addition\n1-40 facilities; 5/10/15 min','#ECE5F3')
    box(.31,.04,.38,.11,'Compare shortfall, objective sensitivity,\ninvestment-scale dynamics, robustness','#F3EFE7')
    arrow(.24,.73,.24,.62)
    arrow(.76,.73,.76,.62)
    arrow(.24,.47,.42,.35)
    arrow(.76,.47,.58,.35)
    arrow(.50,.21,.50,.15)
    ax.text(.50,.92,'Two planning objectives',ha='center',va='center',fontsize=8.5,fontweight='semibold')
    ax.text(.50,.885,'district-wide road coverage  |  equal-subdistrict coverage',ha='center',va='center',fontsize=7.7,color='#555555')
    save(fig,'fig1_study_framework')

def fig2_first_step():
    d=pd.read_csv(SEQ/'indicator_failure_summary.csv')
    fig,axes=plt.subplots(1,2,figsize=(10.5,4.2),sharex=True,layout='constrained')
    xmax=70
    for ax,obj,label in zip(axes,['district','equal'],['A','B']):
        q=d[d.objective==obj].set_index('proxy').loc[PROXY].reset_index()
        y=np.arange(3)
        for i,r in q.iterrows():
            c=COL[r.proxy]
            ax.hlines(y[i],r.q25_first_step_shortfall_pct,r.q75_first_step_shortfall_pct,color=c,lw=6,alpha=.30)
            ax.plot(r.median_first_step_shortfall_pct,y[i],'o',ms=7,color=c,mec='white',mew=.7,zorder=3)
            ax.text(xmax-1,y[i],f"optimal in {r.exact_global_best_rate_pct:.1f}%",ha='right',va='center',fontsize=7.8,color='#4B5563')
        ax.set_yticks(y,[PLAB[p] for p in PROXY])
        ax.invert_yaxis()
        ax.set_xlim(0,xmax)
        ax.set_xlabel('First-step shortfall from best available gain (%)')
        ax.set_title(OLAB[obj],pad=7)
        ax.grid(axis='x')
        panel(ax,label)
    save(fig,'fig2_first_step_validity')

def fig3_spatial_mismatch():
    gpkg=ROOT/'data/processed/p06_refined_clean.gpkg'
    bound=gpd.read_file(gpkg,layer='study_subdistricts')
    cand=pd.read_csv(ROOT/'data/processed/hypothetical_candidate_nodes.csv',encoding='utf-8-sig')
    bound=attach_zones_to_boundaries(bound,cand)
    zone_map=cand[['zone','subdistrict']].drop_duplicates().set_index('subdistrict').zone.to_dict()
    d=pd.read_csv(SEQ/'street_opportunity_540.csv')
    q=d[(d.site_scenario=='INFERRED_89_01')&(d.service=='culture')&(d.threshold_min==10)].copy()
    q['zone']=q.subdistrict.map(zone_map)
    vals=q.set_index('zone')
    b=bound.copy()
    fig,axes=plt.subplots(1,3,figsize=(12.3,4.8),layout='constrained')
    specs=[('facilities_per_10k','A  Supply scarcity: per 10,000 residents','magma_r','min'),
           ('facilities_per_100km_network','B  Supply scarcity: per 100 km roads','magma_r','min'),
           ('max_equal','C  Network opportunity: equal-subdistrict objective','viridis','max')]
    for ax,(field,title,cmap,mode) in zip(axes,specs):
        m=b.merge(vals[[field]],left_on='zone',right_index=True,how='left')
        m.plot(column=field,ax=ax,cmap=cmap,edgecolor='white',linewidth=.9,legend=True,
               legend_kwds={'shrink':.65,'label':field.replace('_',' ')})
        best=q.loc[q[field].idxmin() if mode=='min' else q[field].idxmax(),'zone']
        b[b.zone==best].boundary.plot(ax=ax,color='#111111',linewidth=2.2)
        for r in m.itertuples():
            p=r.geometry.representative_point()
            name=cand.loc[cand.zone==r.zone,'subdistrict_en'].iloc[0].replace(' Subdistrict','')
            ax.text(p.x,p.y,name,fontsize=6.2,ha='center',va='center',color='white' if field!='max_equal' else '#222222')
        ax.set_title(title,loc='left',fontweight='semibold',fontsize=9.5)
        ax.set_axis_off()
    fig.text(.5,.005,'Culture facilities, 10-minute threshold, location scenario 1. Thick outline = indicator-priority or network-opportunity subdistrict.',ha='center',fontsize=8)
    save(fig,'fig3_spatial_mismatch')

def fig4_relationships():
    d=pd.read_csv(SEQ/'indicator_failure_conditions.csv')
    fig,axes=plt.subplots(2,3,figsize=(11.5,6.7),sharex=True,sharey=True,layout='constrained')
    for r,obj in enumerate(['district','equal']):
        for c,proxy in enumerate(PROXY):
            ax=axes[r,c]
            q=d[(d.objective==obj)&(d.proxy==proxy)]
            for svc,marker in [('healthcare','o'),('elderly_care','^'),('culture','s')]:
                z=q[q.service==svc]
                ax.scatter(z.supply_opportunity_rho,z.first_step_shortfall_pct,s=25,marker=marker,color=COL[svc],alpha=.72,edgecolor='white',linewidth=.35,label=SLAB[svc])
            if len(q)>2:
                coef=np.polyfit(q.supply_opportunity_rho,q.first_step_shortfall_pct,1)
                xs=np.linspace(q.supply_opportunity_rho.min(),q.supply_opportunity_rho.max(),100)
                ax.plot(xs,np.polyval(coef,xs),color='#4A4A4A',lw=1.1,ls='--')
            ax.axvline(0,color='#9A9A9A',lw=.7)
            ax.grid(True)
            if r==0:
                ax.set_title(PLAB[proxy])
            if c==0:
                ax.set_ylabel(OLAB[obj]+'\nFirst-step shortfall (%)')
            if r==1:
                ax.set_xlabel('Supply-opportunity rank correlation')
    handles=[Line2D([0],[0],marker=m,color='none',markerfacecolor=COL[s],markeredgecolor='white',label=SLAB[s],markersize=6) for s,m in [('healthcare','o'),('elderly_care','^'),('culture','s')]]
    fig.legend(handles=handles,ncol=3,loc='upper center',bbox_to_anchor=(.5,1.02),frameon=False)
    for ax,l in zip(axes.flatten(),list('ABCDEF')):
        panel(ax,l)
    save(fig,'fig4_supply_opportunity_relationship')

def fig5_absolute_trajectories():
    d=pd.read_csv(ROOT/'outputs/figures/sequential_v11/figure_data_all_services_all_thresholds.csv')
    d=d[(d.threshold_min==15)&(d.objective=='district_gain_m')]
    rules=['network_greedy']+PROXY_RULE
    color={'network_greedy':COL['greedy'],'facilities_per_10k':COL['per_10k'],'facilities_per_km2':COL['per_km2'],'facilities_per_100km_network':COL['per_100km']}
    ls={'network_greedy':'-','facilities_per_10k':'-','facilities_per_km2':'--','facilities_per_100km_network':'-.'}
    label={'network_greedy':'Network-greedy reference',**{k:PLAB[k] for k in PROXY_RULE}}
    fig,axes=plt.subplots(1,3,figsize=(12.2,4.4),layout='constrained')
    for ax,svc,l in zip(axes,['healthcare','elderly_care','culture'],['A','B','C']):
        for rule in rules:
            q=d[(d.service==svc)&(d.rule==rule)].sort_values('new_sites')
            x=np.r_[0,q.new_sites]
            y=np.r_[0,q.gain_median/1000]
            ax.plot(x,y,color=color[rule],ls=ls[rule],lw=2.2 if rule=='network_greedy' else 1.7,label=label[rule])
        ax.set_title(SLAB[svc])
        ax.set_xlabel('Added facilities')
        ax.grid(axis='y')
        panel(ax,l)
        if ax is axes[0]:
            ax.set_ylabel('Additional covered road network (km)')
    handles,labels=axes[0].get_legend_handles_labels()
    fig.legend(handles,labels,ncol=2,loc='upper center',bbox_to_anchor=(.5,1.07),frameon=False)
    save(fig,'fig5_cumulative_coverage')

def fig6_relative_budget():
    d=pd.read_csv(SEQ/'budget_trajectory_summary.csv')
    fig,axes=plt.subplots(1,2,figsize=(10.7,4.4),sharey=False,layout='constrained')
    for ax,obj,l in zip(axes,['district_gain_m','gain_equal_street_mean_pp'],['A','B']):
        q=d[d.objective==obj]
        for rule in PROXY_RULE:
            z=q[q.rule==rule].sort_values('new_sites')
            c=COL[{'facilities_per_10k':'per_10k','facilities_per_km2':'per_km2','facilities_per_100km_network':'per_100km'}[rule]]
            ax.fill_between(z.new_sites,z.q25_relative_difference_pct,z.q75_relative_difference_pct,color=c,alpha=.13,lw=0)
            ax.plot(z.new_sites,z.median_relative_difference_pct,color=c,lw=1.9,label=PLAB[rule])
        ax.set_title(OLAB[obj])
        ax.set_xlabel('Added facilities')
        ax.set_ylabel('Relative shortfall from greedy reference (%)')
        ax.grid(True)
        panel(ax,l)
    axes[0].legend(frameon=False)
    save(fig,'fig6_investment_scale')

def fig7_heterogeneity():
    d=pd.read_csv(SEQ/'indicator_failure_conditions.csv')
    agg=d.groupby(['objective','service','threshold_min','proxy'],as_index=False).first_step_shortfall_pct.median()
    rows=[(s,t) for s in ['healthcare','elderly_care','culture'] for t in [5,10,15]]
    fig,axes=plt.subplots(1,2,figsize=(10.5,5.3),layout='constrained')
    vmax=float(agg.first_step_shortfall_pct.max())
    for ax,obj,l in zip(axes,['district','equal'],['A','B']):
        arr=[]
        for s,t in rows:
            arr.append([float(agg[(agg.objective==obj)&(agg.service==s)&(agg.threshold_min==t)&(agg.proxy==p)].first_step_shortfall_pct.iloc[0]) for p in PROXY])
        arr=np.array(arr)
        im=ax.imshow(arr,cmap='YlOrRd',vmin=0,vmax=vmax,aspect='auto')
        ax.set_xticks(range(3),[PLAB[p] for p in PROXY],rotation=14,ha='right')
        ax.set_yticks(range(len(rows)),[f'{SLAB[s]} | {t} min' for s,t in rows])
        for i in range(arr.shape[0]):
            for j in range(arr.shape[1]):
                ax.text(j,i,f'{arr[i,j]:.1f}',ha='center',va='center',fontsize=7.6,color='#111111')
        ax.set_title(OLAB[obj])
        panel(ax,l)
    cb=fig.colorbar(im,ax=axes,shrink=.78,pad=.02)
    cb.set_label('Median first-step shortfall (%)')
    save(fig,'fig7_service_threshold_heterogeneity')

def fig8_walkability():
    d=pd.read_csv(ROB/'walkability_contribution_robustness.csv')
    fig,axes=plt.subplots(1,2,figsize=(10.5,4.2),layout='constrained')
    for obj,c in [('district_gain_m',COL['district']),('gain_equal_street_mean_pp',COL['equal'])]:
        q=d[d.objective==obj].sort_values('new_sites')
        axes[0].plot(q.new_sites,q.spearman_original_vs_strict_loss,marker='o',lw=1.9,color=c,label=OLAB[obj])
        axes[1].plot(q.new_sites,q.median_abs_loss_difference_pp,marker='o',lw=1.9,color=c,label=OLAB[obj])
    axes[0].axhline(0,color='#999999',lw=.8)
    axes[0].set_ylim(-.65,1.02)
    axes[0].set_ylabel('Rank correlation of supply-rule losses')
    axes[1].set_ylabel('Median absolute loss difference (pp)')
    for ax,l in zip(axes,['A','B']):
        ax.set_xticks([1,12,40])
        ax.set_xlabel('Added facilities')
        ax.grid(True)
        panel(ax,l)
    axes[0].legend(frameon=False)
    save(fig,'fig8_network_robustness')

def main():
    fig1_study_framework()
    fig2_first_step()
    fig3_spatial_mismatch()
    fig4_relationships()
    fig5_absolute_trajectories()
    fig6_relative_budget()
    fig7_heterogeneity()
    fig8_walkability()
    qa={'figure_count':8,'uses_main_outputs':True,'appendix_required':False,'output_dir':str(OUT.relative_to(ROOT))}
    (ROOT/'manuscript/cities/figure_qa.json').write_text(json.dumps(qa,indent=2),encoding='utf-8')
    print(json.dumps(qa,indent=2))

if __name__=='__main__':
    main()
