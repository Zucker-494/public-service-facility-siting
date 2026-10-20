# Derived-output dictionary

| File | Key fields and units | Data lineage |
|---|---|---|
| `p06_rebuilt_network.gpkg/osm_node_identity_edges` | `u_id`,`v_id` original OSM node IDs; `osm_way_id`; `length_m`; `highway`,`bridge`,`tunnel`,`layer`; `zone` | Raw OSM PBF → tagged pedestrian filter → node-reference edges → EPSG:32651 |
| `facility_connector_distances_full.csv` | `facility_name`; `facility_type`; `snap_distance_m`; `edge_index`; `projected_fraction` | 83 accepted legacy points → STRtree nearest OSM edge → projected connector |
| `six_facilities_evidence_and_exclusion.csv` | source name, official address, evidence URL, reason and exclusion status | 89 entity inventory minus 83 accepted geometries, public source cross-check |
| `hypothetical_candidate_nodes.csv` | `candidate_node`; `zone`; `x,y` projected metres | Reconstructed OSM graph → candidate ground-node filter → spatial lattice |
| `supply_verified.csv` | 3 service categories × 12 subdistricts; `count_verified`; per-population/area/network supply proxies | 83 included site counts ÷ sourced denominators |
| `observed_accessibility.csv` | `threshold_min`; `covered_network_m`; `total_network_m`; `network_coverage_share` | Multi-source shortest paths including connectors → partial road edge coverage |
| `candidate_marginal_gain.csv` | `candidate_id`; `district_gain_m`; `target_subdistrict_gain_m` | Recompute covered network length with one additional hypothetical site |
| `decision_regret.csv` | `policy_expected_gain_m`; `oracle_gain_m`; `decision_regret_m`; `regret_fraction`; `optimistic_zone_regret_m` | Deterministic proxy choices and exhaustive candidate comparisons |
| `grid_robustness_summary.csv` | regret range across grid 180/240/320 metres | Re-run candidate generation and entire evaluation independently |
| `missingness_changes_priority.csv` | source-inventory versus 83-site analytical priority | Source count presence without imputing unknown coordinates |
| `unshared_crossings_district.csv` | crossings of road segments without common OSM nodes | Physical geometric crossings query against source-node network |

Metric denominators are sourced; all coordinates in the derived GeoPackage use EPSG:32651. The original dataset retains WGS84 geocoded source points and service names. `p_naive_not_inferential` fields in the descriptive table are exploratory coefficients only; they are not used to support inferential statements.
