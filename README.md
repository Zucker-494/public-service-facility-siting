# Public Service Facility Siting in Yangpu District, Shanghai

This repository contains the spatial data, Python scripts, simulation outputs and figures for a study of public service facility allocation in Shanghai's Yangpu District. It examines the relationship between administrative supply measures and potential gains in pedestrian-network coverage, including their consequences for sequential facility investment.

## Study design

The study covers 12 subdistricts and three public services: healthcare (12 existing facilities), elderly care (65) and culture (12). The official inventory contains 89 facilities. Six locations with uncertain coordinates are represented by five deterministic address-based scenarios.

The principal candidate set contains 1,132 pedestrian-network nodes sampled at 240 m spacing. Candidate sets at 180 m and 320 m support sensitivity analysis. Network coverage is evaluated at 5-, 10- and 15-minute walking thresholds.

Three administrative supply measures are evaluated: facilities per 10,000 residents, per square kilometre and per 100 km of road. The analysis first compares supply scarcity with the highest available marginal coverage gain in each subdistrict. It then evaluates four sequential allocation rules: three supply-based rules that select the best candidate within the priority subdistrict, and a network-greedy reference that selects the best candidate across the district.

Each rule adds 1–40 facilities. The two evaluation objectives are additional district-wide covered road length and the equal-weight mean coverage improvement across subdistricts. The study also examines sensitivity to facility locations, candidate spacing and pedestrian-network filtering.

## Results

The supply-opportunity analysis produces 540 subdistrict-level records and 270 rank-correlation comparisons. The sequential experiment contains 14,400 scenario–rule–investment-step records. These are deterministic model outputs across related scenarios and steps.

Supply scarcity has different associations with available coverage gains under the two planning objectives. The sequential results show how the coverage outcomes of supply-based allocation compare with the network-greedy reference as the investment budget increases.

## Repository contents

| Location | Contents |
|---|---|
| `src/` | Spatial processing, allocation experiments, diagnostics and plotting scripts |
| `data/raw/` | Source data |
| `data/curated/` | Facility inventory |
| `data/processed/` | Processed spatial datasets |
| `data/qa/` | Data checks and provenance |
| `outputs/sequential_investment/` | Sequential allocation results and supply-opportunity analysis |
| `outputs/refined_model/` | Candidate-grid comparisons and sensitivity outputs |
| `outputs/figures/all_figures_png/` | 30 PNG figures |
| `tests/` | Computational checks |
| `docs/` | Methods, data sources and field definitions |

## Reproducing the analysis

Use Python 3.11 or later. Run these commands from the repository root.

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

Run the sequential allocation experiment:

```bash
python src/20_sequential_investment_experiment.py --max-sites 40 --benchmark-sample-check 20
```

Generate the supply-opportunity tables and the three associated figures from the stored candidate-level and sequential results:

```bash
python src/28_supply_opportunity_diagnostics.py
```

This script reads:

- `outputs/osm_inference/inferred_89_candidate_gains_5_scenarios_240m.csv`
- `outputs/address_restoration/full_official_supply_240m_with_partial_accessibility.csv`
- `outputs/sequential_investment/sequential_addition_trajectories.csv`

It writes six tables to `outputs/sequential_investment/`:

- `street_opportunity_540.csv`
- `supply_opportunity_rank_correlations.csv`
- `supply_priority_opportunity_audit.csv`
- `spatial_structure_correlations.csv`
- `paired_objective_correlations.csv`
- `sequential_median_shortfalls.csv`

The corresponding figures are saved in `outputs/figures/all_figures_png/`:

- `supply_opportunity_rank_validity.png`
- `supply_priority_opportunity.png`
- `sequential_opportunity_costs.png`

Other figure scripts are retained in `src/`:

```bash
python src/02_validate_and_figures.py
python src/09_publication_qa_figures.py
python src/15_osm_inference_figures.py
python src/19_decision_evidence_figures.py
python src/23_service_specific_budget_figures.py
python src/25_walkability_figures.py
python src/draw_decision_comparison.py
```

Run the tests:

```bash
python -m pytest -q tests
```

## Documentation and licensing

- [Methodology](docs/METHODOLOGY.md)
- [Data sources](docs/DATA_SOURCES.md)
- [Data dictionary](docs/DATA_DICTIONARY.md)

Road-network data include OpenStreetMap contributions (© OpenStreetMap contributors, ODbL). Original project code is distributed under the [MIT License](LICENSE.txt). Third-party data retain their respective licensing terms; see the [data sources](docs/DATA_SOURCES.md) for details.
