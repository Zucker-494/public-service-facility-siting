# Methodology

## Study design

The study examines whether street-level public service supply indicators provide useful priorities for sequential facility siting. The case study covers 12 subdistricts in Yangpu District, Shanghai, and three separately modelled services: healthcare, elderly care, and culture.

The source inventory contains 89 existing facilities: 12 healthcare, 65 elderly-care, and 12 cultural facilities. Spatial coordinates are inherited for 83 existing facilities; six additional existing facilities are represented using five deterministic, address-constrained location scenarios. The six uncertain locations are part of the **existing baseline**, not new developments.

## Road network and accessibility

The baseline road network is derived from a September 2026 Shanghai OpenStreetMap (OSM) extract. OSM node identities and way attributes are retained when constructing network connectivity, including the distinction between shared network nodes and geometrically intersecting roads that are not connected.

Walking-network coverage is measured at 5-, 10-, and 15-minute thresholds with an assumed walking speed of 1.2 m/s. Road lengths and distances are calculated in a projected coordinate reference system (EPSG:32651). A road segment can be partially covered at a walking-distance threshold. For each service, existing facilities of that category establish the initial network coverage.

Two separate planning objectives are evaluated:

1. **District-wide network gain:** additional length of covered modelled roads, in metres (reported in kilometres in figures).
2. **Equal-subdistrict gain:** the arithmetic mean of coverage-rate improvements across the 12 subdistricts, in percentage points.

These metrics quantify changes in modelled road coverage, not the number of people served.

## Candidate locations and supply indicators

The main sequential experiment uses 1,132 hypothetical candidate locations selected from the road network using a 240-metre spatial sampling grid. Separate 180-metre and 320-metre candidate-grid results support a sampling-sensitivity comparison. The grid sizes refer to candidate sampling, not to service radii or assumed facility catchments.

For each service and subdistrict, three indicators are calculated using the current number of facilities of that service:

- Facilities per 10,000 residents.
- Facilities per square kilometre.
- Facilities per 100 kilometres of modelled road.

The 2020 census provides the subdistrict population denominators. Administrative areas and modelled road lengths provide the other denominators.

## Sequential facility siting

Each service is simulated independently, adding one to 40 hypothetical new facilities. Each step updates the service's facility counts, coverage state, and marginal gains for the remaining candidate locations.

Four decision rules are compared:

- **Population-normalised supply:** select the subdistrict with the lowest current facilities-per-10,000-residents indicator.
- **Area-normalised supply:** select the subdistrict with the lowest current facilities-per-square-kilometre indicator.
- **Road-length-normalised supply:** select the subdistrict with the lowest current facilities-per-100-kilometres indicator.
- **Network-greedy reference:** select the candidate with the greatest current marginal gain across the entire district.

For each of the three supply-based rules, after identifying the lowest-supply subdistrict (or tied subdistricts), the algorithm selects the remaining candidate that yields the **highest marginal network-coverage gain within that selection set**. Candidate choice is not random. Each planning objective is evaluated separately.

The network-greedy reference maximises the **current step's** gain over the available candidate set. It is not claimed to solve the globally optimal multi-facility placement problem.

The principal trajectories are stored in `outputs/sequential_investment/sequential_addition_trajectories.csv`, including the service, scenario, walking threshold, objective, rule, step, selected site, marginal gain, and cumulative gain.

## Sensitivity analyses

The project includes:

- Five deterministic existing-facility location scenarios for the six records lacking accepted coordinates.
- Three walking-time thresholds (5, 10, 15 minutes).
- Two separately defined network-planning objectives.
- Candidate-grid comparisons using 180-, 240-, and 320-metre sampling.
- A stricter OSM road-category filtering scenario, recalculated against its **own** network-specific baseline and greedy reference.

The main sequential experiment contains 14,400 rows (five location scenarios × three services × three thresholds × two objectives × four rules × 40 steps). The restricted-road experiment is stored separately in `outputs/walkability_robustness/walkability_robustness_14400_rows.csv`.

The five location scenarios are deterministic sensitivity settings, not independent observations or statistical confidence samples.

## Interpretation and reproducibility

The central outcome is the change in **modelled pedestrian-network coverage** associated with alternative street-priority rules. Candidate nodes have not been verified as legally or physically buildable parcels, and the available source data do not independently establish all entrance locations or actual walking permissions. These data properties should be considered when interpreting spatial planning applications.

The source scripts are in `src/`; the datasets, derived tables, and charts are in `data/` and `outputs/`. The project root `README.md` provides execution guidance. For the current sequential figures, the underlying aggregation is recorded in `outputs/figures/sequential_v11/figure_data_all_services_all_thresholds.csv` when that file is present in the distribution.
