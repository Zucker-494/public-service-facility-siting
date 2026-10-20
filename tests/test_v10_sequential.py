"""Checks the initial 12 steps directly from the retained 1–40 trajectories."""
from pathlib import Path
import json
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs/sequential_investment'


def data():
    x=pd.read_csv(OUT/'sequential_addition_trajectories.csv')
    return x.loc[x.new_sites.between(1,12)].copy()


def test_fixed_baseline_not_confused_with_new_sites():
    x=data()
    assert set(x.existing_facilities)=={89}
    assert set(x.baseline_inherited_geocodes)=={83}
    assert set(x.baseline_address_imputations)=={6}
    assert set(x.new_sites)==set(range(1,13))
    assert (x.all_facility_count==x.existing_facilities+x.new_sites).all()
    evidence=pd.read_csv(OUT/'existing_six_imputation_provenance.csv')
    assert len(evidence)==5*6
    assert not evidence.is_new_added_site.any()
    selected=pd.read_csv(OUT/'new_added_site_sequence.csv')
    selected=selected.loc[selected.step<=12].copy()
    assert len(selected)==len(x)
    assert selected.is_new_added_site.all()
    # Inferred EXISTING location nodes are never selected as a NEW facility of the same category.
    overlaps=selected.merge(evidence,left_on=['scenario','service','osm_node_id'],
       right_on=['scenario','service','imputed_osm_node_id'],how='inner')
    assert len(overlaps)==0


def test_no_candidate_reused_in_a_trajectory():
    x=data()
    group=['scenario','service','objective','rule','threshold_min']
    assert x.groupby(group).size().eq(12).all()
    assert (x.groupby(group)['added_candidate_node'].nunique()==12).all()
    assert x.groupby(group).new_sites.min().eq(1).all()
    assert x.groupby(group).new_sites.max().eq(12).all()
    assert (x.remaining_candidates==1132-x.new_sites).all()


def test_gain_monotonic_and_additive_across_steps():
    x=data().sort_values(['scenario','service','objective','rule','threshold_min','new_sites'])
    group=['scenario','service','objective','rule','threshold_min']
    for _,part in x.groupby(group):
        np.testing.assert_allclose(part.marginal_gain.cumsum(),part.cumulative_gain,rtol=1e-8,atol=.02)
        assert part.marginal_gain.min()>=-1e-7
        assert np.diff(part.cumulative_gain.to_numpy()).min()>=-1e-7


def test_exact_one_site_independent_and_qa_flags():
    q=json.loads((OUT/'sequential_quality_gate.json').read_text())
    assert q['validation_direct_network_distance_samples']>=20
    assert q['one_site_independent_oracle_check_rows']==90
    assert q['baseline_missing_points_not_new_sites']
    assert q['global_multiple_site_optimality']=='NOT_CLAIMED'
    assert q['scenario_estimates_are_confidence_intervals'] is False
    assert q['decision_results_contain_actual_buildability_validation'] is False
    assert q['maximum_abs_marginal_addition_discrepancy']<0.01


def test_five_scenarios_no_double_counting():
    x=data()
    assert len(x)==5*3*2*3*4*12
    assert x.scenario.nunique()==5
    assert x.service.nunique()==3
    assert x.objective.nunique()==2
    assert x.threshold_min.nunique()==3
    assert x.rule.nunique()==4
