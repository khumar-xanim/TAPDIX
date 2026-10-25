# Run from the repo root:  powershell -ExecutionPolicy Bypass -File .\setup.ps1
$ErrorActionPreference = "Stop"

Write-Host "== Toolchain ==" -ForegroundColor Cyan
node -v
npm -v
$nodeMajor = [int]((node -v).TrimStart('v').Split('.')[0])
if ($nodeMajor -lt 22) { throw "Node 22.12+ required (install: winget install OpenJS.NodeJS.LTS)" }

$py = $null
foreach ($cand in @("py -3.12", "py -3.13", "py -3.11", "python")) {
  try { $v = Invoke-Expression "$cand --version" 2>$null; if ($v -match "Python 3\.(11|12|13)") { $py = $cand; break } } catch {}
}
if (-not $py) { throw "Python 3.11-3.13 required (install: winget install Python.Python.3.12)" }
Write-Host "Using: $py ($v)"

Write-Host "== Web ==" -ForegroundColor Cyan
Push-Location apps/web
npm install
Pop-Location

Write-Host "== Python venv ==" -ForegroundColor Cyan
if (-not (Test-Path .venv)) { Invoke-Expression "$py -m venv .venv" }
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt

if (-not (Test-Path .env)) { Copy-Item .env.example .env }

Write-Host "== Smoke tests ==" -ForegroundColor Cyan
Push-Location apps/web; npm run build; npm test; Pop-Location
& .\.venv\Scripts\python.exe -m pytest

Write-Host "`nDone. Open this folder in VS Code:  code ." -ForegroundColor Green
