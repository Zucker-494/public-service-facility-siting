# Data dictionary

This document describes the principal inputs and outputs used for the current facility-siting study. Some folders also contain earlier diagnostic results; the principal sequential analyses are the 1–40-facility outputs identified below.

## Input and spatial data

| File or folder | Main contents |
|---|---|
| `data/raw/official_inventories/` | Original healthcare, elderly-care and cultural facility inventories |
| `data/curated/official_facility_registry_89_address_audited.csv` | Curated inventory of 89 existing facilities and associated address/coordinate evidence |
| `data/raw/yangpu_subdistrict_resident_population_census2020.csv` | 2020 population for 12 subdistricts |
| `data/raw/shanghai-260929.osm.pbf` | OSM nodes, ways and tags for network construction |
| `data/processed/p06_refined_clean.gpkg` | Spatial model layers used in refined network calculations |
| `data/processed/hypothetical_candidate_nodes.csv` | Candidate network node identities and projected positions |
| `outputs/refined_model/grid_180m/`, `grid_240m/`, `grid_320m/` | Candidate-grid sensitivity outputs, including candidate locations and marginal coverage gains |

## Principal sequential results

`outputs/sequential_investment/sequential_addition_trajectories.csv`

| Field | Definition |
|---|---|
| `scenario` | Existing-facility location scenario |
| `service` | `healthcare`, `elderly_care` or `culture` |
| `threshold_min` | Walking-time threshold, in minutes |
| `objective` | `district_gain_m` or `gain_equal_street_mean_pp` |
| `rule` | Supply-based siting rule or `network_greedy` reference |
| `new_sites` | Number of facilities added by the current step (1–40) |
| `candidate_id`, `added_candidate_node` | Identifier of the selected hypothetical new facility location |
| `added_candidate_subdistrict` | Subdistrict of the selected candidate |
| `marginal_gain` | Increment from the current new facility, in the objective's units |
| `cumulative_gain` | Total improvement after the current number of additions, in the objective's units |
| `district_length_gain_m` | Added district-wide covered road length, metres |
| `equal_street_mean_gain_pp` | Equal-weight mean subdistrict coverage increase, percentage points |
| `greedy_reference_gain` | Comparative cumulative result for the greedy reference, as recorded in the source table |
| `gain_relative_to_greedy`, `signed_shortfall_vs_greedy` | Differences relative to the reference under the stored sign convention |
| `baseline_inherited_geocodes`, `baseline_address_imputations` | Number of previously located and scenario-located existing facilities |
| `buildability_verified` | Whether candidate-site buildability has been independently verified |

The two objective measures have **different units**. A value in metres must not be compared numerically with a value in percentage points.

Other sequential files:

| File | Contents |
|---|---|
| `outputs/sequential_investment/new_added_site_sequence.csv` | Selected candidate sequence at each addition |
| `outputs/sequential_investment/expanded_budget_marginal_summary.csv` | Selected budget endpoints and per-step coverage gains |
| `outputs/sequential_investment/existing_six_imputation_provenance.csv` | Scenario treatment of six existing facilities without accepted inherited coordinates |
| `outputs/walkability_robustness/walkability_robustness_14400_rows.csv` | Separate sequential experiment under strict road-category filtering |
| `outputs/walkability_robustness/walkability_policy_comparison_summary.csv` | Summary of strategy performance across network variants |
| `outputs/figures/all_figures_png/` | One PNG per distinct figure subject, including paper figures and additional analyses |

## Figure groups

The single-format PNG directory includes:

- Service-specific cumulative gains, differences from the greedy reference and walking-threshold comparisons.
- Comparison of the baseline and restricted road-network conditions.
- Candidate sampling-grid sensitivity (180/240/320 metres).
- Planning objective and supply-rule comparisons.
- Source-network, facility-location and spatial-data quality diagnostics.

All figures should be interpreted alongside the source tables and the methodology rather than as independent measurements.

## Chinese and English fields

Where a published CSV includes a Chinese label or text field, companion English-readable columns may be provided using a `_en` suffix. Examples in the curated facility registry include:

- `facility_name` / `facility_name_en`
- `canonical_address` / `canonical_address_en`
- `subdistrict_name` / `subdistrict_name_en`

The original Chinese field is retained to preserve source identity. English fields are publication aids and are not necessarily officially adopted translations. Raw source files are not rewritten solely to add translations.
