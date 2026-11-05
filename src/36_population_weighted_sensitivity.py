#!/usr/bin/env python3
"""Population-weighted sensitivity analysis for sequential public-facility siting.

This sensitivity keeps the existing pedestrian-network model and candidate set, but
weights each covered road metre by the population-per-road-metre of its subdistrict.
The resulting objective is a population-weighted network-coverage proxy, not a
person-level accessibility measure. Population is assumed to be distributed
uniformly over the evaluated road network within each subdistrict.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import time
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from numba import njit

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "outputs" / "population_weighted_sensitivity"
DEST.mkdir(parents=True, exist_ok=True)

spec = importlib.util.spec_from_file_location(
    "p06_sequential", ROOT / "src/20_sequential_investment_experiment.py"
)
seq = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = seq
spec.loader.exec_module(seq)

SERVICE_ORDER = seq.SERVICE_ORDER
PROXY_KEYS = seq.PROXY_KEYS
SCENARIO_INDEX = seq.SCENARIO_INDEX
RULES = ("population_weighted_greedy",) + PROXY_KEYS


@njit(cache=True)
def all_population_marginal_gains(
    ptr, segs, du, dv, eu, ev, length, zone, weight,
    current, population_per_network_metre, available
):
    """Marginal population-weighted network coverage for all available candidates."""
    n = available.shape[0]
    result = np.zeros((n, 3), dtype=np.float64)
    radii = (360.0, 720.0, 1080.0)
    for i in range(n):
        if not available[i]:
            continue
        for j in range(ptr[i], ptr[i + 1]):
            e = segs[j]
            L = length[e]
            a = current[eu[e]]
            b = current[ev[e]]
            aa = du[j]
            bb = dv[j]
            z = zone[e]
            w = weight[e]
            density = population_per_network_metre[z]
            for ti in range(3):
                R = radii[ti]
                l0 = min(L, max(0.0, R - a))
                r0 = min(L, max(0.0, R - b))
                before = min(L, l0 + r0)
                l1 = min(L, max(0.0, R - min(a, aa)))
                r1 = min(L, max(0.0, R - min(b, bb)))
                after = min(L, l1 + r1)
                delta = (after - before) * w * density
                if delta > 0:
                    result[i, ti] += delta
    return result


def weighted_coverage(coverage_by_zone, population, zone_length):
    """Convert covered road length by zone to a population-weighted coverage proxy."""
    return (coverage_by_zone / zone_length * population).sum(axis=1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-sites", type=int, default=40)
    ap.add_argument("--scenario", type=str, default="all")
    ap.add_argument("--benchmark-sample-check", type=int, default=12)
    args = ap.parse_args()
    assert 1 <= args.max_sites <= 40
    begin = time.time()

    edges = gpd.read_file(ROOT / "data/processed/p06_refined_clean.gpkg", layer="osm_node_identity_edges")
    bounds = gpd.read_file(ROOT / "data/processed/p06_refined_clean.gpkg", layer="study_subdistricts")
    snaps = pd.read_csv(ROOT / "data/qa/facility_connector_distances_full.csv")
    candidates = pd.read_csv(ROOT / "outputs/refined_model/grid_240m/hypothetical_candidate_nodes_validated.csv")
    registry = pd.read_csv(ROOT / "data/curated/official_facility_registry_89_address_audited.csv", encoding="utf-8-sig")
    options = pd.read_csv(ROOT / "outputs/osm_inference/six_facility_plausible_osm_network_nodes.csv", encoding="utf-8-sig")
    supply = pd.read_csv(ROOT / "outputs/address_restoration/full_official_supply_240m_with_partial_accessibility.csv")

    assert len(registry) == 89
    assert registry.inherited_spatial_point_present.sum() == 83
    assert len(candidates) == 1132 and candidates.candidate_node.is_unique
    assert len(snaps) == 83

    names = list(bounds.subdistrict_name)
    assert set(supply.subdistrict) == set(names)
    street_id = {n: i for i, n in enumerate(names)}
    c_zone = candidates.subdistrict.map(street_id).astype(int).to_numpy()

    matrix, arr, facility_verts, quality = seq.ref.construct_refined_graph(edges, bounds, snaps)
    u, v, L, z, w = arr
    zone_length = np.bincount(z, weights=L * w, minlength=12)
    assert (zone_length > 0).all()

    pop_ref = (
        supply.query("service == 'healthcare'")
        .set_index("subdistrict")
        .loc[names, "population_census2020"]
        .astype(float)
        .to_numpy()
    )
    assert (pop_ref > 0).all()
    population_per_network_metre = pop_ref / zone_length

    node_map = dict(zip(edges.u_id.astype(int), edges.u_index.astype(int)))
    node_map.update(zip(edges.v_id.astype(int), edges.v_index.astype(int)))
    assert (candidates.candidate_node.map(node_map).astype(int) == candidates.candidate_index).all()

    cache = seq.make_sparse_cache(matrix, arr, candidates)
    ptr, segs, du, dv, _, _, _ = cache

    # Independent direct-Dijkstra validation on the first scenario, healthcare baseline.
    rep0 = SCENARIO_INDEX[0]
    src0, _ = seq.select_scenario_sources(snaps, facility_verts, registry, options, node_map, rep0)
    current0 = seq.ref.source_distance(matrix, src0["healthcare"])
    basecov0 = seq.ref.measure(current0, arr)
    sample = np.linspace(0, len(candidates) - 1, args.benchmark_sample_check, dtype=int)
    for ci in sample:
        direct_candidate = seq.ref.source_distance(matrix, [int(candidates.candidate_index.iloc[ci])])
        after = seq.ref.measure(np.minimum(current0, direct_candidate), arr)
        expected = weighted_coverage(after - basecov0, pop_ref, zone_length)
        mask = np.zeros(len(candidates), dtype=np.bool_)
        mask[ci] = True
        predicted = all_population_marginal_gains(
            ptr, segs, du, dv, u, v, L, z, w,
            current0, population_per_network_metre, mask
        )[ci]
        np.testing.assert_allclose(predicted, expected, rtol=1e-5, atol=0.02)

    fixed_89 = supply.set_index(["service", "subdistrict"])
    scenarios = list(SCENARIO_INDEX)
    if args.scenario != "all":
        scenarios = [SCENARIO_INDEX[int(args.scenario) - 1]]

    bys = c_zone[:, None] == np.arange(12)[None, :]
    ncan = len(candidates)
    records = []

    for rep in scenarios:
        sid = f"INFERRED_89_{rep + 1:02d}"
        sources, _ = seq.select_scenario_sources(snaps, facility_verts, registry, options, node_map, rep)
        for service in SERVICE_ORDER:
            basedist = seq.ref.source_distance(matrix, sources[service])
            basecov = seq.ref.measure(basedist, arr)
            base_weighted = weighted_coverage(basecov, pop_ref, zone_length)

            s = fixed_89.loc[service].loc[names]
            base_count = s["count_full_official"].astype(int).to_numpy()
            pop = s.population_census2020.astype(float).to_numpy()
            area = s.area_km2.astype(float).to_numpy()
            road = s.network_km.astype(float).to_numpy()
            np.testing.assert_allclose(pop, pop_ref)
            denom = np.column_stack((pop / 10000.0, area, road / 100.0))
            assert np.all(denom > 0)

            for rule in RULES:
                for ti, minutes in enumerate(seq.ref.THRESHOLDS):
                    current = basedist.copy()
                    selected = np.zeros(ncan, dtype=np.bool_)
                    unit_counts = base_count.copy()
                    for budget in range(1, args.max_sites + 1):
                        gains = all_population_marginal_gains(
                            ptr, segs, du, dv, u, v, L, z, w,
                            current, population_per_network_metre, ~selected
                        )
                        sc = gains[:, ti]
                        allowed = ~selected
                        tied = []
                        if rule != "population_weighted_greedy":
                            pi = PROXY_KEYS.index(rule)
                            ratio = unit_counts / denom[:, pi]
                            m = ratio.min()
                            tied = np.flatnonzero(np.isclose(ratio, m, rtol=1e-11, atol=1e-12)).tolist()
                            allowed = allowed & np.isin(c_zone, tied)
                        choices = np.flatnonzero(allowed)
                        assert len(choices) > 0
                        ci = int(choices[int(np.argmax(sc[choices]))])
                        delta = float(sc[ci])
                        assert delta >= -1e-6
                        current = seq.apply_candidate(current, ci, cache)
                        selected[ci] = True
                        unit_counts[c_zone[ci]] += 1

                        actual_cov = seq.ref.measure(current, arr)
                        actual_weighted = weighted_coverage(actual_cov, pop_ref, zone_length)
                        cumulative = float(actual_weighted[ti] - base_weighted[ti])

                        records.append(dict(
                            scenario=sid,
                            service=service,
                            threshold_min=int(minutes),
                            objective="population_weighted_network_coverage",
                            rule=rule,
                            new_sites=budget,
                            candidate_id=ci,
                            added_candidate_node=int(candidates.candidate_node.iloc[ci]),
                            added_candidate_subdistrict=names[c_zone[ci]],
                            marginal_population_equivalent_gain=delta,
                            cumulative_population_equivalent_gain=cumulative,
                            priority_subdistrict_tie_count=len(tied) if tied else 0,
                            population_weighting_assumption="uniform_population_per_network_metre_within_subdistrict",
                        ))
            print("finished", sid, service, "elapsed", round(time.time() - begin, 1), flush=True)

    result = pd.DataFrame(records)
    idx = ["scenario", "service", "threshold_min", "new_sites"]
    greedy = (
        result[result.rule.eq("population_weighted_greedy")]
        .set_index(idx)["cumulative_population_equivalent_gain"]
    )
    result["greedy_reference_gain"] = result.set_index(idx).index.map(greedy)
    assert (result.greedy_reference_gain > 0).all()
    result["gain_relative_to_greedy"] = (
        result.cumulative_population_equivalent_gain / result.greedy_reference_gain
    )
    result["relative_shortfall_pct"] = 100.0 * (1.0 - result.gain_relative_to_greedy)
    result.to_csv(DEST / "population_weighted_trajectories.csv", index=False)

    supply_only = result[result.rule != "population_weighted_greedy"].copy()
    first = supply_only[supply_only.new_sites == 1].copy()
    first["exact_first_step_match"] = np.isclose(
        first.gain_relative_to_greedy, 1.0, rtol=1e-11, atol=1e-12
    )
    first_summary = (
        first.groupby("rule", as_index=False)
        .agg(
            n_cases=("exact_first_step_match", "size"),
            exact_first_step_match_rate_pct=("exact_first_step_match", lambda x: 100.0 * x.mean()),
            median_shortfall_pct=("relative_shortfall_pct", "median"),
            q25_shortfall_pct=("relative_shortfall_pct", lambda x: x.quantile(0.25)),
            q75_shortfall_pct=("relative_shortfall_pct", lambda x: x.quantile(0.75)),
        )
    )
    first_summary.to_csv(DEST / "population_weighted_first_step_summary.csv", index=False)

    budgets = [1, 5, 12, 20, 30, 40]
    budget_summary = (
        supply_only[supply_only.new_sites.isin(budgets)]
        .groupby(["rule", "new_sites"], as_index=False)
        .agg(
            median_shortfall_pct=("relative_shortfall_pct", "median"),
            q25_shortfall_pct=("relative_shortfall_pct", lambda x: x.quantile(0.25)),
            q75_shortfall_pct=("relative_shortfall_pct", lambda x: x.quantile(0.75)),
        )
    )
    budget_summary.to_csv(DEST / "population_weighted_budget_summary.csv", index=False)

    by_service = (
        first.groupby(["service", "rule"], as_index=False)
        .agg(
            exact_first_step_match_rate_pct=("exact_first_step_match", lambda x: 100.0 * x.mean()),
            median_shortfall_pct=("relative_shortfall_pct", "median"),
        )
    )
    by_service.to_csv(DEST / "population_weighted_first_step_by_service.csv", index=False)

    qa = {
        "objective": "population_weighted_network_coverage",
        "interpretation": "covered road length weighted by subdistrict population per evaluated road metre",
        "person_level_accessibility_claimed": False,
        "within_subdistrict_population_distribution_assumption": "uniform_over_evaluated_road_network",
        "existing_facilities": 89,
        "candidate_sites": int(len(candidates)),
        "scenario_variants": int(len(scenarios)),
        "services": int(len(SERVICE_ORDER)),
        "walking_thresholds": 3,
        "new_site_budgets": int(args.max_sites),
        "direct_dijkstra_validation_candidates": int(len(sample)),
        "result_rows": int(len(result)),
        "global_multiple_site_optimality": "NOT_CLAIMED",
        "elapsed_sec": round(time.time() - begin, 1),
    }
    (DEST / "population_weighted_quality_gate.json").write_text(
        json.dumps(qa, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(json.dumps(qa, indent=2), flush=True)


if __name__ == "__main__":
    main()
