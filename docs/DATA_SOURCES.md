# Data sources and provenance

## Study inputs

| Source | Repository location | Use |
|---|---|---|
| Shanghai OSM extract (29 September 2026) | `data/raw/shanghai-260929.osm.pbf` | Source network geometry, node identities, ways and road attributes |
| Geofabrik source GIS archive (September 2026) | `data/raw/shanghai-260928-free.gpkg.zip` | Supporting GIS source data and spatial-context checks |
| Yangpu project spatial database | `data/raw/p06_yangpu_original.gpkg` | Inherited study boundaries and previously derived facility geometry |
| 2020 Seventh National Population Census, subdistrict totals | `data/raw/yangpu_subdistrict_resident_population_census2020.csv` | Population denominators |
| Official facility inventories | `data/raw/official_inventories/` | Healthcare, elderly-care and cultural-facility records |
| Curated 89-record facility registry | `data/curated/official_facility_registry_89_address_audited.csv` | Facility identifiers, addresses, source references and existing-location information |

The study uses 12 Yangpu subdistricts. The three facility categories contain 12, 65 and 12 existing records respectively. Official inventory membership and verified facility entrance positions are different forms of evidence: six existing records have no accepted inherited coordinates and are analysed using alternative location scenarios.

## Derived spatial information

- `data/processed/p06_refined_clean.gpkg` contains refined spatial inputs used in the network analysis.
- `data/processed/hypothetical_candidate_nodes.csv` and the candidate-node files under `outputs/refined_model/` record the sampled hypothetical siting locations.
- `outputs/refined_model/grid_180m/`, `grid_240m/` and `grid_320m/` contain candidate-grid comparisons.
- `outputs/sequential_investment/` contains the sequential siting trajectories and derived summaries.
- `outputs/walkability_robustness/` contains results for the alternative road-category configuration.

Road-network length and walking distances use metric coordinates in EPSG:32651. The model uses OSM connectivity and tag evidence; mapped roads should not automatically be treated as independently verified pedestrian routes.

## Facility names, addresses and translations

The original Chinese names and addresses remain in source and derived data. Several published CSV files also include English companion fields, normally ending in `_en`, such as `facility_name_en` or `subdistrict_name_en`.

An English companion field may contain a translated label or romanised identifier. It should not be represented as an official institution name unless confirmed by the source organisation. Chinese source values remain the reference for identifying the facility.

## Data licensing and access

OpenStreetMap-derived data are subject to the Open Database License (ODbL), including attribution and potentially applicable share-alike requirements. Public availability of a government document does not by itself establish unrestricted redistribution rights for every extracted or joined dataset. Some inherited geocoding coordinates also have uncertain upstream redistribution permissions.

Repository files remain subject to their original source licences and attribution requirements. Where upstream redistribution rights are unclear, the documentation records provenance and the route used to obtain or reconstruct the input rather than asserting unrestricted reuse.

Relevant source portals include:

- [OpenStreetMap](https://www.openstreetmap.org/)
- [Geofabrik downloads](https://download.geofabrik.de/)
- [Shanghai Open Data](https://data.sh.gov.cn/view/)
- [Shanghai detailed planning map](https://shanghai.tianditu.gov.cn/xg/map.html)

The detailed planning map is contextual evidence, not a verified cadastral layer establishing the buildability of the sampled candidate nodes.
