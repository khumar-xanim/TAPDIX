# Legacy scoring engine — audit

Scope: `legacy/ai/*` (hand-weighted TypeScript scorer). Python port: `ml/src/tapdix_ml/baseline/`,
verified against the original by `ml/tests/test_legacy_parity.py` (323 cases, exact equality).

Numbers below come from running the original/ported code; "synthetic" means the seeded fixtures in
`ml/tests/fixtures/legacy_cases.json`, **not** real marketplace data.

## A. Bugs (wrong regardless of data)

| # | Defect | Evidence | Fix direction |
|---|---|---|---|
| 1 | **Reliability can never reach 100.** `consistencyScore` is on a 0–20 scale but weighted as if 0–100 → max is 84. | Max over all fixtures = 83.9. A worker maxed on every input scores `reliability 83.9`. | Rescale to 0–100 (new model: learn it) |
| 2 | **Input mutation.** `analyzeTrend` does `reviews.sort()` in place; `getPersonalizedRecommendations` does `workers.sort()` in place. | Review order `1,3,2,5,4` → `5,4,3,2,1` after `scoreWorker()`. Workers `abc` → `bca` after `getPersonalizedRecommendations()`. | Copy before sorting (done in port) |
| 3 | **Dates must be `Date` objects.** API JSON gives strings. | `TypeError: r.date.getTime is not a function` | Parse at the API boundary (pydantic) |
| 4 | **Location matching is substring + English lower-casing.** | `''` matches everything; `İstanbul`≠`istanbul`; `Bakı`≠`BAKI`; `Baku`≠`Bakı`. JS `toLowerCase()` turns `İ` into `i`+combining dot and `I` into `i` (not `ı`). | Az-aware normalisation + canonical city/district table → real distance feature |
| 5 | **Related-category table is one-directional.** | Elektrik worker → "Texniki xidmət" job = 50; reverse = 0. `Boyama`, `Texniki xidmət`, `Santexnika` have no weights → fall back to defaults. | Learn category affinity from data / embeddings |
| 6 | **Non-deterministic.** `Date.now()` inside scoring. | Same inputs, different score tomorrow; past rankings can't be reproduced. | Pass `as_of` (done in port) |

## B. Design weaknesses (what ML should replace)

| # | Weakness | Evidence |
|---|---|---|
| 7 | **No small-sample protection.** One 5.0 review beats fifty 4.8 reviews on quality. | quality 100.0 vs 96.0. `confidence` is computed (54.5 vs 100) but never affects ranking. |
| 8 | **Rating is counted twice.** Review ratings feed `quality` (50% of it); `worker.rating` feeds `reputation` (60% of it). | Effective weight of "rating" is larger than the config says; inputs are near-collinear. |
| 9 | **Saturating inputs.** Years component flat after 6.25 years; jobs component flat after 60 jobs. | 6 y → 58.9 pts, 25 y → 70.0 pts (gap comes from the consistency term, not skill). |
| 10 | **Self-reported certificates are a free bonus.** +3 per certificate, uncapped, unverified. | Identical worker: 0 certs → 78.9, 7 certs → 100.0. |
| 11 | **Weights are hand-set and never validated.** Rows sum to 1.0 (checked) but nothing was fitted. | Also magic numbers: +2/−3 trend, +5 location, label thresholds 85/70/55. |
| 12 | **Rounding then sorting creates ties** broken by input order. | e.g. 3 pairs share a total of 66.0 and 3 share 79.4 among 200 synthetic pairs. |
| 13 | **Missing signals:** price vs budget, real distance, availability, job-text understanding. `URGENCY_MULTIPLIERS` exists but is never referenced. | — |
| 14 | **"Personalised" recommendations** = keep top-3 categories, sort by rating. | No learning, no location, no recency. |
| 15 | **Dead code:** `calculateCommunicationScore`, `calculateProfessionalismScore`, `analyzeClientSatisfaction`. | Not ported. |

Synthetic population: totals range 34.2–91.7 (mean 66.5); 0 of 200 random pairs hit the 100 cap, so
the cap matters only for extreme profiles (the maxed edge case does hit it).

## C. How this feeds the ML plan
- **Baseline to beat:** this scorer, evaluated with NDCG@k / MRR on the same held-out jobs.
- **#7, #8, #9:** a learned ranker (LightGBM LambdaRank) with Bayesian-smoothed rating, review count and
  recency as separate features.
- **#4, #5, #13:** multilingual text embeddings for job↔worker similarity + a distance feature.
- **#11, #12:** weights learned from outcomes (hire / completion / rating), ties broken by model score.
- **#1, #2, #3, #6:** already fixed by construction in the new code path.
