# What is inside Tapdix (as of 2026-10-23)

## 1. Front-end prototype (805 lines, one React component - kept private, not in this repository)
| Part | Lines | What it does |
|---|---|---|
| `LandingPage` | 205-398 | Marketing page + sign-up / login forms (client or worker role) |
| `ClientDashboard` | 399-569 | Client view: listings, offers received, chat with a worker, accept an offer |
| `WorkerDashboard` | 570-805 | Worker view: available jobs, send an offer (price + duration) via modal |
**Known problems:** dashboards are defined *inside* the main component (they remount on every state change, inputs
lose focus); everything is hard-coded demo data; login is faked in the browser (two users, password `123456`, which is
even printed on the page: "Test şifrə: 123456"). Not safe or real - rebuild as typed components behind a real API (planned).

## 2. Legacy "AI" (`legacy/ai/`, 6 TypeScript modules)
A hand-weighted scorer (experience, quality, reliability, match, reputation) - **not machine learning**.
Ported 1:1 to Python and proven identical (`ml/tests/test_legacy_parity.py`); 15 defects documented in
`docs/legacy_engine_audit.md`. It is the baseline every new model has to beat.

## 3. Database (two generations)
* `Customers / Masters / Master_Offers` draft: retired (one table mixed the person and the job; offers could not point at a listing).
* `plumbing_marketplace_schema.sql` + demo: the real design (users, roles, master profiles, skills, listings,
  attachments, offers, jobs, reviews, payments, messages, `ml_predictions`). Kept, with fixes: `db/migrations/002_ml_ready_fixes.sql`, `docs/sql_audit.md`.

## 4. New in this iteration
| Piece | Where |
|---|---|
| 8 core categories, 56 problem types, 54 skills (single source of truth) | `ml/data/taxonomy/taxonomy.json` -> SQL seed `db/seed_taxonomy.sql` |
| Synthetic dataset: 4,480 listings (JSONL + CSV), 400 masters | `ml/data/synthetic/` (see `DATASET_CARD.md`) |
| Independent gold test set (80 clear + 12 vague messages) | `ml/data/gold/gold.json` |
| NLP model: listing text -> problem type -> category (+ keywords, confidence) | `ml/src/tapdix_ml/nlp/` |
| Text-vs-photo decision logic | `ml/src/tapdix_ml/vision/fusion.py` |
| YOLO label set (39 objects, 8 defects) + photo folder layout | `ml/data/vision/classes.json`, `ml/data/images/` |
| v0 master matcher (explainable, small-sample safe) | `ml/src/tapdix_ml/matching.py` |
| Evaluation report | `ml/reports/text_clf_report.json` |

## 5. Not built yet
Real data of any kind; a trained YOLO model; a learned ranker; the real API (auth, listings, offers); the typed React UI.
