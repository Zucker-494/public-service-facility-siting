from pathlib import Path
import json
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "sequential_investment"

def test_failure_condition_outputs():
    c = pd.read_csv(OUT / "indicator_failure_conditions.csv")
    r = pd.read_csv(OUT / "failure_condition_correlations.csv")
    s = pd.read_csv(OUT / "indicator_failure_summary.csv")
    assert len(c) == 270 and len(r) == 144 and len(s) == 6
    assert c.first_step_shortfall_pct.between(-1e-8, 100 + 1e-8).all()
    for field in ["priority_population_share", "priority_area_share", "priority_network_share", "priority_candidate_share"]:
        assert c[field].between(0, 1).all()

def test_budget_outputs():
    t = pd.read_csv(OUT / "budget_shortfall_trends.csv")
    p = pd.read_csv(OUT / "budget_phase_summary.csv")
    q = pd.read_csv(OUT / "budget_trajectory_summary.csv")
    assert len(t) == 270 and len(p) == 18 and len(q) == 240
    assert t.budget_rho_with_relative_difference.dropna().between(-1, 1).all()
    assert set(q.new_sites) == set(range(1, 41))

def test_quality_gate():
    d = json.loads((OUT / "failure_condition_quality_gate.json").read_text())
    assert d["network_simulation_rerun"] is False
    assert d["inferential_p_values_reported"] is False
    assert d["failure_condition_rows"] == 270
