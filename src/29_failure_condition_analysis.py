#!/usr/bin/env python3
"""Diagnose when supply-priority rules diverge from network-coverage opportunity.

This analysis reuses frozen outputs from the sequential siting experiment. It does not
rerun the expensive network simulation. Scenario-level correlations are descriptive:
the five location scenarios are deterministic sensitivity settings, not independent
samples, so no inferential p-values are reported.
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "sequential_investment"
FIG = ROOT / "outputs" / "figures" / "all_figures_png"

PROXY_FIELDS = {
    "per_10k": "facilities_per_10k",
    "per_km2": "facilities_per_km2",
    "per_100km": "facilities_per_100km_network",
}
OBJECTIVE_OPPORTUNITY = {"district": "max_district", "equal": "max_equal"}
TRAJECTORY_OBJECTIVES = ("district_gain_m", "gain_equal_street_mean_pp")
SUPPLY_RULES = tuple(PROXY_FIELDS.values())


def safe_spearman(x: pd.Series | np.ndarray, y: pd.Series | np.ndarray) -> float:
    a = np.asarray(x, dtype=float)
    b = np.asarray(y, dtype=float)
    keep = np.isfinite(a) & np.isfinite(b)
    a = a[keep]
    b = b[keep]
    if len(a) < 3 or np.allclose(a, a[0]) or np.allclose(b, b[0]):
        return float("nan")
    return float(spearmanr(a, b).statistic)


def coefficient_of_variation(x: pd.Series | np.ndarray) -> float:
    a = np.asarray(x, dtype=float)
    a = a[np.isfinite(a)]
    if len(a) == 0:
        return float("nan")
    mean = float(np.mean(a))
    if np.isclose(mean, 0.0):
        return float("nan")
    return float(np.std(a, ddof=0) / abs(mean))


def build_failure_conditions(street: pd.DataFrame, corr: pd.DataFrame, dec: pd.DataFrame) -> pd.DataFrame:
    required_street = {
        "site_scenario", "service", "threshold_min", "subdistrict", "max_district", "max_equal",
        "n_candidates", "population_census2020", "area_km2", "network_km", *PROXY_FIELDS.values(),
    }
    required_dec = {
        "scenario", "service", "threshold_min", "objective", "proxy", "fraction_of_global_best",
        "tied_priority_streets",
    }
    required_corr = {"scenario", "service", "threshold_min", "objective", "proxy", "spearman_rho"}
    assert required_street.issubset(street.columns)
    assert required_dec.issubset(dec.columns)
    assert required_corr.issubset(corr.columns)
    assert len(street) == 540 and len(dec) == 270 and len(corr) == 270

    corr_lookup = corr.set_index(["scenario", "service", "threshold_min", "objective", "proxy"])["spearman_rho"]
    rows: list[dict] = []
    for r in dec.itertuples(index=False):
        d = street[
            (street.site_scenario == r.scenario)
            & (street.service == r.service)
            & (street.threshold_min == r.threshold_min)
        ].copy()
        assert len(d) == 12
        field = PROXY_FIELDS[r.proxy]
        opportunity_col = OBJECTIVE_OPPORTUNITY[r.objective]
        supply_values = d[field].astype(float)
        priority = np.isclose(supply_values, supply_values.min(), rtol=1e-11, atol=1e-12)
        assert int(priority.sum()) == int(r.tied_priority_streets)
        opportunity = d[opportunity_col].astype(float)
        global_best = float(opportunity.max())
        assert global_best > 0

        key = (r.scenario, r.service, r.threshold_min, r.objective, r.proxy)
        rows.append(
            {
                "scenario": r.scenario,
                "service": r.service,
                "threshold_min": int(r.threshold_min),
                "objective": r.objective,
                "proxy": r.proxy,
                "fraction_of_global_best": float(r.fraction_of_global_best),
                "first_step_shortfall_pct": 100.0 * (1.0 - float(r.fraction_of_global_best)),
                "supply_opportunity_rho": float(corr_lookup.loc[key]),
                "opportunity_cv": coefficient_of_variation(opportunity),
                "opportunity_top_share": global_best / float(opportunity.sum()),
                "supply_cv": coefficient_of_variation(supply_values),
                "priority_population_share": float(d.loc[priority, "population_census2020"].sum() / d.population_census2020.sum()),
                "priority_area_share": float(d.loc[priority, "area_km2"].sum() / d.area_km2.sum()),
                "priority_network_share": float(d.loc[priority, "network_km"].sum() / d.network_km.sum()),
                "priority_candidate_share": float(d.loc[priority, "n_candidates"].sum() / d.n_candidates.sum()),
                "rho_population_opportunity": safe_spearman(d.population_census2020, opportunity),
                "rho_area_opportunity": safe_spearman(d.area_km2, opportunity),
                "rho_network_opportunity": safe_spearman(d.network_km, opportunity),
                "rho_candidates_opportunity": safe_spearman(d.n_candidates, opportunity),
                "priority_street_count": int(priority.sum()),
            }
        )
    result = pd.DataFrame(rows)
    assert len(result) == 270
    assert result.first_step_shortfall_pct.between(-1e-8, 100 + 1e-8).all()
    return result


def condition_correlations(condition: pd.DataFrame) -> pd.DataFrame:
    features = [
        "supply_opportunity_rho", "opportunity_cv", "opportunity_top_share", "supply_cv",
        "priority_population_share", "priority_area_share", "priority_network_share", "priority_candidate_share",
        "rho_population_opportunity", "rho_area_opportunity", "rho_network_opportunity", "rho_candidates_opportunity",
    ]
    records: list[dict] = []
    for aggregation in ("scenario_level", "scenario_median"):
        if aggregation == "scenario_level":
            base = condition.copy()
        else:
            numeric = ["first_step_shortfall_pct", *features]
            base = (
                condition.groupby(["service", "threshold_min", "objective", "proxy"], as_index=False)[numeric]
                .median()
            )
        for (objective, proxy), d in base.groupby(["objective", "proxy"]):
            for feature in features:
                records.append(
                    {
                        "aggregation": aggregation,
                        "objective": objective,
                        "proxy": proxy,
                        "feature": feature,
                        "n": int(len(d)),
                        "spearman_rho_with_shortfall": safe_spearman(d[feature], d.first_step_shortfall_pct),
                    }
                )
    out = pd.DataFrame(records)
    assert len(out) == 144
    return out


def condition_summary(condition: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (objective, proxy), d in condition.groupby(["objective", "proxy"]):
        rows.append(
            {
                "objective": objective,
                "proxy": proxy,
                "n_cases": int(len(d)),
                "exact_global_best_rate_pct": 100.0 * float(np.isclose(d.fraction_of_global_best, 1.0, rtol=1e-11, atol=1e-12).mean()),
                "median_first_step_shortfall_pct": float(d.first_step_shortfall_pct.median()),
                "q25_first_step_shortfall_pct": float(d.first_step_shortfall_pct.quantile(0.25)),
                "q75_first_step_shortfall_pct": float(d.first_step_shortfall_pct.quantile(0.75)),
                "median_supply_opportunity_rho": float(d.supply_opportunity_rho.median()),
                "median_opportunity_cv": float(d.opportunity_cv.median()),
            }
        )
    out = pd.DataFrame(rows)
    assert len(out) == 6
    return out


def budget_trends(traj: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    required = {
        "scenario", "service", "threshold_min", "objective", "rule", "new_sites",
        "gain_relative_to_greedy", "signed_shortfall_vs_greedy",
    }
    assert required.issubset(traj.columns)
    assert len(traj) == 14400
    supply = traj[traj.rule != "network_greedy"].copy()
    assert len(supply) == 10800
    supply["relative_difference_pct"] = 100.0 * (1.0 - supply.gain_relative_to_greedy.astype(float))

    group_cols = ["scenario", "service", "threshold_min", "objective", "rule"]
    rows = []
    for key, d in supply.groupby(group_cols, sort=True):
        d = d.sort_values("new_sites")
        assert list(d.new_sites) == list(range(1, 41))
        rel = d.relative_difference_pct.astype(float)
        rows.append(
            {
                **dict(zip(group_cols, key)),
                "budget_rho_with_relative_difference": safe_spearman(d.new_sites, rel),
                "early_median_pct_1_5": float(d.loc[d.new_sites.between(1, 5), "relative_difference_pct"].median()),
                "middle_median_pct_6_20": float(d.loc[d.new_sites.between(6, 20), "relative_difference_pct"].median()),
                "late_median_pct_21_40": float(d.loc[d.new_sites.between(21, 40), "relative_difference_pct"].median()),
                "final_difference_pct_at_40": float(d.loc[d.new_sites == 40, "relative_difference_pct"].iloc[0]),
                "maximum_positive_shortfall_pct": float(rel.max()),
                "minimum_relative_difference_pct": float(rel.min()),
                "share_budgets_below_greedy": float((rel > 1e-9).mean()),
                "step_of_maximum_positive_shortfall": int(d.loc[rel.idxmax(), "new_sites"]),
            }
        )
    trends = pd.DataFrame(rows)
    assert len(trends) == 270

    summary_rows = []
    for (objective, rule, service), d in trends.groupby(["objective", "rule", "service"]):
        summary_rows.append(
            {
                "objective": objective,
                "rule": rule,
                "service": service,
                "n_scenario_threshold_groups": int(len(d)),
                "median_budget_rho": float(d.budget_rho_with_relative_difference.median()),
                "share_groups_with_declining_relative_difference": float((d.budget_rho_with_relative_difference < 0).mean()),
                "median_early_pct_1_5": float(d.early_median_pct_1_5.median()),
                "median_middle_pct_6_20": float(d.middle_median_pct_6_20.median()),
                "median_late_pct_21_40": float(d.late_median_pct_21_40.median()),
                "median_final_pct_at_40": float(d.final_difference_pct_at_40.median()),
            }
        )
    phase = pd.DataFrame(summary_rows)
    assert len(phase) == 18

    trajectory_summary = (
        supply.groupby(["objective", "rule", "new_sites"], as_index=False)
        .agg(
            median_relative_difference_pct=("relative_difference_pct", "median"),
            q25_relative_difference_pct=("relative_difference_pct", lambda s: s.quantile(0.25)),
            q75_relative_difference_pct=("relative_difference_pct", lambda s: s.quantile(0.75)),
        )
    )
    assert len(trajectory_summary) == 240
    return trends, phase, trajectory_summary


def draw_figures(condition: pd.DataFrame, trajectory_summary: pd.DataFrame) -> None:
    FIG.mkdir(parents=True, exist_ok=True)
    labels = {"per_10k": "Per 10,000 residents", "per_km2": "Per km²", "per_100km": "Per 100 km roads"}
    objectives = [("district", "District-wide network gain"), ("equal", "Equal-subdistrict gain")]
    fig, axes = plt.subplots(1, 2, figsize=(9.6, 4.0), layout="constrained")
    for ax, (objective, title) in zip(axes, objectives):
        d = condition[condition.objective == objective]
        for proxy, marker in zip(PROXY_FIELDS, ("o", "s", "^")):
            q = d[d.proxy == proxy]
            ax.scatter(q.supply_opportunity_rho, q.first_step_shortfall_pct, alpha=0.7, marker=marker, label=labels[proxy])
        ax.set_title(title)
        ax.set_xlabel("Supply–opportunity rank correlation")
        ax.set_ylabel("First-step shortfall from best available gain (%)")
        ax.axhline(0, linewidth=0.8)
        ax.grid(alpha=0.2)
    axes[0].legend(frameon=False, fontsize=8)
    fig.suptitle("When do supply priorities diverge from network-coverage opportunity?")
    fig.savefig(FIG / "indicator_failure_conditions.png", dpi=300, bbox_inches="tight")
    plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(9.6, 4.0), layout="constrained")
    obj_titles = {"district_gain_m": "District-wide network gain", "gain_equal_street_mean_pp": "Equal-subdistrict gain"}
    for ax, objective in zip(axes, TRAJECTORY_OBJECTIVES):
        d = trajectory_summary[trajectory_summary.objective == objective]
        for rule in SUPPLY_RULES:
            q = d[d.rule == rule].sort_values("new_sites")
            ax.plot(q.new_sites, q.median_relative_difference_pct, linewidth=2, label=rule.replace("facilities_", ""))
            ax.fill_between(q.new_sites, q.q25_relative_difference_pct, q.q75_relative_difference_pct, alpha=0.12)
        ax.axhline(0, linewidth=0.8)
        ax.set_title(obj_titles[objective])
        ax.set_xlabel("Number of added facilities")
        ax.set_ylabel("Median difference from greedy reference (%)")
        ax.grid(alpha=0.2)
    axes[0].legend(frameon=False, fontsize=8)
    fig.suptitle("Budget dependence of supply-priority allocation")
    fig.savefig(FIG / "budget_scale_effects.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    street = pd.read_csv(OUT / "street_opportunity_540.csv")
    corr = pd.read_csv(OUT / "supply_opportunity_rank_correlations.csv")
    dec = pd.read_csv(OUT / "supply_priority_opportunity_audit.csv")
    traj = pd.read_csv(OUT / "sequential_addition_trajectories.csv")

    condition = build_failure_conditions(street, corr, dec)
    correlations = condition_correlations(condition)
    summary = condition_summary(condition)
    trends, phase, trajectory_summary = budget_trends(traj)

    condition.to_csv(OUT / "indicator_failure_conditions.csv", index=False)
    correlations.to_csv(OUT / "failure_condition_correlations.csv", index=False)
    summary.to_csv(OUT / "indicator_failure_summary.csv", index=False)
    trends.to_csv(OUT / "budget_shortfall_trends.csv", index=False)
    phase.to_csv(OUT / "budget_phase_summary.csv", index=False)
    trajectory_summary.to_csv(OUT / "budget_trajectory_summary.csv", index=False)
    draw_figures(condition, trajectory_summary)

    quality = {
        "source_street_opportunity_rows": int(len(street)),
        "source_rank_correlation_rows": int(len(corr)),
        "source_priority_audit_rows": int(len(dec)),
        "source_sequential_rows": int(len(traj)),
        "failure_condition_rows": int(len(condition)),
        "failure_condition_correlation_rows": int(len(correlations)),
        "failure_summary_rows": int(len(summary)),
        "budget_trend_rows": int(len(trends)),
        "budget_phase_summary_rows": int(len(phase)),
        "budget_trajectory_summary_rows": int(len(trajectory_summary)),
        "deterministic_location_scenarios_are_independent_samples": False,
        "inferential_p_values_reported": False,
        "network_simulation_rerun": False,
        "analysis_role": "descriptive_condition_and_budget_sensitivity_analysis",
    }
    (OUT / "failure_condition_quality_gate.json").write_text(json.dumps(quality, indent=2), encoding="utf-8")
    print(json.dumps(quality, indent=2))


if __name__ == "__main__":
    main()
