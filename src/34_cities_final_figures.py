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
    """Attach candidate-zone IDs to boundary polygons without relying on layer field names."""
    if 'zone' in bound.columns:
        out=bound.copy()
        out['zone']=out['zone'].astype(int)
        return out
    pts=gpd.GeoDataFrame(cand[['zone']].copy(), geometry=gpd.points_from_xy(cand.x,cand.y), crs=bound.crs)
    bb=bound.reset_index(drop=True).reset_index().rename(columns={'index':'poly_idx'})
    joined=gpd.sjoin(pts, bb[['poly_idx','geometry']], predicate='within', how='left')
    # A small number of candidate nodes can sit exactly on polygon boundaries.
    # They are not needed for identifying the zone of each boundary polygon.
    mapped=joined.dropna(subset=['poly_idx']).copy()
    mapping=mapped.groupby('poly_idx').zone.agg(lambda s: int(s.mode().iloc[0]))
    out=bb.set_index('poly_idx').copy()
    out['zone']=out.index.map(mapping)
    expected=int(cand.zone.nunique())
    if out.zone.isna().any() or int(out.zone.nunique()) != expected:
        raise ValueError(f"Could not map all candidate zones to study boundaries: polygons={len(out)}, mapped_zones={out.zone.nunique()}, expected={expected}")
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