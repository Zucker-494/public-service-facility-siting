#!/usr/bin/env python3
from pathlib import Path
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "outputs/walkability_robustness/walkability_contribution_robustness_1_40.csv"
OUT = ROOT / "manuscript/cities/figures"
OUT.mkdir(parents=True, exist_ok=True)

COL = {
    "district_gain_m": "#2F6B8A",
    "gain_equal_street_mean_pp": "#B55D4C",
}
LAB = {
    "district_gain_m": "District-wide coverage",
    "gain_equal_street_mean_pp": "Equal-subdistrict coverage",
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

def main():
    d = pd.read_csv(SRC)
    assert len(d) == 80
    assert set(d.new_sites.unique()) == set(range(1,41))

    fig, axes = plt.subplots(2,1,figsize=(10.8,7.8),sharex=True,layout="constrained")

    ax = axes[0]
    for obj in ["district_gain_m","gain_equal_street_mean_pp"]:
        q = d[d.objective == obj].sort_values("new_sites")
        ax.plot(
            q.new_sites,
            q.spearman_original_vs_strict_loss,
            color=COL[obj],
            lw=2.0,
            marker="o",
            ms=3.8,
            label=LAB[obj],
        )
    ax.axhline(0, color="#777777", lw=1.0, ls="--")
    ax.text(40.4, 0.02, "ρ = 0", va="bottom", ha="left", fontsize=8.7, color="#666666")
    ax.set_ylim(-0.62,1.04)
    ax.set_ylabel("Rank correlation of supply-rule losses")
    ax.grid(True)
    ax.legend(frameon=False, ncol=2, loc="lower right")
    ax.text(-0.065,1.03,"A",transform=ax.transAxes,fontsize=12.5,fontweight="bold",va="bottom")

    ax = axes[1]
    for obj in ["district_gain_m","gain_equal_street_mean_pp"]:
        q = d[d.objective == obj].sort_values("new_sites")
        ax.fill_between(
            q.new_sites,
            q.q25_abs_loss_difference_pp,
            q.q75_abs_loss_difference_pp,
            color=COL[obj],
            alpha=0.13,
            lw=0,
        )
        ax.plot(
            q.new_sites,
            q.median_abs_loss_difference_pp,
            color=COL[obj],
            lw=2.0,
            marker="o",
            ms=3.8,
            label=LAB[obj],
        )
    ax.axhline(0, color="#777777", lw=1.0, ls="--")
    ax.text(40.4, 0.2, "0 pp", va="bottom", ha="left", fontsize=8.7, color="#666666")
    ax.set_ylim(bottom=0)
    ax.set_ylabel("Absolute loss difference (percentage points)")
    ax.set_xlabel("Added facilities")
    ax.grid(True)
    ax.text(-0.065,1.03,"B",transform=ax.transAxes,fontsize=12.5,fontweight="bold",va="bottom")

    axes[1].set_xticks([1,5,10,15,20,25,30,35,40])

    for ext in ["png","pdf"]:
        kwargs={"bbox_inches":"tight","facecolor":"white"}
        if ext=="png":
            kwargs["dpi"]=320
        fig.savefig(OUT/f"fig10_network_robustness_1_40.{ext}", **kwargs)
    plt.close(fig)

if __name__ == "__main__":
    main()
