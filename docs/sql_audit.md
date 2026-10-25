# SQL audit - `db/migrations/001_initial_schema.sql` (+ original demo)

Every row was **reproduced on PostgreSQL 16** before the fix, and is **asserted** in `db/verify.sql` after it
(22 assertions). Apply order: `001_initial_schema.sql` -> `db/migrations/002_ml_ready_fixes.sql` -> `db/seed_taxonomy.sql` -> `db/demo_v2.sql` -> `db/verify.sql`.
Upgrading an existing database works the same way (tested on a database loaded with the original demo twice).

| # | Problem (reproduced) | Fix |
|---|---|---|
| 1 | Only 5 categories, names differ from your 8 core groups (`Electrical`, `Painting`, `Carpentry`) | Renamed to your names, 4 added, `Carpentry` hidden (`is_active=false`, row kept), `slug`/`name_az`/`name_ru` columns |
| 2 | Original demo not repeatable: 2nd run duplicated education, certificate, portfolio rows | `demo_v2.sql`: fixed ids + `ON CONFLICT`; dates relative to today (original had hard-coded 2026-10-25) |
| 3 | One phone number -> 4 accounts (`+994 55...`, `055...`, `055-...`) | `normalize_phone()` trigger + E.164 `CHECK` |
| 4 | `UNIQUE(master_id, city, district)` ignores NULL districts -> duplicate areas | Partial unique index for NULL district |
| 5 | Offer total (5) could disagree with its parts (65) | `CHECK` total = labour+materials+travel+other (`NOT VALID` until old rows are validated; `VALIDATE` passed on the upgraded DB) |
| 6 | A user holding both roles could offer on their own listing, run a job with themselves and leave a 5-star review | `jobs CHECK customer<>master`, offer trigger, review-only-on-Completed trigger |
| 7 | `master_profiles` could exist without the Master role | Deferred constraint trigger (checked at COMMIT) |
| 8 | `ml_predictions` rejected photo predictions (`entity_type='Attachment'`) | Entity types extended (`Attachment`, `Job`) |
| 9 | No vocabulary for the NLP model / no confirmed label on listings | `problem_types`, `problem_type_skills`, `skills.skill_code`, `listings.problem_type_id` (composite FK guarantees the problem belongs to the listing's category) |
| 10 | No consent / PII-safe export for training | `customer_profiles.ml_training_consent(+_at)`, `listing_attachments.exif_stripped/sha256`, view `ml_training_listings` (no name/phone/email/address/coordinates, only consenting customers, published listings, EXIF-stripped photos) |
| 11 | No index on `problem_details` JSONB | GIN index |

## Flagged, NOT changed (your call)
* `master_profiles.profile_score` stores a derived/ML-like number in a source table. Prefer `ml_predictions` or a view,
  so the source of truth is never overwritten by a model.
* `UNIQUE (listing_id, master_id)` on offers: a master cannot re-offer after withdrawing. Allow it with a partial unique index on active statuses if needed.
* PostgreSQL has no Azerbaijani full-text-search configuration; use `simple` + trigram/embedding search later.
* Free-text descriptions can still contain phone numbers or addresses: redact in Python (`text.normalize.redact_pii`) before any training.
* Check Azerbaijani personal-data law with a lawyer before training on customer text/photos.

## The older inline `Customers / Masters / Master_Offers` draft (retired)
Customer identity and the announcement were one row (a customer could have only one problem); `Master_Offers`
pointed at a customer, not at a listing; skills/areas were free-form JSON (no vocabulary to match against);
`category` was free text; ratings were stored counters with no `reviews` table to learn from; no jobs/outcomes.
Everything it was trying to do exists, normalised, in the uploaded schema.
