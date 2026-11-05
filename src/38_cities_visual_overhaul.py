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
from matplotlib.colors import Normalize
from matplotlib.cm import ScalarMappable

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "figures" / "cities_v6"
OUT.mkdir(parents=True, exist_ok=True)

SEQ = ROOT / "outputs" / "sequential_investment"
ROB = ROOT / "outputs" / "walkability_robustness"
POP = ROOT / "outputs" / "population_weighted_sensitivity"
FAIL = ROOT / "outputs" / "failure_condition_multivariable"

COL = {
    "greedy": "#2F3640",
    "per_10k": "#3B7EA1",
    "per_km2": "#D08C2D",
    "per_100km": "#7A5EA7",
    "district": "#4477AA",
    "equal": "#CC6677",
    "healthcare": "#4477AA",
    "elderly_care": "#CC6677",
    "culture": "#228833",
}
PROXY = ["per_10k", "per_km2", "per_100km"]
RULE = ["facilities_per_10k", "facilities_per_km2", "facilities_per_100km_network"]
PLAB = {
    "per_10k": "Per 10,000 residents",
    "per_km2": "Per km²",
    "per_100km": "Per 100 km roads",
    "facilities_per_10k": "Per 10,000 residents",
    "facilities_per_km2": "Per km²",
    "facilities_per_100km_network": "Per 100 km roads",
}
SLAB = {"healthcare": "Healthcare", "elderly_care": "Elderly care", "culture": "Cultural facilities"}
OLAB = {
    "district": "District-wide coverage",
    "equal": "Equal-subdistrict coverage",
    "district_gain_m": "District-wide coverage",
    "gain_equal_street_mean_pp": "Equal-subdistrict coverage",
}

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 10.8,
    "axes.titlesize": 11.6,
    "axes.labelsize": 10.8,
    "xtick.labelsize": 9.8,
    "ytick.labelsize": 9.8,
    "legend.fontsize": 9.4,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.linewidth": 0.8,
    "grid.color": "#D6DADF",
    "grid.linewidth": 0.65,
    "grid.alpha": 0.65,
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
})

def save(fig, stem):
    fig.savefig(OUT / f"{stem}.pdf", bbox_inches="tight", facecolor="white")
    fig.savefig(OUT / f"{stem}.png", dpi=320, bbox_inches="tight", facecolor="white")
    plt.close(fig)

def panel(ax, s):
    ax.text(-0.08, 1.035, s, transform=ax.transAxes, fontsize=12.5, fontweight="bold", va="bottom")

def attach_zones_to_boundaries(bound, cand):
    if "zone" in bound.columns:
        out = bound.copy()
        out["zone"] = out["zone"].astype(int)
        return out
    pts = gpd.GeoDataFrame(
        cand[["zone"]].copy(),
        geometry=gpd.points_from_xy(cand.x, cand.y),
        crs=bound.crs,
    )
    bb = bound.reset_index(drop=True).reset_index().rename(columns={"index": "poly_idx"})
    joined = gpd.sjoin(pts, bb[["poly_idx", "geometry"]], predicate="within", how="left")
    mapped = joined.dropna(subset=["poly_idx"]).copy()
    mapping = mapped.groupby("poly_idx").zone.agg(lambda x: int(x.mode().iloc[0]))
    out = bb.set_index("poly_idx").copy()
    out["zone"] = out.index.map(mapping)
    expected = int(cand.zone.nunique())
    if out.zone.isna().any() or int(out.zone.nunique()) != expected:
        raise ValueError(f"Boundary-zone mapping failed: mapped={out.zone.nunique()}, expected={expected}")
    out["zone"] = out.zone.astype(int)
    return out.reset_index(drop=True)

