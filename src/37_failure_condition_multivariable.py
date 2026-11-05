#!/usr/bin/env python3
"""Descriptive multivariable analysis of first-step allocation shortfalls.

The 270 rows contain repeated deterministic sensitivity settings, so this script
does not report inferential p-values. It fits standardized descriptive linear
models and evaluates coefficient stability by leaving out each facility-location
scenario in turn.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "outputs" / "sequential_investment" / "indicator_failure_conditions.csv"
OUT = ROOT / "outputs" / "failure_condition_multivariable"
OUT.mkdir(parents=True, exist_ok=True)

# Keep one priority-area size variable only. Candidate share was removed because
# it is perfectly inversely correlated with priority population share in this
# experiment, which made the earlier descriptive model rank-deficient.
CONTINUOUS = [
    "supply_opportunity_rho",
    "opportunity_top_share",
    "supply_cv",
    "priority_population_share",
    "threshold_min",
]
CATEGORICAL = ["objective", "proxy", "service"]


def prepare(df: pd.DataFrame):
    work = df.copy()
    stats = {}
    for col in CONTINUOUS:
        mean = float(work[col].mean())
        sd = float(work[col].std(ddof=0))
        assert sd > 0, col
        work[col + "_z"] = (work[col] - mean) / sd
        stats[col] = {"mean": mean, "sd": sd}

    pieces = [pd.Series(1.0, index=work.index, name="intercept")]
    for col in CONTINUOUS:
        pieces.append(work[col + "_z"].rename(col))

    dummies = pd.get_dummies(work[CATEGORICAL], prefix=CATEGORICAL, drop_first=True, dtype=float)
    for col in dummies.columns:
        pieces.append(dummies[col])

    X = pd.concat(pieces, axis=1).astype(float)
    y = work["first_step_shortfall_pct"].astype(float)
    return work, X, y, stats


def fit(X: pd.DataFrame, y: pd.Series):
    arr = X.to_numpy(dtype=float)
    target = y.to_numpy(dtype=float)
    beta, _, rank, singular = np.linalg.lstsq(arr, target, rcond=None)
    pred = arr @ beta
    resid = target - pred
    sse = float(np.sum(resid ** 2))
    sst = float(np.sum((target - target.mean()) ** 2))
    r2 = 1.0 - sse / sst
    condition_number = float(singular.max() / singular.min())
    assert int(rank) == int(X.shape[1]), (rank, X.shape)
    assert condition_number < 100.0, condition_number
    return beta, pred, r2, int(rank), condition_number


def model_for_subset(df: pd.DataFrame, model_name: str):
    work, X, y, scaling = prepare(df)
    beta, pred, r2, rank, cond = fit(X, y)

    rows = []
    for name, value in zip(X.columns, beta):
        rows.append({
            "model": model_name,
            "term": name,
            "full_sample_coefficient": float(value),
            "leave_one_scenario_out_median": np.nan,
            "leave_one_scenario_out_min": np.nan,
            "leave_one_scenario_out_max": np.nan,
        })

    loo = {name: [] for name in X.columns}
    scenarios = sorted(work.scenario.unique())
    for scenario in scenarios:
        keep = work.scenario != scenario
        b, _, _, _, _ = fit(X.loc[keep], y.loc[keep])
        for name, value in zip(X.columns, b):
            loo[name].append(float(value))

    out = pd.DataFrame(rows)
    for i, row in out.iterrows():
        vals = np.asarray(loo[row.term], dtype=float)
        out.loc[i, "leave_one_scenario_out_median"] = float(np.median(vals))
        out.loc[i, "leave_one_scenario_out_min"] = float(vals.min())
        out.loc[i, "leave_one_scenario_out_max"] = float(vals.max())

    diagnostics = {
        "model": model_name,
        "n_rows": int(len(work)),
        "n_scenarios": int(len(scenarios)),
        "r_squared": float(r2),
        "matrix_rank": int(rank),
        "design_columns": int(X.shape[1]),
        "condition_number": float(cond),
        "full_rank": bool(rank == X.shape[1]),
        "inferential_p_values_reported": False,
        "scenario_settings_treated_as_independent_samples": False,
    }
    return out, diagnostics, scaling


def main():
    df = pd.read_csv(SRC)
    assert len(df) == 270
    assert df.scenario.nunique() == 5

    all_results = []
    diagnostics = []
    scaling = {}

    for name, subset in [
        ("pooled", df),
        ("district_only", df[df.objective == "district"].copy()),
        ("equal_subdistrict_only", df[df.objective == "equal"].copy()),
    ]:
        res, diag, scale = model_for_subset(subset, name)
        all_results.append(res)
        diagnostics.append(diag)
        scaling[name] = scale

    coef = pd.concat(all_results, ignore_index=True)
    coef.to_csv(OUT / "standardized_descriptive_coefficients.csv", index=False)

    selected_terms = CONTINUOUS.copy()
    selected = coef[coef.term.isin(selected_terms)].copy()
    selected.to_csv(OUT / "selected_boundary_condition_coefficients.csv", index=False)

    # Pairwise correlations are retained to document the predictor-screening step.
    screening_cols = CONTINUOUS + ["priority_candidate_share", "first_step_shortfall_pct"]
    corr = df[screening_cols].corr(method="spearman")
    corr.to_csv(OUT / "predictor_spearman_matrix.csv")

    paired = (
        df[df.proxy.isin(["per_10k", "per_km2"])]
        .pivot_table(
            index=["scenario", "service", "threshold_min", "objective"],
            columns="proxy",
            values=["first_step_shortfall_pct", "fraction_of_global_best"],
            aggfunc="first",
        )
    )
    paired.columns = ["__".join(c).strip("_") for c in paired.columns]
    paired = paired.reset_index()
    paired["same_first_step_performance"] = np.isclose(
        paired["fraction_of_global_best__per_10k"],
        paired["fraction_of_global_best__per_km2"],
        rtol=1e-11,
        atol=1e-12,
    )
    paired.to_csv(OUT / "population_area_rule_agreement.csv", index=False)

    agreement_summary = {
        "n_paired_cases": int(len(paired)),
        "same_first_step_performance_rate_pct": float(100.0 * paired.same_first_step_performance.mean()),
        "median_absolute_shortfall_difference_pp": float(
            np.median(
                np.abs(
                    paired["first_step_shortfall_pct__per_10k"]
                    - paired["first_step_shortfall_pct__per_km2"]
                )
            )
        ),
    }

    qa = {
        "analysis_type": "descriptive_standardized_linear_models_with_leave_one_scenario_out_stability",
        "rows": int(len(df)),
        "deterministic_location_scenarios": 5,
        "models": diagnostics,
        "continuous_predictors": CONTINUOUS,
        "excluded_collinear_predictor": "priority_candidate_share",
        "exclusion_reason": "perfect inverse Spearman correlation with priority_population_share",
        "categorical_controls": CATEGORICAL,
        "inferential_p_values_reported": False,
        "causal_interpretation": False,
        "population_area_rule_agreement": agreement_summary,
        "scaling": scaling,
    }
    (OUT / "multivariable_quality_gate.json").write_text(
        json.dumps(qa, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
