#!/usr/bin/env python3
"""Build the pedestrian network and calculate baseline coverage and candidate site gains."""
from __future__ import annotations
import argparse,sys,json,time,hashlib,math
from collections import defaultdict
from pathlib import Path
import geopandas as gpd, pandas as pd, numpy as np, networkx as nx
from shapely.geometry import Point,LineString
from shapely.ops import unary_union
from shapely.strtree import STRtree
from pyproj import Transformer
from scipy.stats import spearmanr
from pbf_reader import read_osm

ROOT=Path(__file__).resolve().parents[1]
TBL=ROOT/'outputs/tables';QA=ROOT/'data/qa';SP=ROOT/'data/processed'
for p in (TBL,QA,SP):p.mkdir(parents=True,exist_ok=True)
SERVICES=['healthcare','elderly_care','culture']
THRESHOLDS=[5,10,15]
SPEED=1.2
RADIUS={t:t*60*SPEED for t in THRESHOLDS}
PEDESTRIAN_HIGHWAYS={'footway','pedestrian','path','steps','living_street','residential','service','unclassified','tertiary','secondary','primary','track','road','cycleway','tertiary_link','secondary_link','primary_link'}
EXCLUDE_ACCESS={'no','private'}
REVIEW=[
 ('culture','大桥街道社区文化活动中心','Official site at 平凉路1730号 verified; old candidate geocoded to unrelated healthcare site; no independently confirmed coordinates.','https://www.shanghai.gov.cn/nw17239/20260615/18afd18823ac4b80b0b5270001e04cfe.html'),
 ('culture','延吉新村街道社区文化活动中心','Conflicting public venue locations 延吉中路77号 and 控江路645弄21号; main site/branch unresolved; no independently confirmed coordinates.','https://www.shanghai.gov.cn/nw17239/20250922/b91728e3a1054f68af5d48aaec87f8ca.html'),
 ('elderly_care','上海信养养老服务有限公司杨浦信澜养老院分公司','Institution and 世界路203号 corroborated; original coordinate lacked precise geocode and OSM matched unrelated entity.','https://ybj.sh.gov.cn/gsgg/20230918/e4ca6dfbefb641fea3f6fe0195d32680.html'),
 ('elderly_care','上海市杨浦人和养老院','Facility named in 2024 district subsidy notice; original coordinate lacks an independently verified location.','https://www.shyp.gov.cn/zhengwu/mzj-gyjsygl/2025/219/9a3687cf8d29a385c1ecea069ba67b0f.html'),
 ('elderly_care','上海市杨浦区长海路街道敬老院','Official address 翔殷路505弄9号 corroborated; original geocoding confidence zero and OSM candidate unrelated.','https://www.shyp.gov.cn/shypq/ggfw-bmgg/20241016/465932.html'),
 ('elderly_care','上海杨浦区汇晨长白老年福利院','2023 list gave 民治路15号; 2024/2026 sources report 春江路815号, indicating temporal address discrepancy.','https://mzj.sh.gov.cn/MZ_zhuzhan34_0-2-6/20241213/8a4cd7a8d26f483e95e8fd98802f40ab.html')
]

def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for buf in iter(lambda:f.read(1024*1024),b''):h.update(buf)
 return h.hexdigest()