def common_spatial_data():
    gpkg = ROOT / "data/processed/p06_refined_clean.gpkg"
    bound = gpd.read_file(gpkg, layer="study_subdistricts")
    edges = gpd.read_file(gpkg, layer="osm_node_identity_edges")
    edges = edges[edges["zone"] >= 0]
    cand = pd.read_csv(ROOT / "data/processed/hypothetical_candidate_nodes.csv", encoding="utf-8-sig")
    bound = attach_zones_to_boundaries(bound, cand)
    return bound, edges, cand

def fig01_study_area():
    bound, edges, cand = common_spatial_data()
    reg = pd.read_csv(ROOT / "data/curated/official_facility_registry_89_address_audited.csv", encoding="utf-8-sig")
    reg = reg[reg.wgs84_lon.notna() & reg.wgs84_lat.notna()].copy()
    fac = gpd.GeoDataFrame(
        reg,
        geometry=gpd.points_from_xy(reg.wgs84_lon, reg.wgs84_lat),
        crs="EPSG:4326",
    ).to_crs(edges.crs)
    cg = gpd.GeoDataFrame(cand, geometry=gpd.points_from_xy(cand.x, cand.y), crs=edges.crs)

    fig, (ax, info) = plt.subplots(
        1, 2, figsize=(11.0, 5.9),
        gridspec_kw={"width_ratios": [4.5, 1.45]},
        layout="constrained",
    )
    bound.plot(ax=ax, facecolor="#F6F3EC", edgecolor="#60656B", linewidth=0.95)
    edges.plot(ax=ax, color="#B7BEC5", linewidth=0.34, alpha=0.72)
    cg.plot(ax=ax, color="#74A6B8", markersize=2.0, alpha=0.34)

    marks = {"healthcare": "o", "elderly_care": "^", "culture": "s"}
    for svc in ["healthcare", "elderly_care", "culture"]:
        q = fac[fac.facility_type == svc]
        q.plot(
            ax=ax, marker=marks[svc], color=COL[svc], markersize=27,
            edgecolor="white", linewidth=0.55
        )

    name_map = cand[["zone", "subdistrict_en"]].drop_duplicates().set_index("zone").subdistrict_en.to_dict()
    for r in bound.itertuples():
        p = r.geometry.representative_point()
        name = name_map.get(r.zone, "").replace(" Subdistrict", "")
        ax.text(
            p.x, p.y, name, fontsize=7.1, ha="center", va="center", color="#2F3337",
            bbox=dict(facecolor="white", alpha=0.62, edgecolor="none", pad=0.6)
        )
    ax.set_title("Yangpu District, Shanghai", loc="left", fontweight="semibold", pad=7)
    ax.set_axis_off()

    info.set_axis_off()
    info.set_xlim(0, 1); info.set_ylim(0, 1)
    info.text(0.02, 0.96, "Study inputs", fontsize=12.0, fontweight="semibold", va="top")
    handles = [
        Line2D([0],[0], marker="o", linestyle="none", markerfacecolor="#74A6B8", alpha=.55,
               markeredgecolor="none", markersize=6, label="1,132 candidate sites"),
        Line2D([0],[0], marker="o", linestyle="none", markerfacecolor=COL["healthcare"],
               markeredgecolor="white", markersize=7, label="Healthcare (12 mapped)"),
        Line2D([0],[0], marker="^", linestyle="none", markerfacecolor=COL["elderly_care"],
               markeredgecolor="white", markersize=7, label="Elderly care (61 mapped)"),
        Line2D([0],[0], marker="s", linestyle="none", markerfacecolor=COL["culture"],
               markeredgecolor="white", markersize=7, label="Cultural facilities (10 mapped)"),
    ]
    info.legend(handles=handles, loc="upper left", bbox_to_anchor=(0, 0.88), frameon=False,
                handletextpad=0.7, borderaxespad=0)
    info.text(0.02, 0.51, "Inventory", fontsize=10.4, fontweight="semibold")
    info.text(0.02, 0.465, "89 existing facilities", fontsize=9.7)
    info.text(0.02, 0.37, "Network", fontsize=10.4, fontweight="semibold")
    info.text(0.02, 0.325, "798.6 km evaluated road network", fontsize=9.7)
    info.text(0.02, 0.23, "Location uncertainty", fontsize=10.4, fontweight="semibold")
    info.text(
        0.02, 0.185,
        "Six facilities without accepted\ninherited coordinates are represented\nthrough five address-based scenarios.",
        fontsize=9.2, va="top", linespacing=1.35
    )
    save(fig, "fig01_study_area")

