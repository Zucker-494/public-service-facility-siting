#!/usr/bin/env python3
"""Inventory-vs-coordinate deletion audit. No missing facility positions are imputed.
Tests whether policy decisions change if 6 documented facilities count as official supply
but remain absent from network accessibility (diagnostic only, not a primary scenario).
"""
from pathlib import Path
import numpy as np,pandas as pd,geopandas as gpd
ROOT=Path(__file__).resolve().parents[1]
T=ROOT/'outputs/tables';Q=ROOT/'data/qa'
legacy=ROOT/'data/raw/p06_yangpu_original.gpkg'
all_=gpd.read_file(legacy,layer='facility_geometry_candidates')
all_=all_[all_.facility_type.isin(['healthcare','elderly_care','culture'])]
ready=gpd.read_file(legacy,layer='facility_accessibility_ready')
ready=ready[ready.facility_type.isin(['healthcare','elderly_care','culture'])]
source=all_.groupby(['facility_type','subdistrict_name'],as_index=False).size().rename(columns={'facility_type':'service','subdistrict_name':'subdistrict','size':'source_inventory_count'})
counts=pd.read_csv(T/'supply_verified.csv')
result=counts.merge(source,on=['service','subdistrict'],validate='one_to_one')
result['coordinate_unresolved_count']=result.source_inventory_count-result.count_verified
assert (result.coordinate_unresolved_count>=0).all() and int(result.coordinate_unresolved_count.sum())==6
result['inventory_facilities_per_10k']=result.source_inventory_count/result.population_census2020*10000
result['inventory_facilities_per_km2']=result.source_inventory_count/result.area_km2
result['inventory_facilities_per_100km_network']=result.source_inventory_count/(result.network_km/100)
result.to_csv(Q/'supply_inventory_vs_spatial_analysis.csv',index=False)
# Priority chosen under known existence but geometrically unresolved six: diagnostic only
out=[]
for service,g in result.groupby('service'):
 for x in ['facilities_per_10k','facilities_per_km2','facilities_per_100km_network']:
  a=g.sort_values([x,'subdistrict']).iloc[0]
  b=g.sort_values(['inventory_'+x,'subdistrict']).iloc[0]
  out.append({'service':service,'proxy':x,'coordinate_screened_priority':a.subdistrict,'official_inventory_priority':b.subdistrict,
   'priority_changes_when_unresolved_sites_counted':a.subdistrict!=b.subdistrict,
   'experimental_warning':'Inventory-only prioritization; network benefit remains calculated from 83 spatially accepted facilities; not a plausible complete-facility scenario.'})
pd.DataFrame(out).to_csv(Q/'missingness_changes_priority.csv',index=False)
print(pd.DataFrame(out)[['service','proxy','coordinate_screened_priority','official_inventory_priority','priority_changes_when_unresolved_sites_counted']].to_string(index=False))
