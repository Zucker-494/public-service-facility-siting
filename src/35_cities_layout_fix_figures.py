#!/usr/bin/env python3
from pathlib import Path
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

COL = {'healthcare':'#3B82A0','elderly_care':'#C26A5A','culture':'#6A8E3A'}
plt.rcParams.update({
    'font.family':'DejaVu Sans','font.size':9.5,'axes.titlesize':10.5,
    'axes.labelsize':9.5,'xtick.labelsize':8.5,'ytick.labelsize':8.5,
    'legend.fontsize':8.5,'pdf.fonttype':42,'ps.fonttype':42,
})

def save(fig, stem):
    fig.savefig(OUT / f'{stem}.png', dpi=320, bbox_inches='tight', facecolor='white')
    fig.savefig(OUT / f'{stem}.pdf', bbox_inches='tight', facecolor='white')
    plt.close(fig)

def attach_zones_to_boundaries(bound, cand):
    if 'zone' in bound.columns:
        out = bound.copy()
        out['zone'] = out['zone'].astype(int)
        return out
    pts = gpd.GeoDataFrame(cand[['zone']].copy(), geometry=gpd.points_from_xy(cand.x, cand.y), crs=bound.crs)
    bb = bound.reset_index(drop=True).reset_index().rename(columns={'index':'poly_idx'})
    joined = gpd.sjoin(pts, bb[['poly_idx','geometry']], predicate='within', how='left')
    mapped = joined.dropna(subset=['poly_idx']).copy()
    mapping = mapped.groupby('poly_idx').zone.agg(lambda x: int(x.mode().iloc[0]))
    out = bb.set_index('poly_idx').copy()
    out['zone'] = out.index.map(mapping)
    expected = int(cand.zone.nunique())
    if out.zone.isna().any() or int(out.zone.nunique()) != expected:
        raise ValueError(f'Boundary-zone mapping failed: mapped={out.zone.nunique()}, expected={expected}')
    out['zone'] = out.zone.astype(int)
    return out.reset_index(drop=True)

def fig1_study_area():
    gpkg = ROOT / 'data/processed/p06_refined_clean.gpkg'
    bound = gpd.read_file(gpkg, layer='study_subdistricts')
    edges = gpd.read_file(gpkg, layer='osm_node_identity_edges')
    edges = edges[edges['zone'] >= 0]
    cand = pd.read_csv(ROOT / 'data/processed/hypothetical_candidate_nodes.csv', encoding='utf-8-sig')
    bound = attach_zones_to_boundaries(bound, cand)
    reg = pd.read_csv(ROOT / 'data/curated/official_facility_registry_89_address_audited.csv', encoding='utf-8-sig')
    reg = reg[reg.wgs84_lon.notna() & reg.wgs84_lat.notna()].copy()
    fac = gpd.GeoDataFrame(reg, geometry=gpd.points_from_xy(reg.wgs84_lon, reg.wgs84_lat), crs='EPSG:4326').to_crs(edges.crs)
    cg = gpd.GeoDataFrame(cand, geometry=gpd.points_from_xy(cand.x,cand.y), crs=edges.crs)

    fig, (ax, lax) = plt.subplots(1,2,figsize=(10.8,6.0),gridspec_kw={'width_ratios':[4.0,1.35]},layout='constrained')
    bound.plot(ax=ax, facecolor='#F4F1E8', edgecolor='#666666', linewidth=0.8)
    edges.plot(ax=ax, color='#B9C0C5', linewidth=0.30, alpha=0.76)
    cg.plot(ax=ax, color='#78A7BA', markersize=1.9, alpha=0.38)
    markers = {'healthcare':'o','elderly_care':'^','culture':'s'}
    for svc in ['healthcare','elderly_care','culture']:
        q = fac[fac.facility_type == svc]
        q.plot(ax=ax, color=COL[svc], marker=markers[svc], markersize=25, edgecolor='white', linewidth=0.45)

    zone_name = cand[['zone','subdistrict_en']].drop_duplicates().set_index('zone').subdistrict_en.to_dict()
    for r in bound.itertuples():
        if r.zone in zone_name:
            p = r.geometry.representative_point()
            ax.text(p.x,p.y,zone_name[r.zone].replace(' Subdistrict',''),fontsize=6.8,ha='center',va='center',color='#343A40')
    ax.set_axis_off()
    ax.set_title('Yangpu District, Shanghai', loc='left', fontweight='semibold', pad=6)

    lax.set_axis_off()
    lax.set_xlim(0,1); lax.set_ylim(0,1)
    lax.text(0.04,0.94,'Study inputs',fontsize=11,fontweight='semibold',va='top')
    handles = [
        Line2D([0],[0],marker='o',linestyle='none',markerfacecolor='#78A7BA',markeredgecolor='none',alpha=.55,markersize=5,label='1,132 candidate sites'),
        Line2D([0],[0],marker='o',linestyle='none',markerfacecolor=COL['healthcare'],markeredgecolor='white',markersize=7,label='Healthcare (12 mapped)'),
        Line2D([0],[0],marker='^',linestyle='none',markerfacecolor=COL['elderly_care'],markeredgecolor='white',markersize=7,label='Elderly care (61 mapped)'),
        Line2D([0],[0],marker='s',linestyle='none',markerfacecolor=COL['culture'],markeredgecolor='white',markersize=7,label='Cultural facilities (10 mapped)'),
    ]
    lax.legend(handles=handles,loc='upper left',bbox_to_anchor=(0.0,0.86),frameon=False,handletextpad=.7,borderaxespad=0.0)
    lax.text(0.04,0.48,'Inventory total',fontsize=9.2,fontweight='semibold')
    lax.text(0.04,0.43,'89 existing facilities',fontsize=8.8)
    lax.text(0.04,0.34,'Location uncertainty',fontsize=9.2,fontweight='semibold')
    lax.text(0.04,0.29,'Six facilities without accepted\ninherited coordinates are\nrepresented through five\naddress-based scenarios.',fontsize=8.5,linespacing=1.35,va='top')
    lax.text(0.04,0.08,'Road network: 798.6 km',fontsize=8.5,color='#555555')
    save(fig,'fig1_study_area')

