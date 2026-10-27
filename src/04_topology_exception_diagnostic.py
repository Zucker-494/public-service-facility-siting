#!/usr/bin/env python3
"""Evaluate the effect of connecting an unresolved road crossing."""
from pathlib import Path
import networkx as nx,numpy as np,pandas as pd,geopandas as gpd
from pyproj import Transformer
ROOT=Path(__file__).resolve().parents[1]
q=pd.read_csv(ROOT/'data/qa/unshared_crossings_district.csv')
a=q[~q.tagged_grade_separated.astype(bool)]
assert len(a)==1,f'Expected single at-grade crossing to review; observed {len(a)}'
row=a.iloc[0]
g=gpd.read_file(ROOT/'data/processed/p06_rebuilt_network.gpkg',layer='osm_node_identity_edges')
district=g[g.zone>=0].reset_index(drop=True)
r1=district.iloc[int(row.edge_i)];r2=district.iloc[int(row.edge_j)]
line1,line2=r1.geometry,r2.geometry
cross=line1.intersection(line2)
assert cross.geom_type=='Point'
lon,lat=Transformer.from_crs(32651,4326,always_xy=True).transform(cross.x,cross.y)
G=nx.Graph()
for x in g.itertuples(): G.add_edge(int(x.u_id),int(x.v_id),weight=float(x.length_m))
a1,a2=int(r1.u_id),int(r1.v_id);b1,b2=int(r2.u_id),int(r2.v_id)
# Point on edge distance to endpoints along lines: edges are two-node segments
p1=line1.project(cross);p2=line2.project(cross)
H=G.copy();H.remove_edge(a1,a2);H.remove_edge(b1,b2)
virtual='crossing_test_only'
for n,c in [(a1,p1),(a2,line1.length-p1),(b1,p2),(b2,line2.length-p2)]:H.add_edge(n,virtual,weight=float(c))
rows=[]
for n1 in [a1,a2]:
 for n2 in [b1,b2]:
  try:d0=nx.shortest_path_length(G,n1,n2,weight='weight')
  except nx.NetworkXNoPath:d0=np.inf
  d1=nx.shortest_path_length(H,n1,n2,weight='weight')
  rows.append({'from_osm_node':n1,'to_osm_node':n2,'distance_primary_unshared_m':d0,'distance_if_connected_m':d1,
    'shortening_if_connected_m':d0-d1 if np.isfinite(d0) else np.inf})
pd.DataFrame(rows).to_csv(ROOT/'data/qa/at_grade_crossing_connection_sensitivity.csv',index=False)
pd.DataFrame([{'lon':lon,'lat':lat,'way1':int(r1.osm_way_id),'way2':int(r2.osm_way_id),'way1_highway':r1.highway,'way2_highway':r2.highway,
 'status':'unresolved: primary model retains OSM node identity; connected alternative quantified; physical ground truth not independently checked',
 'connection_in_primary_graph':False}]).to_csv(ROOT/'data/qa/at_grade_crossing_manual_review.csv',index=False)
print(f'At-grade crossing: ({lon:.7f},{lat:.7f}), ways {r1.osm_way_id}/{r2.osm_way_id}')
print(pd.DataFrame(rows).to_string(index=False))