def construct_graph(pbf,boundary):
 print('reading PBF node IDs and ways...',flush=True)
 minx,miny,maxx,maxy=boundary.to_crs('EPSG:4326').total_bounds
 pad=0.035 # ≈3.3 km buffer; exceeds 15min baseline walking radius
 minx-=pad;maxx+=pad;miny-=pad;maxy+=pad
 nodes={};ways=[];n_all=0;w_all=0;rej=defaultdict(int)
 for record in read_osm(pbf):
  if record[0]=='node':
   _,nid,lon,lat=record;n_all+=1
   if minx<=lon<=maxx and miny<=lat<=maxy:nodes[nid]=(lon,lat)
  else:
   _,wid,refs,tags=record;w_all+=1
   typ=tags.get('highway','')
   if typ not in PEDESTRIAN_HIGHWAYS:rej['nonpedestrian_type']+=1;continue
   if tags.get('foot') in EXCLUDE_ACCESS or tags.get('access') in EXCLUDE_ACCESS:rej['foot_or_access_restricted']+=1;continue
   if typ=='cycleway' and tags.get('foot') not in {'yes','designated','permissive'}:rej['cycleway_not_foot_explicit']+=1;continue
   if tags.get('motorroad')=='yes':rej['motorroad']+=1;continue
   if any(r in nodes for r in refs):ways.append((wid,refs,tags))
 print('PBF nodes',n_all,'retained',len(nodes),'ways',w_all,'candidate pedestrian ways',len(ways),flush=True)
 transformer=Transformer.from_crs(4326,32651,always_xy=True)
 needed={r for _,refs,_ in ways for r in refs if r in nodes}
 xs,ys=transformer.transform([nodes[r][0] for r in needed],[nodes[r][1] for r in needed]);xy={r:(x,y) for r,x,y in zip(needed,xs,ys)}
 G=nx.Graph(); edge_meta={}; kept_ways=set();
 for wid,refs,tags in ways:
  for u,v in zip(refs[:-1],refs[1:]):
   if u not in xy or v not in xy or u==v:continue
   a,b=xy[u],xy[v];length=math.dist(a,b)
   if not (0.1<length<2500):rej['invalid_segment_length']+=1;continue
   key=(u,v) if u<v else (v,u)
   if key in edge_meta:
    if length<G[u][v]['weight']:G[u][v]['weight']=length
    continue
   G.add_edge(u,v,weight=length)
   edge_meta[key]=(wid,tags.get('highway',''),tags.get('bridge',''),tags.get('tunnel',''),tags.get('layer',''))
   kept_ways.add(wid)
 # keep all components for access, isolated components are not fabricated together
 print('Routing graph',G.number_of_nodes(),'nodes',G.number_of_edges(),'edges',nx.number_connected_components(G),'components',flush=True)
 return G,xy,edge_meta,dict(rej),len(kept_ways),n_all,w_all

def graph_arrays(G,xy,meta,boundary):
 nodeids=list(G.nodes);idx={n:i for i,n in enumerate(nodeids)}
 bounds=boundary.to_crs(32651).copy().reset_index(drop=True)
 poly=list(bounds.geometry); names=bounds.subdistrict_name.tolist()
 ed=[];geom=[];origin=[]
 for u,v,dat in G.edges(data=True):
  key=(u,v) if u<v else (v,u)
  a,b=xy[u],xy[v];mid=Point((a[0]+b[0])/2,(a[1]+b[1])/2)
  zone=next((i for i,p in enumerate(poly) if p.covers(mid)),-1)
  g=LineString([a,b]);wi,hw,bridge,tunnel,layer=meta[key]
  ed.append((idx[u],idx[v],float(dat['weight']),zone,wi,hw,bridge,tunnel,layer))
  geom.append(g);origin.append((u,v))
 df=pd.DataFrame(ed,columns=['u_index','v_index','length_m','zone','osm_way_id','highway','bridge','tunnel','layer'])
 df['u_id']=[u for u,v in origin];df['v_id']=[v for u,v in origin]
 def maxcomp():
  comps=sorted(nx.connected_components(G),key=len,reverse=True)
  largest=comps[0]
  total=df.length_m.sum();largest_len=df[[u in largest for u,v in origin]].length_m.sum()
  return {'components':len(comps),'largest_node_share':len(largest)/G.number_of_nodes(),'largest_length_share':largest_len/total,'all_length_km':total/1000,'district_length_km':df.loc[df.zone>=0,'length_m'].sum()/1000}
 return df,geom,nodeids,idx,xy,names,maxcomp()

