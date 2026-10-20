# Public service facility siting in Yangpu District, Shanghai

A reproducible spatial simulation examining whether subdistrict-level public service supply indicators identify locations with high marginal pedestrian-network coverage gains.

## Study design

The study covers 12 subdistricts in Yangpu, with 89 existing facilities (12 healthcare, 65 elderly care, 12 culture). Six facilities without confirmed coordinates are retained through five deterministic location scenarios. New facilities are selected separately from 1,132 hypothetical candidate road-network nodes. Three lowest-supply-first rules (facilities per 10,000 residents, per km², and per 100 km of road) are compared with a network-greedy reference. Both the district-wide additional road length and the equally weighted average improvement across subdistricts are assessed at 5-, 10-, and 15-minute walking thresholds. Each service is simulated independently for 1–40 successive additions. A stricter road-class filtering scenario tests network sensitivity.

The supply-led rules use network marginal gains to select candidates **within the selected priority subdistrict**. The network-greedy comparator selects the current best candidate across the whole district; it is not a global optimum over all multi-site combinations.

## Repository structure

- `src/` — source data processing, network analysis, sequential simulations, and plotting.
- `data/raw/` — source GIS files and official facility inventories.
- `data/curated/` — curated facility registers.
- `data/processed/` — derived network and candidate locations.
- `data/qa/` — data provenance and spatial quality checks.
- `outputs/` — analysis outputs, simulation trajectories, and data for figures.
- `outputs/figures/final_manuscript_and_supplement_set/` — all manuscript and supplementary figures, with vector exports where available.
- `tests/` — automated computation checks.
- `docs/` — methods, data dictionary, source access, and reproducibility notes.

## Reproduce

Use Python 3.11+ and install packages with:

```bash
pip install -r requirements.txt
```

For the main sequential simulation and corresponding nine service-specific figures:

```bash
python src/20_sequential_investment_experiment.py --max-sites 40 --benchmark-sample-check 20
python src/23_service_specific_budget_figures.py
python -m pytest -q tests
```

These analyses read from the included processed data and write their outputs to `outputs/`. For complete source reconstruction, consult `docs/METHODOLOGY_AND_DERIVATIONS.md` and `docs/DATA_SOURCES_AND_ACCESS.md`.

## Principal findings

Across 270 first-round rule comparisons, 14.8% of supply-based choices matched the best current network marginal gain. Outcomes depend on the planning objective, service category, and investment budget. Strict road-category filtering can change which simplified rule performs best. The simulated gain is covered network length or mean subdistrict coverage improvement, not observed numbers of residents served.

## Figures and data

All figure files used in the paper and the original supplement are collected in `outputs/figures/final_manuscript_and_supplement_set/`. Service-specific 1–40 addition figures can be recreated using `src/23_service_specific_budget_figures.py`; their plotted values appear in `outputs/figures/sequential_v11/figure_data_all_services_all_thresholds.csv`. Original computed trajectories are in `outputs/sequential_investment/`.

## Data provenance and licensing

The road network uses an OpenStreetMap snapshot (© OpenStreetMap contributors, ODbL). Facility inventories are from the corresponding public governmental publications. Some historical geocodes and original GIS files may have separate redistribution terms; review `docs/DATA_SOURCES_AND_ACCESS.md` before publishing this repository publicly. The model includes unverified entry locations and hypothetical siting candidates; candidate nodes are not certified buildable parcels.

Code licensing: see `LICENSE-CODE.txt`.


## Candidate-grid sensitivity and the 240 m selection

The 240 m lattice is the main experimental candidate set (1,132 network nodes). The 180 m and 320 m lattices were compared to check candidate sampling sensitivity. The comparison is retained in this public-research bundle, rather than submitted as supplementary material.

- `outputs/refined_model/grid_180m/`, `grid_240m/`, and `grid_320m/`: candidate-site inventories, per-site marginal network gains, priority decisions, and diagnostics.
- `outputs/refined_model/policy_robustness_all_grids.csv` and `proxy_ranking_validity_all_grids.csv`: cross-grid summaries.
- `outputs/tables/grid_robustness_all.csv` and `grid_robustness_summary.csv`: initial grid sensitivity results.
- `outputs/figures/refined/07_corrected_candidate_grid_sensitivity.pdf`: comparison figure.
- `outputs/sensitivity/grid_180m/` and `grid_320m/`: additional sampling sensitivity outputs.

The comparisons document the modeling choice; they do not prove that 240 m is universally optimal. Please refer to the methods documentation for the grid-generation rules.

## Supplementary results hosted in the repository

The plots of differences from the greedy reference, 5/10/15-minute threshold comparisons, pedestrian tagging evidence, and alternative walking-network scenarios are available under `outputs/figures/final_manuscript_and_supplement_set/` and the corresponding `outputs/` data folders. There is 
