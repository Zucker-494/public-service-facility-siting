# Candidate-site experiment and analytical interpretation

**Scientific estimand:** difference in district-wide network-length gain from a new hypothetical facility between a proxy-led policy and a graph oracle under identical candidate constraints.

## Decision design

1. Restrict all candidates to original at-grade pedestrian-network nodes; sample one node per 240m projected grid cell. This controls count while approximating network spatial opportunity. It is not a legal construction-site screen.
2. Freeze actual facility set by service category before generating any candidate. Every source location receives its observed connector cost.
3. The three supply indicators choose the minimum-value subdistrict; no accessibility outcome enters this subdistrict decision.
4. Draw a local node uniformly at random. Since all candidate gains are computed exhaustively, the expected result is the exact mean over candidate sites rather than a Monte Carlo approximation.
5. Compute two loss measures: (a) decision regret of random local siting; (b) the *optimistic* regret of the best local site, quantifying the error in street selection alone.
6. Re-evaluate at 5/10/15 minutes and candidate lattice 180m/240m/320m. Report all service categories, including non-discriminating results.

## Interpretability boundaries

The oracle is a network-based spatial benchmark. It does not optimise population welfare, capacity, cost, zoning compliance or real implementation. Facility tiers and capabilities differ among service types, so **separate service categories** are kept. The decision experiment always adds one site in one service category; budgets involving multiple sites require an additional sequential optimisation and are **not performed** in this baseline.

Facility exclusion can produce zero recorded cultural centres in two streets. Missingness changes cultural-priority choices under the complete official 89-record count. The spatial analysis is conditional on the restricted 83-site dataset and cannot justify claims about the true full supply level of cultural services.

The project's policy selection and oracle use overlapping outcome-relevant street geometry; this is the precise operational issue studied. No inference of an exogenous causal mechanism is drawn from it. Robustness to network source completeness and candidate feasibility requires additional evidence before journal submission.