def fig02_framework():
    fig, ax = plt.subplots(figsize=(11.0, 4.8), layout="constrained")
    ax.set_axis_off(); ax.set_xlim(0, 1); ax.set_ylim(0, 1)

    def box(x, y, w, h, title, body, fc):
        p = FancyBboxPatch(
            (x, y), w, h, boxstyle="round,pad=0.012,rounding_size=0.018",
            facecolor=fc, edgecolor="#5E6368", linewidth=0.95
        )
        ax.add_patch(p)
        ax.text(x+w/2, y+h*0.66, title, ha="center", va="center",
                fontsize=10.5, fontweight="semibold")
        ax.text(x+w/2, y+h*0.36, body, ha="center", va="center", fontsize=9.2)

    def arrow(x1, y1, x2, y2):
        ax.add_patch(FancyArrowPatch(
            (x1,y1),(x2,y2), arrowstyle="-|>", mutation_scale=13,
            linewidth=1.0, color="#6A6E73"
        ))

    box(0.04, 0.66, 0.27, 0.19, "Existing provision", "89 facilities + pedestrian network", "#EEF2F4")
    box(0.365,0.66, 0.27, 0.19, "Supply-based rule", "Lowest-supply subdistrict", "#F7E8D5")
    box(0.69, 0.66, 0.27, 0.19, "Network-greedy reference", "Best available candidate", "#E1ECE9")
    box(0.20, 0.34, 0.27, 0.19, "Sequential update", "Recalculate after each addition", "#ECE6F2")
    box(0.53, 0.34, 0.27, 0.19, "Planning objectives", "District-wide | equal-subdistrict", "#EEF1F5")
    box(0.365,0.06, 0.27, 0.17, "Decision validity", "Shortfall | scale | robustness", "#F3EFE7")
    arrow(0.31,0.755,0.365,0.755)
    arrow(0.635,0.755,0.69,0.755)
    arrow(0.50,0.66,0.38,0.53)
    arrow(0.82,0.66,0.67,0.53)
    arrow(0.335,0.34,0.47,0.23)
    arrow(0.665,0.34,0.53,0.23)
    ax.text(0.50, 0.94, "Three supply indicators: per 10,000 residents | per km² | per 100 km roads",
            ha="center", va="center", fontsize=10.2, color="#43484D")
    ax.text(0.50, 0.89, "Three services | 5/10/15 min thresholds | 1-40 additions",
            ha="center", va="center", fontsize=9.6, color="#62676C")
    save(fig, "fig02_decision_framework")

