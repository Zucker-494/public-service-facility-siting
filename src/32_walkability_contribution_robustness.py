#!/usr/bin/env python3
"""Summarise whether the paper's allocation findings survive road-network filtering."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
ROBUST = ROOT / "outputs/walkability_robustness"
SEQ = ROOT / "outputs/sequential_investment"
OUT = ROBUST

SUPPLY_RULES = [
    "facilities_per_10k",
    "facilities_per_km2",
    "facilities_per_100km_network",
]


def safe_spearman(a, b) -> float:
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    keep = np.isfinite(a) & np.isfinite(b)
    a = a[keep]
    b = b[keep]
    if len(a) < 3 or np.allclose(a, a[0]) or np.allclose(b, b[0]):
        return float("nan")
    return float(spearmanr(a, b).statistic)


def main() -> None:
    summary = pd.read_csv(ROBUST / "walkability_policy_comparison_summary.csv")
    agreement = pd.read_csv(ROBUST / "best_proxy_agreement.csv")
    first = pd.read_csv(ROBUST / "first_step_match.csv")
    phase = pd.read_csv(SEQ / "budget_phase_summary.csv")

    assert {"original", "strict"}.issubset(set(summary.network))
    assert set(SUPPLY_RULES).issubset(set(summary.rule))
    assert len(phase) == 18

    rows = []
    for (objective, budget), d in summary[
        summary.new_sites.isin([1, 12, 40]) & summary.rule.isin(SUPPLY_RULES)
    ].groupby(["objective", "new_sites"]):
        piv = d.pivot_table(
            index=["service", "rule"], columns="network", values="loss_pct_median", aggfunc="first"
        ).dropna()
        assert len(piv) == 9
        rows.append(
            {
                "objective": objective,
                "new_sites": int(budget),
                "n_service_rule_pairs": int(len(piv)),
                "spearman_original_vs_strict_loss": safe_spearman(piv["original"], piv["strict"]),
                "median_abs_loss_difference_pp": float((piv["original"] - piv["strict"]).abs().median()),
                "max_abs_loss_difference_pp": float((piv["original"] - piv["strict"]).abs().max()),
                "same_lower_than_10pct_class": float(
                    ((piv["original"] < 10) == (piv["strict"] < 10)).mean()
                ),
            }
        )
    comp = pd.DataFrame(rows)
    assert len(comp) == 6
    comp.to_csv(OUT / "walkability_contribution_robustness.csv", index=False)

    agg = {
        "best_proxy_agreement_all_budgets": float(agreement.same_best_proxy.mean()),
        "best_proxy_agreement_15min": float(agreement.loc[agreement.threshold_min == 15, "same_best_proxy"].mean()),
        "first_step_exact_match_original": float(first.loc[first.network == "original", "match"].mean()),
        "first_step_exact_match_strict": float(first.loc[first.network == "strict", "match"].mean()),
        "median_network_loss_rank_correlation": float(comp.spearman_original_vs_strict_loss.median()),
        "minimum_network_loss_rank_correlation": float(comp.spearman_original_vs_strict_loss.min()),
        "median_abs_loss_difference_pp": float(comp.median_abs_loss_difference_pp.median()),
        "all_main_budget_groups_show_declining_median_relative_difference": bool(
            (phase.share_groups_with_declining_relative_difference >= (2 / 3)).all()
        ),
        "interpretation": "Road-network filtering changes some proxy rankings, but this table quantifies whether the magnitude/order of allocation shortfalls remains structurally similar.",
    }
    (OUT / "walkability_contribution_robustness_qa.json").write_text(
        json.dumps(agg, indent=2), encoding="utf-8"
    )
    print(json.dumps(agg, indent=2))


if __name__ == "__main__":
    main()
