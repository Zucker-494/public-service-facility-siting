#!/usr/bin/env python3
"""Validate the pedestrian-routing rules used by the main network."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import geopandas as gpd
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pbf_reader import read_osm
from pedestrian_access_rules import classify_pedestrian_access

PBF = ROOT / "data/raw/shanghai-260929.osm.pbf"
NETWORK = ROOT / "data/processed/p06_refined_clean.gpkg"
OUT = ROOT / "outputs/validation"
OUT.mkdir(parents=True, exist_ok=True)

TAG_KEYS = (
    "highway", "foot", "access", "motorroad", "sidewalk",
    "sidewalk:left", "sidewalk:right", "footway", "bridge", "tunnel",
)


def main() -> None:
    net = gpd.read_file(NETWORK, layer="osm_node_identity_edges", ignore_geometry=True)
    study = net[net.zone >= 0].copy()
    assert len(study) > 0
    assert study.osm_way_id.notna().all()
    needed = set(study.osm_way_id.astype(int))

    lookup = {}
    for row in read_osm(PBF):
        if row[0] != "way" or row[1] not in needed:
            continue
        tags = row[3]
        lookup[int(row[1])] = {k: tags.get(k, "") for k in TAG_KEYS}

    assert len(lookup) == len(needed), (len(lookup), len(needed))

    grouped = (
        study.groupby("osm_way_id", as_index=False)
        .agg(study_length_m=("length_m", "sum"), edge_count=("length_m", "size"))
    )
    rows = []
    for r in grouped.itertuples(index=False):
        wid = int(r.osm_way_id)
        tags = lookup[wid]
        allowed, basis = classify_pedestrian_access(tags)
        rows.append(
            {
                "osm_way_id": wid,
                "highway": tags.get("highway", ""),
                "foot": tags.get("foot", ""),
                "access": tags.get("access", ""),
                "motorroad": tags.get("motorroad", ""),
                "sidewalk": tags.get("sidewalk", ""),
                "sidewalk_left": tags.get("sidewalk:left", ""),
                "sidewalk_right": tags.get("sidewalk:right", ""),
                "study_length_m": float(r.study_length_m),
                "edge_count": int(r.edge_count),
                "pedestrian_allowed_by_rules": bool(allowed),
                "access_basis": basis,
            }
        )

    df = pd.DataFrame(rows)
    assert len(df) == len(needed)
    assert abs(df.study_length_m.sum() - study.length_m.sum()) < 0.01

    denied = df[~df.pedestrian_allowed_by_rules].copy()
    summary = (
        df.groupby(["pedestrian_allowed_by_rules", "access_basis"], as_index=False)
        .agg(study_length_m=("study_length_m", "sum"), way_count=("osm_way_id", "size"), edge_count=("edge_count", "sum"))
    )
    summary["pct_study_length"] = 100.0 * summary.study_length_m / df.study_length_m.sum()

    by_highway = (
        df.groupby(["highway", "pedestrian_allowed_by_rules", "access_basis"], as_index=False)
        .agg(study_length_m=("study_length_m", "sum"), way_count=("osm_way_id", "size"), edge_count=("edge_count", "sum"))
    )
    by_highway["pct_study_length"] = 100.0 * by_highway.study_length_m / df.study_length_m.sum()

    df.sort_values(["pedestrian_allowed_by_rules", "study_length_m"], ascending=[True, False]).to_csv(
        OUT / "pedestrian_access_rule_by_way.csv", index=False
    )
    summary.to_csv(OUT / "pedestrian_access_rule_summary.csv", index=False)
    by_highway.to_csv(OUT / "pedestrian_access_rule_by_highway.csv", index=False)

    allowed_length = float(df.loc[df.pedestrian_allowed_by_rules, "study_length_m"].sum())
    total_length = float(df.study_length_m.sum())
    qa = {
        "ruleset": "mainland_china_osm_default_access_plus_explicit_overrides_v1",
        "study_unique_osm_ways": int(len(df)),
        "study_network_km": total_length / 1000.0,
        "rule_supported_network_km": allowed_length / 1000.0,
        "rule_supported_network_pct": 100.0 * allowed_length / total_length,
        "rule_denied_way_count": int(len(denied)),
        "rule_denied_network_km": float(denied.study_length_m.sum() / 1000.0),
        "explicit_foot_denied_way_count": int((df.access_basis == "explicit_foot_deny").sum()),
        "explicit_access_denied_way_count": int((df.access_basis == "explicit_access_deny").sum()),
        "motorroad_denied_way_count": int((df.access_basis == "motorroad_implied_foot_no").sum()),
        "field_validation_performed": False,
        "routing_rule_gate": "PASS" if denied.empty else "FAIL",
        "interpretation": "PASS means every road used by the main model is pedestrian-routable under the documented OSM rule set; it does not mean field-survey validation.",
    }
    (OUT / "pedestrian_access_model_qa.json").write_text(
        json.dumps(qa, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(qa, ensure_ascii=False, indent=2))

    if not denied.empty:
        raise AssertionError(
            f"{len(denied)} modelled OSM ways are not pedestrian-routable under the documented rules; "
            "rebuild the network before using the main results."
        )


if __name__ == "__main__":
    main()