def fig03_first_step():
    primary = pd.read_csv(SEQ / "indicator_failure_summary.csv")
    pop = pd.read_csv(POP / "population_weighted_first_step_summary.csv")
    rule_to_proxy = {
        "facilities_per_10k": "per_10k",
        "facilities_per_km2": "per_km2",
        "facilities_per_100km_network": "per_100km",
    }
    panels = []
    for obj, title in [("district", "District-wide coverage"), ("equal", "Equal-subdistrict coverage")]:
        q = primary[primary.objective == obj].copy()
        q = q.set_index("proxy").loc[PROXY].reset_index()
        panels.append((title, q["proxy"].tolist(),
                       q["median_first_step_shortfall_pct"].to_numpy(),
                       q["q25_first_step_shortfall_pct"].to_numpy(),
                       q["q75_first_step_shortfall_pct"].to_numpy(),
                       q["exact_global_best_rate_pct"].to_numpy()))
    pop["proxy"] = pop.rule.map(rule_to_proxy)
    pop = pop.set_index("proxy").loc[PROXY].reset_index()
    panels.append(("Population-weighted sensitivity", pop["proxy"].tolist(),
                   pop["median_shortfall_pct"].to_numpy(),
                   pop["q25_shortfall_pct"].to_numpy(),
                   pop["q75_shortfall_pct"].to_numpy(),
                   pop["exact_first_step_match_rate_pct"].to_numpy()))

    fig, axes = plt.subplots(1, 3, figsize=(12.0, 4.6), sharex=True, layout="constrained")
    xmax = 72
    for j, (ax, dat) in enumerate(zip(axes, panels)):
        title, proxies, med, q25, q75, match = dat
        y = np.arange(3)
        for i, p in enumerate(proxies):
            c = COL[p]
            ax.hlines(y[i], q25[i], q75[i], lw=8, color=c, alpha=0.22)
            ax.plot(med[i], y[i], "o", ms=8.5, color=c, mec="white", mew=0.8, zorder=3)
            ax.text(xmax-1.2, y[i], f"{match[i]:.1f}% match", ha="right", va="center",
                    fontsize=9.0, color="#4D5358")
        ax.set_title(title, pad=8, fontweight="semibold")
        ax.set_xlim(0, xmax)
        ax.set_xlabel("First-step shortfall (%)")
        ax.grid(axis="x")
        ax.set_yticks(y)
        if j == 0:
            ax.set_yticklabels([PLAB[p] for p in proxies])
        else:
            ax.set_yticklabels([])
        ax.invert_yaxis()
        panel(ax, chr(ord("A")+j))
    save(fig, "fig03_first_step_validity")

def fig04_spatial_mismatch():
    bound, _, cand = common_spatial_data()
    zone_map = cand[["zone","subdistrict"]].drop_duplicates().set_index("subdistrict").zone.to_dict()
    d = pd.read_csv(SEQ / "street_opportunity_540.csv")
    q = d[(d.site_scenario=="INFERRED_89_01") & (d.service=="culture") & (d.threshold_min==10)].copy()
    q["zone"] = q.subdistrict.map(zone_map)
    vals = q.set_index("zone")
    names = cand[["zone","subdistrict_en"]].drop_duplicates().set_index("zone").subdistrict_en.to_dict()

    fig, axd = plt.subplot_mosaic(
        [["A","B"],["C","C"]],
        figsize=(11.2, 8.0),
        gridspec_kw={"height_ratios":[1.0,1.08]},
        layout="constrained"
    )
    specs = {
        "A": ("facilities_per_10k", "Supply scarcity: per 10,000 residents", "YlOrRd_r", "min", "Facilities per 10k"),
        "B": ("facilities_per_100km_network", "Supply scarcity: per 100 km roads", "YlOrRd_r", "min", "Facilities per 100 km"),
        "C": ("max_equal", "Network opportunity: equal-subdistrict objective", "viridis", "max", "Maximum marginal gain"),
    }
    for key, ax in axd.items():
        field, title, cmap, mode, cblab = specs[key]
        m = bound.merge(vals[[field]], left_on="zone", right_index=True, how="left")
        norm = Normalize(vmin=float(m[field].min()), vmax=float(m[field].max()))
        m.plot(column=field, ax=ax, cmap=cmap, norm=norm, edgecolor="white", linewidth=1.15)
        best = q.loc[q[field].idxmin() if mode=="min" else q[field].idxmax(), "zone"]
        bound[bound.zone==best].boundary.plot(ax=ax, color="#111111", linewidth=2.7)
        for r in m.itertuples():
            p = r.geometry.representative_point()
            ax.text(
                p.x, p.y, names[r.zone].replace(" Subdistrict",""),
                fontsize=7.8, ha="center", va="center", color="#222222",
                bbox=dict(facecolor="white", alpha=0.66, edgecolor="none", pad=0.55)
            )
        ax.set_title(f"{key}  {title}", loc="left", fontweight="semibold", pad=6)
        ax.set_axis_off()
        sm = ScalarMappable(norm=norm, cmap=cmap); sm.set_array([])
        cb = fig.colorbar(sm, ax=ax, orientation="horizontal", fraction=0.046, pad=0.025, shrink=0.78)
        cb.set_label(cblab, fontsize=9.2)
        cb.ax.tick_params(labelsize=8.5)
    save(fig, "fig04_spatial_mismatch")

