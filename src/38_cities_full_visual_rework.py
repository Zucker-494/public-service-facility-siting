#!/usr/bin/env python3
from pathlib import Path
import json
import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
from matplotlib.lines import Line2D

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "manuscript" / "cities" / "figures_reworked"
OUT.mkdir(parents=True, exist_ok=True)
SEQ = ROOT / "outputs" / "sequential_investment"
ROB = ROOT / "outputs" / "walkability_robustness"
POP = ROOT / "outputs" / "population_weighted_sensitivity"
BND = ROOT / "outputs" / "failure_condition_multivariable"

COL = {
    "greedy":"#263746",
    "per_10k":"#D98C3F",
    "per_km2":"#2A9D8F",
    "per_100km":"#7B61A8",
    "healthcare":"#3B82A0",
    "elderly_care":"#C26A5A",
    "culture":"#6A8E3A",
    "district":"#2F6B8A",
    "equal":"#B55D4C",
}
PLAB = {
    "per_10k":"Per 10,000 residents",
    "per_km2":"Per km²",
    "per_100km":"Per 100 km roads",
    "facilities_per_10k":"Per 10,000 residents",
    "facilities_per_km2":"Per km²",
    "facilities_per_100km_network":"Per 100 km roads",
}
SLAB = {"healthcare":"Healthcare","elderly_care":"Elderly care","culture":"Cultural facilities"}
OLAB = {
    "district":"District-wide coverage",
    "equal":"Equal-subdistrict coverage",
    "district_gain_m":"District-wide coverage",
    "gain_equal_street_mean_pp":"Equal-subdistrict coverage",
}
PROXY = ["per_10k","per_km2","per_100km"]
RULES = ["facilities_per_10k","facilities_per_km2","facilities_per_100km_network"]

plt.rcParams.update({
    "font.family":"DejaVu Sans",
    "font.size":10.5,
    "axes.titlesize":11.5,
    "axes.labelsize":10.5,
    "xtick.labelsize":9.5,
    "ytick.labelsize":9.5,
    "legend.fontsize":9.2,
    "axes.spines.top":False,
    "axes.spines.right":False,
    "axes.linewidth":0.9,
    "grid.color":"#D8DDE2",
    "grid.alpha":0.6,
    "grid.linewidth":0.6,
    "pdf.fonttype":42,
    "ps.fonttype":42,
})

def save(fig, stem):
    fig.savefig(OUT/f"{stem}.png", dpi=320, bbox_inches="tight", facecolor="white")
    fig.savefig(OUT/f"{stem}.pdf", bbox_inches="tight", facecolor="white")
    plt.close(fig)

def panel(ax, label, x=-0.10, y=1.04):
    ax.text(x, y, label, transform=ax.transAxes, fontsize=12.5, fontweight="bold", va="bottom")

def attach_zones(bound, cand):
    if "zone" in bound.columns:
        out = bound.copy()
        out["zone"] = out["zone"].astype(int)
        return out
    pts = gpd.GeoDataFrame(cand[["zone"]].copy(), geometry=gpd.points_from_xy(cand.x, cand.y), crs=bound.crs)
    bb = bound.reset_index(drop=True).reset_index().rename(columns={"index":"poly_idx"})
    joined = gpd.sjoin(pts, bb[["poly_idx","geometry"]], predicate="within", how="left").dropna(subset=["poly_idx"])
    mapping = joined.groupby("poly_idx").zone.agg(lambda s: int(s.mode().iloc[0]))
    out = bb.set_index("poly_idx").copy()
    out["zone"] = out.index.map(mapping)
    assert not out.zone.isna().any()
    assert int(out.zone.nunique()) == int(cand.zone.nunique())
    out["zone"] = out.zone.astype(int)
    return out.reset_index(drop=True)

