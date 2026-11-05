from pathlib import Path
import json
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

def test_pedestrian_access_rule_outputs():
    out = ROOT / "outputs" / "validation"
    q = json.loads((out / "pedestrian_access_model_qa.json").read_text())
    assert q["routing_rule_gate"] == "PASS"
    assert q["rule_denied_way_count"] == 0
    assert q["rule_supported_network_pct"] > 99.999
    assert q["field_validation_performed"] is False
    d = pd.read_csv(out / "pedestrian_access_rule_by_way.csv")
    assert d.pedestrian_allowed_by_rules.all()

def test_walkability_contribution_robustness_outputs():
    out = ROOT / "outputs" / "walkability_robustness"
    d = pd.read_csv(out / "walkability_contribution_robustness.csv")
    assert len(d) == 6
    assert set(d.new_sites) == {1, 12, 40}
    assert d.spearman_original_vs_strict_loss.dropna().between(-1, 1).all()
    q = json.loads((out / "walkability_contribution_robustness_qa.json").read_text())
    assert 0 <= q["best_proxy_agreement_all_budgets"] <= 1
    assert 0 <= q["best_proxy_agreement_15min"] <= 1