def fig05_boundary_conditions():
    d = pd.read_csv(FAIL / "selected_boundary_condition_coefficients.csv")
    order = [
        ("supply_opportunity_rho", "Supply-opportunity alignment"),
        ("opportunity_top_share", "Top-opportunity concentration"),
        ("supply_cv", "Supply variation"),
        ("priority_population_share", "Priority-area population share"),
        ("threshold_min", "Walking threshold"),
    ]
    fig, ax = plt.subplots(figsize=(10.8, 5.2), layout="constrained")
    y = np.arange(len(order))
    offsets = {"district_only": -0.13, "equal_subdistrict_only": 0.13}
    labs = {"district_only": "District-wide", "equal_subdistrict_only": "Equal-subdistrict"}
    colors = {"district_only": COL["district"], "equal_subdistrict_only": COL["equal"]}
    markers = {"district_only": "o", "equal_subdistrict_only": "s"}

    for model in ["district_only","equal_subdistrict_only"]:
        q = d[d.model==model].set_index("term")
        for i, (term, _) in enumerate(order):
            r = q.loc[term]
            yy = y[i] + offsets[model]
            lo = r.leave_one_scenario_out_min
            hi = r.leave_one_scenario_out_max
            val = r.full_sample_coefficient
            ax.hlines(yy, lo, hi, color=colors[model], lw=2.2, alpha=0.75)
            ax.plot(val, yy, marker=markers[model], color=colors[model], ms=7.5,
                    mec="white", mew=0.7)
    ax.axvline(0, color="#8A8F94", lw=0.9)
    ax.set_yticks(y, [x[1] for x in order])
    ax.invert_yaxis()
    ax.set_xlabel("Standardised descriptive coefficient (percentage points)")
    ax.grid(axis="x")
    handles = [
        Line2D([0],[0], marker=markers[m], color=colors[m], lw=2, label=labs[m],
               markerfacecolor=colors[m], markeredgecolor="white")
        for m in ["district_only","equal_subdistrict_only"]
    ]
    ax.legend(handles=handles, frameon=False, ncol=2, loc="lower right")
    save(fig, "fig05_boundary_conditions")

def fig06_cumulative_coverage():
    d = pd.read_csv(ROOT / "outputs/figures/sequential_v11/figure_data_all_services_all_thresholds.csv")
    d = d[(d.threshold_min==15) & (d.objective=="district_gain_m")]
    rules = ["network_greedy"] + RULE
    color = {
        "network_greedy": COL["greedy"],
        "facilities_per_10k": COL["per_10k"],
        "facilities_per_km2": COL["per_km2"],
        "facilities_per_100km_network": COL["per_100km"],
    }
    label = {"network_greedy":"Network-greedy reference", **{k:PLAB[k] for k in RULE}}
    ls = {"network_greedy":"-", "facilities_per_10k":"-", "facilities_per_km2":"--", "facilities_per_100km_network":"-."}

    fig, axes = plt.subplots(1,3,figsize=(12.0,4.4),layout="constrained")
    for j, (ax, svc) in enumerate(zip(axes, ["healthcare","elderly_care","culture"])):
        for rule in rules:
            q = d[(d.service==svc) & (d.rule==rule)].sort_values("new_sites")
            x = np.r_[0, q.new_sites.to_numpy()]
            y = np.r_[0, q.gain_median.to_numpy()/1000.0]
            ax.plot(x, y, color=color[rule], ls=ls[rule],
                    lw=2.5 if rule=="network_greedy" else 2.0,
                    label=label[rule])
        ax.set_title(SLAB[svc], fontweight="semibold")
        ax.set_xlabel("Added facilities")
        ax.grid(axis="y")
        panel(ax, chr(ord("A")+j))
        if j == 0:
            ax.set_ylabel("Additional covered road network (km)")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, frameon=False, ncol=2, loc="upper center", bbox_to_anchor=(0.5,1.08))
    save(fig, "fig06_cumulative_coverage")