def fig1_study_area():
    gpkg = ROOT/"data/processed/p06_refined_clean.gpkg"
    bound = gpd.read_file(gpkg, layer="study_subdistricts")
    edges = gpd.read_file(gpkg, layer="osm_node_identity_edges")
    edges = edges[edges["zone"] >= 0]
    cand = pd.read_csv(ROOT/"data/processed/hypothetical_candidate_nodes.csv", encoding="utf-8-sig")
    bound = attach_zones(bound, cand)
    reg = pd.read_csv(ROOT/"data/curated/official_facility_registry_89_address_audited.csv", encoding="utf-8-sig")
    reg = reg[reg.wgs84_lon.notna() & reg.wgs84_lat.notna()].copy()
    fac = gpd.GeoDataFrame(reg, geometry=gpd.points_from_xy(reg.wgs84_lon, reg.wgs84_lat), crs="EPSG:4326").to_crs(edges.crs)
    cg = gpd.GeoDataFrame(cand, geometry=gpd.points_from_xy(cand.x, cand.y), crs=edges.crs)

    fig = plt.figure(figsize=(10.8,5.8), layout="constrained")
    gs = fig.add_gridspec(1,2,width_ratios=[4.3,1.7])
    ax = fig.add_subplot(gs[0,0])
    lax = fig.add_subplot(gs[0,1])
    bound.plot(ax=ax, facecolor="#F5F2EA", edgecolor="#60666B", linewidth=0.9)
    edges.plot(ax=ax, color="#B7BEC4", linewidth=0.35, alpha=0.78)
    cg.plot(ax=ax, color="#7CA8B7", markersize=2.4, alpha=0.42)
    markers={"healthcare":"o","elderly_care":"^","culture":"s"}
    for svc in ["healthcare","elderly_care","culture"]:
        q=fac[fac.facility_type==svc]
        q.plot(ax=ax,color=COL[svc],marker=markers[svc],markersize=28,edgecolor="white",linewidth=.5)
    zone_name=cand[["zone","subdistrict_en"]].drop_duplicates().set_index("zone").subdistrict_en.to_dict()
    for r in bound.itertuples():
        p=r.geometry.representative_point()
        ax.text(p.x,p.y,zone_name[r.zone].replace(" Subdistrict",""),fontsize=7.2,ha="center",va="center",color="#30363B")
    ax.set_axis_off()
    ax.set_title("Yangpu District, Shanghai", loc="left", fontweight="semibold", pad=7)

    lax.set_axis_off(); lax.set_xlim(0,1); lax.set_ylim(0,1)
    lax.text(.02,.96,"Study inputs",fontsize=12,fontweight="semibold",va="top")
    handles=[
        Line2D([0],[0],marker="o",linestyle="none",markerfacecolor="#7CA8B7",alpha=.55,markeredgecolor="none",markersize=6,label="1,132 candidate sites"),
        Line2D([0],[0],marker="o",linestyle="none",markerfacecolor=COL["healthcare"],markeredgecolor="white",markersize=8,label="Healthcare"),
        Line2D([0],[0],marker="^",linestyle="none",markerfacecolor=COL["elderly_care"],markeredgecolor="white",markersize=8,label="Elderly care"),
        Line2D([0],[0],marker="s",linestyle="none",markerfacecolor=COL["culture"],markeredgecolor="white",markersize=8,label="Cultural facilities"),
    ]
    lax.legend(handles=handles,loc="upper left",bbox_to_anchor=(0,.86),frameon=False,borderaxespad=0)
    lax.text(.02,.50,"Existing inventory",fontsize=10,fontweight="semibold")
    lax.text(.02,.455,"89 facilities in total",fontsize=9.3)
    lax.text(.02,.37,"Location uncertainty",fontsize=10,fontweight="semibold")
    lax.text(.02,.325,"Six facilities without accepted inherited\ncoordinates are represented through five\naddress-based location scenarios.",fontsize=9.0,linespacing=1.35,va="top")
    lax.text(.02,.12,"Pedestrian network: 798.6 km",fontsize=9.0,color="#555")
    save(fig,"fig1_study_area")

