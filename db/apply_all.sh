#!/usr/bin/env bash
# Applies the whole database sequence to an EMPTY database and runs the verification.
# Uses the standard PG* variables:  PGHOST PGPORT PGUSER PGPASSWORD PGDATABASE
#   createdb tapdix && PGDATABASE=tapdix bash db/apply_all.sh
set -euo pipefail
cd "$(dirname "$0")/.."
export PGCLIENTENCODING=UTF8
for f in db/migrations/001_initial_schema.sql db/migrations/002_ml_ready_fixes.sql \
         db/seed_taxonomy.sql db/demo_v2.sql db/verify.sql; do
  echo "-> $f"
  psql -v ON_ERROR_STOP=1 -q -f "$f"
done
echo "database OK"