def fig07_investment_scale():
    d = pd.read_csv(SEQ / "budget_trajectory_summary.csv")
    fig, axes = plt.subplots(1,2,figsize=(11.3,4.8),layout="constrained")
    for j, (ax, obj) in enumerate(zip(axes, ["district_gain_m","gain_equal_street_mean_pp"])):
        q = d[d.objective==obj]
        for rule in RULE:
            z = q[q.rule==rule].sort_values("new_sites")
            p = {"facilities_per_10k":"per_10k","facilities_per_km2":"per_km2","facilities_per_100km_network":"per_100km"}[rule]
            c = COL[p]
            ax.fill_between(z.new_sites, z.q25_relative_difference_pct, z.q75_relative_difference_pct,
                            color=c, alpha=0.12, lw=0)
            ax.plot(z.new_sites, z.median_relative_difference_pct, color=c, lw=2.2, label=PLAB[rule])
        ax.set_title(OLAB[obj], fontweight="semibold")
        ax.set_xlabel("Added facilities")
        ax.set_ylabel("Relative shortfall from greedy reference (%)")
        ax.grid(True)
        panel(ax, chr(ord("A")+j))
    axes[0].legend(frameon=False, loc="upper right")
    save(fig, "fig07_investment_scale")

def fig08_population_weighted():
    d = pd.read_csv(POP / "population_weighted_trajectories.csv")
    q = d[d.rule!="population_weighted_greedy"].copy()
    s = q.groupby(["rule","new_sites"]).relative_shortfall_pct.agg(
        median="median",
        q25=lambda x: x.quantile(0.25),
        q75=lambda x: x.quantile(0.75),
    ).reset_index()
    fig, ax = plt.subplots(figsize=(10.7,4.8),layout="constrained")
    for rule in RULE:
        z = s[s.rule==rule].sort_values("new_sites")
        p = {"facilities_per_10k":"per_10k","facilities_per_km2":"per_km2","facilities_per_100km_network":"per_100km"}[rule]
        c = COL[p]
        ax.fill_between(z.new_sites, z.q25, z.q75, color=c, alpha=0.12, lw=0)
        ax.plot(z.new_sites, z["median"], color=c, lw=2.3, label=PLAB[rule])
    ax.set_xlabel("Added facilities")
    ax.set_ylabel("Population-weighted shortfall from greedy reference (%)")
    ax.grid(True)
    ax.legend(frameon=False, ncol=3, loc="upper right")
    save(fig, "fig08_population_weighted")

