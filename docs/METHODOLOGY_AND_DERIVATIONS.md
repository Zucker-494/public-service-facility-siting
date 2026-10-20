# Methods and reproducible derivation chain

## Inputs and temporal units

- `data/raw/shanghai-260929.osm.pbf`: Shanghai OpenStreetMap snapshot (node, way ID, way tag) dated 2026-09-29.
- `data/raw/p06_yangpu_original.gpkg`: frozen predecessor project; subdistrict operational polygons and inherited accepted facility coordinates are the derived inputs needing downstream validation.
- `data/raw/official_inventories/`: official source entity registers. Source inventory: 12 healthcare centres, 65 elderly-care institutions, 12 cultural activity centres.
- `data/raw/yangpu_subdistrict_resident_population_census2020.csv`: 2020 Seventh Census subdistrict totals; administrative time mismatch is retained.

## Step 1: network reconstruction

`src/pbf_reader.py` parses OSM PBF blocks (zlib), dense OSM node ID deltas, node coordinates, way node-reference deltas, and way tags. The network is limited to Shanghai PBF nodes in a 0.035-degree spatial buffer around the Yangpu subdistrict bounding box. The buffer extends well beyond the 15-minute baseline distance; it avoids treating the district boundary as a pedestrian barrier.

Pedestrian-permitted OSM `highway` classes are defined in `PEDESTRIAN_HIGHWAYS`; motorways/trunks and explicit `foot=no`, `access=no/private`, and `motorroad=yes` are excluded. Cycling-only paths are included only when pedestrian access is explicitly tagged. The policy is reproducible and remains sensitive to missing access tags.

For each retained way, graph edges connect **adjacent original OSM node IDs**. Graph nodes are the real source IDs. Shared x/y coordinates alone never imply a connection. Projection from WGS84 to `EPSG:32651` precedes edge-length calculation. Source OSM way IDs, road types, `bridge`, `tunnel` and `layer` tags are stored for every edge. No arbitrary grade-specific numerical snap tolerance is used.

Road graph connectivity and all geometric intersections without OSM node sharing are audited. The one unshared crossing without grade-separation tags, a footway against a residential road at approximately (121.5032118,31.3160477), is tested in a separate connected scenario. The main graph follows original OSM node identities.

## Step 2: audited geocoded facilities

The legacy spatial layer `facility_accessibility_ready` provides 83 previously accepted records. The six exclusions are recorded in `data/qa/six_facilities_evidence_and_exclusion.csv` and traced to original entity names, original documented addresses, independent public source URLs, and specific geometry limitations. Original site coordinates for those six are never substituted by unrelated OSM polygons or street centroids. The official inventory still contains those six source records.

For each included point, compute the exact geometric nearest *road segment* via Shapely STRtree, then its perpendicular distance \(c_i\) and projected fraction \(a_i\) on the edge. A temporary facility source connects to the two segment endpoints using weights \(c_i+a_iL\) and \(c_i+(1-a_i)L\). The connector is treated as access friction, with no threshold exclusion. A nearby bridged/tunnel edge may be unusable despite proximity; this receives an explicit QA check in `02_validate_and_figures.py` and the source road tags are retained.

## Step 3: network-length coverage

Baseline walking speed \(v=1.2\)m/s. Radii \(R_t=60vt\): 360, 720, 1080 metres for 5, 10, 15 minutes. Multi-source network Dijkstra returns minimal network travel length \(d_u\) to each road vertex (including facility connector cost). The reachable length of a road edge of length \(L\) with endpoints \(u,v\) is approximated as

\[
  \ell_t=\min\{L,\min[L,\max(0,R_t-d_u)]+\min[L,\max(0,R_t-d_v)]\}.
\]

Edges are assigned to the operational subdistrict polygon covering their midpoint. The denominator is total modelled edge length assigned to that district. This midpoint assignment is a reproducible approximation for short OSM node-to-node segments; edges straddling boundaries can introduce small measurement error and exact polygon clipping is an outstanding QA enhancement. It is inappropriate to treat these outputs as the number or fraction of resident people covered.

## Step 4: supply proxies

For each category and street, count accepted facilities from the **same 83-site spatial analysis universe**. Compute count / 2020 population ×10,000; count / street polygon area km²; count / pedestrian network length × 100,000 m. All denominators have source evidence. The official 89-site inventory is preserved as an *additional missingness audit*, without imputing its six uncertain locations.

## Step 5: one-new-facility decision experiment

Candidate points are sampled from on-grade walking-network source nodes using a fixed projected spatial lattice, default 240m. Candidate nodes are **hypothetical network insertion locations**, with unknown property rights, land ownership, vacancy, building codes and service-type suitability. Candidate IDs and coordinates appear in `hypothetical_candidate_nodes.csv`. The 180m and 320m grid experiments test sampling sensitivity.

For each category, each candidate is added as a new network source. New vertex distances are \(\min(d_u,d_u^{new})\). Recompute district network length coverage and sum gains over all 12 streets. A site maximising new district-wide network length coverage is the *network oracle* under the sampled candidate set; the analysis is a finite optimisation exercise.

Each proxy policy picks the street with the smallest simple supply proxy; within the chosen street the policy selects a candidate uniformly from the sampled nodes. Expected gain is the arithmetic average of all local candidate gains. For a matched budget of one hypothetical facility, define

\[
  Regret=(G_{oracle}-E[G_{policy}])/G_{oracle},\quad G_{oracle}>0.
\]

The `optimistic_zone_regret_m` column also records the benefit loss assuming a network-optimal **site within the selected street**; this separates region-choice error from within-region siting error. The broad regret combines the two errors by design. It is unrelated to financial cost or demographic welfare.

All three proxies and the oracle use the same candidate set, walking threshold and outcome. Statistical association between proxy residuals and another quantity containing the same observed accessibility is excluded from this research design.

## Step 6: audit and diagnostics

- `src/02_validate_and_figures.py`: data integrity, time monotonicity, positive marginal gains, finite connector cost and figures.
- `src/03_missingness_and_policy_audit.py`: inventory vs accessible-site counts and proxy priority changes due to six coordinate omissions.
- `src/04_topology_exception_diagnostic.py`: alternative routing distance across one potentially missing at-grade OSM intersection.

Outputs can be rebuilt without invoking any private geocoder or downloading fresh live data. The previous project GPKG is frozen and its SHA-256 is recorded. Full upstream geocoder command/API logs are unavailable and must not be reconstructed speculatively.
