# Quality assessment and publication gates

## A. Verified computational checks (PASSED)

- Full parser reads 2,724,101 source OSM node records and 450,999 source OSM ways; graph retains 94,154 node IDs, 106,698 graph edges and 21,615 street-way IDs inside the buffered study extent.
- 144 connected components; largest component accounts for 99.22% of the buffered graph's edge length. All components are preserved; no synthetic link creates false connectivity.
- 25,523 road edges assigned by midpoint to Yangpu; about 798.59 km of modelled study-area network length.
- Among 99 unshared geometric crossings inside Yangpu, 98 carry bridge/tunnel/nonzero layer information, and one at-grade footway/residential candidate requires manual validation. Source node topology does not join any of these automatically.
- 89 official primary service entities; 83 inherited geometries included; 6 omitted and individually audited.
- Main network connectors: median 16.28m; p90 64.52m; p95 82.52m; max 144.08m. 10/83 are beyond 60m. No 60m deletion.
- Three categories x 12 streets = 36 supply cells; 108 service-street-time accessibility cells; 27 one-facility policy comparisons.
- 1,149 candidate sites at 240m. Alternative 180m and 320m grids computed. Main integrity tests passed.

## B. Topology uncertainty (QUANTIFIED; field confirmation outstanding)

The at-grade unshared crossing occurs around (121.5032118,31.3160477), between OSM way 225995002 (footway) and way 1324895009 (residential). Connecting it changes several nearby OSM-node shortest paths by approximately 725–783m. For 320m-site grid experiments, maximum absolute difference in normalised policy regret across the 27 comparisons is approximately 0.00188, and the policy's chosen subdistrict does not change. Both outputs are retained. The baseline keeps original OSM node IDs.

Additional routing uncertainty remains possible where the underlying OSM data lacks a legitimate connection or encodes an access rule incompletely. The graph algorithm eliminates **fabricated geometric junctions**. Geographic truth would require independent field/map evidence for any disputed specific location. Inferences must reflect this scope.

## C. Six-facility missingness (MATERIAL)

The six omitted points comprise four elderly facilities and two cultural activity centres. In the restricted 83-site universe, 大桥街道 and 延吉新村街道 have zero *included* cultural sites, despite the official inventory reporting a cultural centre for each. The priority subdistrict from each cultural proxy changes when official inventories are counted (`data/qa/missingness_changes_priority.csv`). Therefore, **cultural-service regret comparisons are descriptive sensitivity results and should not support journal headline claims about complete supply**.

The most defensible current primary inference is a network-constrained *conditional* experiment using the accepted coordinate universe. Publication claims about complete public-service planning require additional validation or a restricted conclusion that explicitly incorporates missing data.

## D. Remaining methodological tests before journal submission

1. Independently verify the geocoding and spatial location of the inherited 83 records. Existing 'A' labels are inherited documentation, not a new 2026 field survey.
2. Resolve the one ambiguous at-grade footway/road crossing using independent map/survey evidence, or explicitly use both topology conditions in inference.
3. Check boundary-crossing edge lengths with exact polygon clipping rather than midpoint-only assignment, and verify source boundary appropriateness.
4. Test alternative pedestrian access interpretations: primary/secondary roads with foot restrictions, OSM service/track access, and pedestrian barriers.
5. Expand or justify candidate feasibility assumptions using public detailed-plan parcels if such data can be obtained; maintain network-node only interpretation otherwise.
6. Strengthen inferential design using uncertainty intervals over spatial decision units and grid candidate sets. Twelve streets do not constitute a large independent spatial sample.
7. Assess the interaction of facility coordinate omission with all three policy strategies; cultural-priority reversals show this is substantive.
8. Test multi-facility budgets and optimise sequential placements if such claims are intended; current model simulates **one added site** per category.
9. Confirm redistribution licences for OSM-derived data and third-party geocoder-derived coordinates before public GitHub release.

## E. Manuscript claims currently supported

**Supported:** Under a fully specified pedestrian OSM graph and 83 included coordinates, different supply-proxy priority rules generate the recorded one-site network-length benefits and regrets; outcomes are conditional on candidate feasibility assumptions and missingness.

**Not established by current data:** Population-served gains, real land-use suitability, empirical effectiveness of street proxy rules for actual construction, policy causality, representativeness beyond Yangpu, or accurate service-wide cultural accessibility after six deletions.
