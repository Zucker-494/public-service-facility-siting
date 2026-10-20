# Public Service Facility Siting in Yangpu District, Shanghai

This repository contains the data, Python workflows, and results for a GIS study of public service facility siting. The study compares subdistrict-level supply indicators with network-based selection and examines how different investment sequences affect walking-network coverage.

## Study overview

The analysis covers 12 subdistricts in Yangpu District, Shanghai, and three service categories: healthcare, elderly care, and culture. The baseline comprises 89 existing facility records: 12 healthcare, 65 elderly-care, and 12 cultural facilities. Five location scenarios represent six existing facilities whose coordinates require address-based estimation.

Three supply indicators determine subdistrict investment priority:

- Facilities per 10,000 residents
- Facilities per square kilometre
- Facilities per 100 kilometres of modelled road network

Within the priority subdistrict, each rule selects the candidate with the greatest current marginal coverage gain. A network-greedy reference instead selects the highest-gain candidate across the full district.

Each service is simulated independently as 1–40 facilities are added from a common set of 1,132 hypothetical network-node candidates. Results are evaluated at 5-, 10-, and 15-minute walking thresholds using two planning objectives: additional covered road length across the district and mean coverage improvement across the 12 subdistricts.

## Main findings

Across 270 first-round comparisons, 14.8% of supply-based selections achieved the highest available single-step network coverage gain. Relative performance varied by service category and planning objective. As facilities were added, cumulative coverage increased while marginal gains generally diminished. Road-category filtering also changed the relative performance of some supply indicators.

Together, the results show how existing facility supply and remaining network coverage opportunities can lead to different investment priorities.

## Repository contents

| Path | Contents |
|---|---|
| `src/` | Network construction, spatial analysis, siting experiments and figure generation |
| `data/raw/` | Original spatial datasets and facility inventories |
| `data/curated/` | Consolidated facility records |
| `data/processed/` | Derived network and candidate-node data |
| `data/qa/` | Source and spatial-data checks |
| `outputs/sequential_investment/` | Selected-site sequences and cumulative coverage results |
| `outputs/refined_model/` | Candidate locations, marginal gains and grid-sensitivity results |
| `outputs/walkability_robustness/` | Road-category sensitivity results |
| `outputs/figures/all_figures_png/` | Main-paper and additional analysis figures, one PNG per figure |
| `tests/` | Computational checks |
| `docs/` | Methodology, data sources and data dictionary |

## Reproducing the analysis

Python 3.11 or later is recommended. Install dependencies from the repository root:

```bash
python -m pip install -r requirements.txt
```

Run the main sequential facility-siting experiment, generate the service-specific figures, and execute the computational tests:

```bash
python src/20_sequential_investment_experiment.py --max-sites 40 --benchmark-sample-check 20
python src/23_service_specific_budget_figures.py
python -m pytest -q tests
```

The plotting script exports multiple formats during a local run. The curated figure directory, `outputs/figures/all_figures_png/`, contains the PNG versions selected for this repository.

Detailed definitions and data provenance are provided in:

- [`docs/METHODOLOGY.md`](docs/METHODOLOGY.md)
- [`docs/DATA_SOURCES.md`](docs/DATA_SOURCES.md)
- [`docs/DATA_DICTIONARY.md`](docs/DATA_DICTIONARY.md)

## Candidate-grid sensitivity

The main experiment uses a 240 m candidate-sampling grid, yielding 1,132 network-node candidates. Additional 180 m and 320 m candidate sets allow comparison of siting outcomes across sampling densities.

The relevant data are available in:

- `outputs/refined_model/grid_180m/`
- `outputs/refined_model/grid_240m/`
- `outputs/refined_model/grid_320m/`
- `outputs/refined_model/policy_robustness_all_grids.csv`
- `outputs/refined_model/proxy_ranking_validity_all_grids.csv`
- `outputs/tables/grid_robustness_all.csv`
- `outputs/tables/grid_robustness_summary.csv`

The corresponding figure is `outputs/figures/all_figures_png/07_corrected_candidate_grid_sensitivity.png`.

## Figures and additional results

All 27 distinct project figures are organised under `outputs/figures/all_figures_png/`. The collection covers sequential coverage gains, walking-time thresholds, alternative planning objectives, supply-rule comparisons, candidate-grid sensitivity, road-network assumptions, and facility-location analysis.

Supporting data are retained in the relevant `outputs/` directories. The full sequential trajectory table is:

`outputs/sequential_investment/sequential_addition_trajectories.csv`

English companion columns are provided alongside relevant Chinese place and facility names in the curated analysis tables. Original Chinese names are retained for source identification.

## Data sources and citation

The analysis uses OpenStreetMap network data, Yangpu District public service inventories, subdistrict population statistics, and derived spatial datasets. The repository also records address-based location scenarios and road-network sensitivity analyses.

Source references, spatial assumptions, and redistribution conditions are described in [`docs/DATA_SOURCES.md`](docs/DATA_SOURCES.md). OpenStreetMap data are attributed to © OpenStreetMap contributors under the Open Database License.

The source-code licence is provided in [`LICENSE-CODE.txt`](LICENSE-CODE.txt).