def fig2_framework():
    fig, ax = plt.subplots(figsize=(10.8,5.4), layout="constrained")
    ax.set_axis_off(); ax.set_xlim(0,1); ax.set_ylim(0,1)
    def box(x,y,w,h,text,fc,fs=10,weight="normal"):
        p=FancyBboxPatch((x,y),w,h,boxstyle="round,pad=0.012,rounding_size=0.018",facecolor=fc,edgecolor="#5D6368",linewidth=.95)
        ax.add_patch(p); ax.text(x+w/2,y+h/2,text,ha="center",va="center",fontsize=fs,fontweight=weight)
    def arrow(x1,y1,x2,y2):
        ax.add_patch(FancyArrowPatch((x1,y1),(x2,y2),arrowstyle="-|>",mutation_scale=12,linewidth=1.0,color="#666"))
    box(.18,.84,.64,.10,"Planning objective\nDistrict-wide road coverage  |  Equal-subdistrict coverage","#F2F4F5",10.3,"semibold")
    box(.06,.62,.37,.14,"Existing provision\n89 facilities + pedestrian network","#E9F0F3",10)
    box(.57,.62,.37,.14,"Candidate opportunity\n1,132 network sites","#E9F0F3",10)
    box(.06,.39,.37,.15,"Supply-based priority\nper 10k  |  per km²  |  per 100 km roads","#F7E4CD",10)
    box(.57,.39,.37,.15,"Network-greedy reference\nmaximum marginal gain","#DDEBE8",10)
    box(.30,.18,.40,.12,"Sequential addition\n1–40 facilities; 5/10/15 min","#EAE4F1",10)
    box(.27,.03,.46,.09,"Compare first-step validity, spatial mismatch,\nsequential loss, sensitivity and robustness","#F3EEE5",9.3)
    arrow(.36,.84,.24,.76); arrow(.64,.84,.76,.76)
    arrow(.245,.62,.245,.54); arrow(.755,.62,.755,.54)
    arrow(.245,.39,.43,.30); arrow(.755,.39,.57,.30)
    arrow(.50,.18,.50,.12)
    save(fig,"fig2_decision_framework")

def fig3_primary_first_step():
    d=pd.read_csv(SEQ/"indicator_failure_summary.csv")
    fig,axes=plt.subplots(1,2,figsize=(10.8,4.8),sharex=True,layout="constrained")
    xmax=68
    for ax,obj,lbl in zip(axes,["district","equal"],["A","B"]):
        q=d[d.objective==obj].set_index("proxy").loc[PROXY].reset_index()
        y=np.arange(3)
        for i,r in q.iterrows():
            c=COL[r.proxy]
            ax.hlines(y[i],r.q25_first_step_shortfall_pct,r.q75_first_step_shortfall_pct,color=c,lw=8,alpha=.28)
            ax.plot(r.median_first_step_shortfall_pct,y[i],"o",ms=8.5,color=c,mec="white",mew=.8,zorder=3)
            ax.text(xmax-1,y[i],f"{r.exact_global_best_rate_pct:.1f}% exact",ha="right",va="center",fontsize=9)
        ax.set_yticks(y,[PLAB[p] for p in PROXY]); ax.invert_yaxis()
        ax.set_xlim(0,xmax); ax.grid(axis="x")
        ax.set_title(OLAB[obj],pad=8)
        ax.set_xlabel("First-step shortfall from best available gain (%)")
        panel(ax,lbl)
    save(fig,"fig3_primary_first_step")

