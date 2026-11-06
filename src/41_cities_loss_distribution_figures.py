#!/usr/bin/env python3
from pathlib import Path
import math
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
SEQ = ROOT / "outputs/sequential_investment"
POP = ROOT / "outputs/population_weighted_sensitivity"
OUT = ROOT / "manuscript/cities/figures"
OUT.mkdir(parents=True, exist_ok=True)

COL = {
    "per_10k":"#D98C3F",
    "per_km2":"#2A9D8F",
    "per_100km":"#7B61A8",
}
PLAB = {
    "per_10k":"Per 10,000 residents",
    "per_km2":"Per km²",
    "per_100km":"Per 100 km roads",
    "facilities_per_10k":"Per 10,000 residents",
    "facilities_per_km2":"Per km²",
    "facilities_per_100km_network":"Per 100 km roads",
}
RULE_TO_PROXY = {
    "facilities_per_10k":"per_10k",
    "facilities_per_km2":"per_km2",
    "facilities_per_100km_network":"per_100km",
}
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

def ecdf(values):
    x = np.sort(np.asarray(values, dtype=float))
    y = np.arange(1, len(x)+1, dtype=float) / len(x)
    # prepend the minimum with y=0 so the empirical CDF begins visibly at zero
    return np.r_[x[0], x], np.r_[0.0, y]

def rounded_upper(values, step=10):
    vmax = float(np.nanmax(values))
    return max(step, int(math.ceil(vmax / step) * step))

def save(fig, stem):
    fig.savefig(OUT/f"{stem}.pdf", bbox_inches="tight", facecolor="white")
    fig.savefig(OUT/f"{stem}.png", dpi=320, bbox_inches="tight", facecolor="white")
    plt.close(fig)

def fig3_primary_ecdf():
    d = pd.read_csv(SEQ/"indicator_failure_conditions.csv")
    assert len(d) == 270
    fig, axes = plt.subplots(1, 2, figsize=(11.2, 4.9), sharey=True, layout="constrained")
    for ax, obj, title, label in zip(
        axes,
        ["district","equal"],
        ["District-wide coverage","Equal-subdistrict coverage"],
        ["A","B"],
    ):
        qobj = d[d.objective == obj]
        xmax = rounded_upper(qobj.first_step_shortfall_pct, step=10)
        for proxy in ["per_10k","per_km2","per_100km"]:
            q = qobj[qobj.proxy == proxy].first_step_shortfall_pct.to_numpy(dtype=float)
            assert len(q) == 45
            x, y = ecdf(q)
            med = float(np.median(q))
            ax.step(x, 100*y, where="post", color=COL[proxy], lw=2.2,
                    label=f"{PLAB[proxy]} (median {med:.1f}%)")
        ax.set_xlim(0, xmax)
        ax.set_ylim(0, 100)
        ax.set_xlabel("First-step shortfall from best available gain (%)")
        ax.grid(True)
        ax.set_title(title)
        ax.text(-0.10,1.04,label,transform=ax.transAxes,fontsize=12.5,fontweight="bold",va="bottom")
        ax.legend(frameon=False, loc="lower right")
    axes[0].set_ylabel("Share of scenario combinations with shortfall ≤ x (%)")
    save(fig, "fig3_primary_first_step_ecdf")

def fig8_population_weighted_ecdf():
    traj = pd.read_csv(POP/"population_weighted_trajectories.csv")
    budget = pd.read_csv(POP/"population_weighted_budget_summary.csv")
    first = traj[(traj.rule != "population_weighted_greedy") & (traj.new_sites == 1)].copy()
    assert len(first) == 135
    fig, axes = plt.subplots(1, 2, figsize=(11.2, 4.9), layout="constrained")

    ax = axes[0]
    xmax = rounded_upper(first.relative_shortfall_pct, step=10)
    for rule in ["facilities_per_10k","facilities_per_km2","facilities_per_100km_network"]:
        q = first[first.rule == rule].relative_shortfall_pct.to_numpy(dtype=float)
        assert len(q) == 45
        proxy = RULE_TO_PROXY[rule]
        x, y = ecdf(q)
        med = float(np.median(q))
        ax.step(x, 100*y, where="post", color=COL[proxy], lw=2.2,
                label=f"{PLAB[rule]} (median {med:.1f}%)")
    ax.set_xlim(0, xmax)
    ax.set_ylim(0,100)
    ax.set_xlabel("Population-weighted first-step shortfall (%)")
    ax.set_ylabel("Share of scenario combinations with shortfall ≤ x (%)")
    ax.grid(True)
    ax.legend(frameon=False, loc="lower right")
    ax.text(-0.10,1.04,"A",transform=ax.transAxes,fontsize=12.5,fontweight="bold",va="bottom")

    ax = axes[1]
    for rule in ["facilities_per_10k","facilities_per_km2","facilities_per_100km_network"]:
        z = budget[budget.rule == rule].sort_values("new_sites")
        proxy = RULE_TO_PROXY[rule]
        ax.fill_between(z.new_sites, z.q25_shortfall_pct, z.q75_shortfall_pct,
                        color=COL[proxy], alpha=.13, lw=0)
        ax.plot(z.new_sites, z.median_shortfall_pct, color=COL[proxy], lw=2.1,
                marker="o", ms=4.0, label=PLAB[rule])
    ax.set_xlabel("Added facilities")
    ax.set_ylabel("Population-weighted shortfall from greedy reference (%)")
    ax.grid(True)
    ax.legend(frameon=False, loc="upper right")
    ax.text(-0.10,1.04,"B",transform=ax.transAxes,fontsize=12.5,fontweight="bold",va="bottom")
    save(fig, "fig8_population_weighted_ecdf")

def main():
    fig3_primary_ecdf()
    fig8_population_weighted_ecdf()
    print("Generated ECDF figures without categorical loss thresholds.")

if __name__ == "__main__":
    main()
