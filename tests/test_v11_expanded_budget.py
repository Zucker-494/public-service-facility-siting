"""Published 1..40 budget result-level controls, separate from source-geocode validation."""
from pathlib import Path
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
NEW=ROOT/'outputs/sequential_investment/sequential_addition_trajectories.csv'
F=ROOT/'outputs/sequential_investment/new_added_site_sequence.csv'
E=ROOT/'outputs/sequential_investment/existing_six_imputation_provenance.csv'

def test_dimension_counts():
    d=pd.read_csv(NEW)
    assert len(d)==14400
    assert d.scenario.nunique()==5 and d.service.nunique()==3
    assert d.threshold_min.nunique()==3 and d.objective.nunique()==2
    assert d.rule.nunique()==4
    assert set(d.new_sites.unique())==set(range(1,41))
    assert set(d.existing_facilities)=={89}
    assert set(d.baseline_address_imputations)=={6}
    assert (d.all_facility_count==89+d.new_sites).all()

def test_initial_twelve_steps_retained():
    cur=pd.read_csv(NEW)
    first=cur.loc[cur.new_sites.between(1,12)].copy()
    group=['scenario','service','objective','rule','threshold_min']
    assert len(first)==4320
    assert first.groupby(group).size().eq(12).all()
    assert first.groupby(group)['candidate_id'].nunique().eq(12).all()
    assert (first.remaining_candidates==1132-first.new_sites).all()


def test_marginal_gains_and_decomposition():
    d=pd.read_csv(NEW)
    k=['scenario','service','objective','rule','threshold_min']
    d=d.sort_values(k+['new_sites'])
    for _,x in d.groupby(k,sort=False):
        assert len(x)==40
        assert np.all(np.diff(x.cumulative_gain)>=-1e-7)
        np.testing.assert_allclose(x.cumulative_gain.values,np.cumsum(x.marginal_gain.values),rtol=1e-10,atol=.0001)
        np.testing.assert_allclose(x.greedy_reference_gain-x.cumulative_gain,x.signed_shortfall_vs_greedy,atol=.0001)

def test_inferred_existing_positions_are_not_new_locations():
    a=pd.read_csv(F);b=pd.read_csv(E)
    assert a.is_new_added_site.all()
    assert (~b.is_new_added_site).all()
    collision=a.merge(b,left_on=['scenario','service','osm_node_id'],right_on=['scenario','service','imputed_osm_node_id'],how='inner')
    assert len(collision)==0
    k=['scenario','service','objective','rule','threshold_min']
    assert not a.duplicated(k+['osm_node_id']).any()

def test_figure_data_matches_sources():
    d=pd.read_csv(NEW)
    p=pd.read_csv(ROOT/'outputs/figures/sequential_v11/figure_data_all_services_all_thresholds.csv')
    assert len(p)==2880 and p.n_scenarios.eq(5).all()
    group=d[(d.service=='culture')&(d.objective=='district_gain_m')&(d.rule=='network_greedy')&(d.threshold_min==15)&(d.new_sites==40)]
    q=p[(p.service=='culture')&(p.objective=='district_gain_m')&(p.rule=='network_greedy')&(p.threshold_min==15)&(p.new_sites==40)]
    assert len(q)==1
    np.testing.assert_allclose(q.gain_median.iloc[0],group.cumulative_gain.median(),atol=.001)