def crossgrade_audit(edges,lines):
 # audit all bridge/tunnel segments against different OSM-ID segments at geometric crossings
 flagged=edges[(edges.bridge.astype(str).str.lower().isin(['yes','true','1']) | edges.tunnel.astype(str).str.lower().isin(['yes','true','1']) | edges.layer.astype(str).isin(['1','-1','2','-2','3','-3','4','-4']))]
 tree=STRtree(lines);pairs=[]
 for i in flagged.index:
  a=lines[i]; u,v=edges.loc[i,['u_id','v_id']]
  for j in tree.query(a):
   if j<=i:continue
   b=lines[j]
   if edges.at[j,'osm_way_id']==edges.at[i,'osm_way_id']:continue
   if set([u,v])&set([edges.at[j,'u_id'],edges.at[j,'v_id']]):continue
   if a.crosses(b):
    pt=a.intersection(b)
    pairs.append({'edge_i':int(i),'edge_j':int(j),'osm_way_i':int(edges.at[i,'osm_way_id']),'osm_way_j':int(edges.at[j,'osm_way_id']),
      'bridge_i':edges.at[i,'bridge'],'bridge_j':edges.at[j,'bridge'],'tunnel_i':edges.at[i,'tunnel'],'tunnel_j':edges.at[j,'tunnel'],
      'layer_i':edges.at[i,'layer'],'layer_j':edges.at[j,'layer'],'x':pt.x,'y':pt.y,'junction_created':False})
 return pd.DataFrame(pairs)

def audit_study_crossings(edges,lines):
 """Unshared geometric crossings inside Yangpu, including no-tag at-grade cases."""
 sub=edges[edges.zone>=0].reset_index(drop=True)
 subgeom=[lines[i] for i in edges.index[edges.zone>=0]]
 pairs=STRtree(subgeom).query(subgeom,predicate='crosses')
 rows=[]
 for i,j in zip(*pairs):
  if i>=j:continue
  a,b=sub.iloc[i],sub.iloc[j]
  if a.osm_way_id==b.osm_way_id or ({a.u_id,a.v_id}&{b.u_id,b.v_id}):continue
  grade_any=any(str(v).lower() in ('yes','true','1') for v in [a.bridge,b.bridge,a.tunnel,b.tunnel]) or any(str(v) not in ('','0','None','nan') for v in [a.layer,b.layer])
  rows.append({'edge_i':int(i),'edge_j':int(j),'osm_way_i':int(a.osm_way_id),'osm_way_j':int(b.osm_way_id),
   'highway_i':a.highway,'highway_j':b.highway,'bridge_i':a.bridge,'bridge_j':b.bridge,'tunnel_i':a.tunnel,'tunnel_j':b.tunnel,
   'layer_i':a.layer,'layer_j':b.layer,'tagged_grade_separated':bool(grade_any)})
 return pd.DataFrame(rows)

def snap_sites(sites,lines,G,edges,nodelist):
 tree=STRtree(lines)
 snapped=[];site_nodes=[]
 for ix,row in sites.iterrows():
  pt=row.geometry;ei=int(tree.nearest(pt));line=lines[ei];d=pt.distance(line)
  t=line.project(pt);ln=line.length
  u=int(edges.at[ei,'u_id']);v=int(edges.at[ei,'v_id'])
  site_id=f'facility_{ix}'
  G.add_node(site_id)
  G.add_edge(site_id,u,weight=float(d+t))
  G.add_edge(site_id,v,weight=float(d+(ln-t)))
  site_nodes.append(site_id)
  snapped.append({'facility_type':row.facility_type,'facility_name':row.facility_name,'facility_node':site_id,'osm_way_id':int(edges.at[ei,'osm_way_id']),
    'snap_distance_m':float(d),'projected_fraction':float(t/max(1e-6,ln)),'connector_cost_m':float(d),'edge_index':ei})
 return pd.DataFrame(snapped),site_nodes

def coverage(edge_frame,dist,minidx=None):
 L=edge_frame['length_m'].to_numpy();u=edge_frame['u_index'].to_numpy();v=edge_frame['v_index'].to_numpy()
 zu=edge_frame['zone'].to_numpy();valid=zu>=0
 result={}
 for minutes,radius in RADIUS.items():
  left=np.clip(radius-dist[u],0,L)
  right=np.clip(radius-dist[v],0,L)
  cover=np.minimum(L,left+right)
  numer=np.bincount(zu[valid],weights=cover[valid],minlength=12)
  result[minutes]=numer
 return result

