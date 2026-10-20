#!/usr/bin/env python3
"""Reproducible schematic illustration for P06 facility location strategies.
Visual conventions follow academic-figure-skill and scientific-visualization.
No empirical geography, facility locations, or measured benefits are implied.
"""
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle, FancyBboxPatch, FancyArrowPatch
from matplotlib.lines import Line2D

O=Path(__file__).resolve().parents[1]/'outputs/figures/all_figures_png'
O.mkdir(parents=True,exist_ok=True)
plt.rcParams.update({'font.family':'DejaVu Sans','pdf.fonttype':42,'svg.fonttype':'none','font.size':10})
NAVY='#203549'; MUTED='#5d6973'; ROAD='#c4cbd0'; BORDER='#a6b4bd'; A='#187ca3'; B='#b65d32'; OLD='#2b3d4b'; LIGHT='#f4f7f9'
fig=plt.figure(figsize=(12.7,7.05),facecolor='white')
ax=fig.add_axes([.025,.06,.95,.90]); ax.set_xlim(0,120);ax.set_ylim(0,70);ax.axis('off')

def txt(x,y,s,fs=10,c=NAVY,weight='normal',ha='left'):
 ax.text(x,y,s,fontsize=fs,color=c,fontweight=weight,ha=ha,va='center')
def rounded(x,y,w,h,fill='white',stroke=BORDER,r=1.1):
 ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle=f'round,pad=0.3,rounding_size={r}',lw=1,edgecolor=stroke,facecolor=fill))
def arrow(x,y,xx,yy,col=NAVY):
 ax.add_patch(FancyArrowPatch((x,y),(xx,yy),arrowstyle='-|>',mutation_scale=12,lw=1.5,color=col))

txt(2,67,'How street-priority rules change facility placement',17,weight='bold')
txt(2,63.6,'Same facilities, road network, candidate sites and coverage objective; different search spaces',10.2,MUTED)

# Shared spatial schematic, drawn identically except restricted street and highlighted marginal road segments.
def network(x0, y0, restricted=False):
 width=52; height=27; sep=width/3
 # streets as conceptual districts: 3 columns x 2 rows
 for iy in range(2):
  for ix in range(3):
   is_restricted = (ix==0 and iy==0)
   face = '#e4f1f6' if restricted and is_restricted else '#f6f8f9'
   ax.add_patch(Rectangle((x0+ix*sep,y0+iy*height/2),sep,height/2,facecolor=face,edgecolor='#d4dce2',lw=.9,zorder=0))
   txt(x0+ix*sep+2,y0+iy*height/2+height/2-3,'S'+str(iy*3+ix+1),8.5,'#71818c')
 for i in range(7):
  xx=x0+i*(width/6)
  ax.plot([xx,xx],[y0,y0+height],c=ROAD,lw=2.2,zorder=1)
 for j in range(5):
  yy=y0+j*(height/4)
  ax.plot([x0,x0+width],[yy,yy],c=ROAD,lw=2.2,zorder=1)
 # identical candidate sites, each at road junction
 dots=[(8.67,8.25),(17.33,24.75),(26,8.25),(34.67,16.5),(43.33,24.75),(52,8.25)]
 for dx,dy in dots:
  ax.add_patch(Circle((x0+dx,y0+dy),.72,facecolor='white',edgecolor='#607381',lw=1.3,zorder=4))
 # 3 existing facilities identical
 for dx,dy in [(8.67,24.75),(26,24.75),(43.33,8.25)]:
  ax.scatter(x0+dx,y0+dy,s=95,marker='s',c=OLD,edgecolors='white',linewidths=1,zorder=5)
 if restricted:
  p=(x0+8.67,y0+8.25)
  roads=[((x0,y0+8.25),(x0+17.33,y0+8.25)),((x0+8.67,y0),(x0+8.67,y0+16.5))]
  col=A
 else:
  p=(x0+34.67,y0+16.5)
  roads=[((x0+26,y0+16.5),(x0+52,y0+16.5)),((x0+34.67,y0+8.25),(x0+34.67,y0+24.75)),((x0+26,y0+8.25),(x0+26,y0+16.5))]
  col=B
 for (x1,y1),(x2,y2) in roads:
  ax.plot([x1,x2],[y1,y2],c=col,lw=4.0,solid_capstyle='round',zorder=3)
 ax.scatter(*p,s=220,marker='*',c=col,edgecolors='white',linewidths=.9,zorder=6)
 # selected street border only left
 if restricted:
  ax.add_patch(Rectangle((x0,y0),sep,height/2,fill=False,ec=A,lw=2.6,ls=(0,(4,2)),zorder=7))
 return p

rounded(2,21.5,56,37.5,'white','#ced9df')
rounded(62,21.5,56,37.5,'white','#ced9df')
txt(5,56.5,'A   Three supply-proxy strategies',12.4,A,'bold')
txt(65,56.5,'B   District-wide greedy reference',12.4,B,'bold')
txt(5,53.3,'Choose the lowest-supply street first',9.7,MUTED)
txt(65,53.3,'Compare every remaining site in the district',9.7,MUTED)
network(4,23.7,restricted=True)
network(64,23.7,restricted=False)

# legends
ax.scatter(5.2,18.3,s=65,marker='s',c=OLD)
txt(7.0,18.3,'Existing facility',8.8)
ax.scatter(26.3,18.3,s=70,marker='o',facecolors='white',edgecolors='#607381')
txt(28.1,18.3,'Candidate site',8.8)
ax.scatter(50.2,18.3,s=100,marker='*',c=A)
txt(52.1,18.3,'Selected site',8.8)
ax.plot([73,78],[18.3,18.3],c=A,lw=4)
txt(80,18.3,'Illustrative newly covered roads',8.8)

rounded(2,8.3,116,7.1,LIGHT,'#d1dbe1')
txt(5,13,'Common selection principle: maximize the CURRENT marginal coverage gain',10.3,NAVY,'bold')
txt(5,10.2,'A: maximize within lowest-supply street(s)    |    B: maximize across all district candidate sites',9.8)
arrow(31.0,21.4,31,15.7,A)
arrow(89,21.4,89,15.7,B)
txt(3,4.8,'Repeat after each addition (1–40 facilities): update covered roads and remaining candidates; A also updates street supply.',9.4,NAVY)
txt(3,2.1,'SCHEMATIC ONLY — street cells, road segments and placement choices are illustrative, not Yangpu geospatial observations.',8.4,MUTED)

for ext in ('png'):
 fig.savefig(O/('Facility_Location_Strategies.'+ext),dpi=300,bbox_inches='tight',pad_inches=.15,facecolor='white')
plt.close(fig)
print('Saved figure formats')
