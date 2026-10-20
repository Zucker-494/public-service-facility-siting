#!/usr/bin/env python3
"""Fixed-scale research maps and clearly marked scenario-only chart."""
from pathlib import Path
import geopandas as gpd,pandas as pd,numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from shapely.geometry import box
from matplotlib.patches import Rectangle
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs/osm_inference'
REG=ROOT/'data/processed/p06_refined_clean.gpkg'
plt.rcParams['font.family']='DejaVu Sans'
NAME_TABLE=ROOT/'data/qa/osm_inference/six_facility_address_osm_trace.csv'
# Readable display translations; official Chinese names and existing *_en columns remain in CSV.
DISPLAY_NAMES={
 '大桥街道社区文化活动中心':'Daqiao Community Cultural Activity Centre',
 '延吉新村街道社区文化活动中心':'Yanji Xincun Community Cultural Activity Centre',
 '上海信养养老服务有限公司杨浦信澜养老院分公司':'Xinlan Elderly Care Home (Yangpu)',
 '上海市杨浦人和养老院':'Yangpu Renhe Elderly Care Home',
 '上海市杨浦区长海路街道敬老院':'Changhai Road Elderly Care Home',
 '上海杨浦区汇晨长白老年福利院':'Huichen Changbai Elderly Welfare Home',
}


def make_maps():
    sites=gpd.read_file(OUT/'address_candidate_envelopes.gpkg',layer='sampled_network_access_vertices')
    envelopes=gpd.read_file(OUT/'address_candidate_envelopes.gpkg',layer='plausible_location_corridors')
    roads=gpd.read_file(REG,layer='osm_node_identity_edges')
    bounds=gpd.read_file(REG,layer='study_subdistricts')
    locs=gpd.read_file(REG,layer='facility_inherited_coordinates')
    names=[x.facility_name for x in envelopes.itertuples()]
    translations=pd.read_csv(NAME_TABLE).drop_duplicates('facility_name').set_index('facility_name')['facility_name_en'].to_dict()
    fig,axs=plt.subplots(2,3,figsize=(15.2,10),constrained_layout=True)
    half=900 # all panels have EXACTLY the same 1800m ×1800m view
    for ax,name in zip(axs.flat,names):
        corridor=envelopes.loc[envelopes.facility_name==name].geometry.iloc[0]
        c=corridor.centroid
        xmin,xmax=c.x-half,c.x+half; ymin,ymax=c.y-half,c.y+half
        sub=bounds[bounds.geometry.intersects(box(xmin,ymin,xmax,ymax))]
        if len(sub):sub.boundary.plot(ax=ax,color='#999999',lw=0.5)
        rr=roads.cx[xmin:xmax,ymin:ymax]
        if len(rr):rr.plot(ax=ax,color='#d1d5db',lw=0.35)
        gpd.GeoSeries([corridor],crs=envelopes.crs).plot(ax=ax,color='#0ea5e9',alpha=.19,edgecolor='#0284c7',lw=1.25)
        old=locs.cx[xmin:xmax,ymin:ymax]
        if len(old):old.plot(ax=ax,color='#64748b',markersize=10,alpha=.6)
        ss=sites[sites.facility_name==name]
        ss.plot(ax=ax,color='#d97706',markersize=29,marker='x')
        ax.set_xlim(xmin,xmax);ax.set_ylim(ymin,ymax);ax.set_aspect('equal');
        english=DISPLAY_NAMES.get(name) or translations.get(name)
        if not isinstance(english,str) or not english.strip():
            raise ValueError(f'Missing existing English translation for facility: {name}')
        # The supplied *_en fields contain transliterations rather than always official translations.
        # Wrap long names without altering facility identity.
        import textwrap
        ax.set_title('\n'.join(textwrap.wrap(english,width=38)),fontsize=9)
        ax.add_patch(Rectangle((xmin+90,ymin+95),500,0,ec='black',lw=2))
        ax.text(xmin+340,ymin+130,'500 m',fontsize=9,ha='center')
        ax.tick_params(labelsize=7)
        ax.set_xlabel('UTM E (m)',fontsize=8);ax.set_ylabel('UTM N (m)',fontsize=8)
    fig.suptitle('OSM candidate areas for six existing facilities with uncertain coordinates\nConsistent 1.8 km map extent',fontsize=14)
    fig.savefig(OUT/'01_address_inference_six_equal_scale_maps.png',dpi=160)
    plt.close(fig)

def make_profile():
    df=pd.read_csv(OUT/'street_coverage_scenario_range.csv')
    fig,axs=plt.subplots(1,2,figsize=(13,7),constrained_layout=True)
    for ax,service in zip(axs,['culture','elderly_care']):
        d=df[(df.service==service)&(df.threshold_min==15)].sort_values('baseline_83_coverage_share').reset_index(drop=True)
        y=np.arange(len(d))
        ax.scatter(d.baseline_83_coverage_share*100,y,color='#64748b',s=30,label='83-site baseline')
        lo=d.inferred_89_min_share.to_numpy()*100;hi=d.inferred_89_max_share.to_numpy()*100
        ax.hlines(y,lo,hi,lw=4,color='#0284c7',label='89-site inferred location scenarios')
        ax.scatter((lo+hi)/2,y,color='#075985',marker='|',s=70)
        if 'subdistrict_en' not in d.columns or d.subdistrict_en.isna().any():
            raise ValueError('English subdistrict names are missing in the project data')
        ax.set_yticks(y,d.subdistrict_en)
        ax.set_xlim(0,100);ax.set_xlabel('15-minute walkable network length coverage (%)')
        ax.set_title('Community cultural centres' if service=='culture' else 'Elderly care facilities')
        ax.grid(axis='x',alpha=.25)
        if service=='culture':ax.legend(loc='lower right',fontsize=8)
    fig.suptitle('Sensitivity of 15-minute network coverage to six existing-facility locations\n83 geocoded sites vs. 89-site inferred-location scenarios (scenario ranges; not confidence intervals)',fontsize=12)
    fig.savefig(OUT/'02_missing_facilities_inference_15min_sensitivity.png',dpi=150)
    plt.close(fig)
if __name__=='__main__':make_maps();make_profile();print('Figures generated')
