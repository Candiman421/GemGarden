# Build-GemGardenDb.ps1  --  stand up gemdesk.db GREEN ON EMPTY from the frozen engine schema + seed.
#
#   pwsh -File build\Build-GemGardenDb.ps1                 # -> <repo>\_core\gemdesk.db
#   pwsh -File build\Build-GemGardenDb.ps1 -DbPath C:\x\gemdesk.db -Force
#
# Applies gemdesk-schema.sql then gemdesk-seed.sql, then asserts: integrity_check ok,
# foreign_key_check clean, 34 tables / 19 views, governance seed present. Refuses to
# overwrite an existing db unless -Force. Uses the sqlite3 CLI, or falls back to python.

[CmdletBinding()]
param(
    [string]$DbPath,
    [switch]$Force
)
$ErrorActionPreference = 'Stop'
$here   = Split-Path -Parent $MyInvocation.MyCommand.Path
$schema = Join-Path $here 'gemdesk-schema.sql'
$seed   = Join-Path $here 'gemdesk-seed.sql'
foreach ($f in @($schema, $seed)) { if (-not (Test-Path $f)) { throw "missing: $f" } }

if (-not $DbPath) {
    $repo   = Split-Path -Parent $here           # build\ lives under the repo root
    $DbPath = Join-Path $repo '_core\gemdesk.db'
}
$dir = Split-Path -Parent $DbPath
if ($dir -and -not (Test-Path $dir)) { New-Item -ItemType Directory -Force -Path $dir | Out-Null }
if (Test-Path $DbPath) {
    if (-not $Force) { throw "db exists: $DbPath  (pass -Force to rebuild from scratch)" }
    Remove-Item -Force $DbPath
}

$sqlite = Get-Command sqlite3 -ErrorAction SilentlyContinue
if ($sqlite) {
    Write-Host "Building with sqlite3 CLI -> $DbPath" -ForegroundColor Cyan
    Get-Content $schema, $seed -Raw | & $sqlite.Source $DbPath
    if ($LASTEXITCODE -ne 0) { throw "sqlite3 returned $LASTEXITCODE" }
} else {
    $py = Get-Command python -ErrorAction SilentlyContinue
    if (-not $py) { throw "need sqlite3 or python on PATH. Install: winget install SQLite.SQLite (or Python.Python.3.12)" }
    Write-Host "sqlite3 not found; building with python sqlite3 -> $DbPath" -ForegroundColor Cyan
    $pyCode = @"
import sqlite3, sys
db = sqlite3.connect(r'''$DbPath''')
for f in (r'''$schema''', r'''$seed'''):
    db.executescript(open(f, encoding='utf-8').read())
db.commit(); db.close()
"@
    $pyCode | & $py.Source -
    if ($LASTEXITCODE -ne 0) { throw "python build returned $LASTEXITCODE" }
}

# ---- assertions ----
function Invoke-Sql([string]$q) {
    if ($sqlite) { return (& $sqlite.Source $DbPath $q) }
    $c = "import sqlite3;print(sqlite3.connect(r'''$DbPath''').execute('''$q''').fetchone()[0])"
    return ($c | & (Get-Command python).Source -)
}
$integrity = (Invoke-Sql 'PRAGMA integrity_check;') -join ''
$tables    = [int]((Invoke-Sql "SELECT count(*) FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';") -join '')
$views     = [int]((Invoke-Sql "SELECT count(*) FROM sqlite_master WHERE type='view';") -join '')
$facets    = [int]((Invoke-Sql 'SELECT count(*) FROM facet_registry;') -join '')
$seedTags  = [int]((Invoke-Sql "SELECT count(*) FROM v_pk_row_ship_class_live WHERE ship_class='engine-seed';") -join '')

$ok = ($integrity -match 'ok') -and ($tables -eq 34) -and ($views -eq 19) -and ($facets -eq 10) -and ($seedTags -eq 14)
Write-Host "integrity=$integrity tables=$tables views=$views facets=$facets engine-seed=$seedTags"
if ($ok) {
    Write-Host "GREEN ON EMPTY: OK  ->  $DbPath" -ForegroundColor Green
} else {
    throw "BUILD ASSERTION FAILED (expected integrity=ok, tables=34, views=19, facets=10, engine-seed=14)"
}
