# Source access and provenance

| Dataset | Status | Reproducible acquisition / origin | Research role |
|---|---|---|---|
| September 2026 Shanghai OSM PBF | SUPPLIED | `shanghai-260929.osm.pbf`, contributed by researcher, Geofabrik / © OpenStreetMap contributors | Raw geometry, OSM node identities, road tags |
| September 2026 Geofabrik free GIS GeoPackage | SUPPLIED | `shanghai-260928-free.gpkg.zip`, researcher copy | Source cross-check, road/land-use supporting evidence |
| Yangpu operational subdistrict polygons | FROZEN DERIVED DATA | `p06_yangpu_original.gpkg`, OSM-boundary predecessor GIS dataset | Reporting units, area, spatial joins |
| 2020 census by 12 subdistricts | SUPPLIED OFFICIAL EXTRACT | Original P06 repo `data/raw/yangpu_subdistrict_resident_population_census2020.csv` | Population-divisor supply metric |
| Healthcare centre official inventory | SUPPLIED | Original P06 repo official list | Source records and selected coordinates |
| Elderly-care 2024 inventory | SUPPLIED | Original P06 repo official list | Source records and selected coordinates |
| Culture activity-centre official inventory | SUPPLIED | Original P06 repo official list | Source records and selected coordinates |
| Existing facility geocoded point candidates | FROZEN DERIVED DATA | Legacy `facility_accessibility_ready` | 83 inherited geometries; six excluded; upstream geocoder QA partly documented in original repo |
| Authoritative buildable site polygons | PUBLIC VIEWER FOUND; DOWNLOAD UNVERIFIED | Shanghai detailed-plan public map: https://shanghai.tianditu.gov.cn/xg/map.html | Excluded from the current experiment; site feasibility UNKNOWN |
| Fine-scale population | ALTERNATIVE OPEN DATA FOUND; NOT INTEGRATED | WorldPop 2020 constrained top-down gridded model: https://hub.worldpop.org/Global1_2000-2020 | Excluded; modelled spatial population must be separately evaluated and aligned to census baseline |

DataShanghai open platform: https://data.sh.gov.cn/view/ provides accessible datasets with variable licence and access conditions. A catalogue being public does not certify availability of bulk cadastral/site polygons or resident-level records.

## Verified public sources for six omitted coordinates

- Daqiao cultural activity centre, 平凉路1730号: Shanghai official 2026 cultural programme, https://www.shanghai.gov.cn/nw17239/20260615/18afd18823ac4b80b0b5270001e04cfe.html
- Yanji cultural activity centre, alternative reported cultural event venue 控江路645弄21号: https://www.shanghai.gov.cn/nw17239/20250922/b91728e3a1054f68af5d48aaec87f8ca.html ; older central-office address 延吉中路77号 appears in other directories.
- Xinlan elderly-care operator, 世界路203号: Shanghai Medical Insurance Administration https://ybj.sh.gov.cn/gsgg/20230918/e4ca6dfbefb641fea3f6fe0195d32680.html and operator https://www.senior-living.citic/
- Renhe elderly care: Yangpu Government 2024 care-bed support notice https://www.shyp.gov.cn/zhengwu/mzj-gyjsygl/2025/219/9a3687cf8d29a385c1ecea069ba67b0f.html
- Changhai Road elderly institution, 翔殷路505弄9号: Yangpu district official https://www.shyp.gov.cn/shypq/ggfw-bmgg/20241016/465932.html
- Huichen Changbai elderly welfare institute: 2023 list indicates 民治路15号 https://mzj.sh.gov.cn/MZ_zhuzhan23_0-2-8/20230630/94b3d20431e449dbaa7caaef4d86be76.html ; 2024 municipal report and official operator identify 春江路815号, https://mzj.sh.gov.cn/MZ_zhuzhan34_0-2-6/20241213/8a4cd7a8d26f483e95e8fd98802f40ab.html

These sources corroborate presence or address histories. None provides a verified coordinate in a reproducible geospatial dataset; all six are therefore omitted from the spatially restricted baseline per researcher instruction. Provenance and exact exclusion reasons remain public and searchable in the QA CSV.

## Public dissemination

Original road and network data contain OSM contributors' work and are subject to Open Database License terms. Provider-specific geocoding-derived coordinates have unverified redistribution rights. Inspect these rights before publicly releasing the archived original GeoPackage and layers created from it. The submitted bundle is a private researcher handoff until licence checks are complete.
