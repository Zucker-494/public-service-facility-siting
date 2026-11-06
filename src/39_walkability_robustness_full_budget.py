#!/usr/bin/env python3
"""Recompute road-network robustness for every investment budget k=1..40.

The primary robustness figure uses the 15-minute threshold, matching the previous
checkpoint analysis. For each budget and planning objective, it compares the nine
service-rule pairs (3 services x 3 supply rules) between the baseline and the
strictly filtered pedestrian network.

Panel-A metric:
  Spearman rank correlation of median supply-rule losses across the nine pairs.

Panel-B metric:
  Median absolute difference in loss magnitude (percentage points) across the same
  nine pairs.

No interpolation is used: every k is computed from a completed sequential run.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "outputs/sequential_investment/sequential_addition_trajectories.csv"
STRICT = ROOT / "outputs/walkability_strict_scenario/sequential_addition_trajectories.csv"
OUT = ROOT / "outputs/walkability_robustness"
OUT.mkdir(parents=True, exist_ok=True)

SUPPLY_RULES = [
    "facilities_per_10k",
    "facilities_per_km2",
    "facilities_per_100km_network",
]
OBJECTIVES = ["district_gain_m", "gain_equal_street_mean_pp"]
SERVICES = ["healthcare", "elderly_care", "culture"]
THRESHOLD = 15


def safe_spearman(a, b):
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    keep = np.isfinite(a) & np.isfinite(b)
    a = a[keep]
    b = b[keep]
    if len(a) < 3 or np.allclose(a, a[0]) or np.allclose(b, b[0]):
        return np.nan
    return float(spearmanr(a, b).statistic)


def prepare(path: Path, network: str) -> pd.DataFrame:
    df = pd.read_csv(path, encoding="utf-8-sig")
    required = {
        "scenario","service","objective","rule","threshold_min","new_sites",
        "gain_relative_to_greedy"
    }
    missing = required - set(df.columns)
    assert not missing, (path, missing)
    assert int(df.new_sites.min()) == 1
    assert int(df.new_sites.max()) == 40
    assert set(df.new_sites.unique()) == set(range(1, 41))
    assert set(SUPPLY_RULES).issubset(set(df.rule))
    assert set(OBJECTIVES).issubset(set(df.objective))
    assert set(SERVICES).issubset(set(df.service))

    df = df[
        (df.threshold_min == THRESHOLD)
        & (df.rule.isin(SUPPLY_RULES))
        & (df.objective.isin(OBJECTIVES))
        & (df.service.isin(SERVICES))
    ].copy()
    df["loss_pct"] = 100.0 * (1.0 - df["gain_relative_to_greedy"].astype(float))
    # Numerical noise can create values of order 1e-14 around zero.
    df.loc[df.loss_pct.abs() < 1e-10, "loss_pct"] = 0.0
    df["network"] = network

    expected = 5 * 3 * 2 * 3 * 40
    assert len(df) == expected, (network, len(df), expected)
    return df


def main():
    original = prepare(BASE, "original")
    strict = prepare(STRICT, "strict")
    combined = pd.concat([original, strict], ignore_index=True)

    summary = (
        combined.groupby(
            ["network","service","objective","new_sites","rule"],
            as_index=False
        )
        .agg(
            loss_pct_median=("loss_pct","median"),
            loss_pct_q25=("loss_pct", lambda s: s.quantile(0.25)),
            loss_pct_q75=("loss_pct", lambda s: s.quantile(0.75)),
        )
    )
    summary.to_csv(OUT / "walkability_policy_comparison_summary_1_40.csv", index=False)

    rows = []
    pair_rows = []
    for objective in OBJECTIVES:
        for k in range(1, 41):
            d = summary[
                (summary.objective == objective)
                & (summary.new_sites == k)
                & (summary.rule.isin(SUPPLY_RULES))
            ]
            piv = d.pivot_table(
                index=["service","rule"],
                columns="network",
                values="loss_pct_median",
                aggfunc="first",
            ).dropna()
            assert len(piv) == 9, (objective, k, len(piv))

            absdiff = (piv["original"] - piv["strict"]).abs()
            rho = safe_spearman(piv["original"], piv["strict"])
            rows.append({
                "objective": objective,
                "new_sites": k,
                "n_service_rule_pairs": 9,
                "spearman_original_vs_strict_loss": rho,
                "median_abs_loss_difference_pp": float(absdiff.median()),
                "q25_abs_loss_difference_pp": float(absdiff.quantile(0.25)),
                "q75_abs_loss_difference_pp": float(absdiff.quantile(0.75)),
                "max_abs_loss_difference_pp": float(absdiff.max()),
                "same_lower_than_10pct_class": float(
                    ((piv["original"] < 10) == (piv["strict"] < 10)).mean()
                ),
            })
            for (service, rule), r in piv.iterrows():
                pair_rows.append({
                    "objective": objective,
                    "new_sites": k,
                    "service": service,
                    "rule": rule,
                    "original_loss_pct_median": float(r["original"]),
                    "strict_loss_pct_median": float(r["strict"]),
                    "absolute_difference_pp": float(abs(r["original"] - r["strict"])),
                })

    comp = pd.DataFrame(rows)
    assert len(comp) == 80
    assert comp.groupby("objective").new_sites.nunique().eq(40).all()
    comp.to_csv(OUT / "walkability_contribution_robustness_1_40.csv", index=False)
    pd.DataFrame(pair_rows).to_csv(
        OUT / "walkability_pairwise_losses_15min_1_40.csv", index=False
    )

    qa = {
        "primary_threshold_min": THRESHOLD,
        "budgets": list(range(1, 41)),
        "budget_count": 40,
        "objectives": OBJECTIVES,
        "service_rule_pairs_per_budget": 9,
        "baseline_rows_used": int(len(original)),
        "strict_rows_used": int(len(strict)),
        "comparison_rows": int(len(comp)),
        "finite_rank_correlations": int(comp.spearman_original_vs_strict_loss.notna().sum()),
        "missing_rank_correlations": int(comp.spearman_original_vs_strict_loss.isna().sum()),
        "interpolation_used": False,
        "panel_a_definition": "Spearman correlation of median supply-rule losses across 3 services x 3 supply rules, baseline vs strict network",
        "panel_b_definition": "Median absolute difference in those loss magnitudes, percentage points",
    }
    (OUT / "walkability_contribution_robustness_1_40_qa.json").write_text(
        json.dumps(qa, indent=2), encoding="utf-8"
    )
    print(json.dumps(qa, indent=2))


if __name__ == "__main__":
    main()