def fig4_spatial_mismatch():
    gpkg=ROOT/"data/processed/p06_refined_clean.gpkg"
    bound=gpd.read_file(gpkg,layer="study_subdistricts")
    cand=pd.read_csv(ROOT/"data/processed/hypothetical_candidate_nodes.csv",encoding="utf-8-sig")
    bound=attach_zones(bound,cand)
    zone_map=cand[["zone","subdistrict"]].drop_duplicates().set_index("subdistrict").zone.to_dict()
    d=pd.read_csv(SEQ/"street_opportunity_540.csv")
    q=d[(d.site_scenario=="INFERRED_89_01")&(d.service=="culture")&(d.threshold_min==10)].copy()
    q["zone"]=q.subdistrict.map(zone_map)
    vals=q.set_index("zone")
    fig=plt.figure(figsize=(10.8,8.2),layout="constrained")
    gs=fig.add_gridspec(2,2,height_ratios=[1,1.18])
    axes=[fig.add_subplot(gs[0,0]),fig.add_subplot(gs[0,1]),fig.add_subplot(gs[1,:])]
    specs=[
        ("facilities_per_10k","A  Supply scarcity: per 10,000 residents","magma_r","min","Facilities per 10,000"),
        ("facilities_per_100km_network","B  Supply scarcity: per 100 km roads","magma_r","min","Facilities per 100 km"),
        ("max_equal","C  Network opportunity: equal-subdistrict objective","viridis","max","Maximum marginal gain"),
    ]
    for ax,(field,title,cmap,mode,cblab) in zip(axes,specs):
        m=bound.merge(vals[[field]],left_on="zone",right_index=True,how="left")
        m.plot(column=field,ax=ax,cmap=cmap,edgecolor="white",linewidth=1.0,legend=True,legend_kwds={"shrink":.74,"label":cblab})
        best=q.loc[q[field].idxmin() if mode=="min" else q[field].idxmax(),"zone"]
        bound[bound.zone==best].boundary.plot(ax=ax,color="#111",linewidth=2.6)
        for r in m.itertuples():
            p=r.geometry.representative_point()
            name=cand.loc[cand.zone==r.zone,"subdistrict_en"].iloc[0].replace(" Subdistrict","")
            ax.text(p.x,p.y,name,fontsize=7.6,ha="center",va="center",
                    color="white" if field!="max_equal" and getattr(r,field)>=m[field].median() else "#222")
        ax.set_title(title,loc="left",fontweight="semibold",pad=5)
        ax.set_axis_off()
    fig.text(.5,.005,"Culture facilities, 10-minute threshold, location scenario 1. Thick outline marks the priority subdistrict.",ha="center",fontsize=9)
    save(fig,"fig4_spatial_mismatch")

def fig5_boundary_conditions():
    d=pd.read_csv(BND/"selected_boundary_condition_coefficients.csv")
    terms=["supply_opportunity_rho","opportunity_top_share","supply_cv","priority_population_share","threshold_min"]
    labels={
        "supply_opportunity_rho":"Supply–opportunity alignment",
        "opportunity_top_share":"Top-opportunity concentration",
        "supply_cv":"Cross-subdistrict supply variation",
        "priority_population_share":"Priority-subdistrict population share",
        "threshold_min":"Walking threshold",
    }
    fig,ax=plt.subplots(figsize=(10.8,5.2),layout="constrained")
    y=np.arange(len(terms))
    offsets={"district_only":-.14,"equal_subdistrict_only":.14}
    colors={"district_only":COL["district"],"equal_subdistrict_only":COL["equal"]}
    names={"district_only":"District-wide","equal_subdistrict_only":"Equal-subdistrict"}
    for model in ["district_only","equal_subdistrict_only"]:
        q=d[d.model==model].set_index("term").loc[terms].reset_index()
        yy=y+offsets[model]
        x=q.full_sample_coefficient.to_numpy()
        xmin=q.leave_one_scenario_out_min.to_numpy()
        xmax=q.leave_one_scenario_out_max.to_numpy()
        ax.errorbar(x,yy,xerr=np.vstack([x-xmin,xmax-x]),fmt="o",ms=7.5,capsize=3.5,lw=1.4,color=colors[model],label=names[model])
    ax.axvline(0,color="#777",lw=.9)
    ax.set_yticks(y,[labels[t] for t in terms]); ax.invert_yaxis()
    ax.set_xlabel("Standardised descriptive coefficient (percentage-point shortfall per 1 SD)")
    ax.grid(axis="x"); ax.legend(frameon=False,ncol=2,loc="lower right")
    save(fig,"fig5_boundary_conditions")