def fig09_heterogeneity():
    d = pd.read_csv(SEQ / "indicator_failure_conditions.csv")
    agg = d.groupby(["objective","service","threshold_min","proxy"],as_index=False).first_step_shortfall_pct.median()
    rows = [(s,t) for s in ["healthcare","elderly_care","culture"] for t in [5,10,15]]
    vmax = float(agg.first_step_shortfall_pct.max())

    fig, axes = plt.subplots(1,2,figsize=(11.4,5.9),layout="constrained")
    for j, (ax,obj) in enumerate(zip(axes,["district","equal"])):
        arr = []
        for s,t in rows:
            arr.append([
                float(agg[(agg.objective==obj)&(agg.service==s)&(agg.threshold_min==t)&(agg.proxy==p)]
                      .first_step_shortfall_pct.iloc[0])
                for p in PROXY
            ])
        arr = np.array(arr)
        im = ax.imshow(arr, cmap="YlOrRd", vmin=0, vmax=vmax, aspect="auto")
        ax.set_xticks(range(3), [PLAB[p] for p in PROXY], rotation=12, ha="right")
        ax.set_yticks(range(len(rows)), [f"{SLAB[s]} | {t} min" for s,t in rows])
        for r in range(arr.shape[0]):
            for c in range(arr.shape[1]):
                val = arr[r,c]
                txtc = "white" if val > vmax*0.62 else "#1F2328"
                ax.text(c,r,f"{val:.1f}",ha="center",va="center",fontsize=9.0,color=txtc)
        ax.set_title(OLAB[obj], fontweight="semibold")
        panel(ax, chr(ord("A")+j))
    cb = fig.colorbar(im, ax=axes, shrink=0.80, pad=0.025)
    cb.set_label("Median first-step shortfall (%)")
    save(fig, "fig09_service_threshold_heterogeneity")

def fig10_network_robustness():
    d = pd.read_csv(ROB / "walkability_contribution_robustness.csv")
    fig, axes = plt.subplots(1,2,figsize=(10.8,4.6),layout="constrained")
    for obj, c in [("district_gain_m",COL["district"]),("gain_equal_street_mean_pp",COL["equal"])]:
        q = d[d.objective==obj].sort_values("new_sites")
        axes[0].plot(q.new_sites, q.spearman_original_vs_strict_loss, marker="o", ms=6.5,
                     lw=2.2, color=c, label=OLAB[obj])
        axes[1].plot(q.new_sites, q.median_abs_loss_difference_pp, marker="o", ms=6.5,
                     lw=2.2, color=c, label=OLAB[obj])
        for x,y in zip(q.new_sites,q.spearman_original_vs_strict_loss):
            axes[0].text(x,y+(0.055 if y>=0 else -0.09),f"{y:.2f}",ha="center",fontsize=8.8)
        for x,y in zip(q.new_sites,q.median_abs_loss_difference_pp):
            axes[1].text(x,y+1.0,f"{y:.1f}",ha="center",fontsize=8.8)
    axes[0].axhline(0,color="#90959A",lw=0.8)
    axes[0].set_ylim(-0.68,1.05)
    axes[0].set_ylabel("Rank correlation of supply-rule losses")
    axes[1].set_ylabel("Median absolute loss difference (pp)")
    for j,ax in enumerate(axes):
        ax.set_xticks([1,12,40])
        ax.set_xlabel("Added facilities")
        ax.grid(True)
        panel(ax, chr(ord("A")+j))
    axes[0].legend(frameon=False, loc="lower right")
    save(fig, "fig10_network_robustness")

def main():
    fig01_study_area()
    fig02_framework()
    fig03_first_step()
    fig04_spatial_mismatch()
    fig05_boundary_conditions()
    fig06_cumulative_coverage()
    fig07_investment_scale()
    fig08_population_weighted()
    fig09_heterogeneity()
    fig10_network_robustness()
    qa = {
        "figure_count": 10,
        "all_vector_pdf": True,
        "png_previews": True,
        "results_mapping": {
            "first_step": "fig03",
            "spatial_mismatch": "fig04",
            "failure_conditions": "fig05",
            "absolute_coverage": "fig06",
            "investment_scale": "fig07",
            "population_weighted": "fig08",
            "service_threshold_heterogeneity": "fig09",
            "road_network_robustness": "fig10",
        },
    }
    (OUT / "figure_qa.json").write_text(json.dumps(qa, indent=2), encoding="utf-8")
    print(json.dumps(qa, indent=2))

if __name__ == "__main__":
    main()
