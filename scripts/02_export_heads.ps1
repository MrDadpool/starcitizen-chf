# 02_export_heads.ps1 — export head meshes from Data.p4k to GLB.
#
# UNTESTED, and it needs a real asset path pattern from 01_discover.ps1 first.
#
#   .\scripts\02_export_heads.ps1 -PathList out\discovery\heads.txt
#
# StarBreaker's `skin export` takes a case-insensitive P4k path *substring*,
# so a partial path is fine.

param(
    # A text file with one P4k asset path per line (from 01_discover.ps1).
    [Parameter(Mandatory = $true)]
    [string]$PathList,

    # Where the .glb files land.
    [string]$OutDir = (Join-Path $PSScriptRoot '..\out\heads')
)

$ErrorActionPreference = 'Stop'

$sb = Join-Path $PSScriptRoot '..\vendor\StarBreaker\target\release\starbreaker.exe'
if (-not (Test-Path $sb)) { throw 'starbreaker not built — run 00_setup.ps1 first' }
if (-not (Test-Path $PathList)) { throw "path list not found: $PathList" }

New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

$paths = Get-Content $PathList |
    Where-Object { $_ -match '\S' -and $_ -notmatch '^\s*#' }

Write-Host "[..]   exporting $($paths.Count) meshes to $OutDir" -ForegroundColor Yellow

$ok = 0
$fail = 0
foreach ($p in $paths) {
    $p = $p.Trim()
    # Flatten the asset path into a safe filename.
    $safe = ($p -replace '[\\/:*?"<>|]', '_') -replace '\.(skin|cgf|chr)$', ''
    $dest = Join-Path $OutDir "$safe.glb"

    if (Test-Path $dest) { $ok++; continue }

    & $sb skin export $p $dest 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0 -and (Test-Path $dest)) {
        $ok++
    } else {
        $fail++
        Write-Host "[!!]   failed: $p" -ForegroundColor DarkYellow
    }
}

Write-Host "[ok]   $ok exported, $fail failed" -ForegroundColor Green
Write-Host ''
Write-Host 'Next: blender --background --python scripts\03_render_sheets.py -- --glb-dir out\heads' -ForegroundColor Cyan