def fig6_absolute_coverage():
    d=pd.read_csv(ROOT/"outputs/figures/sequential_v11/figure_data_all_services_all_thresholds.csv")
    d=d[(d.threshold_min==15)&(d.objective=="district_gain_m")]
    rulelist=["network_greedy"]+RULES
    color={"network_greedy":COL["greedy"],"facilities_per_10k":COL["per_10k"],"facilities_per_km2":COL["per_km2"],"facilities_per_100km_network":COL["per_100km"]}
    ls={"network_greedy":"-","facilities_per_10k":"-","facilities_per_km2":"--","facilities_per_100km_network":"-."}
    labels={"network_greedy":"Network-greedy",**{r:PLAB[r] for r in RULES}}
    fig,axes=plt.subplots(1,3,figsize=(11.2,4.4),layout="constrained")
    for ax,svc,lbl in zip(axes,["healthcare","elderly_care","culture"],["A","B","C"]):
        for rule in rulelist:
            q=d[(d.service==svc)&(d.rule==rule)].sort_values("new_sites")
            ax.plot(np.r_[0,q.new_sites],np.r_[0,q.gain_median/1000],color=color[rule],ls=ls[rule],lw=2.25 if rule=="network_greedy" else 1.8,label=labels[rule])
        ax.set_title(SLAB[svc]); ax.set_xlabel("Added facilities"); ax.grid(axis="y")
        if ax is axes[0]: ax.set_ylabel("Additional covered road network (km)")
        panel(ax,lbl)
    h,l=axes[0].get_legend_handles_labels()
    fig.legend(h,l,ncol=2,loc="upper center",bbox_to_anchor=(.5,1.07),frameon=False)
    save(fig,"fig6_absolute_coverage")

def fig7_primary_budget():
    d=pd.read_csv(SEQ/"budget_trajectory_summary.csv")
    fig,axes=plt.subplots(1,2,figsize=(10.8,4.8),layout="constrained")
    for ax,obj,lbl in zip(axes,["district_gain_m","gain_equal_street_mean_pp"],["A","B"]):
        q=d[d.objective==obj]
        for rule in RULES:
            z=q[q.rule==rule].sort_values("new_sites")
            c=COL[{"facilities_per_10k":"per_10k","facilities_per_km2":"per_km2","facilities_per_100km_network":"per_100km"}[rule]]
            ax.fill_between(z.new_sites,z.q25_relative_difference_pct,z.q75_relative_difference_pct,color=c,alpha=.13,lw=0)
            ax.plot(z.new_sites,z.median_relative_difference_pct,color=c,lw=2.0,label=PLAB[rule])
        ax.set_title(OLAB[obj]); ax.set_xlabel("Added facilities"); ax.set_ylabel("Relative shortfall from greedy reference (%)"); ax.grid(True); panel(ax,lbl)
    axes[0].legend(frameon=False)
    save(fig,"fig7_primary_budget")

def fig8_population_weighted():
    first=pd.read_csv(POP/"population_weighted_first_step_summary.csv")
    budget=pd.read_csv(POP/"population_weighted_budget_summary.csv")
    fig,axes=plt.subplots(1,2,figsize=(10.8,4.8),layout="constrained")
    ax=axes[0]
    order=RULES
    q=first.set_index("rule").loc[order].reset_index()
    y=np.arange(3)
    for i,r in q.iterrows():
        c=COL[{"facilities_per_10k":"per_10k","facilities_per_km2":"per_km2","facilities_per_100km_network":"per_100km"}[r.rule]]
        ax.hlines(y[i],r.q25_shortfall_pct,r.q75_shortfall_pct,color=c,lw=8,alpha=.28)
        ax.plot(r.median_shortfall_pct,y[i],"o",ms=8.5,color=c,mec="white",mew=.8)
        ax.text(48,y[i],f"{r.exact_first_step_match_rate_pct:.1f}% exact",ha="right",va="center",fontsize=9)
    ax.set_yticks(y,[PLAB[r] for r in order]); ax.invert_yaxis(); ax.set_xlim(0,50); ax.grid(axis="x")
    ax.set_xlabel("Population-weighted first-step shortfall (%)"); panel(ax,"A")
    ax=axes[1]
    for rule in RULES:
        z=budget[budget.rule==rule].sort_values("new_sites")
        c=COL[{"facilities_per_10k":"per_10k","facilities_per_km2":"per_km2","facilities_per_100km_network":"per_100km"}[rule]]
        ax.fill_between(z.new_sites,z.q25_shortfall_pct,z.q75_shortfall_pct,color=c,alpha=.13,lw=0)
        ax.plot(z.new_sites,z.median_shortfall_pct,color=c,lw=2.0,marker="o",ms=3.7,label=PLAB[rule])
    ax.set_xlabel("Added facilities"); ax.set_ylabel("Population-weighted shortfall (%)"); ax.grid(True); ax.legend(frameon=False); panel(ax,"B")
    save(fig,"fig8_population_weighted")

