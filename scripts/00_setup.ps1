# 00_setup.ps1 — set up the head-extraction pipeline.
#
# Detects what is already installed and installs ONLY what is missing.
# Nothing is upgraded or reinstalled over an existing tool.
#
# UNTESTED. Written on macOS without a game install. Expect to fix something.
#
#   .\scripts\preflight.ps1        # see what you have, install nothing
#   .\scripts\00_setup.ps1         # install what is missing, then build
#   .\scripts\00_setup.ps1 -WhatIf # print the install plan and stop
#   .\scripts\00_setup.ps1 -CoreOnly   # Python + zstd only, skip Rust/Blender

param(
    [switch]$WhatIf,
    [switch]$CoreOnly,
    [string]$P4kPath
)

$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot 'preflight.ps1') -Quiet

$tools = Show-Preflight

# --- Decide what actually needs installing -----------------------------------

$wanted = if ($CoreOnly) { @('core') } else { @('core', 'extract', 'render') }
$missing = @($tools | Where-Object { -not $_.Exe -and $_.Required -in $wanted })

if ($missing.Count -gt 0) {
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
        throw 'winget not found. Install "App Installer" from the Microsoft Store, then re-run.'
    }

    Write-Host 'Will install:' -ForegroundColor Cyan
    foreach ($m in $missing) { Write-Host ("  {0}  ({1})" -f $m.Name, $m.WingetId) }
    Write-Host ''

    if ($WhatIf) { Write-Host 'WhatIf — stopping here.' -ForegroundColor Cyan; exit 0 }

    $answer = Read-Host 'Install these? [y/N]'
    if ($answer -notmatch '^[Yy]') { Write-Host 'Aborted.'; exit 1 }

    foreach ($m in $missing) {
        Write-Host ("[..]   installing {0}" -f $m.Name) -ForegroundColor Yellow
        winget install --id $m.WingetId --exact `
            --accept-source-agreements --accept-package-agreements
    }

    # Refresh PATH so freshly-installed tools resolve in this session.
    $env:Path = [Environment]::GetEnvironmentVariable('Path','Machine') + ';' +
                [Environment]::GetEnvironmentVariable('Path','User')

    $tools = Get-ToolStatus
    $stillMissing = @($tools | Where-Object { -not $_.Exe -and $_.Required -in $wanted })
    if ($stillMissing.Count -gt 0) {
        Write-Host ''
        Write-Host 'Still not detected after install:' -ForegroundColor Yellow
        foreach ($m in $stillMissing) { Write-Host ("  {0}" -f $m.Name) }
        Write-Host 'Open a NEW terminal and re-run — PATH changes often need a fresh shell.'
        exit 1
    }
} else {
    Write-Host 'All required tools already present — installing nothing.' -ForegroundColor Green
    if ($WhatIf) { exit 0 }
}

# --- Verify the pure-Python tools actually run -------------------------------

$repo   = Resolve-Path (Join-Path $PSScriptRoot '..')
$python = ($tools | Where-Object Name -eq 'Python 3').Exe

Write-Host '[..]   verifying chf.py against the bundled sample' -ForegroundColor Yellow
& $python (Join-Path $repo 'tools\chf.py') dump `
          (Join-Path $repo 'samples\combat_veteran.chf') | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'chf.py failed — check that python and zstd resolve' }
Write-Host '[ok]   chf.py works' -ForegroundColor Green

# --- Locate Data.p4k ---------------------------------------------------------

$p4k = if ($P4kPath) { $P4kPath } else { Find-DataP4k }

if (-not $p4k -or -not (Test-Path $p4k)) {
    Write-Host '[!!]   Data.p4k not found.' -ForegroundColor Red
    Write-Host '       Re-run with the path, e.g.:' -ForegroundColor Red
    Write-Host '       .\scripts\00_setup.ps1 -P4kPath "F:\Roberts Space Industries\StarCitizen\LIVE\Data.p4k"'
    exit 1
}

[Environment]::SetEnvironmentVariable('SC_DATA_P4K', $p4k, 'User')
$env:SC_DATA_P4K = $p4k
Write-Host "[ok]   SC_DATA_P4K = $p4k" -ForegroundColor Green

if ($CoreOnly) {
    Write-Host ''
    Write-Host 'Core setup done. You can now read and edit .chf files.' -ForegroundColor Cyan
    Write-Host 'Re-run without -CoreOnly when you want the mesh pipeline.' -ForegroundColor Cyan
    exit 0
}

# --- StarBreaker -------------------------------------------------------------

$vendor = Join-Path $repo 'vendor'
New-Item -ItemType Directory -Force -Path $vendor | Out-Null
$sb = Join-Path $vendor 'StarBreaker'

if (Test-Path (Join-Path $sb '.git')) {
    Write-Host '[..]   updating StarBreaker' -ForegroundColor Yellow
    git -C $sb pull --ff-only
} else {
    Write-Host '[..]   cloning StarBreaker' -ForegroundColor Yellow
    git clone --depth 1 https://github.com/diogotr7/StarBreaker.git $sb
}

$exe = Join-Path $sb 'target\release\starbreaker.exe'
if (Test-Path $exe) {
    Write-Host '[ok]   starbreaker already built — skipping cargo build' -ForegroundColor Green
} else {
    Write-Host '[..]   building starbreaker (release, several minutes)' -ForegroundColor Yellow
    Push-Location $sb
    try { cargo build --release --bin starbreaker } finally { Pop-Location }
    if (-not (Test-Path $exe)) { throw "build produced no binary at $exe" }
}
Write-Host "[ok]   starbreaker at $exe" -ForegroundColor Green

Write-Host ''
Write-Host 'Setup done. Next: .\scripts\01_discover.ps1' -ForegroundColor Cyan
