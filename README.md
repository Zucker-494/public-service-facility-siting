# Public Service Facility Siting in Yangpu District, Shanghai

This repository contains Python code, spatial datasets, and simulation results for a study of how subdistrict-level public service supply indicators relate to pedestrian-network coverage gains from new facility locations.

## Study design

The analysis covers 12 subdistricts and three services: healthcare (12 existing facilities), elderly care (65), and culture (12). The 89-record facility inventory includes six existing locations represented by five deterministic address-based scenarios. The principal experiment uses 1,132 hypothetical candidate network nodes sampled at 240 m spacing, with 180 m and 320 m candidate sets for sensitivity analysis.

Three supply-based priority rules use facilities per 10,000 residents, per square kilometre, and per 100 km of modelled road. For each rule, the candidate with the greatest current marginal coverage gain is chosen within the priority subdistrict. A district-wide network-greedy rule provides a comparison. Each service is simulated separately for 1–40 successive additions, with walking thresholds of 5, 10, and 15 minutes.

Two planning objectives are evaluated: additional covered road length across the district and the equal-weight mean coverage improvement across the 12 subdistricts. Further analyses examine road-network filtering, candidate-grid spacing, and uncertain existing-facility locations.

## Main result

In 270 first-round comparisons, 14.8% of supply-based choices matched the corresponding network-greedy first-step choice. Performance varied with service category, planning objective, and investment sequence.

## Repository structure

| Directory | Contents |
|---|---|
| `src/` | Data preparation, network modelling, simulations, and figures |
| `data/raw/` | Source spatial data and facility inventories |
| `data/curated/` | Consolidated facility records |
| `data/processed/` | Network and candidate-node data |
| `data/qa/` | Data provenance and spatial diagnostics |
| `outputs/` | Derived tables, simulation results, and sensitivity analyses |
| `outputs/figures/all_figures_png/` | 27 project figures in PNG format |
| `tests/` | Computational checks |
| `docs/` | Methods, data provenance, and field definitions |

## Running the code

Use Python 3.11 or later. From the repository root, install the requirements:

```bash
python -m pip install -r requirements.txt
```

The included processed spatial data support the principal sequential experiment:

```bash
python src/20_sequential_investment_experiment.py --max-sites 40 --benchmark-sample-check 20
```

Regenerate the project figures using the following scripts:

```bash
python src/02_validate_and_figures.py
python src/09_publication_qa_figures.py
python src/15_osm_inference_figures.py
python src/19_decision_evidence_figures.py
python src/23_service_specific_budget_figures.py
python src/25_walkability_figures.py
python src/draw_decision_comparison.py
```

These scripts generate the 27 project figures in outputs/figures/all_figures_png/ using the repository's analytical outputs. Run the computational checks using:

```bash
python -m pytest -q tests
```

The main simulation results are in `outputs/sequential_investment/sequential_addition_trajectories.csv`. Candidate-grid comparisons are in `outputs/refined_model/grid_180m/`, `grid_240m/`, and `grid_320m/`; cross-grid summaries are in `outputs/refined_model/policy_robustness_all_grids.csv` and `outputs/refined_model/proxy_ranking_validity_all_grids.csv`.

## Documentation and attribution

- [Methodology](docs/METHODOLOGY.md)
- [Data sources](docs/DATA_SOURCES.md)
- [Data dictionary](docs/DATA_DICTIONARY.md)

The road data include OpenStreetMap contributions (© OpenStreetMap contributors, ODbL). See [Data sources](docs/DATA_SOURCES.md) for provenance and redistribution conditions. The project code is licensed under the [MIT License](LICENSE.txt); the repository's third-party datasets retain their respective licensing terms.
