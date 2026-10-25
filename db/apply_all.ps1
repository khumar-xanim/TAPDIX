# Applies the whole database sequence to an EMPTY database (Windows / PowerShell) and runs the verification.
#   psql -U postgres -c "CREATE DATABASE tapdix"
#   powershell -ExecutionPolicy Bypass -File db\apply_all.ps1 -Db tapdix
param(
  [string]$Db = "tapdix",
  [string]$User = "postgres",
  [string]$DbHost = "localhost",
  [int]$Port = 5432
)
$ErrorActionPreference = "Stop"
$env:PGCLIENTENCODING = "UTF8"
Set-Location (Join-Path $PSScriptRoot "..")
$files = @(
  "db/migrations/001_initial_schema.sql",
  "db/migrations/002_ml_ready_fixes.sql",
  "db/seed_taxonomy.sql",
  "db/demo_v2.sql",
  "db/verify.sql"
)
foreach ($f in $files) {
  Write-Host "-> $f"
  psql -h $DbHost -p $Port -U $User -d $Db -v ON_ERROR_STOP=1 -q -f $f
  if ($LASTEXITCODE -ne 0) { throw "failed: $f" }
}
Write-Host "database OK"