def fig2_framework():
    fig, ax = plt.subplots(figsize=(10.5,5.8),layout='constrained')
    ax.set_axis_off(); ax.set_xlim(0,1); ax.set_ylim(0,1)

    def box(x,y,w,h,text,fc,fontsize=9.5,weight='normal'):
        p = FancyBboxPatch((x,y),w,h,boxstyle='round,pad=0.012,rounding_size=0.018',facecolor=fc,edgecolor='#5B5B5B',linewidth=.9)
        ax.add_patch(p)
        ax.text(x+w/2,y+h/2,text,ha='center',va='center',fontsize=fontsize,fontweight=weight)
    def arrow(x1,y1,x2,y2):
        ax.add_patch(FancyArrowPatch((x1,y1),(x2,y2),arrowstyle='-|>',mutation_scale=12,linewidth=1.0,color='#666666',shrinkA=0,shrinkB=0))

    box(0.19,0.84,0.62,0.09,'Planning objective\nDistrict-wide road coverage   |   Equal-subdistrict coverage','#F3F4F6',fontsize=9.3,weight='semibold')
    box(0.07,0.63,0.36,0.13,'Existing provision\n89 facilities + pedestrian network','#EAF0F3')
    box(0.57,0.63,0.36,0.13,'Candidate opportunity\n1,132 network sites','#EAF0F3')
    box(0.07,0.40,0.36,0.14,'Supply-based priority\nper 10k | per km² | per 100 km roads','#F7E5CF')
    box(0.57,0.40,0.36,0.14,'Network-greedy reference\nmaximum marginal gain','#DCEAE7')
    box(0.30,0.18,0.40,0.12,'Sequential addition\n1-40 facilities; 5/10/15 min','#EAE3F2')
    box(0.29,0.025,0.42,0.085,'Compare decision shortfall, objective sensitivity,\ninvestment-scale dynamics, and network robustness','#F2EEE6',fontsize=8.7)

    arrow(0.38,0.84,0.25,0.76); arrow(0.62,0.84,0.75,0.76)
    arrow(0.25,0.63,0.25,0.54); arrow(0.75,0.63,0.75,0.54)
    arrow(0.25,0.40,0.43,0.30); arrow(0.75,0.40,0.57,0.30)
    arrow(0.50,0.18,0.50,0.11)
    save(fig,'fig2_decision_framework')

def fig4_spatial_mismatch():
    gpkg = ROOT / 'data/processed/p06_refined_clean.gpkg'
    bound = gpd.read_file(gpkg, layer='study_subdistricts')
    cand = pd.read_csv(ROOT / 'data/processed/hypothetical_candidate_nodes.csv', encoding='utf-8-sig')
    bound = attach_zones_to_boundaries(bound, cand)
    zone_map = cand[['zone','subdistrict']].drop_duplicates().set_index('subdistrict').zone.to_dict()
    d = pd.read_csv(SEQ / 'street_opportunity_540.csv')
    q = d[(d.site_scenario=='INFERRED_89_01')&(d.service=='culture')&(d.threshold_min==10)].copy()
    q['zone'] = q.subdistrict.map(zone_map)
    vals = q.set_index('zone')

    fig, axd = plt.subplot_mosaic([['A','B'],['C','C']],figsize=(10.8,8.6),gridspec_kw={'height_ratios':[1.0,1.15]},layout='constrained')
    specs = {
        'A':('facilities_per_10k','A  Supply scarcity: per 10,000 residents','magma_r','min','facilities per 10k'),
        'B':('facilities_per_100km_network','B  Supply scarcity: per 100 km roads','magma_r','min','facilities per 100 km network'),
        'C':('max_equal','C  Network opportunity: equal-subdistrict objective','viridis','max','maximum marginal gain'),
    }
    for key, ax in axd.items():
        field,title,cmap,mode,cblabel = specs[key]
        m = bound.merge(vals[[field]],left_on='zone',right_index=True,how='left')
        m.plot(column=field,ax=ax,cmap=cmap,edgecolor='white',linewidth=1.0,legend=True,legend_kwds={'shrink':0.78,'label':cblabel})
        best = q.loc[q[field].idxmin() if mode=='min' else q[field].idxmax(),'zone']
        bound[bound.zone==best].boundary.plot(ax=ax,color='#111111',linewidth=2.5)
        for r in m.itertuples():
            p = r.geometry.representative_point()
            name = cand.loc[cand.zone==r.zone,'subdistrict_en'].iloc[0].replace(' Subdistrict','')
            val = getattr(r,field)
            color = 'white' if key in ('A','B') and val >= m[field].median() else '#222222'
            ax.text(p.x,p.y,name,fontsize=7.4,ha='center',va='center',color=color)
        ax.set_title(title,loc='left',fontweight='semibold',pad=5)
        ax.set_axis_off()
    save(fig,'fig4_spatial_mismatch')

def main():
    fig1_study_area()
    fig2_framework()
    fig4_spatial_mismatch()
    print('Generated layout-fix figures:',OUT)

if __name__=='__main__':
    main()
