# Public Service Facility Siting in Yangpu District, Shanghai

This repository contains Python code, spatial datasets, and modelled results examining whether subdistrict-level service provision predicts the pedestrian-network coverage opportunity of new public facilities.

## Study design

The study covers 12 subdistricts in Shanghai's Yangpu District and three facility types: healthcare (12 existing facilities), elderly care (65), and culture (12). The official inventory contains 89 facilities; six locations are represented through five deterministic address-based scenarios. The main analysis uses 1,132 candidate network nodes at 240 m spacing, with 180 m and 320 m candidate grids for sensitivity checks.

Three supply indicators measure facilities per 10,000 residents, per square kilometre, and per 100 km of road. The opportunity analysis compares each subdistrict's supply rank with its best available marginal pedestrian-network coverage gain. The allocation experiment selects new facilities within the lowest-supply subdistrict or, for the network-greedy reference, across all district candidates.

Each service is simulated separately for 1–40 additions, with 5, 10, and 15 minute walking thresholds. The planning objectives are additional district-wide road length covered and the equal-weight mean subdistrict coverage improvement. The study also examines network filtering, candidate spacing, and uncertain facility locations.

## Main findings

Supply scarcity shows different spatial associations with achievable coverage gains under the two planning objectives. Across 45 service–scenario–walking-threshold settings, the median Spearman rank correlations between supply scarcity and available gains are 0.46, 0.76, and 0.87 under the district-length objective for the population-, area-, and road-normalised indicators, respectively. The corresponding medians under the equal-subdistrict objective are 0.00, −0.24, and −0.40.

The sequential experiment quantifies how these differences affect accumulated coverage across 1–40 additions. In 270 first-step comparisons, 14.8% of supply-priority choices matched the network-greedy candidate. These results describe deterministic modelling outcomes for the Yangpu case study.

## Repository structure

| Directory | Contents |
|---|---|
| `src/` | Data preparation, network analysis, simulations, and figure generation |
| `data/raw/` | Source spatial data and facility inventories |
| `data/curated/` | Consolidated facility records |
| `data/processed/` | Network and candidate-node data |
| `data/qa/` | Data provenance and spatial diagnostics |
| `outputs/sequential_investment/` | Sequential simulation and supply-opportunity analysis tables |
| `outputs/figures/all_figures_png/` | 30 figures in PNG format |
| `tests/` | Computational checks |
| `docs/` | Methods, data provenance, and field definitions |

## Running the code

Use Python 3.11 or later. Install dependencies from the repository root:

```bash
python -m pip install -r requirements.txt
```

Run the sequential allocation experiment:

```bash
python src/20_sequential_investment_experiment.py --max-sites 40 --benchmark-sample-check 20
```

Regenerate the existing figure set:

```bash
python src/02_validate_and_figures.py
python src/09_publication_qa_figures.py
python src/15_osm_inference_figures.py
python src/19_decision_evidence_figures.py
python src/23_service_specific_budget_figures.py
python src/25_walkability_figures.py
python src/draw_decision_comparison.py
```

Regenerate the supply-opportunity analysis tables and three additional figures:

```bash
python src/28_supply_opportunity_diagnostics.py
```

The new analysis outputs are:

- `outputs/sequential_investment/street_opportunity_540.csv`
- `outputs/sequential_investment/supply_opportunity_rank_correlations.csv`
- `outputs/sequential_investment/supply_priority_opportunity_audit.csv`
- `outputs/sequential_investment/spatial_structure_correlations.csv`
- `outputs/sequential_investment/paired_objective_correlations.csv`
- `outputs/sequential_investment/sequential_median_shortfalls.csv`

The three corresponding figures are:

- `outputs/figures/all_figures_png/supply_opportunity_rank_validity.png`
- `outputs/figures/all_figures_png/supply_priority_opportunity.png`
- `outputs/figures/all_figures_png/sequential_opportunity_costs.png`

Run computational checks:

```bash
python -m pytest -q tests
```

The main sequential simulation file is `outputs/sequential_investment/sequential_addition_trajectories.csv`. Candidate-grid comparisons are stored under `outputs/refined_model/grid_180m/`, `grid_240m/`, and `grid_320m/`; cross-grid summaries include `outputs/refined_model/policy_robustness_all_grids.csv` and `outputs/refined_model/proxy_ranking_validity_all_grids.csv`.

## Documentation and attribution

- [Methodology](docs/METHODOLOGY.md)
- [Data sources](docs/DATA_SOURCES.md)
- [Data dictionary](docs/DATA_DICTIONARY.md)

Road-network data include OpenStreetMap contributions (© OpenStreetMap contributors, ODbL). See [Data sources](docs/DATA_SOURCES.md) for provenance and redistribution conditions. Original project code is licensed under the [MIT License](LICENSE.txt); third-party data retain their respective licence terms.