def fig9_heterogeneity():
    d=pd.read_csv(SEQ/"indicator_failure_conditions.csv")
    agg=d.groupby(["objective","service","threshold_min","proxy"],as_index=False).first_step_shortfall_pct.median()
    rows=[(s,t) for s in ["healthcare","elderly_care","culture"] for t in [5,10,15]]
    fig,axes=plt.subplots(1,2,figsize=(11.2,6.2),layout="constrained")
    vmax=float(agg.first_step_shortfall_pct.max())
    for ax,obj,lbl in zip(axes,["district","equal"],["A","B"]):
        arr=np.array([[float(agg[(agg.objective==obj)&(agg.service==s)&(agg.threshold_min==t)&(agg.proxy==p)].first_step_shortfall_pct.iloc[0]) for p in PROXY] for s,t in rows])
        im=ax.imshow(arr,cmap="YlOrRd",vmin=0,vmax=vmax,aspect="auto")
        ax.set_xticks(range(3),[PLAB[p] for p in PROXY],rotation=12,ha="right")
        ax.set_yticks(range(len(rows)),[f"{SLAB[s]} | {t} min" for s,t in rows])
        for i in range(arr.shape[0]):
            for j in range(arr.shape[1]):
                ax.text(j,i,f"{arr[i,j]:.1f}",ha="center",va="center",fontsize=8.7)
        ax.set_title(OLAB[obj]); panel(ax,lbl)
    cb=fig.colorbar(im,ax=axes,shrink=.84,pad=.02); cb.set_label("Median first-step shortfall (%)")
    save(fig,"fig9_heterogeneity")

def fig10_robustness():
    d=pd.read_csv(ROB/"walkability_contribution_robustness.csv")
    fig,axes=plt.subplots(1,2,figsize=(10.8,4.6),layout="constrained")
    for obj,c in [("district_gain_m",COL["district"]),("gain_equal_street_mean_pp",COL["equal"])]:
        q=d[d.objective==obj].sort_values("new_sites")
        axes[0].plot(q.new_sites,q.spearman_original_vs_strict_loss,marker="o",ms=6,lw=2.0,color=c,label=OLAB[obj])
        axes[1].plot(q.new_sites,q.median_abs_loss_difference_pp,marker="o",ms=6,lw=2.0,color=c,label=OLAB[obj])
    axes[0].axhline(0,color="#888",lw=.8); axes[0].set_ylim(-.65,1.03)
    axes[0].set_ylabel("Rank correlation of supply-rule losses")
    axes[1].set_ylabel("Median absolute loss difference (pp)")
    for ax,lbl in zip(axes,["A","B"]):
        ax.set_xticks([1,12,40]); ax.set_xlabel("Added facilities"); ax.grid(True); panel(ax,lbl)
    axes[0].legend(frameon=False)
    save(fig,"fig10_network_robustness")

def main():
    fig1_study_area()
    fig2_framework()
    fig3_primary_first_step()
    fig4_spatial_mismatch()
    fig5_boundary_conditions()
    fig6_absolute_coverage()
    fig7_primary_budget()
    fig8_population_weighted()
    fig9_heterogeneity()
    fig10_robustness()
    qa={"figure_count":10,"source":"validated repository outputs","appendix_required":False}
    (OUT/"figure_qa.json").write_text(json.dumps(qa,indent=2),encoding="utf-8")
    print(json.dumps(qa,indent=2))

if __name__=="__main__":
    main()