def get_array_dist(G,starts,ni,cutoff=1080):
 out=np.full(len(ni),np.inf,dtype=np.float64)
 if isinstance(starts,list):
  src=nx.multi_source_dijkstra_path_length(G,starts,cutoff=cutoff,weight='weight')
 else:
  src=nx.single_source_dijkstra_path_length(G,starts,cutoff=cutoff,weight='weight')
 for node,meters in src.items():
  if node in ni:out[ni[node]]=meters
 return out

def select_candidates(G,xy,edges,names,boundary,grid=240):
 # candidate NODES, with no parcel/buildability claim, 200m lattice to bound compute cost
 ground=defaultdict(list)
 for row in edges.itertuples():
  if row.zone<0:continue
  if str(row.bridge).lower() in ['yes','true','1'] or str(row.tunnel).lower() in ['yes','true','1'] or str(row.layer) not in ['', '0', 'None','nan']:
   continue
  for n in (row.u_id,row.v_id):ground[row.zone].append(n)
 sites=[]
 for zone,ids in ground.items():
  bins={}
  for n in set(ids):
   x,y=xy[n]; k=(int(x//grid),int(y//grid))
   if k not in bins:bins[k]=n
  for n in bins.values():
   sites.append({'candidate_node':n,'zone':zone,'subdistrict':names[zone],'x':xy[n][0],'y':xy[n][1],'candidate_basis':f'at_grade_pedestrian_node_grid_{grid}m','planning_buildability':'unknown'})
 return pd.DataFrame(sites).sort_values(['zone','candidate_node']).reset_index(drop=True)

def do_experiment(G,edges,nodelist,idx,facilities,snap,candidates,names,boundary):
 road_edge=edges.zone.to_numpy()>=0
 zone=edges.zone.to_numpy()[road_edge]
 length=edges.length_m.to_numpy()[road_edge]
 den=np.bincount(zone,weights=length,minlength=12)
 district_area=(boundary.to_crs(32651).set_index('subdistrict_name').loc[names].geometry.area.to_numpy()/1e6)
 pop=pd.read_csv(ROOT/'data/raw/yangpu_subdistrict_resident_population_census2020.csv')
 population=pop.set_index('subdistrict_name').loc[names].population_total.to_numpy()
 base={}; suprows=[];covrows=[]
 for service in SERVICES:
  nodes=snap.loc[snap.facility_type==service,'facility_node'].tolist()
  arr=get_array_dist(G,nodes,idx)
  base[service]=arr
  cover=coverage(edges,arr)
  counts=np.bincount(facilities.loc[facilities.facility_type==service,'zone'].to_numpy(),minlength=12)
  for z,name in enumerate(names):
   suprows.append({'service':service,'subdistrict':name,'count_verified':int(counts[z]),'population_census2020':int(population[z]),'area_km2':district_area[z],
    'network_km':den[z]/1000,'facilities_per_10k':counts[z]/population[z]*10000,'facilities_per_km2':counts[z]/district_area[z],
    'facilities_per_100km_network':counts[z]/(den[z]/100000) if den[z]>0 else np.nan})
   for t in THRESHOLDS:covrows.append({'service':service,'subdistrict':name,'threshold_min':t,'covered_network_m':cover[t][z],
    'total_network_m':den[z],'network_coverage_share':cover[t][z]/den[z] if den[z] else np.nan})
 pd.DataFrame(suprows).to_csv(TBL/'supply_verified.csv',index=False)
 pd.DataFrame(covrows).to_csv(TBL/'observed_accessibility.csv',index=False)
 print('generating candidate accessibility changes:',len(candidates), 'nodes',flush=True)
 # each candidate node Dijkstra once; evaluate gains against each service observed distance
 service_base_len={s:coverage(edges,base[s]) for s in SERVICES}
 summaries=[]
 for i,r in enumerate(candidates.itertuples()):
  cd=get_array_dist(G,int(r.candidate_node),idx)
  for service in SERVICES:
   trial=coverage(edges,np.minimum(cd,base[service]))
   for minutes in THRESHOLDS:
    gain=trial[minutes]-service_base_len[service][minutes]
    summaries.append({'candidate_id':i,'service':service,'zone':r.zone,'subdistrict':r.subdistrict,'threshold_min':minutes,
      'district_gain_m':float(gain.sum()),'target_subdistrict_gain_m':float(gain[r.zone]),'gain_percent_of_district_network':float(gain.sum()/den.sum()*100)})
  if (i+1)%100==0:print('candidate',i+1,'/',len(candidates),flush=True)
 gain=pd.DataFrame(summaries);gain.to_csv(TBL/'candidate_marginal_gain.csv',index=False)
 supply=pd.DataFrame(suprows); decisions=[]
 for (service,minutes),df in gain.groupby(['service','threshold_min']):
  oracle_gain=df.district_gain_m.max()
  best=df.sort_values(['district_gain_m','candidate_id'],ascending=[False,True]).iloc[0]
  for proxy in ['facilities_per_10k','facilities_per_km2','facilities_per_100km_network']:
   tmp=supply[supply.service==service].sort_values([proxy,'subdistrict'])
   chosen=tmp.iloc[0].subdistrict
   subset=df[df.subdistrict==chosen]
   if subset.empty:continue
   policy_gain=subset.district_gain_m.mean()
   optimistic=subset.district_gain_m.max()
   decisions.append({'service':service,'threshold_min':minutes,'proxy':proxy,'selected_subdistrict':chosen,
      'n_candidate_sites':len(subset),'policy':'lowest_supply_proxy_then_uniform_candidate_within_subdistrict',
      'policy_expected_gain_m':float(policy_gain),'policy_gain_min_m':float(subset.district_gain_m.min()),'policy_gain_max_m':float(optimistic),
      'oracle_gain_m':float(oracle_gain),'oracle_subdistrict':best.subdistrict,'oracle_candidate_id':int(best.candidate_id),
      'decision_regret_m':float(oracle_gain-policy_gain),'regret_fraction':float((oracle_gain-policy_gain)/oracle_gain) if oracle_gain>0 else np.nan,
      'optimistic_zone_regret_m':float(oracle_gain-optimistic),
      'evaluation_unit':'pedestrian_network_length_m','site_buildability_unknown':True})
 pd.DataFrame(decisions).to_csv(TBL/'decision_regret.csv',index=False)
 # proxy rank versus network accessibility and correlated spatial data, descriptive only
 out=[];cov=pd.DataFrame(covrows)
 for (service,t),g in cov.groupby(['service','threshold_min']):
  ss=supply[supply.service==service].merge(g[['subdistrict','network_coverage_share']],on='subdistrict')
  for proxy in ['facilities_per_10k','facilities_per_km2','facilities_per_100km_network']:
   a=spearmanr(ss[proxy],ss.network_coverage_share)
   out.append({'service':service,'threshold_min':t,'proxy':proxy,'spearman_rho':a.statistic,'p_naive_not_inferential':a.pvalue,'n_subdistricts':len(ss)})
 pd.DataFrame(out).to_csv(TBL/'descriptive_proxy_accessibility.csv',index=False)
 return gain,pd.DataFrame(decisions),supply,pd.DataFrame(covrows)

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--pbf',type=Path,required=True);ap.add_argument('--legacy-gpkg',type=Path,required=True);ap.add_argument('--skip-figure',action='store_true');ap.add_argument('--grid-m',type=int,default=240);ap.add_argument('--sensitivity',action='store_true');ap.add_argument('--connect-audit-atgrade',action='store_true');args=ap.parse_args()
 if args.grid_m<100:raise ValueError('candidate grid spacing must be >=100m')
 global TBL
 if args.sensitivity:
  TBL=ROOT/'outputs/sensitivity'/(f'grid_{args.grid_m}m_atgrade_connected' if args.connect_audit_atgrade else f'grid_{args.grid_m}m')
  TBL.mkdir(parents=True,exist_ok=True)
 boundary=gpd.read_file(args.legacy_gpkg,layer='boundary_subdistrict').to_crs(4326)
 assert len(boundary)==12 and boundary.geometry.is_valid.all()
 ready=gpd.read_file(args.legacy_gpkg,layer='facility_accessibility_ready').to_crs(32651)
 ready=ready[ready.facility_type.isin(SERVICES)].copy().reset_index(drop=True)
 all_candidates=gpd.read_file(args.legacy_gpkg,layer='facility_geometry_candidates')
 all_candidates=all_candidates[all_candidates.facility_type.isin(SERVICES)]
 key=lambda d:set(zip(d.facility_type,d.facility_name))
 excluded=key(all_candidates)-key(ready)
 assert len(ready)==83 and len(excluded)==6,(len(ready),excluded)
 assert excluded==set((s,n) for s,n,_,_ in REVIEW),(excluded,REVIEW)
 evidence=[]
 for s,n,reason,url in REVIEW:
  row=all_candidates[(all_candidates.facility_type==s)&(all_candidates.facility_name==n)].iloc[0]
  evidence.append({'facility_type':s,'facility_name':n,'original_official_address':row.address,
   'status':'excluded_from_spatial_model_retained_in_source_audit','reason':reason,'evidence_url':url,
   'original_candidate_geometry_is_not_used':True})
 pd.DataFrame(evidence).to_csv(QA/'six_facilities_evidence_and_exclusion.csv',index=False)
 print('official/inventory',len(all_candidates),'legacy accepted geometry retained',len(ready),'excluded',len(excluded),flush=True)
 # assign facility subdistrict via existing geocoded source; primary coordinate QA
 bound_m=boundary.to_crs(32651).reset_index(drop=True)
 ready['zone']=[next((i for i,p in enumerate(bound_m.geometry) if p.covers(x)), -1) for x in ready.geometry]
 if (ready.zone<0).any():raise RuntimeError('verified facility coordinates outside study area, require manual audit')
 G,xy,meta,rej,nways,n_all,w_all=construct_graph(args.pbf,boundary)
 edges,lines,nodeids,idx,xy,names,qa=graph_arrays(G,xy,meta,boundary)
 if args.connect_audit_atgrade:
  # Explicit scenario for the single questionable at-grade crossing, not baseline.
  pair=None
  ids=[225995002,1324895009]
  left=[i for i,v in enumerate(edges.osm_way_id) if v==ids[0] and edges.at[i,'zone']>=0]
  right=[i for i,v in enumerate(edges.osm_way_id) if v==ids[1] and edges.at[i,'zone']>=0]
  for i in left:
   for j in right:
    if lines[i].crosses(lines[j]):pair=(i,j);break
   if pair:break
  if pair is None:raise ValueError('Expected at-grade crossing not found for sensitivity')
  i,j=pair;point=lines[i].intersection(lines[j]);crossnode=-991005
  xy[crossnode]=(point.x,point.y)
  for edge_i in (i,j):
   u,v=int(edges.at[edge_i,'u_id']),int(edges.at[edge_i,'v_id'])
   tags=meta[(u,v) if u<v else (v,u)]
   line=lines[edge_i];off=float(line.project(point));L=float(line.length)
   G.remove_edge(u,v)
   meta.pop((u,v) if u<v else (v,u))
   for a,b,dist in [(u,crossnode,off),(crossnode,v,L-off)]:
    if dist>0.001:
     G.add_edge(a,b,weight=dist)
     meta[(a,b) if a<b else (b,a)]=tags
  edges,lines,nodeids,idx,xy,names,qa=graph_arrays(G,xy,meta,boundary)
 # degree-2 OSM street nodes are retained; unshared XY crossings are disconnected
 grade=crossgrade_audit(edges,lines)
 if len(grade):grade.to_csv(QA/'non_connected_geometric_crossings.csv',index=False)
 else:pd.DataFrame(columns=['edge_i','edge_j','junction_created']).to_csv(QA/'non_connected_geometric_crossings.csv',index=False)
 audit=audit_study_crossings(edges,lines)
 audit.to_csv((TBL if args.sensitivity else QA)/'unshared_crossings_district.csv',index=False)
 print('study-area unshared crossings',len(audit),'at-grade without tag',int((~audit.tagged_grade_separated).sum()),flush=True)
 print('grade-tagged geometric crossings without common OSM node',len(grade),flush=True)
 baseG=G.copy()
 snap,sites=snap_sites(ready,lines,G,edges,nodeids)
 snap.to_csv(QA/'facility_connector_distances_full.csv',index=False)
 quants=snap.snap_distance_m.quantile([0,.25,.5,.75,.9,.95,.99,1]).reset_index();quants.columns=['quantile','meters'];quants.to_csv(QA/'snap_distance_empirical_quantiles.csv',index=False)
 # network topology: explicit OSM node ID avoids false geometric junctions
 qa_result={'input_pbf_sha256':sha(args.pbf),'legacy_gpkg_sha256':sha(args.legacy_gpkg),'reported_study_subdistricts':len(boundary),
  'raw_osm_nodes_seen':n_all,'raw_osm_ways_seen':w_all,'routing_osm_ways_retained':nways,'routing_graph_nodes':baseG.number_of_nodes(),
  'routing_graph_edges':baseG.number_of_edges(),'edge_grade_crossings_retained_disconnected':len(grade),'network_topology_policy':('OSM IDs + one unverified at-grade crossing (sensitivity ONLY)' if args.connect_audit_atgrade else 'OSM shared node ID only'),
  'legacy_facility_coordinates_included_pending_external_validation':len(ready),'facility_coordinates_excluded':len(excluded),'snap_distance_no_hard_cap':True,
  'routing_threshold_m':RADIUS,'walking_speed_m_per_s':SPEED,'network_components':qa,'exclusion_by_way_tag':rej,
  'site_candidate_assumption':'pedestrian-network nodes; actual buildability unknown',
  'coverage_measure':'length of reachable pedestrian edges inside subdistrict; no population coverage inference'}
 # candidates from undisturbed street nodes graph with no facility synthetic nodes
 candidates=select_candidates(baseG,xy,edges,names,boundary,grid=args.grid_m)
 candidates.to_csv((TBL if args.sensitivity else SP)/'hypothetical_candidate_nodes.csv',index=False)
 qa_result['candidate_sites']=len(candidates); qa_result['candidate_count_by_subdistrict']=candidates.groupby('subdistrict').size().to_dict()
 ((TBL if args.sensitivity else QA)/'rebuild_qa.json').write_text(json.dumps(qa_result,ensure_ascii=False,indent=2),encoding='utf8')
 print('network QA saved',qa,'snap p50,p95',snap.snap_distance_m.median(),snap.snap_distance_m.quantile(.95),flush=True)
 gain,decision,supply,cov=do_experiment(G,edges,nodeids,idx,ready,snap,candidates,names,boundary)
 print('decision preview',decision[['service','threshold_min','proxy','selected_subdistrict','regret_fraction']].head(12).to_string(index=False),flush=True)
 if args.sensitivity:
  print('SENSITIVITY DONE',args.grid_m,flush=True)
  return
 # geographical derivatives; separate generated outputs from raw
 egeo=gpd.GeoDataFrame(edges,geometry=lines,crs=32651)
 # Ensure rerunning the pipeline never appends duplicate spatial records.
 out_gpkg=SP/'p06_rebuilt_network.gpkg'
 if out_gpkg.exists():out_gpkg.unlink()
 egeo.to_file(out_gpkg,layer='osm_node_identity_edges',driver='GPKG')
 bound_m.to_file(out_gpkg,layer='study_subdistricts',driver='GPKG')
 ready[['facility_type','facility_name','zone','geometry']].to_file(out_gpkg,layer='verified_facilities',driver='GPKG')
 gpd.GeoDataFrame(candidates,geometry=gpd.points_from_xy(candidates.x,candidates.y),crs=32651).to_file(out_gpkg,layer='hypothetical_candidate_nodes',driver='GPKG')
 print('DONE',flush=True)

if __name__=='__main__':main()
